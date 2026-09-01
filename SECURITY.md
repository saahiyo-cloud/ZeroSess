# 🛡️ Security Policy

## Security Architecture in ZeroSess

ZeroSess is built with strict privacy and security guarantees:
- **In-Memory Operation:** Client instances and sessions exist exclusively in RAM during authorization. No `.session` or `.sqlite` files are ever written to disk.
- **Zero PII Logging:** Phone numbers, OTP codes, passwords, API hashes, and session strings are filtered and prevented from reaching logs.
- **Auto-Burn Mechanism:** Sensitive input prompts and temporary messages are purged immediately, and final session output messages auto-delete after the configured timeout.
- **Rate Limiting:** Protects against abuse and Telegram FloodWait triggers.

## Reporting a Vulnerability

If you discover a security vulnerability within ZeroSess:
1. **Do NOT** open a public issue.
2. Report the vulnerability privately via GitHub Security Advisories or contact the maintainer directly.
3. Include details of the vulnerability, reproduction steps, and potential impact.

We take security issues seriously and will respond promptly to verify and patch vulnerabilities.
