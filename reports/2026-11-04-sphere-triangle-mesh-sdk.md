# 球×静的三角形集合の共有SDK

2026-11-04 JST。Native最大64面の同じ純粋核を、ABI1の64 F64交換とJS所有snapshotへ接続し、ローカル受入を完了した。公開CI/Pagesは未確認。World/CCD/manifold・ゲームのmesh接触への接続はこのSDKに含めない。

## 変更と交換の契約

新6exports、合計74。begin0..64→1..6面ずつのappend10..60値→query14値で一つの有界stagingを準備する。stagingと最終snapshotは別所有で、begin/appendの成功も直前照会結果/outputを消さない。不正chunkは全体を拒否し、先頭の正常面だけを追加しない。queryのモデル失敗は交換成功で新nearest-nullの診断へ更新し、交換拒否は旧結果を保持する。

header24/source14/row58/candidate13。元順のsource/各row/全候補を読み、全work総和・optionalとzero padding・signed zero・全可能ID・各上下端の最小をJSで検査する。単一面の厳密decoderを各rowでも再利用し、異なる面の法線や局所座標を一つへ混ぜない。JSはnested設定 `{maxSurfaces,primitive:{...}}` を受け、全入力を最初に所有copyする。caller iteratorで容量や成分数を拡張せず、元arrayの有界indexを読む。

契約と例は [SDK文書](../docs/SPHERE_TRIANGLE_MESH_SDK.md)。未解決面も含む全体のnearestを部分成功として作らず、World/他record/clockは独立のままにする。

## ローカル受入

- 独立strict Nativeの追加C ABI18群と既存API77群、共有buildの全34CTestが成功。
- Node526/526・skip0（新SDK専用10群を含む）、構文検査成功。Web build `1f40cf023bb8472f` / 46 modules / 22 entries。
- Native48入力を45モデル照会（29completed/16意図した失敗=6row_failure+10preflight）と3 host拒否へ実測分類。65面はbegin、ID0/unsafeはappendで拒否。host拒否をモデル結果へ埋めない。
- 実主WASMのpacket27160 numeric bitsと所有DTO model20808 numeric bitsがNativeに一致。negative zero比較4453件。Nativeのlayout監査25881bitsとは別集計。
- 実WASMの45結果を独立有理数へ通し、136実面行・128成功の2688成分と集合87成分、計2775成分が成功。43改ざん負例を拒否。実64面・13多重winner・10dominance例も保持。
- 旧単一面SDKの22327packet/13432model bitsと独立1848成分/23負例、旧simulationの回帰も新主WASMで成功。
- 変更しない55 C++原本と7通知の62ファイル、SDK3配布物以外の全authored assets/game sourceが207aa60からbyte不変。22HTMLの生成map/URLは新build IDへ更新。

実ブラウザでは新SDK638777B/build1f40のロード、出撃・前進/boost・停止、3撃破とカバーclip1までの記録を確認。複数generationの履歴を残した22照会は全completed、GPU常駐3mesh、error0。初回の静止中敗北やShiftのみの入力を、移動boostの成功へ読み替えない。これは既存Source/FK/LBS/derivedの互換確認で、新しい集合照会をゲームの接触へ使った意味ではない。計測値から一般fpsや性能改善を主張しない。

## SDK来歴と配布

57 authored source/header、pinned Emscripten6.0.13。同じbinary64 Interval核をstrict flagsでコンパイルした。

| 配布物 | bytes | SHA-256 |
|---|---:|---|
| 主WASM | 638777 | a9424df2c00c9cbf9fb11a979e2c00b991cf17a9128a0ccb52ea86bbc8b871ec |
| ES glue | 53435 | d0b06ae80449622cd98df4df496447a552c4c6c31bfe7a656c08df9eae4aae18 |

7通知は全byte不変。linked runtime memberには既存pinned libc++の `algorithm.o` が1つ増え、除去0。link mapのuint64 sort/introsortとpinned `algorithm.cpp` のSHA/既存LIBCXX-LICENSEへの対応を [runtime監査](sphere-triangle-mesh-sdk-runtime-audit.json)へ保存した。新しいsolver/geometry library/packageではない。標準runtimeの部品増加を「全runtime集合不変」とは記載しない。本体ライセンスは未選定。

## 未完・失敗の記録と公開確認

Windows独立ASanはAPI cpp/追加testをinstrumentする予定だったが、compile未完247.548秒でlauncherを停止した。exit15、object/exeなし、runtime未実行であり成功扱いしない。生ログと [未完記録](sphere-triangle-mesh-sdk-core-proof/asan-attempt.json)を保持する。公開CIではAPI/testのASan/UBSanとregular strict kernel archiveを結合し、pure mesh kernel自体の別ASan/UBSanと区別して検証する予定。

補助Native decoder検査は初回の相対importを訂正後、実Native45packetでPASS（交換はmockで、WASMではない）。配布監査はruntime集合不変という初期仮定で停止したため、実測のalgorithm.o追加と一次ソース/通知を記録して再検査した。数値比較の失敗を無視して通したものではない。

ローカル全commandとhashは [統合検証](sphere-triangle-mesh-sdk-local-verification.json)、原Native proofと未完ASanは `sphere-triangle-mesh-sdk-core-proof/`、実WASM raw/独立負例/旧SDK回帰は `sphere-triangle-mesh-sdk-checks/run-20261104-root/` に保存。exe/obj/libは配布しない。

公開CI/Pages・配信byte・公開の旧ゲーム互換を次に確定する。次の最小段は、集合の入力編集・全行診断・全候補IDと失敗を操作し保存できる手動browser lab。SDKの完成を、閉固体内部、一般接触応答/摩擦支持・関節、流体/弾塑性損傷・専門車両/IK/高精度光学撮像の完成へ拡張しない。
