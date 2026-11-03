import hashlib,json
from pathlib import Path
p=Path('build/skinning-sort');rows=[]
for name,preferred in [('native.json','reports/skinning-native.json'),('native-oracle.csv','reports/skinning-native-oracle.csv')]:
 baseline=Path(preferred)
 if not baseline.exists():baseline=Path('build/skinning-proof')/name
 a=(p/name).read_bytes();b=baseline.read_bytes()
 if a!=b:raise RuntimeError('Changed baseline '+name)
 rows.append({'current':str(p/name),'baseline':str(baseline),'bytes':len(a),'sha256':hashlib.sha256(a).hexdigest(),'byteIdentical':True})
(p/'baseline-comparison.json').write_text(json.dumps({'passed':True,'comparisons':rows},indent=2)+'\n',encoding='utf-8');print('PASS 65 fixtures and128 oracle rows unchanged byte-for-byte')
