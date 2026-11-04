"""Publish the measured local acceptance prose without rewriting numerical sources."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
PREFIX='accelerated-plane-box-coverage'
source=ROOT/f'reports/{PREFIX}-checks/run-20261104-summary-001/acceptance.json'
raw=source.read_bytes(); report=json.loads(raw)
assert report['status']=='PASS' and report['ctest']==44 and report['negativeControls']==65
target=ROOT/f'reports/{PREFIX}-local-verification.json'
assert not target.exists();target.write_bytes(raw)
paragraph='再開位置: Native accelerated_plane_box_coverage の明示B/margin付き全closed-cell核をローカル受入した。固定サイズ原入力・全3座標tube/distance/threshold/gap・全audit/partition/current/frontierを所有し、全leafのgap.lower()>0だけを認証する。Bとmarginは必須4引数でcallerが明示し、実WorldのBを自動で証明しない。44CTest/専用74群/67有限入力、1306実public Evaluationの15672端点bit（2496負零）、独立Fractionの全7836区間・3918座標全域極値・2612固定AST corner、16自己/65拒否/-O、Node684 skip0・構文/Web cd45/54modules26entriesが成功。369既存raw・26生成HTML・92export SDK/32TU/runtime91/7通知を保持。公開Linux CI/ASan/UBSan/Pagesは次に確認する。次は実seedのB/全pair両predicate/明示margin/compiler規約・全体予約・全候補を結ぶWorld guardへ進む。[契約](ACCELERATED_PLANE_BOX_COVERAGE.md)・[記録](../reports/2026-11-04-accelerated-plane-box-coverage.md)。一般接触応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。'
p=ROOT/'docs/PLAN.md';text=p.read_text(encoding='utf8');start=text.index('再開位置:');end=text.index('\n',start)
text=text[:start]+paragraph+text[end:];p.write_text(text,encoding='utf8')
record=f'''# 2026-11-04 明示B・marginによる平面box coverage

Native専用の新核をローカル受入した。公開CIとPagesは未判定で、次段の追記で分けて記録する。元World/SDK/gameの数値経路は変更しない。

## 実装と条件

必須4引数 `Input(sphere,plane,position_error,contact_margin)` で、位置誤差Bとsolverのmarginを推測せず受け取る。全時間座標箱へBを加え、raw法線の左結合dot/offset、別のr+margin、gapを自作Intervalで囲む。各演算nodeの実数またはbinary64 RN-evenの族を含め、同じ結合順序のFMA収縮も包含する。任意再結合・fast-math・FTZ/DAZ・拡張精度・実World全compilerを認証したとはしない。

全closed partition・全返却Evaluation・未照会tail/current・原値bitsを所有する。最大255評価/128leaf/depth32で、全leafのstrict positiveと完全被覆だけをcertifiedとする。誤差Bは宣言値であり、actual bodyの誤差上限・metric分離の別証拠・同じmargin・compilerとの対応・全pair・候補検査は後続World gateである。sqrt/metric/伝播を新核内で呼ばない。接触応答・流体・材料損傷・専門車両/航空/鉄道・IK/制御・任意高精度撮像の完成ではない。

## ローカル実測

| 検査 | 実結果 |
|---|---|
| MSVC strict standalone / CMake統合 | 新74群・67有限入力、44CTest成功 |
| 有限入力の分類 | certified20 / not_certified20 / invalid27 |
| 実public valueの由来 | 1306全Evaluationを再照会し、15672端点bits・2496負零端点一致 |
| 独立全域包含 | 全7836I、3918座標の厳密二次極値±B、2612固定AST corner、21034 node-pairs |
| 独立metadata | 750partition / 149frontier / 5current、最大255audit / 128leaf / 127tail |
| 非自明な認証 | B=.125の放物線35audit/18leafで分割認証 |
| 参照の自己検査・改変 | 16自己群 / 65拒否（Python -O含む）、label/order非依存 |
| 既存Web | 684成功・skip0、構文、build cd45c7f1ac2ba5e5 / 54module / 26entry |
| 既存保持 | 369raw原本、26生成HTML、92exports/67source-header/32TU/runtime91/7通知 |

Canonical fixtureは676814B SHA256 `0dafa4e430ad34958a25795b07a8785972cdf9dd6071cf2f24a8b1a676493cc1` でstandaloneとbyte一致。入力fingerprintは `2d660f51cb84c0bdbc8f8f9e3d26bf59caf92d53878bc12c0bf2ebce72408ec9`。実real-positiveだが個別RNでdotが0になるlost-low-term、FMA/個別積の差、near-unit metric/raw両方向の反例、margin閾値、巨大offset相殺、subnormal半加速度、環境拒否と復帰を検査した。

MSVC19.51 x64のsizeof×返却capacity観測は {report['storageObservation']['sizeofCapacityBytes']}B。Resultのinline snapshotは二重加算しない。これはallocator overhead/一時領域/stack/RSS/実heap使用量の上限ではない。全44CTestのrealは155.60s、捕捉wall155.65sで、一般性能の保証ではない。FTZ/DAZ/丸めmodeの限定probeを全target検証と呼ばない。

## 証拠と試行履歴

[ローカル集計](accelerated-plane-box-coverage-local-verification.json) と `accelerated-plane-box-coverage-checks/run-20261104-{{native,regressions,reference,summary}}-001/` に元stdout/stderr/実command/前後sourcehashを保持する。Native初回standalone・canonical・数学包含は成功。参照run003はcheckerと16self成功後、負例の末尾が既certifiedで変異にならないselector誤想定で停止した。製品や数学基準を変えず対象を未認証leafへ訂正し、run004の61件成功を保持、予定の4追加controlを含む最終run005/親canonicalで65件を再確認した。数学的に有効な広いdistanceと人工nonreturnの整合正例は、実public valueの由来や自然C++故障注入とは区別する。

教材のanchor追加用単発コマンドにshell引用のSyntaxErrorがあり、ファイル変更前に停止した。再利用可能な `lesson-anchor.py` で訂正して表示を確認した。baseline説明のHTML分類も受入前に訂正し、教材本文は生成26entryの外にあることを実hashで確認した。製品失敗として付け替えない。

原著SVG・教材の実表示は `accelerated-plane-box-coverage-local-browser/` の5capture＋observationsに保存。新APIのブラウザ照会やWorld接続の検証とはしない。

## 調査・配布

[Microsoft /fp](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170) と [GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) を実読し、収縮・再結合・環境・中間精度の境界を確認した。外部code/図/本文を移植せず、新package/有料service/本体license選択はない。[調査原本](accelerated-plane-box-coverage-primary-sources.json)、[FP監査](../docs/WORLD_PREDICATE_FLOATING_POINT_AUDIT.md)、[契約](../docs/ACCELERATED_PLANE_BOX_COVERAGE.md)。SDK/WASMは既存配布物を維持する。
'''
(ROOT/'reports/2026-11-04-accelerated-plane-box-coverage.md').write_text(record,encoding='utf8')
research='2026-11-04 明示B/margin平面box coverageローカル受入: 44CTest/74群67入力、1306実public Evaluation全15672端点bitsと独立Fraction全7836I/固定AST exact-or-integer-RN choices、16self65拒否、684Node skip0成功。369原本/26HTML/SDKを保持。Microsoft /fp とGCC Optimize Optionsの公式資料を実読し、FMA収縮と再結合・excess precisionを区別した。actual B・compiler全般/World接続・metric/接触応答は後続。Native-only、公開CI/ASan/UBSan/Pagesは別受入。負例selector失敗rawを保持し製品/数学基準を変えず訂正した。'
additions={
 'docs/RESEARCH.md':research,
 'docs/legal/ASSETS.md':'2026-11-04 平面box coverage: docs/learn/diagrams/accelerated-plane-box-coverage.svg と教材追加文は本repoで新規作成した原著概念図/説明。実測性能・軌道図や外部図の転載ではない。既存sample assetを保持。',
 'docs/legal/DEPENDENCIES.md':'2026-11-04 平面box coverage: 原著C++/Python/Intervalだけを追加。新package・完成数学/物理solver・transitive dependency・有料service・配布runtimeは追加しない。既存92export SDK/32TU/runtime91/7通知を保持。本体licenseは未選定のまま。',
 'docs/legal/REFERENCES.md':'2026-11-04 平面box coverage: [Microsoft /fp](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170)・[GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) を実読。固定AST exact-or-RN包含によるFMA収縮の独自導出を compiler説明と区別し、再結合・FTZ/DAZ・excess precisionの全target保証へ拡張しない。外部code/本文/式画像/図の転載なし。詳細は WORLD_PREDICATE_FLOATING_POINT_AUDIT.md と reports/accelerated-plane-box-coverage-primary-sources.json。',
}
for name,addition in additions.items():
    p=ROOT/name;text=p.read_text(encoding='utf8');assert addition not in text
    p.write_text(text.rstrip()+'\n\n'+addition+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','localRecordCopiedExactly':True,'report':'reports/2026-11-04-accelerated-plane-box-coverage.md','storageBytes':report['storageObservation']['sizeofCapacityBytes']}))
