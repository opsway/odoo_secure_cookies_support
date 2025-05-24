# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an Odoo 18.0 project containing custom addons and third-party modules. The codebase is structured as:

- `/addons/` - Internal custom Odoo addons (opsway_employee_bill, account_validation_by_currency, etc.)
- `/submodules/` - Third-party and external Odoo modules
- `/docker/` - Docker configuration for running Odoo
- `/opsway/` - Additional OpsWay-specific modules

## Development Commands

### Docker Environment
```bash
# Build the Odoo container
docker build -t odoo-internal .

# Run with PostgreSQL database
docker run -d --name postgres-odoo -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres postgres:13

# Run Odoo container linked to database
docker run -d --name odoo --link postgres-odoo:db -p 8069:8069 odoo-internal

# Or use docker-compose if available
docker-compose up -d

# Access Odoo web interface
# http://localhost:8069
```

### Testing
```bash
# Run tests for a specific addon
python3 -m pytest addons/<addon_name>/tests/

# Run tests with Odoo test framework
odoo -d <database_name> -i <addon_name> --test-enable --stop-after-init

# Example: Test opsway_employee_bill
odoo -d test_db -i opsway_employee_bill --test-enable --stop-after-init
```

### Addon Development
```bash
# Install an addon in development mode
odoo -d <database_name> -i <addon_name> --dev=all

# Update an addon
odoo -d <database_name> -u <addon_name>

# Create new addon scaffold
odoo scaffold <addon_name> addons/
```

## Architecture

### Odoo Module Structure
Each addon follows standard Odoo structure:
- `__manifest__.py` - Module metadata and dependencies
- `models/` - Python model definitions extending Odoo base classes
- `views/` - XML view definitions (forms, trees, reports)
- `security/` - Access control definitions
- `tests/` - Unit tests using Odoo's TransactionCase
- `static/` - Static assets (CSS, JS, images)
- `i18n/` - Translation files (.po files)

### Key Patterns
- Models inherit from `models.Model` or `models.TransientModel`
- Tests use `@tagged('post_install', '-at_install')` decorator
- Translations are handled via `update_field_translations()` method
- Reports use QWeb templates with bilingual support (English/Ukrainian)

### Database Integration
- Uses PostgreSQL as backend database
- Database connection configured via environment variables in Docker
- Wait-for-database script ensures DB availability before startup

### Module Dependencies
- Core dependencies: `base`, `account`, `stock`, `crm`
- Internal modules often depend on each other
- Check `__manifest__.py` for specific dependency chains

## Testing Framework

Tests use Odoo's built-in testing framework:
- Inherit from `odoo.tests.common.TransactionCase`
- Use `@classmethod setUpClass(cls)` for test data setup
- Support for multilingual testing (English/Ukrainian)
- PDF report generation testing included
- Database transactions are automatically rolled back after tests

## File Locations

### Key Configuration Files
- `requirements.txt` - Empty (dependencies managed by Docker)
- `requirements-dev.txt` - Development dependencies (pytest-odoo, etc.)
- `Dockerfile` - Complete Odoo environment setup
- `docker/entrypoint.sh` - Container startup script with DB connection handling

### Custom Modules
- Employee billing: `addons/opsway_employee_bill/`
- Account payment customizations: `addons/opsway_account_payment/`
- Currency validation: `addons/account_validation_by_currency/`
- Partner bank defaults: `addons/account_partner_default_recipient_bank/`
- Analytical percentage calculation: `addons/account_analytic_percentage/`

When working on addons, always check the `__manifest__.py` file first to understand dependencies and module metadata.