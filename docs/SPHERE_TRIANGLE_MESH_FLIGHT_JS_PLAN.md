# 保持荷重/自由伝播guardの所有JS API計画

2026-11-04 JST。**未実装の次段計画**。raw C ABIの全wire/独立参照とコード4e422ddの公開受入は成功した。本JS計画は未実装である。初回Nativeは200群・183入力、173 actual model/10 host拒否を確認したが、この件数をJS所有APIやWASM計算の成功件数へ転用しない。SDK再build・raw WASM照合の最終結果は別のreportで確定する。

本段は[正式C ABI案と実装](SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md)の6関数を利用する。新JS module候補は`engine/sphere-triangle-mesh-flight.mjs`、`engine/simulation.mjs`にはimportと2公開methodだけを追加する。C++核/ABI/SDK artifact/既存wrapper/World/ゲームは変更しない。手動UIは別段とする。

## 正式な入口案

```js
runtime.querySphereTriangleMeshHeldLoad(sphere, triangles, horizon, settings = {})
runtime.querySphereTriangleMeshFreeFlightGuard(body, gravity, triangles, horizon, settings = {})
```

`horizon`は元binary64の秒であり、normalized parameterやWorld tick数ではない。

- `sphere`は全必須の`{id,position:[3],velocity:[3],mass,force:[3],gravity:[3],radius}`。元の力・重力・質量を送り、JSでF/mを計算しない。
- `body`はNative fixtureと同じ全必須field: `{id,isStatic,mass,radius,inertiaDiagonal:[3],position:[3],orientation:[4],velocity:[3],angularMomentum:[3],force:[3],torque:[3],material:{restitution,friction}}`。`isStatic`はbooleanで、他のbody数値は有限を要求する。既存World DTOの`inertia/linearVelocity/flat material`を暗黙受理せず、既存`bodyInput()`/`bodyResult()`へfallbackしない。既定慣性・既定速度・未指定torqueの補填は禁止。World DTOから使う必要があれば全fieldを明示する別owned変換として試験する。
- `triangles`は`[{id,vertices:[[3],[3],[3]]}]`。0..64、safe ID、全頂点有限の交換域を検査する。65面/unsafe ID/非有限は書込前拒否、空集合/重複/有限domain外はNativeモデルへ通す。

held settingsはNativeと同じ`mesh:{maxSurfaces,primitive:{maxCandidates,sqrtRefinements,maxTotalSqrtRefinements,maximumLocalWidth,maximumNormalWidth,minimumSineSquared}}`、`timeTolerance,maxEvaluations,maxLeaves,maxDepth,enclosureSqrtRefinements,maxTotalSqrtRefinements`。既定はtol1e-7 **秒**、256/128/24/128/1,000,000、mesh64、primitive7/128/1024/1e-7/1e-8/1e-12。guard settingsは`{heldLoad:上記,maxAngularIncrement:.5}`で固定する。

整数設定はuint32全域を交換し、0や最大値等のモデル無効値をJSで成功用設定へ修正しない。設定整数−0はoriginalInput/echoで保存し、Native型変換後の+0と区別する。位置/q/力など全実数の−0も保存する。body booleanからencodeするstatic flagは+0/1。raw ABIが受理するstatic flagの−0はraw段の試験であり、boolean APIでそのbitを入力できたとは主張しない。

## 書込前captureと能力検出

1. `_pp_sim_sphere_triangle_mesh_flight_begin/_append/_query/_record/_last_mesh/_candidate`の**全6能力**を最初のinput書込前に検出する。旧86-export SDK、一部欠損、同期loader throw/rejected loadを明示して拒否する。旧entry/trajectory/瞬間meshやJS幾何へのfallback、隠れた再queryは禁止。
2. 入力object/各field/配列length/triangle ID/vertices参照/各頂点参照/数値成分を一度captureし、同じ値を検査・copy・encodeへ使う。settingsの各階層も一度captureする。getter/Proxyが再読時に別の値を返しても、検査と書込の値を食い違わせない。
3. dense配列または明示対応する数値typed viewの正確な長さを確認する。hole/undefined/DataView/非数値/不正boolをfiniteのように扱わない。全入力copy完了までNative stageを触らない。
4. mode0はinput32、mode1はinput48、sourceは6面以下ずつappendする。reservedはstrict +0。original echo/sourceとNative snapshotを別所有し、途中のhost拒否で旧stage/record/output/countを壊さない。

元runtime/native/export/prototypeを置換しない。元receiverを保ってNativeを呼び、memory growth後はptr/viewを再取得し、getter出力は次call前に全件owned copyする。scratchはmodule共有で同期・非再入。同じmoduleへ並行交換する利用は対象外と明記する。

## 全所有DTOと所属

返却はNative fixtureの数学/所有診断keysを保ち、enumを既存SDKと同様string化する。可変message原文はwire非対応であり、空文字を復元したふりはしない。初回Native/WASMの固定result projectionを正式decoderの比較対象にする。

held DTOは`status,reason,failedIndex,snapshot,worldBody,acceleration,wholePathBounds,wholeVelocityBounds,initial,initialSeparationProven,certifiedLeaves,safePrefix,bestWitness,window,candidateSurfaceIds,partition,frontier,current,audits,lastMesh,lastMeshAuditIndex,work,partitionLeaves,maximumDepth`を保持する。

guard DTOは`status,reason,failedIndex,worldBody,snapshot,tube,flightFailure,candidateEvaluated,endpoint,inflated,candidate`を保持する。Tubeはnominal/exact Aとdifference、B/roundoff/guardRadius、Endpointは5つのBounds3・L1区間・3監査flagを欠落なく持つ。candidate/worldBodyは全28fieldのNative形で、paddingをomega/energy/time/tickへ解釈しない。

追加原本はheldで`originalInput:{sphere,horizon,triangles,settings,echo:[32]}`、guardで`originalInput:{body,gravity,horizon,triangles,settings,echo:[48]}`とする。caller、originalInput、Native snapshot、worldBody、candidate、inflated snapshot、lastMesh.rowsのtriangle、旧/後続DTOを互いに別所有にする。元入力の編集、返却DTOの編集、scratch上書き、別mode照会後も他の所有物を変えない。

元guard snapshot/bodyのradiusとnested inflatedのradiusは違う。後者はTube.guardRadiusで、元P/V/F/m/g/H/settingsは対応する。guardの外側成功は`certified_separated`のみ。nested entry/initial penetrationは外側未認証の診断であり、元球の物理entryへ昇格しない。失敗時のcaptured invalid bodyも有限なら診断として読む。成功candidate用の物理検証をworldBodyへ再適用してモデル失敗をdecoder例外に変えない。

## 全21kindとmetadata検査

summary24、kind0..20を正式headerどおり読む。input/native snapshot32/48、source14、heldHeader48、heldInput32、worldBody32、Tube24、Endpoint40、candidate32、A/path/velocity各8、audit64、leaf6、partition8、frontier/current4、initial6、witness18、window14、全ID2を扱う。optional不在はnull、未照会は未照会として保持し、空/0へ補填しない。

- 全packetの正確な長さ、dense有限、enum/count/safe ID、canonical正零のmetadata/flag/padding、不在payloadを確認する。区間の順序と原本/interval/unused KKTの−0は保存する。nested row58/candidate13にも同じdense/metadata検査を適用する。
- 各mode専用recordのecho/sourceはcaptured input bitsと一致させる。型変換済snapshotの整数/static正準化だけを分離する。heldHeader.worldBodyはmode0 raw/mode1 nestedとも0、外guard.worldBodyのflagは別に扱う。
- 全256audit、128leaf/partition/frontier、source64、全候補ID64、全lastMesh64row/448candidateを読む。最終meshとlastMeshAuditIndexの所属を検査し、source末尾flag/nearestをentry面や衝撃点へ転用しない。
- cellは元global秒`[0,H]`。initialはaudit0/kind initial_point/time0/cell[0,0]、initial停止currentも通常cellと分ける。全partitionのclosed連続被覆、BFS/同depth左順、blocked/current/未照会、prefix後方の島と全tailを保持する。半径/時間をscene単位へ暗黙変換しない。
- prefixは初期strict正と0から連続するcertified leavesだけで延ばす。windowはprefix L/E込み負witness U/外向きtimeWidth.upper<=timeTolerance/全ID/所属を照合する。window.pathBounds/L1Diameterは別のメートル診断であり、秒幅から空間誤差を推定しない。
- Work11のaudit delta/合計、known/upper、calls/returned roots/limited/lastMesh workを照合する。exact=falseの未知mesh N*512、未知R/E known+512の予約を消さず、0回/正確な測定/成功へ変えない。Nativeが返したpartial allocation failureも情報を落とさない。
- Tube/Endpoint/実candidate/H/originalとinflatedのmetadataリンク、candidate成功only、force/torque保持、global bounds有無/実行順を確認する。squared/L1区間の微小負lowerは合法で、非負rootの条件と混同しない。

JSは距離・KKT・F/m・B・sqrt・区間の幾何包含を再計算しない。数値boundの数学的正しさはC++契約と独立Fraction参照へ置く。一貫した偽boxをJS metadataだけで数学認証できる、と主張しない。

## 失敗境界

capability/入力preflightは書込0で旧Native状態を保持する。C ABIのhost交換/getter拒否は旧stage/record/output/count保持を継承し、モデル失敗は新失敗DTOとして返す。query正常publish後にdecoderが不正packetを発見した場合はthrowし部分DTOを返さないが、既に更新されたNative recordのrollbackは保証しない。以前返したJS DTOの所有は保持する。再queryによる復旧を黙って実行しない。

## 次段の受入

1. 現段の183完全入力（held79/guard100/補足4）を固定原本として再生する。ただし各cohortのhost/model内訳と入力fingerprintは**正式raw reportから取得**し、新owned実行後の実数を保存する。初回Native173/10や前のraw bit数を新JSの実行件数へ転用しない。
2. 実新WASMでacceptedモデルの全DTO keys/型/数値bits/−0と全wireを固定Nativeへ照合する。拒否行はhost出自を保存し、Native結果で埋めて全183をWASMモデル計算としない。実WASM由来モデルDTOだけを独立held/guard Fraction `verify_fixture`へ渡し、正例/負例/fingerprintを固定する。
3. capacity・失敗・両mode・全21kind末尾、mode/recordを交錯した所有、captured invalid body/static/回転失敗/膨張radius域/entry未昇格、初期snapshot null/有り、island/tail/current、全ID/lastMesh候補を実APIで検査する。旧World/body/time/tick、旧entry/trajectory/他recordも照会前後一致を確認する。
4. 全6欠損/旧86の書込0、原本accessor各一度（有効→不正/不正→有効）、sparse/型/uint/予約、header/kind/padding/flags/count/link/seconds幅/原半径−膨張所属/candidate成功flag/Work予約を改ざんして拒否する。元receiverのブランドとmemory growth後copyも検査する。
5. 実WASMでは環境変更操作が利用できないことがある。raw Nativeのunsupported-environment証拠を別保持し、WASM/JSの人工unsupported/exactfalse/partial allocation packetはdecoder試験と明記する。実fenv/faultを変更した証拠と混ぜない。
6. SDK source/artifact/prototype/元method不変と全旧Node/構文/Web/回帰を再確認する。raw HEAP capacityは確保済memory長であり、queryの実使用heap/stack高水位ではない。未計測の使用量・速度・60fpsを主張しない。既存64/256MiB・stack1MiBのまま実測範囲を分けて記録する。

新APIはread-only予測照会である。Worldを進める/接触を解く/時計を進める・荷重を消費する機能ではない。all-pair順序、manifold/反発/摩擦支持、残時間と累積丸め、ゲーム適用・次の手動UIは後続の受入に残す。license未選定と一般物理/流体/損傷/専門モデルの未完scopeも維持する。
