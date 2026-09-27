# Autopark

A [herdr](https://herdr.dev) plugin that parks idle Claude Code agents to free their memory.

Each Claude Code agent left open in a pane holds about 1.8 GB (Claude plus its MCP servers), even after days untouched. Autopark checks every 10 minutes and parks any agent idle for over an hour: it sends `/exit`, and the pane keeps a still view of the conversation until you press Enter, which runs `claude --resume <session>` again with the same flags and working directory.

Parked panes stay in the sidebar, tagged `parked` with a note like `4.1d idle, parked 23:34`. The pane shows the end of the transcript under a prompt box that says "Press Enter to resume". There is no scrollback, and the scroll wheel and arrow keys do nothing.

## Install

```sh
herdr plugin install <owner>/herdr-autopark
herdr plugin action invoke autopark.setup
```

For a local checkout, use `herdr plugin link <path>`. The loop starts with the herdr server, so after installing, restart the server or run `setsid -f python3 bin/autopark --daemon` once from the plugin directory.

Requirements: Linux (it reads `/proc`), Python 3.11+, herdr 0.7.5+ (tested on 0.9.0).

## Configure

Run `herdr plugin action invoke autopark.config` to open the config in `$EDITOR`. The file lives in `herdr plugin config-dir autopark`, and edits take effect on the next sweep.

| Key | Default | Meaning |
| --- | --- | --- |
| `idle_minutes` | `60` | Park after this long without a message or subagent activity |
| `interval_minutes` | `10` | How often the loop checks |
| `resume_grace_minutes` | `idle_minutes` | After you resume a pane, keep it awake at least this long |
| `exclude` | `[]` | Session ids or pane ids never to park |
| `extra_benign_children` | `[]` | Regexes for more child processes that are idle servers, not work |
| `show_transcript` | `true` | `false` shows a one-line banner instead of the transcript |
| `dry_run` | `false` | Log what would be parked, park nothing |

### Sidebar color

A plugin cannot edit your herdr config. To color parked panes, add these rows to `[ui.sidebar.agents] rows` in `~/.config/herdr/config.toml`, then run `herdr server reload-config`:

```toml
["state_icon", "tab", { token = "state_text", rules = [{ equals = "parked", fg = "#74c7ec", bold = true }] }],
[{ token = "$parked", fg = "#74c7ec", dim = true }],
```

## Actions

| Action | What it does |
| --- | --- |
| `autopark.setup` | Creates the config file and shows the sidebar rows |
| `autopark.config` | Opens the config in `$EDITOR` |
| `autopark.preview` | Shows each agent and why it would or would not be parked |
| `autopark.park-now` | Runs a sweep now |

## What counts as idle

Idle time is read from the timestamp of the last user or assistant message in `~/.claude/projects/*/<session>.jsonl`. Restarting herdr or Claude resets herdr's idle timer and the transcript's mtime but leaves that timestamp alone, so an agent idle before a restart counts as idle after it.

An agent is parked only when all of these hold:

- herdr reports it idle or done, and the pane is not focused
- no message and no subagent or workflow file has changed within `idle_minutes`
- no ScheduleWakeup, CronCreate or Monitor is pending
- Claude has no child process other than its own MCP or LSP servers (a shell, dev server or test run keeps it awake)
- the input box has no unsent draft
- it was not resumed from a park within `resume_grace_minutes`

Every check runs again just before `/exit`. If Claude is still alive 30 seconds after `/exit`, the pane is left alone.

Log: `~/.local/state/herdr-autopark/log`. Park records: `~/.local/state/herdr-autopark/parked/`.

## herdr quirks

The waiter is built around these:

- herdr accepts `pane report-agent` only from inside the pane and ignores it from anywhere else, without an error.
- A custom report that claims agent `claude` is refused in a pane where real Claude ran. Other labels work, so parked panes report as `parked`.
- A custom `--source` needs the `custom:` prefix.
