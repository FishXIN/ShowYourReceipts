# Contributing

Thank you for improving research evidence people can inspect.

## Scope

Keep this repository a single self-contained skill. Do not add unrelated agents,
hosted services, research papers, credentials, private receipts or copied skills.
Write English first, with Chinese explanation after it. Keep the root small.

For bug fixes, describe the failure and the corrected behavior. For source-policy
changes, provide the authority's official evidence, coverage dates and an
adversarial test. Never weaken fail-closed behavior to make a fixture pass.

## Development

```bash
python3 -m venv /path/to/dev/.venv
/path/to/dev/.venv/bin/python -m pip install \
  -r skills/show-your-receipts/scripts/requirements.txt
/path/to/dev/.venv/bin/python .github/scripts/validate_skill.py
/path/to/dev/.venv/bin/python -m unittest discover -s tests -v
```

Use synthetic, explicitly labeled fixtures for tests. Do not add copyrighted
publisher PDFs. Place caches and generated packets outside the source tree.
Keep the command-line result format machine-readable and the skill's references
aligned with code behavior.

Preserve exact quotations, original images, section/paragraph attribution,
contrary findings and reviewer identity. A contribution must not claim that
an LLM review or checksum proves scientific truth.

Submit a focused pull request with validation evidence and material limitations.
Report security issues through the process in [SECURITY.md](SECURITY.md).

## License

Contributions are accepted under the repository's MIT license. Contributors must
have the right to contribute their code and documentation.

---

## 中文说明

仓库只维护一个完整 Skill；不要提交论文、私人证据包、凭证或无关项目。
文档保持英文在前、中文在后。修改来源策略必须提供官方依据、适用年份
和对应的拦截测试，不能为了通过测试而降低门槛。

使用明确标记的合成测试素材，生成物和缓存放在源码之外。修改后运行
结构检查与测试，提交说明实际问题、行为变化和验证结果的 PR。
不能声称 Agent 复核或哈希足以证明学术真实性。
