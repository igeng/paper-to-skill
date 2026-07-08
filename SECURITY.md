# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in paper-to-skill, please report it privately via GitHub's [Security Advisories](https://github.com/igeng/paper-to-skill/security/advisories) page. Do not open a public issue.

We aim to respond within 72 hours and provide a fix timeline.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

## Security Considerations

paper-to-skill processes user-provided PDF files. The project:

- Does **not** send paper content to any external service — all extraction runs locally
- Uses only standard Python libraries and well-known open-source parsers (pypdf, pdfminer.six, docling)
- Passes user-provided file paths to subprocess (pdftotext); paths are validated before execution
- Does **not** execute or interpret extracted paper content as code

Users should exercise caution when running paper-to-skill on untrusted PDF files, as with any PDF processing tool. PDF vulnerabilities in third-party parsers are outside our control.
