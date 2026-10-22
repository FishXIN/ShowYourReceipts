# Security

## Supported version

Security fixes target the latest tagged release. Pin a release and update after
reviewing its changes.

## Report privately

Use [GitHub private vulnerability reporting](https://github.com/FishXIN/ShowYourReceipts/security/advisories/new).
Do not post secrets, private PDFs, identifiable participant data or exploit
documents in public issues. Include a minimal, non-sensitive reproducer.

## Boundaries

- PDF parsers process untrusted binary inputs. Run them with OS/container isolation
  and appropriate resource limits. The CLI's limits are not a security sandbox.
- Only explicit `download` requests fetch public HTTPS PDFs, with public-address
  checks on every redirect and address-pinned TLS connections. No other command
  fetches URLs; no script executes instructions embedded in papers.
  Agents must also treat source text as untrusted data.
- Artifact paths are confined and symlinks are rejected. Hashes detect changes;
  they are not authenticity signatures.
- Official-host checks and reviewer records cannot authenticate a fabricated local
  snapshot. Keep source records in a trusted, separately reviewed process.
- HTML-like publisher snapshots are read as data. Generated research summaries
  may contain untrusted text; use a safe Markdown renderer.
- Correct quotations and core-journal membership do not establish an experiment's
  quality, clinical safety or validity of an interpretation.

---

## 中文说明

请通过 GitHub 私密漏洞报告提交安全问题，不要公开私人论文、受试者数据
或凭证。PDF 解析应运行在系统/容器隔离环境中，文件大小限制不是安全沙箱。

只有显式 `download` 命令获取公开 HTTPS PDF，并逐次检查重定向地址。
脚本不执行论文中的指令；哈希和官方域名检查不是真伪签名，
来源记录仍需要可信维护。正确原句与核心资格不等同于研究质量或临床安全。
