# 静的三角形と球の狭域接触: 次のNative受入案

2026-11-04 JST。設計のみ・未実装。Source assetだけの変更でWeb buildを更新するcache修正を先に受け入れ、その後このC2の実形状接触へ進む。一般物理・流体・材料損傷・専門車両・IK/制御・光学撮像の要求を縮小しない。

## 既存の物理を重複実装しない

`core/src/dynamics.cpp`には世界角運動量と姿勢中点の積分、主慣性の検査、接触点速度と角impulse、異方的な接線有効質量とCoulomb円盤上の摩擦衝撃がある。`tests/dynamics_tests.cpp`は自由回転/Euler式・二次収束・摩擦spin・斜面5/7等を調べる。角運動や摩擦すべてを未実装として作り直さない。

一方、Native接触生成は球対/球平面で、Web meshは外接AABBに近似する。W2支持driverは摩擦0を要求し、一般meshの接触・摩擦支持・接触manifold・形状に応じた質量特性・関節/変形連成は未完。Sourceや描画の成功をそれらの証拠にしない。

## 最初のモデルとAPI

静的な両面の薄い三角形1枚と球1個のread-only照会とする。安定surface IDと元頂点順を保持し、world-spaceのm単位で受ける。閉じた固体の内部判定、時間積分、CCD、動的三角形、mesh全体の内部辺処理はこの段階に含めない。

候補 `query_sphere_triangle(Sphere, StaticTriangle, Settings) -> Result` は、三角形上の最近接点q、球表面点、barycentric・距離²・gap・法線の包含、面/辺/頂点の診断、予算と失敗理由を返す。中心x・半径rでは `d=|x-q|, gap=d-r, n=(x-q)/d`。法線は三角形から球中心へ向ける。結果は既存Intervalで入力差/係数/候補を囲み、原World/入力を変更しない。

最近接点は三角形上の距離²の最小化として、内部、3辺と3頂点を扱う。[Eberly, Distance Between Point and Triangle in 3D](https://www.geometrictools.com/Documentation/DistancePoint3Triangle3.pdf) の§1–2の定式化を読取した。実装・図・本文を転用しない。文献の実装が使う負のdeterminantの絶対値化等を、包含計算の成功へ流用しない。

退化/悪条件、有限演算逸脱、最近接領域の未確定、予算不足を明示する。d=0なら法線を捏造しない。feature分類の同率と、幾何上の最近接点/法線の一意性は別に扱う。gapの0跨ぎと有限contact bandも区別する。未知を捨てたplane/AABB fallbackや、区間中点を証明済みの点へ昇格する処理は入れない。

## 受入

- 三角形 `(0,0,0),(4,0,0),(0,0,4)` の面/辺/頂点。辺側中心 `(2,3,-4)` は距離5・法線 `(0,3/5,-4/5)`、頂点側 `(-3,4,0)` も距離5。解析解が全包含へ入ることを確認する。
- 無限平面には近いが三角形外の球を誤接触にしない。裏面/winding/頂点順/剛体変換と安定IDを確認する。
- feature境界、接触境界、退化/近退化、巨大共通offset、予算不足、失敗後再利用を独立Fraction等へ照合する。失敗時に部分成功geometryを返さない。
- 既知の接触点/法線を持つ解析例だけ、コピー候補へ既存`solve_selected_impacts`を接続する。反発後の速度と `ΔK=−m(1−e²)u_n²/2`、接線impulseの `ΔL=(p−x)×J` を照合する。一般区間結果を既存の点値solverへ無条件に落とすAPIを、この試験で正当化しない。
- 面内の既知例は十分広い既存平面と比較する。原World・時刻・荷重・姿勢は進めず、失敗時も不変を確認する。

Native純粋核/独立参照/既存衝撃への解析接続を受け入れた後に、storage、候補生成、全候補残差、SDK/制作meshとの対応を設計する。W1/W2の球平面用CCD/trajectory guardを三角形へ対応済みとして流用しない。一般形状、多接触収束、摩擦支持、タイヤ/レール、流体/損傷は残す。
