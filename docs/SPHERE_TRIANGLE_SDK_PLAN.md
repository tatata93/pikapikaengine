# 球と静的三角形の有界SDK照会: 次の接続案

2026-11-04 JST。**設計のみ・未実装**。Nativeのread-only幾何照会と解析接続を受け入れた次の最小段階。既存ABI1/64 F64交換を維持し、主simulation SDKへ同じC++核を接続する。現在の66exports/592939B WASMに新照会を含めたとはしない。World/CCD/mesh manifoldや一般の区間→point impulse変換はこの計画の対象外。

## 交換形式の候補

新2exports `pp_sim_sphere_triangle(value_count)` / `pp_sim_sphere_triangle_candidate(index)`。入力24 F64、結果58 F64、候補1件13 F64。候補7件全部は91値になるのでordinal getterで取得し、今回batch機構を増やさない。

入力: 0..3=center XYZ/radius、4=surface ID、5..13=ABC頂点XYZ、14..16=maxCandidates/sqrt/maxTotal、17..19=maxLocalWidth/maxNormalWidth/minSin²、20..23=reserved zero。

| 結果offset | 内容 |
|---|---|
| 0..2 | status/reason/hasGeometry |
| 3..5 | surface ID / survivingFeatures / relation |
| 6..9 | candidateCount / examined / sqrtCount / limited |
| 10..12 | hasCross / cross bounds2 |
| 13..15 | hasSine / sine bounds2 |
| 16..21 | barycentric bounds6 |
| 22..27 | closestLocal bounds6 |
| 28..33 | closest world bounds6 |
| 34..39 | delta bounds6 |
| 40..45 | normal bounds6 |
| 46..51 | spherePoint bounds6 |
| 52..57 | distance² / distance / gap、各bounds2 |

Geometryは6×Bounds3で36値と3scalar intervalの6値、ID/mask/relation3を持つ。Result診断等を加えて58値に収まる。geometry不在ならhasGeometryで区別し、対応域はzero paddingへする。候補13値はfeature/disposition/kktCount3、barycentric6、kkt4。未使用KKTもC++の`[-0,+0]`を保ち、count0を理由に符号zeroを書き換えない。

## 失敗・所有・互換性

交換境界は厳密count24・全finite・reserved zero・uint32の整数設定・既存`id_from`を使う。uint32域内のモデル不正設定や有限radius不正はC++へ渡し、JSで成功/失敗モデルを合成しない。Native113例中のzero-id/unsafe-id2例はこの既存ID交換契約ではhost拒否となり、残111モデル結果と別に数える。

交換不正/候補範囲不正は前のsnapshotとoutputの有効prefix/count/bitsを保持する。hostが書くinput scratchの保持は約束しない。正常交換のモデル失敗はSDK交換として成功し、新たなgeometry-null記録へ更新する。全packetを準備してからpublishし、他のmotion/optics/skin/derived記録と独立にする。global resetで消去する。

completedは候補7/examined7。失敗はaudit追加前にexaminedが増える経路もあり、両者が常に一致するとは仮定しない。候補prefixを成功geometryとして扱わない。

JS案 `runtime.querySphereTriangle({position,radius},{id,vertices},settings)` は既存sphere APIのposition表記へ合わせ、元の値をC++へ渡す。入力交換前に新2exportsを検出し、旧SDKは明示拒否。plane/AABB/JSの代替接触計算をしない。全finite/enum/flag/件数/順序・tailを検査後に所有copyを返す。

## 次の受入

Native ABIの交換拒否/古いoutput保持、モデル失敗への更新、候補範囲/末尾、reset/他snapshot独立。113入力の全実行分類、111モデルのNative/WASM全numeric bitsとsigned zero、独立有理数の包含検査、壊れたDTO/flag/countへの負例をそろえる。配布SDKの来歴/通知と新export件数も再記録する。ブラウザの手動照会やゲーム適用は、このSDK接続後に別の有限受入として進める。
