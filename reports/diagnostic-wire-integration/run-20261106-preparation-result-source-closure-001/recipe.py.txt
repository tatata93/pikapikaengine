"""Preflight actual recursive oracle modules and complete32 GNU source list; no Linux execution claim."""
from pathlib import Path
import ast,hashlib,importlib.util,json,types
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-preparation-result-source-closure-001'
def need(v,m):
 if not v:raise ValueError(m)
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 need(__debug__ and not OUT.exists(),'Fresh source preflight')
 spec=importlib.util.spec_from_file_location('preflight_result',ROOT/'scripts/verify-report-preparation-result-wire.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 required=set();seen=set()
 def visit(m):
  if id(m) in seen:return
  seen.add(id(m));p=Path(getattr(m,'__file__','') or ROOT).resolve()
  if not p.is_relative_to(ROOT/'scripts'):return
  required.add(p)
  for v in vars(m).values():
   if isinstance(v,types.ModuleType):visit(v)
 visit(module)
 expected={'scripts/verify-report-preparation-result-wire.py','scripts/verify-report-preparation-snapshot-inventory-wire.py','scripts/verify-report-preparation-pair-values-wire.py','scripts/verify-report-guard-failure-wire.py','scripts/verify-report-values-wire.py','scripts/verify-diagnostic-wire.py'}
 need(required=={ROOT/p for p in expected},'All six real recursive modules')
 driver=ROOT/'reports/diagnostic-wire-recipes/verify-preparation-result-gnu.py';tree=ast.parse(driver.read_text(encoding='utf8'))
 assignment=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sources' for t in n.targets))
 paths=ast.literal_eval(assignment.value.generators[0].iter);headers=json.loads((ROOT/'core/report-values-schema-v1.json').read_bytes())['headers']
 for row in headers:
  if row['path'] not in paths:paths.append(row['path'])
 need(len(paths)==len(set(paths))==32 and expected.issubset(paths),'Exact complete32 source inventory')
 native=json.loads((ROOT/'reports/diagnostic-wire-recipes/run-20261106-preparation-result-native-001/source-before.json').read_bytes());need(expected.issubset({r['path'] for r in native}),'All recursive modules actually captured by Native')
 receiver=ROOT/'reports/diagnostic-wire-publication/accept-preparation-result-gnu-log.py';ast.parse(receiver.read_text(encoding='utf8'))
 result=dict(status='SOURCE_CLOSURE_PREFLIGHT_ONLY',actualRecursiveOraclePaths=sorted(expected),capturedSources=[stamp(ROOT/p) for p in paths],driver=stamp(driver),receiver=stamp(receiver),actualGNUExecuted=False,scope='Actual Python module graph and parsed driver source inventory only; real GNU normal/Debug/sanitizer and all4 controls remain separate.')
 OUT.mkdir();(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());(OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(status=result['status'],oracles=len(required),sources=len(paths))))
if __name__=='__main__':main()
