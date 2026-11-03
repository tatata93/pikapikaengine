# 位置・方向・法線を囲んだまま次の面へ進む参照核

2026-11-03。独自C++ optical_bounds.hpp/.cpp。既存の点入力の
[面交差](OPTICAL_GEOMETRY.md)と[光学界面](OPTICS_INTERFACE.md)は変更しない。
今回は、交点の丸め区間を次の光線の原点へ引き継ぎ、反射・屈折方向も区間のまま照会する。
レンズ処方、媒質割当て、撮像・収差・ghost・偏光位相の厳密輸送を完成したものではない。
以下は独立kernelの契約とstandalone検証であり、公開ABI・配信WASM・ブラウザの統合検証とは区別する。

## APIと入力族

namespaceは pikapika::optical_bounds。Bounds3は既存の3成分Interval。
BoundedRayは原点と方向の二つのbox、閉じたminimum_parameter..maximum_parameterを持つ。
原点はm、方向は無次元、P(t)=O+t d のtはm。原点からの物理距離は t |d| mであり、
方向を単位長と仮定しない。パラメータ範囲は全入力族に共通の指定値である。

boxの各成分端点を正確な二進有理数として、内部の有限実数をすべて入力族と解釈する。
測定誤差や十進の意図は、呼出し側が端点へ含めない限り対象にならない。
成分間、位置と方向、前面交点と法線の相関はbox化で失われる。そのため次の面で
考える族は実際の光路族の上位集合になり得る。中点へ潰して相関の喪失を隠さない。
この保守的な拡大で判定できなくなった場合も、点入力へ戻して成功させない。

    namespace ob = pikapika::optical_bounds;
    namespace og = pikapika::optical_geometry;
    auto ray = ob::enclose_ray(og::Ray{{0,0,-3}, {0,0,1}, 0,10});
    auto first = ob::intersect(ray, og::FullSphere{{0,0,0},1});
    if (first.status == ob::Status::hit) {
        ob::InterfaceInput interface;
        interface.incident = ray.direction;
        interface.normal = first.nearest->incident_normal;
        interface.index_incident = 1;
        interface.index_transmitted = 1.5;
        auto boundary = ob::dielectric_interface(interface);
        if (boundary.kind == ob::InterfaceKind::transmission) {
            auto continued = ob::spawn_ray(*first.nearest, *boundary.transmitted, 0,10);
            auto next = ob::intersect(continued, og::FullSphere{{0,0,3},1});
            // next.nearest encloses the accepted family, never a midpoint ray.
        }
    }

enclose(Vec3)は成分を点区間へ包む補助。spawn_rayは交点boxと出射方向boxを
そのままコピーし、明示した新しいパラメータ範囲を検査する。法線反転・媒質の順序・面の
巡回順序は呼出し側が指定する。元の面の無視、原点オフセット、隠れたepsilonはない。
同じ平面へのt=0が証明できればその交差を返し、同じ球面上のboxがt=0をまたげば未解決になる。
正のt開始を指定すれば、その手前の領域を意図的に除外する。これを安全なself-hit除去の
証明として扱わない。

## 全族に対する成功と存在

intersectは既存の点形状PlaneDisk / FullSphere / SphericalCapを受ける。
形状の寸法・位置・軸は点入力、光線だけがbox入力である。

| Status | 主張する内容 |
|---|---|
| hit | すべての族員で同じ順番の最初の有効根が存在し、指定範囲・面・開口を満たす。根、交点、実単位法線、物理距離を出力区間で包含する |
| miss | どの族員も、指定した面と指定範囲に有効な根を持たない |
| unresolved | 存在、最初の根、選別、向き、幅、数値域のどれかを証明できない。成功交点は空 |

一部の族員だけの交差、一部だけの開口通過、単に式が0を含む状態はhitではない。
サンプリング結果の一致も全族の存在証明には使わない。
missは他の面やパラメータ範囲外まで含めた全光路の不在を意味しない。
すべての面の比較・遮蔽やsurface順序は、この単一面APIの外である。

平面ではn·dが族全体で零を避ければ、各族員にただ一つの実根
t = n·(C−O)/(n·d)がある。区間商がその根族を包む。分母に0の可能性があれば
parallel_or_coplanar。分母が厳密に零、分子が零を避ける場合だけ平行missとする。
得られた位置boxは、平面の線形拘束を各座標について解いた区間と交差して縮める。
これは丸めた中点を平面へ投影する操作ではなく、すでに存在を証明した根の包含の精錬である。
円形開口は真の単位軸Aに対する |(P−C)×A|²−aperture² で選別する。

球では原boxから、係数を先にdoubleへ丸めず

    A = |d|²
    H = (O−C)·d
    Cq = |O−C|²−R²
    Delta = H²−A Cq

を区間で構成する。A.lower>0かつDelta.lower>0なら、族員ごとに二つの異なる実根が
存在する。数学的に小さい根/大きい根のラベルを維持し、符号が確定したHでは
q=−H±sqrt(Delta), q/A, Cq/q、それ以外は直接の二次式を外向きに評価する。
根区間が重なっても、各族員の根の数学的順序は失われない。
Delta.upper<0だけを実根なしとし、0を含む場合は接線/混在/丸めを分け切れず未解決にする。

候補根は小さい側から調べる。範囲外・開口外・cap半球外を全族で証明できた場合のみ
その根を棄却して次へ進む。前根が未解決なら遠根の成功だけを採用しない。
cap中心は原軸の実数正規化からV+R Aを区間で作り、頂点側の半球と射影開口をともに検査する。
軸の通常double正規化や丸め中心を確定形状に置き換えていない。

採用する根ではd·geometric_normalの符号も全族で確定させる。
球/capのgeometric normalは球の外向き、平面は指定法線側。
incident_normalは全族で入射側へ向くよう必要なら反転する。
向きが族内で混じる場合はorientation。表面にある真の法線が実単位長であるという
既知の拘束で各成分を[-1,1]と交差できるが、概算ベクトルの再正規化ではない。

## 反射・Snellとパワーの包含

InterfaceInputのincident/normalがboxで、normalは入射媒質側を向く。
従来のInterfaceInputは、ni/ntと真空波長を指定した波長における点double値として受ける。
dielectric_interfaceは、元doubleを正確な点区間へ包んで下記の新核へ委譲する。
旧302族の3760出力端点はこの拡張前後でビット一致を維持した。

IndexBoundsInterfaceInputとdielectric_interface_boundsは、ni/ntも閉区間として受ける。
各指数端点全体が[1e−6,1e6]内でなければ拒否し、中心・一端・サンプルへ選び直さない。
ni/ntは独立した実数族である。両区間の値が見かけ上同じでも、幅があれば同一媒質とは扱わない。
等媒質の透明特例を使えるのは、両方が同じ一点の場合だけである。
例えばni=nt=[1,2]を独立入力とすると、ni=1/nt=2とni=2/nt=1も含まれる。
斜入射では透過と全反射が混じり得るため、同じ区間という理由で透過identityにはしない。

真空波長は両APIとも一点の有限正m値であり、同じ波長で与えられた指数族を解釈する。
非吸収・等方・正の実屈折率・等しい透磁率という既存モデルを使う。材質表や分散を自動評価しない。
別核dispersion::evaluateが、指定した点波長で返したphase区間をそのままni/ntへ渡せる。
within_interface_domainを確認し、phaseの全端点を保持する。derivativeやgroupを位相指数と取り違えない。
非点の波長帯を点波長のprovenanceで表すAPIではなく、波長と指数の相関輸送は今後の別契約である。

    const double wavelength = 0x1p-20; // vacuum metres, ONE wavelength
    const auto phase = pikapika::optics::dispersion::evaluate(
        pikapika::optics::dispersion::Cauchy{
            1.5,0x1p-44,0x1p-88,{0x1p-21,0x1p-19}},
        {wavelength,wavelength});
    if (phase.values && phase.values->within_interface_domain) {
        ob::IndexBoundsInterfaceInput interface;
        interface.incident = ob::enclose(Vec3{3,-4,0});
        interface.index_transmitted = phase.values->phase; // whole interval
        interface.vacuum_wavelength_m = wavelength;
        auto response = ob::dielectric_interface_bounds(interface);
    }

零方向/零法線を含むbox、または長さの正の下限を証明できないboxは、正規化せず
zero_direction / zero_normalの未解決にする。内積が全族で正なら向き逆として拒否する。
内積が混在/丸めで0を含めばincident_side。内積区間が厳密に[0,0]のときだけ
全族が接線である片側極限を許す。等屈折率の透明特例も向きの検査の後である。

    D = nt² |i|² |n|² − ni² |i×n|²
    sin²(i) = |i×n|² / (|i|² |n|²)
    ci = −(i·n)/(|i||n|) = sqrt(1−sin²(i))
    ct² = D / (nt² |i|² |n|²) = 1−(ni/nt)² sin²(i)
    reflected   = unit(i) + 2 ci unit(n)
    transmitted = (ni/nt) unit(i) + ((ni/nt)ci−ct) unit(n)

Dの厳密な正/負だけで族全体の透過/全反射を分類する。ni/ntの平方・比・D・Fresnel式の全段階に
原index区間を使う。Dが0を含む場合は
critical_angleとし、出射方向とパワーは空。数学的に等しい二つのci/ct²の式の包含を
交差して精錬する。sqrt・正規化・方向もすべて区間演算で構成する。
出射の真の方向は実単位長だが、そのbox内の任意のベクトルまで単位長であるとは言わない。
次の幾何照会では、非単位の成分組合せも含む保守的な上位族として扱われる。

透過時のs/p normal fluxを

    Rs = ((ni ci−nt ct)/(ni ci+nt ct))²
    Rp = ((nt ci−ni ct)/(nt ci+ni ct))²
    Ts = 4 ni nt ci ct / (ni ci+nt ct)²
    Tp = 4 ni nt ci ct / (nt ci+ni ct)²

からそれぞれ区間で計算する。Tを単に1−Rから代入する実装ではない。
非吸収の既知拘束[0,1]との交差を使い、無偏光はs/pの平均を囲む。
全反射ではR=1/T=0、同じ一点の等媒質ではR=0/T=1を解析的に返す。
接線では入射法線fluxが0なので、通常の0/0の比ではなく指定側からの極限である。
電場振幅、放射輝度倍率、Stokes/Jonesの複素位相や光路間干渉の保証とは別である。

## 平方根、品質、数値域

sqrtは通常libmの丸めを仮定しない。非負端点ごとに[0,max(1,x)]から二分し、
midの区間二乗と端点の大小関係で囲みを縮める。二乗が重なる場合も
|sqrt(x)−m|=|x−m²|/(sqrt(x)+m)と正の分母下限で包含を精錬する。
0と1の平方根は解析的な点。一般区間のsqrtは端点単調性から上下を組み立てる。
予算到達はrefinement_limitedへ残す。粗い囲みでも全条件を証明できれば成功できるが、
幅・符号が確定しなければrefinement_budgetで未解決になる。予算到達を精密解と呼ばない。

Settings.maximum_parameter_widthは丸めだけでなく、族全体の実際のt変動も含む上限。
既定1e6 parameter m、設定可能(0,1e6]。狭い誤差を必要とする呼出し側は明示的に狭める。
平方根精錬は端点ごとに1..256回、既定128回。候補は最大二根で、族の再分割はまだない。
既定の広い幅は科学精度の一律保証ではない。出力区間の幅をそのまま評価する必要がある。

原点/方向/法線の各有限端点は絶対値1e6以下、原点はm。零を含む族は上記の未解決。
形状寸法は既存と同じ: 位置成分絶対値1e6以下、軸最大成分[1e−6,1e6]、
半径/開口[1e−6,1e6] m、cap開口≦|符号付き半径|。0≦t開始≦t終了≦1e9。
ni/ntは[1e−6,1e6]、波長は有限正m。NaN/無限端点・逆順・数値域外は拒否する。
出力boxが次の入力域をはみ出した場合もspawn_rayは拒否し、勝手にclipしない。
零に近すぎてノルム・積の正の下限を保てない場合も成功させない。

IEEE binary64、round-to-nearest、gradual underflow、既存intervalの実行環境検査が前提。
Nativeはsourceを /fp:strict、Clangは -fno-fast-math -ffp-contract=off で独立ビルドする。
Native Clang/GCC profileはさらに -frounding-math を使う。WASMは仕様のnearest固定。
FMAの式への再結合、fast-math、FTZ/DAZ、検証外のLTO profileで同じ保証を主張しない。
これは数学的な包含に沿った実装契約であり、コンパイラ全体の形式検証ではない。

## 独立検証と残る範囲

tests/optical_bounds_tests.cppのNative/実WASMはともに20群PASS。平面の全族実根、t/距離、
範囲・開口・向きの混在、球の二根とcap後根、傾斜軸と負半径、零ベクトル、
4% normal/Brewster/TIR/等媒質/臨界、厳密接線の片側極限と向き判定の順序、幅と精錬の上限を確認する。
平面→屈折→次の平面、点球→屈折→次の球、反射→別平面を区間のまま実行する。
元の面へのt=0/未解決も残す。点縮退では旧核の分類と整合し出力を比較する。
さらに指数のnormal反射・臨界混合・同じ非点区間・全族TIR・独立指数と方向/法線のcorner128点・
内部19点・Cauchy phase端点2点の合計149点を、電場透過振幅と法線Poynting fluxから別計算する。
点波長Cauchy/Sellmeierのphase区間を全幅保持してつなぎ、次平面までの継続も実行する。
162の幾何サンプルと149の指数サンプルのlong-double/旧点核との整合は診断であり、全族の証明ではない。

ignored build/optical-bounds-proof/verify-bounds.pyはIEEEビットを整数/Fractionで復号し、
浮動小数点の再計算を参照値に使わない。302族で1880区間を検査する。
平面120族と軸上球120族はt根/実距離の厳密有理端点、cap背面60族は二根順と採用遠根、
2例は3-4-5のBrewster（ni4→nt3、方向(4/5,−3/5)、Rs49/625/Ts576/625/Rp0/Tp1）と
軸長が異なるnormal族（R1/25/T24/25）である。Python -Oを拒否し、case数も固定する。
これはこの有限corpusの独立照合で、あらゆる形状/入力の形式証明ではない。

追加の --index-oracle とverify-index-bounds.pyは、既存302族を変更せず、別の111指数族・
1110区間を検査する。100のnormal族はni上端<nt下端を満たし、eta=ni/ntに対して
R=((1−eta)/(1+eta))²が単調減少、T=4eta/(1+eta)²が単調増加なので、
独立ni/nt区間全体の反射/透過極値を厳密有理端点から得られる。
残る11族は固定3-4-5入射でeta<1。屈折方向x=3eta/5、y=−sqrt(1−9eta²/25)の単調性を使う。
Fresnel sではeta*ci/ctが増加し、pではg=eta*ctの導関数
g′=(1−18eta²/25)/ctが正、g<ci=4/5なので、Rs/Rpは減少、Ts/Tpは増加する。
よって両端の解析値で**連続指数族全体**を検査できる。この単調性は任意角度・任意etaの一般主張ではない。
参照平方根はFractionとinteger isqrtによる256ビットの有理囲みを使い、
電場透過振幅と法線fluxからパワーを別評価する。
最後の1族はλ=2⁻²⁰mのCauchy phase、正確なn=401/256を含む非点出力区間の全幅である。
ni/ntを同じ点へ潰す実装や、同じ幅のindexを透明化する実装はこれらの試験を通らない。

独立Native buildはMSVC 19.51.36247.0 / Windows SDK10.0.26100.0 / CMake4.3.3、
実WASMは既設の公式Emscripten6.0.13 / Node24.14.1で実行した。
Native/WASMの同302族は、出力区間の3760端点がビット一致し、両方がFraction参照を包含した。
追加111指数族の2220端点も両環境でビット一致し、両方が独立参照を包含した。
同一計算の一致だけを包含証明に使っていない。standalone WASMは262051 bytes、
SHA256 586E0A498B1478F660B055931EF2C4DBC2C8C3493995853FEABAF0FBB41D3C2F。
このartifactはignoredの実測証拠で、主配信モジュールの更新ではない。

再現コマンド（リポジトリroot、既設SDK）:

    cmake -S build/optical-bounds-proof -B build/optical-bounds-proof/native -A x64
    cmake --build build/optical-bounds-proof/native --config Release
    build/optical-bounds-proof/native/Release/optical-bounds-tests.exe
    build/optical-bounds-proof/native/Release/optical-bounds-tests.exe --oracle > build/optical-bounds-proof/native.csv
    build/toolchains/emsdk/upstream/emscripten/em++.exe core/src/interval.cpp core/src/optical_geometry.cpp core/src/optics.cpp core/src/dispersion.cpp core/src/optical_bounds.cpp tests/optical_bounds_tests.cpp -Icore/include -std=c++20 -O2 -Wall -Wextra -Wpedantic -fno-fast-math -ffp-contract=off -fwasm-exceptions -sENVIRONMENT=node -sWASM_ASYNC_COMPILATION=0 -o build/optical-bounds-proof/optical-bounds-tests.cjs
    node build/optical-bounds-proof/optical-bounds-tests.cjs
    node build/optical-bounds-proof/optical-bounds-tests.cjs --oracle > build/optical-bounds-proof/wasm.csv
    python build/optical-bounds-proof/verify-bounds.py build/optical-bounds-proof/native.csv build/optical-bounds-proof/wasm.csv
    build/optical-bounds-proof/native/Release/optical-bounds-tests.exe --index-oracle > build/optical-bounds-proof/native-index.csv
    node build/optical-bounds-proof/optical-bounds-tests.cjs --index-oracle > build/optical-bounds-proof/wasm-index.csv
    python build/optical-bounds-proof/verify-index-bounds.py build/optical-bounds-proof/native-index.csv build/optical-bounds-proof/wasm-index.csv

通常の広いsphere族は係数の依存性でDeltaを確定できず、実際には全部当たる族でも
保守的に未解決になり得る。族の分割、相関付き表現、interval Newton、形状自身の
寸法誤差、波長との相関を持つ分散族、媒質・面順の選択、偏光位相、厳密なself-hit除去、
レンズ全体の収差/撮像/ghostは今後の範囲である。

## 一次資料と来歴

2026-11-03に本文を再閲覧:
[PBRT4 §6.8](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error)の交点丸めと次ray原点、
[§6.2](https://pbr-book.org/4ed/Shapes/Spheres)の二次曲面交差、
[§9.3](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission)の幾何光学と界面の前提。
原入力族の全称存在・一律root選別・境界未解決・plane拘束のbox精錬は本核の契約として構成した。
書籍のコード/図/本文、外部数学・交差ライブラリ、測定材質データは取り込んでいない。
エンジンのライセンス選定は行っていない。


## 共通出力への接続

主C ABIのbounded geometry25→41とbounded interface19→59に接続。
JS `queryBoundedSurface` / `queryBoundedInterface` は点成分または[lo,hi]を受け、
全区間をコピーして渡す。indexはそれぞれ独立な区間で、同じ非点区間を同一指数へ潰さない。
既存302族/3760端点bitと追加111指数族/2220端点bitを主ABIでも再送して比較する。
親のcheckerは入力tag/ID/列数/全例数も確認し、切り詰めやPython -Oを拒否する。
主ABIは方向/位置の中央値を作らず、次の指定光路へ全boxを継続できる。
最終証拠は `reports/route-support-verification.json`。interfaceでのmaximumParameterWidthは
共有Settingsの入力検査だけに使い、幾何のt幅以外の誤差許容値とは解釈しない。
