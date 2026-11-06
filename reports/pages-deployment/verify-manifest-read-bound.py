"""Exercise actual bounded reader with virtual large responses; no network or distribution change."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/pages-deployment/run-20261106-manifest-read-bound-001'
spec=importlib.util.spec_from_file_location('manifest_reader',Path(__file__).with_name('verify-manifest.py'));reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
def need(v,m):
    if not v:raise ValueError(m)
class VirtualResponse:
    def __init__(self,total):self.total=total;self.calls=[]
    def read(self,size=-1):
        need(size==16*1024*1024+1,'Exactly one finite limit-plus-one request');self.calls.append(size)
        return b'x'*min(size,self.total)
def main():
    need(__debug__ and not OUT.exists(),'Fresh boundary receipt');OUT.mkdir(parents=True)
    path=Path(__file__).with_name('verify-manifest.py');raw=path.read_bytes();before=hashlib.sha256(raw).hexdigest()
    need(reader.MANIFEST_LIMIT==16*1024*1024 and reader.LIMIT==384*1024*1024,'Finite reader and unchanged delivery budget')
    rows=[]
    for total in [0,8*1024*1024,8*1024*1024+1,16*1024*1024-1,16*1024*1024,16*1024*1024+1,2**60]:
        response=VirtualResponse(total);refused=False;accepted_bytes=None
        try:accepted_bytes=len(reader.read_manifest_bytes(response))
        except ValueError as e:need(str(e)=='Manifest exceeds bounded read','Specific overflow refusal');refused=True
        need(refused==(total>reader.MANIFEST_LIMIT) and response.calls==[reader.MANIFEST_LIMIT+1],'Actual finite boundary behavior')
        if not refused:need(accepted_bytes==total,'Complete accepted body')
        rows.append(dict(virtualResponseBytes=total,readSizes=response.calls,acceptedBytes=accepted_bytes,overflowRefused=refused))
    prior=subprocess.check_output(['git','show','fda5f3ad:reports/pages-deployment/verify-manifest.py'],cwd=ROOT).decode('utf8')
    helper='def read_manifest_bytes(response):\n    raw = response.read(MANIFEST_LIMIT + 1)\n    need(len(raw) <= MANIFEST_LIMIT, "Manifest exceeds bounded read")\n    return raw\n\n\n'
    restored=raw.decode('utf8').replace('MANIFEST_LIMIT = 16 * 1024 * 1024\n','').replace(helper,'').replace('        raw = read_manifest_bytes(response)\n','        raw = response.read(8*1024*1024+1)\n        need(len(raw) <= 8*1024*1024, "Manifest exceeds bounded read")\n')
    need(restored==prior,'All prior Git/schema/cohort/SHA/bundle-budget/URL checks exact')
    after=hashlib.sha256(path.read_bytes()).hexdigest();need(before==after,'Tested reader stable')
    result=dict(status='FINITE_MANIFEST_READ_BOUND_PASS',manifestLimitBytes=reader.MANIFEST_LIMIT,bundleBudgetBytes=reader.LIMIT,cases=rows,acceptedCases=5,overflowRefusals=2,
        sourceSha256=before,sourceStable=True,allOtherReaderChecksExact=True,actualNetworkExecuted=False,
        scope='Bounded read helper only. Empty/non-JSON bodies may pass this byte bound and are still rejected by unchanged downstream schema checks. Virtual huge response is not allocated/transferred in full.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');(OUT/'reader.py.tested.txt').write_bytes(raw)
    print(json.dumps({k:result[k] for k in ['status','manifestLimitBytes','acceptedCases','overflowRefusals','allOtherReaderChecksExact']}))
if __name__=='__main__':main()
