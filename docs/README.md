# Documentation visuals

These assets explain the workflow and show the existing Word output.
They are not part of the installable Skill.

| Asset | Purpose | Origin |
| --- | --- | --- |
| `images/research-flow-en.svg`, `images/research-flow-zh.svg` | Research question → eligible papers → original source → context → Word and ZIP | Original vector diagrams, MIT |
| `images/source-trace-en.svg`, `images/source-trace-zh.svg` | A conceptual citation chain, with checks at every paper | Original vector diagrams, MIT |
| `images/word-layout-demo.png` | Actual output layout with quotes, links, source location and images | Screenshot of the bundled Word renderer using synthetic test text |

The Word preview is **a layout demo, not scientific evidence**. Its source text
and images come from the explicitly labeled synthetic PDF fixture in
`tests/test_receipts.py`. Display labels identify it as a demonstration; it
does not assert a real journal's status, a real DOI, or a research conclusion.
It contains no real research paper, private manuscript or third-party screenshot.

The preview was generated with `receipts.render_word` and macOS Quick Look.
Only unused outer white margins were cropped; text and evidence images were
kept intact. The PNG description repeats the demonstration label.
Regenerate when the actual output layout changes, and visually inspect it.

SVG files use native text and vector paths, contain no external assets,
and include a title/description for accessibility. Edit the bilingual versions
together; do not replace them with screenshots of research evidence.

---

## 中文说明

这些图片用来说明流程和展示 Word 排版，不属于安装包内容。
流程图和溯源图是原创矢量图，英文和中文各一版，遵循 MIT 许可。

Word 截图由实际生成器输出，原句与图片来自明确标记的合成测试 PDF。
**只演示版式，不是科研证据，不可用于论文引用**。截图不包含真实论文、
私人文稿，也不宣称核验了真实期刊或科研结论。只裁去外围空白，
没有删改文字或内部证据图片。

修改输出布局后应重新生成并检查截图；图示的中英文版本同步维护。
