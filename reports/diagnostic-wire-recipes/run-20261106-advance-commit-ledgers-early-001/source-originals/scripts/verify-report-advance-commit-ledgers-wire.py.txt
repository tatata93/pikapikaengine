"""Independent stored advance work/storage counts; no model or memory query."""
from pathlib import Path
import argparse,hashlib,importlib.util,json
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wire_reference',ROOT/'scripts/verify-diagnostic-wire.py');wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
def need(v,m):
 if not v:raise ValueError(m)
def expected():
 work=['guard_queries_attempted', 'guard_queries_returned', 'pair_records_checked', 'call_records_checked', 'origin_bodies_checked', 'origin_planes_checked', 'origin_meshes_checked', 'origin_faces_checked', 'candidates_copied', 'candidate_validations_attempted', 'candidates_validated', 'destination_lookups', 'destinations_resolved', 'body_assignments', 'progress_assignments']
 storage=['body_buffer_slots', 'destination_slots', 'body_buffer_sizeof_bytes', 'destination_buffer_sizeof_bytes']
 values=[0,1,2**53+1,2**64-1,2**63,2**64-2,42,2**32-1]
 records=[]
 for fields,offset in [(work,0),(storage,3)]:
  for i in range(16):records.append(('object',[(key.encode(),('u64',values[(i+j+offset)%8])) for j,key in enumerate(fields)]))
 return 0x52415753,('array',records)
def verify(data):
 actual=wire.decode(data);need(wire.typed_equal(actual,expected()),'Every stored count, field order and full64 value exact')
 return dict(status='PASS',bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),mappedRecordTypes=2,mappedFields=19,mappedVariants=0,fixtureRecords=32,allTypedLeaves=304,mappedFloatBitValues=0,negativeZeroOccurrences=0,present=0,absent=0,totalVariantOccurrences=0,leafKinds={'f64bits':0,'u64':304,'u32':0,'bool':0,'enum':0,'bytes':0},scope='Artificial16 CommitWork and16 CommitStorage records. Count preservation only; no advance execution, physical work/memory measurement or World Report/pump/game acceptance.')
def main():
 need(__debug__,'Optimized Python refused');p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--hex',action='store_true');a=p.parse_args();need(a.capture.stat().st_size<=2097154,'Bounded file');data=a.capture.read_bytes()
 if a.hex:data=bytes.fromhex(data.decode('ascii'))
 print(json.dumps(verify(data)))
if __name__=='__main__':main()
