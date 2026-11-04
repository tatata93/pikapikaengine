"""Independent flight C ABI packets, complete decoding and Fraction audit.

Only exchange-accepted ACTUAL packets are decoded into model results. Host
rejections retain their source identities and never receive a Native model fill.
The expected wire encoder and wire-to-model decoder are separate authored paths.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
legacy=module('flight_legacy_wire','verify-sphere-triangle-mesh-trajectory-native-sdk.py')
held=module('flight_held_fraction','check-sphere-triangle-mesh-held-load.py')
guard=module('flight_guard_fraction','check-sphere-triangle-mesh-free-flight-guard.py')
need,fields,bits=held.need,held.fields,legacy.bits
flatten,optional,work=legacy.flatten,legacy.optional,legacy.work
Compare,signed_json,write_new,file_info=legacy.Compare,legacy.signed_json,legacy.write_new,legacy.file_info
HS=['entry_window','separated','initial_penetration','not_certified','invalid_input','unsupported_environment','numerical_failure']
HR=['none','settings','surface_count','surface_id','duplicate_id','input_domain','surface_budget','mesh_query_failed','initial_boundary','evaluation_budget','leaf_budget','depth_budget','sqrt_budget','time_resolution','nonfinite_intermediate','allocation_failure','environment','coverage_inconsistent','body_not_found','body_invalid','unsupported_body','derived_domain']
GS=['certified_separated','not_certified','invalid_input','unsupported_environment','numerical_failure']
GR=['none','settings','body_not_found','body_invalid','unsupported_body','input_domain','surface_count','surface_id','duplicate_id','surface_budget','flight_tube_failure','derived_domain','inflated_radius_domain','propagation_failure','candidate_invalid','endpoint_tube_failure','held_load_not_separated','environment','allocation_failure','nonfinite_intermediate','coverage_inconsistent']
AK=['initial_point','cell'];AO=['pending','initial_separated','initial_penetration','initial_uncertain','separated','split','unresolved'];LS=['unqueried','certified','unresolved','current']
WORK=['meshQueries','primitiveQueries','candidatesExamined','primitiveSqrtRefinements','enclosureSqrtRefinements','sqrtRefinements','sqrtRefinementsUpper','meshSqrtLimitedRows','enclosureSqrtCalls','enclosureSqrtLimitedCalls','workExact']
INTERVALS=['distance','displacementSquaredBound','errorSquaredBound','displacementRoot','errorRoot','clearanceCertificate','penetrationCertificate']
COUNTS={0:None,1:14,2:None,3:48,4:32,5:32,6:24,7:40,8:32,9:8,10:8,11:8,12:64,13:6,14:8,15:4,16:4,17:6,18:18,19:14,20:2}
ROW_KEYS={'cohort','name','mode','input','inputBits','triangles','triangleBits','beginStatus','appendStatuses','exchangeStatus','failedPhase','hostFailurePreserved','summary','summaryBits','packets','lastMeshSummary','lastMeshSummaryBits','lastMeshRows','outputBefore','outputBeforeBits','outputAfter','outputAfterBits'}

def enum(x,values):
    need(type(x)is str and x in values,'known model enum');return values.index(x)

def settings_values(s):
    p=s['mesh']['primitive']
    return [s['mesh']['maxSurfaces']]+[p[k] for k in legacy.PRIMITIVE_SETTINGS]+[s[k] for k in ['timeTolerance','maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements','maxTotalSqrtRefinements']]

def body_values(b):
    return [b['id'],int(b['isStatic']),b['mass'],b['radius']]+b['inertiaDiagonal']+b['position']+b['orientation']+b['velocity']+b['angularMomentum']+b['force']+b['torque']+[b['material']['restitution'],b['material']['friction']]

def held_values(s):
    b=s['sphere'];return [b['id']]+b['position']+b['velocity']+[b['mass']]+b['force']+b['gravity']+[b['radius'],s['horizon']]+settings_values(s['settings'])+[0]*3

def query_values(s,mode):
    if mode==0:return held_values(s)
    return body_values(s['body'])+s['gravity']+[s['horizon']]+settings_values(s['settings']['heldLoad'])+[s['settings']['maxAngularIncrement'],0,0]

def source_values(s):return [[t['id']]+flatten(t['vertices']) for t in s['triangles']]
def cell(c):return c['timeBounds']+[c['depth']]
def held_header(h,n):
    return [enum(h['status'],HS),enum(h['reason'],HR),n,int(h['snapshot'] is not None)]+optional(None if h['failedIndex'] is None else [h['failedIndex']],1)+[int(h['worldBody'] is not None),int(h['acceleration'] is not None),int(h['wholePathBounds'] is not None),int(h['wholeVelocityBounds'] is not None),int(h['initial'] is not None),int(h['initialSeparationProven']),len(h['certifiedLeaves']),len(h['partition']),len(h['frontier']),len(h['audits'])]+optional(h['safePrefix'],2)+[int(h['bestWitness'] is not None),int(h['window'] is not None),len(h['candidateSurfaceIds']),int(h['current'] is not None),int(h['lastMesh'] is not None)]+optional(None if h['lastMeshAuditIndex'] is None else [h['lastMeshAuditIndex']],1)+[h['partitionLeaves'],h['maximumDepth']]+work(h['work'])+[0]*9

def audit_values(a,index):
    values=[index,enum(a['kind'],AK)]+cell(a['cell'])+[a['time'],enum(a['outcome'],AO)]
    for key in ['pathBounds','pointBounds']:values+=optional(None if a[key] is None else flatten(a[key]),6)
    values+=optional(a['anchor'],3)+[int(a['meshQueried'])]
    for key in ['meshStatus','meshReason']:values+=optional(None if a[key] is None else [a[key]],1)
    for key in INTERVALS:values+=optional(a[key],2)
    return values+work(a['work'])+[0]*2

def expected_wire(s,mode,r):
    h=r if mode==0 else r['inflated'];n=len(s['triangles']);entries=[]
    def add(kind,values,index=0):entries.append({'kind':kind,'index':index,'values':values,'bits':[bits(x) for x in values]})
    summary=[mode,enum(r['status'],HS if mode==0 else GS),enum(r['reason'],HR if mode==0 else GR),n,int(r['snapshot'] is not None)]+optional(None if r['failedIndex'] is None else [r['failedIndex']],1)+[int(r['worldBody'] is not None),int(mode==1 and r['tube'] is not None)]+optional(None if mode==0 or r['flightFailure'] is None else [r['flightFailure']],1)+[int(mode==1 and r['candidateEvaluated']),int(mode==1 and r['endpoint'] is not None),int(mode==1 and h is not None),int(mode==1 and r['candidate'] is not None),int(h is not None)]+[0]*8
    add(0,query_values(s,mode))
    last=None if h is None else h['lastMesh']
    for i,values in enumerate(legacy.source_packets(s,last)):add(1,values,i)
    if r['snapshot'] is not None:
        snap=r['snapshot']
        add(2,held_values({'sphere':snap['input'],'horizon':snap['horizon'],'settings':snap['settings']}) if mode==0 else query_values(snap,1))
    if h is not None:add(3,held_header(h,n))
    if h is not None and h['snapshot'] is not None:
        snap=h['snapshot'];add(4,held_values({'sphere':snap['input'],'horizon':snap['horizon'],'settings':snap['settings']}))
    if r['worldBody'] is not None:add(5,body_values(r['worldBody']['body'])+r['worldBody']['gravity']+[0])
    if mode==1 and r['tube'] is not None:
        t=r['tube'];add(6,t['nominalAcceleration']+flatten(t['exactAcceleration'])+flatten(t['accelerationDifference'])+[t['positionError'],t['roundoff'],t['guardRadius']]+[0]*6)
    if mode==1 and r['endpoint'] is not None:
        e=r['endpoint'];add(7,[x for k in ['nominalPosition','nominalAllowed','exactPosition','exactAllowed','exactDifference'] for x in flatten(e[k])]+e['l1ErrorBound']+[int(e[k]) for k in ['nominalContained','exactContained','l1WithinTube']]+[0]*5)
    if mode==1 and r['candidate'] is not None:add(8,body_values(r['candidate'])+[0]*4)
    if h is not None:
        for kind,key in [(9,'acceleration'),(10,'wholePathBounds'),(11,'wholeVelocityBounds')]:
            if h[key] is not None:add(kind,[0]+flatten(h[key])+[0])
        for i,a in enumerate(h['audits']):add(12,audit_values(a,i),i)
        for i,l in enumerate(h['certifiedLeaves']):add(13,cell(l['cell'])+l['lowerGapCertificate']+[l['auditIndex']],i)
        for i,l in enumerate(h['partition']):add(14,[i]+cell(l['cell'])+[enum(l['state'],LS)]+optional(None if l['auditIndex'] is None else [l['auditIndex']],1)+[enum(l['blockedReason'],HR)],i)
        for i,c in enumerate(h['frontier']):add(15,[i]+cell(c),i)
        if h['current'] is not None:add(16,[0]+cell(h['current']))
        if h['initial'] is not None:
            p=h['initial'];add(17,[0]+p['lowerGapCertificate']+p['upperGapCertificate']+[p['auditIndex']])
        if h['bestWitness'] is not None:
            w=h['bestWitness'];add(18,[0]+cell(w['cell'])+[w['time']]+flatten(w['exactPathBounds'])+w['anchor']+[w['errorUpper']]+w['upperGapCertificate']+[w['auditIndex']])
        if h['window'] is not None:
            w=h['window'];add(19,[0]+w['timeBounds']+w['timeWidth']+flatten(w['pathBounds'])+w['l1DiameterBound']+[w['witnessAuditIndex']])
        for i,identifier in enumerate(h['candidateSurfaceIds']):add(20,[i,identifier],i)
    mesh_summary=None if last is None else legacy.mesh_header(last,n)
    rows=[]
    if last is not None:
        for i,row in enumerate(last['rows']):
            q=row['query'];p=None if q is None else legacy.primitive_packet(q,row['triangle']['id'])
            cs=[] if q is None else [legacy.candidate_packet(c) for c in q['candidates']]
            rows.append({'rowOrdinal':i,'packet':p,'bits':None if p is None else list(map(bits,p)),
                         'candidates':cs,'candidateBits':[list(map(bits,c)) for c in cs]})
    return summary,entries,mesh_summary,rows

def host_path(s,mode):
    rows=source_values(s)
    if len(rows)>64:return 1,[],1,'begin'
    appends=[]
    for offset in range(0,len(rows),6):
        ok=all(type(x[0])is int and 1<=x[0]<=2**53-1 for x in rows[offset:offset+6])
        appends.append(0 if ok else 1)
        if not ok:return 0,appends,1,'append'
    values=query_values(s,mode)
    for x in values:legacy.numeric(x)
    ids=values[0]
    settings_start=16 if mode==0 else 32
    ints=[settings_start+i for i in [0,1,2,3,8,9,10,11,12]]
    ok=1<=ids<=2**53-1 and int(ids)==ids
    ok=ok and all(0<=values[i]<=2**32-1 and int(values[i])==values[i] for i in ints)
    ok=ok and all(bits(x)==bits(0) for x in values[29 if mode==0 else 46:])
    if mode:ok=ok and values[1] in [0,1]
    return 0,appends,0 if ok else 1,None if ok else 'query'

def rows_text(corpus):
    lines=['pikapika_sphere_triangle_mesh_flight_sdk 1',f'cases {len(corpus)}']
    for cohort,fixture,mode in corpus:
        name=fixture['name'];need(re.fullmatch('[A-Za-z0-9_-]{1,96}',name),'bounded fixture identity')
        values=query_values(fixture['input'],mode);sources=source_values(fixture['input'])
        lines.append(json.dumps(cohort)+' '+json.dumps(name)+f' {mode} {len(sources)} '+' '.join(signed_json(x) for x in values))
        lines.extend(' '.join(signed_json(x) for x in row) for row in sources)
    need(all(len(line.encode('ascii'))<=8192 for line in lines),'bounded ASCII lines')
    return ('\n'.join(lines)+'\n').encode('ascii')

def meta(x,maximum=2**53-1):
    legacy.numeric(x);need(x==int(x) and 0<=x<=maximum and not (x==0 and bits(x)!=bits(0)),'canonical bounded F64 integer metadata')
    return int(x)
def input_meta(x,maximum=2**32-1):
    legacy.numeric(x);need(x==int(x) and 0<=x<=maximum,'exchange integer preserves raw -0 then converts to Native +0');return int(x)
def flag(x):return bool(meta(x,1))
def pad(values):need(all(bits(x)==bits(0) for x in values),'unused payload/padding is POSITIVE zero')
def choose(x,values):return values[meta(x,len(values)-1)]
def b3(values):need(len(values)==6,'Bounds3 six values');return [list(values[i:i+2]) for i in range(0,6,2)]
def opt(values,offset,length):
    present=flag(values[offset]);payload=values[offset+1:offset+1+length]
    if not present:pad(payload);return None
    return list(payload)
def time_cell(values):return {'timeBounds':list(values[:2]),'depth':meta(values[2],32)}
def body_decode(v,raw=False):
    need(len(v)==28,'body28')
    return {'id':meta(v[0]),'isStatic':bool(input_meta(v[1],1)) if raw else flag(v[1]),'mass':v[2],'radius':v[3],
            'inertiaDiagonal':v[4:7],'position':v[7:10],'orientation':v[10:14],
            'velocity':v[14:17],'angularMomentum':v[17:20],'force':v[20:23],'torque':v[23:26],
            'material':{'restitution':v[26],'friction':v[27]}}
def settings_decode(v,raw=False):
    convert=input_meta if raw else meta
    p={k:(convert(v[i+1],2**32-1) if i<3 else v[i+1]) for i,k in enumerate(legacy.PRIMITIVE_SETTINGS)}
    return {'mesh':{'maxSurfaces':convert(v[0],2**32-1),'primitive':p},'timeTolerance':v[7],
            **{k:convert(v[i],2**32-1) for i,k in enumerate(['maxEvaluations','maxLeaves','maxDepth','enclosureSqrtRefinements','maxTotalSqrtRefinements'],8)}}
def input_decode(v,mode,triangles,raw=False):
    if mode==0:
        need(len(v)==32,'held input32');pad(v[29:])
        return {'sphere':{'id':meta(v[0]),'position':v[1:4],'velocity':v[4:7],'mass':v[7],'force':v[8:11],'gravity':v[11:14],'radius':v[14]},
                'horizon':v[15],'triangles':copy.deepcopy(triangles),'settings':settings_decode(v[16:29],raw)}
    need(len(v)==48,'guard input48');pad(v[46:])
    return {'body':body_decode(v[:28],raw),'gravity':v[28:31],'horizon':v[31],'triangles':copy.deepcopy(triangles),
            'settings':{'heldLoad':settings_decode(v[32:45],raw),'maxAngularIncrement':v[45]}}
def work_decode(v):
    need(len(v)==11,'Work11');return {k:(flag(x) if k=='workExact' else meta(x,16777216)) for k,x in zip(WORK,v)}

class Packets:
    def __init__(self,row):
        self.row=row;self.values={};self.used=set();last=(-1,-1)
        for p in row['packets']:
            fields(p,{'kind','index','values','bits'},'owned raw record')
            need(type(p['kind'])is int and type(p['index'])is int,'packet identity integer token')
            key=(p['kind'],p['index']);need(key>last and key not in self.values,'all kinds/indices strictly ascending, no duplicates');last=key
            need(p['kind'] in COUNTS and type(p['values'])is list,'known packet kind')
            length=COUNTS[p['kind']] or (32 if row['mode']==0 else 48)
            need(len(p['values'])==length,'exact getter packet count')
            need(type(p['bits'])is list and len(p['bits'])==length,'exact getter bit count')
            for x,h in zip(p['values'],p['bits']):need(bits(x)==h,'raw packet bit integrity')
            self.values[key]=p['values']
    def get(self,kind,index=0,present=True):
        key=(kind,index)
        if not present:need(key not in self.values,'absent optional getter has no fabricated packet');return None
        need(key in self.values,'missing actual getter');self.used.add(key);return self.values[key]
    def finish(self):need(self.used==set(self.values),'no ignored extra/partial records')

def primitive_decode(v,candidates):
    need(len(v)==58,'primitive row58');present=flag(v[2]);sid=meta(v[3]);count=meta(v[6],7)
    need(len(candidates)==count,'all primitive candidate prefix retained')
    geometry=None
    if present:
        geometry={'surfaceId':sid,'survivingFeatures':meta(v[4],127),'relation':meta(v[5],3)}
        for offset,key in zip(range(16,52,6),['barycentric','closestLocal','closest','delta','normal','spherePoint']):geometry[key]=b3(v[offset:offset+6])
        for offset,key in [(52,'squaredDistance'),(54,'distance'),(56,'gap')]:geometry[key]=v[offset:offset+2]
    else:pad(v[4:6]);pad(v[16:])
    cs=[]
    for c in candidates:
        need(len(c)==13,'candidate13');cs.append({'feature':meta(c[0],6),'disposition':meta(c[1],2),'kktCount':meta(c[2],2),'barycentric':b3(c[3:9]),'kkt':[c[9:11],c[11:13]]})
    return {'status':meta(v[0],7),'reason':meta(v[1],32),'geometry':geometry,
            'squaredCross':opt(v,10,2),'sineSquared':opt(v,13,2),'candidates':cs,
            'candidatesExamined':meta(v[7],7),'sqrtRefinements':meta(v[8],1024),'sqrtRefinementLimited':flag(v[9])}

def mesh_decode(row,sources,triangles):
    m=row['lastMeshSummary']
    if m is None:
        need(row['lastMeshSummaryBits'] is None and not row['lastMeshRows'],'no invented last mesh');return None
    need(len(m)==24,'last mesh summary24');pad(m[21:]);has=flag(m[2]);need(meta(m[3],64)==len(sources),'mesh source count')
    present=[i for i,s in enumerate(sources) if flag(s[11])]
    need(len(present)==meta(m[4],64)==len(row['lastMeshRows']),'all existing mesh rows retained')
    rows=[]
    for i,raw in zip(present,row['lastMeshRows']):
        fields(raw,{'rowOrdinal','packet','bits','candidates','candidateBits'},'last mesh row')
        need(type(raw['rowOrdinal'])is int and raw['rowOrdinal']==i,'source ordinal ownership')
        if flag(sources[i][12]):
            need(raw['packet'] is not None,'actual row query retained');q=primitive_decode(raw['packet'],raw['candidates'])
        else:
            need(raw['packet'] is None and raw['bits'] is None and not raw['candidates'] and not raw['candidateBits'],'null query has no fake geometry');q=None
        rows.append({'triangle':copy.deepcopy(triangles[i]),'query':q})
    nearest=None
    if has:
        identifiers=sorted(triangles[i]['id'] for i,s in enumerate(sources) if flag(s[13]))
        need(len(identifiers)==meta(m[14],64),'possible winner IDs from full source flags')
        nearest={'possibleSurfaceIds':identifiers,'squaredDistance':m[15:17],'distance':m[17:19],'gap':m[19:21]}
    else:pad(m[14:21]);need(not any(flag(s[13]) for s in sources),'no possible IDs without nearest')
    failed=opt(m,5,1);first=opt(m,7,1)
    return {'status':meta(m[0],5),'reason':meta(m[1],11),'failedIndex':None if failed is None else meta(failed[0],63),
            'firstFailedRow':None if first is None else meta(first[0],63),'rows':rows,'nearest':nearest,
            **{key:meta(m[i],32768) for i,key in enumerate(['queries','candidatesExamined','sqrtRefinements','sqrtLimitedRows','failedRows'],9)}}

def held_decode(p,row,triangles,sources):
    h=p.get(3);pad(h[39:]);need(meta(h[2],64)==len(triangles) and not flag(h[6]),'raw held WorldBody absent and source count owned')
    failed=opt(h,4,1);link=opt(h,24,1);prefix=opt(h,16,2)
    result={'status':choose(h[0],HS),'reason':choose(h[1],HR),'failedIndex':None if failed is None else meta(failed[0],63),
            'snapshot':None,'worldBody':None,'acceleration':None,'wholePathBounds':None,'wholeVelocityBounds':None,
            'initial':None,'initialSeparationProven':flag(h[11]),'certifiedLeaves':[],'safePrefix':prefix,'bestWitness':None,'window':None,
            'candidateSurfaceIds':[],'partition':[],'frontier':[],'current':None,'audits':[],
            'lastMesh':None,'lastMeshAuditIndex':None if link is None else meta(link[0],255),
            'work':work_decode(h[28:39]),'partitionLeaves':meta(h[26],128),'maximumDepth':meta(h[27],32)}
    if flag(h[3]):
        snap=input_decode(p.get(4),0,triangles);result['snapshot']={'input':snap['sphere'],'horizon':snap['horizon'],'triangles':snap['triangles'],'settings':snap['settings']}
    else:p.get(4,present=False)
    for kind,key,offset in [(9,'acceleration',7),(10,'wholePathBounds',8),(11,'wholeVelocityBounds',9)]:
        v=p.get(kind,present=flag(h[offset]))
        if v is not None:need(meta(v[0],0)==0,'bounds ordinal0');pad(v[7:]);result[key]=b3(v[1:7])
    for i in range(meta(h[15],256)):
        a=p.get(12,i);need(meta(a[0],255)==i,'audit ordinal');pad(a[62:])
        audit={'kind':choose(a[1],AK),'cell':time_cell(a[2:5]),'time':a[5],'outcome':choose(a[6],AO),
               'pathBounds':None,'pointBounds':None,'anchor':opt(a,21,3),'meshQueried':flag(a[25]),
               'meshStatus':None,'meshReason':None,'work':work_decode(a[51:62])}
        for key,o in [('pathBounds',7),('pointBounds',14)]:
            value=opt(a,o,6);audit[key]=None if value is None else b3(value)
        for key,o,maximum in [('meshStatus',26,5),('meshReason',28,11)]:
            value=opt(a,o,1);audit[key]=None if value is None else meta(value[0],maximum)
        for key,o in zip(INTERVALS,[30,33,36,39,42,45,48]):audit[key]=opt(a,o,2)
        result['audits'].append(audit)
    for i in range(meta(h[12],128)):
        v=p.get(13,i);result['certifiedLeaves'].append({'cell':time_cell(v[:3]),'lowerGapCertificate':v[3:5],'auditIndex':meta(v[5],255)})
    for i in range(meta(h[13],128)):
        v=p.get(14,i);need(meta(v[0],127)==i,'partition ordinal');owner=opt(v,5,1)
        result['partition'].append({'cell':time_cell(v[1:4]),'state':choose(v[4],LS),'auditIndex':None if owner is None else meta(owner[0],255),'blockedReason':choose(v[7],HR)})
    for i in range(meta(h[14],128)):
        v=p.get(15,i);need(meta(v[0],127)==i,'frontier ordinal');result['frontier'].append(time_cell(v[1:]))
    v=p.get(16,present=flag(h[22]))
    if v is not None:need(meta(v[0],0)==0,'current ordinal0');result['current']=time_cell(v[1:])
    v=p.get(17,present=flag(h[10]))
    if v is not None:need(meta(v[0],0)==0,'initial ordinal0');result['initial']={'lowerGapCertificate':v[1:3],'upperGapCertificate':v[3:5],'auditIndex':meta(v[5],255)}
    v=p.get(18,present=flag(h[19]))
    if v is not None:
        need(meta(v[0],0)==0,'witness ordinal0');result['bestWitness']={'cell':time_cell(v[1:4]),'time':v[4],'exactPathBounds':b3(v[5:11]),'anchor':v[11:14],'errorUpper':v[14],'upperGapCertificate':v[15:17],'auditIndex':meta(v[17],255)}
    v=p.get(19,present=flag(h[20]))
    if v is not None:
        need(meta(v[0],0)==0,'window ordinal0');result['window']={'timeBounds':v[1:3],'timeWidth':v[3:5],'pathBounds':b3(v[5:11]),'l1DiameterBound':v[11:13],'witnessAuditIndex':meta(v[13],255)}
    for i in range(meta(h[21],64)):
        v=p.get(20,i);need(meta(v[0],63)==i,'conservative ID ordinal');result['candidateSurfaceIds'].append(meta(v[1]))
    if flag(h[23]):result['lastMesh']=mesh_decode(row,sources,triangles)
    else:need(row['lastMeshSummary'] is None and not row['lastMeshRows'],'no borrowed last mesh')
    return result

def decode(row):
    mode=meta(row['mode'],1);s=row['summary'];need(len(s)==24 and meta(s[0],1)==mode,'family summary24/mode');pad(s[16:])
    p=Packets(row);original=p.get(0);sources=[];triangles=[]
    for i in range(meta(s[3],64)):
        v=p.get(1,i);need(meta(v[0],63)==i,'source ordinal');sources.append(v)
        triangles.append({'id':meta(v[1]),'vertices':[v[2:5],v[5:8],v[8:11]]})
    source=input_decode(original,mode,triangles,raw=True);failed=opt(s,5,1)
    if mode==0:
        need(flag(s[15]) and not any(flag(s[i]) for i in [7,8,9,11,12,13,14]),'held-only family flags');pad(s[10:11])
        result=held_decode(p,row,triangles,sources)
        if flag(s[4]):
            snap=input_decode(p.get(2),0,triangles)
            held.source_equal({'input':snap['sphere'],'horizon':snap['horizon'],'triangles':snap['triangles'],'settings':snap['settings']},result['snapshot'])
        else:p.get(2,present=False)
        need(choose(s[1],HS)==result['status'] and choose(s[2],HR)==result['reason']
             and flag(s[4])==(result['snapshot'] is not None)
             and (None if failed is None else meta(failed[0],63))==result['failedIndex'],
             'mode0 family and held header describe the SAME result')
    else:
        result={'status':choose(s[1],GS),'reason':choose(s[2],GR),'failedIndex':None if failed is None else meta(failed[0],63),
                'worldBody':None,'snapshot':None,'tube':None,'flightFailure':None,'candidateEvaluated':flag(s[11]),'endpoint':None,'inflated':None,'candidate':None}
        snap=p.get(2,present=flag(s[4]))
        if snap is not None:result['snapshot']=input_decode(snap,1,triangles)
        world=p.get(5,present=flag(s[7]))
        if world is not None:pad(world[31:]);result['worldBody']={'body':body_decode(world[:28]),'gravity':world[28:31]}
        tube=p.get(6,present=flag(s[8]))
        if tube is not None:pad(tube[18:]);result['tube']={'nominalAcceleration':tube[:3],'exactAcceleration':b3(tube[3:9]),'accelerationDifference':b3(tube[9:15]),'positionError':tube[15],'roundoff':tube[16],'guardRadius':tube[17]}
        ff=opt(s,9,1);result['flightFailure']=None if ff is None else meta(ff[0],12)
        end=p.get(7,present=flag(s[12]))
        if end is not None:
            pad(end[35:]);result['endpoint']={key:b3(end[i:i+6]) for key,i in zip(['nominalPosition','nominalAllowed','exactPosition','exactAllowed','exactDifference'],range(0,30,6))}
            result['endpoint'].update(l1ErrorBound=end[30:32],**{key:flag(end[i]) for key,i in zip(['nominalContained','exactContained','l1WithinTube'],range(32,35))})
        candidate=p.get(8,present=flag(s[14]))
        if candidate is not None:pad(candidate[28:]);result['candidate']=body_decode(candidate[:28])
        need(flag(s[13])==flag(s[15]),'nested held presence flags agree')
        if flag(s[15]):result['inflated']=held_decode(p,row,triangles,sources)
        else:p.get(3,present=False);need(row['lastMeshSummary'] is None and not row['lastMeshRows'],'unqueried guard has no borrowed last mesh')
    p.finish();return source,result

def corpus_fingerprint(corpus):
    rows=[cohort+':'+str(mode)+':'+guard.input_fingerprint([{'input':fixture['input']}]) for cohort,fixture,mode in corpus]
    return hashlib.sha256('\n'.join(sorted(rows)).encode()).hexdigest()

def verify_packets(corpus,packets):
    fields(packets,{'schema','kind','fixtureCount','accepted','hostRejected','fixtures'},'flight raw envelope')
    need(type(packets['schema'])is int and packets['schema']==1 and packets['kind']=='sphere-triangle-mesh-flight-sdk-packets','flight packet schema')
    need(type(packets['fixtures'])is list and len(packets['fixtures'])==len(corpus)==packets['fixtureCount'],'complete frozen source cohort')
    comparison=Compare();models=Compare();prior=[];decoded=[];actual_accepted=[];expected_accepted=[]
    cohorts={key:{'models':0,'hostRejected':0,'mathematics':guard.held_stats() if key=='held' else guard.new_stats(0)} for key in ['held','guard','supplemental']}
    record_count=0;maximums={key:0 for key in ['sources','audits','leaves','partition','frontier','candidateIds','lastMeshRows','lastMeshCandidates']}
    for (cohort,fixture,mode),raw in zip(corpus,packets['fixtures']):
        fields(raw,ROW_KEYS,'raw fixture')
        need(raw['cohort']==cohort and raw['name']==fixture['name'] and type(raw['mode'])is int and raw['mode']==mode,'input identity/mode')
        source=fixture['input'];label=cohort+'/'+fixture['name'];q=query_values(source,mode);triangles=source_values(source)
        comparison.packet(raw['input'],raw['inputBits'],q,label+' input')
        comparison.equal(raw['triangles'],triangles,label+' source values')
        comparison.equal(raw['triangleBits'],[[bits(x) for x in t] for t in triangles],label+' source bit integrity')
        comparison.packet(raw['outputBefore'],raw['outputBeforeBits'],prior,label+' before chain')
        begin,appends,status,phase=host_path(source,mode)
        for key,value in [('beginStatus',begin),('appendStatuses',appends),('exchangeStatus',status),('failedPhase',phase)]:comparison.equal(raw[key],value,label+' '+key)
        if phase is not None:
            cohorts[cohort]['hostRejected']+=1
            need(raw['hostFailurePreserved'] is True,'host failure keeps previous output/count')
            need(raw['summary'] is raw['summaryBits'] is raw['lastMeshSummary'] is raw['lastMeshSummaryBits'] is None
                 and not raw['packets'] and not raw['lastMeshRows'],'host rejects are NOT model results')
            comparison.packet(raw['outputAfter'],raw['outputAfterBits'],prior,label+' rejected output')
            continue
        expected_accepted.append((cohort,fixture,mode));cohorts[cohort]['models']+=1
        need(raw['hostFailurePreserved'] is None,'accepted model is not labelled host preservation')
        summary,entries,mesh_summary,rows=expected_wire(source,mode,fixture['result'])
        comparison.packet(raw['summary'],raw['summaryBits'],summary,label+' summary')
        comparison.equal(raw['packets'],entries,label+' all records')
        comparison.packet(raw['lastMeshSummary'],raw['lastMeshSummaryBits'],mesh_summary,label+' last mesh')
        comparison.equal(raw['lastMeshRows'],rows,label+' full mesh rows/candidates')
        # The decoded model is constructed ONLY from actual input/source/getters.
        # Pure result values are compared after decode, never used as substitutes.
        actual_source,result=decode(raw)
        models.equal(actual_source,source,label+' decoded complete source')
        models.equal(result,fixture['result'],label+' decoded complete Native observables')
        if mode==0:held.verify_fixture(actual_source,result,cohorts[cohort]['mathematics'])
        else:guard.verify_fixture(actual_source,result,cohorts[cohort]['mathematics'])
        decoded.append({'cohort':cohort,'name':fixture['name'],'mode':mode,'input':actual_source,'result':result})
        actual_accepted.append((cohort,{'input':actual_source},mode))
        record_count+=len(entries)
        for kind,key in [(1,'sources'),(12,'audits'),(13,'leaves'),(14,'partition'),(15,'frontier'),(20,'candidateIds')]:maximums[key]=max(maximums[key],sum(p['kind']==kind for p in entries))
        maximums['lastMeshRows']=max(maximums['lastMeshRows'],len(rows));maximums['lastMeshCandidates']=max(maximums['lastMeshCandidates'],sum(len(r['candidates']) for r in rows))
        last=summary
        if entries:last=entries[-1]['values']
        if mesh_summary is not None:last=mesh_summary
        for row in rows:
            if row['packet'] is not None:last=row['packet']
            if row['candidates']:last=row['candidates'][-1]
        comparison.packet(raw['outputAfter'],raw['outputAfterBits'],last,label+' final getter output')
        prior=last
    accepted=sum(c['models'] for c in cohorts.values());rejected=len(corpus)-accepted
    need(type(packets['accepted'])is int and type(packets['hostRejected'])is int
         and packets['accepted']==accepted and packets['hostRejected']==rejected,'measured accepted/host counts')
    expected_fp=corpus_fingerprint(expected_accepted);actual_fp=corpus_fingerprint(actual_accepted)
    need(expected_fp==actual_fp,'all accepted decoded inputs match fixed classified full-input cohort')
    return {'status':'PASS','fixtureCount':len(corpus),'accepted':accepted,'hostRejected':rejected,
            'numericBits':comparison.numeric_count,'negativeZeroBits':comparison.negative_zeros,
            'decodedNumericBits':models.numeric_count,'decodedNegativeZeroBits':models.negative_zeros,
            'acceptedInputFingerprint':actual_fp,'records':record_count,'maximums':maximums,'cohorts':cohorts},decoded

def negative_controls(corpus,packets):
    results=[]
    accepted=next(i for i,r in enumerate(packets['fixtures']) if r['summary'] is not None)
    guard_row=next(i for i,r in enumerate(packets['fixtures']) if r['mode']==1 and r['summary'] is not None and r['summary'][14]==1)
    capacity=next(i for i,r in enumerate(packets['fixtures']) if sum(p['kind']==12 for p in r['packets'])==256)
    full_ids=next(i for i,r in enumerate(packets['fixtures']) if sum(p['kind']==20 for p in r['packets'])==64)
    host=next(i for i,r in enumerate(packets['fixtures']) if r['failedPhase'] is not None)
    def add(name,index,mutate):
        copied=copy.deepcopy(packets);mutate(copied['fixtures'][index])
        try:verify_packets(corpus,copied)
        except (AssertionError,ValueError,KeyError,TypeError,OverflowError) as error:results.append({'name':name,'rejected':True,'diagnostic':str(error)})
        else:raise AssertionError('wire mutation accepted: '+name)
    def change(r,kind,offset,value):
        p=next(p for p in r['packets'] if p['kind']==kind);p['values'][offset]=value;p['bits'][offset]=bits(value)
    add('mode changed',accepted,lambda r:r.update(mode=1-r['mode']))
    add('summary padding negative zero',accepted,lambda r:(r['summary'].__setitem__(23,-0.0),r['summaryBits'].__setitem__(23,bits(-0.0))))
    add('raw bits mismatch',accepted,lambda r:r['summaryBits'].__setitem__(0,'ffffffffffffffff'))
    add('boolean F64 alias',accepted,lambda r:r['summary'].__setitem__(0,False))
    add('getter tail omitted',accepted,lambda r:r['packets'].pop())
    add('getter duplicated',accepted,lambda r:r['packets'].append(copy.deepcopy(r['packets'][-1])))
    add('source geometry corruption',accepted,lambda r:change(r,1,2,999.))
    add('audit256 last omitted',capacity,lambda r:r['packets'].remove([p for p in r['packets'] if p['kind']==12][-1]))
    add('audit +0 padding negative',capacity,lambda r:change(r,12,63,-0.0))
    add('candidate64 ID tail omitted',full_ids,lambda r:r['packets'].remove([p for p in r['packets'] if p['kind']==20][-1]))
    add('guard B erased',guard_row,lambda r:change(r,6,15,0.))
    add('guard radius source mixed',guard_row,lambda r:change(r,6,17,r['input'][3]))
    add('candidate position corrupted',guard_row,lambda r:change(r,8,7,999.))
    add('endpoint error erased',guard_row,lambda r:change(r,7,30,999.))
    add('host rejected source turned into model',host,lambda r:r.update(summary=copy.deepcopy(packets['fixtures'][accepted]['summary']),summaryBits=copy.deepcopy(packets['fixtures'][accepted]['summaryBits'])))
    add('host output retention false',host,lambda r:r.update(hostFailurePreserved=False))
    return {'status':'PASS','count':len(results),'rejectedControls':results,'scope':'Copied raw packets with consistent bit updates where relevant; no Native allocator/environment fault injection.'}

def main():
    need(__debug__,'run flight wire reference without Python -O')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('held');parser.add_argument('guard');parser.add_argument('supplemental');parser.add_argument('probe');parser.add_argument('output')
    parser.add_argument('--packets');parser.add_argument('--scope',choices=['native','wasm-wire'],default='native')
    args=parser.parse_args();out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=False)
    h,g,s=map(held.load,[args.held,args.guard,args.supplemental])
    pure={'held':held.verify(h),'guard':guard.verify(g),'supplemental':guard.verify_supplemental(s)}
    corpus=[('held',f,0) for f in h['fixtures']]+[('guard',f,1) for f in g['fixtures']]+[('supplemental',f,1) for f in s['fixtures']]
    write_new(out/'inputs.rows',rows_text(corpus))
    if args.packets:
        raw=Path(args.packets).read_bytes();invocation={'mode':'captured-packets','path':str(Path(args.packets).resolve())}
    else:
        need(args.scope=='native','WASM scope must provide captured packets')
        command=[str(Path(args.probe).resolve())]
        with (out/'inputs.rows').open('rb') as stdin,(out/'probe.stdout.json').open('xb') as stdout,(out/'probe.stderr.txt').open('xb') as stderr:
            process=subprocess.run(command,stdin=stdin,stdout=stdout,stderr=stderr,timeout=240)
        write_new(out/'probe-command.json',json.dumps({'command':command,'exitCode':process.returncode},indent=2)+'\n')
        need(process.returncode==0,'Native flight probe failed; raw output retained');raw=(out/'probe.stdout.json').read_bytes()
        invocation={'mode':'native-probe','command':command,'exitCode':process.returncode}
    need(len(raw)<=64*1024*1024,'bounded raw packets');write_new(out/'packets.json',raw)
    packets=held.loads(raw);report,decoded=verify_packets(corpus,packets);controls=negative_controls(corpus,packets)
    optimized_command=[sys.executable,'-O',str(Path(__file__).resolve()),args.held,args.guard,args.supplemental,'-',str(out/'optimized-must-not-run'),'--packets',str(out/'packets.json'),'--scope',args.scope]
    optimized=subprocess.run(optimized_command,capture_output=True,timeout=30)
    write_new(out/'optimized.stdout.txt',optimized.stdout);write_new(out/'optimized.stderr.txt',optimized.stderr)
    write_new(out/'optimized-command.json',json.dumps({'command':optimized_command,'exitCode':optimized.returncode},indent=2)+'\n')
    need(optimized.returncode!=0 and b'without Python -O' in optimized.stderr,'optimized independent wire checker fails closed')
    write_new(out/'decoded-models.json',signed_json({'schema':1,'kind':'actual-flight-models','fixtures':decoded})+'\n')
    write_new(out/'packet-negative-controls.json',json.dumps(controls,indent=2)+'\n')
    report.update(scope=args.scope,pureNativeReference=pure,packetNegativeControls=controls,invocation=invocation,
                  optimizedPythonRejected={'status':'PASS','exitCode':optimized.returncode},
                  fullInputFingerprint=corpus_fingerprint(corpus),
                  limitations='Message strings are explicitly excluded by the Native fixture contract. Every other accepted result field is decoded from actual packets and bit-compared; only actual models enter Fraction verification. Host rejected models are never filled from Native. No public JS wrapper, UI, World response or actual allocation-fault injection.',
                  sources={str(p):file_info(p) for p in [Path(args.held),Path(args.guard),Path(args.supplemental),Path(__file__),HERE/'check-sphere-triangle-mesh-held-load.py',HERE/'check-sphere-triangle-mesh-free-flight-guard.py']})
    report['files']={name:file_info(out/name) for name in ['inputs.rows','packets.json','decoded-models.json','packet-negative-controls.json']}
    write_new(out/'report.json',json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
