#!/usr/bin/env bash
# File a sim-prod audit GitHub issue for Aspen to review.
# Captain + Grok last-word: run this AFTER audit, not from an unaudited heartbeat.
set -euo pipefail

REPO="${SANDBOX_GH_REPO:-AbsolutionAI/AspenOS}"
TITLE=""
BODY=""
BODY_FILE=""
PAPERCLIP_ISSUE=""
LINEAR_ID=""
SHA=""

usage() {
  cat <<EOF
Usage: $0 --title <text> (--body <text> | --body-file <path>) [options]

  --title TEXT          Issue title (prefix sim-prod: if missing)
  --body TEXT           Issue body markdown
  --body-file PATH      Read body from file
  --paperclip ID        ASP / UUID to mention
  --linear ID           BEL-N
  --sha SHA             Sandbox worktree SHA
  --repo OWNER/NAME     Default AbsolutionAI/AspenOS
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --title) TITLE="$2"; shift 2 ;;
    --body) BODY="$2"; shift 2 ;;
    --body-file) BODY_FILE="$2"; shift 2 ;;
    --paperclip) PAPERCLIP_ISSUE="$2"; shift 2 ;;
    --linear) LINEAR_ID="$2"; shift 2 ;;
    --sha) SHA="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$TITLE" ]]; then
  echo "--title required" >&2
  exit 2
fi
if [[ -z "$BODY" && -z "$BODY_FILE" ]]; then
  echo "--body or --body-file required" >&2
  exit 2
fi
if [[ -n "$BODY_FILE" ]]; then
  BODY="$(cat "$BODY_FILE")"
fi

case "$TITLE" in
  sim-prod:*) ;;
  *) TITLE="sim-prod: $TITLE" ;;
esac

meta=""
[[ -n "$PAPERCLIP_ISSUE" ]] && meta+="- Paperclip: ${PAPERCLIP_ISSUE}"$'\n'
[[ -n "$LINEAR_ID" ]] && meta+="- Linear: ${LINEAR_ID}"$'\n'
[[ -n "$SHA" ]] && meta+="- Worktree SHA: ${SHA}"$'\n'
if [[ -n "$meta" ]]; then
  BODY="${BODY}"$'\n\n'"## Tracker"$'\n'"${meta}"
fi

# Labels must exist (created at sandbox standup).
exec gh issue create -R "$REPO" \
  --title "$TITLE" \
  --body "$BODY" \
  --label sandbox-audit \
  --label grok-build \
  --label sim-prod \
  --label needs-aspen-review
