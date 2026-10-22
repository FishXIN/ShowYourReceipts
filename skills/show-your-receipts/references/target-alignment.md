# Relate evidence to the user's manuscript or objective

An eligible paper is not sufficient: every receipt needs a specific user-side
anchor. A topic match such as “relevant to wearable devices” is inadequate.

## Target record

Prepare `target.json` from `assets/target.template.json` using the actual user
document. For an objective given in chat, save the exact objective to a UTF-8 TXT
file and label it `research_objective`. Do not invent an unpublished manuscript.

Record:

- Document title and type, local source filename and SHA-256.
- The user's literal passage, actual section heading and heading position.
- DOCX `paragraph` number or TXT/Markdown `line` number, both one-based.
- The research question and intended use: `background`, `hypothesis`, `design`,
  `measurement`, `analysis`, or `interpretation`.

DOCX paragraph numbering follows the main document's XML order, including table
paragraphs and empty paragraphs; it is not a printed page number. TXT/Markdown
lines include blank lines. Inspect numbering before constructing the record:

```bash
python scripts/receipts.py inspect-target --document manuscript.docx --out target-text.json
```

DOCX headers, footnotes and tracked-change
interpretation are outside the current parser's scope.

The heading and target quote must appear in the specified paragraph/line. The
full local target document is copied into the private packet for reproducibility.
Do not put the user's unpublished manuscript into a public repository.

## Alignment review

`review.target_alignment` must identify:

1. The exact target passage and same intended use.
2. The specific related aspect, such as “§3.1.1 emotional valence measurement”.
3. Why the source finding bears on that aspect.
4. What the paper supports, at the appropriate evidence level.
5. What it does not support, including population/device/task mismatches.

For example: a scale-validation paper may justify the selection of an emotion
measure in the user's methods section. It does not establish that a new pneumatic
belt improves mood. A null result may relate to the user's hypothesis as
counterevidence rather than support.

Keep the user's passage, source passage and relevance rationale separate in the
export. The validator checks literal target location and binding; the reviewer
still has to assess the relationship's meaning.

---

## 中文说明

每条证据必须锚定用户论文/研究目的中的具体原句，标明章节、段落或行号，
而非泛泛写“和课题相关”。聊天中的研究目的可原样保存为文本，不得编造
不存在的论文。DOCX 按正文 XML 段落顺序编号，文本/Markdown 按实际行号。

复核中说明对应的变量、量表、假设、实验步骤或分析方法，为什么相关、
可以支持什么、不能支持什么。量表论文支持测量选型，不能直接证明新设备
有效；相反发现可以关联用户假设为反证。

验证器检查用户原句的位置和绑定，相关性的学术判断仍由复核者完成。
完整用户文档只保存在本地私密证据包中，不得随 Skill 上传公开仓库。
