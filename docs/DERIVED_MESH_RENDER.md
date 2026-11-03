# 監査済み局所メッシュの手動3D表示

2026-11-04 JST。**実装・ローカル/公開検証済み**。以下は固定した実装契約で、ローカルの最終試験数・実GPU操作・配信物の照合は根本の受入記録で確定する。[局所CPU核](DERIVED_MESH.md)と[SDK接続](DERIVED_MESH_SDK_PLAN.md)の後段として、小さい成功bufferを既存WebGPU rendererへ渡す。原本形式、C++核、SDK65exports、robot/game原本は変更しない。

## 原本から表示まで

[スキン原本の制作ラボ](../tools/skin-binding-lab.html)で、原本を読み、必要な時刻の「位置を計算する」を実行する。「Float32位置と法線を監査」で共有C++へ照会し、全体がcompletedになった場合だけ「監査済みメッシュを3D表示」を使える。

位置・面積・法線の計算と3D表示は別の操作である。視点の変更では既存の成功bufferだけを描き直し、C++のFK/LBS/派生監査を繰り返さない。毎frameの参照計算、実時間animationやゲームへの変形適用はこの段階に含めない。元のXY/XZ線表示はC++のdouble位置で、3D側は監査後のFloat32位置を使う。

```js
import {createDerivedMeshRenderData} from '../engine/derived-render.mjs';

// result is the successful runtime.prepareDerivedMesh(...) snapshot.
const data = createDerivedMeshRenderData(result);
await renderer.renderChecked([{
  id: 'skin-binding-preview', type: 'derived-mesh', mesh: data,
  position: [0, 0, 0], scale: [1, 1, 1], color: [.20, .78, .67]
}], camera);
```

factoryはresultの全体成功、bufferの型・形・finite・容量・整合を検査し、必要なbytesを所有copyする。返すtokenはfreezeしたmetadata `{vertexCount,triangleCount,floatCount}` のみを公開し、実bufferはWeakMapで私有する。`floatCount=18*triangleCount`。元のtyped arrayを書き換えてもtokenの内容は変わらない。これは呼出側が任意に作ったresultを数学的に再認証する仕組みではない。C++監査から受け取った成功snapshotの来歴と、公開境界の構造検査を区別する。

`type:'derived-mesh'` は専用の描画経路である。監査済みinterleavedのposition3/flat-normal3をそのままuploadし、既存の編集mesh用`compileMesh`で法線を再計算しない。失敗/null/tokenでない入力を編集meshやboxへfallbackさせない。既存の編集mesh/box経路は保持し、mesh ID・instance数・面数などの描画予算は共有する。tokenをScene原本へ保存する形式は追加しない。

SDKからの派生入力は最大2048頂点・32768面で、rendererでの表示成功はSDKの容量を増やさない。小さい帯での表示受入と、大規模入力の参照計算時間・更新頻度は別に扱う。

## 固定した表示条件

mesh-local=skeletonのmetresをidentity model（位置0、scale1、yaw0）で渡す。Sceneのworld変換は適用しない。

| 視点 | eye [m] | target [m] |
|---|---|---|
| 斜め | [3,2,4] | [1,.35,0] |
| 正面 | [1,.35,4] | [1,.35,0] |
| 背面 | [1,.35,-4] | [1,.35,0] |

Y-up、perspectiveの視野60度、near .2m / far1600m。色は上の固定値、照明は既存WGSLのGGX直接光・環境光近似、fog、exposureとtone mappingを使用する。画像の輝度を実測照度や光学POWERと解釈しない。固定cameraの外にある原本は、数値監査が成功しても画面で見えない場合がある。

既存shaderはFloat32 model/VP演算と法線normalizeを行う。CPUの各局所法線成分の誤差上限を、world/view/clip、GPU算術、画素の被覆へ拡張しない。一般のshearを含むnormal変換、新しい自己交差・反転判定、接触・材料損傷の保証も追加しない。

## 状態とGPU資源

時刻、loop、原本、weight、Scene照合、監査予算が変わった場合は古い可視meshを消す。前段計算や派生監査が失敗した場合も、以前の成功bufferを現在の結果として表示しない。使わなくなったmesh bufferを破棄し、再計算・再監査後に手動で表示する。

数値監査とGPU状態は別に表示する。WebGPU非対応、adapter/deviceの作成失敗、validation error、device lostでは3Dを隠してGPU資源を解放するが、成功した数値JSONや構造が有効な保存原本を失敗へ書き換えない。原本を保存・修正でき、同じラボから表示を再試行できる。遅れて完了した旧表示要求が、新しい原本やrendererを表示し直さないよう世代を照合する。

`renderChecked`はvalidationとqueue完了を確認してから表示完了とする。queueの完了はCPU契約がGPU/画素で保存されたという数学的証明ではない。`dispose`は表示の終了やpagehideで所有するmesh/static/instance/uniform bufferとdepth textureを解放し、contextをunconfigureする。繰返し呼出しは許容し、共有され得るGPUDevice自体はdestroyしない。作成途中の失敗や更新時の失敗も受入対象とする。

## 受入と来歴

mock GPUでは全upload bytesと末尾face、draw頂点数、tokenの所有copy、cacheの再利用・更新・削除、dispose、既存編集meshとboxの互換を検査する。UI試験では成功表示→入力変更で消去→再表示、実LBSの180度collapseによるgeometryなし、正常入力への復帰、GPU失敗時の数値/原本保持、描き直しでC++照会回数が増えないことを確認する。実GPU成功はブラウザ操作で別に確認し、mockだけでは報告しない。最終集計と公開検証はこの文書更新時点で未確定。

新しい外部library、モデル、画像、フォント、SDKは導入しない。教材図は既存の原著`docs/learn/diagrams/derived-mesh.svg`を継続使用し、CPU変換の概念図として表示する。新しいGPU測定図ではない。既掲WGSL/MSVC資料の確認範囲を継承し、新たな実読記録は追加しない。配布WASM/glueと既存7通知のbyte不変は最終照合で確定する。本体ライセンスは未選定のまま。

ローカル最終集計: Node391/391・skip0、renderer新18群（既存orientation5群も成功）、lab19群。実ブラウザWebGPU15操作を確認し、SDK/C++/sampleと既存7通知は不変。配信・Linux CIの結果は[検証記録](../reports/2026-11-04-derived-render.md)で別に確定する。

公開受入: コード90b1afeのLinux CI/Pagesが成功。Node391skip0/CTest30、公開WebGPU15操作の全原本・数値packetと表示状態がローカル一致、配信17ファイルbyte一致。既存robotは起動READYまで回帰確認し、戦闘操作/新animation適用の成功へ数えない。全証拠は[検証記録](../reports/2026-11-04-derived-render.md)。
