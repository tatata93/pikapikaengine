"""Finite lesson/doc acceptance after actual wire GNU success."""
from pathlib import Path
import hashlib,json,re,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/world-static-mesh-session-integration/run-20261105-wire-gnu-actual-001'
def stamp(p):
    b=p.read_bytes();return dict(path=p.relative_to(ROOT).as_posix(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
    if OUT.exists():raise ValueError('Fresh output required')
    OUT.mkdir()
    protected=[*sorted((ROOT/'samples').rglob('*')),*sorted((ROOT/'engine').rglob('*')),*sorted((ROOT/'core').rglob('*')),ROOT/'.github/workflows/verify.yml']
    protected=[p for p in protected if p.is_file()];before=[stamp(p) for p in protected]
    old=subprocess.run(['git','show','77a363b38fd1af72a6452af33537b21657668c3f:docs/learn/index.html'],cwd=ROOT,capture_output=True,check=True).stdout.decode('utf8')
    current=(ROOT/'docs/learn/index.html').read_text(encoding='utf8');parts=lambda s:re.findall(r'<article\b.*?</article>',s,re.S)
    assert len(parts(old))==len(parts(current))==26 and parts(old)[:25]==parts(current)[:25]
    commands=[]
    for name,argv in [('learn',['node','--test','docs/learn/learn.test.mjs']),('syntax',['node','scripts/check.mjs']),('build',['node','scripts/build-web.mjs'])]:
        start=time.monotonic();p=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=90)
        (OUT/(name+'.stdout.txt')).write_bytes(p.stdout);(OUT/(name+'.stderr.txt')).write_bytes(p.stderr)
        r=dict(name=name,argv=argv,exitCode=p.returncode,seconds=time.monotonic()-start);commands.append(r)
        (OUT/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
        if p.returncode:raise ValueError('Actual command '+name)
    assert before==[stamp(p) for p in protected]
    result=dict(status='PASS',protectedPaths=len(protected),protectedStable=True,old25ArticlesExact=True,commands=commands)
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
