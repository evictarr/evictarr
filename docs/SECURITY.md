# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report it privately through GitHub's Security Advisories:

**[Report a vulnerability](https://github.com/evictarr/evictarr/security/advisories/new)**

This opens a private disclosure with the maintainer - nothing is visible
publicly until it's resolved and you both agree to disclose it.

If that link doesn't work (e.g. advisories aren't enabled on the repo yet),
email **spinu.petru.boris@gmail.com** directly, or open a regular issue
asking to be contacted privately, without including any exploit details or
proof-of-concept in the issue itself.

## What counts as a security issue

Roughly, anything that could let someone bypass authentication, access or
modify another installation's data, exfiltrate secrets (`SECRET_KEY`,
`ENCRYPTION_KEY`, integration API keys, session tokens), or get Evictarr to
read/write files or make requests it shouldn't. A few areas specific to
how Evictarr is built that are especially relevant:

- Session/cookie handling and the None/Basic authentication toggle
  (`Settings > Security`).
- Handling of integration API keys and the Fernet-encrypted TOTP secrets.
- The Orphaned Files scanner's filesystem walk (path traversal, symlink
  handling).
- Anything involving the CSRF header check on mutating API requests.

If you're not sure whether something qualifies, report it anyway - false
positives are fine.

## Supported versions

Evictarr doesn't have tagged releases yet - security fixes are applied to
the `main` branch. Once versioned releases exist, this section will be
updated with which versions receive fixes.
