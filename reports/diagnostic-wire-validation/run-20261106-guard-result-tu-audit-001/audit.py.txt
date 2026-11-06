"""Audit each actual CL command independently: two data TUs, harness and test-only Interval."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
def need(v,m):
 if not v:raise ValueError(m)
def inspect(text,expected,cfg):
 lines=[line.strip() for line in text.splitlines() if line.strip()];need(len(lines)==2*len(expected),'Exact source/command pair count');rows=[]
 for i in range(0,len(lines),2):
  source,command=lines[i:i+2];need(source.startswith('^') and not command.startswith('^'),'Actual CL source and command');source=source[1:].replace('\\','/').upper();upper=command.replace('\\','/').upper()
  need(source in expected and upper.endswith(source),'Exact expected source in actual compiler command')
  for flag in ['/W4','/WX','/FP:STRICT','/GL-',('/MDD' if cfg=='Debug' else '/MD')]:need(len(re.findall(r'(?:^|\s)'+re.escape(flag)+r'(?=\s|$)',upper))==1,'Actual strict per-TU flag '+flag)
  need(not re.search(r'(?:^|\s)(?:/FP:FAST|/FP:PRECISE|/GL)(?=\s|$)',upper),'No contradictory fast/LTO flags')
  need(bool(re.search(r'/D\s*(?:"NDEBUG"|NDEBUG)(?=\s|$)',upper))==(cfg=='Release'),'True Debug for each source')
  rows.append(dict(source=source,command=command))
 need({r['source'] for r in rows}==set(expected),'Every expected source exactly once');return rows
def audit(build,cfg):
 targets={'pikapika_diagnostic_wire':['core/src/diagnostic_wire.cpp'],'pikapika_report_values_wire':['core/src/report_values_wire.cpp'],'pikapika_report_guard_result_wire_tests':['tests/report_guard_result_wire_tests.cpp','core/src/interval.cpp']};rows=[]
 for target,sources in targets.items():
  log=next((build/(target+'.dir')/cfg).rglob('CL.command.1.tlog'));expected={(ROOT/p).as_posix().upper() for p in sources};actual=inspect(log.read_bytes().decode('utf16'),expected,cfg);rows+=actual
 need(len(rows)==4,'Exactly four real compiled source TUs');return rows
