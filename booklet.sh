#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ubuntu/pco-autoclaw"
CLI="$ROOT/booklet_cli.py"
FORMATTER="$ROOT/booklet/response_formatter.py"
REQUEST_ROUTER="$ROOT/booklet/request_router.py"

run_and_format_reply() {
  local output
  local status

  set +e
  output="$("$@")"
  status=$?
  set -e

  if [[ $status -eq 0 || $status -eq 1 ]]; then
    printf '%s\n' "$output" | python3 "$FORMATTER"
    return $status
  fi

  printf '%s\n' "$output"
  return $status
}

cmd="${1:-}"
shift || true

case "$cmd" in
  preview)
    date="${1:?usage: booklet.sh preview YYYY-MM-DD [template_family]}"
    family="${2:-ordinary_time}"
    python3 "$CLI" preview-service --date "$date" --template-family "$family"
    ;;
  preview-no-pco)
    date="${1:?usage: booklet.sh preview-no-pco YYYY-MM-DD [template_family]}"
    family="${2:-ordinary_time}"
    python3 "$CLI" preview-service --date "$date" --template-family "$family" --skip-pco
    ;;
  auth-google)
    python3 "$CLI" auth-google
    ;;
  auth-google-finish)
    if [[ "${1:-}" == "--response-url" ]]; then
      response_url="${2:?usage: booklet.sh auth-google-finish --response-url <url>}"
      python3 "$CLI" auth-google-finish --response-url "$response_url"
    else
      state="${1:?usage: booklet.sh auth-google-finish <state> <code>}"
      code="${2:?usage: booklet.sh auth-google-finish <state> <code>}"
      python3 "$CLI" auth-google-finish --state "$state" --code "$code"
    fi
    ;;
  copy-template)
    date="${1:?usage: booklet.sh copy-template YYYY-MM-DD [template_family]}"
    family="${2:-ordinary_time}"
    python3 "$CLI" copy-template --date "$date" --template-family "$family"
    ;;
  render-booklet-plan)
    date="${1:?usage: booklet.sh render-booklet-plan YYYY-MM-DD [template_family]}"
    family="${2:-ordinary_time}"
    python3 "$CLI" render-booklet-plan --date "$date" --template-family "$family"
    ;;
  generate-booklet)
    date="${1:?usage: booklet.sh generate-booklet YYYY-MM-DD [template_family] [extra args...]}"
    family="${2:-ordinary_time}"
    shift 2 || true
    python3 "$CLI" generate-booklet --date "$date" --template-family "$family" "$@"
    ;;
  update-booklet)
    date="${1:?usage: booklet.sh update-booklet YYYY-MM-DD [template_family] [extra args...]}"
    family="${2:-ordinary_time}"
    shift 2 || true
    python3 "$CLI" update-booklet --date "$date" --template-family "$family" "$@"
    ;;
  get-booklet-link)
    date="${1:?usage: booklet.sh get-booklet-link YYYY-MM-DD}"
    python3 "$CLI" get-booklet-link --date "$date"
    ;;
  attach-booklet-pdf)
    date="${1:?usage: booklet.sh attach-booklet-pdf YYYY-MM-DD [extra args...]}"
    shift || true
    python3 "$CLI" attach-booklet-pdf --date "$date" "$@"
    ;;
  attach-booklet-pdf-reply)
    date="${1:?usage: booklet.sh attach-booklet-pdf-reply YYYY-MM-DD [extra args...]}"
    shift || true
    run_and_format_reply python3 "$CLI" attach-booklet-pdf --date "$date" "$@"
    ;;
  make)
    date="${1:?usage: booklet.sh make YYYY-MM-DD [template_family] [extra args...]}"
    family="${2:-ordinary_time}"
    shift 2 || true
    python3 "$CLI" generate-booklet --date "$date" --template-family "$family" --attach-pdf-to-pco "$@"
    ;;
  make-reply)
    date="${1:?usage: booklet.sh make-reply YYYY-MM-DD [template_family] [extra args...]}"
    family="${2:-ordinary_time}"
    shift 2 || true
    run_and_format_reply python3 "$CLI" generate-booklet --date "$date" --template-family "$family" --attach-pdf-to-pco "$@"
    ;;
  update)
    date="${1:?usage: booklet.sh update YYYY-MM-DD [template_family] [extra args...]}"
    family="${2:-ordinary_time}"
    shift 2 || true
    python3 "$CLI" update-booklet --date "$date" --template-family "$family" --attach-pdf-to-pco "$@"
    ;;
  update-reply)
    date="${1:?usage: booklet.sh update-reply YYYY-MM-DD [template_family] [extra args...]}"
    family="${2:-ordinary_time}"
    shift 2 || true
    run_and_format_reply python3 "$CLI" update-booklet --date "$date" --template-family "$family" --attach-pdf-to-pco "$@"
    ;;
  link)
    date="${1:?usage: booklet.sh link YYYY-MM-DD}"
    python3 "$CLI" get-booklet-link --date "$date"
    ;;
  link-reply)
    date="${1:?usage: booklet.sh link-reply YYYY-MM-DD}"
    run_and_format_reply python3 "$CLI" get-booklet-link --date "$date"
    ;;
  request-reply)
    action="${1:?usage: booklet.sh request-reply <make|update|link> <sunday reference...>}"
    shift
    python3 "$REQUEST_ROUTER" "$action" "$@"
    ;;
  route-reply)
    python3 "$REQUEST_ROUTER" "$@"
    ;;
  *)
    cat <<'EOF'
booklet.sh — Sunday booklet helper

Usage:
  booklet.sh preview YYYY-MM-DD [template_family]
  booklet.sh preview-no-pco YYYY-MM-DD [template_family]
  booklet.sh auth-google
  booklet.sh auth-google-finish <state> <code>
  booklet.sh auth-google-finish --response-url <redirected-localhost-url>
  booklet.sh copy-template YYYY-MM-DD [template_family]
  booklet.sh render-booklet-plan YYYY-MM-DD [template_family]
  booklet.sh generate-booklet YYYY-MM-DD [template_family] [extra args...]
  booklet.sh update-booklet YYYY-MM-DD [template_family] [extra args...]
  booklet.sh get-booklet-link YYYY-MM-DD
  booklet.sh attach-booklet-pdf YYYY-MM-DD [extra args...]
  booklet.sh attach-booklet-pdf-reply YYYY-MM-DD [extra args...]
  booklet.sh make YYYY-MM-DD [template_family] [extra args...]
  booklet.sh make-reply YYYY-MM-DD [template_family] [extra args...]
  booklet.sh update YYYY-MM-DD [template_family] [extra args...]
  booklet.sh update-reply YYYY-MM-DD [template_family] [extra args...]
  booklet.sh link YYYY-MM-DD
  booklet.sh link-reply YYYY-MM-DD
  booklet.sh request-reply <make|update|link> <sunday reference...>
  booklet.sh route-reply <raw booklet request...>
EOF
    exit 1
    ;;
esac
