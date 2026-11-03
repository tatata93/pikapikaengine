# 重力・外力を含むWorldへのCCD統合設計

設計日: 2026-11-03 JST。これは**未実装の計画**であり、加速WorldのCCD受入実績ではない。
調査した原本は `core/src/dynamics.cpp`、`dynamics.hpp`、`hydrostatics.cpp`、
`simulation_api.cpp`、`tests/dynamics_tests.cpp` と [一定速度TOI核](CONTINUOUS.md)。
本作業はこの新規文書だけを追加し、公開準備中のソース・ABI・テスト・hashを変更しない。

次に実装する縦断は、**複数の動的/静的球proxyと静的平面、非零重力、物体別のheld外力・
トルク、複数の衝撃イベントを持つ1tick全体のtransactional CCD**とする。
持続接触の力学、状態依存荷重、非球形状は後続受入として分ける。初段でそれらに遭遇した
場合は理由付きで失敗し、全tickを原状へ戻す。零重力や1体だけの成功を一般CCDと呼ばない。

## 既存Worldで維持すべき意味

| 現在の処理 | CCDでの扱い |
|---|---|
| `integrate` は `p+=v*h+a*h²/2, v+=a*h`、`a=g+F/m` | 無接触区間の球中心軌道として利用できる。接触後は速度から照会し直す |
| 各 `integrate` の末尾でforce/torqueを零にする | 公開tick開始時に荷重をsnapshotし、全区間で保持。成功した全tickの最後に1回だけ消費する |
| `apply_force(F,world_point)` は適用時のCoMでトルクを蓄積 | CCDでも蓄積した世界トルクを保持する。「動くCoMに対し同じ世界点へ力を再適用」とは別のモデル |
| 世界Lを進め、姿勢は明示的中点回転 | 区間の長さに応じて同じ物理関係を使う。角速度一定に置換せず、gyroscopic効果を維持する |
| 全体を予測した後だけ離散接触生成 | 最初のイベントまで全物体を同じ時刻へ進め、そこで接触を生成する形へ分離する |
| 点速度 `v+omega×r`、世界逆慣性、累積normal impulse、3D Coulomb disk | 瞬間衝撃のsolveを再利用。TOIだけで摩擦・回転応答を代用しない |
| 反発は接触prepare時の接近速度、材料の最大e、閾値未満は0 | バッチ内の全接触についてsolve前の同じ状態から反発targetを固定。反復ごとに反発を再注入しない |
| position correctionは速度と分離した幾何投影 | CCD初段では無効。貫通を大きく許して投影で隠す経路にしない |
| 候補body配列を検証後にcopyしてcommit | 荷重、姿勢、L、接触作業状態、全イベント、残時間を含む1tick単位の原状保持を維持 |
| stable ID順、bounded iterations/contact count | ID順で再現性を保ち、予算超過・残差超過を明示失敗にする。接触や時間を捨てない |

現在の `World::step` は離散接触のAPIとして残す。単にこれをTOI時刻ごとに呼ぶ方法は
荷重を最初の区間で消費し、各終端で投影も行うため採用しない。現在の剛体16試験群には
静止支持・摩擦・転がり・stackの離散近似が含まれるが、その成功をCCD版の持続接触の
検証へ移し替えない。既存planeの単位長許容値とTOI核の許容値にも差がある。
新モードの作業コピーで厳しい単位長条件を検査し、法線とoffsetを同じ長さで正規化する。
満たさない既存入力は明示失敗とし、旧stepの条件は勝手に変更しない。

## 無接触軌道と加速度を含む式

区間開始の状態とheld荷重を使い、動的bodyは `a_i=g+F_i/m_i`、静的bodyは `a_i=0,v_i=0`。
計算した加速度を区間間で一貫して保持する。外力による位置・速度依存の再評価はまだない。
新たな衝撃は速度/Lを変えるが、held外力・世界トルクを消費したり再計算したりしない。

### 球と静的平面: 二次式

単位法線n、offset d、半径Rに対して

```
phi(t) = c + b*t + A*t²
c = n·p0 - d - R          [m]
b = n·v0                 [m/s]
A = (n·a)/2              [m/s²]
```

`A=0` の場合だけ線形式に落とす。小さい非零加速度を閾値で零にしない。
二次根は加算側の根と根の積を使い、小さい入口根の打消しを避ける。両根を `[0,h]` で調べ、
最初の侵入を選ぶ。初期に離反していても、下向き加速度で戻ることがある。初期接近速度
だけで照会を終了しない。接線、重根、判別式の丸め境界は区間で再検査する。
[Kahan §1](https://people.eecs.berkeley.edu/~wkahan/Qdrtcs.pdf)で、安定した二次根と重根付近の
不良条件を確認した。二次式の安定な公式だけで接触の存在・順序の保証が完成するわけではない。

### 二つの球: 一般には四次式

`r=p_B-p_A, v=v_B-v_A, a=a_B-a_A, R=R_A+R_B` とすると

```
F(t) = |r + v*t + a*t²/2|² - R²
     = c0 + c1*t + c2*t² + c3*t³ + c4*t⁴
c0 = r·r - R²
c1 = 2*r·v
c2 = v·v + r·a
c3 = v·a
c4 = (a·a)/4
```

単位は各項の積がm²になる。共通重力だけを受ける二つの動的bodyでは相対加速度が零に
なるが、片側が静的な場合や外力/質量が違う場合は零にならない。線形TOIへのfast pathは、
一貫した加速度snapshotから得た相対加速度が**厳密に零**の場合だけ使う。その結果の
`uncertain`/丸めフラグを確定接触に昇格せず、必要なら加速照会の区間経路で再検査する。

`t=h*u, u in [0,1]` と空間尺度Sを使い、`r/S, v*h/S, a*h²/(2*S), R/S` を扱う。
尺度変換自体にも有限性/underflow検査を行う。四次式の閉形式を初段の本番経路には採らない。
数学上の公式があることと、ほぼ重根・次数低下・係数打消しの下で入口の存在と順番を
安定して認証できることは異なる。導出した式は独立試験や区間評価の照合にも使う。

## 求根方式の比較と採用する境界

| 方式 | 利点 | このWorldでの制限/判断 |
|---|---|---|
| 二次の安定根 / 四次の閉形式 | 低次の明確な根には速い | 二次を候補生成に採用。四次閉形式は初段不採用。根の存在と最初であることを別に検査する |
| 端点だけを調べる二分法 | 符号変化が既知なら簡単 | 同符号の端点の間を往復通過でき、接線/偶数重根も落とすため、探索全体には不十分 |
| 外向き丸めの区間排除+左優先root isolation | 区間全体の安全な非接触判定、入口bracket、未解決の明示ができる | 初段の標準経路。包含に0があるだけで根の存在を認定しない。丸め・接線で決着しなければ失敗 |
| 保守的な線形軌道+膨張半径 | 一定加速度の曲線からのずれを上限付きで包める | broad phase/安全な除外に利用可能。膨張球のヒットを元の球の反発時刻にはしない |
| 距離と速度上限によるconservative advancement | 距離が正なら安全な時間幅を得られる | 接線や持続接触で進捗が消える。加速度を含む上限と進捗検査が必須。初段の唯一の求根器にはしない |

区間排除の原理とfalse negative/過剰な保守性の問題は、著者公開の
[Wang et al. 2021 §5](https://cims.nyu.edu/gcl/papers/2021-CCD.pdf)で確認した。
同論文の主対象は線形に動く頂点/面/辺であり、そこの専用predicateや証明を今回の加速球へ
流用したとは扱わない。以下は本エンジンで導出・実装・試験する方式で、論文コードは転載しない。

1. 基本の加減乗除を外向きに囲む小さな内部interval型を用意する。Native/WASMでround-to-nearest、
   subnormal、`nextafter`、overflow、コンパイラの再結合/FMA規則を検証する。fast-mathは禁止。
2. 入力doubleを点区間とし、相対位置/加速度・係数生成・評価の丸めまで囲む。最終値だけ
   1ulp膨らませる実装にはしない。区間除算で分母が0を含む場合は分割/別式へ回す。
3. `r(t)=r+v*t+a*t²/2` の区間評価を使い、距離二乗の上下限を求める。区間をまたぐ座標の
   二乗の下限は0とする。多項式Horner評価との交差で囲みを狭めてもよい。
4. 全区間で `F>0` なら除外。残った時間区間を左から優先して分割し、手前の区間が安全と
   確認されるまで後ろの根を採用しない。極値を含む区間や偶数重根を端点符号だけで捨てない。
5. 初期が分離し、端点の区間値で `F(lo)>0,F(hi)<0` が証明できれば、連続性から入口の存在が
   分かる。先行区間の除外と組み合わせて最初の入口をbracketする。区間Newton/導関数による
   単調性検査は高速化であり、証明できない区間を消す理由にはしない。
6. 接線候補は衝撃と別。安全なgrazingを証明できればnormal impulseは0。存在も非接触も
   判定できない候補、重根群、隣接doubleまで分割して残る不明区間は `UnresolvedRoot`。
   固定epsilonでmissかhitに丸めて成功にしない。

丸めの区間扱いは [PBRT 4 §6.8](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error)で確認した。
現在の線形核の `roundoff_sensitive` は診断であり、この外向き包含証明の代替ではない。
初段で真の重根を常に分類できるとは約束しない。後続で低次数の符号判定/厳密二進係数の
root isolationを検討し、未解決領域を減らす。新しい数値ライブラリを無断で依存追加しない。

### 線形近似を使うなら、誤差を予算へ含める

開始点の接線 `p0+v0*t` からの相対軌道のずれは、一定相対加速度なら区間hで
`|a_rel|*h²/2` 以下。両端を結ぶ弦からの最大ずれは `|a_rel|*h²/8`。
この量で半径を膨張すれば、膨張軌道が区間全体で非接触の場合に元の軌道も除外できる。
ヒットは候補に過ぎない。加速度や軌道を変えた近似で衝撃を発生させれば、別の物理モデル
になるため、静かに置換しない。保守前進なら `V*h+A*h²/2 < gap` を満たす時間だけ進める。
上限が証明できない荷重には使えない。これらの不等式は今回の軌道式からの導出である。

## 次の縦断 W1: held荷重下の複数球・平面の衝撃

### 新規APIと内部の分離案

以下は次回実装する案であり、現在公開中のABIを変更した宣言ではない。

- 新規 `accelerated.hpp/.cpp`: `AcceleratedSphere{center,velocity,acceleration,radius}` と
  `ToiBracket{kind,t_lower,t_upper,normal,normal_valid,gap_bound,safe_prefix,...}`。
  kindは「非接触を区間全体で確認」「入口存在のbracket」「初期接触」「grazing」「未解決」を
  区別する。単一時刻しか持たない現 `ToiResult` へbracketを押し込まない。
- 新規 `CcdSettings`: 時間/空間/速度誤差条件、総pair照会数、総root node数、分割深さ、
  event数、contact数、solver iterationsと許容残差。単位・上限を検証する。
  W1ではposition correctionを0に限定し、非零指定は拒否する。
- 新規 `World::step_continuous(dt,CcdSettings) -> CcdStepStats`。
  旧 `step` は保持。初段のモード名は「held-load impulsive CCD」で、持続支持対応を示唆しない。
- 内部の `propagate_free(body,held_load,h)` と、時刻固定のcontact生成/prepare/solveを分離する。
  propagationは荷重を消費せず、接触も生成しない。公開tickだけが消費とcommitを所有する。
- `CcdFailure` は理由code、関係stable ID、要求dt、最後の安全な候補時刻、残時間、
  使用予算/残差を持つ。失敗の診断時刻はworldが進んだ時刻ではない。
- `CcdStepStats` は完了dt、event/batch/segment/pair/node/反復数、最小進捗、最大bracket幅、
  接触時の正のgap/貫通上限、solver残差、impulse、投影量/投影仕事、時間破棄量を返す。
  W1の成功では投影量と時間破棄量は0。失敗なら公開状態のadvanced timeは0。

初期の暫定予算案はtick当たり64 event batch、128 propagation segment、1,000,000 pair照会、
4,000,000 interval node、1枝64分割。既存のcontact/iteration上限も守る。
これは性能測定済みの値ではない。1024球+64平面の全組合せは最大589,312組/走査となる。
大きなworldや反復イベントでは総予算に達し得る。将来のbroad phaseでも候補を省く場合は
曲線軌道の包含が必要。初段はO(N²)と予算を明記し、60fps対応とは扱わない。

### 1tickの処理

1. dt・設定・全body/plane・荷重を検証し、worldと荷重の候補コピーを作る。全区間の速度/
   位置の範囲を端点と二次軌道の成分極値から検査する。終点だけが範囲内でも途中で領域外なら失敗。
2. 全候補の区間照会で最初のイベントとbracketを求める。球回転は球proxyのTOIを変えないが、
   接触時姿勢・摩擦・L応答には必要なので全bodyを同じ時刻へ進める。
3. 最初の根より手前が安全と確認された `t_lower` まで進める。そこで接触を少し早く扱う
   場合は、指定された空間誤差内に全接触があることを区間で確認する。これは有限精度の
   contact guardであり、厳密な実数TOIでの衝撃と同一だとは記載しない。
4. `t_upper-t_lower <= time_tolerance` **かつ**
   `V_bound*width + A_bound*width²/2 + propagation_roundoff <= gap_tolerance` を要求する。
   時間幅だけ小さくして高速時の大きな距離誤差を見逃さない。初期提案の絶対条件は
   `time_tolerance=1e-9 s, gap_tolerance=1e-8 m`、最小半径に対するgap許容値の比は `1e-4` 以下。
   小物/大世界などで表現精度が足りなければ値を勝手に緩めず `NumericConditioning`。
5. 順番が区別できるイベントは順番に処理。時間区間が重なる候補はさらに絞るか、明示した
   共通の時空間guard内の同時batchへ入れる。連鎖的な区間重なりで大きくなったbatchを
   無条件に同時扱いしない。全bodyはbatch共通の安全な下端時刻に揃える。
6. その時刻に関係する全接触を安定ID順で生成する。球対の共通接触点は両表面の中点とし、
   早期guardのgapも記録する。同時接触を1対だけ選んで他を次tickへ回さない。
7. 全接触の衝撃前の点速度から反発targetをprepareし、既存のnormal/tangent有効質量と
   Coulomb diskの反復solveを行う。各batchではimpulseを零から開始し、反復内では累積する。
   別時刻の新しい衝撃へ前のbounceやimpulseをそのままwarm startしない。
8. 反復上限だけで成功にせず、normal closing/bounce residual、非負normal impulse、
   friction cone、有限値と所定のエネルギー診断を検査する。不合格なら全tickをrollback。
   同時衝撃のNewton型反発targetは一般に一意な物理解を保証しない。瞬間衝撃で外部の仕事が
   ないのに全運動エネルギーが許容誤差を超えて増える場合も、反復数だけを根拠に成功としない。
9. 新しい速度/Lと同じheld荷重で残時間を再照会する。全時間を消費し、全状態を検証した
   場合だけ荷重を消費してcommitする。ABIの時刻/tickは外側で1回だけ更新する。

残時間は要求dtと累積区間時刻から管理し、加算/減算誤差も検査する。正のhでも累積時刻が
変わらない、必要な残時間が表現できない、event予算に達した、という場合は失敗。
「min_dtだけ進める」「残り時間を零とみなす」「反発を下げる」「摩擦で減衰させて収束させる」
という暗黙の逃げ道は設けない。接触がない経路は従来と同じ1回の中点回転にし、イベント分割
による姿勢の誤差変化は別途収束検査する。角度上限に違反する区間は無音でclampしない。

### 初期重複、零時刻、持続接触

初期に許容誤差を超えて重なるworld、中心一致で必要な法線を得られない球対は初段で拒否する。
従来の固定X法線や大きなposition correctionでCCD成功にはしない。許容誤差内の初期接触も
guardとして数値を報告し、衝撃か持続接触かを速度/加速度から分類する。

反発後や初期接触時に離反しているpairを、そのtick全体からblacklistに入れない。
加速度で同じpairへ再衝突し得るため、t=0の退出根と後の入口根を分けて照会する。
`F(0)=0` の場合は右側の符号を導関数/係数と区間で調べる。分類できなければ失敗。
grazingを処理したpairも、残り軌道の安全性なしに永久除外しない。

`gap≈0, normal_speed≈0` で押し込む加速度がある状態は、衝撃impulseだけでは支持できない。
e=0で床に落ちる球、静止stack、反発の間隔が0へ近づくinelastic collapseは典型例である。
W1では `SustainedContactRequired` / `NoProgress` として全rollbackする。これらを成功させる
ためにWorldを零重力にしたり初期状態を浮かせたりしない。失敗を解析試験で意図的に確認する。
この検査は衝撃solve直後にも行う。guard内の小さい正のgapを理由に微小落下/衝撃を繰り返して
支持対応の代用にしない。速度分類の暫定許容値は `1e-8 m/s` とし、材料の反発抑制閾値とは
分ける。これらの暫定数値は実装前のfixture定義で確定し、結果を見て後から緩めない。

## 持続接触と一般加速Worldへ進む順

衝突と静止接触が別の力学であることは
[Baraff 1997 §6](https://www.cs.cmu.edu/~baraff/sigcourse/notesd2.pdf)で確認した。
衝撃時は速度/Lを変更してODEを再開するが、静止支持には非侵入を保つ接触荷重が必要である。
また [Tedrakeの接触章](https://underactuated.csail.mit.edu/multibody.html)は、イベント駆動の
拘束力学と有限刻みのimpulse/time-steppingを異なるモデルとして整理している。
既存のstep末尾のvelocity solveをdt=0で無限に反復しても、その代わりにはならない。

| 段階 | 実装/受入 | 完了としない範囲 |
|---|---|---|
| A: 加速照会 | 二次/四次のbracket、包含演算、境界・次数低下・未解決を独立試験 | Worldの状態更新や接触応答 |
| W1: 次の縦断 | 上記held-load複数球/静的平面の衝撃CCD、Native→同じC++のWASM→操作lab | 静止支持・stack・浮力接触結合・全World入力での成功 |
| W2a: 持続する球–平面 | active contactを持つ別integrator。まず非零重力/外力下の摩擦なし支持と離脱、複数平面・複数body | 球対の曲率、一般Coulomb摩擦を含む拘束運動の完成 |
| W2b: 球対・摩擦・stack | normal/complementarity残差、最大散逸摩擦、接触の生成/離脱と時刻順序、CCDとの同時solve | 任意の剛体形状や万能な多点衝撃モデル |
| W3: 状態依存荷重 | 浮力・抗力等を中点/必要な内部点で再評価し、軌道誤差/加速度上限を包むCCD | 任意callbackを無条件に連続検出できる保証 |
| W4: 形状/機構拡張 | box/convex/mesh、回転掃引、manifold、joints、車輪/タイヤ/軌条接触を各解析・参照で受入 | 車/航空/鉄道の実機精度を形状追加だけで獲得したという主張 |

W2aは単位平面の接触では `phi_dot=n·v`、`phi_ddot=n·a` を使い、非負normal forceと
非侵入加速度の相補性を解く。外力で床から離れる場合はnormal forceを0にしてfree flightへ
戻す。複数支持を1平面だけの特例で解決したことにはしない。

球対では `phi=|r|-R` に対して
`phi_ddot=n·a_rel + (|v_rel|²-(n·v_rel)²)/|r|`。
法線の曲率項を省くと接線方向に動く接触の支持を誤る。摩擦では点速度と世界逆慣性、
gyroscopic項、接触点/接線基底の変化が必要になる。接触荷重で拘束された軌道は一般に
held外力だけの放物線ではないため、W1の四次式をそのまま使って「一般CCD」としない。

W2では力レベルのactive-set方式と、接触荷重を有限区間impulseとして解くtime-steppingを
小さな独立参照で比較してから選ぶ。後者なら位置/速度更新も同じ離散式から導出し、
現在の厳密な自由並進式と末尾impulseを無検討に混ぜない。free flightにはW1、active contactを
持つ区間には選んだ拘束軌道とその誤差を含むCCDを使う。支持中の別bodyへの高速衝突も受入に入れる。
既存の位置投影を再導入する場合は別オプションとし、投影距離、重力/外力の仕事の変化、
軌道角運動量への影響を記録する。これを保存則の合格に使わない。

W3では現在の `step_isolated_buoyant_body` の1体/接触なし制約を勝手に取り除かない。
荷重callbackは純粋な評価として候補状態へ作用させ、失敗時に外部副作用を残さない規約と
評価回数予算を設ける。自由飛行の数値軌道だけでなく、実モデルからの誤差を囲むための
加速度/jerk等の上限、または検証したdense outputが必要になる。上限なしの任意callbackは拒否する。

## 独立試験・生ログ・失敗条件

実装順は Aの包含演算/照会 → 既存stepを保つ内部分離 → W1単体 → Native CLIの全trajectory →
Native/WASM共通fixtures → ブラウザ操作。既存の剛体・浮力・ABI試験も回帰確認する。

| 試験 | 独立の期待値/検査 |
|---|---|
| 加速平面落下 | `phi0>0,v0=0` の `t=sqrt(2*phi0/g)`、衝突前速度、単一bounce後の区分的放物線 |
| 初期離反して戻る球 | 上向き投射の後の床衝突、同tick内での複数bounce。初期の速度符号だけでは除外しない |
| 相対加速度が非零の球対 | 1軸で `|r+v*t+a*t²/2|=R` を二次式として手で解いた根と四次照会のbracketを比較 |
| 真に3Dの四次/複数根 | 既知の接触時刻/接触位置から入力を構成し、独立な有理係数の符号表/高精度参照を保存。単なる同じ求根器の細刻み版を正解にしない |
| 往復通過/接線/重根 | 同符号の始終点、内点極値、4根、次数低下、近接根。安全な除外/入口bracket/未解決失敗の区別 |
| 複数body+非零重力 | 共通gが相殺する対と、静的球/異なるF/mで相殺しない対を同じworldで検証 |
| 高速衝突と残時間 | 始終点で分離する球対、同tickで球→球→平面の連鎖。最後の自由飛行時間と最終位置まで解析比較 |
| 衝撃の物理 | 2体の質量/反発の解析解、運動量、world-L、e=1/μ=0のエネルギー、摩擦時の散逸とcone |
| 外力・トルクの消費 | eventが0/1/複数でも総力積F*dt、総トルク積tau*dtを確認。衝撃impulseと支持impulseを別に集計 |
| 同時衝撃 | 対称3球・直交2平面。単純に一意な参照を持つケースで対称性/残差を検査し、一般多点の唯一解を主張しない |
| 回転 | 球形慣性/主軸トルクの解析解、世界L、異方慣性のEuler式とdt収束。event分割でgyroscopic挙動が消えない |
| 不変性/精度 | Galilean/平行移動、ID入替の物理結果、空間/時間尺度、horizon端、subnormal/overflow/非単位plane |
| 原状保持 | root/node/pair/event/contact予算、残差、回転角、状態領域、未解決根で失敗させ、全body/荷重/時刻/tickが不変。失敗後の再利用も確認 |
| W1で未対応の支持 | e=0落下後、初期静止球、stack、inelastic collapseを明示失敗。時間破棄や人工減衰でPASSにしない |
| W2以降 | m*g*T支持力積、静止gap/速度、引離し、斜面転がり、接触摩擦/仕事、stack、支持中の別body衝突、刻み収束 |

W1の自由区間では並進エネルギーの変化とheld外力/重力の仕事を比較する。
各瞬間衝撃は同一姿勢/位置で前後の運動量・L・エネルギーを比較する。回転の中点積分誤差、
contact guardによる早期衝撃の時間/位置誤差、同時衝撃の有限反復残差は別に記録する。
摩擦/e<1の散逸を誤差と混同せず、位置投影を有効にした測定で保存則合格を主張しない。

受入の数値条件を実装前にfixtureごとに固定し、dt/許容幅を半分にした収束と、長時間の
誤差を全サンプルで出す。結果を合わせるために抵抗係数や許容値を後から増やさない。
CLI JSON/CSVには全入力、設定、source/build hash、compiler、hardware、全eventのbracket、
gap、impulse、残時間、失敗理由、p50/p95/p99/maxと予算超過を含める。Native/WASMの数値差と
ブラウザ表示の確認は別々に記録する。性能未達/失敗例を除いた平均だけで公開合格にしない。

本計画の作成では外部一次資料の閲覧のみを行った。ライブラリ/SDKの追加、論文コード転載、
実装ファイルの変更、commit/pushは行っていない。

## 実施R0: CCDの前提となる内部分離

2026-11-03 JST、コード原点 `1ebcfc5652191b92efc1632cff5a61d3c3d3fa5b` の後続。
これはA/W1の加速求根やCCD stepの実装ではない。既存public `dynamics.hpp`、C ABI、
一定速度TOI核は変更せず、次を `core/src/dynamics_internal.hpp` に分離した。

- `detail::propagate_free(candidate,gravity,dt,max_angle)` は候補1体を伝播し、held force/torqueを
  保持する。静的bodyは荷重も含め不変。接触の検出/応答/投影を行わない。世界Lと中点姿勢式は従来どおり。
- `detail::solve_contacts_at_current_state(candidates,planes,settings)` は現在の候補姿勢で
  接触生成→prepare→反復solve→任意の既存投影を行う。時間は進めず、force/torqueと姿勢は
  不変。`position_correction=0` なら位置も不変。非零なら従来の幾何投影による位置変更がある。
- 内部APIは検証済み候補/設定/ID順を前提とする。伝播後の状態検査は呼出し側が所有する。
  接触solveは結果を検査するが、例外時の候補内rollbackを約束しない。候補を破棄するのは外側tick。
- 旧 `World::step` は検証・コピー・bodyごとの自由伝播・候補荷重clear・状態再検査・
  接触処理・最終commitを所有する。静的bodyの荷重clearも維持した。候補上では従来と同じ
  時点でclearし、失敗なら原本の荷重/状態は消費されない。新しい公開CCD APIは追加していない。

`tests/dynamics_internal_tests.cpp` の直接10群がPASSした。held荷重保持、同じ荷重を2区間へ
分割した並進/主軸回転の解析解、自由伝播が貫通へ応答しないこと、時刻固定で摩擦/反発により
速度/Lだけが変わる解析例、投影を有効にした従来挙動、接触予算/回転例外後の原本保持と再利用、
成功tickの荷重消費を検証した。これを持続接触対応やCCD完成の実績にはしない。

数値を変えないリファクタであることを、保存した変更前ソースと変更後の同一fixtureで確認した。
MSVC 19.51.36247 x64、C++20、`/O2 /Ob2 /DNDEBUG /MD /W4 /permissive- /fp:precise`。
baseline側は `PP_DYNAMICS_BASELINE_ONLY` を定義して公開Worldのfixture部分だけを実行した。
8ケースは荷重付き自由飛行、斜め摩擦平面、球対（投影あり/なし）、stack、静的/動的荷重消費、
異方慣性回転、多接触+反復荷重である。412時刻・884 body状態、body/統計27,224値を含む
273,422BのJSONが**バイト一致**した。SHA256は
`02C300D2DA56388E09CFC0955AAF9B97DD7D83BAB91ED7FE0A8F63CEEECCC08D`。

既存 `pikapika-simulation-probe --fixtures` の全JSONも変更前Release実行ファイルと再ビルド後で
バイト一致した（SHA256 `667A9CB335D961BAA627068FE3B970ED1623A953951B41D766A83214141CE1A6`）。
浮力の動的trace、free fall/force、TOIを含む公開経路の回帰を別に確認したもので、まだ新ソースの
WASM再生成/実行を測ったものではない。`scripts/build-native.ps1` の既存Release CTestは5/5 PASS。

再現用の `build/native/dynamics-internal-proof/` には `build-baseline.cmd`、`build-after.cmd`、
変更前ソース `baseline/dynamics-before.cpp`、`before.json` / `after.json`、
`simulation-before.json` / `simulation-after.json`、`test-output.txt` と `verification.json` を保持する。
変更前ソースのSHA256は `F4844A20C9A42B04C5BDB0638C3AC117F9BB8442D6A6DC54ED20FCA31AD06DB0`。
baselineを再生成する場合は保存済み変更前ソースをコンパイルし、現在のdynamics.cppで置き換えない。
fixtureの初期状態/荷重・平面・設定は試験原本の `fixtures()` に固定してある。
作業ディレクトリはbuild配下で、公開証拠への転記・CMakeの直接試験登録・WASM依存header記録は統合側で行う。
