#!/usr/bin/env python3
"""Local, fail-closed evidence receipts. SPDX-License-Identifier: MIT."""

from __future__ import annotations

import argparse
import hashlib
import html
import http.client
import io
import ipaddress
import json
import re
import shutil
import socket
import ssl
import sys
import tempfile
import time
import unicodedata
import zipfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

VERSION = "0.1.0"
SYSTEMS = {
    "SCIE": ("mjl.clarivate.com", "clarivate.com"),
    "SSCI": ("mjl.clarivate.com", "clarivate.com"),
    "AHCI": ("mjl.clarivate.com", "clarivate.com"),
    "CSSCI": ("cssci.nju.edu.cn", "cssrac.nju.edu.cn"),
    "CSCD": ("sciencechina.cn", "las.ac.cn"),
    "PKU_CORE": ("lib.pku.edu.cn",),
}
COLLECTION_LABELS = {
    "SCIE": ("SCIE", "Science Citation Index Expanded"),
    "SSCI": ("SSCI", "Social Sciences Citation Index"),
    "AHCI": ("AHCI", "Arts & Humanities Citation Index", "Arts and Humanities Citation Index"),
    "CSSCI": ("CSSCI", "中文社会科学引文索引"),
    "CSCD": ("CSCD", "中国科学引文数据库"),
    "PKU_CORE": ("中文核心期刊", "北大核心", "A Guide to the Core Journals of China"),
}
ROLES = (
    "abstract", "introduction", "literature_review", "methods", "results",
    "discussion", "limitations", "conclusion", "references", "appendix", "other",
)
ORIGINS = ("author_finding", "cited_prior_work", "method_description", "hypothesis")
SUPPORT = ("direct", "indirect", "method_precedent", "contradiction", "insufficient")
TARGET_USES = ("background", "hypothesis", "design", "measurement", "analysis", "interpretation")
NORMALIZATION = "NFKC; whitespace; soft hyphens; line-end hyphenation; case-sensitive"
MAX_BYTES = 100 * 1024 * 1024
MAX_PAGES = 1000
MAX_PIXELS = 16_000_000
SNAPSHOT_SUFFIXES = {".pdf", ".html", ".htm", ".txt", ".csv", ".json"}


class Rejected(ValueError):
    """An input does not satisfy the receipt policy."""


def require(condition, message):
    if not condition:
        raise Rejected(message)


def object_(value, label):
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def text(value, label):
    require(isinstance(value, str) and value.strip(), f"{label} is required")
    require("\x00" not in value, f"{label} contains NUL")
    return value.strip()


def integer(value, label, low, high):
    require(type(value) is int and low <= value <= high, f"{label} must be {low}..{high}")
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest_file(path):
    return digest_bytes(path.read_bytes())


def load_json(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out

    require(path.is_file() and not path.is_symlink(), f"missing or symlinked file: {path.name}")
    require(path.stat().st_size <= MAX_BYTES, "JSON exceeds size limit")
    return json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=unique,
        parse_constant=lambda x: (_ for _ in ()).throw(Rejected(f"invalid JSON number: {x}")),
    )


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def confined(root, value):
    raw = Path(text(value, "artifact path"))
    require(not raw.is_absolute() and ".." not in raw.parts, "artifact path escapes its directory")
    base = root.resolve()
    candidate = root / raw
    require(candidate.resolve().is_relative_to(base), "artifact path escapes its directory")
    current = base
    for part in raw.parts:
        current = current / part
        require(not current.is_symlink(), "symlinked artifacts are not allowed")
    require(candidate.is_file(), f"artifact is missing: {raw}")
    require(candidate.stat().st_size <= MAX_BYTES, f"artifact exceeds size limit: {raw}")
    return candidate


def https(value, label, allowed=None):
    parsed = urlparse(text(value, label))
    require(
        parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username
        and not parsed.password and parsed.port in (None, 443),
        f"{label} must be an HTTPS URL without credentials",
    )
    if allowed:
        host = parsed.hostname.lower()
        require(
            any(host == domain or host.endswith("." + domain) for domain in allowed),
            f"{label} is not on an allowed official registry host",
        )


def public_address(host):
    records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(record[4][0] for record in records))
    require(bool(addresses), "download hostname has no address")
    require(all(ipaddress.ip_address(address).is_global for address in addresses),
            "downloads to non-public addresses are rejected")
    return addresses[0]


class PinnedHTTPS(http.client.HTTPSConnection):
    """Pin a public resolved address while keeping hostname/SNI verification."""

    def connect(self):
        address = public_address(self.host)
        sock = socket.create_connection((address, self.port), self.timeout)
        try:
            self.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def download(args):
    destination = Path(args.out).absolute()
    manifest_path = Path(str(destination) + ".download.json")
    require(destination.suffix.lower() == ".pdf", "download output must end in .pdf")
    require(not destination.exists() and not manifest_path.exists(), "download output already exists")
    timeout = integer(args.timeout, "timeout", 1, 60)
    if args.expected_sha256:
        require(bool(re.fullmatch(r"[a-f0-9]{64}", args.expected_sha256)),
                "expected SHA-256 must be lowercase hex")
    requested = text(args.url, "download URL")
    current = requested
    deadline = time.monotonic() + timeout
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".pdf-download-", dir=destination.parent) as temp:
        candidate = Path(temp) / "paper.pdf"
        for hop in range(6):
            https(current, "download URL")
            require("\r" not in current and "\n" not in current, "invalid URL control characters")
            parsed = urlparse(current)
            remaining = deadline - time.monotonic()
            require(remaining > 0, "download exceeded timeout")
            connection = PinnedHTTPS(parsed.hostname, port=443, timeout=remaining)
            try:
                path = parsed.path or "/"
                if parsed.query:
                    path += "?" + parsed.query
                connection.request("GET", path, headers={
                    "Accept": "application/pdf", "User-Agent": "ShowYourReceipts/" + VERSION,
                })
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    require(bool(location) and hop < 5, "invalid or excessive PDF redirects")
                    current = urljoin(current, location)
                    response.close()
                    continue
                require(response.status == 200, f"PDF download returned HTTP {response.status}")
                content_type = response.getheader("Content-Type", "")
                length = response.getheader("Content-Length")
                if length:
                    require(int(length) <= MAX_BYTES, "download exceeds size limit")
                total = 0
                with candidate.open("wb") as stream:
                    while True:
                        remaining = deadline - time.monotonic()
                        require(remaining > 0, "download exceeded timeout")
                        if connection.sock is not None:
                            connection.sock.settimeout(remaining)
                        chunk = response.read(64 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        require(total <= MAX_BYTES, "download exceeds size limit")
                        stream.write(chunk)
                response.close()
                with Paper(candidate):
                    pass
                checksum = digest_file(candidate)
                require(not args.expected_sha256 or checksum == args.expected_sha256,
                        "download SHA-256 does not match the expected value")
                manifest = {
                    "schema_version": 1, "status": "downloaded_candidate",
                    "requested_url": requested, "final_url": current,
                    "fetched_at": date.today().isoformat(), "pdf_sha256": checksum,
                    "content_type": content_type, "bytes": total,
                }
                require(not destination.exists() and not manifest_path.exists(),
                        "download output appeared during retrieval")
                candidate.rename(destination)
                write_json(manifest_path, manifest)
                return {**manifest, "pdf": str(destination), "manifest": str(manifest_path)}
            finally:
                connection.close()
    raise Rejected("PDF redirect limit exceeded")


def recent(value, label):
    raw = text(value, label)
    try:
        checked = date.fromisoformat(raw)
    except ValueError as exc:
        raise Rejected(f"{label} must be YYYY-MM-DD") from exc
    age = (date.today() - checked).days
    require(0 <= age <= 90, f"{label} is future-dated or older than 90 days")


def reviewer(value, label):
    record = object_(value, label)
    require(record.get("kind") in ("human", "agent"), f"{label}.kind must be human or agent")
    text(record.get("name"), label + ".name")


def normalized(value):
    value = re.sub(r"[-\u2010]\s*\n\s*", "", value)
    value = unicodedata.normalize("NFKC", value).replace("\u00ad", "")
    return "".join(char for char in value if not char.isspace())


class VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("p", "br", "div", "td", "tr", "li"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


class Paper:
    def __init__(self, path):
        import pdfplumber
        import pypdfium2 as pdfium

        require(path.is_file() and not path.is_symlink(), "PDF missing or symlinked")
        require(path.stat().st_size <= MAX_BYTES, "PDF exceeds 100 MiB limit")
        require(path.read_bytes()[:5] == b"%PDF-", "input is not a PDF")
        self.path = path
        self.pdf = pdfplumber.open(path)
        self.renderer = None
        try:
            require(self.pdf.doc.encryption is None, "encrypted PDFs are not supported")
            require(1 <= len(self.pdf.pages) <= MAX_PAGES, "PDF page count outside limits")
            self.renderer = pdfium.PdfDocument(str(path))
            self.maps = {}
            for page in self.pdf.pages:
                require(page.rotation == 0, "rotated PDFs are not supported")
                require(abs(page.mediabox[0]) < .01 and abs(page.mediabox[1]) < .01,
                        "non-zero MediaBox origin is not supported")
                require(page.cropbox is None or tuple(page.cropbox) == tuple(page.mediabox),
                        "differing CropBox/MediaBox is not supported")
                require(page.width * page.height * 4 <= MAX_PIXELS,
                        "page exceeds render pixel limit")
            require(any(page.chars for page in self.pdf.pages),
                    "image-only PDF: OCR must not be silently substituted")
        except Exception:
            self.close()
            raise

    def close(self):
        if self.renderer is not None:
            self.renderer.close()
        self.pdf.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def count(self):
        return len(self.pdf.pages)

    def page(self, number):
        integer(number, "PDF page", 1, self.count)
        return self.pdf.pages[number - 1]

    def mapping(self, number, region=None):
        key = (number, tuple(region) if region else None)
        if key not in self.maps:
            page = self.page(number)
            if region:
                require(len(region) == 4, "region needs four coordinates")
                x0, top, x1, bottom = region
                require(0 <= x0 < x1 <= page.width and 0 <= top < bottom <= page.height,
                        "region lies outside the page")
                page = page.crop(tuple(region))
            tm = page.get_textmap(use_text_flow=True, x_tolerance=1, y_tolerance=3)
            require(len(tm.tuples) <= 2_000_000, "page text exceeds character limit")
            self.maps[key] = tm.tuples
        return self.maps[key]

    def page_text(self, number):
        return "".join(char for char, _ in self.mapping(number))

    def match(self, number, quote, occurrence=None, region=None):
        tuples = self.mapping(number, region)
        raw = "".join(char for char, _ in tuples)
        skipped = set()
        for match in re.finditer(r"[-\u2010]\s*\n\s*", raw):
            skipped.update(range(match.start(), match.end()))
        chars, indices = [], []
        for i, (char, _) in enumerate(tuples):
            if i in skipped:
                continue
            for expanded in unicodedata.normalize("NFKC", char):
                if not expanded.isspace() and expanded != "\u00ad":
                    chars.append(expanded)
                    indices.append(i)
        needle = normalized(text(quote, "quote"))
        require(len(needle) >= 3, "quote is too short to locate safely")
        searchable = "".join(chars)
        starts = [m.start() for m in re.finditer(re.escape(needle), searchable)]
        require(bool(starts), f"quote does not occur on PDF page {number}")
        if occurrence is None:
            require(len(starts) == 1, "ambiguous quote; specify --occurrence")
            selected = 0
        else:
            selected = integer(occurrence, "occurrence", 1, len(starts)) - 1
        start = starts[selected]
        low, high = indices[start], indices[start + len(needle) - 1]
        literal = raw[low:high + 1]
        glyphs = {}
        for _, glyph in tuples[low:high + 1]:
            if glyph:
                key = (glyph["x0"], glyph["top"], glyph["x1"], glyph["bottom"])
                glyphs[key] = glyph
        require(bool(glyphs), "quote has no drawable PDF glyphs")
        boxes = glyph_rectangles(list(glyphs.values()))
        return {
            "literal": literal,
            "occurrence": selected + 1,
            "match_count": len(starts),
            "boxes": boxes,
            "context": raw[max(0, low - 1800):min(len(raw), high + 1801)],
        }


def glyph_rectangles(glyphs):
    rows = {}
    for glyph in glyphs:
        rows.setdefault(round(glyph["top"], 1), []).append(glyph)
    boxes = []
    for glyph_row in rows.values():
        group = []
        for glyph in sorted(glyph_row, key=lambda x: x["x0"]):
            if group and glyph["x0"] - group[-1]["x1"] > max(8, glyph["size"]):
                boxes.append(rectangle(group))
                group = []
            group.append(glyph)
        if group:
            boxes.append(rectangle(group))
    return sorted(boxes, key=lambda r: (r[1], r[0]))


def rectangle(glyphs):
    return [round(value, 3) for value in (
        min(g["x0"] for g in glyphs), min(g["top"] for g in glyphs),
        max(g["x1"] for g in glyphs), max(g["bottom"] for g in glyphs),
    )]


def snapshot_text(path):
    require(path.suffix.lower() in SNAPSHOT_SUFFIXES, "unsupported snapshot format")
    if path.suffix.lower() == ".pdf":
        with Paper(path) as paper:
            return "\n".join(paper.page_text(i) for i in range(1, paper.count + 1))
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".html", ".htm"):
        parser = VisibleHTML()
        parser.feed(raw)
        return html.unescape("".join(parser.parts))
    return raw


def valid_issn(value):
    value = text(value, "article.issn").upper()
    require(bool(re.fullmatch(r"\d{4}-\d{3}[\dX]", value)), "invalid ISSN format")
    digits = value.replace("-", "")
    total = sum(int(digit) * (8 - i) for i, digit in enumerate(digits[:7]))
    total += 10 if digits[7] == "X" else int(digits[7])
    require(total % 11 == 0, "invalid ISSN checksum")
    return value


def target_units(path):
    """Return numbered DOCX paragraphs or plain-text/Markdown lines."""
    require(path.is_file() and not path.is_symlink(), "target document is missing or symlinked")
    require(path.stat().st_size <= MAX_BYTES, "target document exceeds size limit")
    require(path.suffix.lower() in (".docx", ".txt", ".md"),
            "target manuscript must be DOCX, TXT or Markdown")
    if path.suffix.lower() == ".docx":
        with zipfile.ZipFile(path) as archive:
            require(sum(item.file_size for item in archive.infolist()) <= 50 * 1024 * 1024,
                    "target DOCX exceeds decompressed size limit")
            data = archive.read("word/document.xml")
        require(b"<!DOCTYPE" not in data.upper() and b"<!ENTITY" not in data.upper(),
                "target DOCX XML declarations are not supported")
        document = ElementTree.fromstring(data)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        units = [
            "".join(node.text or "" for node in paragraph.findall(".//w:t", ns))
            for paragraph in document.findall(".//w:p", ns)
        ]
        return "paragraph", units
    return "line", path.read_text(encoding="utf-8").splitlines()


def validate_target(record, root):
    object_(record, "target")
    require(record.get("schema_version") == 1, "unsupported target schema")
    require(record.get("kind") in ("manuscript", "research_objective"), "target kind is required")
    for field in ("title", "research_question"):
        text(record.get(field), "target." + field)
    require(record.get("intended_use") in TARGET_USES, "target intended use is required")
    source = confined(root, record.get("document"))
    require(digest_file(source) == record.get("document_sha256"), "target manuscript hash mismatch")
    unit, units = target_units(source)
    loc = object_(record.get("location"), "target.location")
    require(loc.get("unit") == unit, f"target unit must be {unit}")
    number = integer(loc.get("unit_number"), "target unit number", 1, len(units))
    quote = text(loc.get("quote"), "target original passage")
    require(normalized(quote) in normalized(units[number - 1]),
            "target passage absent from the specified manuscript paragraph/line")
    heading = text(loc.get("section_heading"), "target section heading")
    heading_unit = integer(loc.get("heading_unit"), "target heading unit", 1, number)
    if heading != "unheaded":
        require(normalized(heading) in normalized(units[heading_unit - 1]),
                "target section heading absent from the specified paragraph/line")
    return source


def validate_source(record, root, paper):
    object_(record, "source")
    require(record.get("schema_version") == 1, "unsupported source schema version")
    article = object_(record.get("article"), "article")
    for field in ("title", "journal"):
        text(article.get(field), "article." + field)
    https(article.get("url"), "article.url")
    doi = article.get("doi")
    require(doi is None or isinstance(doi, str), "DOI must be a string or null")
    if doi:
        require(bool(re.fullmatch(r"10\.\d{4,9}/\S+", doi)), "invalid DOI")
    year = integer(article.get("year"), "article.year", 1600, date.today().year)
    require(article.get("kind") in (
        "original_research", "review", "systematic_review", "methodology",
    ), "only eligible journal article types are accepted")
    require(article.get("version") == "published", "only the published paper version is eligible")
    issn = valid_issn(article.get("issn"))
    identity = object_(article.get("identity"), "article.identity")
    located = paper.match(identity.get("page"), identity.get("quote"))
    identifier = doi or article["title"]
    require(normalized(identifier).lower() in normalized(located["literal"]).lower(),
            "PDF identity anchor does not contain the article identifier")
    index = object_(record.get("index"), "index")
    require(index.get("system") in SYSTEMS, "journal collection is not eligible")
    https(index.get("official_url"), "index.official_url", SYSTEMS[index["system"]])
    text(index.get("edition"), "index.edition")
    start = integer(index.get("coverage_start_year"), "coverage start", 1600, date.today().year)
    end = integer(index.get("coverage_end_year"), "coverage end", start, date.today().year)
    require(start <= year <= end, "article year is not covered by the official record")
    recent(index.get("checked_at"), "index.checked_at")
    reviewer(index.get("reviewer"), "index.reviewer")
    index_file = confined(root, index.get("snapshot"))
    require(digest_file(index_file) == index.get("snapshot_sha256"), "index snapshot hash mismatch")
    entry = text(index.get("membership_quote"), "membership quote")
    saved_index = normalized(snapshot_text(index_file))
    require(normalized(entry) in saved_index, "membership quote absent from saved index")
    require(normalized(issn) in normalized(entry), "membership entry does not contain the ISSN")
    label = text(index.get("collection_label"), "collection label")
    require(any(normalized(alias).lower() in normalized(label).lower()
                for alias in COLLECTION_LABELS[index["system"]]),
            "collection label does not identify the selected core system")
    require(not any(token in normalized(label).lower()
                    for token in ("esci", "emergingsources", "扩展", "extended")),
            "extended/emerging collections are not eligible")
    require(normalized(label) in saved_index, "collection label absent from official snapshot")
    status = object_(record.get("status"), "status")
    require(status.get("assessment") in ("clear", "corrected"),
            "unchecked, retracted or concerning publisher status is rejected")
    https(status.get("publisher_url"), "status.publisher_url")
    recent(status.get("checked_at"), "status.checked_at")
    reviewer(status.get("reviewer"), "status.reviewer")
    status_file = confined(root, status.get("snapshot"))
    require(digest_file(status_file) == status.get("snapshot_sha256"), "publisher snapshot hash mismatch")
    require(normalized(identifier).lower() in normalized(snapshot_text(status_file)).lower(),
            "publisher status snapshot does not identify the article")
    if status["assessment"] == "corrected":
        https(status.get("correction_url"), "status.correction_url")
        text(status.get("correction_note"), "status.correction_note")
    return index_file, status_file


def validate_location(location, paper):
    object_(location, "location")
    integer(location.get("page"), "location.page", 1, paper.count)
    text(location.get("printed_page"), "location.printed_page")
    text(location.get("paragraph"), "location.paragraph")
    require(location.get("section_role") in ROLES, "section role is required")
    require(location.get("origin") in ORIGINS, "claim origin is required")
    heading = text(location.get("section_heading"), "section heading")
    number = integer(location.get("heading_page"), "heading page", 1, location["page"])
    if heading != "unheaded":
        paper.match(number, heading, occurrence=1)
    return location


def render(paper, number, boxes):
    from PIL import ImageDraw

    page = paper.renderer[number - 1]
    bitmap = page.render(scale=2)
    original = bitmap.to_pil().convert("RGB").copy()
    bitmap.close()
    page.close()
    expected = (round(paper.page(number).width * 2), round(paper.page(number).height * 2))
    require(abs(original.width - expected[0]) <= 1 and abs(original.height - expected[1]) <= 1,
            "rendered geometry mismatch")
    annotated = original.copy()
    draw = ImageDraw.Draw(annotated)
    for x0, _, x1, bottom in boxes:
        y = min(original.height - 1, round(bottom * 2 + 2))
        draw.line((round(x0 * 2), y, round(x1 * 2), y), fill=(220, 25, 35), width=3)
    top = max(0, min(b[1] for b in boxes) - 72)
    bottom = min(paper.page(number).height, max(b[3] for b in boxes) + 72)
    for glyph in paper.page(number).chars:
        if glyph["top"] < top < glyph["bottom"]:
            top = max(0, glyph["top"] - 2)
        if glyph["top"] < bottom < glyph["bottom"]:
            bottom = min(paper.page(number).height, glyph["bottom"] + 2)
    # Full-width context keeps line starts/ends intact around mid-line quotes.
    crop = [0, round(top * 2), original.width, round(bottom * 2)]
    images = {
        "page-original.png": original, "page-underlined.png": annotated,
        "excerpt-original.png": original.crop(tuple(crop)),
        "excerpt-underlined.png": annotated.crop(tuple(crop)),
    }
    encoded = {}
    for name, image in images.items():
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded[name] = buffer.getvalue()
    return encoded, crop


def packet_digest(record):
    return digest_bytes(canonical({key: value for key, value in record.items() if key != "packet_sha256"}))


def validate_anchor(anchor, paper):
    validate_location(anchor, paper)
    return paper.match(anchor["page"], anchor.get("quote"), anchor.get("occurrence"),
                       anchor.get("region"))


def full_page_review(record, paper, label):
    pages = record.get("all_pages_reviewed")
    require(isinstance(pages, list) and all(type(p) is int for p in pages),
            f"{label}.all_pages_reviewed must contain integer pages")
    require(sorted(set(pages)) == list(range(1, paper.count + 1)),
            f"{label} requires full-text page coverage")
    text(record.get("search_notes"), label + ".search_notes")


def validate_abstract_screen(screen, paper):
    object_(screen, "abstract_screen")
    text(screen.get("rationale"), "abstract_screen.rationale")
    quotes = screen.get("quotes")
    require(isinstance(quotes, list), "abstract_screen.quotes must be an array")
    if screen.get("status") == "present":
        require(bool(quotes), "abstract screening needs a literal abstract passage")
        require(screen.get("decision") in ("target_mentioned", "not_mentioned_full_text_review"),
                "invalid abstract screening decision")
        for anchor in quotes:
            require(anchor.get("section_role") == "abstract", "screening passage must be in the abstract")
            validate_anchor(anchor, paper)
        if screen["decision"] == "not_mentioned_full_text_review":
            full_page_review(screen, paper, "abstract_screen")
    else:
        require(screen.get("status") == "absent" and not quotes
                and screen.get("decision") == "no_abstract_full_text_review",
                "missing abstract needs an explicit absence/full-text review record")
        full_page_review(screen, paper, "abstract_screen")


def article_identifier(source):
    article = source["article"]
    return article.get("doi") or article["title"]


def identifier_key(value):
    return normalized(text(value, "article identifier")).casefold()


def reference_identifies(identifier, literal):
    if identifier.startswith("10."):
        # Published references often wrap a DOI across lines. Preserve boundaries
        # so a suffix added to the real DOI cannot pass as the requested paper.
        pattern = r"\s*".join(re.escape(char) for char in identifier) + r"(?![\w/+-])"
        return bool(re.search(pattern, literal, re.I))
    return identifier_key(identifier) in identifier_key(literal)


def trace_names(number):
    prefix = f"trace-{number:03d}"
    names = {prefix + "-source.pdf", prefix + "-source.json"}
    for role in ("passage", "reference"):
        names.add(prefix + "-" + role + "-context.txt")
        names.update(prefix + "-" + role + "-" + name for name in (
            "page-original.png", "page-underlined.png", "excerpt-original.png", "excerpt-underlined.png",
        ))
    return prefix, names


def validate_lineage(lineage, root, source, primary, staging=None):
    """Check every citation edge; optionally copy its immutable evidence to staging."""
    object_(lineage, "lineage")
    require(lineage.get("schema_version") == 1, "unsupported lineage schema")
    require(lineage.get("resolution") == "original_source_resolved",
            "unresolved provenance cannot anchor final evidence")
    recent(lineage.get("reviewed_at"), "lineage.reviewed_at")
    reviewer(lineage.get("reviewer"), "lineage.reviewer")
    final = identifier_key(lineage.get("final_identifier"))
    require(final == identifier_key(article_identifier(source)),
            "lineage endpoint does not identify the primary source PDF")
    hops = lineage.get("hops")
    require(isinstance(hops, list) and len(hops) <= 32, "lineage.hops must be an array of at most 32 hops")
    require(all(isinstance(hop, dict) for hop in hops), "each lineage hop must be an object")
    first = hops[0].get("identifier") if hops else lineage["final_identifier"]
    require(identifier_key(lineage.get("initial_identifier")) == identifier_key(first),
            "lineage starts at a different paper")
    seen = {final}
    expected = {"lineage.json"}
    for number, hop in enumerate(hops, 1):
        object_(hop, "lineage hop")
        current = identifier_key(hop.get("identifier"))
        require(current not in seen, "lineage contains a cycle or repeated paper")
        seen.add(current)
        next_id = hops[number].get("identifier") if number < len(hops) else lineage["final_identifier"]
        require(identifier_key(hop.get("cited_identifier")) == identifier_key(next_id),
                "broken citation chain: cited identifier must match the next paper")
        text(hop.get("citation_marker"), "hop.citation_marker")
        text(hop.get("reference_marker"), "hop.reference_marker")
        text(hop.get("link_rationale"), "hop.link_rationale")
        pdf_path = confined(root, hop.get("pdf"))
        source_path = confined(root, hop.get("source"))
        hop_source = load_json(source_path)
        require(current == identifier_key(article_identifier(hop_source)),
                "hop source record identifies a different paper")
        require(hop.get("pdf_sha256") == digest_file(pdf_path), "hop PDF hash mismatch")
        prefix, names = trace_names(number)
        with Paper(pdf_path) as paper:
            index_file, status_file = validate_source(hop_source, source_path.parent, paper)
            validate_abstract_screen(hop.get("abstract_screen"), paper)
            passage = object_(hop.get("passage"), "hop.passage")
            reference = object_(hop.get("reference"), "hop.reference")
            require(passage.get("origin") == "cited_prior_work",
                    "a citation hop must describe cited prior work")
            require(reference.get("section_role") == "references", "citation entry must be in references")
            passage_match = validate_anchor(passage, paper)
            reference_match = validate_anchor(reference, paper)
            marker = normalized(hop["citation_marker"])
            require(marker in normalized(passage_match["literal"])
                    and normalized(hop["reference_marker"]) in normalized(reference_match["literal"]),
                    "citation marker must link the passage and its reference-list entry")
            reference_id = text(hop["cited_identifier"], "cited identifier")
            require(reference_identifies(reference_id, reference_match["literal"]),
                    "reference entry does not identify the exact next DOI/title")
            index_name = prefix + "-index-record" + index_file.suffix.lower()
            status_name = prefix + "-publisher-record" + status_file.suffix.lower()
            names.update((index_name, status_name))
            if staging is None:
                require(hop["pdf"] == prefix + "-source.pdf"
                        and hop["source"] == prefix + "-source.json",
                        "unexpected bundled hop paths")
                require(hop_source["index"]["snapshot"] == index_name
                        and hop_source["status"]["snapshot"] == status_name,
                        "unexpected bundled hop snapshot paths")
            else:
                shutil.copyfile(pdf_path, staging / (prefix + "-source.pdf"))
                shutil.copyfile(index_file, staging / index_name)
                shutil.copyfile(status_file, staging / status_name)
                hop_source["index"]["snapshot"] = index_name
                hop_source["status"]["snapshot"] = status_name
                write_json(staging / (prefix + "-source.json"), hop_source)
                hop["pdf"] = prefix + "-source.pdf"
                hop["source"] = prefix + "-source.json"
            for role, anchor, matched in (
                ("passage", passage, passage_match), ("reference", reference, reference_match),
            ):
                images, _ = render(paper, anchor["page"], matched["boxes"])
                artifacts = {prefix + "-" + role + "-" + name: data for name, data in images.items()}
                artifacts[prefix + "-" + role + "-context.txt"] = matched["context"].encode("utf-8")
                for name, data in artifacts.items():
                    if staging is not None:
                        (staging / name).write_bytes(data)
                    else:
                        require(confined(root, name).read_bytes() == data,
                                f"lineage image/context mismatch: {name}")
            provenance_path = Path(str(pdf_path) + ".download.json") if staging is not None else (
                confined(root, hop["download_manifest"]) if hop.get("download_manifest") else None)
            if provenance_path is not None and provenance_path.exists():
                provenance = load_json(provenance_path)
                require(provenance.get("pdf_sha256") == hop["pdf_sha256"],
                        "hop download manifest does not identify its PDF")
                https(provenance.get("final_url"), "hop retrieved PDF URL")
                manifest_name = prefix + "-download.json"
                names.add(manifest_name)
                if staging is not None:
                    shutil.copyfile(provenance_path, staging / manifest_name)
                    hop["download_manifest"] = manifest_name
                else:
                    require(hop["download_manifest"] == manifest_name, "unexpected hop manifest path")
            else:
                require(not hop.get("download_manifest"), "hop download manifest is missing")
        expected.update(names)
    ownership = object_(lineage.get("ownership"), "lineage.ownership")
    kind = ownership.get("kind")
    require(kind in ("own_data", "own_method", "own_synthesis"),
            "endpoint must own the data, method or synthesis; cited claims/hypotheses are unresolved")
    text(ownership.get("rationale"), "ownership.rationale")
    cues = ownership.get("context_cues")
    require(isinstance(cues, list) and bool(cues), "ownership needs matched contextual evidence")
    for cue in cues:
        require(cue.get("origin") in ("author_finding", "method_description"),
                "ownership cue cannot itself be a citation or hypothesis")
        validate_anchor(cue, primary)
    if kind == "own_data":
        require(source["article"]["kind"] == "original_research", "own data requires original research")
        require(any(cue["origin"] == "author_finding" for cue in cues),
                "own data needs an author's finding in context")
    elif kind == "own_synthesis":
        require(source["article"]["kind"] in ("review", "systematic_review"),
                "own synthesis requires a review article")
    else:
        require(source["article"]["kind"] in ("original_research", "methodology"),
                "own method requires original research or methodology")
    if staging is not None:
        write_json(staging / "lineage.json", lineage)
    return expected


def extract(args):
    destination = Path(args.out).absolute()
    require(not destination.exists(), "output already exists; use a new packet directory")
    require(not destination.is_symlink(), "output must not be a symlink")
    source_path = Path(args.source).absolute()
    source = load_json(source_path)
    target_path = Path(args.target).absolute()
    target = load_json(target_path)
    target_file = validate_target(target, target_path.parent)
    lineage_path = Path(args.lineage).absolute()
    lineage = load_json(lineage_path)
    quote = Path(args.quote_file).read_text(encoding="utf-8")
    location = {
        "page": args.page, "printed_page": args.printed_page,
        "section_heading": args.section_heading, "heading_page": args.heading_page,
        "section_role": args.section_role, "paragraph": args.paragraph, "origin": args.origin,
    }
    with Paper(Path(args.pdf)) as paper:
        index_file, status_file = validate_source(source, source_path.parent, paper)
        validate_location(location, paper)
        matched = paper.match(args.page, quote, args.occurrence, args.region)
        images, crop = render(paper, args.page, matched["boxes"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".receipt-", dir=destination.parent) as temp:
            staging = Path(temp) / "packet"
            staging.mkdir()
            validate_lineage(lineage, lineage_path.parent, source, paper, staging)
            index_name = "index-record" + index_file.suffix.lower()
            status_name = "publisher-record" + status_file.suffix.lower()
            target_name = "target-document" + target_file.suffix.lower()
            shutil.copyfile(paper.path, staging / "source.pdf")
            shutil.copyfile(index_file, staging / index_name)
            shutil.copyfile(status_file, staging / status_name)
            shutil.copyfile(target_file, staging / target_name)
            source["index"]["snapshot"] = index_name
            source["status"]["snapshot"] = status_name
            write_json(staging / "source.json", source)
            target["document"] = target_name
            write_json(staging / "target.json", target)
            provenance_path = Path(str(paper.path) + ".download.json")
            retrieval = {"method": "local_import"}
            if provenance_path.exists():
                provenance = load_json(provenance_path)
                require(provenance.get("pdf_sha256") == digest_file(paper.path),
                        "download manifest does not identify this PDF")
                https(provenance.get("final_url"), "retrieved PDF URL")
                shutil.copyfile(provenance_path, staging / "download.json")
                retrieval = {"method": "download", "manifest": "download.json"}
            (staging / "context.txt").write_text(matched["context"], encoding="utf-8")
            for name, data in images.items():
                (staging / name).write_bytes(data)
            record = {
                "schema_version": 1, "generator_version": VERSION, "state": "draft",
                "retrieval": retrieval,
                "location": location, "submitted_quote": quote.strip(),
                "literal_quote": matched["literal"], "normalization": NORMALIZATION,
                "occurrence": matched["occurrence"], "match_count": matched["match_count"],
                "region": args.region, "glyph_rectangles": matched["boxes"],
                "render": {"scale": 2, "crop_pixels": crop},
                "files": {p.name: digest_file(p) for p in sorted(staging.iterdir())},
            }
            record["packet_sha256"] = packet_digest(record)
            write_json(staging / "receipt.json", record)
            require(not destination.exists(), "output appeared during extraction")
            staging.rename(destination)
    return {"status": "draft", "bundle": str(destination), "packet_sha256": record["packet_sha256"]}


def validate_review(review, record, paper, source, target):
    object_(review, "review")
    require(review.get("schema_version") == 1, "unsupported review schema")
    require(review.get("packet_sha256") == record["packet_sha256"], "review binds a different packet")
    recent(review.get("reviewed_at"), "review.reviewed_at")
    reviewer(review.get("reviewer"), "review.reviewer")
    require(review.get("support") in SUPPORT, "invalid support category")
    for field in (
        "claim", "summary", "translation", "scope_assessment", "applicability_mismatch",
        "limitations_summary", "counterevidence_summary",
    ):
        text(review.get(field), "review." + field)
    validate_abstract_screen(review.get("abstract_screen"), paper)
    require(record["location"]["origin"] in ("author_finding", "method_description"),
            "final passage is a cited claim or hypothesis; trace to its original source")
    alignment = object_(review.get("target_alignment"), "review.target_alignment")
    require(alignment.get("intended_use") == target["intended_use"],
            "review target use does not match the requested manuscript use")
    require(alignment.get("target_quote") == target["location"]["quote"],
            "review does not bind the exact user manuscript passage")
    for field in ("related_aspect", "rationale", "supports", "does_not_support"):
        text(alignment.get(field), "target_alignment." + field)
    if review["support"] == "direct":
        require(record["location"]["origin"] == "author_finding",
                "cited work, methods or hypotheses cannot be direct experimental evidence")
        require(source["article"]["kind"] == "original_research",
                "reviews/methodology are not direct experimental evidence")
    anchors = object_(review.get("anchors"), "review.anchors")
    for role in ("purpose", "methods", "results", "limitations", "counterevidence"):
        anchor = object_(anchors.get(role), "anchor." + role)
        quotes = anchor.get("quotes")
        require(isinstance(quotes, list), f"anchor.{role}.quotes must be an array")
        if not quotes:
            require(role in ("limitations", "counterevidence"), f"anchor.{role} needs a quote")
            full_page_review(anchor, paper, "anchor." + role)
        for item in quotes:
            validate_anchor(item, paper)


def check(bundle):
    root = Path(bundle).absolute()
    require(root.is_dir() and not root.is_symlink(), "bundle is missing or symlinked")
    record = load_json(confined(root, "receipt.json"))
    require(record.get("schema_version") == 1 and record.get("state") == "draft",
            "unsupported receipt format/state")
    require(record.get("generator_version") == VERSION, "unsupported receipt generator version")
    require(record.get("packet_sha256") == packet_digest(record), "packet manifest hash mismatch")
    source = load_json(confined(root, "source.json"))
    target = load_json(confined(root, "target.json"))
    lineage = load_json(confined(root, "lineage.json"))
    validate_target(target, root)
    expected = {
        "source.pdf", "source.json", "context.txt", "page-original.png", "page-underlined.png",
        "excerpt-original.png", "excerpt-underlined.png",
        source["index"]["snapshot"], source["status"]["snapshot"],
        "target.json", target["document"],
    }
    retrieval = object_(record.get("retrieval"), "receipt.retrieval")
    require(retrieval.get("method") in ("local_import", "download"), "invalid retrieval method")
    if retrieval["method"] == "download":
        require(retrieval.get("manifest") == "download.json", "invalid download manifest path")
        expected.add("download.json")
        provenance = load_json(confined(root, "download.json"))
        require(provenance.get("pdf_sha256") == digest_file(confined(root, "source.pdf")),
                "download manifest does not identify the bundled PDF")
        https(provenance.get("final_url"), "retrieved PDF URL")
    files = object_(record.get("files"), "receipt.files")
    for name, checksum in files.items():
        require(digest_file(confined(root, name)) == checksum, f"artifact hash mismatch: {name}")
    with Paper(confined(root, "source.pdf")) as paper:
        validate_source(source, root, paper)
        expected.update(validate_lineage(lineage, root, source, paper))
        require(set(files) == expected, "receipt artifact set is incomplete or unexpected")
        loc = validate_location(record.get("location"), paper)
        require((lineage["ownership"]["kind"] == "own_method") ==
                (loc["origin"] == "method_description"),
                "endpoint ownership and selected passage origin disagree")
        require(record.get("normalization") == NORMALIZATION, "unexpected normalization")
        matched = paper.match(loc["page"], record.get("submitted_quote"), record.get("occurrence"),
                              record.get("region"))
        require(matched["literal"] == record.get("literal_quote"), "literal quote mismatch")
        require(matched["match_count"] == record.get("match_count"), "match count mismatch")
        require(matched["boxes"] == record.get("glyph_rectangles"), "glyph rectangle mismatch")
        require(confined(root, "context.txt").read_text(encoding="utf-8") == matched["context"],
                "context text mismatch")
        images, crop = render(paper, loc["page"], matched["boxes"])
        require(record.get("render") == {"scale": 2, "crop_pixels": crop}, "render settings mismatch")
        for name, data in images.items():
            require(digest_bytes(data) == files[name], f"rendered image mismatch: {name}")
        review = load_json(confined(root, "review.json"))
        validate_review(review, record, paper, source, target)
    return {
        "status": "record_checks_passed",
        "scientific_interpretation": "reviewer_assessed_not_machine_certified",
        "reviewer": review["reviewer"], "packet_sha256": record["packet_sha256"],
    }, record, source, review


def location_caption(loc):
    return (
        f"PDF p. {loc['page']} / printed p. {loc['printed_page']} | "
        f"{loc['section_heading']} ({loc['section_role']}; heading on PDF p. {loc['heading_page']})"
        f" | {loc['paragraph']} | origin: {loc['origin']}"
    )


def blockquote(value):
    return "\n".join("> " + line for line in value.splitlines())


def report_content(record, source, review, target_record, lineage):
    article = source["article"]
    target_loc = target_record["location"]
    alignment = review["target_alignment"]
    caption = location_caption(record["location"])
    lines = [
        "# ShowYourReceipts", "", "## Evidence receipt", "",
        f"**Claim:** {review['claim']}", "",
        f"**Citation:** {article['title']}. {article['journal']} ({article['year']}).",
        f"**Article:** {article['url']}", f"**DOI:** {article.get('doi') or 'not assigned'}",
        f"**Core record:** {source['index']['system']} / {source['index']['edition']}",
        f"**Location:** {caption}", f"**Support:** {review['support']}", "",
        "### Abstract screening and original-source attribution", "",
        f"**Abstract decision:** {review['abstract_screen']['decision']}",
        review["abstract_screen"]["rationale"], "",
    ]
    for anchor in review["abstract_screen"]["quotes"]:
        lines.extend([blockquote(anchor["quote"]), "", location_caption(anchor), ""])
    lines.extend([
        f"**Trace:** {lineage['initial_identifier']} → {lineage['final_identifier']}",
        f"**Resolution:** {lineage['resolution']}",
        f"**Original source PDF:** [source.pdf](source.pdf)",
        f"**Ownership:** {lineage['ownership']['kind']} — {lineage['ownership']['rationale']}", "",
    ])
    for cue in lineage["ownership"]["context_cues"]:
        lines.extend([blockquote(cue["quote"]), "", location_caption(cue), ""])
    for number, hop in enumerate(lineage["hops"], 1):
        prefix, _ = trace_names(number)
        lines.extend([
            f"#### Citation hop {number}: {hop['identifier']} → {hop['cited_identifier']}", "",
            f"[Original hop PDF]({hop['pdf']})", "", hop["link_rationale"], "",
            f"Abstract decision: {hop['abstract_screen']['decision']}. "
            f"{hop['abstract_screen']['rationale']}", "",
        ])
        for role in ("passage", "reference"):
            anchor = hop[role]
            lines.extend([
                f"**{role}:** {location_caption(anchor)}", "", blockquote(anchor["quote"]), "",
                f"![Original {role}]({prefix}-{role}-page-original.png)", "",
                f"![Underlined {role}]({prefix}-{role}-page-underlined.png)", "",
                f"*{role} · {location_caption(anchor)}*", "",
            ])
    lines.extend([
        "### Relation to your manuscript or objective", "",
        f"**User document:** {target_record['title']}",
        f"**User location:** {target_loc['section_heading']} | "
        f"{target_loc['unit']} {target_loc['unit_number']} "
        f"(heading at {target_loc['unit']} {target_loc['heading_unit']})", "",
        "**User's original passage:**", "", blockquote(target_loc["quote"]), "",
        f"**Research question:** {target_record['research_question']}", "",
        f"**Specific aspect:** {alignment['related_aspect']}",
        f"**Intended use:** {alignment['intended_use']}", "",
        f"**Why this evidence is relevant:** {alignment['rationale']}", "",
        f"**Supports:** {alignment['supports']}", "",
        f"**Does not support:** {alignment['does_not_support']}", "",
        "### Original passage", "", blockquote(record["literal_quote"]), "",
        "### Translation (reviewer supplied)", "", review["translation"], "",
        "### Screenshots", "",
        "![Original full page](page-original.png)", "", "*Original · " + caption + "*", "",
        "![Underlined full page](page-underlined.png)", "", "*Red underline · " + caption + "*", "",
        "![Original excerpt](excerpt-original.png)", "", "*Original excerpt · " + caption + "*", "",
        "![Underlined excerpt](excerpt-underlined.png)", "", "*Underlined excerpt · " + caption + "*", "",
        "### Bounded interpretation", "", review["summary"], "",
        f"**Scope:** {review['scope_assessment']}", "",
        f"**Applicability mismatch:** {review['applicability_mismatch']}", "",
        f"**Limitations:** {review['limitations_summary']}", "",
        f"**Contrary / non-significant findings:** {review['counterevidence_summary']}", "",
        "### Context anchors", "",
    ])
    for role, anchor in review["anchors"].items():
        lines.extend([f"#### {role}", ""])
        if anchor.get("quotes"):
            for item in anchor["quotes"]:
                lines.extend([blockquote(item["quote"]), "", location_caption(item), ""])
        else:
            lines.extend([f"All pages reviewed: {anchor.get('all_pages_reviewed')}",
                          anchor.get("search_notes", ""), ""])
    lines.extend([
        "### Validation boundary", "",
        f"Reviewer: {review['reviewer']['name']} ({review['reviewer']['kind']}).",
        f"Packet SHA-256: `{record['packet_sha256']}`.",
        "Status: `record_checks_passed`. Registry authenticity and scientific interpretation "
        "remain reviewer assessments; hashes are not proof of truth.", "",
        "---", "", "## 中文证据说明", "",
        f"**原文位置：** {caption}", f"**证据类别：** {review['support']}", "",
        f"**摘要初筛：** {review['abstract_screen']['decision']} / "
        f"{review['abstract_screen']['rationale']}", "",
        f"**最终原始来源：** {lineage['final_identifier']} / "
        f"{lineage['ownership']['kind']}；引用链共 {len(lineage['hops'])} 跳，"
        "逐跳原句、位置、原文 PDF 与红线图见上方及 lineage.json。", "",
        f"**对应用户论文/目的：** {target_record['title']} / "
        f"{target_loc['section_heading']} / {target_loc['unit']} {target_loc['unit_number']}", "",
        f"**用户原句：** {target_loc['quote']}", "",
        f"**对应具体事项：** {alignment['related_aspect']}", "",
        f"**关联理由：** {alignment['rationale']}", "",
        f"**可支持：** {alignment['supports']}", "",
        f"**不能支持：** {alignment['does_not_support']}", "",
        "**原文与截图：** 见上方未修改原图、红线图及完整位置图注。",
        "**解读边界：** 目的、方法、结果、限制与相反/不显著发现已逐项登记；"
        "记录检查通过不能等同于学术真实性已经自动验证。",
        f"**复核者：** {review['reviewer']['name']}（{review['reviewer']['kind']}）。", "",
    ])
    return "\n".join(lines)


def export(bundle):
    result, record, source, review = check(bundle)
    root = Path(bundle)
    target = root / "report.md"
    require(not target.exists(), "report.md exists; export to a fresh bundle or remove it deliberately")
    target.write_text(report_content(record, source, review, load_json(root / "target.json"),
                                     load_json(root / "lineage.json")),
                      encoding="utf-8")
    return {**result, "report": str(target)}


def pack(args):
    result, record, source, review = check(args.bundle)
    root = Path(args.bundle).absolute()
    target = Path(args.out).absolute()
    require(target.suffix.lower() == ".zip", "package output must end in .zip")
    require(not target.exists(), "ZIP output already exists")
    require(not target.is_relative_to(root), "ZIP output must be outside the source bundle")
    content = report_content(record, source, review, load_json(root / "target.json"),
                             load_json(root / "lineage.json"))
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".receipt-zip-", dir=target.parent) as temp:
        archive_path = Path(temp) / "bundle.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(set(record["files"]) | {"receipt.json", "review.json"}):
                archive.write(confined(root, name), f"{root.name}/{name}")
            archive.writestr(f"{root.name}/report.md", content)
        require(not target.exists(), "ZIP output appeared during packaging")
        archive_path.rename(target)
    return {**result, "archive": str(target), "archive_sha256": digest_file(target)}


def inspect(args):
    output = Path(args.out)
    require(not output.exists(), "inspect output already exists")
    with Paper(Path(args.pdf)) as paper:
        pages = []
        terms = ("not significant", "no significant", "limitation", "however",
                 "adverse", "inconsistent", "不显著", "无显著", "局限", "未发现")
        for i in range(1, paper.count + 1):
            content = paper.page_text(i)
            normalized_lower = normalized(content).lower()
            pages.append({
                "pdf_page": i, "text": content,
                "review_terms": [term for term in terms if normalized(term).lower() in normalized_lower],
            })
        write_json(output, {"pdf_sha256": digest_file(paper.path), "pages": pages})
    return {"status": "inspection_only", "output": str(output), "pages": len(pages)}


def inspect_target(args):
    output = Path(args.out)
    require(not output.exists(), "target inspection output already exists")
    document = Path(args.document)
    unit, units = target_units(document)
    write_json(output, {
        "document_sha256": digest_file(document), "unit": unit,
        "units": [{"number": i, "text": content} for i, content in enumerate(units, 1)],
    })
    return {"status": "target_inspection_only", "output": str(output), "units": len(units)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    retrieval = commands.add_parser("download", help="download a lawful public HTTPS text PDF")
    retrieval.add_argument("--url", required=True)
    retrieval.add_argument("--out", required=True)
    retrieval.add_argument("--expected-sha256")
    retrieval.add_argument("--timeout", type=int, default=30)
    inspection = commands.add_parser("inspect", help="dump page text for full-text review")
    inspection.add_argument("--pdf", required=True)
    inspection.add_argument("--out", required=True)
    target_inspection = commands.add_parser("inspect-target", help="number user manuscript paragraphs/lines")
    target_inspection.add_argument("--document", required=True)
    target_inspection.add_argument("--out", required=True)
    extraction = commands.add_parser("extract", help="create a source-gated draft receipt")
    extraction.add_argument("--pdf", required=True)
    extraction.add_argument("--source", required=True)
    extraction.add_argument("--target", required=True)
    extraction.add_argument("--lineage", required=True)
    extraction.add_argument("--quote-file", required=True)
    extraction.add_argument("--page", type=int, required=True)
    extraction.add_argument("--section-heading", required=True)
    extraction.add_argument("--heading-page", type=int, required=True)
    extraction.add_argument("--section-role", choices=ROLES, required=True)
    extraction.add_argument("--printed-page", required=True)
    extraction.add_argument("--paragraph", required=True)
    extraction.add_argument("--origin", choices=ORIGINS, required=True)
    extraction.add_argument("--occurrence", type=int)
    extraction.add_argument("--region", nargs=4, type=float)
    extraction.add_argument("--out", required=True)
    for command in ("check", "export"):
        commands.add_parser(command).add_argument("--bundle", required=True)
    packaging = commands.add_parser("pack", help="package validated evidence with original PDFs")
    packaging.add_argument("--bundle", required=True)
    packaging.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "download":
            result = download(args)
        elif args.command == "pack":
            result = pack(args)
        elif args.command == "inspect":
            result = inspect(args)
        elif args.command == "inspect-target":
            result = inspect_target(args)
        elif args.command == "extract":
            result = extract(args)
        elif args.command == "check":
            result = check(args.bundle)[0]
        else:
            result = export(args.bundle)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "rejected", "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
