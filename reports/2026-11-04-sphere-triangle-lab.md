# 球×三角形の手動照会ラボ

2026-11-04 JST。**実装・ローカル受入済み。公開CI/Pagesは未確認。** [照会ラボ](../tools/sphere-triangle-lab.html)は13プリセット、strict JSON入力、返却区間のXY/XZ/YZ投影、全候補/KKT、signed zeroを保持するJSON保存を提供する。同じC++ SDKの実結果を使い、JSで距離や候補分類を計算し直さない。

## 確認した範囲

専用14/全Node516件skip0、構文、Web build fc67426f445af36a/46modules/22entryが成功。[原ログ](sphere-triangle-lab-checks/run-20261103T234822368732Z/commands.json)。全13presetの実SDKは面・全辺・全頂点・裏側の8成功と、中心一致/退化/細すぎる面/候補予算/法線幅の5モデル失敗。解析closest/delta/distance²/3-4-5法線、Source/result所有、unknown/duplicate keys/nonfinite/underflow拒否、signed zero保存を検査した。モデル不正の有限値を勝手にclampしない。

UIは入力変更時に旧geometry/候補/図/JSONを消しsaveを無効にする。投影変更でC++照会を増やさず、選択presetへresetする。実装中にsync loader例外でretry不能になる問題と、reload中に旧runtimeでqueryできる問題を修正。遅延load中の編集、二重retryのcoalesce、dispose後のlate resolve/reject無復活も回帰した。

## 実ブラウザ

localhostで全13例を操作し、成功/モデル失敗のgeometry有無と候補数を記録した。[全ケース](sphere-triangle-lab-local-browser/presets.json)。手編集後の旧表示/JSON消去・save無効、ID0交換拒否と選択presetへのreset復帰を確認。[交換拒否](sphere-triangle-lab-local-browser/host-rejection.json)。

中心x=-0、半径2へ手編集した配置は、成功geometryとboundary_unresolvedを返した。gap区間は[-4.440892098500627e-16,8.881784197001254e-16]mで、0をまたぐ符号を確定接触へ置き換えていない。XYへ投影変更し、実ダウンロード2926Bが表示JSONと完全一致、入力-0も保存された。[返却値](sphere-triangle-lab-local-browser/edited-boundary.json)、[保存ファイル](sphere-triangle-lab-local-browser/downloaded.json)、[画面](sphere-triangle-lab-local-browser/edited-boundary.png)。この2D投影では三角形が線に潰れるが、3D形状の退化と判定したわけではない。

## 来歴・境界

SDK55source/header、7通知、WASM612824B/glue51085B/manifestと、全assets/samplesはd9cf168からbyte不変を照合した。Native32CTest/sanitizerは変更のない[SDK段階](2026-11-04-sphere-triangle-sdk.md)の受入であり、このローカルUI検証で再実行したとはしない。既存原著図を再利用し、25教材記事を維持する。外部package/素材/serviceは追加せず、本体license未選定を維持する。

再現は `python -X utf8 reports/sphere-triangle-lab-recipes/check.py`。UIの純helper/操作検査は `node --test tests/sphere-triangle-lab.test.mjs`。公開確認はプッシュ後に別記録へ保存する。World/CCD/storage/manifold・ゲームmesh接触・一般の接触応答・流体/損傷・専門シミュレータの完成ではない。
