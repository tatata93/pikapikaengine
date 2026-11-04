"""Archive the first public failure and stage the exact test-only correction."""
from datetime import datetime,timezone
from hashlib import sha256
from pathlib import Path
import json,subprocess,time
ROOT=Path(__file__).resolve().parents[2]
PREFIX='reports/accelerated-plane-box-coverage'
FEATURE='a9093238a7cb0c9c82b70c00613610124ca4213b'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==FEATURE
fix_dir=ROOT/(PREFIX+'-ci-fix-development/run-001')
fix=json.loads((fix_dir/'acceptance.json').read_text(encoding='utf8'))
local=json.loads((ROOT/(PREFIX+'-local-verification.json')).read_text(encoding='utf8'))
base=json.loads((ROOT/(PREFIX+'-baseline.json')).read_text(encoding='utf8'))
def info(raw):return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
assert fix['status']=='PASS' and fix['groups']==74 and fix['sourceStable']
source=fix['source'];original=(fix_dir/'original-tests.cpp.txt').read_bytes()
assert original==subprocess.check_output(['git','show',FEATURE+':'+source],cwd=ROOT)
assert info(original)==fix['original']==local['newSources'][source]
assert info((ROOT/source).read_bytes())==fix['new']
expected=original.decode().replace('#include <string>\n','#include <string>\n#include <string_view>\n',1).replace(
    'const std::string& name){const auto at=','std::string_view name){const auto at=',1).replace(
    '"Missing fixed case: "+name','"Missing fixed case: "+std::string(name)',1).encode()
assert (ROOT/source).read_bytes()==expected
for p,s in {**base['protected'],**base['generatedEntries'],**local['newSources']}.items():
    assert info((ROOT/p).read_bytes())==(fix['new'] if p==source else s),p
for command in fix['commands']:
    assert command['exit']==0 and not command['timedOut'] and command['sourceStable']
    for stream in ['stdout','stderr']:
        assert info((fix_dir/command[stream]).read_bytes())==command[stream+'Hash']
assert (fix_dir/'native-fixtures.json').read_bytes()==(ROOT/(PREFIX+'-checks/run-20261104-native-001/native-fixtures.json')).read_bytes()
ci_history=ROOT/(PREFIX+'-public-ci-development/run-001')
failed_log=(ci_history/'failed-job-full.txt').read_bytes()
assert sha256(failed_log).hexdigest()=='c81b0c297b24cc2125321445a2b8eeae0d52ee0cd9df21dab20b05ec893fe453'
assert b'error: possibly dangling reference to a temporary' in failed_log
for name in ['public-bytes','public-runs']:
    raw=(ROOT/(PREFIX+'-'+name+'.json')).read_bytes()
    assert json.loads(raw)['commit']==FEATURE
    target=ci_history/('original-'+name+'.json');assert not target.exists();target.write_bytes(raw)
old_browser=ROOT/(PREFIX+'-public-browser')
archive=ROOT/(PREFIX+'-public-browser-development/run-002/original-captures')
archive.mkdir(parents=True,exist_ok=False)
for path in old_browser.iterdir():
    assert path.is_file() and path.suffix in {'.txt','.jpg','.json'}
    (archive/path.name).write_bytes(path.read_bytes())
record='''# 2026-11-04 平面box検査のGNU警告修正

原実装a909323の公開CI run41835425148/job126592955091は、第22工程の新testのWerrorで失敗した。通常44CTest/684Node、67入力の独立包含・16self65拒否、既存のメモリ検査工程までは成功。新plane-boxのWerrorが停止したため、同工程の新ASan/UBSanと最終WASM工程を成功として扱わない。

名前検索helperはcaller所有corpus内のCaseを返すが、検索名が一時std::stringへのconst参照で渡る形に対しGCC13がdangling-reference警告を出した。検索名をstd::string_view値渡しとし、includeと失敗診断文字列の明示変換だけを変更した。警告抑制、数値核、入力、fixture、oracle、判定閾値、compiler flags、SDKの変更はない。

厳密MSVCの5TUを再コンパイルし警告0・74群成功。全67入力の676814B fixtureは原standalone/canonicalとbyte一致、1306全Evaluation・15672端点bits・2496負零を再確認した。旧local-verificationは旧testをhashした履歴として維持し、新testは別のtargeted-postfix-local receiptへ記録する。公開GCCの警告解消・新ASan/UBSan・全工程は再CIで確認するため、現時点では公開受入未完。

元test・計画/実patch・前後13source hash・全4command/raw/acceptanceは accelerated-plane-box-coverage-ci-fix-development/run-001/。初回失敗の全文ログ900113文字とjob/Pages/100byte配信記録を public-ci-development/run-001/、旧9ブラウザcaptureを public-browser-development/run-002/original-captures/ へ保存した。全文ログの最初の一括書込みはtoolの64k上限で実行前に拒否されたため、既知の公開テキストだけを有界なliteralデータとして転送し、長さ・SHA256を照合して保存した。外部ログのコードは実行していない。
'''
(ROOT/'reports/2026-11-04-accelerated-plane-box-coverage-ci-fix.md').write_text(record,encoding='utf8')
p=ROOT/'docs/PLAN.md';text=p.read_text(encoding='utf8');start=text.index('再開位置:');end=text.index('\n',start)
paragraph='再開位置: plane-box原実装a909323はローカル44CTest/74群・67入力/独立7836区間/16自己65拒否/684Nodeで成功。公開100byte照合・図/教材/ゲーム39正常照会は確認したが、GNU13新test WerrorでCI第22工程が停止し公開受入は未完。検索名helperだけをstring_view値渡しへ修正し、厳密MSVC74群と全fixtureのbyte不変を別receiptで再検証した。旧local-verificationのhashは書き換えず保持。次に修正commitの全24工程/新メモリ検査/Pagesを確認する。[修正記録](../reports/2026-11-04-accelerated-plane-box-coverage-ci-fix.md)。その後は両B・明示margin・丸めdelta/dot/sqrtを含む球box検査からWorld統合へ進む。球boxは設計のみで未実装。一般接触・流体損傷・専門モデル・IK/制御・高精度撮像は未完。'
p.write_text(text[:start]+paragraph+text[end:],encoding='utf8')
p=ROOT/'docs/RESEARCH.md';text=p.read_text(encoding='utf8')
p.write_text(text.rstrip()+'\n\n2026-11-04 plane-box公開CI初回はGNU13のtest補助関数dangling-reference警告で停止した。参照先はcaller所有corpus内だが検索名の一時文字列を値のstring_viewへ変更し、include/診断変換のみを修正。警告を抑制せず、厳密MSVC74群と元676814B fixture byte一致を別receiptへ保存した。原local report/失敗全文log/旧100配信とUIを保持し、公開新ASan/UBSanと最終工程は再CI待ち。数値核・oracle・SDK・license・依存は不変。\n',encoding='utf8')
start=time.perf_counter();process=subprocess.run(['node','scripts/build-web.mjs'],cwd=ROOT,capture_output=True,timeout=60)
web={'args':['node','scripts/build-web.mjs'],'exit':process.returncode,'wallSeconds':time.perf_counter()-start}
for stream in ['stdout','stderr']:
    raw=getattr(process,stream);path=PREFIX+'-ci-fix-web.'+stream+'.txt';(ROOT/path).write_bytes(raw)
    web[stream]=path;web[stream+'Hash']=info(raw)
(ROOT/(PREFIX+'-ci-fix-web.json')).write_text(json.dumps(web,indent=2)+'\n',encoding='utf8')
assert process.returncode==0
assert subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode==0
changed=set(filter(None,subprocess.check_output(['git','diff','--name-only','-z'],cwd=ROOT).decode().split('\0')))
assert changed=={source,'docs/PLAN.md','docs/RESEARCH.md'},changed
paths=set(changed)|{'reports/2026-11-04-accelerated-plane-box-coverage-ci-fix.md',PREFIX+'-recipes/publish-ci-fix.py'}
for directory in [fix_dir,ci_history,archive]:
    paths.update(p.relative_to(ROOT).as_posix() for p in directory.rglob('*') if p.is_file() and p.suffix.lower() not in {'.exe','.obj','.pdb','.lib','.log'})
paths.update(PREFIX+'-ci-fix-web.'+s+'.txt' for s in ['stdout','stderr']);paths.add(PREFIX+'-ci-fix-web.json')
manifest={'schema':1,'baseCommit':FEATURE,'status':'PASS','paths':sorted(paths),'files':{p:info((ROOT/p).read_bytes()) for p in sorted(paths)},'scope':'Exact3line test helper correction and targeted evidence; original local/failed public evidence retained. Fresh GNU full acceptance pending.'}
manifest_path=PREFIX+'-ci-fix-paths.json';nul_path=PREFIX+'-ci-fix-paths.nul'
(ROOT/manifest_path).write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
stage=sorted(paths|{manifest_path,nul_path})
(ROOT/nul_path).write_bytes(b'\0'.join(p.encode() for p in stage)+b'\0')
print(json.dumps({'status':'PASS','paths':len(stage),'bytesBeforeManifest':sum(s['bytes'] for s in manifest['files'].values()),'newTest':fix['new'],'oldLocalUnchanged':True}))
