# Held-load World CCD — W1

`World::step_continuous(dt, CcdSettings)` は、既存の球剛体・静的平面を、一定の world force/torque を保持しながら衝撃間で進める最初の実装である。`World::step` は従来どおりの離散接触法であり、呼出し・演算順・投影を変更していない。W1 は接線、初期境界、持続的な支持、任意形状、加速度が状態依存の流体連成、車輪/翼/レールの完成した接触モデルではない。

## 公開動作

```cpp
auto report = world.step_continuous(1.0/120.0);
if (!report.success) {
    // report.failure/message と pair IDs を表示して、設定/モデルを修正する。
    // body、force、torque は呼出し前のまま。部分的に進んだWorldはない。
}
```

SI 単位、右手系、+Y up。`dt` は `(0,0.1]` s。force [N] と torque [N m] は **tick全体で一定の world-frame荷重**。各bodyの並進加速度は `g+F/m`。静的bodyは不動。衝撃で変わった速度を初期値として、全bodyを同じ残区間だけ再び進める。負荷を衝撃ごとに消費したり、衝撃のなかったbodyの時刻を止めたりしない。

公開成功時だけ、全bodyの検証、荷重の一回消費、既存storageへのcopyを行う。成功・失敗とも既存のbody pointerを置き換えない。静的bodyに直接設定された非zero荷重も、成功時には旧stepと同様に消費する。失敗時の `advanced_dt` は必ず0。`candidate_time`、event配列、solver統計は破棄した候補の診断であり、部分commitではない。World自体に時計はなく、上位runtimeは成功時だけtime/tickを更新する。

通常の不正入力・未対応・予算不足は `CcdReport` の失敗で返す。入力設定・bodyの不正、初期接触、未解決照会、各種予算、幾何guard不足、自由伝播失敗、solver失敗、支持モデル要求、その他数値失敗を `CcdFailure` で区別する。メモリ枯渇時の診断文字列確保まで保証する `noexcept` APIではない。Worldの同時書込みは未対応。

## 検出・伝播・応答

各残区間の先頭で、すべての動的body-平面と少なくとも一方が動的な球対を照会する。候補はstable ID順。Broadphaseによる省略はまだない。

1. `accelerated::sphere_sphere/plane` に**元の半径**を渡す。加速度入力は既存propagatorと同じ binary64演算で得た値。正の連続prefixと負のwitnessを持つentryだけを衝撃候補とし、zeroを含むだけの区間は接触として応答しない。全残区間が証明排除されたときだけnoneとして進む。
2. 最も早いentry bracketを選び、重なるentry候補をbatchにする。先行・同時の可能性が残る別pairがunresolvedなら全tickを失敗させる。遠い将来のunresolvedは、そこまで進まないため、最初の衝撃後に新状態から再照会できる。
3. 元照会のsafe下端より少し前の時刻を選ぶ。後述する位置誤差で膨張した半径について、その自由区間**全体**がnoneであることを別照会で要求する。膨張照会のentryを物理的なentryと取り違えない。これは接線を膨張して反発させることを防ぐためにも必要。
4. 全bodyを選択時刻まで進める。現在の候補形状について正のgapと、gap・伝播誤差の空間guardを検証する。さらに元の `F/m+g` を点入力からintervalで再構成し、元照会の負witness時刻で本当に負であることを再検証する。係数丸めで存在証明が失われる場合はunresolvedに戻す。
5. 選択したcontactだけを、位置・姿勢・荷重・時刻を変えず既存の逐次impulse solverで解く。全contactの反発targetを衝撃前にprepareしてからbounded iterationする。位置投影は禁止。法線反発、Coulomb摩擦、作用点torque、有効質量は旧solverを再利用する。
6. 有限状態、反発/閉速度residual、batch前後の運動エネルギーを監査し、残区間を最初から再照会する。solverの力学的な近似を、無誤差の厳密解と呼ばない。

応答位置では形状はまだ正のgapを持つ。球対の作用点は向かい合う球面点の中点、平面では球面点を使う。これはgap以内の早期接触モデルであり、正確な一点TOIへ位置を投影したものではない。応答後も同じ相手を**再照会**する。pair blacklist、固定epsilon時間の無視、残時間の破棄、solver反復数の無断削減は行わない。

`CcdEvent.entry_lower/upper` は生の丸め加速度TOI bracketではない。膨張guardで安全を証明した応答時刻を下端、**実数としての保持荷重**で確認した負witnessを上端とする保守的なentry bracketである。候補の応答時計は `responded_at`。batchはその合併区間を返す。早期応答がすでに速度を変えるので、上端の負witnessは「応答しなかった自由軌道」に対する存在証明である。

## 有限精度guardの契約

`interval.hpp` と同じbinary64、round-to-nearest、gradual underflow、非fast-math契約を使う。`continuous_world.cpp` はstrict FPでコンパイルする。旧 `dynamics.cpp` とそのpropagatorの演算順・従来flagsは保持する。LTOで演算境界を融合する構成は、この検証profileには含まない。

並進は `p(t)=p0+v0*t+(g+F/m)*t²/2`。`F/m+g` の各演算をintervalで構成し、propagatorが使う丸め加速度との差を `t²/2` 倍して含める。位置の丸めは実装の演算graph

```
q=fl(0.5*t), s=fl(q*t), u=fl(a*s), z=fl(v*t), x=fl(p+z), p'=fl(x+u)
```

の各primitiveで絶対誤差を伝播する。各primitiveの結果の絶対値上限 `M` に対し、`nextafter(M,+inf)-M` の外向き上限をlocal rounding boundとする。operand誤差の積・和もintervalで上方へ伝播する。これにより、単に `epsilon*|p'|` とする計算とは異なり、相殺・binade境界・subnormal中間値を含める。三成分の誤差の和はEuclidean位置誤差の上界になる。自由区間後には、実際のコンパイル済み位置出力がこの演算graph包含に入ることも検査する。

各bodyの半径を、この誤差以上の表現可能な値まで膨張させる。丸め加速度の軌道が膨張した相手から全区間分離していれば、実数 `F/m+g` の自由軌道と、端点の丸め位置も元形状から分離する。各自由区間は**現在の表現済み状態**からの保証である。衝撃solverの丸め・早期impulse・姿勢積分を含む理想剛体運動全体への厳密な前方誤差証明ではない。

local伝播誤差は `spatial_tolerance/32` 以下、tick内の最大body丸め誤差を区間ごとに加算した量は `spatial_tolerance/16` 以下を要求する。eventの空間guardは、現在の実測gapの包含上限 + pairのlocal伝播誤差 + 蓄積丸め誤差の2倍で、`spatial_tolerance` 以下。誤差床がguardより大きい大座標は、質を黙って下げず失敗する。距離の平方根は `hypot` を初期推定に使うが、その上下候補をinterval二乗で証明し、証明できなければ失敗する。

query時刻幅と早期backoffの初期値は `time_tolerance/4`。相対速度の成分和の見積りに応じて `spatial_tolerance/(16*speed_bound)` 以下へ狭める。これは探索のheuristicであり、最終的な時間・空間guardの検証を置き換えない。速い物体を大きな距離の手前で反発させて合格にしない。

実際に積分した各binary64区間長の和もintervalで保持する。`time_roundoff` はその和と要求 `dt` の差の絶対値上限で、`time_tolerance/16` 以下を要求する。残時間を意図的に落とす閾値はないが、実数としてdtと完全に等しい時間和まで約束するAPIではない。報告するentry時刻の上下端は、この時計の外向き包含を含む。

`maximum_propagation_error` は最大のlocal位置誤差上界、`accumulated_position_roundoff` は上記の蓄積量。これらは早期impulseが作る理想運動との差や回転のglobal誤差ではない。orientationは旧実装と同じworld angular momentumとmidpoint姿勢更新。異方性のジャイロ挙動は保持するが、その回転積分誤差をintervalで証明したわけではない。

## 予算・未対応・失敗

既定値は time guard `1e-7 s`、space guard `1e-6 m`、最大32 event batches、65 free segments、100000 pair queries、1000000 total root evaluations。元半径照会とguard照会の**両方**を数える。1照会は32768 evaluations、4096 frontier、64 depth。solverは16反復。設定上限はheader/validationに明記しており、budgetを超えたcontactやpairを捨てない。

`spatial_tolerance` は `[1e-12,1e-2] m` かつ全半径の0.001倍以下、`time_tolerance` は `[1e-12,1e-3] s`。既存bodyの数・state domainに加え、加速度成分は `1e12 m/s²` 以下。自由区間全体の位置・速度包含が既存domainを超える場合も失敗する。bounded intervalの過大評価による保守的な拒否はあり得る。

初期overlap、正確な境界、離反中でも初期boundary、接線、負witnessのないhorizon終点、近接が誤差膨張幅以下、TOI予算不足は成功/noneに変換しない。W1はstrictly separatedな初期状態から始める。

法線衝突速度が既定 `1e-6 m/s` 以下ならW2支持モデルを要求する。反発後に法線速度がこの範囲で、相対法線加速度（球対は曲率項も含む）が内向きなら、反発係数0の重力支持を微小bounceで隠さず `sustained_contact_required` にする。反発が繰り返される場合にもevent budgetを使い果たせば全tick失敗する。積み重ね、静止摩擦を持つ支持、接触中の外力再配分、Zeno収束の処理はW2の仕事である。

同時多点の逐次Newton反発は一意の物理解を一般に定義しない。W1はstableなprepare/solve順、閉速度residual（既定 `1e-7 m/s`）、運動エネルギー非増加の監査（既定 `1e-10*max(1 J,E_before)`）を要求する有限反復モデル。監査はbinary64の数値検査であり、任意多点に対する厳密な保存量証明ではない。摩擦や反発係数<1ではエネルギーは減る。重力・保持外力・torqueは仕事をするので、tick全体の運動エネルギー保存は要求しない。

## Native検証

独立proof directory: `build/continuous-world-proof/`。MSVC 19.51.36247 x64、C++20 `/O2 /MD`、新kernel `/fp:strict`、旧dynamics `/fp:precise`。依存する既存interval/acceleratedはRelease libraryのstrict版。CMake統合は親開発タスクが行う。

`tests/continuous_world_tests.cpp` は解析解を別に置いた試験を含む。重力とF/mが異なる球対、10000 m/sの球-平面、非零重力中の同tick3壁反射、3body衝撃連鎖、同時batch、静的球、傾いた平面、Galilean変換、異方性bodyの主軸torque、摩擦による角力積、guardを縮める収束、失敗後再利用を検査する。曲がる相対軌道では `(-2+24t)^2+(240t²)^2-1` の最初のentry `t=0.05 s` を使う。初期境界/支持/接線、contact/event/segment/query/root予算、角度刻み、solver残差、大座標誤差の失敗が、荷重を含めたWorld全stateを戻すことも検査する。

旧stepは既存8fixture・412時点・884body状態のJSON **273422 bytesがbyte一致**。SHA256 `02c300d2da56388e09cfc0955aaf9b97dd7d83bab91ed7fe0a8f63ceeeccc08d`。この比較は新stepの力学的正しさの証明ではなく、従来stepに数値変更を加えていない回帰証拠である。

`--fixtures` は3衝撃corridorのevent bracket/gap/誤差と最終bodyをJSONに出す。raw log・fixture・前後JSON・build commandはproof directoryへ保存する。ブラウザ描画性能、長時間支持安定性、DCS級精度の証拠ではない。

最終Native実行は **21試験群PASS**。既定corridorは16 pair照会（元半径とguardを含む）、219 root evaluations、4自由区間、3衝撃。最大local位置誤差上界 `2.6752659115780761e-15 m`、蓄積丸め上界 `8.680841039546707e-15 m`、時間和の誤差上界 `2.0816681711721688e-17 s`。解析的な最終x=0に対し、space guard `1e-4 / 1e-6 / 1e-8 m` の絶対誤差はそれぞれ `2.075205671314695e-5 / 4.818372644210811e-7 / 5.089697219240463e-9 m`。これはこの解析例での収束測定であり、任意多点のglobal精度次数を証明しない。

新dynamics objectへ再リンクした既存試験も、core15、dynamics16、internal10、hydrostatics20、C ABI23群PASS。調整中に実数荷重witnessを絶対位置から別々に構成して、平行移動したpairの包含が無用に広がる失敗を検出した。相対位置/速度の入力差を先に取る構成へ修正し、許容値を広げずに同じ独立解析試験を通した。

## 調査した一次資料

- [Baraff, SIGGRAPH 1997, Rigid Body Simulation II §6](https://www.cs.cmu.edu/~baraff/sigcourse/notesd2.pdf): 衝撃で積分を停止・速度を変えて再開するモデルと、支持力を扱う接触を区別する。W1/W2分離の根拠。
- [Pharr, Jakob, Humphreys, PBRT 4e §6.8](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error): 交差点の丸め誤差と固定epsilonの問題。W1は資料のray offset処理を転載せず、独自の伝播演算graphと半径guardを構成した。
- [Wang et al., 2021, A Large Scale Benchmark and an Inclusion-Based Algorithm for CCD](https://cims.nyu.edu/gcl/papers/2021-CCD.pdf): conservative inclusionの過大判定と検出/応答の区別。W1は論文のmesh kernel実装ではなく、自作の一定加速度球/平面核を呼ぶ。

資料は2026-11-03に実閲覧。外部solver/libraryや論文コードの転載なし。

## 共有ABIと操作ラボへの統合

後続で主CMake/実WASMへ統合した。`World.stepContinuous(dt,settings)`は1tickのreportと
全eventをコピーして返す。失敗reportはsuccess=falseで、state/荷重/World時計/tickを維持する。
ABIの入力数や上限が不正ならC statusを失敗にして先行outputを保持する。
last CCD attemptのeventは失敗候補も診断として保存し、次attempt/reset/destroyまで維持する。
他のWorld編集に追従して書き換わる現在stateの履歴とは扱わない。

主APIの4つの実WASM試験と、完全入力fixtureから再構築したNative/WASM41値比較が成功。
MSVC比較の最大差0はその実行の観測。独立corridorの最終X=0に対する誤差はspace guard
1e−4/1e−6/1e−8mで2.0752056713146949e−5/4.818372644210811e−7/5.0896972192404633e−9m。
[Worldラボ](../tools/continuous-world-lab.html)は9つの実WASM/操作試験が成功。
公開経路の配列と予算は[SIMULATION_ABI.md](SIMULATION_ABI.md)。
独立buildのprovenance内doc hashは追記前の原本で、現在の本書のhashとは区別する。
