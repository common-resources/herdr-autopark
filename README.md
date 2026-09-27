<div align="center">

# Autopark

**Idle Claude Code agents give their RAM back. The conversation stays on screen, and Enter resumes it.**

A plugin for [herdr](https://herdr.dev), the terminal workspace for coding agents.

[![License: MIT](https://img.shields.io/badge/license-MIT-74c7ec)](LICENSE)
![herdr 0.7.5+](https://img.shields.io/badge/herdr-0.7.5%2B-6E56CF)
![platform: linux](https://img.shields.io/badge/platform-linux-lightgrey)
![python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)

<img src="docs/parked.png" alt="A herdr window: the sidebar lists a parked agent in blue with the note '4.1d idle, parked 23:34', and its pane shows the last part of the conversation above a 'Press Enter to resume' prompt" width="860">

</div>

## Why

An agent you left open three days ago still holds about **1.8 GB**: Claude itself plus every MCP server it started. Keep ten tabs open and that adds up to a sizeable share of your machine, all spent on conversations you might come back to.

Autopark checks every ten minutes and parks each agent that has been quiet for an hour. The process exits and its memory is freed. The pane stays put, with the conversation still showing, and one keypress brings it back on the same session, with the same flags and in the same directory.

## Install

```sh
herdr plugin install 0xKrauser/herdr-autopark
herdr plugin action invoke autopark.setup
```

The background loop starts with the herdr server, so restart herdr once after installing. `autopark.setup` creates the config file and shows the two sidebar rows that color parked panes.

To hack on it, clone the repo and use `herdr plugin link <path>`, which runs the plugin from your checkout.

## What you get

- **A still view of the conversation.** A parked pane shows the end of the transcript, drawn like Claude's screen, under a prompt box. It has no scrollback, and the wheel and arrow keys do nothing, so a stray scroll can't write into it.
- **It stays in the sidebar.** Parked panes keep their place, tagged `parked` and colored, with a note such as `4.1d idle, parked 23:34`.
- **Resume with Enter.** You get `claude --resume <session>` with the flags you started it with. Ctrl+C drops to a plain shell instead.
- **Careful about what counts as idle.** When anything suggests the agent is still busy, it is left alone (see below).
- **Settings live in one file** and apply on the next check.

## Configure

```sh
herdr plugin action invoke autopark.config   # opens the config in $EDITOR
```

| Key | Default | What it does |
| --- | --- | --- |
| `idle_minutes` | `60` | Park after this long without a message or subagent activity |
| `interval_minutes` | `10` | How often to check |
| `resume_grace_minutes` | same as `idle_minutes` | After you resume a pane, keep it awake at least this long |
| `exclude` | `[]` | Session ids or pane ids never to park |
| `extra_benign_children` | `[]` | Regexes for more child processes that are idle servers, not work |
| `show_transcript` | `true` | Set `false` for a one-line banner instead of the conversation |
| `dry_run` | `false` | Log what would be parked, park nothing |

The file lives in `herdr plugin config-dir autopark`. [`config.example.toml`](config.example.toml) has every key with a comment.

### Sidebar colors

A plugin can't edit your herdr config, so add these to `[ui.sidebar.agents] rows` in `~/.config/herdr/config.toml`, then run `herdr server reload-config`:

```toml
["state_icon", "tab", { token = "state_text", rules = [{ equals = "parked", fg = "#74c7ec", bold = true }] }],
[{ token = "$parked", fg = "#74c7ec", dim = true }],
```

## Actions

| Action | What it does |
| --- | --- |
| `autopark.setup` | Creates the config file and shows the sidebar rows |
| `autopark.config` | Opens the config in `$EDITOR` |
| `autopark.preview` | Lists every agent and why it would or would not be parked |
| `autopark.park-now` | Runs a check now instead of waiting for the next one |

Bind any of them to a key with a `[[keys.command]]` entry of `type = "plugin_action"`.

## When an agent counts as idle

Autopark reads the timestamp of the last message from you or Claude in the session transcript (`~/.claude/projects/*/<session>.jsonl`). Restarting herdr or Claude resets herdr's idle timer and touches the file, but that timestamp stays the same, so an agent that was idle before a restart is still idle after it.

It parks an agent only when all of these are true:

- herdr reports it idle or done, and you're not focused on it
- nothing was said, and no subagent or workflow file changed, within `idle_minutes`
- no `/loop` wakeup, cron job or monitor is pending
- Claude has no child process other than its own MCP and language servers, so a shell, dev server or test run keeps it awake
- the input box has no unsent draft
- you didn't resume it from a park within `resume_grace_minutes`

Every check runs again right before `/exit` is sent. If Claude is still alive 30 seconds after `/exit`, the pane is left alone.

To see what it's doing, look at `~/.local/state/herdr-autopark/log`, or run `autopark.preview`.

## Notes on herdr

Some herdr behavior shaped the design, in case you build something similar:

- herdr accepts `pane report-agent` only from inside the pane, and silently ignores it from anywhere else. That's why the waiting script in the pane registers itself.
- A custom report that claims agent `claude` is refused in a pane where the real Claude integration ran. Other labels work, which is why parked panes report as `parked`.
- A custom `--source` needs the `custom:` prefix.

## License

[MIT](LICENSE) © 2026 Johannes Krauser
