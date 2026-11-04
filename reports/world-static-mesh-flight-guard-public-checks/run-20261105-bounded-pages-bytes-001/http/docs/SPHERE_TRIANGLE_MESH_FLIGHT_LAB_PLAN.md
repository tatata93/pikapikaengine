# 保持荷重/自由伝播guardの手動ラボ計画

2026-11-04 JST。**次のUI受入案・未実装**。現所有JS段の最終統合/公開状態はPLANと当該reportを優先する。この文書はラボの実行・公開・性能を証明しない。[所有JS契約](SPHERE_TRIANGLE_MESH_FLIGHT_JS_PLAN.md)と[raw SDK契約](SPHERE_TRIANGLE_MESH_FLIGHT_SDK_PLAN.md)を使い、既存entryラボとは別の入口を作る。URL候補は`tools/sphere-triangle-mesh-flight-lab.html`。このUI段では現92-export SDK、C++/全数値核、既存game/assets/旧labをbyte保護する。

## 二つのモードと入力

実計算は現在のowned APIを一回だけ呼ぶ。

```js
runtime.querySphereTriangleMeshHeldLoad(sphere, triangles, horizon, settings)
runtime.querySphereTriangleMeshFreeFlightGuard(body, gravity, triangles, horizon, settings)
```

入力はstrictなtagged unionとする。

```text
held:  {mode:'held',sphere:{id,position3,velocity3,mass,force3,gravity3,radius},
        triangles:[{id,vertices:[3x3]}],horizon,settings:HeldSettings}
guard: {mode:'guard',body:NativeBody,gravity3,triangles:[...],horizon,
        settings:{heldLoad:HeldSettings,maxAngularIncrement}}
```

NativeBodyは全必須の`id,isStatic,mass,radius,inertiaDiagonal,position,orientation,velocity,angularMomentum,force,torque,material:{restitution,friction}`。旧World DTOの`inertia/linearVelocity/flat material`や推定慣性/速度0へ暗黙変換しない。HとtimeToleranceは秒、P/radius/B/距離はm、massはkg、forceはN、torqueはNm、Lはkg m²/s。heldの数学pathは厳密実数`g+F/m`、guardのBは既存自由伝播の並進operation graphとの誤差上界であり、二つを同じ成功意味へ潰さない。

入力codecは既存strict JSON方式でduplicate/unknown key、非有限/overflow、不正Unicode、欠落field、array hole相当を拒否し、signed zeroを保存する。初期予算案は128KiB/depth16/24000nodes。省略設定はundefined相当だけをNative既定へ補完し、明示nullを既定へ変えない。既定時間幅1e-7s、評価256/葉128/depth24/root128/全sqrt1,000,000を表示する。予算/品質値の自動増加や入力縮小は禁止。

空集合/重複/有限モデル域外/不良bodyは実APIへ渡しモデル結果を表示する。65面/unsafe ID等のhost拒否を切詰めない。JSON形式、loader/能力、host交換、モデルstatus、描画/保存の失敗を段階別に表示する。旧86/6能力欠損はNative書込前に拒否し、旧API/JS幾何へのfallbackを使わない。

## 固定presetと証拠の出自

約24～30の代表を、正式raw/owned受入の**凍結183入力**からmode/cohort/fixtureNameの組で選ぶ。Native raw inputの全数値bitsを再現し、原本Receipt・input fingerprint・入力JSONのSHAを実装開始時に固定する。fixtureNameへ分岐して期待結果を表示せず、実APIを呼ぶ。外部fileをruntime fetchしてfixtureを生成しない。

選択候補（網羅するために追加できるが、値/角度/品質を成功都合で変更しない）:

| mode/cohort | exact fixtureName候補 | 受入の意味 |
|---|---|---|
| held | static-face / analytic-chord-false-collision | 全Hのstrict非接触、端点chord判定との違い |
| held | analytic-chord-false-safe-force-gravity / analytic-edge-quartic / analytic-vertex-quartic | 実force/mass/gravityのentry、面/辺/頂点の独立解析 |
| held | analytic-irrational-minimum-safe / analytic-irrational-minimum-entry | 単なるendpoint例でない四次距離の基準 |
| held | force-mass-cancellation-not-point / analytic-tangent-no-negative | 係数相殺・負witness無しを未認証に保持 |
| held | initial-strict-negative / initial-boundary | 初期負と新規entry・初期strict正無しの区別 |
| held | actual-256-audits-128-leaves / breadth-frontier-budget | 最大256audit/128partitionと全未照会tail |
| held | actual-64-entry-all-conservative-ids / middle-degenerate-later-row-preserved | 全64source/全保守ID・失敗面後の実row |
| held | signed-source-zero / sqrt-reservation-before-mesh | −0と初期未照会/予算prefix |
| guard | safe-face-held-rotation / safe-edge / safe-vertex | 候補の全6DOF/荷重保持、丸めtube込み安全 |
| guard | safe-cancelled-nominal-acceleration / non-dyadic-global-seconds | nominal/exact A・実global秒を区別 |
| guard | inflated-entry-is-not-original-entry / inflated-radius-over-domain | 膨張球の窓を元球の接触へ昇格しない |
| guard | rotation-increment-failure / candidate-final-validation-failure | 数学path以外の実candidate失敗 |
| guard | invalid-body-quaternion / static-body-unsupported | captured不良body/静的未対応の全診断 |
| heldまたはguard | 65-source-rejection（guardはheld-input- prefix） | 原本65面のhost拒否、model packetを捏造しない |

最終preset名/件数はNative原本照合後に固定する。補足4を使う場合もcohort=`supplemental`を保持する。signed zeroを消す通常のJSON.stringifyを生成recipeへ使わず、既存strict codecまたは厳密な数字字句からsourceを生成し、開発時のrecipeと全input bits照合を保存する。raw static flag−0の受入とJS boolean isStatic=falseの原本を混同しない。

既存独立Fraction/RN参照は数学的出自であり、図の見た目を証明にしない。全presetを成功させる受入にはせず、各mode/status/hostの実内訳を測定して保存する。

## 状態の表示と全診断

非接触を緑で表示できるのはheld `separated`とguard `certified_separated`だけ。held `entry_window`は証明された開始窓として別表示し、運動/応答成功ではない。initial_penetration、not_certified、invalid_input、unsupported_environment、numerical_failure、host/loader拒否を安全やmissへ変えない。reason・failedIndex・実段階をそのまま表示する。

- heldはoriginalInput/native snapshot/worldBodyの有無、acceleration/wholePath/wholeVelocity、initial、全audit、safePrefixと全certified islands、全partition/frontier/current、witness/windowとtimeWidth/pathBounds/L1Diameter、全保守ID、Work、lastMesh全row/candidate/所属を表示・保存する。`null`と`[0,0]`、未照会と失敗queryを分ける。
- guardは元body/gravity/H/settings、Tubeのnominal/exact A/difference/B/roundoff/guardRadius、Endpointの5bounds/L1/3flag、flightFailure、candidateEvaluated、nested inflatedの全held診断を保持する。成功candidateは全28fieldと保持force/torqueを表示し、失敗時は過去candidateを残さない。
- 元radiusとguardRadius、元snapshotとinflated snapshotを専用欄で併記する。nested `entry_window`があっても外側がnot_certifiedなら未認証のまま。worldBodyの不良q等は有限失敗診断であり、成功candidateの検証と混同しない。
- 初期込み最大256audit、全128leaf/partition/frontier、64source/保守ID、lastMesh64row/448候補の末尾まで選択できる。表示を省略する場合も明示page選択で全件へ到達でき、JSONを切詰めない。Workはdelta/aggregate、known/upper、exact/unknown reservationを分ける。
- 閲覧対象はheldまたはguard.inflatedと明示する。lastMeshAuditIndexと選択auditが一致するときだけclosest/normal等を重ね、別所属ならそう表示する。全部の法線を平均したり、保守IDをnearestへ縮めたりしない。

人工unsupported/exactfalse/partial allocation DTOは表示・decoder試験として追加できるが、自然presetや実fenv/fault注入の証拠と別にする。optionalがないことを旧表示の再利用で埋めない。

## 図は表示用proxy

XY/XZ/YZへ入力mesh/初期中心、実SDKのwhole/audit/point bounds・anchor、成功candidate中心を説明表示する。UIにF/m、距離/KKT/sqrt、接触solverや証明用Intervalを実装しない。任意anchor/box中心を真のp(t)へ昇格しない。曲線を描く場合もSDK返却点/boundsを結ぶ**表示proxy**に留め、真の軌道や安全証明とラベルしない。追加queryで描画sampleを増やさない。

時間帯は元[0,H]秒、initial、全partition/state/blocked、全島、連続prefix、witness/window、current、全tailを分ける。数値L/U/timeWidth/tolを併記し、最小1pxのink拡張は表示専用と記す。timeToleranceを空間誤差へ換算しない。巨大座標/極小時間を有限描画へ変換できなければ図だけ明示拒否し、数値結果・status・保存を維持する。図はWorld/GPU精度や性能の証拠ではない。

## 編集・実行・世代の受入

手動参照ラボとしてrun一回につき選択modeの実API一回、連続再生無し。初期load/preset/reset/retryの自動一回を採る場合は現在のcaptured inputが未編集である世代に限定し、query数を試験する。projection/audit/面/候補選択はquery0。

mode変更・入力編集・preset/reset・retry開始時に旧summary/geometry/candidate/全表/時間帯/JSON/save可能状態を**即消去**する。modeを変える際に旧World DTOやsphereから必要fieldを黙って合成しない。最後の実行input、現在のeditor、dirty、run generationを区別し、旧成功の緑を現在入力の結果として表示しない。

loadはPromiseでcoalesceし同期throw/rejectedから復帰できる。retry開始時に旧runtime/metadataを無効化する。load中編集、二重retry、入力mode/presetの切替、破棄/pagehide後の遅延callbackで旧結果を復活させない。getStateは最後にdisplayしたowned packetのcopyまたはnull。disposeはhandler・保存を無効化する。実装時にcontroller/export/DOM IDをUIとtest担当間で先に固定し、旧labをimportしてauto-initしない。

## strict保存と実Blob

full packet案はschema1/kind=`sphere-triangle-mesh-flight-lab`、mode、補完済みinput、実full result（originalInput込み）、SDK/build diagnostics、viewのprojection/inspectedAudit/inspectedOrdinal/inspectedSurfaceId。空の選択はnull。モデル失敗DTOも保存でき、loader/host拒否を偽モデル結果として保存しない。

strict serializerは8MiB/depth32/1,000,000nodesを初期予算案とし、**最終LFを含むUTF8 bytes**で上限/超過を検査する。非有限・循環・予算超過を明示拒否し、診断/末尾/負零を切らない。表示JSONとBlobは同じowned captured packetから作る。

実ブラウザで少なくとも2回、成功full packetと失敗full packet（nested entryまたは不良body診断を含む）を実Blob/downloadする。downloadされたfileのbytesを取得し、strict再読込→型/keys/全数値bits/−0/optional/viewがdisplayed packetと一致することを確認する。callback stubだけの成功を実ダウンロードと呼ばない。入力だけの別saveボタンを加えるなら同じ原本照合を追加し、最小受入に必須ではない。

## 有限検証と後続依存

1. 固定preset全input bitsを原183 corpusへ照合し、実92 SDKの直接owned APIとUI full DTO/JSON/実downloadを全数比較する。host/modelの内訳と出自を別保存し、Native結果でWASM拒否例を補填しない。
2. Node実SDK/DOMで全status/optional/capacity/末尾、原本不変・別所有、編集即消去、閲覧query0、loader世代/失敗後復帰/dispose、codec/最終LF上限/2Blobを検査する。人工packetの表示試験は別記録。
3. old92 SDK/core/既存game/assets/oldlabsの保護hash、全Node/構文/Web、必要な旧raw/owned/math回帰を確認する。新UIだけの都合でSDKを再生成せず、課金/外部素材追加無し、本体license未選定を維持する。
4. 実local/publicブラウザ、公開CI/Pages、配信byte、旧ゲームの通常操作を別証拠にし、初回失敗rawを保持する。未測定heap/stack/速度や60fpsの保証を追加しない。

ラボ後の物理依存は、静的meshを実Worldへ所有させる形状/lifetime/全pair監査、元球の接触窓の順序付けと残時間/累積丸め、面/辺/頂点・複数候補からの妥当な接触/manifold、摩擦/反発/支持、transactional tickと一回の荷重消費の順に設計する。区間normalのmidpointをpoint impulseへ落とすだけの接続は受入にしない。まずread-only全pair free-flight guard等の不足証拠を整理し、step/responseは独立解析・保存量/仕事・rollbackを揃えてから追加する。

本UIは一般接触、World advance/物理応答、車両/航空/鉄道、流体、損傷、関節/制御の完成ではない。既存最上位scopeを縮めず、数値核→実状態との証明→安全な応答→制作利用という依存順で進める。
