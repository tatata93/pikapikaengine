"""Build the unchanged Web bundle and prepare exact receipt paths; never stage.

Usage: python reports/accelerated-plane-box-coverage-recipes/publish-public.py
       FULL_FEATURE FRESH_OUTPUT_DIRECTORY
"""
from hashlib import sha256
from pathlib import Path,PurePosixPath
import json,re,subprocess,sys,time

if not __debug__:raise SystemExit('Run without Python -O')
ROOT=Path(__file__).resolve().parents[2]
PREFIX='accelerated-plane-box-coverage'
CHECKS=ROOT/f'reports/{PREFIX}-checks'
FEATURE='4b5bf37e5f501088647d735dd45a86ed27d30e5b'
DOCS={'docs/PLAN.md','docs/RESEARCH.md','docs/ACCELERATED_PLANE_BOX_COVERAGE_PLAN.md',
      'reports/2026-11-04-accelerated-plane-box-coverage.md',
      'reports/2026-11-04-accelerated-plane-box-coverage-ci-fix.md'}
IMMUTABLE={'docs/ACCELERATED_PLANE_BOX_COVERAGE.md','docs/learn/index.html',
           'docs/learn/diagrams/accelerated-plane-box-coverage.svg'}


def need(ok,message):
    if not ok:raise AssertionError(message)


def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}


def relative(path):
    p=Path(path);p=(p if p.is_absolute() else ROOT/p).resolve()
    need(p.is_relative_to(ROOT),'repository-owned path')
    return p.relative_to(ROOT).as_posix()


def raw(path):return (ROOT/relative(path)).read_bytes()


def read(path):return json.loads(raw(path).decode('utf-8-sig'))


def git(*args,input=None):return subprocess.check_output(['git',*args],cwd=ROOT,input=input)


def blobs(commit,paths):
    paths=sorted(set(paths));need(len(paths)<=2048,'bounded Git blob list')
    for path in paths:
        p=PurePosixPath(path);need(not p.is_absolute() and '..' not in p.parts and '\n' not in path,'literal Git path')
    stream=git('cat-file','--batch',input=''.join(commit+':'+p+'\n' for p in paths).encode())
    result={};offset=0
    for path in paths:
        end=stream.index(b'\n',offset);header=stream[offset:end].split();need(len(header)==3 and header[1]==b'blob','existing feature blob '+path)
        size=int(header[2]);offset=end+1;result[path]=stream[offset:offset+size];offset+=size
        need(stream[offset:offset+1]==b'\n','Git blob terminator');offset+=1
    need(offset==len(stream),'complete Git blob stream');return result


def normalized_html(value):
    return re.sub(rb'<script type="importmap" id="engine-imports">.*?</script>\s*',b'',
                  re.sub(rb'\?build=[a-f0-9]{16}',b'',value),flags=re.S).replace(b'\r\n',b'\n')


def match_feature(path,value):
    current=raw(path)
    if current==value:return None
    need(current.replace(b'\r\n',b'\n')==value,'raw first, then declared CRLF-only feature comparison: '+path)
    return 'CRLF-to-LF text only, after exact raw comparison'


def main():
    need(len(sys.argv)==3 and sys.argv[1]==FEATURE,'exact fixed-feature CLI')
    need(git('rev-parse','HEAD').decode().strip()==FEATURE,'receipt based on exact current feature')
    output=(ROOT/sys.argv[2]).resolve()
    need(output.is_relative_to(CHECKS.resolve()) and not output.exists(),'fresh bounded publication directory')
    output.mkdir(parents=True)
    index_before=info(git('ls-files','--stage','-z'))
    acceptance_path=f'reports/{PREFIX}-checks/run-20261104-public-summary-001/acceptance.json'
    receipt_path=f'reports/{PREFIX}-public-verification.json'
    acceptance=read(acceptance_path);base=read(f'reports/{PREFIX}-baseline.json');local=read(f'reports/{PREFIX}-local-verification.json')
    need(acceptance['status']=='PASS' and acceptance['commit']==FEATURE,'actual final public acceptance')
    need(raw(receipt_path)==raw(acceptance_path),'byte-exact public receipt copy')
    need(local['status']=='PASS' and info(raw(acceptance['localVerification']['path']))=={k:acceptance['localVerification'][k] for k in ['bytes','sha256']},'original local receipt')
    need(len(base['protected'])==369 and len(base['generatedEntries'])==26,'protected baseline capacities')
    need(acceptance['publicFiles']==100 and acceptance['publicChannels']=={'pages':99,'githubSource':1},'actual two-channel hundred resources')
    need(acceptance['publicCiScope']['engineSteps']==24 and acceptance['publicCiScope']['pagesJobs']==3,'final full CI and Pages')
    need(acceptance['warnings']=={'current':48,'prior':48,'sameMultiset':True,'new':0},'unchanged GNU diagnostics')
    evidence={}
    for path,stamp in acceptance['evidence'].items():
        need(info(raw(path))==stamp,'accepted evidence remains exact: '+path);evidence[path]=stamp
    # The original local test hash remains historical; its exact one-file fix
    # and targeted receipt were independently accepted, never rewritten.
    fix=acceptance['postfixTestVerification'];need(info(raw(fix['path']))=={k:fix[k] for k in ['bytes','sha256']},'postfix receipt')
    need(fix['record']['fixtureByteIdenticalToOriginalStandalone'] and fix['record']['groups']==74,'targeted test-only fix')
    feature_paths=set(acceptance['sourceComparisons'])|set(acceptance['permittedOldChanges'])|IMMUTABLE
    feature_blobs=blobs(FEATURE,feature_paths)
    conversions={p:match_feature(p,value) for p,value in feature_blobs.items()}
    for path,stamp in base['protected'].items():need(info(raw(path))==stamp,'raw protected source '+path)
    generated=base['generatedEntries'];old_blobs=blobs(base['baseCommit'],generated)
    for path in generated:need(normalized_html(raw(path))==normalized_html(old_blobs[path]),'old generated HTML body '+path)
    stable=set(base['protected'])|set(generated)|feature_paths|DOCS|{relative(__file__)}
    before={p:info(raw(p)) for p in sorted(stable)}
    started=time.monotonic();command=['node','scripts/build-web.mjs']
    result=subprocess.run(command,cwd=ROOT,capture_output=True,timeout=180)
    (output/'web-build.stdout.txt').write_bytes(result.stdout);(output/'web-build.stderr.txt').write_bytes(result.stderr)
    after={p:info(raw(p)) for p in sorted(stable)}
    record={'command':command,'exit':result.returncode,'elapsedSeconds':time.monotonic()-started,
            'sourceBefore':before,'sourceAfter':after,'sourceStable':before==after,
            'stdout':relative(output/'web-build.stdout.txt'),'stdoutHash':info(result.stdout),
            'stderr':relative(output/'web-build.stderr.txt'),'stderrHash':info(result.stderr)}
    (output/'commands.json').write_text(json.dumps([record],indent=2)+'\n',encoding='utf-8')
    need(result.returncode==0 and re.fullmatch(rb'Web build cd45c7f1ac2ba5e5: 54 versioned modules; generated import maps\s*',result.stdout),'unchanged Web build')
    need(before==after,'all preserved sources, generated entries, receipt docs stable during build')
    for path,stamp in base['protected'].items():need(info(raw(path))==stamp,'post-build raw protected source '+path)
    for path in generated:need(normalized_html(raw(path))==normalized_html(old_blobs[path]),'post-build HTML body '+path)
    # Only changed tracked receipt prose and exact new plane evidence/recipes.
    changed={p.decode() for p in git('diff','--name-only','HEAD','-z').split(b'\0') if p}
    need(changed<=DOCS,'unexpected tracked change outside five receipt docs: '+repr(changed-DOCS))
    untracked={p.decode() for p in git('ls-files','--others','--exclude-standard','-z').split(b'\0') if p}
    selected=set(changed)
    for path in untracked:
        if not path.startswith('reports/'+PREFIX):continue
        parts=PurePosixPath(path).parts
        if 'obj' in parts or Path(path).suffix.lower() not in {'.py','.json','.txt','.jpg','.md'}:continue
        selected.add(path)
    expected_dirs=[f'reports/{PREFIX}-checks/run-20261104-public-status-00{i}' for i in range(1,5)]+[
        f'reports/{PREFIX}-checks/run-20261104-public-bytes-00{i}' for i in range(1,3)]+[
        f'reports/{PREFIX}-checks/run-20261104-public-summary-001',f'reports/{PREFIX}-public-browser',
        f'reports/{PREFIX}-public-browser-development/run-001',f'reports/{PREFIX}-public-browser-development/run-003']
    for directory in expected_dirs:
        files=[p for p in (ROOT/directory).rglob('*') if p.is_file()]
        need(files,'required actual receipt history '+directory)
        for path in files:
            need(path.suffix.lower() in {'.json','.txt','.jpg','.py'},'bounded evidence file type')
            key=relative(path)
            if key in untracked:selected.add(key)
            evidence[key]=info(path.read_bytes())
    for name in ['public-ci-evidence.json','public-runs.json','public-bytes.json','engine-jobs.json','pages-jobs.json','job-126605836056-full.txt']:
        path=f'reports/{PREFIX}-'+name;need((ROOT/path).is_file(),'final public raw record '+name);evidence[path]=info(raw(path))
        if path in untracked:selected.add(path)
    need(receipt_path in selected,'new byte-exact receipt included')
    need(not any('sphere-box' in p or 'WORLD_STATIC_MESH' in p or 'world_static_mesh' in p for p in selected),'future work excluded')
    # Output files are deliberately listed, with no self-referential hash.
    future=[relative(output/name) for name in ['publication-manifest.json','stage-paths.nul']]
    stage=sorted(selected|set(future));need(len(stage)<=1024,'bounded exact stage manifest')
    need(not any(Path(p).suffix.lower() in {'.exe','.obj','.o','.pdb','.lib','.a'} or 'obj' in PurePosixPath(p).parts for p in stage),'no compiled outputs')
    nul=b'\0'.join(p.encode() for p in stage)+b'\0';(output/'stage-paths.nul').write_bytes(nul)
    need(info(git('ls-files','--stage','-z'))==index_before,'Git index unchanged')
    manifest={'schema':1,'status':'PASS','feature':FEATURE,'publicReceipt':{'path':receipt_path,**info(raw(receipt_path))},
              'stagePathCount':len(stage),'stagePaths':stage,'stagePathsNul':{'path':relative(output/'stage-paths.nul'),**info(nul)},
              'files':{p:info(raw(p)) for p in stage if p not in future},'protectedRaw':369,'generatedBodies':26,
              'featureComparisons':conversions,'webBuild':'cd45c7f1ac2ba5e5','command':record,
              'indexBefore':index_before,'indexAfter':info(git('ls-files','--stage','-z')),'indexChanged':False,
              'evidence':evidence,'scope':'Receipt-only publication preparation. No stage/commit/push, feature integration, Native numerical rerun or future Sphere/World work included.'}
    (output/'publication-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','stagePathCount':len(stage),'manifest':relative(output/'publication-manifest.json'),'stagePathsNul':relative(output/'stage-paths.nul'),'indexChanged':False}))


if __name__=='__main__':main()
