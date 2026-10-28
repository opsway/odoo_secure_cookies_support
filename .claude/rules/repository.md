# Standalone addon repository rules

- Addons live directly at repository root; a directory is an addon when it contains `__manifest__.py`.
- Repository-level documentation belongs under `docs/`. Root `README.md` and `CLAUDE.md` are deliberate exceptions.
- Addon-specific documentation belongs inside that addon directory.
- Keep unrelated third-party/vendor addons out of first-party packs. If mixing is unavoidable, document provenance/license/upgrade ownership explicitly.
- Recommend repository names prefixed with `odoo-addons-`; do not enforce the prefix.
- Maintain Odoo-major version branches such as `18.0`, `19.0`. The same repository may support several versions.
- Merge commits, squash merges and rebase merges are all allowed on version branches; choose per pull request.
- Prefer a merge commit when the branch history is itself meaningful: imported/baseline history, forward-ports between Odoo version branches, staged adoption work. Prefer squash when the branch is only iteration noise.
- Never rewrite published history on version branches; force-push and branch deletion stay blocked.
- Each addon owns its manifest version independently. An addon version may be absent when there is a justified reason; do not invent a pack-wide semantic version.
- Existing/imported licenses and versions are facts: preserve them during baseline import and normalization.
- ZIP is an intake format, not maintained source. Unpack it, baseline the resulting source, then use Git.
