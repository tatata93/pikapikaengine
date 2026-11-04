"""Record completed public acceptance after the exact-feature aggregate passed."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
proof = json.loads((root/'reports/world-static-mesh-preparation-public-verification.json').read_text(encoding='utf-8'))
assert proof['status'] == 'PASS' and proof['commit'] == '6608bc3963a7eaca1ac8a9d40f3ae5d76f93d05e'
assert proof['publicFiles'] == 74 and proof['publicBytes'] == 2430924
assert proof['publicGame']['queries'] == 23

def replace(path, before, after):
    target = root/path
    text = target.read_text(encoding='utf-8')
    assert text.count(before) == 1, path
    target.write_text(text.replace(before, after, 1), encoding='utf-8', newline='\n')

replace('docs/PLAN.md',
        '続くNative world_static_mesh_flight::prepareを実装しローカル検証成功（公開Linux CI/Pagesは次）。',
        '続くNative world_static_mesh_flight::prepareは機能6608bc3で公開受入済み。Engine41820304200全22段/Pages41820303901が成功。通常・全依存source計装ASan/UBSanの有限84入力は独立参照と一致し、新3TUのWerror成功、旧48GNU警告は同一。配信73件とGitHubのworkflow原本1件、合計74件2430924Bをfeature blobと照合。公開ゲームは射撃2撃破/boost/停止/23正常照会を確認した（prepareはNative専用でゲーム数値モデルへ未接続）。')
replace('docs/PLAN.md', '次は公開受入後に[全World guard計画]',
        '次は全closed-cell証拠を所有する球対/平面coverage核から[全World guard計画]')
replace('docs/WORLD_STATIC_MESH_PREPARATION.md',
        '新Native APIのローカル受入を確認。公開Linux CI/Pagesの検証は次に行う。',
        '新Native APIは機能6608bc3でローカル・公開Linux CI/Pagesの受入を確認。')
replace('docs/WORLD_STATIC_MESH_PREPARATION.md',
        'Linux warning/sanitizer、allocation fault、FTZ/DAZ注入、全pair数値認証はこのローカル受入では未実施。',
        'このローカル時点ではLinux warning/sanitizerは未実施だった。その後の公開受入は下記の別実行で確認した。allocation fault、FTZ/DAZ注入、全pair数値認証は未実施のままである。')
replace('docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md',
        'ローカル検証した（Native42CTest/有限84、公開受入は次）。',
        '公開受入した（機能6608bc3、Native42CTest/有限84、Linux全22段・ASan/UBSanとPages成功）。')
replace('reports/2026-11-04-world-static-mesh-preparation.md',
        '新prepareのローカル受入はPASS。公開Linux CI/Pages・warning/sanitizer監査は次に確認する。',
        '新prepareは機能6608bc3963a7eaca1ac8a9d40f3ae5d76f93d05eでローカル・公開受入PASS。公開Linux CI/Pages・warning/sanitizer監査も確認した。')
replace('reports/2026-11-04-world-static-mesh-preparation.md',
        '次は公開CI/Pages・74ファイルのfeature blob照合と新Linux warning/sanitizer監査を確認する。その後、',
        '公開受入の詳細は以下に追記した。次は、')

public_text = '''

## 機能6608bc3の公開受入

[公開集計](../reports/world-static-mesh-preparation-public-verification.json)はfresh public-summary-002でPASS。Engine [41820304200](https://github.com/tatata93/pikapikaengine/actions/runs/41820304200) / job126541504170の全22段と、Pages [41820303901](https://github.com/tatata93/pikapikaengine/actions/runs/41820303901)の全3job/stepが成功した。Linuxの42CTest/684Node skip0、新89群、通常実行84入力と全依存7sourceをASan/UBSanで計装した別84入力を確認。両fixture JSONはbyte一致し、各実行の全入力・結果を独立Pythonで検査した。自己12群/改変拒否45、新3TUのWerrorが成功し、既存48警告は前段とfile/line/column/診断のmultisetが同一、新規0だった。これはNativeの検証であり、準備APIのNative/WASM parityではない。

公開73件＋Pages対象外のworkflowのGitHub完全commit原本1件、計74件2430924Bがfeature Git blobと一致。初回bytes001はworkflowをPagesから取得して404になった。そのrawを保持し、collectorの取得先・distribution/channelだけを明示的4置換で直してbytes002を全件再実行した。製品sourceや照合対象は削らない。最初の集計001はexcerptにANSI色付きloop終端doneが欠けて拒否された。同じ取得済みjob logの原行4件を追加し、doneも含む元の全command照合を維持して集計002が成功した。初回失敗のstdout/stderr/exitを保持する。

公開図と教材は実ブラウザで画像1120×780の読み込み、原本リンク、全記事文字、図の文字・矢印・組会計を確認した。図は概念説明で数値実測ではない。同じ公開ゲームは射撃2撃破・boost energy59・129km/h・一時停止を操作し、23照会すべてchecked/validated/completed、resident mesh3、errors0を記録した。prepareをブラウザやゲームの数値接触に接続した証拠ではない。

保存したCI抜粋は全11818行/876630文字のうち4621行を原ordinal付きで選択したもので、完全remote logを保存したとは主張しない。既存355raw・旧26HTML・7つの新準備source・92export SDK/runtime91/32TU/7通知・WASM800982B/glue61661Bは公開集計時も保持された。scope、所有入力bit、capacity観測の限界は上記ローカル記録を維持する。

起動: [ロボットゲーム](https://tatata93.github.io/pikapikaengine/?v=6608bc3) / [原著教材](https://tatata93.github.io/pikapikaengine/docs/learn/index.html?v=6608bc3#accelerated) / [準備の概念図](https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/world-static-mesh-preparation.svg?v=6608bc3)。次は球対/平面の全closed-cell非接触coverageを所有して独立監査する核へ進む。全World候補・接触応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。
'''
for name in ['docs/WORLD_STATIC_MESH_PREPARATION.md', 'reports/2026-11-04-world-static-mesh-preparation.md']:
    target = root/name
    assert '## 機能6608bc3の公開受入' not in target.read_text(encoding='utf-8')
    with target.open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(public_text)

with (root/'docs/RESEARCH.md').open('a', encoding='utf-8', newline='\n') as stream:
    stream.write('\n\nNative prepare公開受入6608bc3: Engine41820304200全22段/Pages成功。通常84と全依存source ASan/UBSan84はbyte一致・各独立参照成功、42CTest/684Node skip0、Werror新3TU・旧48warning multiset不変。73Pages＋GitHub完全commit workflow1の74件2430924B一致。実公開図/教材とゲーム2撃破/boost/停止/23正常照会を確認した。初回workflow Pages404とANSI done抜粋漏れの失敗rawを残し、取得経路と抜粋だけを修正して全件受入。新外部資料/依存/素材/有料service無し、prepareはNative専用で数値全pair guard/World更新ではない。次は全closed-cell証拠を所有する球対/平面coverage核。\n')
print(json.dumps({'status': 'PASS', 'feature': proof['commit'], 'updatedDocuments': 5}))
