# 次の受入: 描画用の派生mesh

2026-11-03。**初段契約固定・Native純粋核を実装中（未受入）**。owned bindingと原本codecの公開受入は[記録](../reports/2026-11-03-skin-binding.md)。ここからは数値completedの位置を、保存原本を変更せず描画bufferへ変換する。

## 既存経路の確認

`engine/mesh.mjs`のsource validatorはdouble位置の面積とFloat32丸め後のcrossをdoubleで点判定する。`compileMesh`のflat normalは丸め後の頂点から計算する。`platform/windows/viewer.cpp`はworld変換後double位置から法線/明るさを作り、頂点をfloatへ変換するため、実際のGPU頂点と法線の基準に差がある。既存source検証を突然置換せず、まず独立した派生buffer APIで条件を確定する。

単に新しい位置をSceneのmesh原本へ代入すると、author sourceを失い、描画cacheのobject identityにも依存する。派生snapshotは原本/Scene編集とは分ける。前frameの成功bufferを破棄してから新しい候補を検査する順序にはしない。複数object全体のtransactionと既存rendererへのcache接続は、単一mesh核の後に別途受入する。

## 最小のNative核案

- 任意の位置列と三角形index列をread-only spanで受け、所有するFloat32位置、flat normal付きface順bufferと診断を返す。skinning固有のFK/weightを再計算しない。原本の名前、行列、raw weight、double位置と順序は変更しない。
- 初段はmesh-local位置のCPU変換。world/camera/GPU matrix計算後の退化、shaderやrasterizerの精度、自己交差、材料力学を保証する意味ではない。実3D接続の際に適用する座標空間を明示する。
- 各位置のfinite、Float32範囲、数/indices/重複、予算を確保前に検査する。初段の共通位置上限2048・三角形上限131072を候補とし、切捨てや自動batchをしない。丸め後の位置と実bufferに使う位置を同じ値にする。
- strict IEEE環境とFloat32変換のnearest-even/subnormal条件を検査する。既存[区間演算](INTERVAL.md)を使い、丸め後の点を厳密な二進有理入力としたedge/cross/二乗面積を囲む。単にdouble crossが非零という理由で非退化の証明にはしない。
- 面積下限が明示floorを超えた場合だけ受理する案。上限がfloor以下と証明できる場合と、floorをまたぐ未解決を区別する。未解決を成功へ移さない。floorの単位はcross norm squaredのm^4であり、triangle面積m^2そのものではない。既存sourceの1e-24と同じ設定を採用するかは実装前に固定する。
- 法線は丸め後の位置から生成し、finiteとFloat32格納後の長さ/方向を監査する。normalizationの点誤差と面積の包含を別に記録する。一般の面反転を「旧法線と新法線の内積が負」で判定しない。180度の剛体回転でもその符号は変わる。
- failureは失敗face/vertex、理由と実行量だけを返し、有効な部分bufferを公開しない。所有snapshotは次の照会で変わらない。settingsや結果は明示version/上限を持つ。status名、floor、normal許容とbuffer layoutは次の実装開始前に固定する。

## 独立検証と接続順序

1. C++核とNative試験。既知平面/回転/非一様scale/shear、index/予算、Float32 overflow/collapse、細い面、境界floor、非対応丸め環境、失敗後の復帰・元データ保持を検証する。
2. Python Fractionで出力Float32 bitsを厳密に復元し、crossと二乗面積が各区間に含まれることを確認する。正例だけでなく、偽造したbits/区間/normal/部分成功を負例として検出する。面積の包含を任意inputの法線角度誤差保証へ拡張しない。
3. 既存主SDKとWeb bridgeへ有界接続し、Native/実WASM比較。保存原本のbyte不変を再確認する。外部math/rendererは導入しない。
4. 自作の小さいmeshで実3D描画。編集→照会→buffer交換→保存/再読込、rest復帰、失敗時の古い表示の扱いを実ブラウザ/Nativeで確認してから、オリジナルrobot sampleへ適用する。

法線のsmooth化/接線/UV/材質、GPU skinning、衝突mesh同期、弾塑性損傷、IK/物理制御はそれぞれ別の受入を持つ。

## 初段で採用した固定値

`derived_mesh::prepare(span<const Vec3>, span<const array<uint32_t,3>>, Settings)`。既定2048頂点/32768三角形、hard65536/131072、座標±1e6m、sqrt予算128（1..256）。sourceの131072三角形より既定描画予算は小さいため、超過は明示failureにする。Qfloorはbinary64定数`1e-24`を正確な実数と解釈し、m^4で扱う。

statusはcompleted/invalid_input/budget_exceeded/degenerate/quality_rejected/quality_unresolved/numerical_failure/unsupported_environment。失敗時にgeometryを返さない。幾何auditのcross全成分が点0ならdegenerate、Q上限<=floorならquality_rejected、Q下限>floorと少なくとも一cross成分のstrict nonzeroを証明できなければquality_unresolved。

同じ量子化位置のcrossから候補法線を作ってFloat32へ格納する。区間crossと既存sqrt_enclosure(Q)による単位法線の包含に対し、候補の各成分の最大誤差上限<=`1e-6`を必要とする。sqrtが予算limitedでも包含幅が条件を満たせば可、満たさなければ拒否する。候補値を作るlibmの精度そのものは証明の前提にしない。全faceが成功した場合だけowned indexed位置/triangles/flat pos3+normal3 bufferと全auditを返す。

これはstrict build/CPU環境の条件付きである。[WGSLの浮動小数点評価](https://www.w3.org/TR/WGSL/#floating-point-evaluation)はGPU側の精度/評価規約を別に持つため、このCPU証拠をGPU演算の証明と扱わない。[MSVC /fp:strict](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170)の環境/丸め/縮約規約を確認し、既存strict flagsを維持する。外部コードを移植しない。
