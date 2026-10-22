# Source policy

## Eligible collections

| System | Authority | Default registry hosts |
| --- | --- | --- |
| SCIE / SSCI / AHCI | Clarivate Master Journal List | `mjl.clarivate.com`, `clarivate.com` |
| CSSCI | Nanjing University | `cssci.nju.edu.cn`, `cssrac.nju.edu.cn` |
| CSCD | Chinese Science Citation Database | `sciencechina.cn`, `las.ac.cn` |
| PKU_CORE | Peking University core journal catalogue | `lib.pku.edu.cn` |

Only main/source collections qualify in this version. CSSCI extended collections
and CSCD extended collections do not qualify. A journal's web page, a university
library's unofficial spreadsheet, or a commercial ranking site is not an official
listing. If an authority changes its host, raise a policy update with evidence;
do not disable the allowlist in the middle of a task.

An official PDF/HTML/CSV/plain-text export may be saved locally. Preserve the
original bytes and source URL. A screenshot without extractable membership text
requires manual transcription with explicit OCR provenance; version 0.1 does
not accept it automatically.

## Verify the right year

Do not apply current journal membership retroactively. Record the list edition
and coverage start/end years demonstrated by the official record. The article's
publication year must lie within that range. If historic coverage is unavailable,
the candidate remains ineligible; do not invent a range from the journal's age.

ISSN is the join key. Use the exact print/electronic ISSN present in the official
entry, not just a similar title. Journal renames and ISSN changes require an
explicit, sourced relationship. All relevant systems have to be stated correctly:
SSCI is not SCIE, and ESCI is not a substitute for either.

## Source record

`source.json` includes:

- Article title, journal, DOI or stable URL, publication year, article kind,
  verified ISSN, and a literal PDF identity anchor.
- Collection name, edition, demonstrated coverage years, official URL,
  collection label, membership quote, saved snapshot and SHA-256.
- A reviewer with `kind` = `human` or `agent`, and a recent verification date.
- A current publisher status snapshot, article identifier, status assessment,
  and a correction note if applicable.

Only research, review, systematic-review, and methodology journal articles are
eligible. Conference proceedings, book chapters, abstracts, editorials and
protocols are not admitted as empirical evidence by this version. A review can
support a synthesis but must not be represented as the review author's experiment.

The CLI checks the record, host, dates, exact saved passages and local hashes.
It cannot prove that a local snapshot came from the asserted URL, that a reviewer
is trustworthy, or that a record establishes collection membership semantically.
Organizations should supply independently curated, access-controlled records
and review claims before clinical or other consequential decisions.

## Retraction and correction

Consult the publisher's article record and Crossmark when available. Crossref
and bibliographic databases may assist discovery but do not certify either
core status or absence of retraction. Save the inspected publisher record.

Reject retractions and expressions of concern. For corrections, inspect the
correction text, record its URL and explain how it affects the quoted finding.
Absence of a retraction notice is a reviewer assessment, not a machine theorem.

## Search discipline

Search eligible collections before broad web search. Maintain a candidate log
with exclusion reasons and unavailable historic coverage. Seek contrary findings,
replication studies and null results. Do not keep searching only for confirmation.
Disclose when support comes from a single study or dependent datasets.

Search snippets, abstract-only records and inaccessible full texts are leads,
not final evidence. Do not bypass authentication, paywalls or publisher restrictions.
Keep copyrighted articles and confidential files out of public repositories.

Screen each candidate's abstract, then inspect the detailed context for ownership.
If a target claim is borrowed, follow the citation chain recursively to the paper
that actually generated the evidence. Every hop and the endpoint require the
same source verification; a secondary core-journal citation cannot admit an
ineligible original source. A missing/ineligible ancestor stays an evidence gap.

---

## 中文说明

正式证据仅接受 SCIE、SSCI、AHCI、CSSCI 来源集、CSCD 核心库、北大核心
期刊中的研究、综述、系统综述或方法学文章。扩展集、会议、书籍章节、
预印本、学位论文和普通期刊不准入。综述不能伪装成作者自己的实验。

以 ISSN 对齐期刊身份，核验文章发表年份对应的官方收录记录，保存版本、
覆盖年份、条目原句、官方链接、文件哈希、核验日期和复核者身份。
不能用当前收录反推历史年份，也不能用 DOI、知网、PubMed 或影响因子
代替核心资格。

检查出版社当前文章记录中的撤稿、关注声明和勘误。脚本检查本地记录
一致性，不担保下载来源和语义真实；正式部署应使用独立维护的收录记录，
对学术结论做实质复核。找不到合格来源时如实输出证据缺口。
先筛摘要，再判断正文归属；目标论断若为转引，逐层追到原始研究，每一跳
及最终原文都须核验核心资格。原始来源不合格或无法取得，不能以转引它的
核心论文代替，只能登记证据缺口。
