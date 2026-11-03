# 球×静的三角形の共有SDK接続

2026-11-04 JST。**実装・ローカル/公開Linux CI/Pages受入済み。** Native純粋核/headerをbyte不変で主ABI1へ接続し、入力24/結果58/候補13の2exportsを追加した。JS `querySphereTriangle({position,radius},{id,vertices},settings)` は同じC++を呼び、検査済みの所有snapshotを返す。[APIと使用例](../docs/SPHERE_TRIANGLE_SDK.md)。

## ローカルの根拠

- 新C ABIは77試験群、全体32CTest、Node502件skip0、構文検査、Web buildが成功。Native全体の原ログは[sphere-triangle-sdk-checks](sphere-triangle-sdk-checks/run-20261103T232431069618Z/native-commands.json)。
- 同じ113入力を実Native ABIと主WASMへ渡し、111モデル（88 completed / 23モデル失敗）と2件のID交換拒否を分離した。入力/前後output/58値summary/全13値candidateを含む22,327数値bitsと、JSから再構成した13,432モデル数値bitsが一致。符号付きzero比較3,472。geometry-nullを成功geometryに補填しない。[実比較記録](sphere-triangle-sdk-checks/run-20261103T232431069618Z/sdk/report.json)。
- 実WASMの88成功geometryを、binary64入力を厳密な有理数に変換する独立参照へ渡し、1,848成分の包含を確認。23改ざん負例が拒否された。Nativeとの一致だけを数学的根拠としない。[独立負例](sphere-triangle-sdk-checks/run-20261103T232431069618Z/sdk/negative-controls/negative-controls.json)。
- 専用JS6試験群は旧SDK能力検出、実解析配置の面/辺/頂点/裏側、文書の3-4-5例、モデル失敗、copy所有、全summary/候補の不正DTO、unused KKTの[-0,+0]、交換拒否時output保持、独立snapshot/resetを含む。NativeはWorld時刻/姿勢/荷重と全旧snapshotの保持も確認した。
- 独立Native buildはwarning/stderr0、77群、113行probeを再実行し、純核とのpacket配置17,782数値bitsを別照合した。[証拠](sphere-triangle-sdk-standalone/provenance.json)と[layout監査](sphere-triangle-sdk-standalone/transport-audit.json)。exe/obj/libは配布せず、全体CMakeからのbuildも上記で別に確認した。
- 初回Nodeは500/502。先行した教材リンク先の報告ファイルが未作成だった点と、既存profiler試験のsource53/export66固定が原因。報告を作成し、試験を全source/hash mapと実headerのexport列挙比較へ変更後、502/502へ復帰。初回の失敗ログを保持し、成功記録で上書きしない。

## 配布物・来歴

既設Emscripten6.0.13、ABI1、64F64出力容量を維持する。68exports、55 source/header、sphere_triangle.cppは-fno-fast-math / -ffp-contract=off。旧53原本の変更はsimulation_api.cpp/.hのみ、新規参照は既存sphere_triangle.cpp/.hpp。7通知hashとlinked標準library member集合は直前SDKと一致し、主SDKの3配布物以外の全assets原本はbyte不変。

| artifact | bytes | SHA256 |
|---|---:|---|
| main WASM | 612824 | eff93890e4dcf6387ba9fe55e5b15e38f4db817f68dfd112bb1ba503b78fb90d |
| generated glue | 51085 | 0d541bc399cbdd6b55e7f2f848479acd39af408d2dec5b4379d8b1b09fb0a7d0 |

Web build `f7448823095f375b`、45 modules。全hashと52証拠ファイルは[ローカル統合記録](sphere-triangle-sdk-local-verification.json)。既設SDKを `node scripts/build-simulation.mjs` でbuildし、再現は `python -X utf8 reports/sphere-triangle-sdk-recipes/check.py native`、表示されたrun directoryを引数に `validate`。初回修正後の全試験は `recheck` に保存した。比較CLIは `node scripts/verify-sphere-triangle-sdk.mjs native-fixtures.json native-sdk-probe output-directory`。出力を新規作成し、既存rawを上書きしない。

## 実ブラウザと範囲

新WASMの既存IRON FIELD互換をlocalhostで確認。READY、出撃、Shift+Wの1.1秒入力、pause後に背面カバー20query/20validated・常駐3mesh・device lostなし。開度約93%。[raw](sphere-triangle-sdk-local-browser/boost-paused.json)、[UI](sphere-triangle-sdk-local-browser/ui.txt)、[画面](sphere-triangle-sdk-local-browser/boost-paused.png)。表示されたbuild IDと612824Bの実ロードを確認した。CPU/rAF値をGPU時間や一般fps保証にしない。

これは瞬間のread-only狭域照会で、World/CCD/storage/manifold・ゲームmesh衝突・一般の区間→点衝撃応答は未接続。材料損傷・流体・車両/航空/鉄道/ロボット制御・高精度光学撮像の完成とはしない。次の最小受入は、入力編集・失敗/候補区間・JSON保存を実行できる手動ブラウザtriangle labである。公開結果は次節と別の統合記録に保存する。

## 公開コードe100beeの確認

[Linux CI 41740127784](https://github.com/tatata93/pikapikaengine/actions/runs/41740127784)と[Pages 41740127278](https://github.com/tatata93/pikapikaengine/actions/runs/41740127278)の全job/全stepが成功した。GNU13.3.0/Node22.23.4で32CTest/Node502skip0、新SDKの22327packet・13432model numeric bits、独立1848成分/23負例、旧SDK2841・両transport各2318・quick profile54410比較、球×三角形kernel ASan/UBSan126群と既存sanitizer工程を確認した。新ABIの専用sanitizerを追加したとはしない。既存compiler warning36行を全保存し、診断メッセージの列は前回と一致、新核warning0である。原ログの全文は保存せず、全工程の状態と必要な数値/compiler/sanitizer行・全warningを原行番号付きの有限抜粋で残した。

公開31ファイル合計1,330,820Bをe100beeのGit blobと照合して完全一致。実ブラウザもREADYから出撃→Shift+W 1.1秒→pauseへ進め、21query/21validated、常駐3mesh/device lostなし・開度約87%を確認。main WASM612824B、build `f7448823095f375b`、原本Sourceも一致。これは既存ゲーム互換であり、ゲームの三角形接触を実装した意味ではない。

[全統合証拠](sphere-triangle-sdk-public-verification.json)、[公開配信](sphere-triangle-sdk-public-bytes.json)、[game raw](sphere-triangle-sdk-public-game.json)、[画面](sphere-triangle-sdk-public-game.png)。[ゲームを起動](https://tatata93.github.io/pikapikaengine/?v=e100bee)。次の手動ラボは[有限受入計画](../docs/SPHERE_TRIANGLE_LAB_PLAN.md)に沿って実装する。
