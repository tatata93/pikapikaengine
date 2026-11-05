# 位置誤差と接触余裕を明示した平面の全区間検査

Native専用の `accelerated_plane_box_coverage` は、呼び出し側が指定した位置誤差の上限Bと接触余裕marginを含む、平面判定の条件付き証拠を返す。実装・検証の受入状況は [PLAN](PLAN.md) と本段階の記録を参照する。実Worldの誤差上限を自動で導く機能、Worldの時間進行、接触応答は後続である。

## 入力と計算

`Input(sphere, plane, position_error, contact_margin)` は4引数を必須にする。Bとmarginを省略してsolver既定値を推測しない。位置・速度・一定加速度・半径とraw平面は元のbinary64値を保持する。半径は正、法線は非zero、各成分/offset/半径の絶対値は有限で1e12以下、Bは有限の0以上1e12以下、marginは有限の0以上0.1以下。時間Hは秒で0より大きくbinary64の.1以下である。

閉時間区間Tごとに、自作の外向き区間演算で次を求める。

```text
Xk = I(Pk) + I(Vk)*T + (I(ak)*I(.5))*square(T) + [-B,B]
distance = ((I(nx)*Xx + I(ny)*Xy) + I(nz)*Xz) - I(offset)
threshold = I(radius) + I(contact_margin)
gap = distance - threshold
```

半加速度を通常doubleへ先に丸めず、thresholdを独立して記録する。全3座標の箱・distance・threshold・gapが各auditに所有される。全leafの `gap.lower()>0` と閉区間全被覆が揃ったときだけcertifiedになる。接線、zero、時間幅による停止、評価やleafの予算不足はcertifiedにならない。

Bは各軸のnominal quadraticからの位置誤差上限という呼び出し側の宣言である。実際の中心がこの箱の中にあるという別の証拠を必要とする。箱は座標間の相関を捨てるため、正しいBでも有限予算での成功は保証しない。

## 丸めと幾何を区別する

固定した左結合ASTの各演算nodeで、実数演算またはbinary64の最近接偶数丸めを取る族を包含する。積の丸めを省いて親の和で丸めるFMA収縮もこの族に含む。任意の再結合、fast-math、FTZ/DAZ、拡張精度全般を許可するものではない。[浮動小数点監査](WORLD_PREDICATE_FLOATING_POINT_AUDIT.md)に対象compiler/flagsと境界を記録した。

raw法線を正規化しない。この判定と、既存の球対平面metric条件 `n·p-offset-radius*|n|>0` は異なる。ほぼunitという入力検査は厳密にunitという等式ではない。将来のWorld統合では同じowned pairに両方の全時間証拠を結び付け、同じ明示marginと実Bを検査する必要がある。各証拠のleaf境界は一致しなくてもよい。

## 返却する診断

環境を最初に検査し、supported環境では不正入力も検証前に固定サイズsnapshotへコピーする。最大255評価、128leaf、depth32で最小depth・同率最左のBFSを行う。停止しても全partition、全audit、未照会tail、必要なcurrentを所有する。評価を試みた回数と正常返却した回数を分け、返らなかったEvaluationを補填しない。sqrt/metric/伝播の呼び出しは行わない。

数値包含の独立検査はFractionによる二次関数の全域極値と、整数演算で実装したbinary64丸めの有限choicesを使う。実public value全端点bitの再照会は別の由来検査であり、数学的に有効な広い区間の受入と混同しない。有限試験を全compiler・実World・一般接触の完成へ拡張しない。

[設計契約](ACCELERATED_PLANE_BOX_COVERAGE_PLAN.md) · [元の球対・metric平面coverage](ACCELERATED_PAIR_COVERAGE.md) · [全Worldへの後続計画](WORLD_STATIC_MESH_FLIGHT_PLAN.md)
