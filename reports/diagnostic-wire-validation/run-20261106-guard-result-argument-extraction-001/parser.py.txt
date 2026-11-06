"""Strict captured CTest parser with explicit allowlisted --run/stop arguments.

Original45-test extractor and proof stay unchanged. This extension must pass an
actual captured-log experiment before Native continuation uses it.
"""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]
def stamp(p):
 b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def parse(raw,expected):
 text=raw.decode('utf8');starts=re.findall(r'^\s*Start\s+(\d+):\s+(\S+)\s*$',text,re.M)
 passed=re.findall(r'^\s*\d+/\d+\s+Test\s+#(\d+):\s+(\S+)\s+\.+\s+Passed\s+',text,re.M)
 assert starts==passed and len(starts)==len(expected) and len({i for i,_ in starts})==len(starts) and {n for _,n in starts}==set(expected)
 assert re.findall(r'(\d+)% tests passed, (\d+) tests failed out of (\d+)',text)==[('100','0',str(len(expected)))]
 payloads=re.findall(rb'^\s*(\d+): (\{[^\r\n]*\})\r?$',raw,re.M)
 assert len(payloads)==len(starts) and {i.decode() for i,_ in payloads}=={i for i,_ in starts}
 records=[]
 for number,name in starts:
  payload=next(value for i,value in payloads if i.decode()==number);row=expected[name];prior=(ROOT/row['stdout']).read_bytes()
  assert payload==prior.rstrip(b'\r\n') and json.loads(payload)==json.loads(prior)
  argument=row.get('argument','--run');assert argument in {'--run',*('--stop-shard-'+str(i) for i in range(16))}
  if argument!='--run':assert re.fullmatch(r'report_guard_result_wire_stop_(\d+)',name) and name.rsplit('_',1)[1]==argument.rsplit('-',1)[1]
  commands=[line for line in text.splitlines() if line.startswith(number+': Test command: ')]
  assert commands==[number+': Test command: '+row['binary']+' "'+argument+'"']
  records.append(dict(name=name,ctestNumber=int(number),originalStdout=stamp(ROOT/row['stdout']),actualArgument=argument,allJSONTextExceptLineTerminatorsExact=True))
 return records
