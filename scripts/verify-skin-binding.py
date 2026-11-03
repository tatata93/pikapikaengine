#!/usr/bin/env python3
"""Independent finite-corpus skin-binding reference (stdlib only).

Usage: python scripts/verify-skin-binding.py runDirectory | latest.json
JSON numbers are exact binary64 inputs; literal integer -0 is preserved.
No C++/JS FK, inverse, LBS implementation is called. The 90-degree reference
uses exact Fraction authored-weight ratios. Time .5 is parity-only. This is
finite point validation, not an interval or universal precision guarantee.
"""
import argparse
import copy
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

NAMES = ('default','edited-hidden-track','permuted','unicode-signedzero-subnormal-max-id',
         'author-underflow','invalid-inverse-quality','stored-rest-mismatch','rest-fk-overflow')
TIMES = ((0,False),(.5,False),(1,False),(2,False),(3,True))
TOL = F(256,2**52)
MAX_BYTES = 32*1024*1024

def require(ok,text):
    if not ok: raise ValueError(text)

def number_token(text):
    value=float(text)
    require(math.isfinite(value),'nonfinite/overflow JSON number')
    mantissa=re.split('[eE]',text,1)[0]
    require(value!=0 or not any(c in '123456789' for c in mantissa),'nonzero JSON decimal underflow')
    return value

def object_pairs(pairs):
    out={}
    for k,v in pairs:
        require(k not in out,'duplicate JSON key: '+k)
        out[k]=v
    return out

def inspect_tree(value,depth=0,counter=None):
    if counter is None: counter=[0]
    counter[0]+=1
    require(depth<=32 and counter[0]<=2000000,'JSON tree budget')
    if isinstance(value,str): value.encode('utf-8',errors='strict')
    elif type(value) is float: require(math.isfinite(value),'nonfinite tree value')
    elif type(value) is dict:
        for k,v in value.items():
            require(isinstance(k,str),'JSON key type');k.encode('utf-8',errors='strict');inspect_tree(v,depth+1,counter)
    elif type(value) is list:
        for v in value: inspect_tree(v,depth+1,counter)
    else: require(value is None or type(value) is bool,'unknown JSON value type')

def loads(text):
    require(len(text.encode('utf-8'))<=MAX_BYTES,'JSON byte budget')
    def constant(t): raise ValueError('nonfinite JSON constant '+t)
    out=json.loads(text,parse_int=number_token,parse_float=number_token,
                   parse_constant=constant,object_pairs_hook=object_pairs)
    inspect_tree(out);return out

def load(path):
    b=Path(path).read_bytes();require(len(b)<=MAX_BYTES,'JSON file byte budget')
    return loads(b.decode('utf-8',errors='strict'))

def keys(value,expected,label):
    require(type(value) is dict and set(value)==set(expected),label+' fields')

def integer(value):return type(value) is float and math.isfinite(value) and value.is_integer()

def bit_tree(x):
    if type(x) in (float,int):
        require(math.isfinite(x),'nonfinite bit value');return {'f64':struct.pack('>d',float(x)).hex()}
    if type(x) is list:return [bit_tree(v) for v in x]
    if type(x) is dict:return {k:bit_tree(v) for k,v in sorted(x.items())}
    require(x is None or type(x) in (bool,str),'bit tree type');return x

def numeric_count(x):
    if type(x) in (float,int):return 1
    if type(x) is list:return sum(numeric_count(v) for v in x)
    if type(x) is dict:return sum(numeric_count(v) for v in x.values())
    return 0

def same_bits(a,b,label):require(bit_tree(a)==bit_tree(b),label+' binary64 bits differ')

def identity(tx=0):return [1,0,0,0,0,1,0,0,0,0,1,0,tx,0,0,1]
def trs(p=None,q=None,s=None):return {'position':p or [0,0,0],'rotation':q or [0,0,0,1],'scale':s or [1,1,1]}
def expected_sources():
    bones=[{'id':19,'name':'Child','parentId':7,'rest':trs([1,0,0])},
           {'id':7,'name':'Root','parentId':0,'rest':trs()}]
    base={'version':1,'kind':'mesh-skin-binding','name':'Original arm binding','units':'m-s-kg',
          'axes':'right-handed-y-up','space':'mesh-local-is-skeleton',
          'target':{'objectId':'arm-mesh','nativeId':'42'},'fingerprint':'9da65482c00e78b0',
          'mesh':{'version':1,'positions':[[0,-.2,0],[1,-.2,0],[2,-.2,0],[0,.2,0],[1,.2,0],[2,.2,0]],
                  'triangles':[[0,1,4],[0,4,3],[1,2,5],[1,5,4]]},
          'influences':[[{'boneId':7,'weight':1}],[{'boneId':19,'weight':1},{'boneId':7,'weight':1}],
                        [{'boneId':19,'weight':1}],[{'boneId':7,'weight':1}],
                        [{'boneId':19,'weight':1},{'boneId':7,'weight':1}],[{'boneId':19,'weight':1}]],
          'joints':[{'id':19,'restWorld':identity(1),'inverseBind':identity(-1)},
                    {'id':7,'restWorld':identity(),'inverseBind':identity()}],
          'restBones':[{k:copy.deepcopy(b[k]) for k in ('id','parentId','rest')} for b in bones],
          'motion':{'version':1,'kind':'skeletal-motion','name':'Original arm motion','bones':bones,
                    'clip':{'name':'Bend','duration':2,'tracks':[{'boneId':19,'interpolation':'linear',
                    'keys':[{'time':t,**trs([1,0,0],[0,0,1,1] if t==1 else [0,0,0,1])} for t in (0,1,2)]}]}}}
    out=[base];edited=copy.deepcopy(base);edited['influences'][1][0]['weight']=3
    edited['motion']['clip']['tracks'].append({'boneId':7,'interpolation':'step','keys':[{'time':t,**trs()} for t in (0,2)]});out.append(edited)
    permuted=copy.deepcopy(edited)
    for k in ('joints','restBones'):permuted[k].reverse()
    permuted['motion']['bones'].reverse();permuted['motion']['clip']['tracks'].reverse()
    for w in permuted['influences']:w.reverse()
    out.append(permuted)
    tiny=copy.deepcopy(base);tiny['name']='原本🙂 "quote" \\';tiny['target']={'objectId':'腕🙂','nativeId':'9007199254740991'}
    tiny['mesh']['positions'][0][0]=-0.;tiny['influences'][0][0]['weight']=float.fromhex('0x0.0000000000001p-1022')
    tiny['influences'][1][1]['weight']=-0.;tiny['joints'][0]['inverseBind'][2]=-0.;tiny['joints'][0]['restWorld'][2]=-0.;tiny['restBones'][0]['rest']['rotation'][0]=-0.;out.append(tiny)
    underflow=copy.deepcopy(base);underflow['influences'][1]=[{'boneId':19,'weight':sys.float_info.max},{'boneId':7,'weight':float.fromhex('0x0.0000000000001p-1022')}];out.append(underflow)
    inverse=copy.deepcopy(base);inverse['joints'][0]['inverseBind'][0]=2;out.append(inverse)
    mismatch=copy.deepcopy(base);mismatch['joints'][0]['restWorld'][12]=2;out.append(mismatch)
    huge=copy.deepcopy(base);huge['motion']['bones']=[{'id':i+1,'name':'Overflow '+str(i),'parentId':i,'rest':trs(s=[1e6,1e6,1e6])} for i in range(128)]
    huge['motion']['clip']['tracks']=[];huge['restBones']=[{k:copy.deepcopy(b[k]) for k in ('id','parentId','rest')} for b in huge['motion']['bones']]
    huge['joints']=[{'id':b['id'],'restWorld':identity(),'inverseBind':identity()} for b in huge['motion']['bones']]
    huge['influences']=[[{'boneId':1,'weight':1}] for p in huge['mesh']['positions']];out.append(huge)
    return out

def mesh_fingerprint(mesh):
    # Independent struct packing, distinct from engine shift/DataView code.
    data=bytearray(b'pikapika_mesh_fingerprint 1\n')
    data.extend(struct.pack('<III',int(mesh['version']),len(mesh['positions']),len(mesh['triangles'])))
    for p in mesh['positions']:
        for x in p:data.extend(struct.pack('<d',0. if x==0 else x))
    for tri in mesh['triangles']:data.extend(struct.pack('<III',*(int(x) for x in tri)))
    value=0xcbf29ce484222325
    for b in data:value=((value^b)*0x100000001b3)&0xffffffffffffffff
    return format(value,'016x')

def analytic_source(source):
    # Assert the derivation's domain independently, never assume arbitrary keys
    # happen to represent an identity/90-degree pivot animation.
    bones={int(b['id']):b for b in source['motion']['bones']}
    require(set(bones)=={7,19},'analytic two bone IDs')
    require(bones[7]['parentId']==0 and bones[7]['rest']==trs(),'analytic root rest')
    require(bones[19]['parentId']==7 and bones[19]['rest']==trs([1,0,0]),'analytic child rest')
    require(source['motion']['clip']['duration']==2,'analytic duration')
    tracks={int(t['boneId']):t for t in source['motion']['clip']['tracks']}
    require(19 in tracks and set(tracks)<={7,19},'analytic track IDs')
    child=tracks[19];require(child['interpolation']=='linear' and child['keys']==[{'time':t,**trs([1,0,0],[0,0,1,1] if t==1 else [0,0,0,1])} for t in (0,1,2)],'analytic exact child keys')
    if 7 in tracks:require(tracks[7]=={'boneId':7,'interpolation':'step','keys':[{'time':t,**trs()} for t in (0,2)]},'analytic hidden root identity track')
    joints={int(j['id']):j for j in source['joints']}
    for i in (7,19):require(joints[i]['restWorld']==identity(i==19) and joints[i]['inverseBind']==identity(-1 if i==19 else 0),'analytic rest/inverse matrices')

def reference_point(p,weights,quarter_turn):
    x,y,z=map(F,p);total=sum((F(w['weight']) for w in weights),F(0));require(total>0,'analytic weight sum')
    out=[F(0)]*3
    for w in weights:
        transformed=(1-y,x-1,z) if quarter_turn and w['boneId']==19 else (x,y,z)
        for k in range(3):out[k]+=F(w['weight'])/total*transformed[k]
    return out

def result_schema(result,source,status):
    keys(result,('status','positions','diagnostics','weightResiduals'),'model result')
    require(result['status']==status,'model classification/status')
    ids=[j['id'] for j in source['joints']];expected_ids=ids[:1] if status=='ill_conditioned' else ids
    require(type(result['diagnostics']) is list and len(result['diagnostics'])==len(expected_ids),'diagnostic prefix length')
    for d,i in zip(result['diagnostics'],expected_ids):
        keys(d,('id','condition','residual','pivotFailure'),'diagnostic');require(d['id']==i and d['pivotFailure'] is False,'diagnostic identity')
        require(type(d['id']) is float and type(d['condition']) is float and type(d['residual']) is float and d['condition']==(2 if status=='ill_conditioned' else 1) and d['residual']==(2 if status=='ill_conditioned' else 0),'known inverse condition/residual')
    require(type(result['weightResiduals']) is list,'weight residual array')
    expected_residuals=0 if status=='ill_conditioned' else 1 if status=='numerical_failure' else 6
    require(len(result['weightResiduals'])==expected_residuals and all(type(v) is float and v==0 for v in result['weightResiduals']),'normalization residual prefix')
    if status=='completed':
        require(type(result['positions']) is list and len(result['positions'])==6,'completed position count')
        for p in result['positions']:require(type(p) is list and len(p)==3 and all(type(x) is float and math.isfinite(x) for x in p),'finite position3')
    else:require(result['positions'] is None,'failure has no partial positions')

def basename(path):return path.replace('\\','/').rsplit('/',1)[-1]

def verify(run):
    data=load(run/'outputs.json');keys(data,('schema','fixtures'),'output root');require(integer(data['schema']) and data['schema']==1,'output schema')
    require(type(data['fixtures']) is list and len(data['fixtures'])==8,'fixed eight fixture count')
    require([f.get('name') if type(f) is dict else None for f in data['fixtures']]==list(NAMES),'fixed unique fixture identities/order')
    expected=expected_sources();source_numbers=result_numbers=bit_numbers=point_checks=0;max_abs=F(0);max_scaled=F(0);max_at='';fingerprints=[]
    commands=load(run/'commands.json');require(type(commands) is list and len(commands)==57,'command corpus count')
    counts={'completed':0,'numerical_failure':0,'ill_conditioned':0};exceptions=0
    for index,(record,oracle) in enumerate(zip(data['fixtures'],expected)):
        keys(record,('name','input','roundtrip','inputBits','roundtripBits','samples'),'fixture');name=record['name'];source=record['input']
        keys(source,oracle.keys(),name+' source');keys(source['mesh'],('version','positions','triangles'),name+' mesh')
        fingerprint=mesh_fingerprint(source['mesh']);require(fingerprint==source['fingerprint']=='9da65482c00e78b0',name+' independent FNV64');fingerprints.append(fingerprint)
        same_bits(source,oracle,name+' fixed complete input corpus');same_bits(record['roundtrip'],source,name+' roundtrip')
        require(record['inputBits']==bit_tree(source) and record['roundtripBits']==bit_tree(record['roundtrip']),name+' captured source bit tree')
        raw=load(run/(name+'.json'));same_bits(raw,source,name+' raw JSON');n=numeric_count(source);source_numbers+=3*n;bit_numbers+=2*n
        require(type(record['samples']) is list and len(record['samples'])==5,'five fixed samples')
        if index<4:analytic_source(source)
        for command_index,verb in ((index*7,'roundtrip'),(index*7+1,'match')):
            c=commands[command_index];keys(c,('command','exitCode','stdout','stderr','error'),'command');require(type(c['command']) is list and len(c['command'])==4 and all(type(x) is str for x in c['command']) and c['command'][1]==verb and integer(c['exitCode']) and c['exitCode']==0 and c['error'] is None and c['stderr']=='','source roundtrip/context command')
            require(basename(c['command'][2])==name+('.skin' if verb=='roundtrip' else '-roundtrip.skin'),'command input identity')
            require(basename(c['command'][3])==name+('-roundtrip.skin' if verb=='roundtrip' else '.scene'),'command output identity')
            if verb=='roundtrip':require(c['stdout']=='','roundtrip stdout')
            else:require(loads(c['stdout'])=={'matches':True,'nativeId':source['target']['nativeId'],'browserAliasNotInterpreted':True},'actual native context match')
        for j,(sample,(seconds,loop)) in enumerate(zip(record['samples'],TIMES)):
            require(type(sample) is dict and type(sample.get('seconds')) is float and sample['seconds']==seconds and sample.get('loop') is loop,'sample time/mode identity')
            c=commands[index*7+2+j];keys(c,('command','exitCode','stdout','stderr','error'),'sample command');args=c['command']
            require(type(args) is list and len(args)==(5 if loop else 4) and all(type(x) is str for x in args) and args[1]=='sample' and basename(args[2])==name+'-roundtrip.skin' and number_token(args[3])==seconds and (not loop or args[4]=='loop') and c['error'] is None and integer(c['exitCode']),'sample command identity')
            if index>=6:
                keys(sample,('seconds','loop','classification','nativeExit'),'source quality sample');require(sample['classification']=='source-quality-exception' and integer(sample['nativeExit']) and sample['nativeExit']==c['exitCode']==1,'source quality failure classification');require(c['stdout']=='' and type(c['stderr']) is str and c['stderr'].startswith('ERROR Skin stored restWorld' if index==6 else 'ERROR Skin rest FK'),'native source-quality diagnostic');exceptions+=1;continue
            keys(sample,('seconds','loop','classification','native','web','nativeBits','webBits'),'model sample');require(sample['classification']=='actual-cpp-model-result' and c['exitCode']==0 and c['stderr']=='','model process classification')
            status='completed' if index<4 else 'numerical_failure' if index==4 else 'ill_conditioned'
            for key in ('native','web'):result_schema(sample[key],source,status)
            same_bits(sample['native'],sample['web'],name+' model parity');require(sample['nativeBits']==bit_tree(sample['native']) and sample['webBits']==bit_tree(sample['web']),name+' captured result bit tree')
            same_bits(loads(c['stdout']),sample['native'],name+' actual native stdout');n=numeric_count(sample['native']);result_numbers+=n;bit_numbers+=2*n;counts[status]+=1
            if index<4 and seconds!=.5:
                for v,(p,w,actual) in enumerate(zip(source['mesh']['positions'],source['influences'],sample['native']['positions'])):
                    for component,(truth,value) in enumerate(zip(reference_point(p,w,seconds in (1,3)),actual)):
                        error=abs(F(value)-truth);scaled=error/max(F(1),abs(truth));require(scaled<=TOL,f'{name} t{seconds} v{v} c{component}: independent affine point error');point_checks+=1
                        if error>max_abs:max_abs=error;max_at=f'{name}/t{seconds}/vertex{v}/component{component}'
                        max_scaled=max(max_scaled,scaled)
    final=commands[-1];keys(final,('command','exitCode','stdout','stderr','error'),'preserve command');require(type(final['command']) is list and len(final['command'])==4 and all(type(x) is str for x in final['command']) and final['command'][1]=='roundtrip' and basename(final['command'][2])=='default.skin' and basename(final['command'][3])=='preserve.skin' and integer(final['exitCode']) and final['exitCode']!=0 and final['error'] is None and type(final['stderr']) is str and final['stderr'].startswith('ERROR '),'existing output refusal command')
    require((run/'preserve.skin').read_bytes()==b'existing output must remain\n','existing output preservation')
    require(point_checks==288 and counts=={'completed':20,'numerical_failure':5,'ill_conditioned':5} and exceptions==10,'complete analytic/classification coverage')
    require(source_numbers==26322 and result_numbers==650,'fixed numerical corpus counts')
    report=load(run/'report.json');keys(report,('schema','status','runDirectory','sourceFixtures','modelEvaluations','modelStatusCounts','sourceFailureEvaluations','matchingSourceNumbers','matchingResultNumbers','sourceArtifacts','wasmBytes','wasmSHA256','scope'),'report')
    require(all(integer(report[k]) for k in ('schema','sourceFixtures','modelEvaluations','sourceFailureEvaluations','matchingSourceNumbers','matchingResultNumbers','wasmBytes')) and report['schema']==1 and report['status']=='PASS' and report['sourceFixtures']==8 and report['modelEvaluations']==30 and report['sourceFailureEvaluations']==10 and report['modelStatusCounts']==counts and report['matchingSourceNumbers']==source_numbers and report['matchingResultNumbers']==result_numbers,'reconstructed JS report counters')
    require(type(report['runDirectory']) is str and type(report['scope']) is str and type(report['wasmSHA256']) is str and re.fullmatch('[0-9a-f]{64}',report['wasmSHA256']) is not None,'report metadata')
    require(type(report['sourceArtifacts']) is list and len(report['sourceArtifacts'])==8,'report source artifacts')
    paths=[]
    for a in report['sourceArtifacts']:
        keys(a,('path','bytes','sha256'),'source artifact');require(type(a['path']) is str and integer(a['bytes']) and a['bytes']>0 and type(a['sha256']) is str and re.fullmatch('[0-9a-f]{64}',a['sha256']) is not None,'artifact metadata');paths.append(a['path'])
    require(len(set(paths))==8,'unique artifact paths')
    return {'schema':1,'status':'PASS','fixtures':8,'sourceNumbersMatched':source_numbers,'modelResultNumbersMatched':result_numbers,'capturedBitTreeNumericLeavesChecked':bit_numbers,'nativeStdoutModelResults':30,'modelStatusCounts':counts,'sourceQualityExceptions':exceptions,'independentFNV64':fingerprints,'analyticSources':list(NAMES[:4]),'analyticTimes':[0,1,2,3],'analyticPointComponents':point_checks,'parityOnlyTime':.5,'maximumAbsoluteError':float(max_abs),'maximumScaledError':float(max_scaled),'maximumAbsoluteErrorAt':max_at,'scaledTolerance':float(TOL),'scope':'Exact binary64 inputs reconstructed as Fraction; finite known identity/90-degree pivot corpus. Not an interval enclosure or arbitrary-input error theorem. Time0.5 is parity only; quality failures are not successful points.'}

def main():
    require(__debug__,'Python -O is rejected; checker must run without optimization')
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');args=p.parse_args();target=Path(args.run)
    if target.is_file():
        latest=load(target);require(type(latest) is dict and type(latest.get('runDirectory')) is str,'latest.json runDirectory');path=Path(latest['runDirectory']);require(not path.is_absolute() and '..' not in path.parts,'latest runDirectory must be repository relative');target=path
    require(target.is_dir(),'runDirectory must exist');print(json.dumps(verify(target),indent=2,allow_nan=False))

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,IndexError,OverflowError,OSError,UnicodeError,RecursionError,struct.error) as error:
        print('FAIL '+str(error),file=sys.stderr);sys.exit(1)
