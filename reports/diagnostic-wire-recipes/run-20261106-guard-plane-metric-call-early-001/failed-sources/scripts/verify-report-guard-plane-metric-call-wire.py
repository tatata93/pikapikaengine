"""Independent complete artificial PlaneMetricCall oracle using fixed pair coverage and ledger specifications."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
pair=module('plane_metric_pair','scripts/verify-report-coverage-pair-result-wire.py')
ledger=module('plane_metric_ledger','scripts/verify-report-ledgers-wire.py');wire=pair.wire
def need(v,m):
 if not v:raise ValueError(m)
def fields(v):return dict(v[1])
def expected():
 def obj(**v):return ('object',[(k.encode(),x) for k,x in v.items()])
 def opt(yes,v):return ('present',v) if yes else ('absent',None)
 snapshots=pair.snapshot_ref.expected()[1][1];results=pair.expected()[1][1];grant=ledger.expected()[1][1][5]
 counts=[0,2**64-1,9007199254740993,2**63];kinds=[0,1,2,3,2**31,2**32-1];rows=[]
 for i in range(16):
  which=16 if i==15 else 1 if i%4==3 else 3 if i%8==6 else 0
  rows.append(obj(state=('enum',kinds[i%6]),attempt_ordinal=opt(i&1,('u64',counts[(i//2)%4])),requested_settings=fields(snapshots[i%16])[b'settings'],used_settings=fields(snapshots[(i+1)%16])[b'settings'],granted=('bool',bool(i&4)),grant=grant,result=opt(i&2,results[which]),messages=obj(fields=('u64',counts[i%4]),nonempty_fields=('u64',counts[(i+1)%4]),bytes=('u64',counts[(i+2)%4]),omitted=('bool',bool(i&8)))))
 return 0x5247504d,('array',rows)
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every original PlaneMetricCall field and complete nested child exact')
 rows=[fields(v) for v in actual[1][1]];need(len(rows)==16,'All16 artificial calls')
 masks={(r[b'attempt_ordinal'][0]=='present',r[b'result'][0]=='present',r[b'granted'][1],fields(r[b'messages'])[b'omitted'][1]) for r in rows};need(len(masks)==16,'All16 independent optional and boolean combinations')
 need({r[b'state'][1] for r in rows}=={0,1,2,3,2**31,2**32-1},'All3 documented states and3 unknown ordinals')
 need({r[b'attempt_ordinal'][1][1] for r in rows if r[b'attempt_ordinal'][0]=='present'}=={0,2**64-1,9007199254740993,2**63},'All4 original attempt boundaries')
 nested=[fields(r[b'result'][1]) for r in rows if r[b'result'][0]=='present'];inputs=[fields(v[b'snapshot'][1])[b'input'] for v in nested if v[b'snapshot'][0]=='present']
 need({v[1][0] for v in inputs}=={0,1},'Both nested original Input alternatives')
 need(len(nested[-1][b'audits'][1])==20 and len(nested[-1][b'partition'][1])==12,'All final child audits and partition tail')
 need(all(not wire.typed_equal(r[b'requested_settings'],r[b'used_settings']) for r in rows),'Original requested and used settings differ in every source')
 leaves=[];present=absent=variants=0
 def walk(v):
  nonlocal present,absent,variants
  kind,value=v
  if kind=='object':
   for _,x in value:walk(x)
  elif kind=='array':
   for x in value:walk(x)
  elif kind=='present':present+=1;walk(value)
  elif kind=='absent':absent+=1
  elif kind=='variant':variants+=1;walk(value[1])
  else:leaves.append(v)
 walk(actual[1]);floats=[v for k,v in leaves if k=='f64bits']
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=1,mappedFields=8,fixtureRecords=16,allTypedLeaves=len(leaves),mappedFloatBitValues=len(floats),negativeZeroOccurrences=floats.count(2**63),present=present,absent=absent,nestedVariants=variants,leafKinds={k:sum(t==k for t,_ in leaves) for k in ['f64bits','u64','u32','bool','enum','bytes']},outerBooleanPresenceMasks=16,presentAttemptBoundaryValues=4,scope='Artificial16 PlaneMetricCall values, differing requested/used settings, original grant even when refused, complete returned child or absence and original omission counts. No model query, Child variant/Pair/GuardResult/World Report/pump/game connection acceptance.')
def main():
 need(__debug__,'Optimized Python is refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
