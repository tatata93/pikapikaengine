# 球×静的三角形集合: Native有限受入

2026-11-04 JST。最大64面のread-only全列挙を実装し、ローカル受入を完了した。公開Linux CI/Pagesも修正版5c9093bで全工程成功した。この核は主SDK・World・CCD・ゲームのmesh接触へ未接続である。

## 実装と意味

新しい `sphere_triangle_mesh.hpp/.cpp` が既存単一三角形核を呼ぶ。元順の所有triangleと実queryを全行に残し、通常のモデル失敗後も照会を継続する。全件成功時だけ距離²/距離/gapの上下端の最小から集合nearestを作る。距離²下限が最小上限以下のstable IDを全て昇順保持し、面別のclosest/barycentric/normalを一つへ合成しない。

環境を最初に検査し、全入力を事前検査する。構造拒否はrows空/作業0。通常のrow failureでは全行の実結果を残してnearestを返さない。割当失敗等のfatal経路は不完全な診断になり得る。割当失敗注入は未実施。最大64query/448候補/32768sqrt更新を明示し、時間性能の保証とはしない。単一面のsqrt予算は呼出後監査という既存の意味を維持する。

## ローカル検証

- 全CMake build成功、33/33 CTest、Node516/516・skip0、構文検査成功。
- 独立MSVC `/O2 /W4 /fp:strict` と別ASan buildは各59群成功。新3ファイルのコンパイル警告0、stderr0。full buildの既存警告とは分ける。
- 48入力: 集合29completed、6row_failure、13事前拒否。実136面照会のうち128completed/8失敗。64面全同率、全7feature、6順列、符号零/所有copy/再試行、FE_UPWARDとFTZ/DAZ、遠い不良面も隠さない条件を含む。
- Native/ASan fixture全373170Bがbyte一致。SHA-256 `6cad93d2d7187cd2a817c413f63822aa232aa2932e3f8c437a647d935ad59b88`。
- 独立Fraction参照は各面2688成分と集合87成分、計2775成分を検査。真の多重winner13例、厳密dominance10例、64面成功1例。43改ざん負例を全拒否し、fixtureの改名/逆順で集計不変。
- SDKの55 source/header・7通知・2artifact・manifest、全assets/samplesと既存単一面核/header/testが38b59f1からbyte不変。WASM612824B/68exportsを新しい集合APIとして扱わない。
- Web build `50e73448d9d02126`、46modules/22entriesで不変。教材25記事を維持し、区間記事に原著SVGを追加。

統合recipe初回は新fixtureへ旧single検査器を呼ぶ1か所で停止した。`recover-reference.py`が対象callだけを新検査器へ訂正再実行しPASSを確認。他検証のsource hash一致を確認して既存結果を保持した。初回FAIL summaryとstdout/stderrを残す。

証拠: [統合記録](sphere-triangle-mesh-local-verification.json)、[独立核受入](sphere-triangle-mesh-core-proof/acceptance.json)、[原出力対応](sphere-triangle-mesh-core-proof/archive-map.json)。全text bytesを保存し、exe/objは配布しない。再現recipeは `reports/sphere-triangle-mesh-recipes/check.py`、独立build recipeは保存したcmd/py（元buildパスを保持）にある。

## 公開確認と次段

以下の初回・修正版の履歴を区別し、最終公開記録を末尾に保存した。Native局所の幾何包含を、World/CCD/manifold・摩擦支持、閉固体内部、流体/弾塑性損傷、専門車両、IK/制御・高精度撮像の完成へ広げない。

次は有界C ABI/JS所有snapshot契約の設計。入力上限/原本ID・signed zero、全行診断と失敗時nearest不在、旧SDK検出、原子的入力交換と旧出力保持、独立参照との全数値照合を固定してから実装する。ゲーム接触へ中点法線や選ばれた一面を無断適用しない。

初回コード7b598e7のLinux CI/Pagesは全成功。28公開ファイル1,091,366Bがcommit blobと一致し、原著SVG実表示・既存ゲームREADY・単一面ラボの既定completedを確認した。GNUの追加2warningは新試験のfor/if同一行配置で、核のwarningではなかった。行を分けてstrict Native59群と独立2775成分を再検査し、48fixture全373170Bのbyte不変を確認。初回の全job/step状態と全38warningを含む有限ログ抜粋を別名保存。修正版の公開CI/Pagesはまだ確認待ち。

最終コード5c9093bの公開CI [41747231968](https://github.com/tatata93/pikapikaengine/actions/runs/41747231968)、Pages [41747231937](https://github.com/tatata93/pikapikaengine/actions/runs/41747231937)は全job/step成功。GNU13.3/Node22.23.4で33CTest/Node516skip0、mesh独立2775成分/43負例とASan/UBSan59群、単一面126群・旧SDK2841bits/両transport各2318bits/quick54410等の回帰が成功。新試験warning0、既存36warningの診断列は前回ラボと一致した。全状態と全warningを含む有限ログ抜粋を保存し、全文保存とはしない。

公開29ファイル1,097,707Bは最終commit blobとbyte一致。実ブラウザの原著図・既存ゲームREADY・単一面ラボ既定completedは初回7b598e7の観測で、最終commitで観測対象13資源のbyte不変を別照合した。二回目のブラウザ操作を行ったとはしない。機械検査と全hashは [sphere-triangle-mesh-public-verification.json](sphere-triangle-mesh-public-verification.json)。起動: [ロボット](https://tatata93.github.io/pikapikaengine/?v=5c9093b)、[単一面ラボ](https://tatata93.github.io/pikapikaengine/tools/sphere-triangle-lab.html?v=5c9093b)、[原著図](https://tatata93.github.io/pikapikaengine/docs/learn/diagrams/sphere-triangle-mesh.svg?v=5c9093b)。新集合照会はNative限定のままである。
