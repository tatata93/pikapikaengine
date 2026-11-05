# 両方の位置誤差を含む球接触式の全時間検査

Native用の `accelerated_sphere_box_coverage` は、宣言した二つの位置誤差と接触余裕を含む球接触式を全時間で調べる。実装・検証・公開の現在地は [PLAN](PLAN.md) と [設計契約](ACCELERATED_SPHERE_BOX_COVERAGE_PLAN.md) に分けて記録する。実Worldの誤差上限や外部sqrtのcompiler/runtimeとの対応は、後続の統合条件である。

`Input(firstSphere, secondSphere, firstB, secondB, contactMargin)` の5引数を必須にする。Sphereには点の位置・速度・一定加速度と元の半径を渡す。Bは各軸の位置誤差上限として呼び出し側が宣言する。各成分と半径の絶対値は有限で1e12以下、半径は正、両Bは0以上1e12以下、marginは0以上0.1以下、照会Hは秒で0より大きく0.1以下とする。

閉時間区間ごとに、両方の全位置を箱へ囲む。

```text
X = quadratic(PA,VA,aA,T) + [-BA,BA]   // 各軸
Y = quadratic(PB,VB,aB,T) + [-BB,BB]
D = Y-X
Qraw = (square(Dx)+square(Dy))+square(Dz)
Qsafe = [max(0,Qraw.lower),Qraw.upper]
root = sqrt_enclosure(Qsafe,refinements)
distance = root.value
threshold = (I(rA)+I(rB))+I(margin)
gap = distance-threshold
```

全15区間を各Evaluationへ保存する。この数にはroot.valueと、それと同じbitsを持つdistanceの両方が含まれる。生の二乗距離、非負性に基づく下端の切詰め、全SqrtResultの反復数・limited診断も保持する。負の上端は不整合として扱う。

位置差、二乗と和、閾値の加算順序、平方根の丸めが判定に影響する。固定ASTの各演算nodeで実数またはbinary64 RN-evenを取る族を自作区間演算で包含する。非負のbinary64端点で全実平方根を囲めば、丸めの単調性と端点の固定性から、正しく丸めた平方根もその中に入る。この数学的条件と、実際にリンクした外部std::sqrtがその規約を満たすかの検査は別である。

全closed leafのgap下限が正で、全時間被覆・返却・会計の整合が揃ったときだけcertifiedとする。Eは最大255評価、leafは最大128、depthは最大32。sqrtの精錬は各端点1..256、既定128。limitedでも包含が有効でgapが正なら認証できる。

正確なvalue呼出し回数と、完全なEvaluationを通して観測したsqrtの返却・反復数を分ける。valueが返らなければ、その内部のsqrtがどこまで進んだかを推測せず、最大2×refinementsの予約上界を保持する。全call上界130560は反復枠であり、使用heapやstackのbyte保証ではない。

独立参照は、6座標について真の二次軌道の全域極値±BをFractionで検査する。その記録された座標箱から先の位置差・二乗・左結合和・閾値・gapは、実数と整数によるbinary64丸めの選択を検査する。平方根は平方不等式と非負binary64端点の丸め固定性で包含を確かめる。座標箱を作る全演算nodeの丸め選択まで独立に列挙したという意味ではない。実public valueの全15区間の端点bitsとroot診断の再照会は、別の由来検査である。

全World/pair/candidate、接触応答、流体、材料損傷、繰返しsubstepの真解をこの単体核の受入へ含めない。
