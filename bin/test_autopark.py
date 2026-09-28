"""Self-check. Runs with `python3 bin/test_autopark.py` or pytest; needs no herdr server."""

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
from harnesses import ClaudeCode, Hermes  # noqa: E402


def load_autopark():
    """Import the extension-less script without running its sweep."""
    argv, sys.argv = sys.argv, ['autopark']
    os.environ['AUTOPARK_CONFIG'] = '/nonexistent'
    mod = types.ModuleType('autopark')
    mod.__file__ = f'{HERE}/autopark'
    try:
        exec(open(mod.__file__).read().replace("if __name__ == '__main__':", 'if False:'), mod.__dict__)
    finally:
        sys.argv = argv
    return mod


AP = load_autopark()


def test_relaunch_swaps_resume_flags():
    claude = ClaudeCode().relaunch(['/x/claude', '--model', 'opus', '--resume', 'old', '-c'], 'S')
    assert claude == ['claude', '--model', 'opus', '--resume', 'S']
    hermes = Hermes().relaunch(['/v/python3', '/v/bin/hermes', '--yolo', '-c', 'name', '--resume=x'], 'S')
    assert hermes == ['hermes', '--yolo', '--resume', 'S']
    bare_continue = Hermes().relaunch(['/v/python3', '/v/bin/hermes', '--continue', '--yolo'], 'S')
    assert bare_continue == ['hermes', '--yolo', '--resume', 'S']


def test_placeholders_are_not_drafts():
    assert AP.typed_text(' \x1b[0m\x1b[3m\x1b[38;5;136mSummarize this folder\x1b[0m') == ''
    assert AP.typed_text(' \x1b[2mTry "fix lint"\x1b[22m') == ''
    # truecolor operands that contain a 2 or 3 are colors, not faint/italic
    assert AP.typed_text(' \x1b[38;2;215;119;87mhalf a sentence\x1b[0m') == 'half a sentence'
    assert AP.typed_text(' plain draft') == 'plain draft'


def test_view_replays_snapshot_without_input_box():
    with tempfile.NamedTemporaryFile('w', suffix='.screen', delete=False) as f:
        f.write('\x1b[1mhistory line\x1b[0m\n' + 'x' * 300 + '\n───\n❯ my old draft\n───\nstatus bar\n')
    try:
        env = {**os.environ, 'AUTOPARK_SNAPSHOT': f.name, 'COLUMNS': '80', 'LINES': '12'}
        out = subprocess.run([f'{HERE}/parked-view', 'sid', 'title', 'note'], capture_output=True, text=True, env=env).stdout
    finally:
        os.unlink(f.name)
    plain = [AP.SGR.sub('', ln) for ln in out.replace('\x1b[H\x1b[2J', '').split('\n')]
    assert 'history line' in plain and 'x' * 80 in plain, plain
    assert not any('my old draft' in ln or 'status bar' in ln for ln in plain), plain
    assert any('Press Enter to resume' in ln for ln in plain)


DIALOG = """
   Background work is running
   The following will stop when you exit:

   subagent · Reply with the single word ok only.
   {extra}
   ❯ 1. Exit and stop tasks
     2. Move to background and exit
     3. Stay

   Enter to confirm · n to cancel
"""


def test_exit_dialog_stops_only_idle_subagents():
    assert AP.exit_confirm_choice('❯ plain prompt') == (None, [])
    assert AP.exit_confirm_choice(DIALOG.format(extra='')) == ('stop', ['subagent'])
    choice, items = AP.exit_confirm_choice(DIALOG.format(extra='shell · pnpm dev'))
    assert choice == 'cancel' and items == ['subagent', 'shell']
    AP.CFG['stop_idle_subagents'] = False
    try:
        assert AP.exit_confirm_choice(DIALOG.format(extra=''))[0] == 'cancel'
    finally:
        AP.CFG['stop_idle_subagents'] = True


def test_crons_keep_the_session_awake_until_each_is_deleted():
    now = time.time()

    def at(sec):
        return dt.datetime.fromtimestamp(now - 3600 + sec, dt.UTC).isoformat()

    def use(sec, uid, name, inp):
        return {
            'type': 'assistant',
            'timestamp': at(sec),
            'message': {'content': [{'type': 'tool_use', 'id': uid, 'name': name, 'input': inp}]},
        }

    def result(sec, uid, text, err=None):
        return {
            'type': 'user',
            'timestamp': at(sec),
            'message': {'content': [{'type': 'tool_result', 'tool_use_id': uid, 'content': text, 'is_error': err}]},
        }

    def cron_at(epoch):
        t = dt.datetime.fromtimestamp(epoch)
        return f'{t.minute} {t.hour} {t.day} {t.month} *'

    made = [
        use(1, 'u1', 'CronCreate', {'cron': '7 * * * *'}),
        result(2, 'u1', 'Scheduled recurring job aaaa1111 (Every hour at :07). Session-only'),
        use(3, 'u2', 'CronCreate', {'cron': '9 * * * *'}),
        result(4, 'u2', 'Scheduled recurring job bbbb2222 (Every hour at :09). Session-only'),
        use(5, 'u3', 'CronCreate', {'cron': '1 2 3 4 *', 'recurring': False}),
        result(6, 'u3', 'Error: bad cron', True),
    ]
    one_shot = [
        use(1, 'u4', 'CronCreate', {'cron': cron_at(now + 7200), 'recurring': False}),
        result(2, 'u4', 'Scheduled one-shot task cccc3333 (...). Session-only'),
    ]
    past = [
        use(1, 'u5', 'CronCreate', {'cron': cron_at(now - 3000), 'recurring': False}),  # fired 50 min ago
        result(2, 'u5', 'Scheduled one-shot task dddd4444 (...)'),
    ]
    cases = [
        (made, ['cron']),
        (made + [use(7, 'u6', 'CronDelete', {'id': 'aaaa1111'})], ['cron']),  # one of two deleted
        (made + [use(7, 'u6', 'CronDelete', {'id': 'aaaa1111'}), use(8, 'u7', 'CronDelete', {'id': 'bbbb2222'})], []),
        (one_shot, ['cron']),
        (past, []),
    ]
    h = ClaudeCode()
    with tempfile.TemporaryDirectory() as d:
        for rows, want in cases:
            path = f'{d}/s.jsonl'
            with open(path, 'w') as f:
                f.write('\n'.join(json.dumps(r) for r in rows) + '\n')
            h._transcript = lambda sid, p=path: p
            assert h.activity('s', now - 7200)[1] == want, (rows[-1], want)
            assert h.activity('s', now)[1] == [], 'crons from before the process started died with it'


if __name__ == '__main__':
    tests = [f for name, f in sorted(globals().items()) if name.startswith('test_')]
    for t in tests:
        t()
    print(f'ok ({len(tests)} tests)')
