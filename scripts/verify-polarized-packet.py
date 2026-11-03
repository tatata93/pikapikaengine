#!/usr/bin/env python3
"""Exact-rational acceptance checks for a finite POWER measure, not radiance.

Required Native JSON fixture input, optional WASM JSON, optional hex CSV corpus.
Each JSON number is first a binary64 value and then an exact Fraction.
"""
import argparse
import csv
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

NAMES=('empty identity-bundle normal-plate normal-ghost normal-reflection '
       'noncoplanar-unpolarized noncoplanar-u two-tir all-route-miss all-sensor-miss '
       'mixed-sensor-miss mixed-route-miss sensor-boundary power-prefix-route-miss '
       'parallel-reference near-normal-family invalid-later-stokes invalid-later-ray '
       'invalid-later-shape invalid-sensor uncertain-cone batch-sqrt-budget '
       'evaluation-budget packet-sqrt-budget packet-count-budget step-count-budget '
       'low-refinement zero-power subnormal-power homogeneous inclined-nonunit-sensor '
       'full-sphere spherical-cap zero-power-unknown mixed-known-unknown unavailable-branch').split()

def check(ok,message):
    if not ok:raise ValueError(message)

def keys(x,names):check(type(x) is dict and set(x)==set(names.split()),'object schema mismatch')
def number(x):
    check(type(x) in (int,float) and math.isfinite(x),'finite binary64 number required')
    return float(x)
def integer(x,lo,hi):check(type(x) is int and lo<=x<=hi,'integer outside domain')
def bounds(x):
    check(type(x) is list and len(x)==2,'interval shape')
    a,b=map(number,x);check(a<=b,'reversed interval');return F(a),F(b)
def vector(x,bounded=True):
    check(type(x) is list and len(x)==3,'vector shape')
    for v in x:bounds(v) if bounded else number(v)
def stokes(x):
    check(type(x) is list and len(x)==4,'Stokes shape')
    for v in x:number(v)
def complex_bounds(x):
    check(type(x) is list and len(x)==2,'complex shape');bounds(x[0]);bounds(x[1])
def state(x):
    keys(x,'power diagonal upper');check(bounds(x['power'])[0]>=0,'negative POWER')
    check(type(x['diagonal']) is list and type(x['upper']) is list and len(x['diagonal'])==len(x['upper'])==3,'coherency shape')
    for v in x['diagonal']:check(bounds(v)[0]>=0,'negative diagonal')
    for v in x['upper']:complex_bounds(v)

def bits(x):
    if type(x) in (int,float):return ('n',struct.pack('>d',float(x)))
    if type(x) is list:return [bits(v) for v in x]
    if type(x) is dict:return {k:bits(v) for k,v in x.items()}
    return x

def route_schema(r,step_count):
    keys(r,'status powerFailure geometryStatus completedPowerSteps failedPowerStep counters limited initial segments completion')
    integer(r['status'],0,5);integer(r['powerFailure'],0,5);integer(r['geometryStatus'],-1,7)
    for k in ('completedPowerSteps','failedPowerStep'):integer(r[k],0,64)
    check(r['completedPowerSteps']==r['failedPowerStep'],'power prefix position')
    check(type(r['counters']) is list and len(r['counters'])==4 and type(r['limited']) is bool,'route counter/flag shape')
    for v in r['counters']:integer(v,0,5000000)
    check(r['counters'][0]<=64 and r['counters'][1]<=r['counters'][0],'route geometry queries')
    if r['initial'] is not None:state(r['initial'])
    check(type(r['segments']) is list and len(r['segments'])<=step_count,'route segment shape')
    completed=0
    for j,s in enumerate(r['segments']):
        keys(s,'ordinal branch exactNormal homogeneous s p state')
        check(s['ordinal']==j,'power segment ordinal');integer(s['branch'],0,1)
        check(type(s['exactNormal']) is bool and type(s['homogeneous']) is bool,'power flags')
        for k in ('s','p'):
            if s[k] is not None:complex_bounds(s[k])
        if s['state'] is not None:state(s['state']);completed+=1
    check(completed==r['completedPowerSteps'] and len(r['segments']) in (completed,completed+1),'completed power prefix')
    check((r['completion'] is not None)==(r['status']==0),'route completion/status')
    if r['completion'] is not None:
        c=r['completion'];keys(c,'state origin direction index');state(c['state']);vector(c['origin']);vector(c['direction']);bounds(c['index'])
        check(completed==step_count and r['geometryStatus']==0,'incomplete route completion')
        check(bits(c['state'])==bits(r['segments'][-1]['state'] if completed else r['initial']),'route final state differs from prefix')

def sensor_schema(s):
    keys(s,'status reason rootCount consideredCount sqrt limited discriminant nearest')
    integer(s['status'],0,2);integer(s['reason'],0,18);integer(s['rootCount'],0,2);integer(s['consideredCount'],0,2);integer(s['sqrt'],0,8192)
    check(type(s['limited']) is bool,'sensor limited flag')
    if s['discriminant'] is not None:bounds(s['discriminant'])
    check((s['nearest'] is not None)==(s['status']==0),'sensor nearest/status')
    if s['nearest'] is not None:
        h=s['nearest'];keys(h,'parameter distance position normal incidentNormal frontFace');bounds(h['parameter']);bounds(h['distance']);vector(h['position']);vector(h['normal']);vector(h['incidentNormal']);check(type(h['frontFace']) is bool,'frontFace flag')

def schema(row):
    keys(row,'name input result');q,r=row['input'],row['result']
    keys(q,'packets steps index wavelength sensor settings')
    check(type(q['packets']) is list and len(q['packets'])<=1024,'packet input shape')
    for v in q['packets']:
        keys(v,'origin direction domain power reference');vector(v['origin']);vector(v['direction']);bounds(v['domain']);stokes(v['power']);vector(v['reference'],False)
    check(type(q['steps']) is list and len(q['steps'])<=64,'step input shape')
    for s in q['steps']:
        integer(s.get('kind'),0,2)
        fields=('center normal aperture' if s['kind']==0 else 'center radius' if s['kind']==1 else 'vertex axis radius aperture')
        keys(s,'kind branch nextIndex domain '+fields)
        for k in ('center','normal','vertex','axis'):
            if k in s:vector(s[k],False)
        for k in ('radius','aperture'):
            if k in s:number(s[k])
        integer(s['branch'],0,1);bounds(s['nextIndex']);bounds(s['domain'])
    bounds(q['index']);number(q['wavelength']);keys(q['sensor'],'center normal aperture domain');vector(q['sensor']['center'],False);vector(q['sensor']['normal'],False);number(q['sensor']['aperture']);bounds(q['sensor']['domain'])
    check(type(q['settings']) is list and len(q['settings'])==8,'settings shape')
    for x in q['settings']:number(x)
    keys(r,'status counts queries sqrt limited stats records');integer(r['status'],0,4)
    for name,length in (('counts',6),('queries',3),('sqrt',3)):
        check(type(r[name]) is list and len(r[name])==length,'batch counters shape')
        for x in r[name]:integer(x,0,16000000)
    check(type(r['limited']) is bool and type(r['records']) is list,'batch flags/records')
    check(len(r['records']) in (0,len(q['packets'])),'all admitted packet records required')
    expected_counts=[0]*6;queries=[0]*3;roots=[0]*3;limited=False
    for j,v in enumerate(r['records']):
        keys(v,'ordinal power status sensorPower route sensor');check(v['ordinal']==j,'record ordinal');stokes(v['power']);check(bits(v['power'])==bits(q['packets'][j]['power']),'original watts not retained');integer(v['status'],0,10)
        if v['route'] is not None:
            route_schema(v['route'],len(q['steps']));expected_counts[0]+=1
            c=v['route']['counters'];queries[0]+=c[0];queries[1]+=c[1];roots[0]+=c[2];roots[1]+=c[3];limited=limited or v['route']['limited']
        if v['sensor'] is not None:
            sensor_schema(v['sensor']);queries[2]+=1;roots[2]+=v['sensor']['sqrt'];limited=limited or v['sensor']['limited']
        if v['status'] in (1,2,3,4):expected_counts[v['status']]+=1
        else:expected_counts[5]+=1
        if v['status']==0:check(v['route'] is None and v['sensor'] is None,'not-examined has output')
        check((v['sensorPower'] is not None)==(v['status']==1),'sensor POWER only for accepted packet')
        if v['status']==1:
            bounds(v['sensorPower']);check(v['sensor'] is not None and v['sensor']['status']==0 and v['route'] is not None and v['route']['status']==0,'accepted without full hit')
            check(bits(v['sensorPower'])==bits(v['route']['completion']['state']['power']),'extra cosine/index factor at sensor')
        if v['status']==2:check(v['route']['geometryStatus']==1,'route miss diagnostic absent')
        if v['status']==3:check(v['route']['geometryStatus']==4,'branch unavailable diagnostic absent')
        if v['status']==4:check(v['sensor']['status']==1,'sensor miss diagnostic absent')
    check(r['counts']==expected_counts and r['queries']==queries and r['sqrt']==roots and r['limited']==limited,'aggregate counters differ from records')
    check((r['stats'] is not None)==(r['status']==0),'stats/status mismatch')
    if r['stats'] is not None:
        check(r['counts'][5]==0,'unknown acquired tally');keys(r['stats'],'totalSource acceptedSource detected')
        for x in r['stats'].values():check(bounds(x)[0]>=0,'negative aggregate watts')
        check(bounds(r['stats']['detected'])[1]<=bounds(r['stats']['acceptedSource'])[1]<=bounds(r['stats']['totalSource'])[1],'aggregate passivity')
        check(sum(r['sqrt'])<=q['settings'][7],'completed over batch budget')

def load(path):
    def pairs(xs):
        d={}
        for k,v in xs:check(k not in d,'duplicate JSON key');d[k]=v
        return d
    data=json.loads(Path(path).read_text(encoding='utf-8-sig'),object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
    keys(data,'schema fixtures');check(data['schema']==1,'schema version');rows=data['fixtures']
    check(type(rows) is list and len(rows)==len(NAMES) and [r.get('name') for r in rows]==NAMES,'fixture count/identity/order')
    for row in rows:schema(row)
    packet=bits([{'name':r['name'],'input':r['input']} for r in rows])
    digest=hashlib.sha256(json.dumps(packet,sort_keys=True,separators=(',',':'),default=lambda x:x.hex()).encode()).hexdigest()
    # Filled from the final original acceptance corpus, independent of outputs.
    check(digest==INPUT_SHA,'fixture exact binary64 inputs changed')
    return rows

INPUT_SHA='979351af6d4569997f7beada4edc60115b3fa117afb2a329910d96cb14970d79'
INCLUSIONS=0
def contains(bound,value):
    global INCLUSIONS
    lo,hi=bounds(bound);check(lo<=value<=hi,'independent exact Fraction watt value absent');INCLUSIONS+=1

EXPECTED_RECORDS={
 'empty':[],'identity-bundle':[1,1],'normal-plate':[1,1],'normal-ghost':[1,1],
 'normal-reflection':[1],'noncoplanar-unpolarized':[1],'noncoplanar-u':[1],'two-tir':[1],
 'all-route-miss':[2],'all-sensor-miss':[4],'mixed-sensor-miss':[1,4],'mixed-route-miss':[1,2],
 'sensor-boundary':[7],'power-prefix-route-miss':[2],'parallel-reference':[6],'near-normal-family':[6],
 'invalid-later-stokes':[],'invalid-later-ray':[],'invalid-later-shape':[],'invalid-sensor':[],
 'uncertain-cone':[6],'batch-sqrt-budget':[9,0],'evaluation-budget':[1,0],
 'packet-sqrt-budget':[9,0],'packet-count-budget':[],'step-count-budget':[],
 'low-refinement':[1],'zero-power':[1],'subnormal-power':[1,1],'homogeneous':[1],
 'inclined-nonunit-sensor':[1],'full-sphere':[1],'spherical-cap':[1],
 'zero-power-unknown':[6],'mixed-known-unknown':[1,6],'unavailable-branch':[3]}

def factor(name):
    # Independent normal-incidence power derivation: r=(1-3/2)/(1+3/2),
    # R=r*r=1/25, T=1-R=24/25. Two transmissions / two internal reflections.
    if name in ('normal-plate','mixed-route-miss','subnormal-power','zero-power'):return F(24,25)**2
    if name=='normal-ghost':return F(24,25)**2*F(1,25)**2
    if name=='normal-reflection':return F(1,25)
    if name in ('full-sphere','spherical-cap'):return F(24,25)
    if name in ('noncoplanar-unpolarized','low-refinement'):return F(42544,17294403)
    if name=='noncoplanar-u':return F(322768,259416045)
    return F(1)

def verify(rows):
    for row in rows:
        n,q,r=row['name'],row['input'],row['result'];statuses=[v['status'] for v in r['records']]
        check(statuses==EXPECTED_RECORDS[n],n+': packet classification')
        top=2 if n.startswith('invalid-') else 3 if n.endswith('budget') else 1 if any(s not in (1,2,3,4) for s in statuses) else 0
        check(r['status']==top,n+': batch classification')
        if n.startswith('invalid-'):check(r['counts'][0]==0 and r['stats'] is None,'invalid later input not preflighted')
        for v in r['records']:
            if v['route'] is not None and v['route']['initial'] is not None:contains(v['route']['initial']['power'],F(float(v['power'][0])))
            if v['status']==1:contains(v['sensorPower'],F(float(v['power'][0]))*factor(n))
        if r['stats'] is not None:
            total=sum(F(float(p['power'][0])) for p in q['packets'])
            accepted=sum(F(float(v['power'][0])) for v in r['records'] if v['status']==1)
            contains(r['stats']['totalSource'],total);contains(r['stats']['acceptedSource'],accepted);contains(r['stats']['detected'],accepted*factor(n))
            if accepted==0:check(bounds(r['stats']['detected'])==(F(0),F(0)),'known no arrival gained POWER')
        if n=='power-prefix-route-miss':
            v=r['records'][0];check(v['route']['completedPowerSteps']==1,'diagnostic power prefix lost');contains(v['route']['segments'][0]['state']['power'],F(24,25))
        if n=='low-refinement':check(r['limited'],'valid wide enclosure lost limited flag')
    # Explicitly exclude scalar unpolarized reset and extra cosine at sensor.
    by={r['name']:r for r in rows}
    lo,hi=bounds(by['noncoplanar-unpolarized']['result']['stats']['detected'])
    check(not(lo<=F(1263376,466948881)<=hi),'incorrect per-surface polarization reset accepted')
    lo,hi=bounds(by['inclined-nonunit-sensor']['result']['stats']['detected'])
    check(not(lo<=F(4,5)<=hi),'extra cosine double-count accepted')

ORACLE_HEADER='id,kind,I,Q,U,V,totalLo,totalHi,acceptedLo,acceptedHi,detectedLo,detectedHi'.split(',')
def corpus(path):
    with open(path,encoding='utf-8-sig',newline='') as stream:rows=list(csv.reader(stream))
    check(len(rows)==129 and rows[0]==ORACLE_HEADER,'oracle header/count')
    result=[]
    for j,row in enumerate(rows[1:]):
        check(len(row)==12 and row[0]==str(j) and row[1]==str(j%3),'oracle identity/type/row width')
        v=[]
        for s in row[2:]:
            check(s.lower().startswith(('0x','-0x')),'oracle exact hex binary64 required')
            x=float.fromhex(s);check(math.isfinite(x),'nonfinite oracle');v.append(x)
        watts=F(1)+F(j,128);check(list(map(F,v[:4]))==[watts,F(0),F(0),watts],'oracle Stokes watts changed')
        f=(F(1),F(24,25)**2,F(24,25)**2*F(1,25)**2)[j%3]
        contains(v[4:6],watts);contains(v[6:8],watts);contains(v[8:10],watts*f);result.append(v)
    return result

def main():
    check(__debug__,'Python -O is unsupported: fail closed')
    parser=argparse.ArgumentParser();parser.add_argument('native');parser.add_argument('wasm',nargs='?');parser.add_argument('--oracle');parser.add_argument('--wasm-oracle');args=parser.parse_args()
    rows=load(args.native);verify(rows);matched=False;oracle_rows=0
    if args.wasm:
        other=load(args.wasm);verify(other);check(bits(rows)==bits(other),'Native/WASM fixture binary64 bits differ');matched=True
    if args.oracle:
        o=corpus(args.oracle);oracle_rows=len(o)
        if args.wasm_oracle:check(bits(o)==bits(corpus(args.wasm_oracle)),'Native/WASM oracle bits differ')
    else:check(not args.wasm_oracle,'--wasm-oracle needs --oracle')
    print(json.dumps({'status':'PASS','fixtures':len(rows),'oracleRows':oracle_rows,'independentInclusions':INCLUSIONS,'wasmBitsMatch':matched,'incorrectResetAndCosineExcluded':True}))

if __name__=='__main__':
    try:main()
    except Exception as error:print('FAIL: '+str(error),file=sys.stderr);sys.exit(1)
