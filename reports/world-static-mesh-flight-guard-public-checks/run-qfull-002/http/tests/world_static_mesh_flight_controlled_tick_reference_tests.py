"""Finite controlled tick actual references and copied adversarial controls.

Synthetic helper/self tests and copied fault metadata are explicitly distinct
from actual Native execution or exception/allocator fault injection.
"""
from pathlib import Path
from fractions import Fraction
import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
CHECKER=ROOT/'scripts/verify-world-static-mesh-flight-controlled-tick.py'
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('controlled_tick_preparation_controls',CHECKER)
ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)


def need(value,message):
    if not value:raise AssertionError(message)


def rejected(action):
    try:action()
    except (AssertionError,ValueError):return
    raise AssertionError('Invalid helper input accepted')


def body(identifier,static=False):
    return {'id':identifier,'isStatic':static,'mass':2.,'inertiaDiagonal':[1.,1.,1.],'radius':.25,
            'position':[0.,4.,-0.],'velocity':[0.,0.,0.],'angularMomentum':[0.,0.,0.],
            'orientation':[0.,0.,0.,1.],'force':[3.,-0.,0.],'torque':[-0.,0.,0.],
            'material':{'restitution':0.,'friction':0.}}


def self_tests():
    names=[]
    def check(name,action):action();names.append(name)
    p={'time':.125,'ticks':17};bodies=[body(11),body(7,True)]
    packet={'mode':0,'expectedTick':17,'loads':[{'bodyId':7,'force':[-0.,0.,-0.],'torque':[0.,-0.,0.]},
                                            {'bodyId':11,'force':[5.,-0.,0.],'torque':[-0.,0.,0.]}]}
    original=copy.deepcopy([bodies,packet]);staged,mapping=ref.replacement_reference(bodies,p,packet)
    check('absolute-three-replaced-by-five-not-eight',lambda:need(staged[0]['force'][0]==5.,'absolute replacement'))
    check('packet-order-versus-body-order',lambda:need(mapping==[{'packetOrdinal':0,'bodyOrdinal':1,'bodyId':7},{'packetOrdinal':1,'bodyOrdinal':0,'bodyId':11}],'ID mapping without sorting source bodies'))
    check('static-negative-zero-preserved',lambda:need(ref.bits(staged[1]['force'][0]).hex()=='8000000000000000','raw zero sign retained'))
    check('dynamic-negative-zero-preserved',lambda:need(ref.bits(staged[0]['force'][1]).hex()=='8000000000000000','raw zero sign retained'))
    check('originals-unchanged',lambda:ref.equal(original,[bodies,packet],'original helper source'))
    staged[0]['force'][0]=99.
    check('staged-owned-source-separated',lambda:need(bodies[0]['force'][0]==3. and packet['loads'][1]['force'][0]==5.,'no borrowed array mutation'))
    cleared=ref.cleared_candidates(staged)
    check('cleared-loads-all-positive-zero',lambda:need(all(ref.bits(v).hex()=='0000000000000000' for b in cleared for k in ('force','torque') for v in b[k]),'force/torque +0'))
    check('cleared-copy-owned',lambda:need(staged[0]['force'][0]==99.,'source candidate not mutated by clear expectation'))
    h=Fraction(1,16);x,v=ref.exact_translation([0.,0.,0.],[0.,0.,0.],2.,[4.,0.,0.],[0.,0.,0.],h)
    check('dyadic-first-tick-closed-form',lambda:need(x[0]==Fraction(1,256) and v[0]==Fraction(1,8),'exact first requested load'))
    x2,v2=ref.exact_translation(x,v,2.,[-4.,0.,0.],[0.,0.,0.],h)
    check('dyadic-second-opposite-load',lambda:need(x2[0]==Fraction(1,128) and v2[0]==0,'exact second requested load'))
    old_x,old_v=ref.exact_translation(x,v,2.,[0.,0.,0.],[0.,0.,0.],h)
    check('first-load-only-batch-is-different',lambda:need(old_x[0]==Fraction(3,256) and old_v[0]==Fraction(1,8) and old_x!=x2,'old batch comparison is analytic only'))
    check('protected-integer-clock-reference',lambda:need(ref.advance.clock.self_test()==11,'integer ties-even pure reference'))
    check('packet-unknown-mode',lambda:rejected(lambda:ref.replacement_reference(bodies,p,{**packet,'mode':1})))
    check('packet-stale-tick',lambda:rejected(lambda:ref.replacement_reference(bodies,p,{**packet,'expectedTick':18})))
    check('packet-bool-tick',lambda:rejected(lambda:ref.replacement_reference(bodies,p,{**packet,'expectedTick':True})))
    check('packet-negative-zero-mode',lambda:rejected(lambda:ref.replacement_reference(bodies,p,{**packet,'mode':-0.})))
    check('missing-allbody-row',lambda:rejected(lambda:ref.replacement_reference(bodies,p,{**packet,'loads':packet['loads'][:1]})))
    duplicate=copy.deepcopy(packet);duplicate['loads'][1]['bodyId']=7
    check('duplicate-packet-id',lambda:rejected(lambda:ref.replacement_reference(bodies,p,duplicate)))
    unknown=copy.deepcopy(packet);unknown['loads'][1]['bodyId']=99
    check('unknown-packet-id',lambda:rejected(lambda:ref.replacement_reference(bodies,p,unknown)))
    unsafe=copy.deepcopy(packet);unsafe['loads'][1]['bodyId']=2**53
    check('unsafe-packet-id',lambda:rejected(lambda:ref.replacement_reference(bodies,p,unsafe)))
    loaded_static=copy.deepcopy(packet);loaded_static['loads'][0]['force'][0]=1.
    check('static-nonzero-load',lambda:rejected(lambda:ref.replacement_reference(bodies,p,loaded_static)))
    overflow=copy.deepcopy(packet);overflow['loads'][1]['force'][0]=1e25
    check('absolute-load-domain',lambda:rejected(lambda:ref.replacement_reference(bodies,p,overflow)))
    invalid=copy.deepcopy(bodies);invalid[0]['force'][0]=1e25
    check('invalid-original-not-repaired-by-packet',lambda:rejected(lambda:ref.replacement_reference(invalid,p,packet)))
    check('duplicate-json-key',lambda:rejected(lambda:ref.loads('{"a":1,"a":2}')))
    check('nonfinite-json-token',lambda:rejected(lambda:ref.loads('{"x":NaN}')))
    check('actual-document-entry-still-refuses',lambda:rejected(lambda:ref.verify({'synthetic':'not Native'})))
    return names


def actual_controls(args,groups,out,write):
    data=ref.load(args.fixture);baseline=ref.verify(data,development_unpinned=args.development_unpinned)
    write('actual-reference.json',baseline);rows=data['fixtures'];controls=[];positive=[]
    changed=copy.deepcopy(data);changed['fixtures'].reverse()
    scenarios={key:'renamed-group-'+str(i) for i,key in enumerate(sorted({r['scenario'] for r in rows}))}
    for i,row in enumerate(changed['fixtures']):row['name']='renamed-row-'+str(i);row['scenario']=scenarios[row['scenario']]
    reordered=ref.verify(changed,development_unpinned=args.development_unpinned)
    ref.equal(baseline,reordered,'renamed/reordered actual document has same complete counts and original input fingerprint')
    positive.append('actual-label-scenario-name-and-document-order-independent')

    def pick(predicate):
        matches=[i for i,r in enumerate(rows) if predicate(r)];need(matches,'Required actual control anchor missing');return matches[0]
    success=pick(lambda r:r['report']['committed'] and len(r['worldBefore']['bodies'])==1 and not r['worldBefore']['bodies'][0]['isStatic'])
    preflight=pick(lambda r:r['report']['child'] is None and r['report']['reason']=='expected_tick')
    failed=pick(lambda r:r['report']['child'] is not None and not r['report']['child']['committed'] and r['report']['child']['guard'] is not None)
    clock_failed=pick(lambda r:r['report']['child'] is not None and r['report']['child']['guard'] is None)
    mapped_failure=pick(lambda r:r['report']['reason'] in ('packet_load','static_load') and any(x is not None for x in r['report']['mappings']))
    hard=pick(lambda r:r['report']['capture']=='none')

    def row_control(name,index,mutate):
        altered=copy.deepcopy(rows[index]);mutate(altered)
        need(json.dumps(altered,sort_keys=True)!=json.dumps(rows[index],sort_keys=True),'Control must actually alter evidence: '+name)
        rejected(lambda:ref.verify_row(altered,data['layoutSizes'],new_stats()))
        controls.append({'name':name,'rejected':True,'scope':'Copied JSON alteration; no Native fault injection'})
    def document_control(name,mutate):
        altered=copy.deepcopy(data);mutate(altered)
        need(json.dumps(altered,sort_keys=True)!=json.dumps(data,sort_keys=True),'Document control must alter evidence: '+name)
        rejected(lambda:ref.verify(altered,development_unpinned=args.development_unpinned))
        controls.append({'name':name,'rejected':True,'scope':'Copied envelope/history alteration'})
    def r(row):return row['report']
    def tick(row):return row['report']['child']
    def new_stats():
        return ref.new_stats()

    document_control('unknown-schema',lambda d:d.update(schema=2))
    document_control('schema-bool-alias',lambda d:d.update(schema=True))
    document_control('unknown-kind',lambda d:d.update(kind='controlled-tick'))
    document_control('extra-envelope-key',lambda d:d.update(expectedResult=True))
    document_control('missing-full-row-field',lambda d:d['fixtures'][0].pop('inputAfter'))
    document_control('duplicate-context-name',lambda d:d['fixtures'][1].update(name=d['fixtures'][0]['name']))
    document_control('fixture-tail-removed',lambda d:d['fixtures'].pop())
    for key in sorted(ref.REPORT_KEYS):
        row_control('report-missing-'+key,success,lambda row,k=key:r(row).pop(k))
    row_control('unknown-status',success,lambda row:r(row).update(status='advanced'))
    row_control('unknown-reason',success,lambda row:r(row).update(reason='success'))
    row_control('outer-committed-integer',success,lambda row:r(row).update(committed=1))
    row_control('original-validated-integer',success,lambda row:r(row).update(originalBodiesValidated=1))
    row_control('requested-mode-negative-zero',success,lambda row:r(row).update(requestedMode=-0.))
    row_control('requested-tick-bool',success,lambda row:r(row).update(requestedTick=True))
    row_control('original-tick-float-alias',success,lambda row:r(row)['originalProgress'].update(ticks=17.))
    row_control('requested-dt-changed',success,lambda row:r(row).update(requestedDt=.03125))
    row_control('advanced-dt-changed',success,lambda row:r(row).update(advancedDt=0.))
    row_control('failure-advanced-negative-zero',failed,lambda row:r(row).update(advancedDt=-0.))
    row_control('binding-profile-bool',success,lambda row:r(row)['binding'].update(profile=True))
    row_control('binding-not-configured',success,lambda row:r(row)['binding'].update(configured=False))
    row_control('binding-malformed-id',success,lambda row:r(row)['binding'].update(buildId='a'*63))
    row_control('binding-wrong-upstream',success,lambda row:r(row)['binding'].update(upstreamBuildId='0'*64))
    row_control('mapping-unused-tail-removed',success,lambda row:r(row)['mappings'].pop())
    row_control('mapping-body-ordinal-bool',success,lambda row:r(row)['mappings'][0].update(bodyOrdinal=False))
    row_control('mapping-packet-ordinal-bool',success,lambda row:r(row)['mappings'][0].update(packetOrdinal=False))
    row_control('mapping-ID-wrong',success,lambda row:r(row)['mappings'][0].update(bodyId=999))
    row_control('ID-resolved-load-failure-mapping-erased',mapped_failure,lambda row:r(row)['mappings'].__setitem__(0,None))
    row_control('hard-count-invents-capture',hard,lambda row:r(row).update(capture='complete'))
    row_control('stale-invents-child',preflight,lambda row:r(row).update(child=copy.deepcopy(rows[success]['report']['child'])))
    row_control('stale-invents-private-world',preflight,lambda row:r(row).update(stagedBefore=copy.deepcopy(row['worldBefore'])))
    row_control('stale-wrong-failure-stage',preflight,lambda row:r(row)['failure'].update(stage='child'))
    row_control('unknown-failure-stage',preflight,lambda row:r(row)['failure'].update(stage='accepted'))
    row_control('failure-index-bool',mapped_failure,lambda row:r(row)['failure'].update(bodyOrdinal=False))
    row_control('capture-state-unknown',success,lambda row:r(row).update(capture='owned'))
    row_control('staged-state-unknown',success,lambda row:r(row).update(stagedCapture='ready'))
    row_control('private-after-incomplete',success,lambda row:r(row).update(privateAfterCapture='partial'))
    row_control('original-packet-stale',success,lambda row:r(row)['original']['packet'].update(expectedTick=99))
    row_control('original-source-body-lost-force-zero',success,lambda row:r(row)['original']['world']['bodies'][0].update(force=[99.,0.,0.]))
    row_control('original-source-ID-float',success,lambda row:r(row)['original']['world']['bodies'][0].update(id=float(row['worldBefore']['bodies'][0]['id'])))
    row_control('staged-force-added-instead-of-replaced',success,lambda row:r(row)['stagedBefore']['bodies'][0].update(force=[99.,0.,0.]))
    row_control('staged-gravity-changed',success,lambda row:r(row)['stagedBefore'].update(gravity=[99.,0.,0.]))
    row_control('private-after-body-missing',success,lambda row:r(row)['privateAfter']['bodies'].pop())
    row_control('private-after-force-not-cleared',success,lambda row:r(row)['privateAfter']['bodies'][0].update(force=[1.,0.,0.]))
    row_control('private-after-torque-negative-zero',success,lambda row:r(row)['privateAfter']['bodies'][0].update(torque=[-0.,0.,0.]))
    row_control('private-progress-wrong',success,lambda row:r(row)['privateProgressAfter'].update(ticks=999))
    row_control('missing-child-no-production-fill',success,lambda row:r(row).update(child=None))
    row_control('child-missing-guard-message',success,lambda row:tick(row).pop('guardMessage'))
    row_control('child-profile-unchecked',success,lambda row:tick(row).update(advanceProfileChecked=False))
    row_control('child-original-time-changed',success,lambda row:tick(row)['originalProgress'].update(time=0.))
    row_control('child-proposed-time-changed',success,lambda row:tick(row)['proposedProgress'].update(time=0.))
    row_control('child-clock-excludes-exact',success,lambda row:tick(row)['clock'].update(timeSum=[-2.,-1.]))
    row_control('child-clock-RN-difference-changed',success,lambda row:tick(row)['clock'].update(representedDt=0.))
    row_control('child-guard-absent',success,lambda row:tick(row).update(guard=None))
    row_control('child-guard-candidate-tail-missing',success,lambda row:tick(row)['guard']['candidateBodies'].pop())
    row_control('child-guard-work-counter',success,lambda row:tick(row)['guard']['work'].update(childCallsReturned=999))
    row_control('child-guard-input-is-original-not-staged',success,lambda row:tick(row)['guard']['preparation']['snapshot']['bodies'][0].update(force=[99.,0.,0.]))
    def math_child(row,kind,call):
        return next(p['child'][call]['result'] for p in tick(row)['guard']['pairs'] if p['child'] and p['child']['kind']==kind and p['child'][call]['result'] is not None)
    math_anchor=pick(lambda row:row['report']['committed'] and row['report']['child']['guard'] is not None and
        {'mesh','plane','sphere'}.issubset({p['child']['kind'] for p in row['report']['child']['guard']['pairs'] if p['child']}))
    row_control('actual-mesh-child-tube-underbound',math_anchor,lambda row:math_child(row,'mesh','mesh')['tube'].update(positionError=0.))
    row_control('actual-metric-child-value-excludes-range',math_anchor,lambda row:math_child(row,'plane','metric')['audits'][0].update(value=[7.,8.]))
    row_control('actual-plane-box-child-coordinate-excludes-range',math_anchor,lambda row:math_child(row,'plane','box')['audits'][0]['evaluation']['tubeCoordinates'].__setitem__(1,[7.,8.]))
    def cut_sphere_root(row):
        evaluation=math_child(row,'sphere','sphere')['audits'][0]['evaluation']
        evaluation['root']['value']=[0.,0.];evaluation['distance']=[0.,0.]
    row_control('actual-sphere-box-root-excludes-sqrt',math_anchor,cut_sphere_root)
    row_control('clock-refusal-invents-guard-call',clock_failed,lambda row:tick(row)['work'].update(guardQueriesAttempted=1))
    row_control('clock-refusal-invents-guard-message',clock_failed,lambda row:tick(row).update(guardMessage='not returned'))
    row_control('child-refusal-invents-external-commit',failed,lambda row:r(row).update(committed=True))
    row_control('child-refusal-invents-store-count',failed,lambda row:r(row)['work'].update(bodyAssignments=1))
    row_control('outer-refusal-body-mutated',failed,lambda row:row['worldAfter']['bodies'][0]['position'].__setitem__(0,99.))
    row_control('outer-refusal-progress-mutated',failed,lambda row:row['progressAfter'].update(ticks=999))
    row_control('outer-success-load-not-cleared',success,lambda row:row['worldAfter']['bodies'][0].update(force=[1.,0.,0.]))
    row_control('outer-success-negative-zero-clear',success,lambda row:row['worldAfter']['bodies'][0].update(torque=[-0.,0.,0.]))
    row_control('outer-success-progress-wrong',success,lambda row:row['progressAfter'].update(ticks=999))
    row_control('outer-source-packet-mutated',success,lambda row:row['inputAfter']['packet']['loads'][0]['force'].__setitem__(0,99.))
    row_control('outer-source-mesh-revision-mutated',success,lambda row:row['inputAfter']['scene']['meshes'][0].update(revision=999))
    for key in sorted(ref.WORK_KEYS):
        row_control('work-phase-'+key,success,lambda row,k=key:r(row)['work'].__setitem__(k,r(row)['work'][k]+1))
    row_control('work-attempt-counter-bool',success,lambda row:r(row)['work'].update(childAttempts=True))
    for key in ('candidateSlots','destinationSlots','candidateSizeofBytes','destinationSizeofBytes'):
        row_control('storage-'+key,success,lambda row,k=key:r(row)['storage'].__setitem__(k,r(row)['storage'][k]+1))
    for key in ('captureComplete','packetUnchanged','meshesUnchanged','settingsUnchanged','horizonUnchanged','planesUnchanged','gravityUnchanged'):
        row_control('observation-'+key,success,lambda row,k=key:row['observations'].__setitem__(k,False))
    row_control('observation-call-bool',success,lambda row:row['observations'].update(controlledCalls=True))
    row_control('observation-world-unchanged-wrong',success,lambda row:row['observations'].update(worldUnchanged=not row['observations']['worldUnchanged']))
    row_control('observation-progress-unchanged-wrong',success,lambda row:row['observations'].update(progressUnchanged=not row['observations']['progressUnchanged']))
    row_control('pointer-ordinal-bool',success,lambda row:row['observations']['pointerStability']['bodies'][0].update(ordinal=False))
    row_control('pointer-source-ID-bool',success,lambda row:row['observations']['pointerStability']['bodies'][0].update(originalId=True))
    row_control('pointer-address-changed',success,lambda row:row['observations']['pointerStability']['bodies'][0].update(sameOrdinalAddress=False))
    row_control('pointer-storage-integer',success,lambda row:row['observations']['pointerStability'].update(bodyStorageStable=1))
    row_control('pointer-face-tail-missing',success,lambda row:row['observations']['pointerStability']['meshFaceStorageStable'].pop())

    # Non-vacuous actual dyadic sequence; selected by original numeric inputs,
    # not by fixture labels. This is independent real closed form, with only
    # binary-exact chosen translations asserted equal to the actual states.
    analytic=[]
    for row in rows:
        scene=row['input']['scene'];bs=scene['bodies'];ls=row['input']['packet']['loads']
        if len(bs)!=1 or len(ls)!=1 or row['frameOrdinal'] not in (0,1) or not row['report']['committed']:continue
        b=bs[0]
        if ref.fraction(scene['horizon'])!=Fraction(1,16) or ref.fraction(b['mass'])!=2 or any(ref.fraction(v)!=0 for v in scene['gravity']):continue
        force=ls[0]['force']
        if ref.fraction(force[0]) not in (4,-4) or any(ref.fraction(v)!=0 for v in force[1:]):continue
        p,v=ref.exact_translation(b['position'],b['velocity'],b['mass'],force,scene['gravity'],scene['horizon'])
        actual=row['worldAfter']['bodies'][0]
        need(all(ref.fraction(actual['position'][i])==p[i] and ref.fraction(actual['velocity'][i])==v[i] for i in range(3)),'actual dyadic exact translation')
        analytic.append((row['frameOrdinal'],p[0],v[0]))
    need((0,Fraction(1,256),Fraction(1,8)) in analytic and (1,Fraction(1,128),Fraction(0)) in analytic,'both actual dyadic opposite-load analytic ticks')
    positive.append('actual-two-dyadic-opposite-load-ticks-independent-closed-form')
    argv=[sys.executable,'-O',str(CHECKER),str(args.fixture.resolve())]
    if args.development_unpinned:argv.append('--development-unpinned')
    start=time.perf_counter();optimized=subprocess.run(argv,cwd=ROOT,capture_output=True,check=False,timeout=120)
    (out/'optimized.stdout.txt').write_bytes(optimized.stdout);(out/'optimized.stderr.txt').write_bytes(optimized.stderr)
    write('optimized-command.json',{'argv':argv,'exit':optimized.returncode,'seconds':time.perf_counter()-start})
    need(optimized.returncode!=0 and b'normal Python' in optimized.stderr,'actual -O process explicitly refuses protected references')
    controls.append({'name':'optimized-python-rejected','rejected':True,'scope':'Actual separate Python process'})
    result={'status':'PASS','baseline':baseline,'selfTestGroups':len(groups),'selfTests':groups,'negativeControls':len(controls),
        'rejectedControls':controls,'positiveControls':positive,'labelAndOrderIndependent':True,
        'optimizedPythonRejected':{'status':'PASS','exitCode':optimized.returncode},
        'scope':'Copied adversarial JSON metadata/interval controls and actual finite full transaction/analytic references. No production query, artificial intermediate measured World/pointer row, actual C++ allocator/exception/post-child fault injection, or complete clock/commit machine proof.'}
    write('negative-controls.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture',type=Path,nargs='?')
    parser.add_argument('--self-only',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--development-unpinned',action='store_true')
    args=parser.parse_args();need(args.self_only==(args.fixture is None),'Use --self-only or one actual fixture')
    need(__debug__,'Control suite requires normal Python')
    out=args.output.resolve();need(out.is_relative_to(ROOT) and out!=ROOT,'New workspace child output');out.mkdir(parents=True,exist_ok=False)
    watched=[CHECKER,Path(__file__).resolve(),ROOT/'scripts/verify-world-static-mesh-flight-advance.py',
        ROOT/'scripts/verify-world-static-mesh-flight-scheduler.py',ROOT/'scripts/verify-world-static-mesh-flight-guard.py',
        ROOT/'reports/world-static-mesh-flight-advance-recipes/clock-reference.py']
    if args.fixture is not None:watched.append(args.fixture.resolve())
    def stamp(path):
        raw=path.read_bytes();return {'path':path.relative_to(ROOT).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    def write(name,value):(out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    before=[stamp(p) for p in watched];write('source-before.json',before);start=time.perf_counter()
    try:
        groups=self_tests()
        if args.self_only:
            result={'status':'SELF_ONLY_PASS','selfTestGroups':len(groups),'selfTests':groups,'actualNativeFixturesVerified':0,
                'scope':'Original synthetic helper/analytical preparation only; no controlled Native dataset, child query, transaction/commit acceptance or fault injection.'}
            write('self-tests.json',result)
        else:
            result=actual_controls(args,groups,out,write)
    finally:
        after=[stamp(p) for p in watched];write('provenance.json',{'sourceBefore':before,'sourceAfter':after,'sourceStable':before==after,'seconds':time.perf_counter()-start});need(before==after,'Preparation sources unchanged')
    print(json.dumps(result))


if __name__=='__main__':main()
