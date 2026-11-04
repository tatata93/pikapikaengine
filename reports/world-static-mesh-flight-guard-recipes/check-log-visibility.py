"""Exercise real child log forwarding without changing any numerical checks."""
from contextlib import redirect_stdout
from hashlib import sha256
import importlib.util
from io import StringIO
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if len(sys.argv) != 2:
    raise SystemExit('usage: check-log-visibility.py NEW_ONE_COMPONENT_RUN')
name = sys.argv[1]
if Path(name).name != name or name in {'', '.', '..'}:
    raise SystemExit('one new run directory component required')
out = ROOT / 'reports/world-static-mesh-flight-guard-public-checks' / name
out.mkdir(parents=True, exist_ok=False)
recipe = Path(__file__).with_name('verify-gnu.py')
before = recipe.read_bytes()
(out / 'recipe.py.txt').write_bytes(before)
spec = importlib.util.spec_from_file_location('gnu_log_forwarding_recipe', recipe)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
commands = module.Commands(out, 30)
visible = StringIO()
failure = None
with redirect_stdout(visible):
    try:
        commands.run('synthetic-child-failure', [sys.executable, '-B', '-X', 'utf8', '-c',
                     "import sys; print('exact child diagnostic'); print('stderr diagnostic',file=sys.stderr); sys.exit(7)"])
    except ValueError as error:
        failure = str(error)
text = visible.getvalue()
(out / 'forwarded.stdout.txt').write_text(text, encoding='utf8')
forwarded = json.loads(text)
if not (failure == 'Command failed: synthetic-child-failure' and forwarded == {
        'failedCommand': 'synthetic-child-failure', 'exitCode': 7,
        'stdout': 'exact child diagnostic' + os.linesep, 'stderr': 'stderr diagnostic' + os.linesep}):
    raise RuntimeError('failed child diagnostics or rejection changed')
quiet = StringIO()
with redirect_stdout(quiet):
    returned = commands.run('synthetic-child-success', [sys.executable, '-B', '-c', "print('unchanged success bytes')"])
if quiet.getvalue() or returned != b'unchanged success bytes\r\n' and returned != b'unchanged success bytes\n':
    raise RuntimeError('successful child behavior changed')
if recipe.read_bytes() != before:
    raise RuntimeError('recipe changed during test')
result = {'schema': 1, 'status': 'PASS', 'recipeSha256': sha256(before).hexdigest(),
          'failedChildExitCode': 7, 'failedChildStillRejected': True, 'exactDiagnosticForwarded': True,
          'successfulChildBytesReturnedUnchanged': True, 'successfulChildNotPrinted': True,
          'sourceUnchanged': True, 'commands': commands.items,
          'scope': 'Synthetic subprocess visibility regression only. Does not diagnose or accept the failed GNU artifact audit.'}
(out / 'result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
print(json.dumps({'status': 'PASS', 'result': str(out / 'result.json'), 'scope': result['scope']}))
