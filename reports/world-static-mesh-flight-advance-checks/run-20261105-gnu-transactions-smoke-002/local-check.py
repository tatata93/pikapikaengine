"""Windows-only preparation checks; no GNU build or target execution."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
DRIVER = ROOT/'reports/world-static-mesh-flight-advance-recipes/verify-gnu.py'
PLAN = DRIVER.with_name('GNU_PLAN.md')
PHYSICAL = ROOT/'build/wfag4'
FIXTURE = ROOT/'reports/world-static-mesh-flight-advance-checks/run-20261105-transaction-capture-001/transactions.json'
sys.dont_write_bytecode = True


def need(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(path):
    raw = path.read_bytes()
    return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


def tree(path):
    return {p.relative_to(path).as_posix():stamp(p) for p in sorted(path.rglob('*')) if p.is_file()}


need(sys.platform == 'win32', 'This receipt is explicitly Windows preparation')
need(not PHYSICAL.exists(), 'Fresh short physical preparation directory')
PHYSICAL.mkdir(parents=True)
spec = importlib.util.spec_from_file_location('advance_gnu_preparation', DRIVER)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
helper = driver.import_file('guard_gnu_comparison_preparation', driver.HELPER_PATH)
before = driver.sources()+[stamp(FIXTURE),stamp(Path(__file__))]
write(OUT/'sources-before.json',before)
commands=[]


def run(name,args,exit_zero=False,error=None):
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    argv=[sys.executable,*map(str,args)];start=time.perf_counter()
    child=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True,timeout=120,check=False)
    stdout,stderr=OUT/(name+'.stdout.txt'),OUT/(name+'.stderr.txt')
    stdout.write_bytes(child.stdout);stderr.write_bytes(child.stderr)
    record={'name':name,'argv':argv,'cwd':str(ROOT),'exit':child.returncode,
            'elapsedSeconds':time.perf_counter()-start,'stdout':stamp(stdout),'stderr':stamp(stderr)}
    write(OUT/(name+'.command.json'),record);commands.append(record)
    need((child.returncode==0)==exit_zero,'Unexpected CLI exit: '+name)
    if error is not None:
        need(error.encode() in child.stderr+child.stdout,'Expected specific CLI refusal: '+name)
    return child


start=time.perf_counter()
result={'status':'FAIL','scope':'Windows preparation only. Copied actual MSVC data with synthetic identity alterations, not actual normal/sanitizer GNU data. No compiler/target execution or GNU acceptance.','actualGNUExecuted':False}
try:
    run('syntax',['-c','from pathlib import Path; p=Path('+repr(str(DRIVER))+'); compile(p.read_bytes(),str(p),"exec"); print("syntax PASS")'],True)
    run('help',[DRIVER,'--help'],True)
    base=[DRIVER,'--normal',PHYSICAL/'n','--output',PHYSICAL/'o','--sanbuild',PHYSICAL/'s','--debugbuild',PHYSICAL/'d']
    run('windows-platform-refused',base,error='Actual Linux GNU13 execution required')
    refused=json.loads((PHYSICAL/'o/verification.json').read_text(encoding='utf-8'))
    need(refused['status']=='FAIL' and refused['actualGNUExecuted'] is False and
         refused['normalBuildReconfiguredOrBuilt'] is False and refused['sourceStable'] is True and
         refused['commands']==[],'Actual refusal must not pretend to execute GNU or build normal')
    first_tree=tree(PHYSICAL/'o')
    run('output-reuse-refused',base,error='Fresh output directory required')
    need(first_tree==tree(PHYSICAL/'o'),'Refusal output unchanged on reuse')
    def bounded(name,changes,error):
        values={'normal':PHYSICAL/'n','output':PHYSICAL/name,'sanbuild':PHYSICAL/'s','debugbuild':PHYSICAL/'d'}
        values.update(changes);argv=[DRIVER]
        for key,value in values.items():argv.extend(['--'+key,value])
        run(name,argv,error=error)
    bounded('root-refused',{'normal':ROOT},'All paths must remain')
    bounded('build-root-refused',{'output':ROOT/'build'},'All paths must remain')
    bounded('duplicate-refused',{'normal':PHYSICAL/'same','output':PHYSICAL/'same'},'Four distinct directories')
    bounded('ancestor-refused',{'normal':PHYSICAL/'parent/n','output':PHYSICAL/'parent'},'Output must not contain')
    bounded('overlap-refused',{'sanbuild':PHYSICAL/'overlap-refused/child'},'must not overlap')
    run('parallel-refused',[*base[:1],'--normal',PHYSICAL/'n','--output',PHYSICAL/'p','--sanbuild',PHYSICAL/'s','--debugbuild',PHYSICAL/'d','--parallel','5'],error='Bounded command settings')
    run('timeout-refused',[*base[:1],'--normal',PHYSICAL/'n','--output',PHYSICAL/'t','--sanbuild',PHYSICAL/'s','--debugbuild',PHYSICAL/'d','--command-timeout','29'],error='Bounded command settings')
    actual=helper.load(FIXTURE)
    normal_id=actual['fixtures'][0]['report']['binding']['buildId'];san_id='a'*64
    need(normal_id!=san_id,'Distinct copied comparison identity')
    synthetic=copy.deepcopy(actual)
    for row in synthetic['fixtures']:
        row['report']['binding']['buildId']=san_id
        if row['report']['guard'] is not None:
            row['report']['guard']['binding']['buildId']=san_id
    original_tree=helper.exact_tree(actual);synthetic_tree=helper.exact_tree(synthetic)
    positive=driver.compare_transactions(helper,actual,synthetic,normal_id,san_id)
    need(original_tree==helper.exact_tree(actual) and synthetic_tree==helper.exact_tree(synthetic),'Comparison must not mutate inputs')
    write(OUT/'comparison-positive.json',positive)
    controls=[]
    success=next(i for i,r in enumerate(actual['fixtures']) if r['report']['committed'] and r['input']['bodies'])
    failure=next(i for i,r in enumerate(actual['fixtures']) if not r['report']['committed'])
    def reject(name,mutate,left=None):
        right=copy.deepcopy(synthetic);mutate(right)
        try:
            driver.compare_transactions(helper,actual if left is None else left,right,normal_id,san_id)
        except ValueError as error:
            controls.append({'name':name,'rejected':True,'error':str(error)})
        else:
            raise ValueError('Altered comparison accepted: '+name)
    reject('wrong-outer-identity',lambda d:d['fixtures'][0]['report']['binding'].update(buildId='b'*64))
    reject('wrong-owned-identity',lambda d:d['fixtures'][success]['report']['guard']['binding'].update(buildId='b'*64))
    reject('missing-fixture-tail',lambda d:d['fixtures'].pop())
    reject('body-field-change',lambda d:d['fixtures'][success]['worldAfter']['bodies'][0].update(radius=.125))
    reject('failed-advanced-negative-zero',lambda d:d['fixtures'][failure]['report'].update(advancedDt=-0.))
    reject('integer-float-type-change',lambda d:d['fixtures'][0]['progressBefore'].update(ticks=17.0))
    reject('boolean-integer-alias',lambda d:d['fixtures'][0]['report'].update(advanceProfileMatches=1))
    reject('key-order-change',lambda d:d['fixtures'][0].update(report=dict(reversed(list(d['fixtures'][0]['report'].items())))))
    reject('array-order-change',lambda d:d['fixtures'].reverse())
    reject('nested-pair-tail-deletion',lambda d:d['fixtures'][success]['report']['guard']['pairs'].pop())
    reject('unexpected-buildid-field',lambda d:d['fixtures'][0]['report'].update(otherBuildId=san_id))
    left_message=copy.deepcopy(actual);left_message['fixtures'][0]['report']['message']='not-normalized:'+normal_id
    reject('no-global-message-identity-replacement',lambda d:d['fixtures'][0]['report'].update(message='not-normalized:'+san_id),left_message)
    write(OUT/'comparison-negative-controls.json',{'status':'PASS','scope':'Synthetic copied metadata changes; not Native fault injection.','rejectedControls':controls})
    need(len(driver.WARN)==3 and len(driver.TARGET_SOURCES)==3 and
         sum(map(len,driver.TARGET_SOURCES.values()))==17 and
         len(set.union(*driver.TARGET_SOURCES.values()))==10,'Explicit three-target source inventories')
    result.update(status='WINDOWS_PREPARATION_PASS',cliCommands=len(commands),comparisonPositive=positive,
                  comparisonNegatives=len(controls),normalOutputReuseUnchanged=True,
                  warningTranslationUnits=3,targetCompileCommands=17,distinctHarnessSources=10,
                  compilerInvocations=0,targetExecutions=0,actualGNUExecuted=False)
finally:
    after=driver.sources()+[stamp(FIXTURE),stamp(Path(__file__))]
    write(OUT/'sources-after.json',after);write(OUT/'commands.json',commands)
    result.update(sourceStable=before==after,elapsedSeconds=time.perf_counter()-start)
    if before!=after:result['status']='FAIL'
    write(OUT/'result.json',result)
    need(before==after,'Protected inputs and the two owned files must remain unchanged during checks')
print(json.dumps({k:result[k] for k in ['status','cliCommands','comparisonNegatives','sourceStable','actualGNUExecuted','elapsedSeconds']}))
