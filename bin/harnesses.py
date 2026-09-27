"""Per-harness knowledge: how to find a session's history, judge its last activity, redraw it,
and relaunch it. The sweep in `autopark` and the view in `parked-view` are harness-agnostic.

An adapter answers five questions for one herdr agent kind:
  procs          process names (/proc/<pid>/comm) of the harness
  session_id     the session to resume (herdr's report, else the adapter's own lookup)
  activity       last real message time, and anything still pending (wakeups, background jobs)
  blocks         the conversation as display blocks, oldest first, for the parked view
  relaunch       the argv that resumes the session
Display blocks: ('user', text) ('assistant', text) ('tool', name, arg) ('result', first_line).
"""
import datetime as dt
import glob
import json
import os
import sqlite3
import time

HOME = os.path.expanduser('~')
TAIL_BYTES = 3_000_000


def _strip_flags(args, with_value, bare, optional_value=()):
    """Drop resume-style flags so the adapter can append its own. `optional_value` flags eat the
    next arg only when it is not another flag."""
    out, i = [], 0
    while i < len(args):
        x = args[i]
        if x in with_value:
            i += 2
            continue
        if x in optional_value:
            i += 2 if i + 1 < len(args) and not args[i + 1].startswith('-') else 1
            continue
        if x in bare or any(x.startswith(f + '=') for f in (*with_value, *optional_value)):
            i += 1
            continue
        out.append(x)
        i += 1
    return out


def _first_arg(inp):
    for k in ('description', 'command', 'file_path', 'path', 'pattern', 'query', 'prompt', 'url'):
        v = inp.get(k)
        if isinstance(v, str) and v:
            return v.splitlines()[0]
    return ''


def _first_line(text):
    return next((ln for ln in str(text or '').splitlines() if ln.strip()), '(no output)')


class ClaudeCode:
    kind = 'claude'
    procs = ('claude',)

    def _transcript(self, sid):
        tx = glob.glob(f'{HOME}/.claude/projects/*/{sid}.jsonl')
        return tx[0] if tx else None

    def session_id(self, agent, pid, cwd):
        return (agent.get('agent_session') or {}).get('value')

    def activity(self, sid, since_epoch):
        """(last activity epoch or None, pending kinds). Subagent and workflow files under the
        session dir count as activity."""
        path = self._transcript(sid)
        if not path:
            return None, []
        size = os.path.getsize(path)
        with open(path, 'rb') as f:
            f.seek(max(0, size - TAIL_BYTES))
            lines = f.read().decode(errors='replace').splitlines()[1 if size > TAIL_BYTES else 0:]
        last_msg, pending, crons = None, [], {}
        for line in lines:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get('type') not in ('user', 'assistant') or o.get('isMeta') or not o.get('timestamp'):
                continue
            ts = dt.datetime.fromisoformat(o['timestamp'].replace('Z', '+00:00')).timestamp()
            last_msg = ts
            if o['type'] != 'assistant' or ts < since_epoch:
                continue
            for c in (o.get('message') or {}).get('content') or []:
                if not isinstance(c, dict) or c.get('type') != 'tool_use':
                    continue
                name, inp = c.get('name'), c.get('input') or {}
                if name == 'ScheduleWakeup':
                    pending = [] if inp.get('stop') else [('wakeup', ts + float(inp.get('delaySeconds') or 0))]
                elif name == 'CronCreate':
                    crons[c.get('id')] = ts
                elif name == 'CronDelete':
                    crons.clear()  # ids differ from tool_use ids; any delete after a create is treated as teardown
                elif name == 'Monitor':
                    pending.append(('monitor', float('inf')))
        now = time.time()
        live = [kind for kind, until in pending if until > now - 600]
        if crons:
            live.append('cron')
        if last_msg is None:
            return None, live
        return max(last_msg, _newest_mtime(path[:-6])), live

    def blocks(self, sid):
        path = self._transcript(sid)
        if not path:
            return
        for raw in open(path, errors='replace'):
            try:
                d = json.loads(raw)
            except ValueError:
                continue
            if d.get('type') not in ('user', 'assistant') or d.get('isMeta') or d.get('isSidechain') or d.get('isCompactSummary'):
                continue
            c = (d.get('message') or {}).get('content')
            if isinstance(c, str):
                c = [{'type': 'text', 'text': c}]
            for b in c or []:
                t = b.get('type')
                if d['type'] == 'user' and t == 'text':
                    yield ('user', b['text'])
                elif t == 'text':
                    yield ('assistant', b['text'])
                elif t == 'tool_use':
                    yield ('tool', b.get('name', '?'), _first_arg(b.get('input') or {}))
                elif t == 'tool_result':
                    r = b.get('content')
                    if isinstance(r, list):
                        r = ' '.join(x.get('text', '') for x in r if isinstance(x, dict))
                    yield ('result', _first_line(r))

    def relaunch(self, argv, sid):
        rest = _strip_flags(argv[1:], ('--resume', '-r', '--session-id'), ('--continue', '-c'))
        return ['claude', *rest, '--resume', sid]


class Hermes:
    kind = 'hermes'
    procs = ('hermes',)
    db = f'{HOME}/.hermes/state.db'
    processes = f'{HOME}/.hermes/processes.json'

    def _q(self, sql, *args):
        con = sqlite3.connect(f'file:{self.db}?mode=ro', uri=True, timeout=5)
        try:
            return con.execute(sql, args).fetchall()
        finally:
            con.close()

    def session_id(self, agent, pid, cwd):
        """herdr's Hermes integration may not report a session id, so fall back to the one open
        CLI session in this cwd that started after the process did. Ambiguity means no id."""
        sid = (agent.get('agent_session') or {}).get('value')
        if sid:
            return sid
        argv = open(f'/proc/{pid}/cmdline', 'rb').read().decode(errors='replace').split('\0')
        for flag in ('--resume', '-r'):
            if flag in argv[:-1]:
                return argv[argv.index(flag) + 1]  # a resumed session keeps its old started_at
        from_proc = _proc_start(pid) - 5
        rows = self._q("select id from sessions where source='cli' and ended_at is null and cwd=? and started_at>=?", cwd, from_proc)
        return rows[0][0] if len(rows) == 1 else None

    def activity(self, sid, since_epoch):
        last = self._q("select max(timestamp) from messages where session_id=? and role in ('user','assistant')", sid)[0][0]
        pending = []
        if self._q("select 1 from async_delegations where ? in (origin_session_id, parent_session_id, origin_session) "
                   "and (completed_at is null or delivery_state='pending') limit 1", sid):
            pending.append('delegation')
        try:
            procs = json.load(open(self.processes))
        except (OSError, ValueError):
            procs = []
        if any(isinstance(p, dict) and p.get('pid') and os.path.exists(f"/proc/{p['pid']}") for p in procs):
            pending.append('background process')
        return last, pending

    def blocks(self, sid):
        rows = self._q("select role, content, tool_calls from messages where session_id=? and active=1 order by id", sid)
        for role, content, calls in rows:
            if role == 'user' and content:
                yield ('user', content)
            elif role == 'assistant':
                if content:
                    yield ('assistant', content)
                for c in json.loads(calls or '[]'):
                    fn = c.get('function') or {}
                    try:
                        inp = json.loads(fn.get('arguments') or '{}')
                    except ValueError:
                        inp = {}
                    yield ('tool', fn.get('name', '?'), _first_arg(inp if isinstance(inp, dict) else {}))
            elif role == 'tool':
                yield ('result', _first_line(content))

    def relaunch(self, argv, sid):
        # argv is `python .../bin/hermes <args>`; keep what follows the entry script.
        start = next((i for i, a in enumerate(argv) if os.path.basename(a) == 'hermes'), 0)
        rest = _strip_flags(argv[start + 1:], ('--resume', '-r'), (), ('--continue', '-c'))
        return ['hermes', *rest, '--resume', sid]


def _newest_mtime(dirpath):
    newest = 0
    for root, _, files in os.walk(dirpath):
        for fn in files:
            try:
                newest = max(newest, os.path.getmtime(os.path.join(root, fn)))
            except OSError:
                pass
    return newest


def _proc_start(pid):
    boot = time.time() - float(open('/proc/uptime').read().split()[0])
    ticks = int(open(f'/proc/{pid}/stat').read().rsplit(')', 1)[1].split()[19])
    return boot + ticks / os.sysconf('SC_CLK_TCK')


HARNESSES = {h.kind: h for h in (ClaudeCode(), Hermes())}
