# ShowYourReceipts

**Less paper chasing. More research.**

[![CI](https://github.com/FishXIN/ShowYourReceipts/actions/workflows/ci.yml/badge.svg)](https://github.com/FishXIN/ShowYourReceipts/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skill](https://img.shields.io/badge/Agent-Skill-green.svg)](skills/show-your-receipts/SKILL.md)

For those “I know I read that somewhere” moments.

Give your AI a research sidekick that checks where a claim really came from.
ShowYourReceipts helps find papers, follow citations, mark the useful passages,
and put the evidence together—so you can spend more time moving your research forward.

It's **one installable Agent Skill**. Use it with your agent's search and reading tools.

**English first · [中文说明](#中文说明)**

## What it helps you do

- **Find the right papers.** Start with your research question, manuscript or experiment.
- **Follow the footnotes.** Read the abstract, check the context, and trace borrowed
  claims to the paper that actually produced the data or method.
- **See the evidence.** Get exact quotes, translations and red-underlined screenshots,
  with the page, section and paragraph spelled out.
- **Connect it to your work.** See which hypothesis, scale or experiment step a
  paper supports, including its limits and contrary findings.
- **Keep it all together.** Package the original PDFs, screenshots and summary
  into a ZIP you can revisit.

Useful for literature reviews, checking citations, choosing measurement scales,
and finding a sound basis for an experiment.

## Get your research sidekick

```bash
npx skills add FishXIN/ShowYourReceipts --skill show-your-receipts
```

Then give your agent a task:

> Use ShowYourReceipts to find core-journal evidence for my experiment.
> Trace the claims to their original papers, show the key passages, explain
> which parts of my experiment they support, and package the PDFs.
> Tell me where the evidence runs out.

For a pinned version, download the [release](https://github.com/FishXIN/ShowYourReceipts/releases)
or copy the skill from a tagged checkout:

```bash
git clone --branch v0.1.1 --depth 1 https://github.com/FishXIN/ShowYourReceipts.git
mkdir -p /path/to/project/.agents/skills
cp -R ShowYourReceipts/skills/show-your-receipts /path/to/project/.agents/skills/
```

Use the skill directory your agent supports:

| Agent | Project skill directory |
| --- | --- |
| Codex / Agent Skills clients | `.agents/skills/` |
| Claude Code | `.claude/skills/` |
| GitHub Copilot | `.github/skills/` |
| TRAE | `.trae/skills/` |

If your agent doesn't load skills automatically, ask it to read
[SKILL.md](skills/show-your-receipts/SKILL.md) and its linked guides first.

## Fast research still needs a trail

Three rules keep the shortcuts honest:

1. **Check the journal.** Accept SCIE, SSCI, AHCI, CSSCI, CSCD core or PKU core
   journal articles, with official coverage verified for the publication year.
2. **Check who said it.** A sentence in “Methods” or “Discussion” can still cite
   someone else's work. Follow the references until the real origin is clear.
3. **Show the source.** Keep complete PDFs, literal passages and their context.
   Missing full text or unresolved provenance blocks final export.

This helps reduce unsupported AI claims. Study quality, source authenticity and
interpretation still need a researcher’s judgment.

## Local tools

The skill includes a Python helper for downloading public PDFs, marking passages,
checking records and packaging evidence. Requires Python **3.10–3.13** and text PDFs.

```bash
python3 -m venv /path/to/task/.venv
/path/to/task/.venv/bin/python -m pip install \
  -r /path/to/skill/scripts/requirements.txt
```

Your agent follows the [skill instructions](skills/show-your-receipts/SKILL.md).
For manual use, the [packet guide](skills/show-your-receipts/references/packet-format.md)
covers the commands and input templates.

Search and access depend on your agent and its available tools. The helper
downloads lawful public PDFs; it does not log in or bypass paywalls.
Evidence packs stay local unless you choose to share them.
Scanned, encrypted, rotated or unsupported PDF layouts are rejected.

## Contribute

Have a citation that keeps sending an agent in circles? Found a misleading
quote or a broken check? [Open an issue](https://github.com/FishXIN/ShowYourReceipts/issues)
or see [CONTRIBUTING.md](CONTRIBUTING.md).

The repository contains one self-contained skill, tests and project configuration.
It ships no research papers, private manuscripts or credentials. Project code is MIT.

CI runs 43 adversarial tests across Linux, macOS and Windows on Python 3.10–3.13.

```bash
python .github/scripts/validate_skill.py
python -m unittest discover -s tests -v
```

---

## 中文说明

**最好的科研搭子，减少Agent幻觉**

「我记得有篇论文这么说过。」让你的科研搭子接着找。

ShowYourReceipts 帮你的 AI 找论文、追出处、画重点、整理资料，
让你少花时间翻来翻去，多花时间推进研究。
一个 Skill，给常用 Agent 装上就能用。

### 它能帮你什么

- **找对论文：** 围绕你的课题、文稿或实验，寻找核心期刊依据。
- **追到原始出处：** 先看摘要，再核对正文；遇到转引，沿参考文献继续找。
- **把重点摆出来：** 原句、翻译、红线截图，以及具体章节和页码一起给你。
- **说明与你的研究有什么关系：** 支持哪个假设、量表或实验步骤，有哪些限制。
- **把资料收好：** 原文 PDF、截图和总结一起打包，下次不用从头翻。

写综述、查引用、选量表、找实验依据，都可以叫它帮忙。

### 开始用

```bash
npx skills add FishXIN/ShowYourReceipts --skill show-your-receipts
```

装好后，直接对 Agent 说：

> 帮我找这个实验的核心期刊依据。追到真正的原始论文，把关键原句画出来，
> 说明它支持我实验的哪个环节，再把 PDF 和资料打包。找不到依据就直说。

也可以从 [发布页](https://github.com/FishXIN/ShowYourReceipts/releases)
下载，按上方目录表放进你的 Agent。
本地工具需要 Python 3.10–3.13；具体步骤交给 Skill 指引。

### 找得快，出处也要跟得上

只接受核验过发表年份收录范围的指定核心期刊。
实验部分可能采用他人方法，讨论部分也可能比较他人成果；
要看语境，追到真正产生目标数据或方法的论文。
原文拿不到、出处没追清，就说明缺口，不把转引当成最终依据。

它帮你减少无依据的回答、节省查证和整理的功夫。
论文质量与结论解读，仍需要你的专业判断。资料默认留在本地。
