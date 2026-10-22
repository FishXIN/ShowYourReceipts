# Packet format and commands

The distributable is one self-contained Agent Skill. There is no hosted service,
model dependency, publisher crawler, or hidden credential. The agent performs
search and semantic review; the bundled CLI performs local provenance checks.

## Source preparation

Copy `assets/source.template.json` outside the skill directory. Fill every factual
field using inspected sources. Resolve `index.snapshot` and `status.snapshot`
relative to that JSON file. Allowed snapshot formats are PDF, HTML, TXT, CSV and
JSON. Compute SHA-256 with a local hashing tool. Do not fabricate an official
registry record when authentication or historical coverage is unavailable.

`index.membership_quote` must occur literally in the saved record and contain
the matching ISSN. `index.collection_label` must also appear. The official host
must match the collection allowlist. For the publisher status check, the saved
record must contain the article DOI, or the title if no DOI exists.

Dates use `YYYY-MM-DD`. Membership and status checks expire after 90 days.
Article `identity` is a literal passage on the published PDF identifying its DOI
(or title when no DOI exists). Identity, collection eligibility and interpretation
are separate checks.

## Download

```bash
python scripts/receipts.py download --url "$PDF_URL" --out paper.pdf
```

Use only lawful published PDFs from publishers or authorized archives. The helper
checks HTTPS, public IPs at each redirect, bounded size/time, PDF content and
supported page geometry. It pins the resolved public address while verifying TLS
against the original hostname. It does not log in or bypass a paywall.
`paper.pdf.download.json` records requested/final URLs, date and PDF SHA-256.
This is a downloaded candidate, not core-eligible evidence until the source gate
passes. Importing a lawfully supplied PDF is also supported.

## User target

Prepare `target.json` from its template. Bind the user's original DOCX, TXT or
Markdown document by hash, specific section and paragraph/line. The alignment
review explains the related variable, scale, hypothesis or experiment step,
the reason for relevance, and what cannot be inferred.

## Inspect

```bash
python scripts/receipts.py inspect --pdf paper.pdf --out paper-text.json
```

Outputs page text and potential counterevidence terms. They are search aids, not
an exhaustive linguistic or statistical review. Inspection refuses image-only
PDFs and unsupported page geometry; OCR is deliberately not silent.

## Extract

```bash
python scripts/receipts.py extract \
  --pdf paper.pdf --source source.json --target target.json --page 5 --quote-file quote.txt \
  --section-heading "Results" --heading-page 4 --section-role results \
  --printed-page "3105" --paragraph "paragraph 2, right column" \
  --origin author_finding --out receipt-001
```

One contiguous passage on one PDF page is supported per packet. Split cross-page
passages into separate, explicitly linked receipts. Repeated passages require
`--occurrence 1` (one-based match); never silently choose the first occurrence.
`--region x0 top x1 bottom` narrows matching to a column in PDF points.
Keep that selection visible in the recorded metadata.

Matching is case-sensitive. The only normalization is Unicode NFKC, whitespace,
soft-hyphens and line-end hyphenation. The original extracted text is always saved.
Ellipses and changes to negation are not normalized away.

Version 0.1 rejects rotated pages, non-zero MediaBox origins, differing CropBoxes,
encrypted PDFs, oversized files/pages and scanned PDFs. This avoids silently
misaligned underlines. Correctly exported text PDFs are the supported input.

## Packet contents

```text
receipt-001/
├── receipt.json
├── source.json
├── source.pdf
├── target.json
├── target-document.*
├── download.json           # when retrieved by the download command
├── index-record.*
├── publisher-record.*
├── context.txt
├── page-original.png
├── page-underlined.png
├── excerpt-original.png
├── excerpt-underlined.png
└── review.json             # supplied by the reviewer after extraction
```

All artifact paths are relative and confined to the packet directory. Symlinks,
absolute paths, path traversal and overwriting an existing packet are rejected.
Draft extraction writes through a staging directory and then renames it.

`receipt.json` contains schema version, draft state, source identity, quote,
normalization rule, page/section/paragraph/origin location, glyph rectangles,
rendering settings, crop coordinates, artifact hashes, and `packet_sha256`.
The digest binds the packet manifest; the hashes detect changed source/artifacts.
They do not prove that an artifact was authentic before hashing.

## Review and check

Copy `assets/review.template.json` to `receipt-001/review.json`. Fill the generated
packet digest, scope/summary/translation, reviewer and exact context anchors.
Empty templates fail. `check` recomputes source eligibility, quote matching,
heading location, rectangles, rendering and artifact hashes, then validates
the review binding and anchor locations:

```bash
python scripts/receipts.py check --bundle receipt-001
```

Review anchors for purpose, methods and results are required. Limitations and
counterevidence may contain matched passages or an explicit all-page review
record with search notes.

## Export and package

```bash
python scripts/receipts.py export --bundle receipt-001
python scripts/receipts.py pack --bundle receipt-001 --out evidence-001.zip
```

Creates `report.md` only after `check` passes. Export shows English first and
Chinese labels afterwards, with original/underlined images and location captions.
The underlying packet remains a draft artifact; export is marked
`record_checks_passed`, not “scientifically verified”. Never bypass `check` using
manually generated final screenshots.

`pack` reruns all checks and generates a fresh summary from the validated records.
The ZIP contains the complete original `source.pdf`, original/annotated images,
the user's source document, target mapping, source/review records and `report.md`.
It does not pick up arbitrary extra files in the packet directory. A local packet
contains private or copyrighted source documents; share only as authorized.

All command results are JSON on stdout. Validation errors return exit code `2`.
Only `download` uses the network; the other commands operate on local inputs.
There is no arbitrary command execution or implicit remote fetching.
Run PDF parsing with OS/container isolation for untrusted files.

---

## 中文说明

复制模板到研究任务目录，填入真实核验信息。保存官方收录与出版社状态
记录，计算哈希。源记录须包含匹配 ISSN、收录集标识、覆盖年份和复核者；
核验超过 90 天需要更新。脚本不负责登录、爬取或绕过访问限制。

单个证据包支持单页连续原句。重复原句要指定出现序号，多栏可指定区域；
跨页原文拆成多个关联证据包。原图、红线图、上下文、章节定位和哈希同时
保存。只做 Unicode、空白和断行连字符规范化，不容许改写。
另填用户论文/目的的原句、章节与段落/行号，说明具体相关事项。

填写绑定证据包哈希的复核记录后执行检查，检查通过才能导出双语 Markdown。
检查通过代表记录和文件一致，不能写成学术真伪已经自动验证。扫描、旋转、
裁切异常或加密 PDF 会拒绝处理，不能静默用 OCR 猜测原句。
`download` 获取合法完整 PDF 并记录链接、日期和哈希；下载文件仍需通过
核心来源核验。`pack` 将原文 PDF、图片、用户论文映射、复核记录和总结
一起打包，默认仅用于本地私密研究，不会自动公开上传。
