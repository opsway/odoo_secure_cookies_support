#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="odoo_secure_cookies_support"
TECH_LEAD="@opsway/tech-leads"
VERSION_BRANCHES=("18.0" "17.0" "19.0" )

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v gh >/dev/null 2>&1 || fail "GitHub CLI (gh) is not installed. Install it from https://cli.github.com/ or configure the repository manually in GitHub Settings, then rerun this command."
gh auth status >/dev/null 2>&1 || fail "gh is installed but not authenticated. Run 'gh auth login' with an account allowed to administer this OpsWay repository, then rerun."

REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+/${REPO_NAME})(\.git)?$ ]]; then
  REPO="${BASH_REMATCH[1]}"
else
  REPO="opsway/${REPO_NAME}"
  printf 'Could not infer repository from origin; assuming %s\n' "$REPO"
fi

printf 'Configuring %s\n' "$REPO"

gh api --method PATCH "repos/${REPO}" \
  -f description='Secure and SameSite flags on the cookies Odoo sets' \
  -F has_wiki=false \
  -F has_projects=false \
  -F delete_branch_on_merge=true \
  -F allow_merge_commit=true \
  -F allow_squash_merge=true \
  -F allow_rebase_merge=true \
  -f merge_commit_title=PR_TITLE \
  -f merge_commit_message=PR_BODY >/dev/null

TEAM_ORG="opsway"

grant_team() {
  local team="$1" permission="$2"
  if ! gh api "orgs/${TEAM_ORG}/teams/${team}" >/dev/null 2>&1; then
    printf 'Skipping %s access: team %s/%s not found. Create it, then rerun.\n' "$permission" "$TEAM_ORG" "$team"
    return 0
  fi
  if gh api --method PUT "orgs/${TEAM_ORG}/teams/${team}/repos/${REPO}" -f permission="$permission" >/dev/null 2>&1; then
    printf 'Granted %s access to %s/%s\n' "$permission" "$TEAM_ORG" "$team"
  else
    printf 'Could not grant %s access to %s/%s; organization owner or repository admin rights are required.\n' "$permission" "$TEAM_ORG" "$team"
  fi
}

REPO_OWNER="${REPO%%/*}"
if [[ "$REPO_OWNER" == "$TEAM_ORG" ]]; then
  grant_team lumirang push
  grant_team tech-leads admin
else
  printf 'Repository owner %s is not %s; skipping team access grants.\n' "$REPO_OWNER" "$TEAM_ORG"
fi

for BRANCH in "${VERSION_BRANCHES[@]}"; do
  if ! git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null 2>&1; then
    printf 'Skipping ruleset for missing remote branch %s (create/push it first).\n' "$BRANCH"
    continue
  fi

  RULESET_NAME="Odoo ${BRANCH} version branch"
  EXISTING_ID="$(gh api "repos/${REPO}/rulesets" --jq ".[] | select(.name == \"${RULESET_NAME}\") | .id" | head -n1 || true)"

  BODY="$(mktemp)"
  cat > "$BODY" <<JSON
{
  "name": "${RULESET_NAME}",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["refs/heads/${BRANCH}"],
      "exclude": []
    }
  },
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
      "type": "required_status_checks",
      "parameters": {
        "do_not_enforce_on_create": true,
        "required_status_checks": [{"context": "CI gate"}],
        "strict_required_status_checks_policy": false
      }
    },
    {
      "type": "pull_request",
      "parameters": {
        "allowed_merge_methods": ["merge", "squash", "rebase"],
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_approving_review_count": 0,
        "required_review_thread_resolution": false
      }
    }
  ],
  "bypass_actors": []
}
JSON

  if [[ -n "$EXISTING_ID" ]]; then
    gh api --method PUT "repos/${REPO}/rulesets/${EXISTING_ID}" --input "$BODY" >/dev/null
    printf 'Updated ruleset for %s\n' "$BRANCH"
  else
    gh api --method POST "repos/${REPO}/rulesets" --input "$BODY" >/dev/null
    printf 'Created ruleset for %s\n' "$BRANCH"
  fi
  rm -f "$BODY"
done

DEFAULT="${VERSION_BRANCHES[0]}"
if git ls-remote --exit-code --heads origin "$DEFAULT" >/dev/null 2>&1; then
  gh api --method PATCH "repos/${REPO}" -f default_branch="$DEFAULT" >/dev/null
  printf 'Default branch: %s\n' "$DEFAULT"
fi

printf 'Repository provisioning complete. CODEOWNERS is %s; branch rules require PRs and CI gate, with no approval; merge, squash and rebase merges are all allowed.\n' "$TECH_LEAD"
