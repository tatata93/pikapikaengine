#!/usr/bin/env python3
"""Independent exact-rational reference for the finite skinning point corpus.

Column-major binary64 inputs are interpreted as exact real rationals. Inverses
use an original 4x4 rational Gauss-Jordan elimination, not the kernel's scaled
3x3 implementation. Deformation uses the supplied inverse-bind numbers and the
exact ratio of authored weights; it does not replace imported binds by ideal
inverses. Acceptance is a point-error test, NOT an interval/error guarantee for
arbitrary skinning inputs, normals, triangles, volume or a continuous surface.

Usage: python scripts/verify-skinning.py native.json [wasm.json]
       --oracle native-oracle.csv [--wasm-oracle wasm-oracle.csv]
The fixed input fingerprints include signed zero. Python -O is rejected.
"""
import argparse
import csv
from fractions import Fraction as F
import hashlib
import io
import json
import math
from pathlib import Path
import re
import struct
import sys

NAMES = ("bind-identity bind-affine-shear bind-tiny-uniform bind-huge-uniform "
 "bind-inverse-translation-domain bind-singular bind-condition-failure "
 "bind-condition-boundary bind-condition-setting-one bind-condition-setting-max "
 "bind-residual-setting-min bind-residual-setting-max bind-empty bind-zero-id "
 "bind-unsafe-id bind-largest-id bind-duplicate-id bind-nonaffine bind-matrix-domain "
 "bind-budget bind-invalid-budget bind-invalid-condition bind-invalid-residual "
 "bind-invalid-vertex-budget bind-invalid-influence-budget deform-identity "
 "deform-translation deform-two-weighted deform-pose-order deform-influence-order "
 "deform-weight-scaled deform-max-weights deform-subnormal-single-weight "
 "deform-scaling-underflow deform-normalizing-underflow deform-zero-weight-known "
 "deform-all-zero deform-negative-weight deform-unknown-zero-weight "
 "deform-duplicate-weight deform-no-influences deform-too-many-influences "
 "deform-four-influences deform-nonuniform-shear deform-explicit-inverse "
 "deform-invalid-inverse-residual deform-residual-exact-boundary "
 "deform-residual-above-boundary deform-inverse-nonaffine deform-missing-pose "
 "deform-extra-pose deform-duplicate-pose deform-duplicate-bind deform-source-domain "
 "deform-output-outside-mesh-domain deform-singular-pose-allowed "
 "deform-empty-vertices deform-vertex-budget deform-influence-budget "
 "deform-palette-domain-finite deform-large-finite-product deform-bind-order "
 "deform-shear-rest-identity bind-dependent-pivot deform-cancellation-limit").split()
INPUT_SHA = '7ebe5edc01e9201679d823d895695a1373bb6a4d9e83fc883abc61dc19cb7274'
ORACLE_INPUT_SHA = 'fadc435e90ac5995d538837b62e35f101eb7eb2435b14d3afd727fc22229c5f4'
MAX_ID = 9007199254740991
TOL = F(256, 2**52)
MIN_SUB = F(1, 2**1074)
HEADER = (['id'] + [f'{p}_{i}' for p in ('r0','r1','g0','g1') for i in range(16)]
          + ['px','py','pz','w0','w1']
          + [f'{p}_{i}' for p in ('i0','i1') for i in range(16)] + ['x','y','z'])

def check(ok, message):
    if not ok:
        raise ValueError(message)

def keys(x, names):
    check(type(x) is dict and set(x) == set(names.split()), 'object schema mismatch')

def num(x):
    check(type(x) in (int,float) and math.isfinite(x), 'finite binary64 number required')
    return float(x)

def integer(x, lo, hi):
    check(type(x) is int and lo <= x <= hi, 'integer shape/domain')

def array(x, maximum):
    check(type(x) is list and len(x) <= maximum, 'array shape/budget')

def vector(x, n):
    check(type(x) is list and len(x) == n, 'vector shape')
    for v in x:
        num(v)

def matrix_records(x, bind=False):
    array(x, 128)
    for b in x:
        keys(b, 'id restWorld inverseBind' if bind else 'id matrix')
        integer(b['id'], 0, MAX_ID+1)  # Deliberately invalid-ID fixtures remain representable.
        for k in ('restWorld','inverseBind') if bind else ('matrix',):
            vector(b[k], 16)

def bits(x):
    if type(x) in (int,float):
        return ['binary64', struct.pack('>d', num(x)).hex()]
    if type(x) is list:
        return [bits(v) for v in x]
    if type(x) is dict:
        return {k:bits(v) for k,v in x.items()}
    return x

def fingerprint(x):
    return hashlib.sha256(json.dumps(bits(x), sort_keys=True, separators=(',',':')).encode()).hexdigest()

def read_text(path):
    p = Path(path)
    check(p.stat().st_size <= 2*1024*1024, 'corpus file too large')
    return p.read_text(encoding='utf-8-sig')

def parse_json(text):
    def pairs(items):
        out = {}
        for k,v in items:
            check(k not in out, 'duplicate JSON key')
            out[k] = v
        return out
    def invalid_constant(token):
        raise ValueError('nonfinite JSON constant: '+token)
    return json.loads(text, object_pairs_hook=pairs,
                      parse_int=lambda s: -0.0 if s == '-0' else int(s),
                      parse_constant=invalid_constant)

def schema(row):
    keys(row, 'name input result')
    check(type(row['name']) is str, 'fixture name')
    q,r = row['input'],row['result']
    keys(q, 'operation rest joints pose vertices settings')
    check(q['operation'] in ('bind','deform'), 'operation')
    matrix_records(q['rest']); matrix_records(q['pose']); matrix_records(q['joints'], True)
    array(q['vertices'], 65536)
    for v in q['vertices']:
        keys(v, 'position influences'); vector(v['position'], 3); array(v['influences'], 5)
        for w in v['influences']:
            keys(w, 'id weight'); integer(w['id'], 0, MAX_ID+1); num(w['weight'])
    check(type(q['settings']) is list and len(q['settings']) == 5, 'settings shape')
    for v in q['settings'][:3]:
        integer(v, 0, 262145)
    for v in q['settings'][3:]:
        num(v)
    keys(r, 'status joints positions diagnostics weightResiduals'); integer(r['status'], 0, 4)
    if q['operation'] == 'bind':
        check(r['positions'] is None and r['weightResiduals'] == [], 'bind output fields')
        check((r['joints'] is not None) == (r['status'] == 0), 'atomic bind output')
        if r['joints'] is not None:
            matrix_records(r['joints'], True)
    else:
        check(r['joints'] is None, 'deform output fields')
        check((r['positions'] is not None) == (r['status'] == 0), 'atomic deform output')
        if r['positions'] is not None:
            array(r['positions'], 65536)
            check(len(r['positions']) == len(q['vertices']), 'source vertex order/size')
            for p in r['positions']: vector(p, 3)
    array(r['diagnostics'], 128)
    diagnostic_ids = [d.get('id') if type(d) is dict else None for d in r['diagnostics']]
    source_ids = [b['id'] for b in (q['rest'] if q['operation'] == 'bind' else q['joints'])]
    check(diagnostic_ids == source_ids[:len(diagnostic_ids)] and len(set(diagnostic_ids)) == len(diagnostic_ids),
          'diagnostic prefix/order/IDs')
    for d in r['diagnostics']:
        keys(d, 'id condition residual pivotFailure'); integer(d['id'], 1, MAX_ID)
        check(type(d['pivotFailure']) is bool, 'pivot flag')
        for k in ('condition','residual'):
            if d[k] is not None: check(num(d[k]) >= 0, 'negative diagnostic')
    array(r['weightResiduals'], 65536)
    check(len(r['weightResiduals']) <= len(q['vertices']), 'normalization prefix size')
    for v in r['weightResiduals']:
        check(0 <= num(v) <= 32*2**-52, 'normalization residual')
    if q['operation'] == 'deform' and r['status'] == 0:
        check(len(r['weightResiduals']) == len(q['vertices']), 'normalization diagnostics count')

def load(path):
    data = parse_json(read_text(path)); keys(data, 'schema fixtures')
    check(type(data['schema']) is int and data['schema'] == 1, 'schema version')
    rows = data['fixtures']; array(rows, len(NAMES))
    check([r.get('name') if type(r) is dict else None for r in rows] == NAMES,
          'fixed fixture identity/count/order')
    for row in rows: schema(row)
    check(fingerprint([{'name':r['name'],'input':r['input']} for r in rows]) == INPUT_SHA,
          'fixed corpus binary64 inputs changed')
    return rows

def mat(x):
    return [[F(num(x[4*c+r])) for c in range(4)] for r in range(4)]

def eye():
    return [[F(r == c) for c in range(4)] for r in range(4)]

def inverse(a):
    # Full exact 4x4 elimination with first nonzero pivot: intentionally unlike
    # the implementation's scaled floating 3x3 affine elimination.
    a = [list(row)+ident for row,ident in zip(a,eye())]
    for col in range(4):
        pivot = next((r for r in range(col,4) if a[r][col]), None)
        if pivot is None: return None
        a[col],a[pivot] = a[pivot],a[col]
        scale = a[col][col]; a[col] = [v/scale for v in a[col]]
        for r in range(4):
            if r != col:
                scale = a[r][col]
                a[r] = [x-scale*y for x,y in zip(a[r],a[col])]
    return [row[4:] for row in a]

def mm(a,b):
    return [[sum((a[r][k]*b[k][c] for k in range(4)), F(0)) for c in range(4)] for r in range(4)]

def mv(a,p):
    return [sum((a[r][k]*p[k] for k in range(4)), F(0)) for r in range(4)]

def norm(a,n):
    return max(sum(abs(a[r][c]) for c in range(n)) for r in range(n))

def residual(a,b):
    return max(norm([[p[r][c]-int(r == c) for c in range(4)] for r in range(4)],4)
               for p in (mm(a,b),mm(b,a)))

def affine_ok(x):
    return all(abs(v) <= 1e150 for v in x) and [x[i] for i in (3,7,11,15)] == [0,0,0,1]

def expected_status(q):
    """Independent input predicates plus exact algebraic rejection witnesses.

    These corpus witnesses are separated from the kernel's point diagnostic
    algorithm. They are not a specification that every near-threshold input
    must have the same result as an exact condition/residual test.
    """
    mb,mvtx,mi,mc,mr = q['settings']
    if not (1 <= mb <= 128 and 1 <= mvtx <= 65536 and 1 <= mi <= 262144
            and 1 <= mc <= 1e12 and 1e-15 <= mr <= 1e-3): return 1
    records = q['rest'] if q['operation'] == 'bind' else q['joints']
    ids = [b['id'] for b in records]
    if not ids or len(set(ids)) != len(ids) or any(not 1 <= i <= MAX_ID for i in ids): return 1
    for b in records:
        for k in ('matrix',) if q['operation'] == 'bind' else ('restWorld','inverseBind'):
            if not affine_ok(b[k]): return 1
    if q['operation'] == 'deform':
        pids = [b['id'] for b in q['pose']]
        if len(set(pids)) != len(pids) or set(pids) != set(ids): return 1
        if any(not affine_ok(b['matrix']) for b in q['pose']): return 1
        for v in q['vertices']:
            ws = v['influences']; wis = [w['id'] for w in ws]
            if (any(abs(p) > 1e6 for p in v['position']) or not 1 <= len(ws) <= 4
                or len(set(wis)) != len(wis) or not set(wis) <= set(ids)
                or any(w['weight'] < 0 for w in ws) or not any(w['weight'] > 0 for w in ws)): return 1
    if (len(records) > mb or len(q['pose']) > mb or len(q['vertices']) > mvtx
        or sum(len(v['influences']) for v in q['vertices']) > mi): return 2
    for b in records:
        a = mat(b['matrix'] if q['operation'] == 'bind' else b['restWorld'])
        exact_inv = inverse(a)
        if exact_inv is None: return 3
        # The output domain is a binary64 point domain. A real inverse just
        # beyond the boundary can round to the permitted boundary value.
        if q['operation'] == 'bind' and any(abs(float(v)) > 1e150 for row in exact_inv for v in row): return 4
        if norm(a,3)*norm(exact_inv,3) > F(num(mc)): return 3
        if q['operation'] == 'deform' and residual(a,mat(b['inverseBind'])) > F(num(mr)): return 3
    if q['operation'] == 'deform':
        for v in q['vertices']:
            ws = [F(num(w['weight'])) for w in v['influences'] if w['weight'] > 0]
            # Exact positive mathematical weight that rounds to zero in one
            # of the documented two normalization stages (ties-to-even).
            if any(w/max(ws) <= MIN_SUB/2 or w/sum(ws) <= MIN_SUB/2 for w in ws): return 4
    return 0

class Audit:
    def __init__(self):
        self.checks = 0; self.max_abs = F(0); self.max_scaled = F(0)
        self.cancellation = None; self.max_abs_label = None
    def close(self, actual, reference, label, scale=None):
        error = abs(F(num(actual))-reference)
        denominator = max(F(1), abs(reference)) if scale is None else max(F(1),scale)
        check(error <= TOL*denominator, label+': point error exceeds fixed tolerance')
        self.checks += 1
        if error > self.max_abs: self.max_abs_label = label
        self.max_abs = max(self.max_abs,error); self.max_scaled = max(self.max_scaled,error/denominator)
        return error
    def summary(self):
        return {'pointChecks':self.checks, 'maximumAbsoluteError':float(self.max_abs),
                'maximumAbsoluteErrorAt':self.max_abs_label,
                'maximumScaledError':float(self.max_scaled), 'tolerance':float(TOL),
                'cancellationLimit':self.cancellation}

def deform_reference(q):
    pose = {b['id']:mat(b['matrix']) for b in q['pose']}
    inv = {b['id']:mat(b['inverseBind']) for b in q['joints']}
    answer = []
    for v in q['vertices']:
        p = [F(num(x)) for x in v['position']]+[F(1)]
        total = sum(F(num(w['weight'])) for w in v['influences'])
        terms = [(F(num(w['weight']))/total, mv(mm(pose[w['id']],inv[w['id']]),p)) for w in v['influences']]
        answer.append(([sum(w*t[c] for w,t in terms) for c in range(3)],
                       [sum(abs(w*t[c]) for w,t in terms) for c in range(3)]))
    return answer

def verify(rows):
    audit = Audit()
    for row in rows:
        name,q,r = row['name'],row['input'],row['result']
        check(r['status'] == expected_status(q), name+': independent status witness')
        if r['status'] != 0: continue
        if q['operation'] == 'bind':
            check(len(r['joints']) == len(q['rest']), name+': bind count')
            for b,j in zip(q['rest'],r['joints']):
                check(j['id'] == b['id'] and bits(j['restWorld']) == bits(b['matrix']), name+': rest order/ID/bits')
                check(affine_ok(j['inverseBind']), name+': inverse output domain')
                exact = inverse(mat(b['matrix']))
                for col in range(4):
                    for rr in range(4):
                        audit.close(j['inverseBind'][4*col+rr],exact[rr][col],name+': inverse')
        else:
            for vi,(actual,(reference,scale)) in enumerate(zip(r['positions'],deform_reference(q))):
                for c in range(3):
                    if name == 'deform-cancellation-limit':
                        error = audit.close(actual[c],reference[c],name)
                        if c == 0:
                            check(reference[c] == 1, 'independent cancellation analytic reference')
                            audit.cancellation = {'exactX':'1', 'pointX':actual[c],
                              'absoluteError':float(error), 'weightedTermMagnitude':float(scale[c]),
                              'acceptance':'ordinary 256 epsilon times max(1, absolute exact result); no special cancellation exemption'}
                    else:
                        audit.close(actual[c],reference[c],f'{name}: vertex {vi} component {c}')
        # Diagnostic values are floating estimates, not outward bounds. Check
        # closeness to independently formed rational metrics, not containment.
        palette = {b['id']:b for b in (r['joints'] if q['operation'] == 'bind' else q['joints'])}
        check(len(r['diagnostics']) == len(palette), name+': complete diagnostic count')
        check([d['id'] for d in r['diagnostics']] == list(palette), name+': diagnostic order')
        for d in r['diagnostics']:
            b = palette[d['id']]; a,inv = mat(b['restWorld']),mat(b['inverseBind'])
            check(not d['pivotFailure'] and d['condition'] is not None and d['residual'] is not None,
                  name+': completed diagnostic validity')
            audit.close(d['condition'],norm(a,3)*norm(inv,3),name+': condition estimate')
            audit.close(d['residual'],residual(a,inv),name+': residual estimate')
    byname = {r['name']:r for r in rows}
    baseline = bits(byname['deform-two-weighted']['result']['positions'])
    for name in ('deform-pose-order','deform-influence-order','deform-bind-order'):
        check(bits(byname[name]['result']['positions']) == baseline, name+': stable ID/order regression')
    return audit.summary()

def load_oracle(path):
    raw = list(csv.reader(io.StringIO(read_text(path))))
    check(len(raw) == 129 and raw[0] == HEADER, 'oracle fixed header/128-row count')
    rows = []
    for i,row in enumerate(raw[1:]):
        check(len(row) == len(HEADER) and row[0] == str(i), 'oracle width/identity/order')
        check(all(re.fullmatch(r'-?0x[0-9a-f]+(?:\.[0-9a-f]*)?p[+-]?[0-9]+',s) for s in row[1:]),
              'oracle canonical hexadecimal binary64 required')
        values = [float.fromhex(v) for v in row[1:]]
        for v in values: num(v)
        rows.append([i]+values)
    check(fingerprint([row[:70] for row in rows]) == ORACLE_INPUT_SHA,
          'fixed oracle binary64 inputs changed')
    return rows

def verify_oracle(rows):
    audit = Audit()
    for row in rows:
        m = [row[1+i*16:17+i*16] for i in range(4)]
        p,ws = row[65:68],row[68:70]
        invs = [row[70:86],row[86:102]]
        for rest,actual in zip(m[:2],invs):
            exact = inverse(mat(rest)); check(exact is not None, 'oracle singular rest')
            for c in range(4):
                for r in range(4): audit.close(actual[c*4+r],exact[r][c],'oracle inverse')
        # Derive the final position using the ideal exact rest inverse too:
        # this corpus's dyadic affine inverses are exactly representable.
        for k in range(2):
            check(mat(invs[k]) == inverse(mat(m[k])), 'oracle supplied inverse not exact dyadic reference')
        total = sum(F(w) for w in ws)
        transformed = [mv(mm(mat(m[k+2]),inverse(mat(m[k]))),list(map(F,p))+[F(1)]) for k in range(2)]
        for c in range(3):
            expected = sum(F(ws[k])/total*transformed[k][c] for k in range(2))
            audit.close(row[102+c],expected,'oracle weighted position')
    return audit.summary()

def self_test():
    a = [[F(x) for x in row] for row in ([2,1,0,3],[0,4,2,-1],[0,0,5,2],[0,0,0,1])]
    b = inverse(a)
    check(mm(a,b) == eye() and mm(b,a) == eye(), 'rational inverse self-test')
    check(b[0] == [F(1,2),F(-1,8),F(1,20),F(-69,40)], 'independent triangular inverse row')
    check(inverse([[F(0)]*4 for _ in range(4)]) is None, 'singular inverse self-test')
    check(F(1,4)*F(2)+F(3,4)*F(7) == F(23,4), 'exact weight self-test')
    check(bits(parse_json('-0')) != bits(parse_json('0')), 'signed zero was lost')
    for text in ('{"x":1,"x":2}', 'NaN', 'Infinity'):
        try: parse_json(text)
        except ValueError: pass
        else: raise ValueError('JSON rejection self-test')
    try: num(parse_json('1e999'))
    except ValueError: pass
    else: raise ValueError('overflow JSON rejection self-test')

def main():
    check(__debug__, 'Python optimized mode (-O) is not supported')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('native', nargs='?'); p.add_argument('wasm', nargs='?')
    p.add_argument('--oracle'); p.add_argument('--wasm-oracle'); p.add_argument('--self-test',action='store_true')
    args = p.parse_args(); self_test()
    check(args.native is not None or args.self_test, 'native fixture file required')
    result = {'selfTest':'passed','reference':'independent exact-rational 4x4 inverse and authored-weight LBS',
              'scope':'fixed finite point corpus; not a general rigorous error enclosure'}
    if args.native:
        rows = load(args.native); result.update(fixtures=len(rows),inputSHA256=INPUT_SHA,native=verify(rows))
        if args.wasm:
            other = load(args.wasm); result['wasm'] = verify(other)
            check(bits(other) == bits(rows), 'Native/WASM fixture binary64 bits differ')
            result['fixtureBitsMatch'] = True
    if args.oracle:
        oracle = load_oracle(args.oracle); result.update(oracleRows=len(oracle),oracleInputSHA256=ORACLE_INPUT_SHA,
                                                       nativeOracle=verify_oracle(oracle))
        if args.wasm_oracle:
            other = load_oracle(args.wasm_oracle); result['wasmOracle'] = verify_oracle(other)
            check(bits(other) == bits(oracle), 'Native/WASM oracle binary64 bits differ')
            result['oracleBitsMatch'] = True
    check(not args.wasm_oracle or args.oracle, '--wasm-oracle requires --oracle')
    print(json.dumps(result,indent=2,allow_nan=False))

if __name__ == '__main__':
    try: main()
    except (ValueError,TypeError,KeyError,OverflowError,OSError,json.JSONDecodeError,csv.Error) as exc:
        print('FAIL '+str(exc), file=sys.stderr); sys.exit(1)
