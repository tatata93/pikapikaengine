"""Build the unchanged Web bundle and prepare exact receipt paths; never stage.

Usage: python reports/accelerated-sphere-box-coverage-recipes/publish-public.py
       FULL_FEATURE FRESH_OUTPUT_DIRECTORY [--acceptance SUMMARY_ACCEPTANCE_JSON]
"""
from hashlib import sha256
from pathlib import Path,PurePosixPath
import difflib,json,re,subprocess,sys,time

if not __debug__:raise SystemExit('Run without Python -O')
ROOT=Path(__file__).resolve().parents[2]
PREFIX='accelerated-sphere-box-coverage'
CHECKS=ROOT/f'reports/{PREFIX}-checks'
FEATURE='63f5d3d7b841633980eac2006717f30614ee9e1f'
DOCS={'docs/PLAN.md','docs/RESEARCH.md','docs/ACCELERATED_SPHERE_BOX_COVERAGE_PLAN.md',
      'reports/2026-11-04-accelerated-sphere-box-coverage.md'}
IMMUTABLE={'docs/ACCELERATED_SPHERE_BOX_COVERAGE.md','docs/learn/index.html',
           'docs/learn/diagrams/accelerated-sphere-box-coverage.svg'}


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
    need(len(sys.argv) in (3,5) and sys.argv[1]==FEATURE,'exact fixed-feature CLI')
    if len(sys.argv)==5:need(sys.argv[3]=='--acceptance','explicit alternate acceptance flag')
    need(git('rev-parse','HEAD').decode().strip()==FEATURE,'receipt based on exact current feature')
    output=(ROOT/sys.argv[2]).resolve()
    need(output.is_relative_to(CHECKS.resolve()) and not output.exists(),'fresh bounded publication directory')
    output.mkdir(parents=True)
    index_before=info(git('ls-files','--stage','-z'))
    acceptance_path=sys.argv[4] if len(sys.argv)==5 else f'reports/{PREFIX}-checks/run-20261104-public-summary-001/acceptance.json'
    accepted_path=(ROOT/acceptance_path).resolve()
    need(accepted_path.is_relative_to(CHECKS.resolve()) and accepted_path.name=='acceptance.json' and 'public-summary-' in accepted_path.parent.name,'bounded explicit public aggregate')
    receipt_path=f'reports/{PREFIX}-public-verification.json'
    acceptance=read(acceptance_path);base=read(f'reports/{PREFIX}-baseline.json');local=read(f'reports/{PREFIX}-local-verification.json')
    need(acceptance['status']=='PASS' and acceptance['commit']==FEATURE,'actual final public acceptance')
    if (ROOT/receipt_path).exists():need(raw(receipt_path)==raw(acceptance_path),'existing receipt stays exact')
    else:(ROOT/receipt_path).write_bytes(raw(acceptance_path))
    need(raw(receipt_path)==raw(acceptance_path),'byte-exact public receipt copy')
    need(local['status']=='PASS' and info(raw(acceptance['localVerification']['path']))=={k:acceptance['localVerification'][k] for k in ['bytes','sha256']},'original local receipt')
    need(len(base['protected'])==376 and len(base['generatedEntries'])==26,'protected baseline capacities')
    need(acceptance['publicFiles']==113 and acceptance['publicChannels']=={'pages':112,'githubSource':1},'actual two-channel113 resources')
    need(acceptance['publicCiScope']['engineSteps']==25 and acceptance['publicCiScope']['pagesJobs']==3,'final full CI and Pages')
    need(acceptance['warnings']=={'current':48,'prior':48,'sameMultiset':True,'new':0},'unchanged GNU diagnostics')
    evidence={}
    for path,stamp in acceptance['evidence'].items():
        need(info(raw(path))==stamp,'accepted evidence remains exact: '+path);evidence[path]=stamp
    # Production/oracle7 and the other helpers remain exact; only the accepted
    # read-only public collector's two stale footer counts may differ.
    public_recipe=f'reports/{PREFIX}-recipes/public.py'
    fix=acceptance['collectionDriverCorrection'];correction=read(fix['path'])
    need(correction==fix['record'] and correction['feature']==FEATURE and correction['source']==public_recipe,'accepted collection-only correction')
    feature_paths=set(acceptance['sourceComparisons'])|set(acceptance['permittedOldChanges'])|IMMUTABLE
    feature_blobs=blobs(FEATURE,feature_paths)
    original=raw(fix['original']['path']);need(info(original)=={k:fix['original'][k] for k in ['bytes','sha256']} and original==feature_blobs[public_recipe],'archived exact original collector')
    pairs=[("'channels': {'pages': 99, 'githubSource': 1}","'channels': {'pages': 112, 'githubSource': 1}"),
           ("sum(row['distribution'] == 'pages' for row in files) == 99","sum(row['distribution'] == 'pages' for row in files) == 112")]
    need(correction['literalReplacements']==[list(pair) for pair in pairs],'only two authorized literal replacements')
    current=original
    for old,new in pairs:
        need(current.count(old.encode())==1,'one original footer literal');current=current.replace(old.encode(),new.encode(),1)
    need(current==raw(public_recipe) and info(current)==correction['new'],'current collector exact corrected bytes')
    patch=''.join(difflib.unified_diff(original.decode().splitlines(True),current.decode().splitlines(True),fromfile='a/'+public_recipe,tofile='b/'+public_recipe)).encode()
    need(patch==raw(fix['patch']['path']) and info(patch)=={k:fix['patch'][k] for k in ['bytes','sha256']},'exact two-line collector patch')
    conversions={p:match_feature(p,value) for p,value in feature_blobs.items() if p!=public_recipe}
    conversions[public_recipe]='Accepted two-literal read-only collection footer correction; no production/math/CI changes.'
    need(local['newSources']==base['newSources'] and len(local['newSources'])==7,'frozen seven source map')
    for path,stamp in local['newSources'].items():need(info(raw(path))==stamp and raw(path)==feature_blobs[path],'all seven source bytes unchanged: '+path)
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
    # Only changed tracked receipt prose and exact new Sphere evidence/recipes.
    changed={p.decode() for p in git('diff','--name-only','HEAD','-z').split(b'\0') if p}
    need(changed<=DOCS|{public_recipe},'unexpected tracked change outside four receipt docs/accepted collector fix: '+repr(changed-DOCS-{public_recipe}))
    untracked={p.decode() for p in git('ls-files','--others','--exclude-standard','-z').split(b'\0') if p}
    selected=set(changed)
    for path in untracked:
        if not path.startswith('reports/'+PREFIX):continue
        parts=PurePosixPath(path).parts
        if 'obj' in parts or Path(path).suffix.lower() not in {'.py','.json','.txt','.jpg','.md'}:continue
        selected.add(path)
    expected_dirs=[f'reports/{PREFIX}-checks/run-20261104-public-bytes-00{i}' for i in range(1,3)]+[
        relative(path) for path in sorted(CHECKS.iterdir()) if path.is_dir() and (
            path.name.startswith('run-20261104-public-status-') or path.name.startswith('run-20261104-public-summary-'))]+[
        f'reports/{PREFIX}-public-browser',f'reports/{PREFIX}-public-browser-development/run-001',
        f'reports/{PREFIX}-public-collection-development/run-001']
    for directory in expected_dirs:
        files=[p for p in (ROOT/directory).rglob('*') if p.is_file()]
        need(files,'required actual receipt history '+directory)
        for path in files:
            need(path.suffix.lower() in {'.json','.txt','.jpg','.py'},'bounded evidence file type')
            key=relative(path)
            if key in untracked:selected.add(key)
            evidence[key]=info(path.read_bytes())
    engine=next(job for job in acceptance['jobs'] if job['name']=='portable-core')
    for name in ['public-ci-evidence.json','public-runs.json','public-bytes.json','engine-jobs.json','pages-jobs.json','job-'+str(engine['id'])+'-full.txt']:
        path=f'reports/{PREFIX}-'+name;need((ROOT/path).is_file(),'final public raw record '+name);evidence[path]=info(raw(path))
        if path in untracked:selected.add(path)
    need(receipt_path in selected and public_recipe in selected,'receipt and accepted collection fix included')
    need(not any('WORLD_STATIC_MESH' in p or 'world_static_mesh' in p or 'world-static-mesh' in p or 'before-corebinding' in p for p in selected),'future work excluded')
    # Output files are deliberately listed, with no self-referential hash.
    future=[relative(output/name) for name in ['publication-manifest.json','stage-paths.nul']]
    stage=sorted(selected|set(future));need(len(stage)<=1024,'bounded exact stage manifest')
    need(not any(Path(p).suffix.lower() in {'.exe','.obj','.o','.pdb','.lib','.a'} or 'obj' in PurePosixPath(p).parts for p in stage),'no compiled outputs')
    nul=b'\0'.join(p.encode() for p in stage)+b'\0';(output/'stage-paths.nul').write_bytes(nul)
    need(info(git('ls-files','--stage','-z'))==index_before,'Git index unchanged')
    manifest={'schema':1,'status':'PASS','feature':FEATURE,'publicReceipt':{'path':receipt_path,**info(raw(receipt_path))},
              'stagePathCount':len(stage),'stagePaths':stage,'stagePathsNul':{'path':relative(output/'stage-paths.nul'),**info(nul)},
              'files':{p:info(raw(p)) for p in stage if p not in future},'protectedRaw':376,'generatedBodies':26,
              'collectionDriverCorrection':fix,'featureComparisons':conversions,'webBuild':'cd45c7f1ac2ba5e5','command':record,
              'indexBefore':index_before,'indexAfter':info(git('ls-files','--stage','-z')),'indexChanged':False,
              'evidence':evidence,'scope':'Receipt-only publication preparation. No stage/commit/push, feature integration, Native numerical rerun or future World work included.'}
    (output/'publication-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'PASS','stagePathCount':len(stage),'manifest':relative(output/'publication-manifest.json'),'stagePathsNul':relative(output/'stage-paths.nul'),'indexChanged':False}))


if __name__=='__main__':main()
