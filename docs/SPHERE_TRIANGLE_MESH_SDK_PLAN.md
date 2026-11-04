# 三角形集合の共有SDK: 次の有界接続案

2026-11-04 JST。**実装・ローカル統合検証済み。公開CI/Pagesは未確認**。Native最大64面の公開受入後、既存ABI1/64 F64交換で全原本と全行診断を運ぶC ABI/JSへ接続した。新SDK74exports/57 source-headerで数値照合・独立参照を受け入れた。旧68-export SDKがこの集合照会に対応していたとは扱わない。World/CCD/応答・ゲーム適用は別段階で、追加APIの独立MSVC ASan試行は未完了として残す。

## 64値を超える入力を所有する

三角形1枚はIDと9座標の10値で、64枚は640値になる。一回の64値交換へ押し込まず、runtimeごとに一つの有界stagingを追加する。resource handleやWorld資源は追加しない。begin/appendは入力準備であり、照会完了とはしない。

接続する6exports:

- `pp_sim_sphere_triangle_mesh_begin(uint32_t triangle_count)` — 0..64を受理し、空の新stagingを用意。直前の照会snapshotとoutputは保持。65以上の交換拒否はstagingも保持する。
- `pp_sim_sphere_triangle_mesh_append(uint32_t value_count)` — input scratchの10..60値、10の倍数（1..6枚）を元順に追加。id/ABC XYZ。未begin・予定数超過・不正count/ID/非有限は拒否し、追加前stagingと照会snapshot/outputを保持。chunkを全部検査してから所有copyを交換する。
- `pp_sim_sphere_triangle_mesh(uint32_t value_count)` — 完成したstagingと入力14値から実Native query。未begin/予定数未達を交換拒否し、前snapshot/outputを保持。正しい交換のモデル失敗は新しいnearest-null記録へ更新。stagingは再照会用に保持する。
- `pp_sim_sphere_triangle_mesh_source(uint32_t ordinal)` — 照会時原本を所有した記録から14値。後のbegin/appendに追従しない。
- `pp_sim_sphere_triangle_mesh_row(uint32_t ordinal)` — 実照会済みrowの既存単一面形式58値。row不在/null queryは交換拒否し、他面の結果で代用しない。
- `pp_sim_sphere_triangle_mesh_candidate(uint32_t row, uint32_t ordinal)` — 当該実rowの候補13値。単一面照会snapshotとは独立。

0枚はNativeのsurface_count拒否を検証できる入力として渡す。重複IDや有限だが域外の座標はNativeの事前拒否に任せる。IDは既存交換契約の正safe整数に従い、NativeのID0/unsafe例はhost拒否として別集計する。uint32設定は整数域を交換検査し、域内の不正モデル値をJSだけで分類しない。

stagingと最終snapshotは別所有。appendは先行chunkまでの有効な原本を、後続不正chunkで壊さない。queryは全packet検査/有限性/診断整合を終えてから一回でcommit/publishする。他のsingle/optics/motion/skin/derived記録は保持し、global resetでstagingと集合snapshotを消す。割当失敗の強い保証は実装のmove/swap/publish順で検査し、未実施のfault injectionを実施済みとしない。

## 交換packet契約

query入力14値: 0..3=center XYZ/radius、4=maxSurfaces、5..7=maxCandidates/sqrtRefinements/maxTotalSqrtRefinements、8..10=maxLocalWidth/maxNormalWidth/minimumSineSquared、11..13=reserved zero。

集合headerは24値。下表のoptional indexはflag0ならpayloadをzero paddingとし、index0との混同を防ぐ。

| offset | 内容 |
|---|---|
| 0..4 | status / reason / hasNearest / originalSourceCount / ownedRowCount |
| 5..8 | hasFailedIndex / failedIndex / hasFirstFailedRow / firstFailedRow |
| 9..14 | queries / candidatesExamined / sqrtRefinements / sqrtLimitedRows / failedRows / possibleIdCount |
| 15..20 | squaredDistance / distance / gap、各bounds2 |
| 21..23 | reserved zero |

source packet14値: 0=元ordinal、1=ID、2..10=ABC XYZ、11=hasRow、12=hasQuery、13=isPossibleNearest。構造拒否でrowsが空でも照会時原本はsource recordから読める。nearest不在なら全isPossibleNearestが0。成功時は全source flagを集めてID昇順にし、header件数・各row距離²から導く全候補集合と一致を検査する。候補IDを64値のheaderへ切り詰めない。

hasNearest=0ならheader[14]も0、[15..20]は全て+0。hasQueryならhasRowも1、ownedRowCountは全sourceのhasRow総数、queriesはhasQuery総数と照合する。fatal診断でも不在域へ古い数値を残さず、実際に所有/実行した件数だけを表す。

row58/candidate13は既存の単一面packetの配置をそのまま再利用する。unused KKTの `[-0,+0]`、audit prefixとexaminedの最大1差、geometry不在/候補不在のzero paddingを保持する。原本sourceのsigned zeroを不在域のpaddingと混同しない。sourceの全numeric bitsはJS側の事前所有copyとも照合する。

## JSと受入

確定した入口は `runtime.querySphereTriangleMesh({position,radius}, triangles, {maxSurfaces,primitive})`。`maxSurfaces`の既定64、nested `primitive` は既存6設定 `maxCandidates,sqrtRefinements,maxTotalSqrtRefinements,maximumLocalWidth,maximumNormalWidth,minimumSineSquared` の既定・意味を継承する。6exportsの能力検出を入力書込前に行う。呼出し元の全入力を一度所有copyして検証し、そのcopyをchunk化する。途中でcallerが配列を編集しても入力を混ぜない。全行/全候補を取得・検査後、Native Resultに対応する所有DTOを返す。status/reason等は既存SDKと同じsnake_case文字列。原本triangleと行別query、failedIndex/firstFailedRow、全workとnearest区間/possibleSurfaceIdsを保持する。

各source/row/candidateの厳密count・enum/flag/index・元順/ID・原本bits・optional整合・全work総和と最小上下端・全候補ID条件を検査する。1行失敗を成功に隠したpacket、null queryをmissにしたpacket、候補削除/法線合成、不正末尾を拒否する。旧SDK/壊れた出力にJS幾何fallbackを追加しない。

最小実装順はC ABI交換とNative probe、JS decoder、pinned SDK再build、実WASM全bitsと独立有理数参照、公開検証。ローカルではNative48例をhost拒否とモデル結果へ実測分類し、実64面/最後の面と候補、複数chunk/失敗chunk後復旧、begin後の旧snapshot所有、異なるrecord/reset、atomic旧output保持を試験した。成功WASMのfixtureも独立Fractionと43変異へ通した。公開検証はまだ未確認である。

実buildで新6exportsを含む合計74、追加cpp/headerを含め57 source/headerを確認した。7通知はbyte不変だが、既設libc++のalgorithm.oがlinked memberとして1増加したためruntime集合不変とは記載しない。外部solver/package/素材、ライセンス選定は追加しない。手動集合ラボやゲーム接触を、この接続段階の完成と扱わない。

## 実装着手の記録

以下は新SDK build前の履歴で、現在の結果は次節へ分ける。

[SDK使用契約](SPHERE_TRIANGLE_MESH_SDK.md)へ入力例、stage/確定snapshotの別所有、全row/候補、unused KKT符号零、host拒否と受理したモデル失敗、copied DTOの扱いを記録した。C ABI headerとJS method/decoderを追加中で、主WASMの新export・bytes/hash、Native48入力からhost/実モデルへの分類、bit照合・独立参照・負例、公開受入はまだ未確定である。新しい原著図の枠幅やappend件数を、時間短縮やGPU性能の根拠にしない。既存単一面SDK68の受入は別の履歴として維持する。

## ローカル受入の確定

Native48入力は45実モデル（29成功/16意図した失敗＝6 row_failure＋10 preflight）と3 host拒否（65面begin・ID0/unsafe ID append）に分かれた。主WASM packet27160 / model20808 numeric bits、負の零4453件がNativeに一致した。実WASM独立Fraction2775成分と43改ざん拒否、新Native API18群/旧77群/全34CTest、専用10群を含むNode526skip0・構文・Web `1f40cf023bb8472f` / 46 modules・22 entryが成功した。旧単一面SDK22327/13432等の既存回帰も成功した。

SDKはWASM638777 B / SHA256 `a9424df2c00c9cbf9fb11a979e2c00b991cf17a9128a0ccb52ea86bbc8b871ec`、glue53435 B / SHA256 `d0b06ae80449622cd98df4df496447a552c4c6c31bfe7a656c08df9eae4aae18`。基準207aa60から保護対象62（C++原本55＋既存通知7）と全authored assets/game Sourceはbyte不変。意図したSDK3artifact・生成HTML変更と区別する。

linked memberに `libc++-debug-legacyexcept.a(algorithm.o)` が増加した。昇順uint64 ID sort/introsort用で、既設pinned source2718 B / SHA256 `32d0eded6a24dcf1e5d4968e7a8e9902b459084bbe08d681dc14bf093ce53f9a`、SPDX `Apache-2.0 WITH LLVM-exception`、既存LIBCXX-LICENSE.txtで通知する。[監査](../reports/sphere-triangle-mesh-sdk-runtime-audit.json)のmap抜粋と原本hashを根拠とし、新solver/package導入とはしない。

独立MSVC ASanはcompile未完了247.548秒/exit15、runtime未実行のNOT_COMPLETEDである。先行純粋核ASan59群と混同せず、公開GNUでのAPI cpp/新試験instrument＋通常核library、純粋核の別ASan検査はこれから受け入れる。ローカル実ゲーム3撃破/boost/停止・22照会全成功/3常駐mesh・新SDK読込みは旧機能互換で、新集合mesh接触の適用ではない。公開CI/Pagesは未確認。[統合報告](../reports/2026-11-04-sphere-triangle-mesh-sdk.md)と[使用契約](SPHERE_TRIANGLE_MESH_SDK.md)に根拠・限界を記録し、手動集合ラボを次の別受入とする。
