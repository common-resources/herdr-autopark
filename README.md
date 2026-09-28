<div align="center">

# Autopark

**Idle coding agents give their RAM back. The conversation stays on screen, and Enter resumes it.**

A plugin for [herdr](https://herdr.dev), the terminal workspace for coding agents.

[![GitHub stars](https://img.shields.io/github/stars/common-resources/herdr-autopark?style=flat&logo=github&color=f9e2af)](https://github.com/common-resources/herdr-autopark/stargazers)
[![License: MIT](https://img.shields.io/badge/license-MIT-74c7ec)](LICENSE)
![herdr 0.7.5+](https://img.shields.io/badge/herdr-0.7.5%2B-6E56CF)
![platform: linux, macOS planned](https://img.shields.io/badge/platform-linux%20%C2%B7%20macOS%20planned-lightgrey)
![python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)

<img src="docs/parked.png" alt="A herdr window: the sidebar lists a parked agent in blue with the note '4.1d idle, parked 23:34', and its pane shows the last part of the conversation above a 'Press Enter to resume' prompt" width="860">

</div>

## Why

An agent you left open three days ago still holds its memory: a Claude Code session with its MCP servers sits around 1.8 GB. Keep ten tabs open and that adds up to a sizeable share of your machine, all spent on conversations you might come back to.

Autopark checks every ten minutes and parks each agent that has been quiet for an hour. The process exits and its memory is freed. The pane stays put, with the conversation still showing, and one keypress brings it back on the same session, with the same flags and in the same directory.

## Install

```sh
herdr plugin install common-resources/herdr-autopark
herdr plugin action invoke autopark.setup
```

The background loop starts with the herdr server, so restart herdr once after installing. `autopark.setup` creates the config file and shows the two sidebar rows that color parked panes.

To hack on it, clone the repo and use `herdr plugin link <path>`, which runs the plugin from your checkout.

## Supported agents

| Agent | herdr kind | Status | Session history | Resumes with |
| --- | --- | --- | --- | --- |
| [Claude Code](https://claude.com/claude-code) | `claude` | ✅ supported | `~/.claude/projects/*/<session>.jsonl` | `claude <flags> --resume <id>` |
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | `hermes` | ✅ supported | `~/.hermes/state.db` | `hermes <flags> --resume <id>` |
| [Codex CLI](https://github.com/openai/codex) | `codex` | 🗺️ next | | |
| [OpenCode](https://opencode.ai) | `opencode` | 🗺️ next | | |
| [Gemini CLI](https://github.com/google-gemini/gemini-cli) | `gemini` | 🗺️ next | | |
| [Pi](https://github.com/badlogic/pi-mono) | `pi` | 🗺️ next | | |
| Copilot CLI, Cursor Agent, Amp, Droid, Kimi, Qwen Code, Grok and the other kinds herdr detects | | 💭 later | | |

Agents without an adapter are left alone. Each one is a small class in [`bin/harnesses.py`](bin/harnesses.py) that answers five questions:

1. What is its process called?
2. Which session is it on? (herdr often reports this; otherwise the adapter looks it up.)
3. When was it last active, and is anything still pending, like a scheduled wakeup or a background job?
4. What does the conversation look like? (Only used when the screen capture is missing.)
5. Which command resumes it?

The rows marked "next" are the ones worth doing first. Each needs someone to check where the agent keeps its sessions and how it resumes one, and then a real park and resume in herdr. Pull requests are welcome, and so are issues that just say "I'd use this with X".

## What you get

- A still view of the conversation. Right before parking, autopark captures the agent's own screen and replays it in the pane, with a prompt box at the bottom. If the capture fails, it draws the conversation from the session history instead. It has no scrollback, and the wheel and arrow keys do nothing, so a stray scroll can't write into it.
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
| `stop_idle_subagents` | `true` | When Claude asks to confirm exit because background subagents are open, stop them if every one is a subagent; anything else (a shell, a workflow) cancels the park |
| `show_transcript` | `true` | Set `false` for a one-line banner instead of the captured screen |
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

Every check runs again right before `/exit` is sent. If Claude asks to confirm exit and only idle subagents are listed, autopark picks "Exit and stop tasks"; otherwise it cancels and waits for new activity before trying again. If the agent is still alive 30 seconds after `/exit`, the pane is left alone.

To see what it's doing, look at `~/.local/state/herdr-autopark/log`, or run `autopark.preview`.

## Notes on herdr

Some herdr behavior shaped the design, in case you build something similar:

- herdr accepts `pane report-agent` only from inside the pane, and silently ignores it from anywhere else. That's why the waiting script in the pane registers itself.
- A custom report that claims agent `claude` is refused in a pane where the real Claude integration ran. Other labels work, which is why parked panes report as `parked`.
- A custom `--source` needs the `custom:` prefix.
- herdr's Hermes integration may not report a session id, so the Hermes adapter looks it up in `state.db` (by working directory and process start, or the `--resume` argument).
- Hermes leaves a pasted line unsent, so `/exit` is typed and followed by Enter rather than pasted.

## Roadmap

These are planned, roughly in order. None of them are built yet.

**macOS**

- [ ] Replace the `/proc` reads (finding the agent process, its children, working directory and start time) with `ps` and `lsof`
- [ ] Declare `macos` in the plugin manifest once a real park and resume has been tested on a Mac

**More agents**

- [ ] Codex, OpenCode, Gemini CLI and Pi adapters (see the table above)
- [ ] A short guide in the repo for writing an adapter, with a checklist for the live park-and-resume test

**Quality of life**

- [ ] Show how much memory each park freed, in the log and in the parked pane's note (`1.9 GB freed`)
- [ ] `autopark.resume-all` action, and `autopark.park` to park the focused pane right away
- [ ] Optionally resume when the pane gets focus, instead of waiting for Enter
- [ ] Per-workspace idle thresholds, so a scratch workspace can park sooner than the main one
- [ ] Redraw from the session history when the pane is resized to a very different size, instead of cropping the capture
- [ ] Delete park records and screen captures once their pane is resumed or closed
- [ ] Optional herdr toast when something is parked
- [ ] Cap how long subagents can keep an agent awake (`max_subagent_minutes`): past it, park anyway and stop them through the exit dialog, and show the open subagents in `autopark.preview`

**Upkeep**

- [ ] Warn in `autopark.setup` when an agent's herdr integration is missing, since that is where the session id and state come from

## Development

```sh
make check   # ruff, shellcheck, shfmt and the self-check; this is what CI runs
make fmt     # apply ruff and shfmt fixes
```

The only requirement is [uv](https://docs.astral.sh/uv/): the linters run through `uvx`, and the self-check (`bin/test_autopark.py`) is plain Python that also runs under pytest.

## Like it?

If Autopark gave you back a few gigabytes, please [star the repo](https://github.com/common-resources/herdr-autopark) ⭐. Stars help other herdr users find it, and they tell me it's worth adding more (macOS support, more agents). Issues and pull requests are welcome too.

<a href="https://star-history.com/#common-resources/herdr-autopark&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=common-resources/herdr-autopark&type=Date&theme=dark" />
    <img alt="Star history chart" src="https://api.star-history.com/svg?repos=common-resources/herdr-autopark&type=Date" width="600" />
  </picture>
</a>

## License

[MIT](LICENSE) © 2026 Johannes Krauser
