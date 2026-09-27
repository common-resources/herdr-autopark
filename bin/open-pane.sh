#!/usr/bin/env bash
# Action helper: open one of this plugin's panes as an overlay.
set -euo pipefail
exec "${HERDR_BIN_PATH:-herdr}" plugin pane open --plugin autopark --entrypoint "$1" --placement overlay --focus
