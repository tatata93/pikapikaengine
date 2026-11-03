#!/usr/bin/env python3
"""Original rational reference self-tests and retained Native negative controls.

Every invocation creates a fresh ignored run directory. Original fixture files
are copied, never overwritten/deleted. Rejected controls are not successful
geometry cases. No external package, compiler or finished geometry solver is used.
"""
import argparse
import copy
from fractions import Fraction as F
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
CHECKER=ROOT/'scripts/verify-derived-mesh.py'
spec=importlib.util.spec_from_file_location('derived_mesh_reference',CHECKER)
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class RationalReferenceTests(unittest.TestCase):
    def test_binary32_exact_values(self):
        for bits,value in [(0,F(0)),(0x80000000,F(0)),(1,F(1,2**149)),(0x80000001,-F(1,2**149)),
                           (0x00800000,F(1,2**126)),(0x3f800000,F(1)),(0xc0000000,F(-2)),
                           (0x7f7fffff,F(2**128-2**104))]:
            self.assertEqual(d.f32_fraction(bits),value)
        for bits in (0x7f800000,0xff800000,0x7fc00000):
            with self.assertRaises(ValueError):d.f32_fraction(bits)
    def test_rounding_binary_boundaries(self):
        pairs=[(0.,0),(-0.,0x80000000),(1+2**-24,0x3f800000),(1+3*2**-24,0x3f800002),
               (math.nextafter(1+2**-24,2),0x3f800001),(-1-2**-24,0xbf800000),
               (2**-150,0),(3*2**-150,2),(-2**-150,0x80000000),
               (2**-149,1),(2**-126,0x00800000),(sys.float_info.max,0x7f800000)]
        for value,bits in pairs:self.assertEqual(d.rounded_f32_bits(value),bits)
    def test_finite_binary32_exact_roundtrip(self):
        # Deterministic bit corpus; the oracle never invokes struct.pack('f').
        state=0x243f6a88
        for _ in range(2048):
            state=(1664525*state+1013904223)&0xffffffff
            if ((state>>23)&255)==255:continue
            self.assertEqual(d.rounded_f32_bits(float(d.f32_fraction(state))),state)
    def test_exact_cross_and_oriented_rational_normal(self):
        c=d.cross([F(0)]*3,[F(1),F(0),F(0)],[F(0),F(4),F(-3)])
        self.assertEqual(c,[0,3,4]);self.assertEqual(sum(v*v for v in c),25)
        self.assertTrue(d.normal_contains(F(3),F(25),F(3,5),F(3,5)))
        self.assertFalse(d.normal_contains(F(-3),F(25),F(3,5),F(3,5)))
        self.assertTrue(d.normal_contains(F(-3),F(25),F(-3,5),F(-3,5)))
    def test_irrational_root_uses_square_inequalities(self):
        self.assertTrue(d.normal_contains(F(1),F(2),F(7,10),F(71,100)))
        self.assertFalse(d.normal_contains(F(1),F(2),F(0),F(7,10)))
        n=d.f32_fraction(0x3f3504f3)
        self.assertTrue(d.normal_contains(F(1),F(2),n-d.NORMAL_TOLERANCE,n+d.NORMAL_TOLERANCE))
        self.assertFalse(d.normal_contains(F(1),F(2),n,n))
        self.assertTrue(d.normal_contains(F(0),F(2),F(0),F(0)))
        with self.assertRaises(ValueError):d.normal_contains(F(0),F(0),F(0),F(0))
    def test_true_candidate_error_not_unit_length_alone(self):
        n=d.f32_fraction(0x3f19999a)
        self.assertNotEqual(n,F(3,5))
        self.assertTrue(d.normal_contains(F(3),F(25),n-d.NORMAL_TOLERANCE,n+d.NORMAL_TOLERANCE))
        self.assertFalse(d.normal_contains(F(3),F(25),n,n))
        self.assertFalse(d.normal_contains(F(3),F(25),-n-d.NORMAL_TOLERANCE,-n+d.NORMAL_TOLERANCE))
    def test_json_and_exact_binary64_constants(self):
        self.assertNotEqual(d.FLOOR,F(1,10**24));self.assertNotEqual(d.NORMAL_TOLERANCE,F(1,10**6))
        self.assertNotEqual(d.f64hex(d.loads('-0')),d.f64hex(d.loads('0')))
        for text in ('{"a":1,"a":2}','NaN','Infinity'):
            with self.assertRaises(ValueError):d.loads(text)
        for text in ('1e999','1e-999','-1e-999'):
            with self.assertRaises(ValueError):d.loads(text)
        self.assertEqual(d.loads('0e-999'),0)
        self.assertEqual(d.f64hex(d.loads('-0.0e-999')),d.f64hex(-0.0))

def main():
    d.require(__debug__,'reference tests require normal Python, not -O')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('native')
    parser.add_argument('--output',default=str(ROOT/'build/derived-mesh-reference'));args=parser.parse_args()
    output=Path(args.output).resolve();allowed=(ROOT/'build').resolve()
    relative=output.relative_to(allowed)
    d.require(relative.parts and relative.parts[0].startswith('derived-mesh-reference'),
              'proof output must stay in build/derived-mesh-reference*')
    original=Path(args.native).resolve();d.require(original.is_file(),'Native fixture file required')
    output.mkdir(parents=True,exist_ok=True);proof=Path(tempfile.mkdtemp(prefix='run-',dir=output))
    snapshot=proof/'native.json';shutil.copyfile(original,snapshot)
    captured=proof/'captured-native';captured.mkdir()
    for path in original.parent.iterdir():
        if path.is_file() and path.suffix in ('.json','.cmd','.txt','.bin'):
            shutil.copyfile(path,captured/path.name)
    unitlog=io.StringIO();suite=unittest.defaultTestLoader.loadTestsFromTestCase(RationalReferenceTests)
    units=unittest.TextTestRunner(stream=unitlog,verbosity=2).run(suite)
    (proof/'reference-self-tests.txt').write_text(unitlog.getvalue(),encoding='utf-8')
    d.require(units.wasSuccessful(),'rational self-tests failed: '+unitlog.getvalue())
    records=[];positive=negative=0
    def invoke(label,path,success,fragment=None,optimized=False):
        nonlocal positive,negative
        command=[sys.executable,*(['-O'] if optimized else []),str(CHECKER),str(path)]
        r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
        matched=(r.returncode==0) if success else (r.returncode!=0 and (fragment is None or fragment in r.stderr))
        records.append({'name':label,'command':command,'exitCode':r.returncode,'expectedSuccess':success,
                        'expectedFailureFragment':fragment,'matchedExpectation':matched,'stdout':r.stdout,'stderr':r.stderr})
        (proof/'commands.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
        d.require(matched,'control mismatch '+label+': '+r.stderr)
        if success:
            positive+=1
            if label=='actual-native':(proof/'acceptance.json').write_text(r.stdout,encoding='utf-8')
        else:negative+=1
    invoke('actual-native',snapshot,True)
    data=d.read(snapshot)
    def dump(label,value):
        path=proof/(label+'.json');path.write_text(json.dumps(value,separators=(',',':'),allow_nan=True)+'\n',encoding='utf-8');return path
    rewritten=dump('literal-integer-negative-zero',data)
    rewritten.write_text(re.sub(r'-0\.0(?=[,}\]])','-0',rewritten.read_text(encoding='utf-8')),encoding='utf-8')
    invoke('literal-integer-negative-zero',rewritten,True)
    def find(value,name):return next(row for row in value['fixtures'] if row['name']==name)
    def bad(label,mutation,fragment):
        value=copy.deepcopy(data);mutation(value);invoke(label,dump(label,value),False,fragment)
    def raw(label,text,fragment):
        path=proof/(label+'.json');path.write_text(text,encoding='utf-8');invoke(label,path,False,fragment)
    bad('drop-case',lambda x:x['fixtures'].pop(),'fixtures array width/count')
    bad('duplicate-case',lambda x:x['fixtures'].__setitem__(1,copy.deepcopy(x['fixtures'][0])),'fixed fixture names/count/order')
    bad('reorder-cases',lambda x:x['fixtures'].reverse(),'fixed fixture names/count/order')
    bad('unknown-root-field',lambda x:x.update(extra=0),'root fields')
    bad('boolean-schema',lambda x:x.update(schema=True),'schema version')
    bad('boolean-status',lambda x:x['fixtures'][0]['result'].update(status=False),'status integer')
    bad('wrong-failure-status',lambda x:find(x,'area-below-floor')['result'].update(status=5),'fixed independent expected status/reason')
    bad('changed-input',lambda x:x['fixtures'][0]['input']['positions'][1].__setitem__(0,2),'input fingerprint')
    bad('lost-input-zero-sign',lambda x:find(x,'signed-zero')['input']['positions'][0].__setitem__(0,0),'input fingerprint')
    raw('duplicate-json-key',snapshot.read_text(encoding='utf-8').replace('"schema":1','"schema":1,"schema":1',1),'duplicate JSON key')
    bad('nonfinite-json',lambda x:x['fixtures'][0]['result']['audits'][0]['cross'][0].__setitem__(0,float('nan')),'nonfinite JSON constant')
    text=re.sub(r'"normalError":\[[^\]]*\]','"normalError":[0,0,1e999]',snapshot.read_text(encoding='utf-8'),count=1)
    raw('decimal-overflow',text,'nonfinite JSON decimal')
    original_text=snapshot.read_text(encoding='utf-8')
    d.require('"cross":[[-0,0]' in original_text,'zero output endpoint control target')
    for label,token,fragment in [('zero-endpoint-underflow','1e-999','nonzero JSON decimal underflow'),
                                 ('zero-endpoint-overflow','1e999','nonfinite JSON decimal')]:
        raw(label,original_text.replace('"cross":[[-0,0]','"cross":[[-0,'+token+']',1),fragment)
    bad('reversed-interval',lambda x:x['fixtures'][0]['result']['audits'][0].update(squaredCross=[2,1]),'reversed interval')
    bad('false-cross-bound',lambda x:x['fixtures'][0]['result']['audits'][0]['cross'].__setitem__(2,[0,0]),'exact rounded cross containment')
    bad('false-Q-bound',lambda x:x['fixtures'][0]['result']['audits'][0].update(squaredCross=[0,0]),'exact squared cross containment')
    bad('false-normal-bound',lambda x:x['fixtures'][0]['result']['audits'][0]['normalized'].__setitem__(2,[0,0]),'exact oriented unit normal containment')
    bad('understated-normal-error',lambda x:find(x,'rational-345')['result']['audits'][0].update(normalError=[0,0,0]),'claimed candidate normal error bound')
    def false_candidate(x):
        result=find(x,'rational-345')['result'];result['audits'][0]['normalBits'][1]=0x3f800000
        for corner in range(3):result['interleavedBits'][corner*6+4]=0x3f800000
    bad('consistent-false-candidate-and-buffer',false_candidate,'claimed candidate normal error bound')
    def false_position(x):
        result=x['fixtures'][0]['result'];result['positionsBits'][1][0]=0x40000000;result['interleavedBits'][6]=0x40000000
    bad('consistent-false-position-and-buffer',false_position,'independent nearest-even position bits')
    bad('nonfinite-f32-bits',lambda x:x['fixtures'][0]['result']['positionsBits'][0].__setitem__(0,0x7fc00000),'nonfinite binary32')
    bad('truncated-expanded-buffer',lambda x:x['fixtures'][0]['result']['interleavedBits'].pop(),'expanded output array width/count')
    bad('wrong-expanded-order',lambda x:x['fixtures'][0]['result']['interleavedBits'].__setitem__(0,0x3f800000),'expanded candidate/position bits and order')
    bad('boolean-output-index',lambda x:x['fixtures'][0]['result']['triangles'][0].__setitem__(1,True),'output index integer')
    bad('failure-partial-position',lambda x:find(x,'second-degenerate-no-buffer')['result'].update(positionsBits=[[0,0,0]]),'failure has no partial buffer')
    bad('failure-partial-buffer',lambda x:find(x,'area-below-floor')['result'].update(interleavedBits=[]),'failure has no partial buffer')
    bad('completed-missing-buffer',lambda x:x['fixtures'][0]['result'].update(positionsBits=None),'completed buffer fields missing')
    bad('missing-failure-audit',lambda x:find(x,'collinear-uncertain')['result'].update(audits=[]),'failed face audit prefix missing')
    bad('wrong-first-failing-face',lambda x:find(x,'second-invalid-preflight')['result'].update(failedFace=0),'first invalid face')
    bad('wrong-audit-prefix',lambda x:find(x,'second-degenerate-no-buffer')['result']['audits'][0].update(face=1),'audit prefix/order')
    bad('wrong-sqrt-counter',lambda x:x['fixtures'][0]['result'].update(sqrtRefinements=0),'total sqrt count')
    bad('integer-sqrt-flag',lambda x:x['fixtures'][0]['result']['audits'][0].update(sqrtRefinementLimited=1),'sqrt limited flag')
    bad('false-minimum-bounds',lambda x:x['fixtures'][0]['result']['minimumBits'].__setitem__(0,0x3f800000),'exact indexed bounds')
    bad('uncertified-error-threshold',lambda x:x['fixtures'][0]['result']['audits'][0].update(normalError=[0,0,1e-5]),'candidate error exceeds fixed tolerance')
    invoke('python-optimized',snapshot,False,'Python -O is unsupported',True)
    paths=[CHECKER,Path(__file__).resolve(),snapshot,ROOT/'core/include/pikapika/derived_mesh.hpp',ROOT/'core/src/derived_mesh.cpp',ROOT/'tests/derived_mesh_tests.cpp']
    files=[]
    for path in paths:
        content=path.read_bytes();files.append({'path':str(path),'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    report={'status':'PASS','runDirectory':str(proof),'selfTests':units.testsRun,'acceptedControls':positive,'rejectedControls':negative,
            'actualNative':json.loads((proof/'acceptance.json').read_text(encoding='utf-8')),
            'originalNativeFile':str(original),'files':files,
            'scope':'Native only; injected controls are separate from actual model successes. LBS collapse is an analytic input, not an end-to-end skinning test.'}
    (proof/'provenance.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    (proof/'summary.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    # A mutable discovery pointer only; every complete run and original raw file
    # remains intact. This is not an acceptance/fingerprint blessing mechanism.
    (output/'latest.json').write_text(json.dumps({'runDirectory':str(proof)},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print('FAIL '+str(error),file=sys.stderr);sys.exit(1)
