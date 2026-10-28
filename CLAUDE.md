# Agent entry point

This is a standalone Odoo addon/addon-pack repository. Addons live directly at repository root.

Before changing code, read the applicable files under `.claude/rules/`. Reusable procedures live under `.claude/skills/`.

Core expectations:

- source code, technical documentation, comments, commit/PR text and original translatable strings are English;
- translations belong in normal Odoo translation files/workflows, not as non-English source strings;
- keep addon-specific documentation inside the addon; keep pack/repository documentation under `docs/`;
- preserve existing addon licenses and provenance;
- treat `.claude/rules/`, `.claude/skills/` and shared workflow files as template-managed/read-only by convention; put local additions in `.claude/rules/local.md`;
- use the security-review skill for adoption/high-risk changes and the architectural-review skill for non-trivial structural changes.

Do not assume this repository is a deployable Odoo project. Runtime customer deployment belongs elsewhere; Workbench may later be used for isolated staging/UAT.
