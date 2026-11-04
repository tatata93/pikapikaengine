"""Record narrow observed anchors from preserved dumps; not a CFG verifier."""
from pathlib import Path
import json
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
correlation = json.loads((OUT / 'byte-map-correlation.json').read_text(encoding='utf-8'))
functions = {f['name']: f for f in correlation['functions']}
map_path = ROOT / 'build/wfa2/Release/world-flight-advance.map'
map_addresses = {}
for ordinal, line in enumerate(map_path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
    m = re.match(r'^\s*[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}\s+(\S+)\s+([0-9A-Fa-f]{16})(?:\s|$)', line)
    if m:
        map_addresses.setdefault(int(m.group(2), 16), []).append({'line': ordinal, 'symbol': m.group(1), 'text': line})


def instructions(name):
    f = functions[name]
    if not f['mapAndByteCorrespondence']:
        raise ValueError('No unique byte/map correspondence: '+name)
    base = int(f['executableMatches'][0]['virtualAddress'], 16)
    lines = (OUT / (name+'-executable-'+hex(base)+'.txt')).read_text(encoding='utf-8').splitlines()
    result = []
    for line in lines:
        m = re.match(r'^(\d+):\s*([0-9A-F]{16}):\s+((?:[0-9A-F]{2} )+)\s*(\S+)\s*(.*)$', line)
        if m:
            row = {'dumpLine': int(m.group(1)), 'address': hex(int(m.group(2), 16)),
                   'offset': int(m.group(2), 16)-base, 'bytes': m.group(3).strip(),
                   'mnemonic': m.group(4), 'operands': m.group(5), 'raw': line}
            if row['mnemonic'] == 'call' and re.fullmatch(r'[0-9A-F]{16}', row['operands']):
                row['targetMapRecords'] = map_addresses.get(int(row['operands'], 16), [])
            result.append(row)
    return result


advance, clock = instructions('advance'), instructions('clock_preflight')
standalone = instructions('commit')
by_offset = lambda rows, offset: next(r for r in rows if r['offset'] == offset)
addition, difference = by_offset(clock, 0xc3), by_offset(clock, 0x10d)
if addition['mnemonic'] != 'addsd' or difference['mnemonic'] != 'subsd':
    raise ValueError('Actual observed clock anchor changed')
body_start, progress = by_offset(advance, 0xaa5), by_offset(advance, 0xb04)
if body_start['mnemonic'] != 'movups' or progress['mnemonic'] != 'movups':
    raise ValueError('Actual observed copy anchor changed')
calls = [r for r in advance if r['mnemonic'] == 'call']
commit_va = int(functions['commit']['executableMatches'][0]['virtualAddress'], 16)
record = {'schema': 1, 'status': 'EXPLORED',
          'scope': 'Instruction/map observations only; not source-field/alias, branch/EH dominance, dependency closure or compiler attestation.',
          'allSixFunctionMapAndByteCorrespondences': all(f['mapAndByteCorrespondence'] for f in functions.values()),
          'clock': {'addition': addition, 'representedDifference': difference,
                    'proposalTimeStore': by_offset(clock, 0xee),
                    'proposalTicksStore': by_offset(clock, 0xf7),
                    'intervalAndOtherCallSites': [r for r in clock if r['mnemonic'] == 'call']},
          'commit': {'standaloneSymbolRetained': True,
                     'directCallsToStandaloneFromAdvance': [r for r in calls if int(r['operands'], 16) == commit_va],
                     'inlinedFirstBodyStore': body_start,
                     'inlinedBodyStoreInstructions': [r for r in advance if 0xaa5 <= r['offset'] <= 0xaf2 and r['mnemonic'] == 'movups'],
                     'inlinedProgressStore': progress,
                     'callsBetweenFirstBodyAndProgressStore': [r for r in calls if 0xaa5 <= r['offset'] <= 0xb04],
                     'normalEpilogueCallsAfterProgressBeforeRet': [r for r in calls if 0xb04 < r['offset'] < 0xb61],
                     'standaloneCommitCallInstructions': [r for r in standalone if r['mnemonic'] == 'call']},
          'advanceCallSites': calls,
          'formalClockGraphProof': False, 'formalCommitCompilerAttestation': False,
          'notProved': correlation['notProved']}
with (OUT / 'observations.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': 'EXPLORED', 'functionsWithUniqueMapAndByteMatch': 6,
                  'inlinedBodyStores': len(record['commit']['inlinedBodyStoreInstructions']),
                  'callsBetweenBodyAndProgressStore': len(record['commit']['callsBetweenFirstBodyAndProgressStore'])}))
