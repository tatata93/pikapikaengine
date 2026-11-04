# 保持荷重・自由伝播guardの手動ラボ

2026-11-04。ローカル受入成功。公開CI/Pagesは次に確認する。前段の所有API公開は8035f93、確定記録はb3d2470。このUIの実行を前段の公開成功へ加算しない。

## 追加した入口

`tools/sphere-triangle-mesh-flight-lab.html`でheld/guardの二つの原本JSONを編集する。保持荷重の曲線の元半径と、丸め誤差Bを加えたguardの膨張半径を分ける。元bodyの全field・Hの未commit候補・全audit/証明島/partition/frontier/tail・Work・全source/lastMesh行/候補を保持し、未認証や失敗を安全へ変えない。全256audit、128partition、127frontier、64面/全保守ID、448候補を省略しない。

表示は返却されたbox/anchorの投影とglobal秒[0,H]の帯で、F/m・距離・KKT・sqrt・法線・接触solverをJSへ追加していない。選択auditとlastMeshの所属が違うと幾何を重ねない。最小pixel幅は表示用で、証明や誤差幅を変えない。

編集/mode変更/失敗/再試行で旧結果と保存可能状態を消去し、世代で遅延loadを無効化する。pagehideでdisposeへ接続し、handlerを解除する。保存は最後に表示したcaptured原本/全所有結果を使う。入力128KiB、結果8MiBは最終LF込みのUTF8 bytesで判定し、負零・optional・末尾を切らない。

原著[ガイド](../docs/SPHERE_TRIANGLE_MESH_FLIGHT_LAB.md)・[SVG](../docs/learn/diagrams/sphere-triangle-mesh-flight-lab.svg)・教材を追加した。新package/外部solver/転載素材/有料serviceなし、本体license未選定。Worldの時間進行/衝突応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。

## ローカルの実行と出自

[集計JSON](sphere-triangle-mesh-flight-lab-local-verification.json)はPASS。最終canonicalは`sphere-triangle-mesh-flight-lab-checks/run-20261104-final-002/`。全raw command/開始/終了code/所要秒数/stdout/stderr/実行sourceの前後hashを保持する。

| 対象 | 結果 |
|---|---|
| 専用 / 全Node | 23/23 / 684/684、skip0 |
| 固定原本 | Native183入力から出自付き30例、全source4625数値bit/負零112 |
| 実owned method呼出 | 30、実モデル29 / host拒否1 |
| model全照合 | 83292数値bit / 負零1779 |
| 保存packet全照合 | 85265数値bit / 負零1835 |
| 実ブラウザ | 全30例の可視原本/全JSON/表の件数、実モデル29とhost1 |
| browser追加閲覧 | 最後のaudit255、最後の面63とlastMesh所属、projection/audit/面切替後の全結果保持 |
| 実ダウンロード | 成功11615B・未認証319666B、返却された実file/archived bytes/表示JSONの完全一致、負零と最終LF保持 |
| Web | cd45c7f1ac2ba5e5 / 54modules / 26entries |
| 原本保護 | 349tracked raw原本不変、既存25HTML本文保持 |
| SDK | 92exports / 67source-header / 32TU / runtime91 / 7通知、WASM800982B/glue61661Bとmanifest全byte不変 |

heldの内訳はseparated5/entry_window5/not_certified6/initial_penetration1、guardはcertified_separated5/not_certified6/invalid_input1、hostは65面1。hostをNative結果で補填しない。旧World DTOの慣性や速度を暗黙変換せず、Native body全fieldを明示して使う。

[browser照合](sphere-triangle-mesh-flight-lab-browser/browser-verification.json)は448473数値bit/負零13142の**比較assertion回数**を記録する。同じUI値をNode UI、前段実173-owned、enum投影したNativeへ複数回照合しているため、独立な数値の件数や実行モデル数ではない。primary30例と追加view・downloadのscopeを分ける。全可視JSON/AX/画像/表metadataと、実ダウンロード元path・file名・bytes/hash・保存コピーを残す。

ブラウザのretryはcached runtimeが次のDOM観測前に完了した。復旧後の全結果は確認したが、瞬間的な空表示を実画面で観測したとは扱わず、`browserRetryTransientClearObserved:false`を明示する。遅延resolve/reject・二重retry・編集中load・pagehide・dispose後の復活阻止と閲覧query0は、実controllerを使うカウント付き23群のNode試験で確認した。ブラウザで追加照会数0を直接測れたとは扱わない。

新buildで既存ロボットゲームの射撃2撃破・boost・停止と、背面カバー22照会全完了/3mesh常駐/error0を観測した。ゲーム/SDK/Native数値核の原本は保持する。新UIだけのローカル受入ではNative41件や旧173 Fractionを再実行したとは報告せず、byte保護したb3d2470の公開済み証拠を継承する。公開CIは41CTest・旧173/15負例・raw183/16負例を改めて実行する設定のまま、新UI検証を追加した。

## 初回試行と訂正

- [初回専用](sphere-triangle-mesh-flight-lab-agent-tests/run-001/)20群18成功/2失敗は、deferred-load試験のJSONがguardなのにdropdownをheldのままにしていたsetup誤り。明示mode変更を先に行い、mode不一致の拒否を緩めずに再試行した。21群成功の後、pagehide2群を追加し最終23群を再実行した。旧成功/失敗を保存する。
- 初期の未versioned UIではwholePath/wholeVelocityの表示field名を誤り、実返却boundsがnull表示になった。canonical名`wholePathBounds`/`wholeVelocityBounds`へ訂正し、6成分の実DOM比較を専用試験へ追加した。初期画面は`sphere-triangle-mesh-flight-lab-browser-development/`に保持し、source観測は修正後であることを分け、数値受入の証拠へ転用しない。headerを縮め、最初の画面で図と入力へ到達できるようにした。
- 最初の統合集計では、新HTMLへの初回`?build=`追加をnormalizerが本文差分と誤認して停止した。試験684/23・実30例自体は成功していたが、その集合を最終成功にせず、生成queryを完全除去する新HTML用規約へ直した。旧25HTMLのbaseline規約は保持する。[元の生成前HTMLの全byte復元](sphere-triangle-mesh-flight-lab-html-normalization-correction.json)も確認し、別fresh `final-002`でWeb/全684/23/実30例とbrowser比較を再実行した。元`final`の失敗collectionは変更していない。

実growth/allocator使用量/stack高水位/故意Native allocation faultやFP環境の注入はこのUIの受入対象にしていない。通常のcapacity観測や人工packetをその証拠へ読み替えない。

## 次段

静的meshの原本/lifetime/ID/revisionを所有し、World全pairのread-only自由伝播guardへ拡張する最小設計を調査中。現在の単一body照会を全Worldの順序付け・累積丸め・接触manifold・反発/摩擦/支持やtransactional tickの完成と呼ばない。接触応答は独立の解析/保存量/仕事/rollbackの受入を揃えて進める。
