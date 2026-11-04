# 球×三角形の手動照会ラボ

2026-11-04 JST。**実装・最終ローカル/公開Linux CI/Pages受入済み。** [照会ラボ](../tools/sphere-triangle-lab.html)は13プリセット、strict JSON入力、返却区間のXY/XZ/YZ投影、全候補/KKT、signed zeroを保持するJSON保存を提供する。同じC++ SDKの実結果を使い、JSで距離や候補分類を計算し直さない。

## 確認した範囲

専用14/全Node516件skip0、構文、Web build fc67426f445af36a/46modules/22entryが成功。[原ログ](sphere-triangle-lab-checks/run-20261103T234822368732Z/commands.json)。全13presetの実SDKは面・全辺・全頂点・裏側の8成功と、中心一致/退化/細すぎる面/候補予算/法線幅の5モデル失敗。解析closest/delta/distance²/3-4-5法線、Source/result所有、unknown/duplicate keys/nonfinite/underflow拒否、signed zero保存を検査した。モデル不正の有限値を勝手にclampしない。

UIは入力変更時に旧geometry/候補/図/JSONを消しsaveを無効にする。投影変更でC++照会を増やさず、選択presetへresetする。実装中にsync loader例外でretry不能になる問題と、reload中に旧runtimeでqueryできる問題を修正。遅延load中の編集、二重retryのcoalesce、dispose後のlate resolve/reject無復活も回帰した。

## 実ブラウザ

localhostで全13例を操作し、成功/モデル失敗のgeometry有無と候補数を記録した。[全ケース](sphere-triangle-lab-local-browser/presets.json)。手編集後の旧表示/JSON消去・save無効、ID0交換拒否と選択presetへのreset復帰を確認。[交換拒否](sphere-triangle-lab-local-browser/host-rejection.json)。

中心x=-0、半径2へ手編集した配置は、成功geometryとboundary_unresolvedを返した。gap区間は[-4.440892098500627e-16,8.881784197001254e-16]mで、0をまたぐ符号を確定接触へ置き換えていない。XYへ投影変更し、実ダウンロード2926Bが表示JSONと完全一致、入力-0も保存された。[返却値](sphere-triangle-lab-local-browser/edited-boundary.json)、[保存ファイル](sphere-triangle-lab-local-browser/downloaded.json)、[画面](sphere-triangle-lab-local-browser/edited-boundary.png)。この2D投影では三角形が線に潰れるが、3D形状の退化と判定したわけではない。

## 来歴・境界

SDK55source/header、7通知、WASM612824B/glue51085B/manifestと、全assets/samplesはd9cf168からbyte不変を照合した。Native32CTest/sanitizerは変更のない[SDK段階](2026-11-04-sphere-triangle-sdk.md)の受入であり、このローカルUI検証で再実行したとはしない。既存原著図を再利用し、25教材記事を維持する。外部package/素材/serviceは追加せず、本体license未選定を維持する。

再現は `python -X utf8 reports/sphere-triangle-lab-recipes/check.py`。UIの純helper/操作検査は `node --test tests/sphere-triangle-lab.test.mjs`。公開確認はプッシュ後に別記録へ保存する。World/CCD/storage/manifold・ゲームmesh接触・一般の接触応答・流体/損傷・専門シミュレータの完成ではない。

## 公開後の視認性修正と最終受入

初期公開eef9e51の数値・操作は成功したが、極小のrectは3px stroke指定だけでは図の白枠が見えにくかった。0db8f54では表示inkを各側1.5 SVG px広げ、区間数値や元の投影modelは変えなかった。図の表示サイズを距離誤差へ読み替えない。最終buildは `50e73448d9d02126` / 46 modules / 22 entry。[再ローカル全516件](sphere-triangle-lab-checks/run-20261103T235808657751Z/commands.json)と[全13例の1491数値bits不変](sphere-triangle-lab-marker-verification.json)を確認した。最初の全ログ/画面と修正後の証拠を別保存した。

[最終Linux CI 41743458000](https://github.com/tatata93/pikapikaengine/actions/runs/41743458000)、[Pages 41743456326](https://github.com/tatata93/pikapikaengine/actions/runs/41743456326)の全job/stepが成功した。GNU13.3.0/Node22.23.4で32CTest/Node516skip0、SDK22327packet/13432model bits、独立1848成分/23負例、旧SDK2841/両transport各2318/quick54410、新kernel ASan/UBSan126群と既存sanitizer工程が成功。既存warning36行の診断列はSDK受入時と一致し、全warningを原行番号付きで保存した。全ログの全文保存とはせず、全工程状態と有限の必要行の抜粋である。

最終公開25ファイル合計1,078,093Bは0db8f54のGit blobと完全一致。公開ブラウザの全13presetは最終ローカルの入力/結果1491数値bitsと一致した。手編集での旧結果消去、ID0の交換拒否とreset復帰、x=-0/radius2のboundary_unresolved、XY投影、実ダウンロード2926B/表示JSONの完全一致・-0保持を再確認した。初期summary検査ではPython標準JSONが整数表記-0を+0へ読むため符号監査が失敗したが、ファイルは変更せずparse_intで-0を保持するよう検査側を訂正した。JavaScriptのObject.isと実ダウンロードのbyte一致は一貫して成功していた。

[最終統合証拠](sphere-triangle-lab-public-verification.json)、[公開25ファイル](sphere-triangle-lab-final-public-bytes.json)、[最終13例と保存ファイル](sphere-triangle-lab-final-public-browser/downloaded.json)、[最終画面](sphere-triangle-lab-final-public-browser/edge-bc.png)。[照会ラボを起動](https://tatata93.github.io/pikapikaengine/tools/sphere-triangle-lab.html?v=0db8f54)、[既存ゲーム](https://tatata93.github.io/pikapikaengine/?v=0db8f54)。ゲームの接触処理へこの照会を適用した意味ではない。

次は[Native有限集合の受入案](../docs/SPHERE_TRIANGLE_MESH_PLAN.md)。最大64面・全列挙・安定ID/所有copy・未解決失敗の伝播・同率候補保持と独立有理数参照を設計しただけで、まだ実装していない。
