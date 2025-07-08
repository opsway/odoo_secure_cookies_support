# Odoo Repository Structure

## Purpose

This guide defines standardized repository structure to ensure consistency and maintainability across engineering teams.

## Repo naming

Private repository named as `odoo-<project_name>`.

## Branches

Ensure that following branches exist and set up properly:

- Main branch: `main`, add it to protection rules to prevent deletion and require PR before merging.
- Staging branch: `stage`, add it to protection rules to prevent deletion and require PR before merging.

## File Structure

```
📁 .github/
├─ GitHub Actions workflows.
│
📁 addons/
├─ Custom Odoo add-ons and modules developed for this project.
│
📁 addons_third_party/
├─ Universal third-party Odoo add-ons.
│
📁 docker/
├─ entrypoint.sh — Entrypoint script to initialize Odoo container.
├─ wait-for-psql.py — Helper to wait for PostgreSQL readiness before starting.
│
📁 enterprise/
├─ .gitkeep — Placeholder to ensure that enterprise/ folder exists before compose creats it with incorrect rights.
├─ TODO: put Odoo Enterprise here, do not clone directly as git clone will not do it to existing directory.
│
📁 env/
├─ common/
│ ├─ check_odoo_updates.py — CD script (on-prem installation).
│ ├─ odoo-nginx.conf — Nginx config for proxying Odoo (on-prem installation).
│ ├─ proxy.conf — Generic proxy settings (on-prem installation).
│ ├─ sample-credentials.env — Example environment variables (credentials) (on-prem installation).
│ ├─ test-odoo.conf — Test configuration for Odoo (stub: specifics vary).
│
├─ live/
│ ├─ stub: production environment compose files and configs (on-prem installation).
│
├─ local/
│ ├─ data/ — Odoo data dir mapping (optional, see below).
│ │ └─ .gitkeep — Placeholder to ensure the local/data/ folder exists before compose creats it with incorrect rights.
│ ├─ data-mapping.yml — Mapping of local data overrides (optional, drop in into PyCharm compiler to activate).
│ ├─ docker-compose.yml — Compose file for local development (Odoo, PostgreSQL).
│ ├─ odoo.conf — Odoo config for local development.
│
├─ stage/
│ ├─ stub: staging environment compose files and configs (on-prem installation).
│
📁 scripts/
├─ Utility scripts for maintenance, migrations, backups, etc (optional).
│
📁 submodules/
├─ Git submodules for shared libraries or third-party modules.
│
📄 .autopep8
├─ Configuration for autoppep8 code formatting.
│
📄 .gitignore
├─ List of files and folders to exclude from Git.
│
📄 .pre-commit-config.yaml
├─ Pre-commit hooks configuration (linting, formatting, safety checks).
│
📄 .pylintrc
├─ Pylint configuration for Python code style and static analysis.
│
📄 Dockerfile
├─ Defines how to build the Odoo Docker image.
│
📄 init.sh
├─ Initialization script (e.g., setting permissions, preparing directories).
│
📄 Makefile
├─ Deploy CI/CD image, service actions, etc.
│
📄 README.md
├─ Project overview, setup instructions, and developer guide.
│
📄 requirements.txt
├─ Core Python dependencies (e.g., Odoo version, psycopg2).
│
📄 requirements-actions.txt
├─ Dependencies for GitHub Actions runners (lint, test environment).
│
📄 requirements-dev.txt
├─ Development dependencies (pytest, coverage, flake8).
│
📄 requirements-lint.txt
├─ Linting-specific dependencies (for local pylint).
```
