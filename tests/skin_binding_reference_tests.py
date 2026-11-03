#!/usr/bin/env python3
"""Run positive and deliberately invalid CLI controls without deleting evidence."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

CHECKER=Path('scripts/verify-skin-binding.py')
spec=importlib.util.spec_from_file_location('skin_binding_reference',CHECKER)
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')
def replace_once(text,a,b):
    checker.require(a in text,'control mutation anchor');return text.replace(a,b,1)

def main():
    checker.require(__debug__,'control runner requires normal Python')
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',nargs='?',default='build/skin-binding-proof/latest.json');parser.add_argument('--output',default='build/skin-binding-reference');args=parser.parse_args()
    original=Path(args.run)
    if original.is_file():original=Path(checker.load(original)['runDirectory'])
    checker.require(original.is_dir(),'reference run exists');root=Path(args.output);root.mkdir(parents=True,exist_ok=True);proof=Path(tempfile.mkdtemp(prefix='run-',dir=root))
    files=['outputs.json','commands.json','report.json','preserve.skin']+[n+'.json' for n in checker.NAMES]
    records=[];positive=negative=0
    def duplicate(label):
        directory=proof/label;directory.mkdir()
        for file in files:shutil.copyfile(original/file,directory/file)
        return directory
    def invoke(label,path,success,fragment=None,optimized=False):
        nonlocal positive,negative
        command=[sys.executable,*(['-O'] if optimized else []),str(CHECKER),str(path)];r=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
        ok=(r.returncode==0) if success else (r.returncode!=0 and (fragment is None or fragment in r.stderr))
        records.append({'name':label,'command':command,'exitCode':r.returncode,'expectedSuccess':success,'expectedFailureFragment':fragment,'matchedExpectation':ok,'stdout':r.stdout,'stderr':r.stderr})
        (proof/'commands.json').write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        checker.require(ok,'control did not fail/pass as intended: '+label+' '+r.stderr)
        if success:
            positive+=1
            if label=='actual-run':(proof/'acceptance.json').write_text(r.stdout,encoding='utf-8')
        else:negative+=1
    invoke('actual-run',original,True)
    pointer=proof/'latest.json';write_json(pointer,{'runDirectory':original.as_posix()});invoke('latest-pointer',pointer,True)
    rewritten=duplicate('rewritten-json-numeric-tokens')
    for file in [n+'.json' for n in checker.NAMES]+['outputs.json','commands.json','report.json']:
        write_json(rewritten/file,checker.load(rewritten/file))
        text=(rewritten/file).read_text(encoding='utf-8');(rewritten/file).write_text(re.sub(r'-0\.0(?=[,}\]])','-0',text),encoding='utf-8')
    invoke('literal-integer-negative-zero',rewritten,True)
    def bad_data(label,mutation,fragment):
        directory=duplicate(label);data=checker.load(directory/'outputs.json');commands=checker.load(directory/'commands.json');mutation(data,commands,directory);write_json(directory/'outputs.json',data);write_json(directory/'commands.json',commands);invoke(label,directory,False,fragment)
    bad_data('dropped-case',lambda d,c,p:d['fixtures'].pop(),'fixed eight fixture count')
    bad_data('duplicate-case',lambda d,c,p:d['fixtures'].__setitem__(1,copy.deepcopy(d['fixtures'][0])),'fixed unique fixture identities/order')
    bad_data('reordered-cases',lambda d,c,p:d['fixtures'].reverse(),'fixed unique fixture identities/order')
    bad_data('unknown-output-field',lambda d,c,p:d.update(extra=0),'output root fields')
    bad_data('boolean-schema',lambda d,c,p:d.update(schema=True),'output schema')
    bad_data('wrong-time',lambda d,c,p:d['fixtures'][0]['samples'][2].update(seconds=3),'sample time/mode identity')
    bad_data('dropped-sample',lambda d,c,p:d['fixtures'][0]['samples'].pop(),'five fixed samples')
    def corrupt_bits(d,c,p):d['fixtures'][0]['inputBits']['mesh']['positions'][0][0]['f64']='3ff0000000000000'
    bad_data('captured-bit-tree-corruption',corrupt_bits,'captured source bit tree')
    def fingerprint(d,c,p):
        f=d['fixtures'][0]
        for key in ('input','roundtrip'):f[key]['fingerprint']='0000000000000000'
        f['inputBits']=checker.bit_tree(f['input']);f['roundtripBits']=checker.bit_tree(f['roundtrip']);write_json(p/'default.json',f['input'])
    bad_data('wrong-FNV-field',fingerprint,'independent FNV64')
    def point(d,c,p):
        s=d['fixtures'][0]['samples'][2]
        for key in ('native','web'):s[key]['positions'][2][0]=8.
        s['nativeBits']=checker.bit_tree(s['native']);s['webBits']=checker.bit_tree(s['web']);c[4]['stdout']=json.dumps(s['native'],allow_nan=False)+'\n'
    bad_data('self-consistent-wrong-quarter-turn',point,'independent affine point error')
    def no_partial(d,c,p):
        s=d['fixtures'][4]['samples'][0]
        for key in ('native','web'):s[key]['positions']=[]
        s['nativeBits']=checker.bit_tree(s['native']);s['webBits']=checker.bit_tree(s['web']);c[30]['stdout']=json.dumps(s['native'])+'\n'
    bad_data('quality-failure-partial-output',no_partial,'failure has no partial positions')
    def stdout(d,c,p):
        value=checker.loads(c[4]['stdout']);value['positions'][2][0]=8;c[4]['stdout']=json.dumps(value)+'\n'
    bad_data('native-stdout-differs',stdout,'actual native stdout binary64 bits differ')
    def negative_zero(d,c,p):
        raw=checker.load(p/(checker.NAMES[3]+'.json'));raw['mesh']['positions'][0][0]=0.;write_json(p/(checker.NAMES[3]+'.json'),raw)
    bad_data('raw-json-negative-zero-lost',negative_zero,'raw JSON binary64 bits differ')
    bad_data('command-dropped',lambda d,c,p:c.pop(),'command corpus count')
    def preserved(d,c,p):(p/'preserve.skin').write_bytes(b'damaged\n')
    bad_data('existing-output-damaged',preserved,'existing output preservation')
    def raw_control(label,file,mutate,fragment):
        directory=duplicate(label);path=directory/file;path.write_bytes(mutate(path.read_bytes()));invoke(label,directory,False,fragment)
    raw_control('duplicate-json-key','outputs.json',lambda b:replace_once(b.decode(),'{"schema":1,','{"schema":1,"schema":1,').encode(),'duplicate JSON key')
    raw_control('nonfinite-constant','outputs.json',lambda b:replace_once(b.decode(),'{"schema":1,','{"schema":NaN,').encode(),'nonfinite JSON constant')
    raw_control('overflow-number','default.json',lambda b:replace_once(b.decode(),'"version":1,','"version":1e999,').encode(),'nonfinite/overflow JSON number')
    raw_control('decimal-underflow','default.json',lambda b:replace_once(b.decode(),'"weight":1','"weight":1e-400').encode(),'nonzero JSON decimal underflow')
    raw_control('invalid-UTF8','outputs.json',lambda b:b+b'\xff','utf-8')
    raw_control('unpaired-surrogate','default.json',lambda b:replace_once(b.decode(),'"arm-mesh"','"\\ud800"').encode(),'surrogates not allowed')
    raw_control('truncated-JSON','outputs.json',lambda b:b.rstrip()[:-1],'Expecting')
    invoke('optimized-Python-rejected',original,False,'Python -O',True)
    # Independent primitive checks do not use captured engine fingerprints.
    expected=checker.expected_sources();checker.require(checker.mesh_fingerprint(expected[0]['mesh'])=='9da65482c00e78b0','independent FNV primitive')
    checker.require(checker.mesh_fingerprint(expected[3]['mesh'])==checker.mesh_fingerprint(expected[0]['mesh']),'FNV zero canonicalization')
    value=checker.reference_point([2,-.2,0],[{'boneId':19,'weight':1}],True);checker.require(value==[1-checker.F(-.2),checker.F(1),checker.F(0)],'rational ninety-degree pivot')
    result={'status':'PASS','runDirectory':proof.as_posix(),'positiveControls':positive,'negativeControlsRejected':negative,'allMatchedExpectations':True,'analyticPointComponents':288,'checkerSHA256':hashlib.sha256(CHECKER.read_bytes()).hexdigest(),'inputRunDirectory':original.as_posix(),'notes':'No source run overwritten or recursively deleted. Incorrect quarter-turn was made self-consistent across both runtimes, captured bits and actual Native stdout; exact reference still rejected it.'}
    (proof/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');write_json(root/'latest.json',result);print(json.dumps(result,indent=2))

if __name__=='__main__':
    try:main()
    except (ValueError,TypeError,KeyError,IndexError,OSError,UnicodeError) as error:print('FAIL '+str(error),file=sys.stderr);sys.exit(1)
