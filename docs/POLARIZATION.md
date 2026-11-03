# 偏光を保持する単一界面の分岐

2026-11-03。独自C++の`polarization.hpp/.cpp`。単色・非吸収・等方・等透磁率の媒質に限定し、
既存の[単一界面](OPTICS_INTERFACE.md)を用いて反射/透過の枝へ偏光状態を引き継ぐ。
多面レンズ、描画器、位相を保った光路の再結合はまだ実装していない。

## 状態と座標

波の時間規約は`Re(E exp(i k·x − i ωt))`。進行方向dと横断面のfirst/secondを右手系
`first × second = d`にとる。Stokesの符号は名称だけに頼らず、coherency行列から定義する。

```
C = <a a*> = [[Cxx, Cxy], [conj(Cxy), Cyy]]
I = Cxx+Cyy; Q = Cxx-Cyy; U=2 Re(Cxy); V=2 Im(Cxy)
Cxy = (U+iV)/2
```

Iは同じray tubeのパワーの重み。照度・放射輝度や電場の振幅ではない。
無偏光は`(I,0,0,0)`、純粋状態は`I²=Q²+U²+V²`、部分偏光は不等号を満たす。
有限成分、`0<=I<=1e100`を検査し、I=0ではQ/U/Vも0を要求する。
通常doubleの丸めのため物理円錐の相対64epsまでを受け付けるが、状態の投影や強制正規化はしない。
結果の検査に失敗した界面分岐は両枝を破棄して`numerical_output`とする。

`make_frame(d, reference)`は明示されたreferenceを横断面へ射影する。
各ベクトルの最大絶対成分は[1e−6,1e6]、referenceとdのsinは1e−8以上を要求する。
この値は条件数の制限であり、光学的な接触判定epsilonではない。勝手な代替軸は選ばない。
`reexpress`は同じ進行方向の二つの基底の間でQ/Uを2倍角で回転する。
単位長・直交・右手系・方向一致の検査は2e−12の数値整合条件であり、幾何の区間証明ではない。

## 枝の演算

局所s方向は`normalize(n×d)`、p方向は`d×s`。反射と透過でも同じsを使い、
それぞれの進行方向からpを作る。したがって垂直入射では反射側pの空間方向が反転する。
一般の微小入射角でs方向を安定に決められなければ`incidence_plane_uncertain`を返す。
元入力の外積が区間で厳密な零と分かった垂直入射では入力基底のfirstを使える。
等屈折率の近垂直では入力の横軸を使える。透過する物理的な偏光はidentityだが、
局所基底が入力と異なる場合は成分がその基底へ変換される。

`C' = diag(a,b) C diag(a,b)*`を直接展開すると、`z=a conj(b)`に対して

```
I' = (|a|²+|b|²)I/2 + (|a|²-|b|²)Q/2
Q' = (|a|²-|b|²)I/2 + (|a|²+|b|²)Q/2
U' = Re(z)U - Im(z)V
V' = Im(z)U + Re(z)V
```

`diagonal_jones`は受動的な|a|/|b|<=1（丸め64eps）だけを受け付ける。
coherencyの積はfrexp/ldexpで仮数と指数を分け、出力の最後でdoubleへ戻す。
例えば`I=2^300,a=b=2^-600`の出力`I'=2^-900`は、振幅を先にdoubleで二乗すると
途中で0になるため、この順序にはしない。不均一な振幅の純p入力や最小subnormalのidentityも検査する。
指数範囲を保持する方式であり、仮数の任意精度化・正しい最終丸め・打消しの一様誤差保証ではない。
入射・出射基底を保持したままこの式を適用し、面が変わるときには先に基底を変換する。
毎回無偏光に戻して反射率を平均する演算ではない。

反射の電場係数は`rs=(ni ci−nt ct)/(ni ci+nt ct)`、
`rp=(nt ci−ni ct)/(nt ci+ni ct)`。透過は既存核が別に求めたパワー比Ts/Tpの正の平方根を使う。
これは`electric_t × sqrt(nt ct/(ni ci))`というパワー正規化で、電場振幅t自体とは区別する。
異媒質のgrazingでは一方向から近づく極限を使う。等媒質のgrazingは透過identity。

全反射の分類は既存核の原入力区間Dに従う。近似の`kappa²=(ni sin(i)/nt)²−1`が正と
評価できる場合だけ、`ct=+i kappa`を選んだ複素rs/rpを返す。この符号は上記の時間規約と
透過側へ減衰するevanescent波に対応する。通常doubleの位相であり、その区間保証ではない。
伝搬する透過枝は作らない。臨界D/入射側が未確定の場合は反射枝も返さない契約である。

## 独立に確認する例

`tests/polarization_tests.cpp`は以下を別の式・構成から確認する。

- 基底射影と右手系、2倍角、往復基底変換、V保持、不正基底/物理円錐の拒否。
- 電場ベクトルa/bを直接変換してcoherencyを作る100例と、Stokes変換の一致。
- 二枚の理想偏光子のMalus則`Iout=Iin cos²(theta)/2`、retarderのV符号。
- 垂直4%と反射p基底反転、無偏光/等媒質/grazing/近垂直の条件。
- Brewster条件のRs=25/169とRp=0。二面の同じ入射面なら反射はRs²/2、
  入射面を90度回せば最初のs偏光が次のpになり反射が消える。
- `i=(.8,−.6,0), ni=1.5,nt=1`の全反射。局所45度直線偏光から
  `U=53/75,V=16sqrt(11)/75`となる独立解析値を確認する。
- 透過時の電場振幅をパワー正規化から戻し、接線E/Hの四つの境界条件を確認。
- 角度/屈折率/入射偏光を変えた枝のパワー収支。単にT=1−Rを割り当てた試験ではない。

これらは有限集合での観測であり、全Stokes値の区間包含や測定装置の校正ではない。

## 研究と残る範囲

[Mitsuba開発者の偏光解説](https://mitsuba.readthedocs.io/en/stable/src/key_topics/polarization.html)の
基底整合・Stokes/JonesとFresnelの符号規約を2026-11-03に確認。
[PBRT4 §9.3](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission)も確認した。
実装、試験の構成、上のcoherency展開と解析例は本リポジトリで作成した。
Mitsuba/PBRTのコード・図・本文・ライブラリや測定材質値を取り込んでいない。

coherency/Stokesは一本の光路内の相対偏光位相を保持するが、異なる光路の相関や共通位相を
保持しない。分かれた枝を足して干渉・コーティング・回折を再現したと扱わない。
実材質の分散、吸収/複素屈折率、薄膜、有限ビームの臨界効果、波面伝搬は対象外。
この核とレンズ面の幾何を組み合わせた光路追跡・収差/ゴースト/フレアの評価は後続である。

## 共有出力の検証

Native/standalone実WASM各17群、420界面flux例・41接線E/H境界例・100直接電場例が成功。
両対象の最大差は各4.4408920985006262e−16。実装範囲内の有限集合の観測であり一様保証ではない。
極小振幅の中間underflowと、等媒質45度で参照軸が反射方向に重なる例も回帰に含む。
主C ABIは入力16/出力57、JSは`queryPolarizedInterface`で実WASMへ照会する。
4つの公開API試験でnormal/TIR/二面Brewster/未確定を確認した。枝と基底の配列は
[SIMULATION_ABI.md](SIMULATION_ABI.md)、ログはreports/polarization-{native,wasm}-tests.txt。
