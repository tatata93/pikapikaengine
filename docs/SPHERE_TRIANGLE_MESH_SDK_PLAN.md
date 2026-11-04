# 三角形集合の共有SDK: 次の有界接続案

2026-11-04 JST。**設計のみ・未実装**。Native最大64面の受入後、既存ABI1/64 F64交換で全原本と全行診断を運ぶ。現行68-export SDKはこの集合照会に未対応。World/CCD/応答・ゲーム適用は別段階。

## 64値を超える入力を所有する

三角形1枚はIDと9座標の10値で、64枚は640値になる。一回の64値交換へ押し込まず、runtimeごとに一つの有界stagingを追加する。resource handleやWorld資源は追加しない。begin/appendは入力準備であり、照会完了とはしない。

新しい6exportsの案:

- `pp_sim_sphere_triangle_mesh_begin(uint32_t triangle_count)` — 0..64を受理し、空の新stagingを用意。直前の照会snapshotとoutputは保持。65以上の交換拒否はstagingも保持する。
- `pp_sim_sphere_triangle_mesh_append(uint32_t value_count)` — input scratchの10..60値、10の倍数（1..6枚）を元順に追加。id/ABC XYZ。未begin・予定数超過・不正count/ID/非有限は拒否し、追加前stagingと照会snapshot/outputを保持。chunkを全部検査してから所有copyを交換する。
- `pp_sim_sphere_triangle_mesh(uint32_t value_count)` — 完成したstagingと入力14値から実Native query。未begin/予定数未達を交換拒否し、前snapshot/outputを保持。正しい交換のモデル失敗は新しいnearest-null記録へ更新。stagingは再照会用に保持する。
- `pp_sim_sphere_triangle_mesh_source(uint32_t ordinal)` — 照会時原本を所有した記録から14値。後のbegin/appendに追従しない。
- `pp_sim_sphere_triangle_mesh_row(uint32_t ordinal)` — 実照会済みrowの既存単一面形式58値。row不在/null queryは交換拒否し、他面の結果で代用しない。
- `pp_sim_sphere_triangle_mesh_candidate(uint32_t row, uint32_t ordinal)` — 当該実rowの候補13値。単一面照会snapshotとは独立。

0枚はNativeのsurface_count拒否を検証できる入力として渡す。重複IDや有限だが域外の座標はNativeの事前拒否に任せる。IDは既存交換契約の正safe整数に従い、NativeのID0/unsafe例はhost拒否として別集計する。uint32設定は整数域を交換検査し、域内の不正モデル値をJSだけで分類しない。

stagingと最終snapshotは別所有。appendは先行chunkまでの有効な原本を、後続不正chunkで壊さない。queryは全packet検査/有限性/診断整合を終えてから一回でcommit/publishする。他のsingle/optics/motion/skin/derived記録は保持し、global resetでstagingと集合snapshotを消す。割当失敗の強い保証は実装のmove/swap/publish順で検査し、未実施のfault injectionを実施済みとしない。

## 交換packet案

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

入口案は `runtime.querySphereTriangleMesh({position,radius}, triangles, settings)`。6exportsの能力検出を入力書込前に行う。呼出し元の全入力を一度所有copyして検証し、そのcopyをchunk化する。途中でcallerが配列を編集しても入力を混ぜない。全行/全候補を取得・検査後、Native Resultに対応する所有DTOを返す。status/reason等は既存SDKと同じsnake_case文字列。原本triangleと行別query、failedIndex/firstFailedRow、全workとnearest区間/possibleSurfaceIdsを保持する。

各source/row/candidateの厳密count・enum/flag/index・元順/ID・原本bits・optional整合・全work総和と最小上下端・全候補ID条件を検査する。1行失敗を成功に隠したpacket、null queryをmissにしたpacket、候補削除/法線合成、不正末尾を拒否する。旧SDK/壊れた出力にJS幾何fallbackを追加しない。

最小実装順はC ABI交換とNative probe、JS decoder、pinned SDK再build、実WASM全bitsと独立有理数参照、公開検証。Native48例をhost拒否とモデル結果へ実測分類し、実64面/最後の面と候補、複数chunk/失敗chunk後復旧、begin後の旧snapshot所有、異なるrecord/reset、atomic旧output保持を試験する。成功WASMのfixtureも独立Fractionと43変異へ通す。

新6exportsなら合計74、追加cpp/headerを含め57 source/headerという予定だが、実buildのmanifest/exports/hash/通知と実測件数で改めて確定する。外部solver/package/素材、ライセンス選定は追加しない。手動集合ラボやゲーム接触を、この接続計画の完成と扱わない。
