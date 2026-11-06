"""Actual archive reader7 byte bounds and valid large manifest archives; fixed16MiB only."""
from pathlib import Path
import hashlib,importlib.util,io,json,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/pages-deployment/run-20261106-archive-manifest-bound-001'
BUILD=ROOT/'build/pages-archive-manifest-bound-001'
spec=importlib.util.spec_from_file_location('archive_gate',Path(__file__).with_name('verify-archive.py'));ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
def need(v,m):
    if not v:raise ValueError(m)
class VirtualFile:
    def __init__(self,total):self.total=total;self.calls=[]
    def is_symlink(self):return False
    def is_file(self):return True
    def open(self,mode):need(mode=='rb','Binary read only');return self
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,size=-1):
        need(size==16*1024*1024+1,'Fixed limit+1 read');self.calls.append(size);return b'x'*min(size,self.total)
def main():
    need(__debug__ and not OUT.exists() and not BUILD.exists(),'Fresh bounded check');OUT.mkdir(parents=True);BUILD.mkdir(parents=True)
    source=Path(__file__).with_name('verify-archive.py');raw=source.read_bytes();need(ref.MANIFEST_BYTES_LIMIT==16*1024*1024 and ref.FILE_BYTES_LIMIT==384*1024*1024,'Fixed limits')
    prior=subprocess.check_output(['git','show','215d799d8f63899bb08ee6fa4deb7f3ae9f368cb:reports/pages-deployment/verify-archive.py'],cwd=ROOT)
    need(raw.replace(b'MANIFEST_BYTES_LIMIT = 16 * 1024 * 1024',b'MANIFEST_BYTES_LIMIT = 8 * 1024 * 1024')==prior,'Only constant changed; all archive safety checks source-exact')
    bounds=[]
    for total in [0,8*1024*1024,8*1024*1024+1,16*1024*1024-1,16*1024*1024,16*1024*1024+1,2**60]:
        stream=VirtualFile(total);refused=False
        try:result=ref.read_manifest(stream);need(len(result)==total,'Full accepted length')
        except ValueError as e:need(str(e)=='Bounded manifest read','Specific bound refusal');refused=True
        need(refused==(total>ref.MANIFEST_BYTES_LIMIT) and stream.calls==[ref.MANIFEST_BYTES_LIMIT+1],'Actual bounded read')
        bounds.append(dict(virtualBytes=total,readSizes=stream.calls,refused=refused))
    actual=[];payload=b'x'
    manifest=dict(schema=1,kind='pikapika-pages-bundle',status='PASS',budgetBytes=ref.FILE_BYTES_LIMIT,selectedFiles=1,selectedBytes=1,files=[dict(path='data.txt',bytes=1,sha256=hashlib.sha256(payload).hexdigest())])
    base=(json.dumps(manifest)+'\n').encode()
    for size in [8*1024*1024+1,16*1024*1024]:
        body=base+b' '*(size-len(base));path=BUILD/('manifest-'+str(size)+'.json');path.write_bytes(body);tar=BUILD/('archive-'+str(size)+'.tar')
        with tarfile.open(tar,'w',format=tarfile.USTAR_FORMAT) as archive:
            for name,data in [('data.txt',payload),('pages-manifest.json',body)]:
                item=tarfile.TarInfo(name);item.size=len(data);archive.addfile(item,io.BytesIO(data))
        r=ref.verify(tar,path);need(r['status']=='PASS' and r['manifest']['bytes']==size and r['selectedFiles']==1,'Actual full large manifest archive');actual.append(r)
    too_large=base+b' '*(ref.MANIFEST_BYTES_LIMIT+1-len(base));refused=False
    try:ref.manifest(too_large)
    except ValueError as e:need(str(e)=='Bounded manifest bytes','Full parser byte bound');refused=True
    need(refused and source.read_bytes()==raw,'Overflow rejected before JSON; source stable')
    (OUT/'checker-tested.py.txt').write_bytes(raw)
    result=dict(status='FINITE_ARCHIVE_MANIFEST_BOUND_PASS',manifestLimitBytes=ref.MANIFEST_BYTES_LIMIT,bundleBudgetBytes=ref.FILE_BYTES_LIMIT,virtualBounds=bounds,acceptedByteBounds=5,overflowByteBounds=2,actualValidLargeArchives=actual,oversizeParserRefused=True,allOtherCheckerSourceExact=True,scope='Actual local tar/JSON byte checks and virtual reader bounds. Not an official action archive or actual HTTP deployment; huge virtual length not allocated in full.')
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({k:result[k] for k in ['status','manifestLimitBytes','acceptedByteBounds','overflowByteBounds']}))
if __name__=='__main__':main()
