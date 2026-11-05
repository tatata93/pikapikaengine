"""Compare moved diagnostic CI commands with the previous accepted workflow."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/diagnostic-wire-integration/run-20261106-flight-wire-ci-layout-001'
def need(v,m):
    if not v:raise ValueError(m)
def main():
    need(__debug__ and not OUT.exists(),'Fresh evidence');OUT.mkdir(parents=True)
    before=subprocess.check_output(['git','show','d4cfda77:.github/workflows/verify.yml'],cwd=ROOT).decode('utf8')
    after=(ROOT/'.github/workflows/verify.yml').read_text(encoding='utf8')
    start=before.index('      - name: Audit typed diagnostic primitives independently')
    end=before.index('      - name: Build and test C++ core on Linux',start)
    original=before[start:end]
    marker='\n  native-diagnostic-values:\n';need(after.count(marker)==1,'One new bounded job')
    old_jobs,new=after.split(marker)
    need(old_jobs==before[:start]+before[end:],'All six original jobs unchanged except relocation')
    need(new.count(original)==1,'All15 original audit commands preserved byte for byte')
    expected=original+'      - name: Audit free flight snapshots and error tubes independently\n        run: python3 reports/diagnostic-wire-recipes/verify-flight-source-tube-gnu.py --output build/ci-report-flight-source-tube-wire\n'
    need(new.endswith(expected),'Exactly one new audit after the original15')
    need('    timeout-minutes: 20\n' in new and '    runs-on: ubuntu-24.04\n' in new and '    if: github.event.repository.private == false\n' in new,'Same public standard runner and bounded runtime')
    a=before.index('      - name: Fetch exact public source commit');b=before.index('      - name: Prepare browser-independent modules',a)
    need(before[a:b] in new,'Same exact source checkout')
    result=dict(status='PASS',source='d4cfda77',originalAuditSteps=15,newAuditSteps=1,allOriginalCommandsExact=True,allOtherJobsExact=True,portableBoundMinutes=25,diagnosticBoundMinutes=20,permissionsUnchanged=True,runner='ubuntu-24.04',workflowSha256=hashlib.sha256(after.encode()).hexdigest(),scope='Structural relocation check only; actual seven-job execution is separate public CI acceptance.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
