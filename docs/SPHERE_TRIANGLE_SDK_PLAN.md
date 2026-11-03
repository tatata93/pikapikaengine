# 球と静的三角形の有界SDK照会: 接続計画と受入

2026-11-04 JST。**実装・ローカル統合検証済み。公開CI/Pagesは未確認**。既存ABI1/64 F64交換を維持し、Nativeのread-only幾何照会を同じC++核のまま主simulation SDKへ接続した。68exports/612824B WASMとJSの所有DTOをローカル受入済み。直前の66exports/592939B WASMに新照会を含めたとはしない。World/CCD/mesh manifoldや一般の区間→point impulse変換はこの計画の対象外。末尾に設計・着手時の履歴と確定した受入結果を分けて記録する。

## 実装した交換形式

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

JS入口 `runtime.querySphereTriangle({position,radius},{id,vertices},settings)` は既存sphere APIのposition表記へ合わせ、元の値をC++へ渡す。入力交換前に新2exportsを検出し、旧SDKは明示拒否。plane/AABB/JSの代替接触計算をしない。全finite/enum/flag/件数/順序・tailを検査後に所有copyを返す。

## 接続の受入項目（下記ローカル受入で実施）

Native ABIの交換拒否/古いoutput保持、モデル失敗への更新、候補範囲/末尾、reset/他snapshot独立。113入力の全実行分類、111モデルのNative/WASM全numeric bitsとsigned zero、独立有理数の包含検査、壊れたDTO/flag/countへの負例をそろえる。配布SDKの来歴/通知と新export件数も再記録する。ブラウザの手動照会やゲーム適用は、このSDK接続後に別の有限受入として進める。


## 実装着手時の状態（2026-11-04 JST）

以下は着手時の履歴であり、現在の実装状態ではない。

Native単独段階の公開CI/Pages受入後、上記24/58/13のC ABIとJS decoderへの接続に着手した。**本計画を実装済み・受入済みへ変更するのは親の検証結果を受けてから**とする。現時点の新artifact bytes/hash・全試験件数は未確定で、旧66-export SDKを新照会対応と扱わない。

準備中の[SDK使用契約](SPHERE_TRIANGLE_SDK.md)に入力例・失敗/所有・unused KKT符号零・Native113から111モデル/2host拒否への分類を記録する。JS methodは `querySphereTriangle({position,radius},{id,vertices},settings)`、設定keyは `maxCandidates,sqrtRefinements,maxTotalSqrtRefinements,maximumLocalWidth,maximumNormalWidth,minimumSineSquared` に確定し、decoder原本を追加した。messageを除くNative相当camelCase DTO、status/reason/relation/feature/dispositionのsnake_case文字列、常に2区間のKKT符号零を保持する契約である。主WASMはまだbuild/検証前であり、API確定を実行成功としない。来歴/7通知/新SDKとNativeの全bits・独立参照・旧record保持を受け入れた後に、この段階の実装状態と次の受入を改めて記載する。

## ローカル受入の確定（2026-11-04 JST）

入力24/結果58/候補13の2exportsとJS decoderを実装し、実際の68-export主WASMで受け入れた。Native cpp/headerはbyte不変。Native API77群・全32CTest、Node502/502（skip0）、構文、Web build `f7448823095f375b` / 45 modulesが成功した。初回Node500/502は、先行した報告リンク未作成とprofile CLI試験の旧source53/export66固定が原因だった。報告作成とmanifest/hash/headerの実列挙比較への更新後、全502件を再実行した。

Native113入力を111実C++モデル（88 completed / 23意図した失敗）と2 ID host拒否に分類した。actual主WASMのraw packet22327 numeric bitsとJS projected model13432 numeric bitsがそれぞれNativeに一致し、符号零比較3472件を保持した。実WASMの88 geometryを独立Fraction1848成分で監査し、23改ざん負例も拒否した。host拒否をモデル結果へ補填せず、Native出力をWASM結果として流用していない。使用契約の3-4-5配置も実WASM専用試験で成功した。

SDKのsource/headerは合計55原本、WASM612824 B / SHA256 `eff93890e4dcf6387ba9fe55e5b15e38f4db817f68dfd112bb1ba503b78fb90d`、glue51085 B / SHA256 `0d541bc399cbdd6b55e7f2f848479acd39af408d2dec5b4379d8b1b09fb0a7d0`。全DTO・ABIの利用契約は[SDK文書](SPHERE_TRIANGLE_SDK.md)、原rawと再現条件は[SDK統合報告](../reports/2026-11-04-sphere-triangle-sdk.md)を参照する。

公開CI/Pagesはまだ未確認。ローカルの既存ゲームREADY・出撃/boost20 query全成功・3 resident meshは互換受入であり、ゲームへ三角形接触を適用した意味ではない。次の最小受入は、入力編集・失敗/候補区間の検査・JSON保存を行う**手動ブラウザtriangle lab**である。World/CCD/mesh manifold・一般形状の接触応答は引き続き別段階とする。
