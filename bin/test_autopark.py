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
