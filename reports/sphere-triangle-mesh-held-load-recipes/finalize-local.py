"""Write the measured local milestone receipt after the machine acceptance passes."""
from pathlib import Path
import json, re
root=Path(__file__).resolve().parents[2]
proof=json.loads((root/'reports/sphere-triangle-mesh-held-load-local-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS' and (proof['node'],proof['ctest'],proof['fixtures'])==(631,39,79)
resume='保持荷重・秒時間のNative球×静的mesh照会をローカル受入。新核は元F/m+gを区間のままp(t)へ通すread-only queryとconst World adapter。専用92群/39CTest/631Node skip0、独立79入力=13window8separated2初期負23未認証33不正、2028audit/748leaf/37prefix外island/2268lastMesh成分、16self/63負例（-O拒否含む）/label-order独立が成功。初回buildは試験clock callback署名だけを訂正、物理入力/閾値/核は無変更。旧345原本/SDK86exports719410B/glue58933BとWeb6aa725ed1898f4e9/51modules25entries不変。公開Linux strict/Werror/全核ASan-UBSan/Pages/選定配信は未確認。[実装ガイド](SPHERE_TRIANGLE_MESH_HELD_LOAD.md)・[検証記録](../reports/2026-11-04-sphere-triangle-mesh-held-load.md)。Worldの丸めた伝播/一般TOI応答/摩擦・流体/材料損傷/専門モデル/IK制御/高精度撮像は未完。'
p=root/'docs/PLAN.md';text=p.read_text(encoding='utf-8');text,n=re.subn(r'^再開位置:.*$', '再開位置: '+resume,text,count=1,flags=re.M);assert n==1;p.write_text(text.rstrip()+'\n\n追記: '+resume+'\n',encoding='utf-8',newline='\n')
p=root/'docs/SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md';text=p.read_text(encoding='utf-8');old='2026-11-04 JST。**設計のみ・未実装**。';assert old in text;text=text.replace(old,'2026-11-04 JST。**Native実装のローカル受入済み・公開Linux検証待ち**。[実装ガイド](SPHERE_TRIANGLE_MESH_HELD_LOAD.md)と[実行記録](../reports/2026-11-04-sphere-triangle-mesh-held-load.md)を参照する。',1);text=text.replace('新規予定は`core/include/','新規追加は`core/include/',1);text=text.replace('今回この計画からSDK/JS/UIが使えるとは案内しない。','今回のNative実装からSDK/JS/UIが使えるとは案内しない。',1);p.write_text(text,encoding='utf-8',newline='\n')
p=root/'docs/RESEARCH.md';p.write_text(p.read_text(encoding='utf-8').rstrip()+'\n\n保持荷重Nativeのローカル受入: 79入力を厳密Fractionの二次全域極値・独立距離・R/E二乗/全prefix/partitionで監査し、13entry/8separatedを非vacuousに確認。2028audit/748leaf、16self/63負例（-O拒否含む）/label-order独立、専用92/39CTest/631Node skip0成功。FP/品質/予算不足を成功へ変えず、一般四次最小化/World伝播/衝撃応答/実fault注入は別受入とする。公開GNU strictとメモリ検査は未確認。\n',encoding='utf-8',newline='\n')
report='''# 保持荷重・秒時間の球×静的メッシュ — Native受入

2026-11-04。元の質量・世界外力・重力から一定加速度を区間のまま構成し、有限三角形の面/辺/頂点へ曲がる自由経路を照会する新しいNative-only核を追加した。`query` と `query_body(const World&)` は全所有診断を返す。Worldを進めず、元荷重を消費しない。公開CI/Pagesは確認待ち。

## 実行結果

専用92群、全39CTest、631Node（skip0）、syntax/Web buildが成功。新79完全入力は13侵入窓・8全域非接触・2初期負・23未認証・33入力拒否。独立Fractionは2028audit、748認証葉、37prefix外island、2268lastMesh成分を監査し、16数学自検査・63負例（Python -O拒否含む）・ラベルと順序に依存しない検証も成功した。原入力fingerprintは `3a7679cff9aa2cebf0b162bdb920821d16b272fe645cec5ccc9849f0025dc85e`。

全区間の二次coordinate極値を端点/内部停留点から求め、point-triangleは可行face解と全3clamped辺から独立に最小化した。C++候補maskを正解にせず、R/E上界は有理数の二乗比較で確認する。一般quartic全最小化oracleとはしない。

解析例は、chordが見逃すface侵入（force/gravity別分解2件）、chordが偽衝突する回避、辺/頂点四次の入口、非有理極小を持つ安全/侵入で非vacuousに成功した。接線とF/m丸め打消しは証拠不足を未認証のまま保持する。代表face窓は[0.015624940395355225,0.015625029802322388]秒、外向き時間幅上端8.940696716308595e−8秒。窓の経路箱のL1上界は約8.58e−6mで、時間幅を位置精度や貫通量へ換算していない。

全256audit/128partition、127frontier、64source/全候補ID、予算事前予約、初期点だけのprefix、失敗祖先と後続の証拠、所有snapshot、FP環境拒否と復帰、全World body/plane/gravity/荷重/storage/pointer不変も専用試験で実行した。allocation/不明work例外を実際に注入したという主張はしない。

## 保全と再現

旧345ファイルの全byteがbaselineと一致。Native/SDK/JS/旧tests/ゲーム/資産/配布runtimeの原本を保持した。主SDKは86exports/61source-header、WASM719410B、glue58933B。Webは6aa725ed1898f4e9/51modules/25entriesで、今回の新核はWASMへ出力していない。

freshの旧entry所有SDKは62実model+3host、全105056モデル数値/3239負零・原入力4728数値/108負零を一致。明示補足mixed65の独立558leaf/1452audit/3840成分、17self/90負例、所有copyを再実行して成功した。それ以前の旧全wire/専門核の検証は、全byte保全・今回の631Node/39CTestと既公開記録を組み合わせて継承する。ゲーム実操作は前回公開ラボ受入の記録を継承する。

[機械集計](sphere-triangle-mesh-held-load-local-verification.json)は全コマンド/exit/source前後hash/原stdout-stderr/fixture/hashを監査する。[最終ログ](sphere-triangle-mesh-held-load-checks/run-20261104-final)と[再現recipe](sphere-triangle-mesh-held-load-recipes/check.py)を参照。原著SVGは実ブラウザで全体を目視し文字/配置を確認した。[画像](sphere-triangle-mesh-held-load-browser/diagram.png)は説明の表示証拠で、数値受入の代用ではない。

初回buildは試験補助FixedClock callbackの引数型不一致C2664で失敗し、`[](double){}`へ1箇所訂正した。[初回](sphere-triangle-mesh-held-load-checks/run-20261104-initial)と[修正後](sphere-triangle-mesh-held-load-checks/run-20261104-002)の原ログを保持する。物理入力/閾値/核を変更して通過させていない。独立参照の予備run001..005は全exit0で、self-onlyから79入力・58→63負例の追加を区別して[原ログを保管](sphere-triangle-mesh-held-load-reference-attempts/archive-map.json)した。最終root検証は全ソース凍結後に別実行した。

## 境界

これは数学的な元荷重の自由経路の照会。ordinary-double伝播tube、全pair/同時event順序、法線/feature競合/manifold、反発・摩擦・支持、衝撃後の残時間・再照会と全tick rollbackがWorld接続に必要。候補IDやinterval midpointをそのままpoint impulseへ渡さない。SDK/JS/UI、流体/塑性損傷、専門車両/航空/鉄道、IK/制御、高精度撮像も後続。

新外部依存/転載素材/有料serviceなし。本体license未選定。[入力・証拠・単位・API](../docs/SPHERE_TRIANGLE_MESH_HELD_LOAD.md)を参照する。
'''
(root/'reports/2026-11-04-sphere-triangle-mesh-held-load.md').write_text(report,encoding='utf-8',newline='\n')
print('Local receipt written; public acceptance remains pending.')
