"""Original tiny tar controls for the actual Pages upload archive gate."""
import argparse
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT/'reports/pages-deployment/verify-archive.py'
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('pages_archive_reference', CHECKER)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


def need(condition, message):
    if not condition:
        raise AssertionError(message)


def stamp(path):
    raw=path.read_bytes()
    return {'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def dump(path, value):
    with path.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def make_manifest(files):
    return {'schema':1,'kind':'pikapika-pages-bundle','status':'PASS','budgetBytes':ref.FILE_BYTES_LIMIT,
            'selectedFiles':len(files),'selectedBytes':sum(len(v) for v in files.values()),
            'files':[{'path':k,'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in files.items()]}


def encode(value):
    return (json.dumps(value,ensure_ascii=True,indent=2)+'\n').encode()


def regular(name, raw):
    value=tarfile.TarInfo(name);value.size=len(raw)
    return value,raw


def directory(name):
    value=tarfile.TarInfo(name);value.type=tarfile.DIRTYPE
    return value,b''


def write_tar(path, members, mode='w', format=tarfile.GNU_FORMAT):
    with tarfile.open(path,mode=mode,format=format) as archive:
        for item,raw in members:
            archive.addfile(item,io.BytesIO(raw))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/('build/pages-archive-tests-'+uuid.uuid4().hex[:12]))
    args=parser.parse_args();out=args.output.resolve()
    need(out.is_relative_to(ROOT) and out!=ROOT,'New workspace test output only')
    out.mkdir(parents=True,exist_ok=False)
    watched=[CHECKER,Path(__file__).resolve()];before=[stamp(p) for p in watched]
    dump(out/'source-before.json',before)
    started=time.perf_counter();passed=[];rejected=[];commands=[]
    files={'.gitattributes':b'original hidden bytes\n','index.html':b'<p>original</p>\n',
           'dir/.hidden':b'kept\x00bytes','dir/data.txt':b'xyz'}
    value=make_manifest(files);raw=encode(value);manifest_path=out/'pages-manifest.json';manifest_path.write_bytes(raw)
    def members():
        return [directory('./'),directory('./dir/')]+[regular('./'+k,v) for k,v in files.items()]+[regular('./pages-manifest.json',raw)]
    def positive(name, entries, metadata=manifest_path):
        path=out/(name+'.tar');write_tar(path,entries)
        result=ref.verify(path,metadata);need(result['status']=='PASS',name)
        passed.append({'name':name,'result':result});return path
    def negative(name, entries=None, metadata=manifest_path, physical=None):
        path=out/(name+'.tar')
        if physical is not None:path.write_bytes(physical)
        else:write_tar(path,members() if entries is None else entries)
        try:ref.verify(path,metadata)
        except (ValueError,tarfile.TarError,UnicodeError,EOFError,OSError) as error:
            rejected.append({'name':name,'reason':str(error),'archive':stamp(path),'manifest':stamp(metadata)})
        else:raise AssertionError('Altered archive accepted: '+name)
    try:
        good=positive('complete-hidden-files',members())
        need(passed[-1]['result']['hiddenSelectedFiles']==2,'Both original hidden files retained')
        positive('directories-optional',members()[2:])
        plain=[]
        for item,body in members()[2:]:
            item=copy.deepcopy(item);item.name=item.name.removeprefix('./');plain.append((item,body))
        positive('plain-relative-names',plain)
        # Use genuine GNU longname and PAX format metadata. These are format
        # records, not extra logical files or extraction links.
        long_files={'long/'+('a'*120)+'.txt':b'long name bytes'}
        long_raw=encode(make_manifest(long_files));long_manifest=out/'long-manifest.json';long_manifest.write_bytes(long_raw)
        long_entries=[regular(k,v) for k,v in long_files.items()]+[regular('pages-manifest.json',long_raw)]
        positive('gnu-longname',long_entries,long_manifest)
        pax=out/'pax-longname.tar';write_tar(pax,long_entries,format=tarfile.PAX_FORMAT)
        passed.append({'name':'pax-longname','result':ref.verify(pax,long_manifest)})

        # v4's broad hidden-file exclusion removes declared .gitattributes and
        # dir/.hidden. The tar itself is valid; exact set equality must fail.
        negative('v4-equivalent-hidden-omission',[x for x in members() if x[0].name not in ('./.gitattributes','./dir/.hidden')])
        negative('one-selected-file-missing',[x for x in members() if x[0].name!='./index.html'])
        negative('all-selected-files-missing',[regular('pages-manifest.json',raw)])
        negative('manifest-self-missing',members()[:-1])
        changed=members();changed[2]=regular('./.gitattributes',b'X'*len(files['.gitattributes']))
        negative('file-byte-tamper',changed)
        changed=members();changed[2]=regular('./.gitattributes',b'wrong size')
        negative('file-size-tamper',changed)
        changed=members();changed[-1]=regular('pages-manifest.json',raw.replace(b'PASS',b'FAIL'))
        negative('manifest-raw-tamper',changed)
        negative('unexpected-file',members()+[regular('extra.bin',b'extra')])
        negative('unexpected-directory',members()+[directory('empty-unselected/')])
        negative('duplicate-file',members()+[regular('index.html',files['index.html'])])
        negative('duplicate-directory',members()+[directory('dir/')])
        for i,name in enumerate(('../escape','/absolute','C:/escape','dir\\escape','a//b','a/./b','./../b','././index.html','bad\nname')):
            negative('unsafe-member-'+str(i),members()+[regular(name,b'not allowed')])
        negative('root-alias-directory',members()+[directory('.//')])
        for name,kind in [('symlink',tarfile.SYMTYPE),('hardlink',tarfile.LNKTYPE),('fifo',tarfile.FIFOTYPE),
                          ('character-device',tarfile.CHRTYPE),('block-device',tarfile.BLKTYPE),('contiguous-file',tarfile.CONTTYPE)]:
            item=tarfile.TarInfo('forbidden');item.type=kind
            if kind in (tarfile.SYMTYPE,tarfile.LNKTYPE):item.linkname='index.html'
            negative('nonregular-'+name,members()+[(item,b'')])
        item=tarfile.TarInfo('dir/');item.type=tarfile.DIRTYPE;item.size=1
        altered=members();altered[1]=(item,b'x')
        negative('directory-payload',altered)
        ordinary=tarfile.TarInfo('extra');ordinary.linkname='index.html'
        negative('regular-with-linkname',members()+[(ordinary,b'')])
        sparse=tarfile.TarInfo('sparse');sparse.type=tarfile.GNUTYPE_SPARSE
        negative('gnu-sparse-member',members()+[(sparse,b'')])
        metadata=tarfile.TarInfo('format-metadata');metadata.type=tarfile.GNUTYPE_LONGNAME;metadata.size=ref.CHUNK+1
        negative('bounded-internal-gnu-longname-read',[(metadata,b'a'*(ref.CHUNK+1))]+members())
        pax_sparse=tarfile.TarInfo('pax-metadata');pax_sparse.type=tarfile.XHDTYPE
        pax_data=b'22 GNU.sparse.major=1\n';pax_sparse.size=len(pax_data)
        negative('pax-sparse-member',[(pax_sparse,pax_data)]+members())
        compressed=out/'gzip.tar';write_tar(compressed,members(),mode='w:gz')
        negative('compressed-not-official-uncompressed',physical=compressed.read_bytes())
        negative('malformed-header',physical=b'not a tar'+bytes(10240-9))
        negative('misaligned-archive',physical=good.read_bytes()+b'x')
        negative('nonzero-trailer',physical=good.read_bytes()+b'x'+bytes(511))
        negative('concatenated-hidden-second-archive',physical=good.read_bytes()+good.read_bytes())
        with tarfile.open(good,'r:') as archive:
            archive.getmembers();end=archive.offset
        negative('one-end-block-only',physical=good.read_bytes()[:end+512])
        damaged=bytearray(good.read_bytes())
        with tarfile.open(good,'r:') as archive:
            item=next(x for x in archive if x.name=='./index.html')
            damaged[item.offset_data+item.size]=1
        negative('nonzero-payload-padding',physical=bytes(damaged))

        def bad_manifest(name, mutate):
            altered=copy.deepcopy(value);mutate(altered)
            path=out/(name+'.json');path.write_bytes(encode(altered))
            negative(name,metadata=path)
        bad_manifest('manifest-schema-bool',lambda v:v.update(schema=True))
        bad_manifest('manifest-count-bool',lambda v:v.update(selectedFiles=True))
        bad_manifest('manifest-total-wrong',lambda v:v.update(selectedBytes=0))
        bad_manifest('manifest-sha-malformed',lambda v:v['files'][0].update(sha256='bad'))
        bad_manifest('manifest-duplicate-path',lambda v:v['files'].append(copy.deepcopy(v['files'][0])))
        bad_manifest('manifest-parent-file-conflict',lambda v:v['files'].append({'path':'dir','bytes':0,'sha256':hashlib.sha256(b'').hexdigest()}))
        bad_manifest('manifest-self-selected',lambda v:v['files'][0].update(path='pages-manifest.json'))
        bad_manifest('manifest-path-escape',lambda v:v['files'][0].update(path='../outside'))
        bad_manifest('manifest-size-overflow',lambda v:v['files'][0].update(bytes=ref.FILE_BYTES_LIMIT+1))
        bad_manifest('manifest-budget-overflow',lambda v:v.update(budgetBytes=ref.FILE_BYTES_LIMIT+1))
        bad_manifest('manifest-payload-budget',lambda v:v.update(budgetBytes=1))
        bad_manifest('manifest-files-over-count',lambda v:v.update(files=v['files']*(ref.MAX_FILES//len(v['files'])+1)))
        for name,raw_json in [('duplicate-json-key',b'{"schema":1,"schema":1}'),('nonfinite-json',b'{"x":NaN}')]:
            path=out/(name+'.json');path.write_bytes(raw_json);negative(name,metadata=path)
        huge_manifest=out/'oversized-manifest.json';huge_manifest.write_bytes(b' '*(ref.MANIFEST_BYTES_LIMIT+1))
        negative('bounded-manifest-read',metadata=huge_manifest)
        old=ref.MAX_ENTRIES
        try:
            ref.MAX_ENTRIES=2
            negative('entry-count-reduced-cap-boundary')
        finally:ref.MAX_ENTRIES=old
        old=ref.MAX_ARCHIVE_BYTES
        try:
            ref.MAX_ARCHIVE_BYTES=1024
            negative('physical-size-reduced-cap-boundary')
        finally:ref.MAX_ARCHIVE_BYTES=old
        argv=[sys.executable,'-O',str(CHECKER),str(good),str(manifest_path)]
        run=subprocess.run(argv,capture_output=True,check=False,timeout=30)
        (out/'optimized.stdout.txt').write_bytes(run.stdout);(out/'optimized.stderr.txt').write_bytes(run.stderr)
        commands.append({'argv':argv,'exit':run.returncode,'stdout':stamp(out/'optimized.stdout.txt'),'stderr':stamp(out/'optimized.stderr.txt')})
        need(run.returncode==0 and json.loads(run.stdout)['status']=='PASS','Explicit checks remain effective with -O')
        passed.append({'name':'optimized-python-no-assert-dependency'})
        bad_argv=[sys.executable,'-O',str(CHECKER),str(out/'v4-equivalent-hidden-omission.tar'),str(manifest_path)]
        bad_run=subprocess.run(bad_argv,capture_output=True,check=False,timeout=30)
        (out/'optimized-bad.stdout.txt').write_bytes(bad_run.stdout);(out/'optimized-bad.stderr.txt').write_bytes(bad_run.stderr)
        commands.append({'argv':bad_argv,'exit':bad_run.returncode,'stdout':stamp(out/'optimized-bad.stdout.txt'),'stderr':stamp(out/'optimized-bad.stderr.txt')})
        need(bad_run.returncode!=0 and b'Missing selected files' in bad_run.stderr,
             'Actual optimized CLI must reject v4-equivalent hidden omission with missing-file diagnosis')
        rejected.append({'name':'optimized-cli-hidden-omission-rejected','reason':'Actual -O subprocess nonzero and missing-selected-files diagnostic',
                         'archive':stamp(out/'v4-equivalent-hidden-omission.tar'),'manifest':stamp(manifest_path)})
        dump(out/'result.json',{'schema':1,'status':'PASS','positiveTests':len(passed),'negativeTests':len(rejected),
             'positives':passed,'rejectedControls':rejected,'commands':commands,
             'scope':'Original tiny physical tar fixtures. Includes mandatory v4-equivalent hidden omission rejection. Reduced-cap entry/physical-size tests exercise explicit production guard branches without allocating maximum archives; other descriptor limits use actual constants. Not an official action run or HTTP proof.'})
    finally:
        after=[stamp(p) for p in watched]
        dump(out/'provenance.json',{'sourceBefore':before,'sourceAfter':after,'sourceStable':before==after,'elapsedSeconds':time.perf_counter()-started})
        need(before==after,'Archive checker and tests unchanged during execution')
    print(json.dumps({'status':'PASS','positiveTests':len(passed),'negativeTests':len(rejected),'output':str(out)}))


if __name__=='__main__':
    main()
