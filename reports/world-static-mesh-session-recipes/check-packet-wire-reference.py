"""Pinned independent24 packet reference and copied actual-record controls."""
from pathlib import Path
import copy,hashlib,importlib.util,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'reports/world-static-mesh-session-packet-wire-reference/run-20261105-pinned-001'
def need(v,m):
    if not v:raise ValueError(m)
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,d):
    with p.open('x',encoding='utf8',newline='\n') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def main():
    need(not OUT.exists(),'Fresh pinned reference');OUT.mkdir(parents=True);path=ROOT/'scripts/verify-world-static-mesh-session-packet-wire.py';sys.dont_write_bytecode=True;spec=importlib.util.spec_from_file_location('packet_ref',path);ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    inputs=[HERE/'run-20261105-packet-wire-producer-002'/(c+'-packet-wire.json') for c in ['Release','Debug']];paths=[path,Path(__file__).resolve(),*inputs,ROOT/'core/include/pikapika/world_static_mesh_session_packet_wire.hpp',ROOT/'core/src/world_static_mesh_session_packet_wire.cpp',ROOT/'tests/world_static_mesh_session_packet_wire_tests.cpp'];before=[stamp(p) for p in paths];write(OUT/'before.json',before);observations=[]
    for label,source in zip(['Release','Debug'],inputs):
        argv=[sys.executable,'-B',str(path),str(source)];p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30);(OUT/(label+'.stdout.txt')).write_bytes(p.stdout);(OUT/(label+'.stderr.txt')).write_bytes(p.stderr);write(OUT/(label+'.command.json'),dict(argv=argv,exitCode=p.returncode));need(p.returncode==0,'Actual pinned subprocess '+label);r=json.loads(p.stdout);need(r['status']=='PASS' and r['rows']==24 and r['mappedFloatBitValues']==492,'Complete mapped reference');observations.append(r)
    original=json.loads(inputs[0].read_bytes());negative=[]
    def reject(name,mutate):
        d=copy.deepcopy(original);mutate(d);write(OUT/(name+'.rejected-input.json'),d)
        try:ref.verify(d)
        except (ValueError,KeyError,TypeError):negative.append(name);return
        raise ValueError('Copied tamper accepted '+name)
    reject('clamped-mode',lambda d:d['rows'][5]['packets'][0].__setitem__('mode',0));reject('truncated-tick',lambda d:d['rows'][2]['packets'][0].__setitem__('expectedTick',2**53-1));reject('truncated-body-id',lambda d:d['rows'][2]['packets'][0]['loads'][0].__setitem__('bodyId',2**53-1));reject('lost-negative-zero',lambda d:d['rows'][2]['packets'][0]['loads'][0]['forceBits'].__setitem__(1,0));reject('short-vector',lambda d:d['rows'][2]['packets'][0]['loads'][0]['forceBits'].pop());reject('load-order',lambda d:d['rows'][3]['packets'][0]['loads'].reverse());reject('packet-order',lambda d:d['rows'][3]['packets'].reverse());reject('invented-diagnostic',lambda d:d['rows'][2].__setitem__('packet',0));reject('wrong-nonfinite-component',lambda d:d['rows'][-1].__setitem__('component',0));reject('missing-success-data',lambda d:d['rows'][2].__setitem__('packets',None));reject('bool-status',lambda d:d['rows'][0].__setitem__('status',False));reject('bool-input-word',lambda d:d['rows'][0]['words'].__setitem__(0,False));reject('both-input-output',lambda d:(d['rows'][2]['floatBits'].__setitem__(0,0),d['rows'][2]['packets'][0]['loads'][0]['forceBits'].__setitem__(0,0)));reject('missing-case',lambda d:d['rows'].pop());reject('unknown-field',lambda d:d.__setitem__('hidden',0));reject('lost-round-mode',lambda d:d['rows'][8].__setitem__('actualEnvironment','nearest'))
    renamed=copy.deepcopy(original)
    for i,r in enumerate(renamed['rows']):r['name']='renamed-independent-'+str(i)
    renamed['rows'].reverse();need(ref.verify(renamed)['status']=='PASS','Labels/order independent reference');write(OUT/'renamed-reversed.accepted-input.json',renamed)
    argv=[sys.executable,'-O',str(path),str(inputs[0])];p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30);(OUT/'optimized.stdout.txt').write_bytes(p.stdout);(OUT/'optimized.stderr.txt').write_bytes(p.stderr);write(OUT/'optimized.command.json',dict(argv=argv,exitCode=p.returncode));need(p.returncode!=0 and b'normal Python' in p.stderr,'Actual optimized Python refusal')
    after=[stamp(p) for p in paths];need(before==after,'Reference/producer/original captures stable');write(OUT/'after.json',after);write(OUT/'verification.json',dict(status='PASS',actualReferences=observations,copiedRejections=negative,actualOptimizedPythonRefused=True,namesAndInputOrderIndependent=True,sourceStable=True,producerRawExact=inputs[0].read_bytes()==inputs[1].read_bytes(),scope='Independent Native packet-data reference only; no GNU/main/C ABI/pump or allocator acceptance.'));print(json.dumps(dict(status='PASS',copiedRejections=len(negative),mappedFloatBitValues=492)))
if __name__=='__main__':main()
