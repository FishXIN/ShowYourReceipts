#!/usr/bin/env python3
"""Validate the single distributable skill and repository hygiene."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/show-your-receipts"


def main():
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)

    paths = list((ROOT / "skills").glob("*/SKILL.md"))
    require(paths == [SKILL / "SKILL.md"], "repository must contain exactly one named skill")
    document = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\nname: ([^\n]+)\ndescription: ([^\n]+)\n---\n(.+)", document, re.S)
    require(bool(match), "frontmatter must have a plain name and description")
    if match:
        name, description, body = match.groups()
        require(name == SKILL.name, "name must match the skill folder")
        require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)), "invalid skill name")
        require(2 <= len(name) <= 64, "skill name length outside limits")
        require(not any(token in description for token in (": ", "<", ">", "TODO", '"')),
                "invalid description")
        require("Use for" in description or "Use when" in description, "description needs a trigger")
        require(bool(body.strip()), "skill body cannot be empty")
    require(len(document.splitlines()) < 500, "move extended instructions into references")
    for md in SKILL.rglob("*.md"):
        if "node_modules" in md.relative_to(SKILL).parts:
            continue
        content = md.read_text(encoding="utf-8")
        require("## 中文" in content, f"{md.name} needs English-first Chinese explanation")
        for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", content):
            if "://" not in link and not link.startswith("#"):
                target = md.parent / link.split("#")[0]
                require(target.is_file(), f"broken skill reference in {md.name}: {link}")
        require("\r" not in content, f"{md.name} must use LF line endings")
    for template in (SKILL / "assets").glob("*.json"):
        json.loads(template.read_text(encoding="utf-8"))
    require((SKILL / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes(),
            "skill must retain the repository license")
    for workflow in (ROOT / ".github/workflows").glob("*.yml"):
        content = workflow.read_text(encoding="utf-8")
        for action in re.findall(r"uses:\s*([^\s#]+)", content):
            require(bool(re.fullmatch(r"[^@\s]+@[a-f0-9]{40}", action)),
                    f"third-party action must be pinned to a commit: {action}")
        require("permissions:" in content, "workflow permissions must be explicit")
    for file in ROOT.rglob("*"):
        if any(part in (".git", ".venv", "__pycache__", "node_modules") for part in file.relative_to(ROOT).parts):
            continue
        require(not file.is_symlink(), f"unexpected symlink: {file.relative_to(ROOT)}")
        if file.is_file():
            require(file.suffix.lower() not in (".pdf", ".docx", ".png", ".jpg", ".zip"),
                    f"research or output artifact found: {file.relative_to(ROOT)}")
            if file.suffix in (".md", ".py", ".cjs", ".json", ".yml"):
                content = file.read_text(encoding="utf-8")
                require(not re.search(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9]{30,})", content),
                        f"possible credential in {file.relative_to(ROOT)}")
    if errors:
        print(json.dumps({"status": "rejected", "errors": errors}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "passed", "skill": SKILL.name, "skill_count": 1}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
