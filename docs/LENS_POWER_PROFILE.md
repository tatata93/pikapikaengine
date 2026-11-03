# 合成レンズの有限POWER packet実験

`engine/polarized-camera.mjs`と`tools/lens-power-lab.html`は、合成両凸レンズの指定された二経路を
有限個の明示POWER packetで調べる独自の参照機能である。既存の幾何spot profileは変更しない。
交差、屈折・反射、全区間の偏光輸送、sensor判定と最終POWER集計は共通C++を実WASMで呼ぶ。
JavaScriptで光学を代替計算しない。

## 原入力の測度と単位

version=1、kind=`synthetic-biconvex-finite-power`。`powerWatts`は**各単色実験の有限ソース光束P [W]**。
既定は1W、入力範囲は1e−6..1e6W。真空波長450/550/650nmはそれぞれ独立した実験であり、
スペクトル密度・波長重みやRGBの応答は定義しない。波長間の合計、二つの経路の合計を出力しない。

Nr∈{1,2,4,8,16}、Na∈{4,8,16,32,64}、N=Nr Na≤1024。
全packetのI=P/N、初期Stokesは無偏光またはQ/U/Vの一成分だけが±Iの点入力とする。
Nは二の冪なので二進浮動小数点の指数移動として除算は正確であり、このP/Nは範囲全体でnormalである。
原入力doubleを厳密実数として解釈したN個のIの和はPである。繰返しdouble加算の結果が必ずPになるという主張ではない。
純粋偏光のI²=Q²+U²+V²も厳密に成立する。Iを幾何重みから推測したり、丸め許容幅で物理円錐へ投影しない。

節点はr_i=a sqrt((i+1/2)/Nr)、θ_j=2π(j+1/2)/Naで半周を作り、残りを正確な符号反転の対とする。
sin/cos/sqrtで作った座標は丸め済みbinary64の原入力である。等r²の配置でも、ここでは未標本の連続瞳の
積分・誤差・照度分布を保証しない。開口aを変えても明示ソースPは変わらず、別の有限packet実験になる。

sourceはparallelのみ。生のdirectionとtransverseReferenceを保持し、発射面Z=−0.01mの各節点へ
`makeOpticalLaunchRay`を呼ぶ。JavaScriptで方向を規格化しない。既定参照軸は[1,0,0]。
初期Stokesは各方向で明示参照軸を横断面へ射影した基底に対する値で、C++が全方向・基底・coherencyを囲む。
参照軸を決められない場合に別軸を選んで成功扱いしない。

## 固定形状、材質、二つの明示経路

前頂点Z=0、後頂点Z=0.005m、signed radiusは+0.05/−0.05m、axis=[0,0,1]、
共通開口半径1e−5..0.015m。既定は0.005m。合成CauchyはA=1.48、B=6.05e−15m²、C=0m⁴、
有効帯400..700nm。実レンズ処方・実測ガラスではない。保存profileではCauchy係数・有効帯・1..8点波長を明示できる。
`queryDispersion`が返したphase-indexの**全区間**を渡す。分散が未解決・非物理ならその波長の二経路resultはnullのまま。

| 経路ID | 面列と分岐 | 各境界の他方index |
| --- | --- | --- |
| primary | T前 → T後 | glass phase → air1 |
| ghost | T前 → R後 → R前 → T後 | glass phase → air1 → air1 → air1 |

反射時は現在の媒質indexを保つ。全段のparameter domainは[0,1e6]、固定epsilonのself-root省略はない。
この指定面列と媒質ラベルは実験の入力規約である。閉じた媒質領域、最も近い物理界面、未指定面との非交差、
筐体による吸収、全ghost列や経路の排他性を自動証明しない。同じphase区間を繰返し渡しても相関が数値boxで
失われる場合があるが、区間中央値へ潰して一致を偽装しない。

## 理想sensorと結果

sensorはnormal=[0,0,−1]の理想吸収円盤。中心は各軸±1m以内、Z≥0.00501m、半径1e−6..1m。
既定center=[0,0,639/11800]m、半径0.05m。Canvas表示窓と実sensorの開口は独立で、描画倍率は受理対象を変えない。
センサーは新たな屈折界面ではない。到達packetの`sensorPower`はroute completionのPOWER区間そのもので、
cosやindex²を二重に掛けない。偏光による検出感度、量子効率、面積当たりW/m²、pixelへの配分は定義していない。

各経路・各波長で、全packetが到達または確定した指定経路欠落になった場合だけ、C++のstatsに
`totalSourcePower`、`acceptedSourcePower`、`detectedPower`の区間[W]が入る。
acceptedSourcePowerは到達packetの**元のI**で、減衰後の検出POWERとは別の量である。
確定したroute miss、選択枝なし、sensor missはこの経路の検出量へ0を寄与するが、
未知・未実行・予算不足を0Wへ置換しない。不完全ならstatsはnullで、既知packetだけに再正規化しない。
preflight失敗でrecordsが空でも元packet入力は保存し、UIでは未受理として区別する。

全recordは原Stokes、polarized routeの全prefix、幾何sensor結果とsensorPowerを保持する。
世界XYZ coherencyの各成分は実入力族の物理テンソルを囲むもので、区間端点の任意の組合せ全体がPSDという意味ではない。
一本内の相対s/p位相を保持するが、経路間やpacket間の相互相関・共通位相は保持しない。
二つの経路の行列を足して干渉・薄膜・回折・波動PSFと呼ばない。

## 予算・保存・検証

settingsはmaximumRouteSteps、maximumParameterWidth、maxSqrtRefinements、powerMaxSqrtRefinements、
maximumPackets、maximumPacketEvaluations、maximumTotalSqrtRefinements、maximumPhaseWidth。
optional maximumRouteSqrtRefinementsは原本にある場合だけ保持し、未指定ならruntimeが全体予算と同値にする。
総sqrtはC++が報告する有限作業の予算であり、経路/packet単位の事後監査による失敗時overshootは核の契約に従う。
予算を理由に黙ってpacket数を減らさない。

profileは未知field・非有限値・不正範囲を拒否する。保存読込で材質・参照軸・非表示予算も保持し、
UIで触らないdouble原値をmm表示から逆変換しない。明示計算だけで実行し、入力変更は古い結果を消す。
処理中は入力と再読込を固定し、実照会の進行と操作時間を表示する。JSON保存はユーザーのクリックだけで行う。

検証は`tests/lens-power-profile.test.mjs`と`tests/lens-power-lab.test.mjs`。
独立BigInt有理数で各P/Nと総P、厳密な純偏光円錐を確認し、既知の節点対称性、経路生成、
phase区間/原Wの転送、保存読込、欠落・未知・未実行・preflight・予算復帰と実WASMを調べる。
原本固定の実行件数とbyte/hash・実ブラウザ記録は親統合のreportsで確定する。

## 一次資料の確認（2026-11-03）

[PBRT3 Realistic Cameras §6.4](https://pbr-book.org/3ed-2018/Camera_Models/Realistic_Cameras)を実読し、
面列による屈折と、同節の基本モデルが反射を省略する範囲を確認した。本機能のghost列・偏光核は独自であり同実装の移植ではない。
[PBRT4 Radiometry §4.1](https://pbr-book.org/4ed/Radiometry,_Spectra,_and_Color/Radiometry)で光束W、
面積密度、放射輝度の量の違いを確認した。[Peatross/Ware著者版 §3.3–3.5](https://optics.byu.edu/docs/opticsBook.pdf)
pp78–82で電場振幅と法線fluxの係数、透過の面積/角度因子、TIRの範囲を確認した。
今回はこれら三つの一次資料を取得・実読できた。外部コード・図・本文・材質数表・ライブラリは取り込んでいない。
