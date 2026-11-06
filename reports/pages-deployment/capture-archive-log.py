"""Save a decoded real Pages build log and its single actual archive audit record.

No archive download, extraction, HTTP delivery, rerun, or deployment acceptance.
"""
from pathlib import Path
import argparse,base64,hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('run',type=int);p.add_argument('job',type=int);p.add_argument('base64_log',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 assert __debug__ and re.fullmatch('[a-f0-9]{40}',a.source) and min(a.run,a.job)>0
 source=a.base64_log.resolve();out=a.output.resolve();assert source.is_relative_to(ROOT/'build') and out.is_relative_to(ROOT/'reports/pages-deployment') and not out.exists()
 raw=base64.b64decode(source.read_bytes());text=raw.decode('utf8');assert a.source in text
 lines=[v[v.index('{'):] for v in text.splitlines() if '"schema": 1, "status": "PASS", "archive":' in v];assert len(lines)==1;record=json.loads(lines[0])
 assert record['status']=='PASS' and 0<record['archive']['bytes']<=384*1024*1024 and 0<record['manifest']['bytes']<=16*1024*1024 and record['files']==record['selectedFiles']+1 and record['fileBytes']==record['selectedBytes']+record['manifest']['bytes']
 out.mkdir(parents=True);(out/'decoded-build-log.txt').write_bytes(raw);(out/'actual-archive-verification.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8',newline='\n')
 provenance=dict(schema=1,status='ACTUAL_ARCHIVE_LOG_CAPTURED',source=a.source,run=a.run,buildJob=a.job,decodedLogBytes=len(raw),decodedLogSha256=hashlib.sha256(raw).hexdigest(),archiveTransferred=False,fullHTTPPayloadTransferred=False,publicFeatureAccepted=False)
 (out/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf8',newline='\n');(out/'recipe.py.txt').write_bytes(Path(__file__).read_bytes());print(json.dumps(provenance))
if __name__=='__main__':main()
