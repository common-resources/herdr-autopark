"""Self-check. Runs with `python3 bin/test_autopark.py` or pytest; needs no herdr server."""

import os
import subprocess
import sys
import tempfile
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


if __name__ == '__main__':
    tests = [f for name, f in sorted(globals().items()) if name.startswith('test_')]
    for t in tests:
        t()
    print(f'ok ({len(tests)} tests)')
