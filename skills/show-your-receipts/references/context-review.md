# Context review

## Locate the passage

Record all of the following, even if the passage fits in one screenshot:

| Field | Requirement |
| --- | --- |
| PDF page | One-based file page, not the journal page number |
| Printed page | Visible journal page; use `unpaginated` only when none is printed |
| Heading | Actual verbatim heading, with the page on which it appears |
| Section role | `abstract`, `introduction`, `literature_review`, `methods`, `results`, `discussion`, `limitations`, `conclusion`, `references`, `appendix`, or `other` |
| Paragraph locator | E.g. `paragraph 2, right column`, `Table 3, row 4`, or `Figure 2 caption` |
| Claim origin | `author_finding`, `cited_prior_work`, `method_description`, or `hypothesis` |

The CLI locates the heading literally; the reviewer must confirm that it actually
governs the selected passage. Headings can occur on an earlier page. A phrase
merely mentioned in body text is not a heading. If the document has no explicit
heading, record `unheaded` and explain the section classification in the review.

Make the location visible in each exported figure caption. Do not silently infer
“Results” merely because a sentence sounds conclusive.

## Read the whole paper

Screen the abstract for the target content first and record its literal passage,
location and decision in `abstract_screen`. Then inspect the full text and
determine ownership of the particular claim. Methods may adopt other authors'
tools/data; discussion may compare current results with cited studies. Section
names and citation presence alone do not settle attribution. Follow cited claims
recursively to their actual origin and record every step in `lineage.json`.

Review purpose, population, design, intervention/device, comparator, outcomes,
results, tables, limitations and correction notices. Supply exact context anchors:

1. **Purpose:** the question or intended contribution.
2. **Methods:** participants, design, exposure, comparator and measurement.
3. **Results:** the finding that actually bears on the proposed claim.
4. **Limitations:** author-stated boundaries; if none exist, record full-text
   pages reviewed and what was searched.
5. **Counterevidence:** null, contrary, adverse, or subgroup-specific findings.
   “Not found” requires all pages reviewed and explicit search notes.

Each anchor must specify its actual heading, section role, paragraph position,
PDF and printed page, and claim origin. The validator checks that anchor quotes
appear on those PDF pages. It does not assess study design or statistical validity.

## Interpretation rules

- Do not remove “not”, “may”, “some”, confidence intervals or subgroup conditions.
- Do not convert non-significance into equivalence, safety or proof of no effect.
- Do not replace association with causation.
- Do not generalize a device, body location, age group or task without declaring
  the mismatch.
- Do not copy an optimum timing/pressure from a different actuator as the optimum
  for a new device.
- Do not describe translated/adapted scale items as a validated scale.
- Separate an author's data from cited claims in every section. Follow reference
  entries repeatedly until the actual original eligible paper is inspected.
  Preserve each hop's PDF, citation passage and reference-list entry. Final
  borrowed claims cannot pass by being labeled `indirect` or `insufficient`.
- Do not treat a hypothesis, protocol or future-work proposal as an observed result.
- Distinguish a review's synthesis from an original experiment.
- Preserve disagreements and independent-study counts in the final synthesis.

Use one support category:

| Category | Meaning |
| --- | --- |
| `direct` | Population/intervention/comparator/outcome/setting support the bounded claim |
| `indirect` | A material mismatch limits transfer |
| `method_precedent` | Supports measurement/design, not intervention efficacy |
| `contradiction` | The paper challenges the claim |
| `insufficient` | Insufficient evidence for the proposed inference |

Only `author_finding` can be classified as `direct`; review citations, methods and
hypotheses must be labeled appropriately. Final passages must be an author's
finding or an own-method description, with contextual ownership cues. A review's
own computed synthesis is different from a result it merely quotes.
A draft is never final evidence.

## Reviewer record

Set `reviewer.kind` truthfully to `human` or `agent`. Bind the review to the packet
SHA-256. Provide a bounded summary, translation, applicability mismatch, limitations,
counterevidence and scope assessment. A generic “reviewed” checkbox is inadequate.

The review record makes interpretation inspectable, not infallible. Disagreement
between reviewers should remain visible; do not use a second agent's agreement
as proof of truth.

---

## 中文说明

每段划线内容必须注明：PDF 页序、期刊印刷页、实际章节标题及其页码、
章节类型、段落/表格/图注位置、原文是谁的发现。例如：
“PDF 第 5 页 / 印刷页 3105 / Literature review / 第 2 段右栏 /
引用前人研究”。章节可以从前一页开始，但必须确认它实际管辖该段落。

阅读全文，保留目的、方法、结果、限制、不显著或相反发现的原句与位置。
不能把文献综述中的引用当成目标论文自己的结果，不能把方法先例当成
有效性证明，不能把不显著写成无影响，也不能把不同设备的参数直接迁移。
“未发现限制或反证”须记录所有页码已检查及搜索说明。

先看摘要，再细查正文的具体归属。实验部分也可能采用他人方法或量表，
讨论部分也可能是与别人结果比较；不能单凭章节或是否出现引用作判断。
保存引用原句与参考文献原条目，逐层追到真正产生目标证据的原始论文，
每一跳保留 PDF 与定位，最终借用的论断不能靠改成“间接支持”通过。

明确区分直接支持、间接支持、方法先例、反证和证据不足。复核者须如实
标明人类或 Agent；复核记录提高可检查性，不能保证解读绝对正确。
