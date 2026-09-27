<div align="center">

# Autopark

**Idle coding agents give their RAM back. The conversation stays on screen, and Enter resumes it.**

A plugin for [herdr](https://herdr.dev), the terminal workspace for coding agents.

[![GitHub stars](https://img.shields.io/github/stars/0xKrauser/herdr-autopark?style=flat&logo=github&color=f9e2af)](https://github.com/0xKrauser/herdr-autopark/stargazers)
[![License: MIT](https://img.shields.io/badge/license-MIT-74c7ec)](LICENSE)
![herdr 0.7.5+](https://img.shields.io/badge/herdr-0.7.5%2B-6E56CF)
![platform: linux](https://img.shields.io/badge/platform-linux-lightgrey)
![python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)

<img src="docs/parked.png" alt="A herdr window: the sidebar lists a parked agent in blue with the note '4.1d idle, parked 23:34', and its pane shows the last part of the conversation above a 'Press Enter to resume' prompt" width="860">

</div>

## Why

An agent you left open three days ago still holds its memory: a Claude Code session with its MCP servers sits around 1.8 GB. Keep ten tabs open and that adds up to a sizeable share of your machine, all spent on conversations you might come back to.

Autopark checks every ten minutes and parks each agent that has been quiet for an hour. The process exits and its memory is freed. The pane stays put, with the conversation still showing, and one keypress brings it back on the same session, with the same flags and in the same directory.

## Install

```sh
herdr plugin install 0xKrauser/herdr-autopark
herdr plugin action invoke autopark.setup
```

The background loop starts with the herdr server, so restart herdr once after installing. `autopark.setup` creates the config file and shows the two sidebar rows that color parked panes.

To hack on it, clone the repo and use `herdr plugin link <path>`, which runs the plugin from your checkout.

## Supported agents

| Agent | herdr kind | Session history | Resumes with |
| --- | --- | --- | --- |
| [Claude Code](https://claude.com/claude-code) | `claude` | `~/.claude/projects/*/<session>.jsonl` | `claude <flags> --resume <id>` |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | `hermes` | `~/.hermes/state.db` | `hermes <flags> --resume <id>` |

Other agents herdr detects are left alone. Each harness is one small class in [`bin/harnesses.py`](bin/harnesses.py) that answers five questions: its process name, its session id, when it was last active (and whether anything is still pending), its conversation for the parked view, and the command that resumes it. Pull requests for Codex, OpenCode, Gemini CLI, Pi and the rest are very welcome.

## What you get

- A still view of the conversation. A parked pane shows the end of the transcript, drawn the way the agent draws it, under a prompt box. It has no scrollback, and the wheel and arrow keys do nothing, so a stray scroll can't write into it.
- It stays in the sidebar. Parked panes keep their place, tagged `parked` and colored, with a note such as `4.1d idle, parked 23:34`.
- Resume with Enter. The agent comes back on the same session with the flags you started it with. Ctrl+C drops to a plain shell instead.
- Careful about what counts as idle. When anything suggests the agent is still busy, it is left alone (see below).
- Settings live in one file and apply on the next check.

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

Autopark reads the timestamp of the last message from you or the agent in its own session history. Restarting herdr or the agent resets herdr's idle timer, but that timestamp stays the same, so an agent that was idle before a restart is still idle after it.

It parks an agent only when all of these are true:

- herdr reports it idle or done, and you're not focused on it
- nothing was said, and no subagent or workflow file changed, within `idle_minutes`
- nothing is pending: for Claude a `/loop` wakeup, cron job, monitor or subagent; for Hermes a delegated task or background process
- the agent has no child process other than its own MCP and language servers, so a shell, dev server or test run keeps it awake
- the input box has no unsent draft
- you didn't resume it from a park within `resume_grace_minutes`

Every check runs again right before `/exit` is sent. If the agent is still alive 30 seconds after `/exit`, the pane is left alone.

To see what it's doing, look at `~/.local/state/herdr-autopark/log`, or run `autopark.preview`.

## Notes on herdr

Some herdr behavior shaped the design, in case you build something similar:

- herdr accepts `pane report-agent` only from inside the pane, and silently ignores it from anywhere else. That's why the waiting script in the pane registers itself.
- A custom report that claims agent `claude` is refused in a pane where the real Claude integration ran. Other labels work, which is why parked panes report as `parked`.
- A custom `--source` needs the `custom:` prefix.
- herdr's Hermes integration may not report a session id, so the Hermes adapter looks it up in `state.db` (by working directory and process start, or the `--resume` argument).
- Hermes leaves a pasted line unsent, so `/exit` is typed and followed by Enter rather than pasted.

## Like it?

If Autopark gave you back a few gigabytes, please [star the repo](https://github.com/0xKrauser/herdr-autopark) ⭐. Stars help other herdr users find it, and they tell me it's worth adding more (more agents, macOS support). Issues and pull requests are welcome too.

<a href="https://star-history.com/#0xKrauser/herdr-autopark&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=0xKrauser/herdr-autopark&type=Date&theme=dark" />
    <img alt="Star history chart" src="https://api.star-history.com/svg?repos=0xKrauser/herdr-autopark&type=Date" width="600" />
  </picture>
</a>

## License

[MIT](LICENSE) © 2026 Johannes Krauser
