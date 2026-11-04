"""Bind full connector job/log captures to their exact public feature run."""
from collections import Counter
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[2]
PREFIX='reports/accelerated-sphere-box-coverage'
commit=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',commit)
def read(name):return json.loads((ROOT/name).read_text(encoding='utf8'))
engine=read(PREFIX+'-engine-jobs.json');pages=read(PREFIX+'-pages-jobs.json')
assert len(engine['jobs'])==1 and len(pages['jobs'])==3
for j in [*engine['jobs'],*pages['jobs']]:
    assert j['status']=='completed' and j['conclusion']=='success'
    assert all(s['status']=='completed' and s['conclusion']=='success' for s in j['steps'])
job=engine['jobs'][0]
run_id=job['run_id'];job_id=job['id'];pages_run_id=pages['jobs'][0]['run_id']
assert all(type(v) is int and v>0 for v in [run_id,job_id,pages_run_id])
assert len(job['steps'])==25
assert all(j['run_id']==pages_run_id for j in pages['jobs'])
path=PREFIX+'-job-'+str(job_id)+'-full.txt'
raw=(ROOT/path).read_bytes();text=raw.decode('utf8');assert 0<len(raw)<16*1024*1024
clean=re.sub(r'\x1b\[[0-9;]*m','',text)
prior_path='reports/accelerated-pair-coverage-job-126568510900-excerpt.json'
prior=read(prior_path)
def warnings(lines):
    rows=[]
    for line in lines:
        line=re.sub(r'\x1b\[[0-9;]*m','',line)
        if 'warning:' not in line:continue
        m=re.search(r'((?:core|tests|tools|reports)/[^\s:]+):(\d+):(\d+): warning:(.*)$',line)
        assert m,line
        rows.append({'file':m[1],'line':int(m[2]),'column':int(m[3]),'diagnostic':m[4]})
    return rows
current=warnings(clean.splitlines());old=warnings(r['text'] for r in prior['lines'])
def counts(rows):return Counter((r['file'],r['line'],r['column'],r['diagnostic']) for r in rows)
assert len(current)==len(old)==48 and counts(current)==counts(old)
record={'schema':1,'commit':commit,'checked':datetime.now(timezone.utc).isoformat(),
 'engine':{'runId':run_id,'jobId':job_id,'jobs':engine,
           'log':{'path':path,'bytes':len(raw),'sha256':sha256(raw).hexdigest(),
                  'decodedCharacters':len(text),'totalLines':len(text.splitlines())}},
 'pages':{'runId':pages_run_id,'jobs':pages},
 'warnings':{'priorExcerptPath':prior_path,'current':current,'prior':old,'sameMultiset':True},
 'collectionScope':'Full decoded job log saved as UTF8 exactly from GitHub connector structuredContent.content; no partial excerpt. Jobs are linked by run_id to the independently fetched exact-commit run state.'}
target=ROOT/(PREFIX+'-public-ci-evidence.json');assert not target.exists()
target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','engineSteps':len(job['steps']),'pagesJobs':3,'log':record['engine']['log'],'warnings':len(current),'newWarnings':0}))
