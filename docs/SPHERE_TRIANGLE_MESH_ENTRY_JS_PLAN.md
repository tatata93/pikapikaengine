# Entry-window所有JavaScript APIの次段案

2026-11-04 JST。**実装・ローカル受入済み、公開受入確認待ち**。[実装契約](SPHERE_TRIANGLE_MESH_ENTRY_JS.md)と[実測記録](../reports/2026-11-04-sphere-triangle-mesh-entry-js.md)を参照。以下は実装前に定めた受入計画であり、現在の再開位置はPLANを優先する。正式[raw C ABI](SPHERE_TRIANGLE_MESH_ENTRY_ABI.md)を使い、全診断を所有するJS decoderを追加する段階である。現86-export SDKのraw交換と、JSの通常API・UIを利用可能であることは別。raw C ABIコード4b03f0cの公開CI/Pages/実公開操作は受入済みだが、本計画のJS所有APIは実装・ローカル検証を完了し、手動編集UIは後続とする。

現物manifestは86 exports/hash対象61 source-header/7通知/runtime linked member91。WASM719,410B/SHA256 `d1ece57ca29df06e91cf10c7b598a9b073a86b63959d4ef76e2e0da5f84d5f58`、glue58,933B/SHA256 `7de3e5160b478aea5fcdc10cad4187e4641c592561414b1d99acaeb184562952`を読取確認した。ABI1、F64入力49,152/U32入力98,304/出力64は維持する。JS段でC++核・ABI・SDK artifact・ゲームを変更する計画ではない。

## 入口と一度だけの入力capture

公開method案は `SimulationRuntime.querySphereTriangleMeshEntry({start,end,radius},triangles,settings={})`。独立module案 `engine/sphere-triangle-mesh-entry.mjs` に交換/decoderを分離し、既存の[trajectory wrapper](../engine/sphere-triangle-mesh-trajectory.mjs)を原著の所有/入力方式として参照する。

settingsは`mesh:{maxSurfaces,primitive:{maxCandidates,sqrtRefinements,maxTotalSqrtRefinements,maximumLocalWidth,maximumNormalWidth,minimumSineSquared}}`、`parameterTolerance`とguard5項目。既定はNativeに合わせtol1e-6、maxEvaluations256/maxLeaves128/maxDepth24/enclosureSqrtRefinements128/maxTotalSqrtRefinements1000000。旧guardのdepth16やfrontier33を流用しない。

1. `_pp_sim_sphere_triangle_mesh_entry` と同prefixの `_begin/_append/_record/_last_mesh/_candidate` 全6関数を最初のinput書込前に検出する。旧80・一部欠損・loader rejectionを明示し、旧trajectory/瞬間mesh/JS幾何へfallbackしない。
2. 面数、各triangle、ID、vertices配列、3頂点参照、各数値成分を一度captureして検査/所有copyする。settings/endpoint/radiusも同じ値を検査とencodeへ使う。getter/Proxyが再読時に変わっても検査値とcopy値を食い違わせない。
3. 面数0..64、safe ID1..2^53−1、dense finite XYZ/半径/設定、整数設定uint32全域をhost交換域として検査する。空集合・重複・有限の域外/負半径/設定0等はNativeモデルへ通す。65面/ID0/unsafe/非有限/非整数は書込前に拒否する。
4. 全入力copy後に専用begin、最大6面ずつappend、query24。整数−0も元echo/所有設定では保持し、Native snapshot整数の正規化+0と分ける。reserved4値はstrict +0を生成する。数値条件・予算を自動で増やさない。

元native/export/prototypeを置換せず、元receiverで呼ぶ。memory growth後はscratch view/pointerを再取得し、各getter出力を次call前にcopyする。同期・非再入、同じmoduleの並行交換非対応を維持する。

## 返却するowned DTO

Native fixtureと同じ全数学・所有診断keysを基本に、enumは既存SDK同様string化する。

```text
status,reason,failedIndex,snapshot,initial,initialSeparationProven,
certifiedLeaves,safePrefix,bestWitness,window,candidateSurfaceIds,
partition,frontier,current,audits,lastMesh,lastMeshAuditIndex,
work,partitionLeaves,maximumDepth,
originalInput:{start,end,radius,triangles,settings,echo:[24]}
```

snapshotはNative flagが真のときだけ原echo/source/正規化settingsから復元する。C ABI側のbit照合を前提とし、snapshot:nullでもoriginalInputは残る。caller、originalInput、snapshot、lastMesh.rowsのtriangleを別所有にし、以前のDTOと後続query/scratchもaliasさせない。所有copyは全値を凍結して編集不能にすることとは区別する。可変message原文はraw wire同様対象外で、空文言を復元したふりはしない。

summary40と全recordを読む。audit256、certified island128、partition128、frontier128、source64、候補ID64、optional current/initial/witness/window、lastMeshの全64行/448候補を省略しない。lastMeshには既存mesh decoderのpure getter callback抽象を再利用できるが、旧global snapshotへ一時代入しない。source14 flagsとlastMesh.nearestは最後のmeshだけの所属で、entry面の同定ではない。

## metadataの厳密監査

各packetの正確な長さ、dense有限数、整数count、canonical0/1 flag、enum、optional、不在payloadとreservedの+0、全index/末尾を監査する。実原本/interval/unused KKT[-0,+0]を正零へ丸めない。全source/echoを入力bitsと比較し、完了するまで部分DTOを公開しない。

- initial auditは0番の`kind:initial_point`、parameter0/cell[0,0]/depth0。通常cellは幅正のglobal dyadic領域。初期停止current[0,0]を通常partitionへ強制しない。initialProofの両certificateとaudit link、初期strict正/負/境界分類を照合する。
- 初期正証拠だけでsafePrefix[0,0]が成立する。nullを0と解釈しない。certifiedLeavesは全証明islandであり、前方の未知を後方の成功で埋めない。全partitionは[0,1]のclosed連続被覆、state/auditIndex/blockedReasonを保持し、frontierは全unqueried葉と一致させる。bestU以後のtailも削除しない。
- 幅優先・同depth左順・bestUより前というeligible条件と、split/blocked/currentの履歴をmetadataとして確認する。失敗ancestorからproofを作らず、exact row_failureから子cellの新しい証拠へ進める意味を保つ。無auditの予算停止currentやfatal部分診断も未照会と区別する。
- Work11のdeltaと合計、実mesh/primitive/root calls、limited数、lastMesh所属を照合する。上限は256 mesh/16,384 primitive/114,688候補、primitive sqrt8,388,608・enclosure262,144・合計8,650,752、保守upper16,777,216。`workExact:false`は未知実行blockを含み得る既知work＋保守上限であり、0回/正確な測定へ変えない。
- windowは初期strict正、closed prefix[0,L]、bestWitnessのE込みstrict負、window両端/外向きwidth/parameterTolerance/所属audit、exact workを照合する。候補IDは全source IDの昇順保守集合。witness時のnearest IDsへ縮めない。separatedは全[0,1]strict被覆のみ。初期負はwindow無し。

これはwire/所有/metadataの監査である。JSで距離・sqrt・KKT・Lipschitz境界・Interval幅を再計算してC++証拠を代替しない。bounds順序や証明式のstrict符号は検査しても、その式が真の幾何を包含する数学的根拠はNative契約と独立Fraction参照に置く。任意に一貫した偽boxをJSだけで数学認証できるとはしない。

## 拒否と保持の境界

能力・入力preflight拒否は書込0で、旧Native stage/record/outputを保持する。C ABI自体のhost交換/getter拒否も既存の原子性を継承する。一方、正常queryは既に新Native recordをcommitしている。その後decoderが不正packetを見つけた場合はJS結果を返さずthrowするが、Native record/outputのrollbackは保証しない。以前に返したJS DTOの所有と不変性は維持する。rollback用ABIや隠れた再queryは追加しない。

## 次段の有限受入

1. 実86-WASMで新65原本の62モデル/3host拒否を目標に全件再生し、JS段の実内訳を測定する。raw Native147,638bits/実WASM146,130bitsの先行比較を、そのまま新owned DTO件数としない。全DTO型・keys・数値bits・−0・全optionalをpure Nativeへ照合し、旧trajectory62を新entry65へ混ぜない。
2. 全256audit/128partition/128frontier/64sourceと各末尾、preflightのsnapshot:nullと初期point失敗のsnapshot有り/initial:nullを区別する。初期負/境界、surface予算、対称通過の失敗祖先と成功子、連続prefixと後方island/tail、全保守IDを保持する。current初期点と通常cell、getter不在、失敗後成功/reset/他snapshotと時計の独立を実SDKで検査する。
3. 元入力/設定・snapshot/originalInput・旧/後続DTO・scratchを別々に改変し、所有分離を確認する。全6欠損、同期throw/rejected loader、count/enum/padding/flags/link/width/counter改ざん、accessor一度capture、旧80拒否の書込0を試す。人工exactfalse packetはdecoder試験と明記し、実allocation fault注入とは呼ばない。
4. 実WASMから復元した62モデルDTOを独立Fraction参照へ渡す。host拒否3件にpure Native補足を使う場合はmixed65として各行出自を保存し、全65を実WASMモデル計算と呼ばない。独立参照・負例・全旧Node/構文/Web・公開CI/Pages/配信byteの確認を分けて記録する。

次の手動entry UIは別計画とする。既存trajectory guardラボをentry UIへ読み替えず、World・TOI/応答・ゲーム接触へ接続したとはしない。新外部solver/素材/課金は追加せず、本体license未選定を維持する。
