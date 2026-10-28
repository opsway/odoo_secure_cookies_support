.PHONY: lint catalog configure-repository adoption-docs licences licence-tests licence-inventory

lint:
	pre-commit run --all-files

catalog:
	python3 scripts/update_readme.py

configure-repository:
	./scripts/configure_repository.sh

adoption-docs:
	python3 scripts/create_adoption_docs.py

# Offline mode, as pre-commit runs it: no network, no pip, curated maps.
licences:
	python3 scripts/check_licenses.py

# The gate's own tests. Offline and stdlib only, so they run anywhere the gate
# does -- including the odoo container, which has no pytest.
licence-tests:
	python3 -m unittest discover -s tests

# Resolved mode, for a release record. Needs network access and installs
# nothing. pip >= 22.2 for --dry-run --report, and >= 25.0 to be useful: earlier
# pips drop the PEP 639 License-Expression field, so wheels that declare their
# licence that way come back looking unlicensed. See docs/repository.md,
# "Before a release".
#
# ADDONS_PATH is required rather than optional: without it the Odoo side falls
# back to KNOWN_LICENSES, stops walking external dependencies transitively, and
# cannot notice an upstream manifest that changed licence -- so the record
# attached to a release would be weaker than the one CI already rejects on.
licence-inventory:
	@test -n "$(ADDONS_PATH)" || { \
	  echo "ADDONS_PATH is required: a release record has to resolve real" >&2; \
	  echo "manifests, not the offline map. Point it at Odoo core and every" >&2; \
	  echo "pinned OCA source, as the CI job does:" >&2; \
	  echo "  make licence-inventory ADDONS_PATH=/path/odoo/addons,/path/server-auth" >&2; \
	  exit 1; }
	python3 scripts/check_licenses.py \
		--addons-path="$(ADDONS_PATH)" \
		--resolve-python \
		--inventory licence-inventory.json
