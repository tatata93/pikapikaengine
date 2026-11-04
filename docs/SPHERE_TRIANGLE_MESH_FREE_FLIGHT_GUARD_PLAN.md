# 球×静的三角形集合: 丸め自由伝播guardの次段計画

状態: **未実装のNative次段計画**。保持荷重核のローカル試験や既存W1の成功を、本guardの実行証拠に流用しない。この文書の追加ではC++、SDK、86 exports、配布artifact、World、ゲームを変更しない。新しいC ABI/JS/UIはこのNative受入の後に判断する。

## 今ここで埋める依存

[保持荷重核](SPHERE_TRIANGLE_MESH_HELD_LOAD_PLAN.md)は、入力binary64を厳密実数とした

`p(t) = P + V t + (g + F/m) t²/2`, `0 <= t <= H`

の有限静的meshに対する証明である。一方、実際の[自由伝播](../core/src/dynamics.cpp)は丸めた`a = g + F * inverse_mass()`と複数の丸め演算で位置を更新する。前者の安全証明だけでは後者の中心位置を含まない。

[continuous_world.cpp](../core/src/continuous_world.cpp)の匿名`flight()`（現57–94行）は既に、この係数差と実装の位置operation graphの丸めを区間で上から評価している。`advance`（現212–234行）は実際に`detail::propagate_free`した候補をそのendpoint enclosureへ戻して検査する。本段はこの根拠を再使用し、有限三角形meshについて**1 body・1自由区間の非接触をread-onlyで認証**する。新たな衝撃、支持、積分法を作る段ではない。

保持荷重照会をSDKへ運ぶ案Aも有用で、ブラウザからSI荷重の予測を照会できる。しかし数学pathの証拠自体は増えない。先に本段で実装伝播との間を埋め、その後に必要な診断をまとめてSDKへ運ぶ順を推奨する。

## 成功の数学的条件

既存自由伝播の並進分岐を、**初期bodyを毎回コピーして**binary64 duration `t`で一回実行した中心を`q_fl(t)`とする。繰返し小刻みに積分した中心とは異なる。

既存W1の係数差・operation graphから、全representable `t in [0,H]`について

`||q_fl(t) - p(t)||₂ <= B`

となる有限・非負の上界`B [m]`を得る。各座標の絶対誤差上界を外向きに足したL1を使うので、Euclidean normの平方根は新たに必要ない。入力durationを表現できる実数の時計へ連続拡張したり、丸めた出力を連続軌道そのものと呼んだりしない。

`r_guard = upper(I(r) + I(B))`を計算し、元の`P,V,F,m,g`とこの半径を既存保持荷重核へ渡す。同核が**全[0,H]のseparatedだけを返す**とき、全tの数学pathについて`d(p(t), mesh) > r_guard >= r+B`であり、距離のLipschitz性から、対応する全representable durationの丸め並進中心も`d(q_fl(t), mesh) > r`となる。証明は全source・全leafの厳密正clearanceに依存し、端点だけでは代用しない。

膨張半径の`entry_window`、`initial_penetration`、未認証、品質/予算失敗は**元球の物理entry/貫通を意味しない**。これらはguard未認証の診断としてそのまま保持し、成功へ変換しない。元半径のentryが必要なら別の保持荷重照会結果を明示して保持し、両者の半径・所属・Workを分ける。本最小段ではその追加照会は必須にしない。

## W1再使用の方法と変更境界

`flight()`とその`Flight`/`Stop`は匿名namespace内にあり、新TUから直接呼べない。数式・ULP recurrenceを新kernelへ複製して保守対象を二つにする案は採用しない。最小案は次である。

1. 新private header `core/src/free_flight_internal.hpp`へownedな返却型と入口を宣言する。位置上界、丸め部分、nominal acceleration、上向きguard radius、明示的失敗を返す。型/名前は実装開始時に固定する。
2. **既存`continuous_world.cpp`と同じTU**にprivate bridgeを追加する。既存の`flight()`を一回呼び、返却値をコピーする。匿名`Stop`を外へ漏らさずfailure enumへ変換する。既存`flight`本文・旧World呼出し・演算順は変えない。
3. 新公開Native核はbridgeと既存`detail::propagate_free`を利用する。後日、本当に共有実装を別cppへ抽出する必要があれば別受入とし、本段で不要な移動をしない。

bridge追加にも共有cppのsource hash変更が伴う。旧W1の全fixture/report/state bits・status/failureの前後比較、既存C ABI/World試験が必要である。既存builderがこの共有cppを配布SDKのsource hashへ含めるため、実装を統合するときは**同じ86 exportsの再buildとsource/artifact/license/provenance監査が必要になり得る**。出力byte不変は事前に主張しない。SDKに新guard能力が公開されたことにもならない。ビルド依存はrootと固定し、古いmanifestへ新source hashを手書きして済ませない。

## 最小の純粋入口・owned結果案

新規候補は`core/include/pikapika/sphere_triangle_mesh_free_flight_guard.hpp`と同名cpp、専用Native tests/fixture、独立checker。入口は`query_body(const World&, body_id, triangles, H, Settings)`を優先する。Worldのbody/plane storage・gravity・保持force/torque・pointerを変更せず、時計も進めない。選択bodyが妥当な動的・CoM中心の球proxyであることを確認する。別bodyとの接触を無視してWorld tick成功とは呼ばない。

既存保持荷重と同じ入力/派生域、H `(0,.1]`秒、source最大64、照会256・partition128等の上限を維持する。別の有限`maximum_position_tube [m]`を公開するかは正式headerで決める。W1のresponse用`spatial_tolerance/32`等を理由なく移植せず、数値品質gateを足す場合は値・単位・不合格を明示する。

結果は少なくとも以下を別所有する。

- 原body全field・gravity・元radius・元H/source/settings。
- nominal accelerationと、厳密`g+F/m`との差を囲む診断。普通double値を厳密係数へ昇格しない。
- 既存operation graphのroundoff部分と、係数差を含む総位置上界B、上向き`r_guard`。
- 膨張半径を入力とした保持荷重の完全結果（全audit/partition/島/lastMesh/全ID/unknown Workを省略しない）。
- 元bodyコピーをHで**実際に**`detail::propagate_free`したowned candidateと、endpoint位置のenclosure確認結果。失敗時に成功candidateは返さない。
- `certified_separated`と未認証/invalid/environment/numerical/budgetの区別。原Worldは全経路で不変。

`B`、半径和、`r_guard`をfinite/非負・上向きで検査する。元rが許容内でも、膨張後が既存半径上限1e9を超えれば派生域未対応として明示失敗する。Bを切り捨てる、半径をcapへ丸める、旧核のdomainを黙って広げる処理は禁止。

## 並進証明と実candidateの成功条件

W1の`flight`が証明するのは並進のoperation graphである。現`propagate_free`はさらに世界L、姿勢中点、torqueを進め、回転増分制限で失敗し得る。球中心の幾何に回転項を足さないが、**body全体のcandidate成功には回転の実行と最終`RigidBody::validate`が必要**である。

候補はコピー上でH一回だけ進める。各位置成分をnominal endpointの区間＋既存roundoff上界へ戻して確認し、さらに厳密保持荷重endpointとの差がB以内であることを独立区間で確認する。候補のvelocity/q/Lのfinite/domain検査と、位置の証明を分ける。速度・姿勢の連続真解誤差や全時刻の回転増分成立を、この並進Bから主張しない。

厳密には全representable durationについての**並進分岐の値の包含**と、Hでの**完全propagate_free成功**の二つである。各内部durationで完全6DOF伝播が必ず成功する、と追加証明なしに拡張しない。元body/force/torqueは保存し、candidateも荷重を消費しない。複数substepの累積誤差、残時間の減算、時刻和のroundoffは本H一回の契約外である。

## 独立受入と反例

独立Fraction参照はbinary64を厳密有理数へ戻し、数学的`A=g+F/m`、各二次成分の端点/内部極値、点から三角形への距離を監査する。参照の候補選択にNative KKT maskを使わない。旧保持荷重79入力を新guardの実行済みと数えない。

新たに必要な受入は次である。

1. 一定速度/一定加速度の安全face/edge/vertex近傍と、曲線だけ安全なchord反例。実Bを加えても複数の通常例が全H成功し、全未認証の自明実装で合格しない。
2. `m=3,Fy=-1,g=fl(1/3)`の係数相殺。nominal A=0と厳密A非零を区別し、Bから係数誤差を削った偽安全を拒否する。
3. 大きい共通offset・binade境界・subnormal中間値・零速度/加速度。実compilerの候補位置をendpointへ照合し、観測数点を全durationの根拠にしない。全包含の根拠は各丸め段のrecurrence、有限duration corpusはその独立検査とする。
4. 真gapがBより狭い例。元数学pathが安全でもguard未認証が許されること、膨張球entryを元球entryと呼ばないことを確認する。
5. 膨張半径の上限超過、元入力不正、degenerate source、予算、環境、回転増分/最終validate失敗後の再利用・World全bits/pointer/保持荷重不変。
6. candidateをepsilonで直さず、上界とendpoint・半径和の負例（B削除、係数差削除、下向き半径和、誤ったoperation graph、部分source/tail削除）を独立checkerが拒否する。
7. 旧W1の通常/失敗/複数イベント・非零gravity/force/torqueを含む前後fixture bit比較、strict FP/GNU warning gate、API/World旧回帰、範囲を明記したASan/UBSan。

## この段の後にも残る依存

成功は「選択球proxyの1自由区間が、与えた静的最大64面に対して安全」である。World全body pair/planeとの順序付け、同時接触と三角形manifold、区間normalから許容された接触の構成、反発/摩擦/支持、複数イベント、残時間/累積丸め、tick全体のatomic commit/一回の荷重消費は後続である。膨張球の窓をpoint impulseへ落とす接続は行わない。

このNative証拠を受けてから、保持荷重/自由伝播guardのC ABI→owned JSと実利用する予測照会をまとめて設計する。ゲームの実接触適用、流体場、損傷、車両/航空/鉄道モデルの完成とは区別し、既存最上位要求を縮小しない。本稿は既存sourceを読んだ設計であり、新しい外部研究の実読・新実測を行ったとは主張しない。
