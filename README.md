# ShowYourReceipts

**No receipts, no claims.**

[![CI](https://github.com/FishXIN/ShowYourReceipts/actions/workflows/ci.yml/badge.svg)](https://github.com/FishXIN/ShowYourReceipts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-green.svg)](skills/show-your-receipts/SKILL.md)

Make your research agent show the paper before it makes the claim.

ShowYourReceipts is **one installable Agent Skill**, with local Python helpers.
It turns eligible journal passages into original screenshots, red underlines,
section-aware citations, context reviews and traceable summaries. It ships no
research papers, private data, model API or hosted service.

**English first · [中文说明](#中文说明)**

## What a receipt contains

- A source record for **SCIE, SSCI, AHCI, CSSCI, CSCD or PKU core journals**,
  verified against an official listing covering the publication year.
- A literal original passage, separately labeled translation and original PDF.
- Original and underlined full-page images, plus readable excerpts.
- **Exact location:** PDF page, printed page, actual section heading,
  section role, paragraph/table/figure position and claim origin.
- Purpose, methods, results, limitations and contrary/non-significant findings.
- The user's literal manuscript/objective passage and location, the specific
  variable/scale/step it relates to, and what it does and does not support.
- A bounded summary labeled direct, indirect, method precedent, contradiction
  or insufficient evidence.
- JSON records and hashes that tie the source, quote, images and review together.
- A validated evidence ZIP containing the **complete original PDF**, not just its URL.

For example, a literature-review citation is labeled `cited_prior_work`, not the
target paper's own experimental result. A missing full text, unverifiable
historic coverage, altered quote or missing review blocks final export.

## Install the skill

Agent Skills-compatible installers can discover the single skill:

```bash
npx skills add FishXIN/ShowYourReceipts --skill show-your-receipts
```

For an explicit, reproducible installation, clone a release and copy the folder:

```bash
git clone --branch v0.1.0 --depth 1 https://github.com/FishXIN/ShowYourReceipts.git
mkdir -p /path/to/project/.agents/skills
cp -R ShowYourReceipts/skills/show-your-receipts /path/to/project/.agents/skills/
```

Use the directory your agent supports:

| Agent | Typical project skill directory |
| --- | --- |
| Codex / Agent Skills clients | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| GitHub Copilot | `.github/skills/` |
| TRAE | `.trae/skills/` |

The payload is [skills/show-your-receipts](skills/show-your-receipts). It is
self-contained; root governance files and tests are not needed to invoke it.
If your agent does not load skills automatically, instruct it to read `SKILL.md`
and its linked references before beginning research.

Example prompt:

> Use ShowYourReceipts to find core-journal evidence for this claim. Verify
> historic collection coverage, read the full papers, show the literal passages
> with original and underlined screenshots, label their actual sections, and
> report limitations and contrary findings. If evidence is missing, say so.

## Local helpers

Requires Python **3.10–3.13**, a text PDF, and a working environment that can
install the pinned dependencies. No model credentials are required.

```bash
python3 -m venv /path/to/task/.venv
/path/to/task/.venv/bin/python -m pip install \
  -r /path/to/skill/scripts/requirements.txt
```

Set `SKILL_DIR` to the installed `show-your-receipts` directory. Download a lawful
complete published PDF, or import the user's authorized original, then inspect:

```bash
python "$SKILL_DIR/scripts/receipts.py" download --url "$PDF_URL" --out paper.pdf
python "$SKILL_DIR/scripts/receipts.py" inspect \
  --pdf paper.pdf --out paper-text.json
```

Copy and complete [source.template.json](skills/show-your-receipts/assets/source.template.json)
using inspected official records. Save the actual registry and publisher
snapshots; empty templates do not pass.
Also complete [target.template.json](skills/show-your-receipts/assets/target.template.json)
with the exact user's manuscript/objective passage and location.
Number the user's document before filling it:

```bash
python "$SKILL_DIR/scripts/receipts.py" inspect-target \
  --document user-manuscript.docx --out target-text.json
```

Then extract:

```bash
python "$SKILL_DIR/scripts/receipts.py" extract \
  --pdf paper.pdf --source source.json --target target.json --page 5 --quote-file quote.txt \
  --section-heading "Results" --heading-page 4 --section-role results \
  --printed-page "3105" --paragraph "paragraph 2, right column" \
  --origin author_finding --out receipt-001
```

Complete [review.template.json](skills/show-your-receipts/assets/review.template.json)
as `receipt-001/review.json`, including the generated packet digest and exact
context anchors. Then:

```bash
python "$SKILL_DIR/scripts/receipts.py" check --bundle receipt-001
python "$SKILL_DIR/scripts/receipts.py" export --bundle receipt-001
python "$SKILL_DIR/scripts/receipts.py" pack --bundle receipt-001 --out evidence-001.zip
```

Commands return JSON; rejection returns exit code `2`. Export produces Markdown
with images, section captions and exact user-side relevance.
`pack` validates the records again and includes original PDFs and summaries. See the
[packet guide](skills/show-your-receipts/references/packet-format.md) for fields,
matching, repeated passages and the full output structure.

## Trust boundaries

This project reduces unverifiable research output; it **does not guarantee
hallucination-free agents or scientifically valid conclusions**.

The helpers validate supplied records, literal PDF matches, heading occurrence,
glyph geometry, image rendering, hashes and review anchors. They do not
independently authenticate a locally saved registry snapshot, judge an
experiment, or certify a summary's meaning. A genuine core-journal article may
still be weak, corrected or inapplicable.

For production use, pin a release, isolate untrusted PDF parsing, maintain
independently curated source records, and apply a substantive review appropriate
to the use case. Mark agent reviews as agent reviews. Membership/status records
expire after 90 days. Do not equate `record_checks_passed` with scientific approval.

Version 0.1 accepts single-page, contiguous, text-backed passages. It rejects
scans, rotated/nonstandard page geometry, encrypted PDFs and oversized inputs.
Only the explicit `download` command fetches a public HTTPS PDF with bounded
redirects, public-address checks, TLS verification and download provenance.
It does not bypass paywalls, rank journals, silently OCR pages or publish user documents.
Evidence packages include copyrighted PDFs and potentially unpublished user
manuscripts; they are local research outputs and must be shared only as authorized.

## Repository layout

```text
ShowYourReceipts/
├── skills/show-your-receipts/
│   ├── SKILL.md
│   ├── LICENSE
│   ├── assets/            # empty, explicit input templates
│   ├── references/        # source gate and context-review rules
│   └── scripts/           # local receipt helpers and pinned dependencies
├── tests/                 # synthetic adversarial cases, not scientific evidence
├── .github/               # CI, issue templates and repository checks
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── AGENTS.md
└── CITATION.cff
```

CI checks the single Skill and runs adversarial tests across Linux, macOS and
Windows on Python 3.10–3.13. Tests cover invented passages, missing negation,
ineligible collections, wrong dates, fake registry hosts, image tampering,
missing reviews, ambiguous passages, literature-review attribution, exact user
passage mapping, download checks and full-PDF packaging.

```bash
python -m pip install -r skills/show-your-receipts/scripts/requirements.txt
python .github/scripts/validate_skill.py
python -m unittest discover -s tests -v
```

The layout follows the self-contained skill pattern in
[Anthropic Skills](https://github.com/anthropics/skills), with lightweight
repository checks informed by
[GitHub Awesome Copilot](https://github.com/github/awesome-copilot).
Project code is MIT; dependencies retain their own licenses. No third-party
skill content is vendored.

---

## 中文说明

**让 AI 先亮原文，再下结论。**

ShowYourReceipts 是一个可直接安装的 Agent Skill，附带本地 Python 工具。
它要求每个证据结论提供原文、原图、红线、上下文、来源资格与解读边界。
仓库只包含 Skill、测试与必要的开源配置，不包含论文、私人报告或账号信息。

### 核心规则

- 只接受 SCIE、SSCI、AHCI、CSSCI、CSCD 核心库、北大核心期刊文章。
- 用 ISSN 核验文章发表年份对应的官方收录记录，不能以 DOI、知网或
  PubMed 收录代替核心资格；扩展集、会议与普通期刊不准入。
- 原句必须在 PDF 中匹配，红线按原文字形坐标生成。
- **标明划线位置**：PDF 页码、印刷页码、实际章节标题、章节类型、
  段落/表格/图注位置，以及作者自己的发现或引用前人研究。
- 检查目的、方法、结果、限制、不显著及相反发现；证据不足明确说明。
- 对应用户论文/目的的具体原句、章节和段落，说明相关变量、量表或步骤，
  以及可支持和不能支持的内容。
- 下载完整已发表原文 PDF，保存来源和哈希，与截图及总结一起打包。
- 未核验来源、未读全文或未完成上下文复核时，不导出最终证据。

### 安装与使用

执行上方安装命令，或复制 `skills/show-your-receipts` 到所用 Agent 的
Skill 目录。安装 Python 依赖后，依次运行 `download → inspect → extract →
check → pack`，填写来源、用户论文定位与复核模板。已有合法原文可跳过
下载。所有文档遵循英文在前、中文在后。

可对 Agent 说：

> 使用 ShowYourReceipts 寻找支持这个实验的核心期刊依据。提供原句、
> 原图与红线，标出章节和段落位置，检查是否断章取义，并列出限制和反证；
> 指明对应我论文的具体原句和实验事项，将原文 PDF 与证据一起打包；
> 找不到合格证据就明确说没有。

### 生产使用边界

脚本检查文件、原句、坐标、哈希和核验记录的一致性，不担保官方记录
的下载来源，也不能自动判定学术解读正确。部署时应锁定版本、隔离不可信
PDF 解析、独立维护收录记录，并做相应的实质复核。Agent 复核不得伪装
成人工审核；“记录检查通过”不能写成“学术真实性已经验证”。

当前支持单页连续且可提取文字的 PDF 原句；扫描、旋转、裁切异常、加密
或超大文件会拒绝处理。工具不负责自动爬取、登录或绕过出版社访问限制。
