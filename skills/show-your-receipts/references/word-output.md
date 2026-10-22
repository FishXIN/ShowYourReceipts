# Fixed final Word report

Deliver **one `.docx` report and its matching evidence ZIP** for each research
task. Use the bundled `deliver` command after all packets pass `check`. Do not
ask the user to choose an output format or compose a free-form final report.
Markdown is an internal audit record, not the final user deliverable.

## Minimal layout

Use A4, white background, black text, 20 mm margins, 11 pt body text, 16 pt
title and 13 pt evidence headings. Start directly with
“论文原文、中文对照与红线截图”. Repeat this fixed block for every evidence item,
in the requested research order:

1. `证据 N：` followed by the bounded claim.
2. Citation, verified collection/edition, support category and clickable DOI/article URL.
3. User manuscript/objective location, literal user passage and specific relevance.
4. Original quote and Chinese translation as two rows of a borderless text table.
5. What it supports, then limits, mismatches and contrary/non-significant findings.
6. Source PDF/printed page, actual section/paragraph and author/cited origin.
7. Original-source trace, then original and red-underlined excerpt images with
   complete location captions. Each citation hop adds its citation passage,
   reference entry and corresponding original/underlined images.

Embed actual checked screenshots. Keep their original bytes and aspect ratio.
Keep original wording, negation and uncertainty intact. Supply the reviewer
claim, relevance, support and limits in Chinese for a Chinese-language task;
retain original article titles, quotes and identifiers. Do not invent translations.

Do not add a cover, table of contents, executive summary, decorative boxes,
colored section backgrounds, icons, promotional copy, unrelated advice, or a
second analysis section. Do not copy a former report's source choices, approximate
quotes or conclusions merely because its layout is the reference.

All source gates, full-text review and recursive provenance checks still apply.
The concise Word view does not need to reproduce JSON hashes or every review
anchor in the visible text; these remain in the ZIP with the complete original
PDFs, original images and machine-readable review records.

## Generate

Requires Node.js 20+ in addition to the Python dependencies:

```bash
npm ci --ignore-scripts --no-audit --no-fund --prefix "$SKILL_DIR/scripts"
python "$SKILL_DIR/scripts/receipts.py" deliver \
  --bundles receipt-001 receipt-002 \
  --out "/path/to/task/论文证据.docx"
```

This writes `论文证据.docx` and `论文证据.zip`. Every packet is rechecked before
generation; one failed packet stops the whole delivery. Existing outputs are not
overwritten. Images and hyperlinks are embedded in the Word file. The ZIP
contains that same Word file, every original source/citation-hop PDF and the
complete checked evidence packets.

For one packet, `export` also writes `report.docx` with an internal `report.md`;
`pack` embeds a newly generated `report.docx` in its ZIP. Use `deliver` for the
task's one consolidated final Word report. No layout/format override exists.

Inspect the actual Word output for missing images, unreadable text, broken links
and blank pages. If Word generation fails, fix the dependency/input or report
the specific failure; do not silently substitute chat text, HTML or Markdown.
When there is no eligible evidence, state that gap; do not fabricate a completed
illustrated report or admit rejected sources to fill it.

---

## 中文说明

每次研究任务最终固定交付 **一份极简图文 Word＋配套原文 ZIP**，
不让用户选输出格式，不允许 Agent 自由编排成另一种报告。
版式参考“第五部分”：直接进入“论文原文、中文对照与红线截图”，逐条写
证据标题、出处和链接、对应用户论文的位置、原句与翻译、支持与边界、
原文位置与归属、溯源，以及原图/红线图。

A4 白底黑字、20 mm 页边距、正文 11 pt；原句与中文对照用无边框两行表格。
图片保持原始字节和比例，每张图注标明章节、页码和段落。
不加封面、目录、装饰、额外总结或无关建议。参考的是排版，不能沿用旧报告
不符合来源门槛的文献、近似引文或未经复核的结论。

通过 `deliver --bundles ... --out 论文证据.docx` 一次生成 Word 和同名 ZIP。
它会重新检查全部证据包；任一证据不通过就停止。ZIP 保存原文 PDF、
逐跳引用材料、原图和复核记录。Markdown 只是内部核验文件，不能代替
最终 Word；生成失败要修复或说明原因，不能偷偷换成网页或聊天文本。
