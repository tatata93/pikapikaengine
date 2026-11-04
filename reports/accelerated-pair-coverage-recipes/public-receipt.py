"""Update documentation only after exact-feature public acceptance passed."""
from pathlib import Path
import json

root=Path(__file__).resolve().parents[2]
proof=json.loads((root/'reports/accelerated-pair-coverage-public-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS' and proof['commit']=='f128f5040c2a4de0c0adba48896022c759f1b215'
assert proof['publicFiles']==84 and proof['publicBytes']==2573147
assert proof['publicCiScope']['engineSteps']==23 and proof['publicGame']['queries']==22

changes={
 'docs/ACCELERATED_PAIR_COVERAGE.md':[
  ('**ローカル受入済み：Native43CTest/専用69群・独立Fractionの全1913区間・自己14群/拒否53・Node684 skip0。公開Linux CI/Pages・GNU warning/sanitizerは次に確認する**。',
   '**機能f128f50で公開受入済み：Native43CTest/専用69群・独立Fractionの全1913区間・自己14群/拒否53・Node684 skip0、Linux CI全23段/Pages・GNU warning/sanitizerも確認**。'),
  ('GNU/sanitizer・公開受入は未実施。','GNUで通常と独自依存5sourceをASan/UBSan計装した各65入力を実行し、fixture byte一致と各独立数学監査を確認した。新3TUのWerrorが成功し、旧48警告は同一。公開受入の詳細は末尾を参照。')],
 'docs/ACCELERATED_PAIR_COVERAGE_PLAN.md':[
  ('**契約設計と受入方針。実装はローカル受入済み、公開GNU/sanitizer確認は次段**。',
   '**契約設計と受入方針。実装は機能f128f50で公開GNU/sanitizer・CI/Pagesまで受入済み**。'),
  ('既存SDKやゲームを更新しておらず、公開確認は未実施。',
   '既存SDKやゲームを更新せず、機能f128f50のLinux全23段/Pages・84配信原本・実公開図/教材/ゲームを確認した。')],
 'docs/PLAN.md':[
  ('次は公開Linux CI/GNU warning/sanitizer/Pagesと84件（83Pages+workflow原本1）のfeature blob照合を確認し、その後に全World guardのB膨張・plane追加条件・global予算・全候補へ接続する。',
   '機能f128f50のLinux全23段/Pages・通常/独自5source ASan/UBSan・旧48warning同一と、84件2573147B（83Pages+workflow原本1）のfeature blob一致を公開受入した。実公開図2viewport/教材全文・ゲーム2撃破/boost59/193kmh/停止/22正常照会を確認。次は全World guardのB膨張・plane追加条件（丸めdot/明示contact marginを含む）・global予算・全候補へ接続する。')],
 'reports/2026-11-04-accelerated-pair-coverage.md':[
  ('ローカル受入PASS、公開Linux CI/Pages・GNU/sanitizerは未実施。',
   '機能f128f5040c2a4de0c0adba48896022c759f1b215でローカル・公開受入PASS。Linux CI/Pages・GNU/sanitizerも確認した。'),
  ('次は公開全23段の実行、通常と全依存5source ASan/UBSan fixtureのbyte一致/各独立参照、旧GNU warning比較、83Pages+GitHub原本1の配信一致、図/教材/既存ゲームの公開実操作を確認する。',
   '公開全23段・通常/独自依存5source ASan/UBSan・旧GNU warning比較・84原本配信・実公開UIの受入結果を以下に追記した。次は全Worldの数値統合へ進む。')]
}
# Validate every match before writing any document.
pending={}
for name,edits in changes.items():
    text=(root/name).read_text(encoding='utf-8')
    for before,after in edits:
        assert text.count(before)==1,(name,before)
        text=text.replace(before,after,1)
    pending[name]=text

public_text='''

## 機能f128f50の公開受入

[公開集計](../reports/accelerated-pair-coverage-public-verification.json)はfresh public-summary-001でPASS。Engine [41828267971](https://github.com/tatata93/pikapikaengine/actions/runs/41828267971) / job126568510900の全23段と、Pages [41828267271](https://github.com/tatata93/pikapikaengine/actions/runs/41828267271)の全3job/stepが成功した。

Linuxでも43CTest/Node684 skip0、専用69群/65有限入力・全1913区間を確認。通常fixtureと、interval/accelerated/新coverage/新tests2の独自5sourceをASan/UBSan計装した別fixtureがbyte一致し、両実行へ独立Fractionを適用した。自己14群/拒否53、新3TUのWerrorが成功。既存48GNU警告は前準備版とfile/line/column/診断multisetが同一、新規0だった。MSVC/GNU全DTOのbit一致や、新APIのNative/WASM parityへ拡張した主張ではない。

83Pages資源＋完全feature commitのGitHub workflow原本1、計84件2573147BがGit blobと一致。図2viewportと教材の全記事/原リンク/画像1120×780を実公開で確認し、図の文字・区画・費用上界・未実装境界に重なりは見られなかった。全11証拠を原本hashと照合した。概念図と旧ゲームの互換性であり、ブラウザで新Native coverageを実行した証拠ではない。

既存ゲームは再出撃後に射撃2撃破・boost energy59/193kmh・一時停止を操作し、22照会の全checked/validated/completed、resident mesh3/errors0を保存した。最初の出撃ではコンテナへキーを準備するUI操作が送信前にtimeoutし、フォーカス済み入力へ切替後の経過21秒で通常の敗北となった。その1撃破のAX/操作メモを別の履歴へ保存し、正式なboost/停止互換性の証拠には採用していない。製品コード変更なしでfresh再出撃し、成功記録とは分離した。

CIは全11844行/882882文字のうち4661行を原ordinal付きで保存した抜粋であり、完全remote logの保存を主張しない。ANSI色付きloop終端・inline参照JSONを初めから含めて元command照合を維持した。status/bytes/browser-record/公開集計は全exit0。既存362raw・旧26HTML・新7source・SDK92exports/67source-header/32TU/runtime91/7通知・WASM800982B/glue61661Bは公開集計時も保持された。

起動: [ロボットゲーム](https://tatata93.github.io/pikapikaengine/?v=f128f50) / [教材](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=f128f50#accelerated) / [原著図](https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/accelerated-pair-coverage.svg?v=f128f50)。次は同owned snapshotの全pairへB/半径膨張とplaneの追加条件・全体予算・H候補検査を接続する。実Worldのrounded dotと明示contact marginを考慮し、数学的な幾何非交差を既存solverのcontact無しへ読み替えない。一般応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。
'''
for name in ['docs/ACCELERATED_PAIR_COVERAGE.md','reports/2026-11-04-accelerated-pair-coverage.md']:
    assert '## 機能f128f50の公開受入' not in pending[name]
    pending[name]+=public_text
for name,text in pending.items():
    (root/name).write_text(text,encoding='utf-8',newline='\n')
with (root/'docs/RESEARCH.md').open('a',encoding='utf-8',newline='\n') as stream:
    stream.write('\n\ncoverage公開受入f128f50: Engine41828267971全23段/Pages成功、43CTest/684Node skip0、通常/独自5TU ASan/UBSan fixture byte一致・各65入力1913区間の独立数学、14自己/53拒否、新3TU Werror、旧48warning multiset同一。84件2573147B（83Pages+完全commit workflow1）一致、実公開図2view/教材/ゲーム2撃破boost停止22正常照会。最初のUIキー準備timeout/通常敗北は別履歴へ保存し正式成功と分離。新coverageのBrowser数値接続・Native/WASM parity・全World認証は主張しない。次はowned全pair/丸めdot＋明示margin/B/全体予算/候補検査へ進む。\n')
print(json.dumps({'status':'PASS','feature':proof['commit'],'updatedDocuments':5,'publicAccepted':True}))
