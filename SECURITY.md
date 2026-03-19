# Security Policy

`pymodules` is distributed on PyPI as `pytmodules`.

## Supported Versions

Only the latest stable release line receives security fixes.

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes     |

Older versions are considered unsupported and may not receive patches.

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues by emailing the maintainer directly. You can find contact details via the GitHub profile at [github.com/tomcroot](https://github.com/tomcroot).

Include in your report:

- A description of the vulnerability
- Steps to reproduce
- Potential impact
- (Optional) A suggested fix or patch

You will receive an acknowledgement within **48 hours** and a resolution or mitigation plan within **7 days** for confirmed issues.

Please include the affected version (for example, `0.1.0`) and whether you installed from PyPI (`pytmodules`) or from source.

## Scope

pymodules is a developer tooling library. The primary attack surfaces to consider are:

- **Manifest loading** — `module.json` is loaded via `json.loads()`. Malicious manifest files from untrusted module sources could inject unexpected configuration.
- **Dynamic imports** — the `providers` list in `module.json` is used to import and instantiate classes. Only load modules from trusted sources.
- **Code generation** — scaffold presets write Python files to disk. Run `module_make` only in trusted project directories.

## Disclosure Policy

Once a fix is released, we will publish a GitHub Security Advisory with details and include the fix in release notes.
