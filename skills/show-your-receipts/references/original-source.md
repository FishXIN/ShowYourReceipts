# Trace to the paper that generated the evidence

## Screen the abstract first

For each candidate, read its abstract before searching the body for a convenient
sentence. Record a literal abstract passage with its actual location and explain
whether it mentions the user's target variable, method or result. An abstract is
a screening aid, not proof of ownership or sufficient final evidence.

Use `abstract_screen` in the endpoint's review and in every citation hop:

- `status: present`, `decision: target_mentioned`: supply abstract quotes and rationale.
- `status: present`, `decision: not_mentioned_full_text_review`: supply abstract
  quotes, rationale, all PDF pages reviewed and search notes explaining why a
  detailed review was warranted. Lack of an abstract keyword alone is not exclusion.
- `status: absent`, `decision: no_abstract_full_text_review`: use an empty quote
  list and document the absence, all pages reviewed and search notes. This means
  the paper has no abstract, not that its abstract or full PDF was inaccessible.

Do this screening during collection; a filled JSON record does not prove reading
order. Never invent an abstract for an older paper.

## Determine who produced the particular claim

Inspect the sentences before and after the target passage, subject/author
attribution, citation markers, methods, tables and results. Identify the origin of
the exact datum or method, rather than of the whole paragraph.

| Context | Required distinction |
| --- | --- |
| Introduction / literature review | Usually describes prior work; follow the relevant citation |
| Methods / experiment | May implement the authors' own method, adopt a cited method or scale, or describe inherited data; inspect attribution |
| Results | May compare current results against published results or reuse a dataset; locate who actually generated the specific number |
| Discussion | Separate the current study's results from other studies used for comparison |
| Review / meta-analysis | Own pooled estimate or synthesis belongs to the review; a primary study's result still belongs to that study |

No section is automatically original. A citation near a sentence does not
automatically make every part of that sentence borrowed. For mixed passages,
separate the claims and preserve enough surrounding text to justify attribution.
For an adopted scale, trace development/validation to its original paper; an
application study alone does not establish scale validity. For a dataset, trace
collection to the generating study when collection is the claimed precedent.

## Follow each citation recursively

1. Save the citation-bearing literal passage and its location.
2. Find its exact reference-list entry. Save the complete identifying passage,
   location, in-text citation marker and corresponding reference marker.
3. Resolve the DOI, or exact full title when there is no DOI. Inspect the next
   published PDF and verify its identity and publication-year core eligibility.
4. Start with that paper's abstract, then inspect the detailed context. If it
   credits another source for the target datum/method, repeat from step 1.
5. Stop only at the paper that actually generated the data, developed the method
   or computed the specific synthesis being used. Save matched context cues and
   explain ownership. Recursion ending at another review's borrowed sentence is
   unresolved.

Use a separate lineage for each claimed datum/method when citations branch to
different origins. Do not drop an inconvenient branch or combine unrelated
references into a single supposed origin. An original synthesis can support a
synthesis claim; it cannot become evidence that the review ran every included
experiment. Identify dependent datasets separately from citation lineage.

## Lineage record

Copy `assets/lineage.template.json` (relative to the skill directory). Remove
`hop_example_do_not_submit` after using it as a shape guide.

- `initial_identifier`: DOI or full title of the first paper inspected.
- `final_identifier`: DOI/full title matching the primary `source.json` and
  `--pdf`. The main receipt must quote this final original source.
- `hops`: ordered citing papers, excluding the endpoint. Each hop contains a
  PDF path/hash, its own source JSON path, abstract screen, citation passage,
  reference entry, `citation_marker`, `reference_marker`, `cited_identifier`
  and `link_rationale`. Mark the passage `cited_prior_work` and the reference
  section role `references`. The two markers may be formatted differently
  (e.g. `[12]` and `12.`); explain their correspondence.
- `resolution`: `original_source_resolved` only after completing the trace.
- `ownership.kind`: `own_data`, `own_method` or `own_synthesis`.
- `ownership.context_cues`: located literal endpoint passages showing its own
  data/method/synthesis, with `author_finding` or `method_description` origin.
- `ownership.rationale`: explain attribution using the surrounding context,
  experimental implementation/results and explicit author/citation cues.
- `reviewed_at`, `reviewer`: current date and honest reviewer identity/type.

Input PDF and source JSON paths are relative to lineage.json. Each source record's
snapshot paths remain relative to that source JSON. The CLI copies all files into
flat `trace-001-*`, `trace-002-*` names, regenerates original/red-underlined
passage and reference images, and binds them into the packet manifest.
Sidecar `paper.pdf.download.json` files are preserved when present.

If the first paper already generated the target evidence, use `hops: []` and
identical initial/final identifiers. Still document abstract screening and
ownership; absence of a visible citation alone is not proof of originality.

The CLI rejects unresolved chains, cycles, missing/wrong PDFs, broken DOI/title
links, unverifiable core eligibility, absent context cues, and final
`cited_prior_work`/`hypothesis` passages in every support category. It permits
an own method to cite background work, but that method description cannot be
classified as direct experimental evidence. It requires an own-method receipt
to use `method_description` for the selected passage.

If the ultimate source is inaccessible or fails the core gate, record the gap in
the candidate log and do not export a final receipt for that claim. The tool
never follows remote citations implicitly; the agent uses its available lawful
search/download tools. The 32-hop resource limit is a refusal boundary, not
permission to truncate a chain and label it resolved.

Hashes, exact matches and identifier links validate recorded provenance. They
cannot certify that the reviewer chose the correct reference, interpreted
ownership correctly, found every ancestor or made a valid scientific inference.

---

## 中文说明

先看每篇候选论文的摘要，判断是否涉及目标变量、方法或结果，再进入正文
细查。摘要没出现关键词但仍有必要查全文时，记录理由和所有已读页码；
原论文没有摘要时明确登记，不能编摘要，也不能拿摘要代替全文。

逐句判断“谁产生了这个数据或方法”。引言/综述经常引用前人；实验部分也
可能采用别人量表或方法；讨论部分经常把自己的结果和别人结果比较。
不能只看章节名称，也不能见到引用就认定整段都是别人的。混合归属要拆分
具体论断，保留上下文。量表的开发和验证，应继续追到原始开发/验证论文。

保存引用原句、章节/页码/段落、引用标记及参考文献原条目，核对 DOI 或
完整标题，下载下一篇已发表原文 PDF，并重新核验核心资格、先看摘要、
再判断正文归属。仍是转引就继续追，直到找到实际产生目标证据的原始论文。
不同数据引用不同论文时分别建立溯源链，不能随意删掉分支。

`lineage.json` 记录每一跳及最终归属，`review.json` 记录最终论文的摘要
初筛。主证据的 `--pdf` 和 `source.json` 必须来自最终原始论文。最初已是
原始研究时，引用链可以为空，但仍要提供摘要初筛、归属原句和理由。
最终文章自己的汇总估计可作为综述综合结论，不能冒充亲自完成全部实验。

每一跳的 PDF、来源核验、引用段和参考文献条目的原图/红线图都会保留并
打包。原始来源找不到、拿不到全文或不符合核心准入，明确报告缺口；
不能停在转引文章上冒充已完成溯源。脚本检查记录与文件一致性，不能自动
担保语境判断、引用选择或整个学术结论正确。
