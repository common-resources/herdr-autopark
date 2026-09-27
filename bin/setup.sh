#!/usr/bin/env bash
# Setup pane: create the config from the example if missing, then show where it lives and the
# sidebar rows to add. With --edit, open the config in $EDITOR instead.
set -uo pipefail
root=$(dirname "$(dirname "$(realpath "${BASH_SOURCE[0]}")")")
dir=$("${HERDR_BIN_PATH:-herdr}" plugin config-dir autopark 2>/dev/null) || dir=$HOME/.config/herdr/plugins/config/autopark
mkdir -p "$dir"
cfg=$dir/config.toml
[[ -f $cfg ]] || cp "$root/config.example.toml" "$cfg"
if [[ ${1:-} == --edit ]]; then
  exec "${VISUAL:-${EDITOR:-nano}}" "$cfg"
fi
cat <<MSG

  Autopark is running: idle Claude agents are parked on a timer.

  Config:  $cfg
           (edit with the "Autopark: edit config" action; changes apply on the next sweep)
  Log:     ${XDG_STATE_HOME:-$HOME/.local/state}/herdr-autopark/log

  Sidebar: parked panes report the state label "parked" and a \$parked note
  ("4.1d idle, parked 23:34"). To color them, put these into [ui.sidebar.agents] rows
  in ~/.config/herdr/config.toml, then run: herdr server reload-config

    ["state_icon", "tab", { token = "state_text", rules = [{ equals = "parked", fg = "#74c7ec", bold = true }] }],
    [{ token = "\$parked", fg = "#74c7ec", dim = true }],

  Press Enter to close.
MSG
read -r _
