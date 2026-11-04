"""Update the receipt only after exact public jobs, bytes and source proofs pass."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parents[2]
proof=json.loads((root/'reports/sphere-triangle-mesh-held-load-public-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS' and proof['commit']=='7844b46863a9b3168e9f831adc5a362f53ce13c8'
resume='保持荷重・秒時間のNative球×静的mesh照会7844b46を公開受入。元F/m+gを区間のままp(t)へ通すread-only queryとconst World adapter。専用92群/39CTest/631Node skip0、独立79入力=13window8separated2初期負23未認証33不正、2028audit/748leaf/37prefix外island/2268lastMesh成分、16self/63負例（-O拒否含む）/label-order独立が成功。Engine41790729060/Pages41790728378全job/step成功、GNU新3TUのWerrorと新核/interval/mesh/dynamics/tests全ASan-UBSan、Release-sanitized fixture bytecmpも成功。既存36warning multiset不変。33公開file1627338Bがfeatureblob一致。旧345原本/SDK86exports719410B/glue58933B、Web6aa725ed1898f4e9/51modules25entries不変。[検証記録](../reports/2026-11-04-sphere-triangle-mesh-held-load.md)。次は[丸め自由伝播guard](SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD_PLAN.md)をNative-onlyで実装する。計画のみで、W1の既存operation-graph上界を再使用しr+Bで全域separatedを証明、Hの実candidateを検査する。World進行/一般TOI応答/摩擦・流体/材料損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';text=p.read_text(encoding='utf-8');text,n=re.subn(r'^再開位置:.*$','再開位置: '+resume,text,count=1,flags=re.M);assert n==1;p.write_text(text.rstrip()+'\n\n追記: '+resume+'\n',encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md';text=p.read_text(encoding='utf-8');old='**Native実装のローカル受入済み・公開Linux検証待ち**';assert old in text;p.write_text(text.replace(old,'**Native実装の公開受入済み（7844b46）**',1).rstrip()+'\n\n次段は[丸め自由伝播guardの計画](SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD_PLAN.md)。この計画追加では新guardは未実装。\n',encoding='utf-8',newline='\n')
p=root/'docs/RESEARCH.md';p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n保持荷重7844b46の公開受入: Engine41790729060/Pages41790728378全job/step成功、GNU39CTest/631Node skip0/79Fraction/16self63負例、旧SDK・専門核回帰、3新TUのWerrorと新核/interval/mesh/dynamics/新tests全ASan-UBSan、Release-sanitized fixture同byteも成功。既存36warning診断multiset不変。33公開file1627338BがGitblob一致し、原著図も実公開表示を確認。次は新外部依存を増やさずW1の既存operation-graph上界をprivate bridgeで再使用するNative-only guardを計画する。共有cpp変更時は旧bit回帰とSDK provenance再生成を別受入に含め、今回の数学path成功をWorld応答へ昇格しない。\n',encoding='utf-8',newline='\n')
p=root/'reports/2026-11-04-sphere-triangle-mesh-held-load.md';text=p.read_text(encoding='utf-8');text=text.replace('公開CI/Pagesは確認待ち。','公開CI/Pagesまで受入済み。',1);text=text.replace('(sphere-triangle-mesh-held-load-browser/diagram.png)','(sphere-triangle-mesh-held-load-browser/diagram.jpg)',1)
text+='''
## 公開受入

feature `7844b46863a9b3168e9f831adc5a362f53ce13c8` のEngine41790729060（job126443232581）、Pages41790728378（build126443236177/deploy126443378806/report126443378901）は全job/step成功。GNU39CTest/631Node skip0、新79入力Fraction/16self63負例、旧SDK/専門核回帰も成功した。3新TUはstrict FP＋Wall/Wextra/Wpedantic/Werrorで通過し、新held-load核・interval・sphere/mesh・dynamics・新testsをすべてinstrumentした独立ASan/UBSanも92群成功。Releaseとsanitizedの全fixture JSONがbyte一致し、sanitizedの独立Fractionも成功した。Windows sanitizer実行や例外注入をこの結果に含めない。

既存36warningの診断multiset/数は不変。全Run block・全warning・選定した実行結果を原行番号つきで保存し、全logのarchiveとは呼ばない。[公開機械集計](sphere-triangle-mesh-held-load-public-verification.json)が全job/step、source/原stdout-stderr/hash、数値/Work、保護原本/配信を検査する。

33選定公開ファイル計1627338Bがfeature Gitblobに完全一致した。原著SVGは公開ブラウザで全体表示を目視。[公開画像](sphere-triangle-mesh-held-load-browser/public-diagram.jpg)とlocal画像は同byteの1265×760 JPEG。初回保存名の`.png`はcapture APIが返したJPEGの拡張子誤りで、元byteを保持したまま`.jpg`へ複製し、画像を加工せず形式/寸法/hashを機械集計で確認した。図は説明の表示証拠で、数値計算や新ブラウザAPIの実行証拠ではない。

[説明を開く](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=7844b46#accelerated) · [ゲームを起動](https://tatata93.github.io/pikapikaengine/?v=7844b46)。ゲーム/SDKの原本は全byte保全し、その実操作は前回の公開受入を継承する。

次の[丸め自由伝播guard計画](../docs/SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD_PLAN.md)を追加した。これは未実装で、保持荷重pathとordinary-double伝播の差Bを既存W1の実装から再使用し、r+Bの全域separatedとHでの実candidate成功を別に要求する。全Worldのevent順序・衝撃/摩擦/支持・残時間/atomic commitと荷重消費は後続である。
'''
p.write_text(text,encoding='utf-8',newline='\n')
print('Public acceptance receipt written; free-flight guard remains a plan.')
