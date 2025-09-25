IMAGE_ODOO:=quay.io/opsway/odoo:ops19

all: build push

build:
	docker build --pull -t ${IMAGE_ODOO} .

push:
	docker push ${IMAGE_ODOO}

add-checks:
	pip3 install  --break-system-packages -r requirements-lint.txt && pre-commit install

remove-checks:
	pre-commit uninstall

update-content-list:
	python3 scripts/doc/update_readme_content_list.py


# Makefile — add a subtree AND record it in .gitmodules-subtree
# Usage:
#   make add-subtree NAME=a-lib PREFIX=vendor/a-lib REMOTE=mono REF=split/a-lib URL=https://github.com/owner/monorepo.git
# Optional:
#   SQUASH=true|false   (default: true)
#   MANIFEST=.gitmodules-subtree  (default)

SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -euo pipefail -c

MANIFEST ?= .gitmodules-subtree
SQUASH   ?= true

# Required params: NAME, PREFIX, REMOTE, REF
req = $(if $($1),,$(error Missing required variable '$1'))

.PHONY: add-subtree
add-subtree:
	$(call req,NAME)
	$(call req,PREFIX)
	$(call req,REMOTE)
	$(call req,REF)

	# Ensure we are in a git repo with full history
	git rev-parse --is-inside-work-tree >/dev/null

	# Create remote if missing and URL provided; else fail clearly
	if ! git remote | grep -qx '$(REMOTE)'; then
	  if [[ -n '$(URL)' ]]; then
	    echo ">> Adding remote '$(REMOTE)' -> $(URL)"
	    git remote add '$(REMOTE)' '$(URL)'
	  else
	    echo "ERROR: remote '$(REMOTE)' not found and no URL provided."
	    echo "       Pass URL=https://... or create the remote manually."
	    exit 1
	  fi
	fi

	echo ">> Fetching remote '$(REMOTE)'"
	git fetch '$(REMOTE)'

	# Check that PREFIX doesn't already host something conflicting
	if [[ -d '$(PREFIX)' ]] && [[ -n "$$(ls -A '$(PREFIX)' 2>/dev/null || true)" ]]; then
	  echo "ERROR: prefix path '$(PREFIX)' already exists and is non-empty."
	  echo "       Choose another PREFIX or remove existing contents."
	  exit 1
	fi

	# Decide squash option
	if [[ "$(SQUASH)" == "false" ]]; then
	  SQUASH_OPT=""
	else
	  SQUASH_OPT="--squash"
	fi

	echo ">> Adding subtree: $(REMOTE) $(REF)  ->  $(PREFIX)  $${SQUASH_OPT}"
	git subtree add --prefix='$(PREFIX)' '$(REMOTE)' '$(REF)' $${SQUASH_OPT}

	# Record/Update manifest entry
	echo ">> Updating manifest $(MANIFEST) for '$(NAME)'"
	git config -f '$(MANIFEST)' "subtree.$(NAME).prefix" '$(PREFIX)'
	git config -f '$(MANIFEST)' "subtree.$(NAME).remote" '$(REMOTE)'
	git config -f '$(MANIFEST)' "subtree.$(NAME).ref"    '$(REF)'
	git config -f '$(MANIFEST)' "subtree.$(NAME).squash" '$(SQUASH)'
	if [[ -n '$(URL)' ]]; then
	  git config -f '$(MANIFEST)' "subtree.$(NAME).remoteURL" '$(URL)'
	fi

	# Stage manifest if it changed (non-fatal if not tracked yet)
	git add -N '$(MANIFEST)' >/dev/null 2>&1 || true
	if ! git diff --quiet -- '$(MANIFEST)'; then
	  git add '$(MANIFEST)'
	  echo ">> Manifest $(MANIFEST) updated."
	else
	  echo ">> Manifest already up to date."
	fi

	echo "Done."

################################################################################
# Bonus: pull-all target reads the manifest and updates every subtree defined.
# You can add new subtrees by only appending to the manifest; no script changes.
################################################################################
.PHONY: pull-all
pull-all:
	[[ -f '$(MANIFEST)' ]] || { echo "No $(MANIFEST) file found."; exit 1; }
	mapfile -t names < <(git config -f '$(MANIFEST)' --name-only --get-regexp '^subtree\..*\.prefix' | sed -E 's/^subtree\.([^.]*)\.prefix/\1/')
	if [[ $${#names[@]} -eq 0 ]]; then
	  echo "No subtrees defined in $(MANIFEST)."; exit 0; fi

	git remote update
	for n in "$${names[@]}"; do
	  prefix=$$(git config -f '$(MANIFEST)' --get "subtree.$$n.prefix")
	  remote=$$(git config -f '$(MANIFEST)' --get "subtree.$$n.remote")
	  ref=$$(git    config -f '$(MANIFEST)' --get "subtree.$$n.ref")
	  squash=$$(git config -f '$(MANIFEST)' --get "subtree.$$n.squash" || echo "true")

	  [[ -d "$$prefix" ]] || { echo "Skip '$$n' (no directory at $$prefix yet)"; continue; }

	  echo ">> Pulling '$$n'  ($$remote $$ref -> $$prefix)"
	  if [[ "$$squash" == "false" ]]; then
	    git subtree pull --prefix="$$prefix" "$$remote" "$$ref"
	  else
	    git subtree pull --prefix="$$prefix" "$$remote" "$$ref" --squash
	  fi
	  echo
	done
	echo "All subtrees updated."

# Usage:
#   make rm-subtree NAME=a-lib
# It removes the subtree’s directory recorded in the manifest,
# drops the manifest section, and removes its remote if no longer referenced.

SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -euo pipefail -c

MANIFEST ?= .gitmodules-subtree

.PHONY: rm-subtree
rm-subtree:
	: $${NAME:?"Missing NAME=... (the manifest section name)"}
	[[ -f '$(MANIFEST)' ]] || { echo "No $(MANIFEST) found"; exit 1; }

	prefix=$$(git config -f '$(MANIFEST)' --get "subtree.$${NAME}.prefix" || true)
	remote=$$(git config -f '$(MANIFEST)' --get "subtree.$${NAME}.remote" || true)

	if [[ -z "$$prefix" ]]; then
	  echo "No subtree named '$$NAME' in $(MANIFEST)"; exit 1
	fi

	# Remove the directory if present
	if [[ -d "$$prefix" ]]; then
	  echo ">> Removing directory '$$prefix'"
	  git rm -r "$$prefix"
	else
	  echo ">> Directory '$$prefix' not found; skipping git rm"
	fi

	# Remove the manifest section
	echo ">> Removing '$$NAME' from $(MANIFEST)"
	git config -f '$(MANIFEST)' --remove-section "subtree.$${NAME}" || true
	git add -A '$(MANIFEST)' || true

	# Commit
	if ! git diff --cached --quiet; then
	  git commit -m "chore(subtree): remove $$NAME ($$prefix)"
	else
	  echo ">> Nothing to commit"
	fi

	# If no other subtrees reference the same remote, remove it
	if [[ -n "$$remote" ]]; then
	  used_elsewhere=$$(git config -f '$(MANIFEST)' --get-regexp '^subtree\..*\.remote$$' 2>/dev/null | grep -v "subtree.$$NAME.remote" | awk '{print $$3}' | grep -Fx "$$remote" || true)
	  if [[ -z "$$used_elsewhere" ]]; then
	    if git remote | grep -qx "$$remote"; then
	      echo ">> Removing unused remote '$$remote'"
	      git remote remove "$$remote"
	    fi
	  else
	    echo ">> Remote '$$remote' still used by other subtrees; keeping it"
	  fi
	fi

	echo "Done."
