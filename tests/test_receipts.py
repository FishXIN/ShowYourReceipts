"""Adversarial receipt tests. Fixtures are synthetic and never scientific evidence."""

import argparse
import contextlib
import copy
import importlib.util
import io
import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/show-your-receipts/scripts/receipts.py"
SPEC = importlib.util.spec_from_file_location("receipts", SCRIPT)
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def pdf_fixture(path, repeated=False, rotated=False, identifier="10.1234/fixture",
                extra_lines=None, include_abstract=True):
    """Generate a tiny PDF with actual text glyphs using only the standard library."""
    lines = [
        "TEST ONLY - NOT A REAL JOURNAL PAPER",
        "Test paper DOI " + identifier,
        "Abstract",
        "We tested tactile feedback and accuracy in a synthetic task.",
        "Introduction",
        "We examined tactile feedback during a task.",
        "Methods",
        "Twelve synthetic participants completed two conditions.",
        "Results",
        "Feedback did not significantly improve accuracy.",
        "Pleasantness increased for this test device.",
        "Limitations",
        "The synthetic sample does not support generalization.",
    ]
    if repeated:
        lines.append("Feedback did not significantly improve accuracy.")
    if not include_abstract:
        del lines[2:4]
    lines.extend(extra_lines or [])
    stream = b"BT /F1 12 Tf 50 740 Td 22 TL\n"
    for i, line in enumerate(lines):
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream += (("" if i == 0 else "T* ") + f"({escaped}) Tj\n").encode("ascii")
    stream += b"ET"
    rotation = b" /Rotate 90" if rotated else b""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]" + rotation +
        b" /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n"
    for offset in offsets[1:]:
        data += f"{offset:010} 00000 n \n".encode()
    data += f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(data)


def anchor(quote, heading, role, origin="author_finding"):
    return {
        "page": 1, "printed_page": "unpaginated", "quote": quote,
        "section_heading": heading, "heading_page": 1, "section_role": role,
        "paragraph": "paragraph 1", "origin": origin,
    }


def abstract_screen():
    return {
        "status": "present", "decision": "target_mentioned",
        "rationale": "The synthetic abstract mentions the test outcome.",
        "quotes": [anchor("We tested tactile feedback and accuracy in a synthetic task.",
                          "Abstract", "abstract")],
    }


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="syr-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pdf = self.root / "paper.pdf"
        pdf_fixture(self.pdf)
        self.index = self.root / "index.txt"
        self.index.write_text("TEST ONLY registry fixture\nSCIE\nTest Journal 1234-5679", encoding="utf-8")
        self.publisher = self.root / "publisher.txt"
        self.publisher.write_text("TEST ONLY publisher fixture\n10.1234/fixture", encoding="utf-8")
        self.person = {"kind": "agent", "name": "synthetic-test-reviewer"}
        today = date.today().isoformat()
        self.source = {
            "schema_version": 1,
            "article": {
                "title": "Test paper", "journal": "Test Journal",
                "doi": "10.1234/fixture", "url": "https://example.org/test-only",
                "issn": "1234-5679", "year": date.today().year,
                "kind": "original_research", "version": "published",
                "identity": {"page": 1, "quote": "Test paper DOI 10.1234/fixture"},
            },
            "index": {
                "system": "SCIE", "edition": "TEST ONLY",
                "coverage_start_year": date.today().year,
                "coverage_end_year": date.today().year,
                "official_url": "https://mjl.clarivate.com/test-only-fixture",
                "collection_label": "SCIE", "membership_quote": "Test Journal 1234-5679",
                "snapshot": "index.txt", "snapshot_sha256": r.digest_file(self.index),
                "checked_at": today, "reviewer": self.person,
            },
            "status": {
                "assessment": "clear", "publisher_url": "https://example.org/test-only",
                "snapshot": "publisher.txt", "snapshot_sha256": r.digest_file(self.publisher),
                "checked_at": today, "reviewer": self.person,
                "correction_url": "", "correction_note": "",
            },
        }
        self.source_path = self.root / "source.json"
        r.write_json(self.source_path, self.source)
        self.quote = "Feedback did not significantly improve accuracy."
        self.quote_path = self.root / "quote.txt"
        self.quote_path.write_text(self.quote, encoding="utf-8")
        self.bundle = self.root / "receipt"
        self.manuscript = self.root / "user.txt"
        self.manuscript.write_text("3. Experiment\nWe test whether feedback improves accuracy.\n",
                                   encoding="utf-8")
        self.target = {
            "schema_version": 1, "kind": "research_objective", "title": "TEST ONLY objective",
            "document": "user.txt", "document_sha256": r.digest_file(self.manuscript),
            "research_question": "Does feedback improve accuracy?", "intended_use": "interpretation",
            "location": {
                "section_heading": "3. Experiment", "heading_unit": 1,
                "unit": "line", "unit_number": 2,
                "quote": "We test whether feedback improves accuracy.",
            },
        }
        self.target_path = self.root / "target.json"
        r.write_json(self.target_path, self.target)
        self.lineage = {
            "schema_version": 1, "resolution": "original_source_resolved",
            "reviewed_at": today, "reviewer": self.person,
            "initial_identifier": "10.1234/fixture", "final_identifier": "10.1234/fixture",
            "hops": [],
            "ownership": {
                "kind": "own_data", "rationale": "Only a synthetic ownership test.",
                "context_cues": [anchor("Pleasantness increased for this test device.",
                                        "Results", "results")],
            },
        }
        self.lineage_path = self.root / "lineage.json"
        r.write_json(self.lineage_path, self.lineage)

    def args(self, **changes):
        opts = {
            "pdf": str(self.pdf), "source": str(self.source_path),
            "target": str(self.target_path),
            "lineage": str(self.lineage_path),
            "quote_file": str(self.quote_path), "page": 1,
            "section_heading": "Results", "heading_page": 1, "section_role": "results",
            "printed_page": "unpaginated", "paragraph": "paragraph 1", "origin": "author_finding",
            "occurrence": None, "region": None, "out": str(self.bundle),
        }
        opts.update(changes)
        return argparse.Namespace(**opts)

    def extraction(self, **changes):
        return r.extract(self.args(**changes))

    def complete_review(self):
        receipt = r.load_json(self.bundle / "receipt.json")
        record = {
            "schema_version": 1, "packet_sha256": receipt["packet_sha256"],
            "reviewed_at": date.today().isoformat(), "reviewer": self.person,
            "claim": "Accuracy benefit is not established in this synthetic fixture.",
            "support": "contradiction", "summary": "The fixture states a non-significant result.",
            "translation": "合成测试文档：反馈未显著改善正确率。",
            "scope_assessment": "Synthetic fixture only.",
            "applicability_mismatch": "Not a real experiment.",
            "limitations_summary": "Synthetic sample.",
            "counterevidence_summary": "No significant accuracy improvement.",
            "abstract_screen": abstract_screen(),
            "target_alignment": {
                "target_quote": self.target["location"]["quote"], "intended_use": "interpretation",
                "related_aspect": "accuracy outcome", "rationale": "The same outcome is discussed.",
                "supports": "Treat accuracy benefit as unestablished in this fixture.",
                "does_not_support": "No general efficacy inference.",
            },
            "anchors": {
                "purpose": {"quotes": [anchor("We examined tactile feedback during a task.",
                                             "Introduction", "introduction")]},
                "methods": {"quotes": [anchor("Twelve synthetic participants completed two conditions.",
                                             "Methods", "methods")]},
                "results": {"quotes": [anchor(self.quote, "Results", "results")]},
                "limitations": {"quotes": [anchor(
                    "The synthetic sample does not support generalization.", "Limitations", "limitations")]},
                "counterevidence": {"quotes": [anchor(self.quote, "Results", "results")]},
            },
        }
        r.write_json(self.bundle / "review.json", record)
        return record

    def mutate_source(self, section, field, value):
        data = copy.deepcopy(self.source)
        data[section][field] = value
        r.write_json(self.source_path, data)

    def test_extract_check_export_roundtrip_and_locations(self):
        self.extraction()
        self.complete_review()
        result = r.export(str(self.bundle))
        self.assertEqual(result["status"], "record_checks_passed")
        report = (self.bundle / "report.md").read_text(encoding="utf-8")
        self.assertIn("Results (results; heading on PDF p. 1)", report)
        self.assertIn("origin: author_finding", report)
        self.assertIn("did not significantly", report)
        self.assertIn("page-original.png", report)
        self.assertIn("User location:** 3. Experiment | line 2", report)
        self.assertIn("We test whether feedback improves accuracy.", report)
        self.assertIn("original_source_resolved", report)
        self.assertIn("Abstract decision", report)
        self.assertLess(report.index("## Evidence receipt"), report.index("## 中文"))
        self.assertEqual(result["report"], str(self.bundle / "report.docx"))
        self.assertTrue((self.bundle / "report.docx").is_file())

    def test_unreviewed_draft_cannot_export(self):
        self.extraction()
        with self.assertRaises(r.Rejected):
            r.export(str(self.bundle))
        self.assertFalse((self.bundle / "report.md").exists())

    def test_fabricated_quote_and_removed_negation_rejected(self):
        self.quote_path.write_text("Feedback significantly improved accuracy.")
        with self.assertRaises(r.Rejected):
            self.extraction()
        self.assertFalse(self.bundle.exists())

    def test_ordinary_and_esci_sources_rejected(self):
        for system in ("ESCI", "EI", "conference", ""):
            self.mutate_source("index", "system", system)
            with self.assertRaises(r.Rejected):
                self.extraction()

    def test_unofficial_lookalike_host_rejected(self):
        self.mutate_source("index", "official_url", "https://mjl.clarivate.com.evil.example/record")
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_wrong_year_and_future_verification_rejected(self):
        self.mutate_source("article", "year", date.today().year - 1)
        with self.assertRaises(r.Rejected):
            self.extraction()
        r.write_json(self.source_path, self.source)
        self.mutate_source("index", "checked_at", "2999-01-01")
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_retracted_and_concerning_papers_rejected(self):
        for state in ("retracted", "expression_of_concern", "unchecked"):
            self.mutate_source("status", "assessment", state)
            with self.assertRaises(r.Rejected):
                self.extraction()

    def test_conference_article_rejected(self):
        self.mutate_source("article", "kind", "conference")
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_membership_and_identity_must_match_saved_sources(self):
        self.mutate_source("index", "membership_quote", "Different Journal 1234-5679")
        with self.assertRaises(r.Rejected):
            self.extraction()
        r.write_json(self.source_path, self.source)
        self.mutate_source("article", "doi", "10.1234/not-this-paper")
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_ambiguous_quote_requires_occurrence(self):
        pdf_fixture(self.pdf, repeated=True)
        with self.assertRaises(r.Rejected):
            self.extraction()
        self.extraction(occurrence=2)
        record = r.load_json(self.bundle / "receipt.json")
        self.assertEqual(record["match_count"], 2)
        self.assertEqual(record["occurrence"], 2)

    def test_wrong_heading_missing_location_and_rotated_pdf_rejected(self):
        with self.assertRaises(r.Rejected):
            self.extraction(section_heading="Nonexistent heading")
        with self.assertRaises(r.Rejected):
            self.extraction(paragraph="")
        pdf_fixture(self.pdf, rotated=True)
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_tampered_image_and_manifest_rejected(self):
        self.extraction()
        self.complete_review()
        image = self.bundle / "page-underlined.png"
        image.write_bytes(image.read_bytes() + b"tampered")
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_changed_artifact_with_updated_hash_still_rejected(self):
        self.extraction()
        record = r.load_json(self.bundle / "receipt.json")
        image = self.bundle / "page-underlined.png"
        image.write_bytes(b"forged image")
        record["files"][image.name] = r.digest_file(image)
        record["packet_sha256"] = r.packet_digest(record)
        r.write_json(self.bundle / "receipt.json", record)
        self.complete_review()
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_changed_manifest_and_review_binding_rejected(self):
        self.extraction()
        review = self.complete_review()
        review["packet_sha256"] = "0" * 64
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_cited_prior_work_cannot_be_direct(self):
        self.extraction(origin="cited_prior_work", section_role="literature_review")
        review = self.complete_review()
        review["support"] = "direct"
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def trace_hop(self, name, cited_identifier):
        identifier = "10.1234/" + name
        pdf = self.root / (name + ".pdf")
        passage = "Prior work [1] reported an accuracy result."
        reference = "1. Test paper. DOI " + cited_identifier
        pdf_fixture(pdf, identifier=identifier, extra_lines=[
            "Discussion", passage, "References", reference,
        ])
        source = copy.deepcopy(self.source)
        source["article"]["doi"] = identifier
        source["article"]["kind"] = "review"
        source["article"]["identity"]["quote"] = "Test paper DOI " + identifier
        publisher = self.root / (name + "-publisher.txt")
        publisher.write_text("TEST ONLY publisher fixture\n" + identifier, encoding="utf-8")
        source["status"]["snapshot"] = publisher.name
        source["status"]["snapshot_sha256"] = r.digest_file(publisher)
        source_path = self.root / (name + "-source.json")
        r.write_json(source_path, source)
        return {
            "identifier": identifier, "cited_identifier": cited_identifier,
            "pdf": pdf.name, "pdf_sha256": r.digest_file(pdf), "source": source_path.name,
            "citation_marker": "[1]", "reference_marker": "1.",
            "link_rationale": "Synthetic numbered citation links to entry 1.",
            "abstract_screen": abstract_screen(),
            "passage": anchor(passage, "Discussion", "discussion", "cited_prior_work"),
            "reference": anchor(reference, "References", "references", "cited_prior_work"),
        }

    def two_hops(self):
        self.lineage["initial_identifier"] = "10.1234/lead"
        self.lineage["hops"] = [
            self.trace_hop("lead", "10.1234/middle"),
            self.trace_hop("middle", "10.1234/fixture"),
        ]
        r.write_json(self.lineage_path, self.lineage)

    def test_recursive_trace_exports_and_packages_each_original_pdf_and_citation(self):
        self.two_hops()
        self.extraction()
        self.complete_review()
        output = self.root / "traced.zip"
        r.pack(argparse.Namespace(bundle=str(self.bundle), out=str(output)))
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.read("receipt/trace-001-source.pdf"),
                             (self.root / "lead.pdf").read_bytes())
            self.assertEqual(archive.read("receipt/trace-002-source.pdf"),
                             (self.root / "middle.pdf").read_bytes())
            self.assertIn("receipt/lineage.json", archive.namelist())
            self.assertIn("receipt/trace-002-reference-page-underlined.png", archive.namelist())
            report = archive.read("receipt/report.md").decode("utf-8")
            self.assertIn("Citation hop 2", report)
            self.assertIn("Discussion (discussion", report)

    def test_missing_and_unresolved_lineage_rejected(self):
        with self.assertRaises(r.Rejected):
            self.extraction(lineage=str(self.root / "missing.json"))
        self.lineage["resolution"] = "unresolved"
        r.write_json(self.lineage_path, self.lineage)
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_broken_chain_wrong_endpoint_and_cycles_rejected(self):
        self.two_hops()
        base = copy.deepcopy(self.lineage)
        for mutate in (
            lambda x: x.update(final_identifier="10.1234/other"),
            lambda x: x["hops"][0].update(cited_identifier="10.1234/other"),
            lambda x: x["hops"][1].update(identifier="10.1234/lead"),
        ):
            changed = copy.deepcopy(base)
            mutate(changed)
            r.write_json(self.lineage_path, changed)
            with self.assertRaises(r.Rejected):
                self.extraction()

    def test_trace_citation_marker_and_fabricated_reference_rejected(self):
        self.two_hops()
        base = copy.deepcopy(self.lineage)
        for field, value in (("citation_marker", "[99]"), ("reference_marker", "99.")):
            changed = copy.deepcopy(base)
            changed["hops"][0][field] = value
            r.write_json(self.lineage_path, changed)
            with self.assertRaises(r.Rejected):
                self.extraction()
        changed = copy.deepcopy(base)
        changed["hops"][0]["reference"]["quote"] = "1. A fabricated paper. DOI 10.1234/middle"
        r.write_json(self.lineage_path, changed)
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_reference_doi_prefix_is_not_the_next_paper(self):
        hop = self.trace_hop("lead", "10.1234/fixture-extra")
        hop["cited_identifier"] = "10.1234/fixture"
        self.lineage.update(initial_identifier="10.1234/lead", hops=[hop])
        r.write_json(self.lineage_path, self.lineage)
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_wrapped_reference_dois_preserve_exact_identifier_boundaries(self):
        self.assertTrue(r.reference_identifies("10.1016/j.jesp.2006.05.003",
                                              "doi: 10.\n1016/j.jesp.2006.05.003"))
        self.assertTrue(r.reference_identifies("10.1234/FIXTURE", "doi: 10.1234/fixture."))
        self.assertFalse(r.reference_identifies("10.1234/fixture", "doi: 10.1234/fixture-extra"))
        self.assertFalse(r.reference_identifies("10.1234/fixture", "doi: 10.1234/fixture2"))

    def test_trace_hop_must_pass_source_gate_and_pdf_hash(self):
        self.two_hops()
        lead = self.root / "lead-source.json"
        source = r.load_json(lead)
        source["index"]["system"] = "ESCI"
        r.write_json(lead, source)
        with self.assertRaises(r.Rejected):
            self.extraction()
        self.two_hops()
        self.lineage["hops"][0]["pdf_sha256"] = "0" * 64
        r.write_json(self.lineage_path, self.lineage)
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_rehashed_trace_image_is_still_checked_against_its_pdf(self):
        self.two_hops()
        self.extraction()
        record = r.load_json(self.bundle / "receipt.json")
        image = self.bundle / "trace-001-passage-page-underlined.png"
        image.write_bytes(b"forged trace image")
        record["files"][image.name] = r.digest_file(image)
        record["packet_sha256"] = r.packet_digest(record)
        r.write_json(self.bundle / "receipt.json", record)
        self.complete_review()
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_cited_claim_and_hypothesis_cannot_export_in_any_support_category(self):
        self.extraction(origin="cited_prior_work", section_role="discussion", section_heading="Results")
        review = self.complete_review()
        for support in r.SUPPORT:
            review["support"] = support
            r.write_json(self.bundle / "review.json", review)
            with self.assertRaises(r.Rejected):
                r.check(self.bundle)
        record = r.load_json(self.bundle / "receipt.json")
        record["location"]["origin"] = "hypothesis"
        record["packet_sha256"] = r.packet_digest(record)
        r.write_json(self.bundle / "receipt.json", record)
        self.complete_review()
        with self.assertRaises(r.Rejected):
            r.export(self.bundle)

    def test_missing_abstract_and_fabricated_abstract_screen_rejected(self):
        self.extraction()
        review = self.complete_review()
        base = copy.deepcopy(review)
        del review["abstract_screen"]
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)
        base["abstract_screen"]["quotes"][0]["quote"] = "We proved an accuracy benefit."
        r.write_json(self.bundle / "review.json", base)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_abstract_no_match_requires_full_text_review(self):
        self.extraction()
        review = self.complete_review()
        screen = review["abstract_screen"]
        screen["decision"] = "not_mentioned_full_text_review"
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)
        screen.update(all_pages_reviewed=[1], search_notes="TEST ONLY full-text review rationale.")
        r.write_json(self.bundle / "review.json", review)
        self.assertEqual(r.check(self.bundle)[0]["status"], "record_checks_passed")

    def test_absent_abstract_requires_full_text_record(self):
        pdf_fixture(self.pdf, include_abstract=False)
        self.extraction()
        review = self.complete_review()
        review["abstract_screen"] = {
            "status": "absent", "decision": "no_abstract_full_text_review", "quotes": [],
            "rationale": "TEST ONLY fixture has no abstract.",
        }
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)
        review["abstract_screen"].update(all_pages_reviewed=[1], search_notes="All pages inspected.")
        r.write_json(self.bundle / "review.json", review)
        self.assertEqual(r.check(self.bundle)[0]["status"], "record_checks_passed")

    def test_ownership_cannot_be_cited_or_a_hypothesis(self):
        for kind in ("cited_prior_work", "hypothesis", ""):
            self.lineage["ownership"]["kind"] = kind
            r.write_json(self.lineage_path, self.lineage)
            with self.assertRaises(r.Rejected):
                self.extraction()
        self.lineage["ownership"]["kind"] = "own_data"
        self.lineage["ownership"]["context_cues"][0]["origin"] = "cited_prior_work"
        r.write_json(self.lineage_path, self.lineage)
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_own_method_may_have_background_citations_without_being_direct_data(self):
        method = "We implemented our new synthetic method, unlike prior work [1]."
        pdf_fixture(self.pdf, extra_lines=["Methods", method])
        self.quote_path.write_text(method, encoding="utf-8")
        self.lineage["ownership"] = {
            "kind": "own_method", "rationale": "An implemented test method with a background citation.",
            "context_cues": [anchor(method, "Methods", "methods", "method_description")],
        }
        r.write_json(self.lineage_path, self.lineage)
        self.extraction(origin="method_description", section_role="methods", section_heading="Methods")
        review = self.complete_review()
        review["support"] = "method_precedent"
        review["anchors"]["results"]["quotes"][0]["quote"] = (
            "Feedback did not significantly improve accuracy.")
        review["anchors"]["counterevidence"]["quotes"][0]["quote"] = (
            "Feedback did not significantly improve accuracy.")
        r.write_json(self.bundle / "review.json", review)
        self.assertEqual(r.check(self.bundle)[0]["status"], "record_checks_passed")
        review["support"] = "direct"
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_fake_review_anchor_rejected(self):
        self.extraction()
        review = self.complete_review()
        review["anchors"]["methods"]["quotes"][0]["quote"] = "A randomized clinical trial was completed."
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_absence_assertion_requires_all_pages(self):
        self.extraction()
        review = self.complete_review()
        review["anchors"]["counterevidence"] = {
            "quotes": [], "all_pages_reviewed": [], "search_notes": "Looked for null outcomes.",
        }
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_snapshot_symlink_and_path_traversal_rejected(self):
        symlink = self.root / "link.txt"
        symlink.symlink_to(self.index)
        for path in ("link.txt", "../outside.txt"):
            self.mutate_source("index", "snapshot", path)
            with self.assertRaises(r.Rejected):
                self.extraction()

    def test_no_overwrite_and_machine_readable_failure(self):
        self.extraction()
        with self.assertRaises(r.Rejected):
            self.extraction()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = r.main(["check", "--bundle", str(self.root / "missing")])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(output.getvalue())["status"], "rejected")

    def test_inspect_and_normalization(self):
        out = self.root / "inspect.json"
        r.inspect(argparse.Namespace(pdf=str(self.pdf), out=str(out)))
        self.assertIn("not significant", r.load_json(out)["pages"][0]["review_terms"])
        self.assertEqual(r.normalized("affec-\ntive \ufb01nding"), "affectivefinding")

    def test_missing_target_and_fabricated_user_passage_rejected(self):
        with self.assertRaises(r.Rejected):
            self.extraction(target=str(self.root / "missing.json"))
        self.target["location"]["quote"] = "We already proved clinical effectiveness."
        r.write_json(self.target_path, self.target)
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_missing_or_misbound_target_alignment_rejected(self):
        self.extraction()
        review = self.complete_review()
        review["target_alignment"]["target_quote"] = "Another user's objective."
        r.write_json(self.bundle / "review.json", review)
        with self.assertRaises(r.Rejected):
            r.check(self.bundle)

    def test_changed_user_manuscript_rejected(self):
        self.manuscript.write_text("changed")
        with self.assertRaises(r.Rejected):
            self.extraction()

    def test_docx_target_paragraph_location(self):
        docx = self.root / "user.docx"
        with zipfile.ZipFile(docx, "w") as archive:
            archive.writestr("word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body><w:p><w:r><w:t>3. Experiment</w:t></w:r></w:p>'
                '<w:p><w:r><w:t>We test whether feedback improves accuracy.</w:t></w:r></w:p>'
                '</w:body></w:document>')
        output = self.root / "target-text.json"
        r.inspect_target(argparse.Namespace(document=str(docx), out=str(output)))
        self.assertEqual(r.load_json(output)["units"][1]["number"], 2)
        self.target["document"] = docx.name
        self.target["document_sha256"] = r.digest_file(docx)
        self.target["location"]["unit"] = "paragraph"
        r.write_json(self.target_path, self.target)
        self.extraction()
        self.complete_review()
        self.assertEqual(r.check(self.bundle)[0]["status"], "record_checks_passed")

    def test_pack_contains_original_pdf_review_mapping_and_summary(self):
        self.extraction()
        self.complete_review()
        destination = self.root / "evidence.zip"
        r.pack(argparse.Namespace(bundle=str(self.bundle), out=str(destination)))
        with zipfile.ZipFile(destination) as archive:
            self.assertEqual(archive.read("receipt/source.pdf"), self.pdf.read_bytes())
            self.assertIn("receipt/target.json", archive.namelist())
            self.assertIn("receipt/report.md", archive.namelist())
            self.assertIn("receipt/report.docx", archive.namelist())
            self.assertIn(b"did not significantly", archive.read("receipt/report.md"))

    def test_unreviewed_packet_cannot_be_packaged(self):
        self.extraction()
        with self.assertRaises(r.Rejected):
            r.pack(argparse.Namespace(bundle=str(self.bundle), out=str(self.root / "bad.zip")))

    def test_fixed_word_delivery_contains_quotes_links_images_and_no_decoration(self):
        self.extraction()
        self.complete_review()
        output = self.root / "final.docx"
        result = r.deliver(argparse.Namespace(bundles=[str(self.bundle)], out=str(output)))
        self.assertEqual(result["evidence_count"], 1)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        with zipfile.ZipFile(output) as archive:
            document = ElementTree.fromstring(archive.read("word/document.xml"))
            content = "".join(t.text or "" for t in document.findall(".//w:t", ns))
            self.assertIn("论文原文、中文对照与红线截图", content)
            self.assertIn(self.quote, content)
            self.assertIn(self.target["location"]["quote"], content)
            self.assertIn("合成测试文档", content)
            self.assertIn("原文位置与归属", content)
            self.assertEqual(len(document.findall(".//w:sectPr", ns)), 1)
            self.assertEqual(len(document.findall(".//w:drawing", ns)), 2)
            self.assertFalse(document.findall(".//w:instrText", ns))
            self.assertFalse(any("header" in name or "footer" in name for name in archive.namelist()))
            rels = ElementTree.fromstring(archive.read("word/_rels/document.xml.rels"))
            targets = [rel.attrib.get("Target") for rel in rels]
            self.assertIn("https://doi.org/10.1234/fixture", targets)
            images = [archive.read(name) for name in archive.namelist() if name.startswith("word/media/")]
            self.assertIn((self.bundle / "excerpt-original.png").read_bytes(), images)
            self.assertIn((self.bundle / "excerpt-underlined.png").read_bytes(), images)
        with zipfile.ZipFile(output.with_suffix(".zip")) as archive:
            self.assertEqual(archive.read("final.docx"), output.read_bytes())
            self.assertEqual(archive.read("evidence-001/source.pdf"), self.pdf.read_bytes())

    def test_one_word_combines_all_receipts_in_order_and_all_source_pdfs(self):
        self.extraction()
        self.complete_review()
        second = self.root / "second"
        self.extraction(out=str(second))
        review = r.load_json(self.bundle / "review.json")
        review["packet_sha256"] = r.load_json(second / "receipt.json")["packet_sha256"]
        review["claim"] = "Second synthetic claim."
        r.write_json(second / "review.json", review)
        output = self.root / "combined.docx"
        result = r.deliver(argparse.Namespace(bundles=[str(self.bundle), str(second)], out=str(output)))
        self.assertEqual(result["evidence_count"], 2)
        with zipfile.ZipFile(output) as archive:
            text = archive.read("word/document.xml").decode("utf-8")
            self.assertLess(text.index("证据 1"), text.index("证据 2"))
            self.assertIn("Second synthetic claim.", text)
        with zipfile.ZipFile(output.with_suffix(".zip")) as archive:
            self.assertIn("evidence-001/source.pdf", archive.namelist())
            self.assertIn("evidence-002/source.pdf", archive.namelist())

    def test_word_delivery_rejects_unreviewed_wrong_format_and_existing_outputs(self):
        self.extraction()
        output = self.root / "final.docx"
        with self.assertRaises(r.Rejected):
            r.deliver(argparse.Namespace(bundles=[str(self.bundle)], out=str(output)))
        self.assertFalse(output.exists())
        self.complete_review()
        with self.assertRaises(r.Rejected):
            r.deliver(argparse.Namespace(bundles=[str(self.bundle)], out=str(self.root / "final.html")))
        output.with_suffix(".zip").write_bytes(b"existing")
        with self.assertRaises(r.Rejected):
            r.deliver(argparse.Namespace(bundles=[str(self.bundle)], out=str(output)))
        self.assertFalse(output.exists())

    def test_failed_word_generation_leaves_no_final_outputs(self):
        self.extraction()
        self.complete_review()
        output = self.root / "final.docx"
        with mock.patch.object(r, "render_word", side_effect=r.Rejected("renderer unavailable")):
            with self.assertRaises(r.Rejected):
                r.deliver(argparse.Namespace(bundles=[str(self.bundle)], out=str(output)))
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix(".zip").exists())

    def test_download_rejects_local_private_addresses_and_bad_schemes(self):
        with mock.patch.object(r.socket, "getaddrinfo", return_value=[
                (2, 1, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaises(r.Rejected):
                r.public_address("publisher.example")
        with self.assertRaises(r.Rejected):
            r.download(argparse.Namespace(
                url="http://example.org/paper.pdf", out=str(self.root / "bad.pdf"),
                timeout=5, expected_sha256=None))

    def test_download_records_original_pdf_and_provenance(self):
        response = mock.MagicMock()
        response.status = 200
        response.getheader.side_effect = lambda key, default=None: (
            "application/pdf" if key == "Content-Type" else default)
        response.read.side_effect = [self.pdf.read_bytes(), b""]
        connection = mock.MagicMock()
        connection.getresponse.return_value = response
        destination = self.root / "downloaded.pdf"
        with mock.patch.object(r, "PinnedHTTPS", return_value=connection):
            result = r.download(argparse.Namespace(
                url="https://publisher.example/paper.pdf", out=str(destination),
                timeout=10, expected_sha256=r.digest_file(self.pdf)))
        self.assertEqual(destination.read_bytes(), self.pdf.read_bytes())
        self.assertEqual(result["status"], "downloaded_candidate")
        self.assertTrue(Path(str(destination) + ".download.json").is_file())
        self.extraction(pdf=str(destination))
        self.assertIn("download.json", r.load_json(self.bundle / "receipt.json")["files"])

    def test_collection_label_and_unpublished_version_rejected(self):
        self.mutate_source("index", "collection_label", "ESCI")
        with self.assertRaises(r.Rejected):
            self.extraction()
        r.write_json(self.source_path, self.source)
        self.mutate_source("article", "version", "preprint")
        with self.assertRaises(r.Rejected):
            self.extraction()


if __name__ == "__main__":
    unittest.main()
