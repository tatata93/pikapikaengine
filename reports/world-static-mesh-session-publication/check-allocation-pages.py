"""Read four selected public owner documents and compare raw bytes to fixed Git."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
SHA='bbfd9a9c5f3a745003f12c02becdfb6e5fc21a69'
OUT=Path(__file__).resolve().parent/'run-20261105-allocation-bytes-001'
PATHS=['docs/learn/index.html','docs/learn/diagrams/world-static-mesh-session.svg',
       'reports/world-static-mesh-session-allocation-verification.json',
       'reports/world-static-mesh-session-full-verification.json']


def main():
    OUT.mkdir(exist_ok=False);(OUT/'recipe.py.txt').write_bytes(Path(__file__).read_bytes())
    manifest=json.loads((ROOT/'reports/pages-deployment/run-20261105-owner-allocation-public-001/pages-manifest.json').read_bytes())
    assert manifest['head']==SHA
    selected={x['path'] for x in manifest['files']};rows=[]
    for i,path in enumerate(PATHS):
        row={'path':path,'selectedByManifest':path in selected,'status':'FAIL'}
        url='https://tatata93.github.io/pikapikaengine/'+path+'?source='+SHA;row['url']=url
        try:
            assert path in selected,'Do not request intentionally excluded raw evidence'
            with urllib.request.urlopen(url,timeout=45) as response:
                raw=response.read();row['httpStatus']=response.status;row['contentType']=response.headers.get('Content-Type')
            (OUT/(str(i)+'.raw')).write_bytes(raw)
            expected=subprocess.check_output(['git','show',SHA+':'+path],cwd=ROOT)
            row.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),rawExact=raw==expected)
            assert row['httpStatus']==200 and row['rawExact'],'Actual transfer differs from fixed Git'
            row['status']='PASS'
        except Exception as error:row['error']=type(error).__name__+': '+str(error)
        rows.append(row)
    result={'schema':1,'status':'PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL','source':SHA,'actualSelectedTransfers':len(rows),'rows':rows,
            'scope':'Four actual HTTP bodies raw compared to fixed Git; not every manifest member, archive inspection, new owner GNU or current game interaction.'}
    (OUT/'receipt.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(result));return int(result['status']!='PASS')


if __name__=='__main__':raise SystemExit(main())
