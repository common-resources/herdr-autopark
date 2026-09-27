"""Run: python3 bin/test_autopark.py (no herdr needed)."""
import os, sys, types

here = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, here)
from harnesses import ClaudeCode, Hermes  # noqa: E402

sys.argv = ['autopark']
os.environ['AUTOPARK_CONFIG'] = '/nonexistent'
ap = types.ModuleType('ap')
ap.__file__ = f'{here}/autopark'
exec(open(ap.__file__).read().replace("if __name__ == '__main__':", 'if False:'), ap.__dict__)

# relaunch keeps flags, swaps any resume/continue for the parked session
assert ClaudeCode().relaunch(['/x/claude', '--model', 'opus', '--resume', 'old', '-c'], 'S') == ['claude', '--model', 'opus', '--resume', 'S']
assert Hermes().relaunch(['/v/python3', '/v/bin/hermes', '--yolo', '-c', 'name', '--resume=x'], 'S') == ['hermes', '--yolo', '--resume', 'S']
assert Hermes().relaunch(['/v/python3', '/v/bin/hermes', '--continue', '--yolo'], 'S') == ['hermes', '--yolo', '--resume', 'S']

# placeholder hints (italic/faint) are not drafts; truecolor operands containing 2/3 are not styles
assert ap.typed_text(' \x1b[0m\x1b[3m\x1b[38;5;136mSummarize this folder\x1b[0m') == ''
assert ap.typed_text(' \x1b[2mTry "fix lint"\x1b[22m') == ''
assert ap.typed_text(' \x1b[38;2;215;119;87mhalf a sentence\x1b[0m') == 'half a sentence'
assert ap.typed_text(' plain draft') == 'plain draft'
print('ok')

# the parked view replays a snapshot: the agent's input box is cut, long lines are cropped
import subprocess, tempfile  # noqa: E402
with tempfile.NamedTemporaryFile('w', suffix='.screen', delete=False) as f:
    f.write('\x1b[1mhistory line\x1b[0m\n' + 'x' * 300 + '\n───\n❯ my old draft\n───\nstatus bar\n')
out = subprocess.run([f'{here}/parked-view', 'sid', 'title', 'note'], capture_output=True, text=True,
                     env={**os.environ, 'AUTOPARK_SNAPSHOT': f.name, 'COLUMNS': '80', 'LINES': '12'}).stdout
os.unlink(f.name)
plain = [ap.SGR.sub('', ln) for ln in out.replace('\x1b[H\x1b[2J', '').split('\n')]
assert 'history line' in plain and 'x' * 80 in plain, plain
assert not any('my old draft' in ln or 'status bar' in ln for ln in plain), plain
assert any('Press Enter to resume' in ln for ln in plain)
print('ok view')
