"""Record the manually inspected native-accepted diagram; no public UI or performance claim."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parents[2]

def main():
 assert __debug__
 n=json.loads((R/'reports/diagnostic-wire-advance-commit-ledgers-verification.json').read_bytes())
 assert n['status']=='FINITE_NATIVE_REPORT_ADVANCE_COMMIT_LEDGERS_PASS' and n['fullNativeParentObservedExitCode']==0 and n['selectedCTestPerConfiguration']==67
 out=R/'reports/diagnostic-wire-learning/run-20261106-advance-commit-ledgers-local-002'
 svg=R/'docs/learn/diagrams/report-advance-commit-ledgers-wire.svg';raw=svg.read_bytes()
 assert (out/'diagram.png').is_file() and not (out/'observation.json').exists()
 assert 'Native有限受入：各67回帰／10,547変更を確認。新GNU・公開は別受入。'.encode() in raw
 (out/'diagram.svg.txt').write_bytes(raw);(out/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
 record=dict(schema=1,browserTab=140,url='http://127.0.0.1:8785/docs/learn/diagrams/report-advance-commit-ledgers-wire.svg',fullPage=True,allThreePanelsAndFooterVisuallyInspected=True,footerScope='Native both67 CTests and10547 controls accepted; new GNU/public pending',sourceSha256=hashlib.sha256(raw).hexdigest(),screenshotSha256=hashlib.sha256((out/'diagram.png').read_bytes()).hexdigest(),performanceBenchmark=False,publicDeploymentVerified=False)
 (out/'observation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(status='LOCAL_NATIVE_ACCEPTED_DIAGRAM_OBSERVATION_RECORDED',publicDeploymentVerified=False)))

if __name__=='__main__':main()
