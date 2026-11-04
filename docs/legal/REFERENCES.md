# 一次資料の確認記録

確認日はいずれも2026-11-03。教材本文・図・コードは独自作成で、下記資料の図版やコードを転載していません。リンクの掲載を、対象分野全体の研究・許諾確認の完了とは扱いません。

| 資料 | 確認した内容 | この版への適用・限界 |
|---|---|---|
| [ECMA-262, Math.sin](https://tc39.es/ecma262/multipage/numbers-and-dates.html#sec-math.sin) | sinの引数がradであること、実装近似のNumber値であること | 炎デモの角度と単位の説明。2027版表記のLiving Specificationを閲覧。異なる実装のビット一致は主張しない |
| [WHATWG HTML, Animation frames](https://html.spec.whatwg.org/multipage/imagebitmap-and-animations.html#animation-frames) | requestAnimationFrameのコールバック、タイムスタンプ、取消の仕組み | 炎デモの描画呼出し。閲覧ページの更新日2026-10-30。fpsそのものの保証ではない |
| [WHATWG HTML, Event loop processing](https://html.spec.whatwg.org/multipage/webappapis.html#event-loop-processing-model) | 描画機会の決定と、非表示状態等に応じた制限 | フレーム時間教材。コールバック数と実提示数を区別 |
| [NASA Glenn, Speed of Sound Interactive](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/speed-of-sound-interactive/) | 音は媒質中の小さな擾乱として伝わること、音速は気体状態・温度に依存すること | 音響教材の前提確認。343m/sは本教材の仮定でありNASAの実測値という主張ではない。ソースやアプレットは取り込まない |
| [W3C WebGPU, 2026-09-15](https://www.w3.org/TR/2026/CRD-webgpu-20260915/) | GPU描画・計算API、`navigator.gpu`、`GPUDevice`、canvas、SecureContextの条件 | 実装はWebGPUへ直接接続。Candidate Recommendation Draftで、すべての端末での利用保証ではない |
| [W3C WGSL, 2026-10-26](https://www.w3.org/TR/2026/CRD-WGSL-20261026/) | WebGPUのシェーディング言語、頂点・フラグメント処理 | `engine/renderer.mjs`内の自作WGSL。Candidate Recommendation Draftの版を記録 |
| [Walterほか, Microfacet Models for Refraction through Rough Surfaces, 2007](https://www.cs.cornell.edu/~srm/publications/EGSR07-btdf.pdf) | §3の微小面による反射・散乱モデル、§5.2のGGX分布の位置づけ | ブラウザ版のGGX分布を理解する一次資料。屈折モデルや論文の実測比較を実装済みとは扱わない。図・コードの転載なし |

## 独自に置いた前提と導出

- 固定刻みの概念コードは教材用に新規記述。実際のエンジンAPIではない。追いつき更新の上限、再現性、接触安定性の詳細は実装試験と併せて拡張する。
- 音の距離モデルは、一様な自由音場の点音源、球面へのエネルギー保存から強度1/d²、振幅1/dを導出。343m/s、基準距離1mを仮定。近距離ゲインのクランプはゲーム用近似。
- 炎はsinと自作の1次元値ノイズ。3u²−2u³で隣接する疑似乱数値を補間する。既存のPerlinノイズの実装を転載したものではなく、燃焼や流体の論文・検証を代替しない。
- フレーム予算グラフの11/12/24/10msは説明用に決めた値。実機性能の証拠ではない。
- ブラウザのWGSLではGGXの直接光成分と、向きに応じた定数の環境光近似を加算する。粗さ0.52、正面反射率0.04、光源の係数3.4は試作の仮定値。実測照明・材質の再現ではなく、影、間接光の伝搬、参照積分とのエネルギー検証は未完了。Windowsの面ごとの色付けとは機能差がある。

## 実読済み追加記録と未完事項

今回の光学面・偏光とW1: [OPTICAL_GEOMETRY.md](../OPTICAL_GEOMETRY.md)は既掲PBRTの球/丸め/レンズ面の規約、
[POLARIZATION.md](../POLARIZATION.md)は[Mitsuba開発者の偏光解説](https://mitsuba.readthedocs.io/en/stable/src/key_topics/polarization.html)の
基底整合・Stokes/Jones・複素Fresnelの符号規約を本文確認（2026-11-03）。
[CONTINUOUS_WORLD.md](../CONTINUOUS_WORLD.md)はBaraffの衝撃/支持の分離と既掲CCD資料を確認。
どのレンダラー/solverのコードも移植せず、独自の区間・coherency展開・保持荷重のevent処理と解析試験を作成した。
外部の処方・材質・形状・図・本文は追加していない。独立の核が複数面撮像や持続支持の完成を意味するものではない。

単一光学界面: [OPTICS_INTERFACE.md](../OPTICS_INTERFACE.md)で、PBRT第4版§9.3/§9.5と
[MIT 6.007 Lecture33](https://ocw.mit.edu/courses/6-007-electromagnetic-energy-from-motors-to-lasers-spring-2011/082040cbe101109ac9f87e94a75ea5b5_MIT6_007S11_lec33.pdf)の本文確認を記録。
等透磁率の境界条件、Snell/Fresnel、法線fluxと放射輝度輸送の違いの確認に使用。
原文/図/コード/処方データは取り込まず、自作の界面核・試験・図を作成した。
加速接触の区間構成と探索は[ACCELERATED.md](../ACCELERATED.md)へ導出と独立解析例を保持する。

区間演算のビルド前提（2026-11-03本文確認）: [Clang Users Manual](https://clang.llvm.org/docs/UsersManual.html#controlling-floating-point-behavior)の丸め環境と収縮の制御、[Microsoft /fp](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170)のstrictモード、[WebAssembly numerics](https://webassembly.github.io/spec/core/exec/numerics.html#floating-point-operations)のnearest-even固定を確認。独自の四則/平方の各段階を外側へ広げる設計と、実行環境を拒否する条件の比較に使用した。仕様本文・実装コードは取り込まない。具体的なコンパイル/実行結果と適用範囲は[INTERVAL.md](../INTERVAL.md)。

一定速度の接触時刻: [Kahan, On the Cost of Floating-Point Computation Without Extra-Precise Arithmetic, 2004, §1](https://people.eecs.berkeley.edu/~wkahan/Qdrtcs.pdf)の小さい二次根での打消し回避と重根の不良条件、[PBRT4 §6.2](https://pbr-book.org/4ed/Shapes/Spheres)の球交差の二次式、[§6.8](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error)の交差判定の丸めを本文確認。式と制約は[CONTINUOUS.md](../CONTINUOUS.md)。独自実装の診断guardは厳密な区間包含の証明ではない。外部のコード・本文・図の転載や新ライブラリ導入なし。

共通C++のWeb出力: Emscripten公式[SDK導入手順](https://emscripten.org/docs/getting_started/downloads.html)、例外・C/JS接続・ライセンスの文書と、実際に導入した6.0.13の原文通知を確認。確認範囲・版・代替案は[WASM_DYNAMICS_PLAN.md](../WASM_DYNAMICS_PLAN.md)、配布条件は[依存台帳](DEPENDENCIES.md)。生成ランタイム/標準ライブラリは今回から配布物に含むため、以下の従来モデルの「外部ランタイムなし」は資料転載の有無を示す過去の範囲であり、この出力全体には当てはまらない。

追加の光学調査: [OPTICS_SCOPE.md](../OPTICS_SCOPE.md) にPBRT第3版§6.4のレンズ面・開口の経路と、第4版§9.3のSnell/Fresnel/全反射の確認範囲を記録（2026-11-03閲覧）。処方データ・図・コードの導入なし。反射を省略した撮像経路だけではフレア/ゴーストの受入を満たさない。

Native浮遊結合と操作ラボ: [BUOYANCY.md](../BUOYANCY.md)、[浮力ラボ](../learn/buoyancy.html) は既掲の静水圧・発散定理・剛体の一次資料を使い、式・独立解析例・初回不安定形状の検証を記録。予測中点の結合・UI・図は独自作成。ソルバーの2次収束を実船校正やCFDの検証と取り違えない。

M2の追加調査は各モデルに式・適用条件と併記する。[DYNAMICS.md](../DYNAMICS.md) にBaraffの剛体講義・Cattoの接触反復法、[FLUID_MODELS.md](../FLUID_MODELS.md) にOpenStaxの静水圧/浮力・Purdueの発散定理・NASAの係数抗力、[CONTROL_DESIGN.md](../CONTROL_DESIGN.md) にMathWorksのsample time/IK設計を記録。実装は独自で、資料の本文・図・コードや外部ランタイムの同梱はない。モデリング教材は既掲WebGPU仕様の頂点バッファー節を確認し、外積・法線・境界を独自実装した。光学の新要件は研究待ちであり、フレア等を計算済みとはしない。

高度な光学、実測材質、室内反射・残響、気象音響、HRTF、空力、専門車両、外部モデル・モーションの取込みについて、この教材の参考資料だけで研究済み・実装済みとはしない。採用する機能ごとに原著・仕様の版と適用条件を追加する。

波長分散の追加調査（2026-11-03閲覧）: [SCHOTT TIE-29 August 2023](https://media.schott.com/api/public/content/aaa572afd854434fb7b3faa4bc46103f?v=7f40e8ec)の相対屈折率・Sellmeier有効帯/単位、[RP Photonics Encyclopedia “Group Index”, Dr. Rüdiger Paschotta](https://www.rp-photonics.com/group_index.html)の真空波長による群指数、[同 “Sellmeier Formula”](https://www.rp-photonics.com/sellmeier_formula.html)の透明材質モデルを確認。確認と独自導出は [DISPERSION.md](../DISPERSION.md)。ページ本文・図・表・係数・コードを取り込まず、新規ランタイム/ライブラリも追加しない。

## 今回の区間継続・指定光路・支持反力（2026-11-03実読）

| 一次資料 | 確認した本文 | 今回への適用と限界 |
|---|---|---|
| [PBRT第4版 §6.8 Managing Rounding Error](https://pbr-book.org/4ed/Shapes/Managing_Rounding_Error) | 交点誤差が次rayの自己交差に与える影響と固定epsilonの問題 | [OPTICAL_BOUNDS.md](../OPTICAL_BOUNDS.md)と[OPTICAL_ROUTE.md](../OPTICAL_ROUTE.md)で全origin/direction boxを維持する動機を確認。PBRTのray offset処理を転載・移植せず、今回はself-hitを自動省略しない |
| [PBRT第4版 §6.2 Spheres](https://pbr-book.org/4ed/Shapes/Spheres) | 球面交差の二次式と根の扱い | 原入力族のA/Delta符号、根存在・順序・一律選別を独自の区間契約として構成。資料のコードや図、レンズ処方を取り込まない |
| [PBRT第4版 §9.3 Specular Reflection and Transmission](https://pbr-book.org/4ed/Reflection_Models/Specular_Reflection_and_Transmission) | 幾何光学と誘電体界面、Fresnelと偏光の前提 | ni/ntの全区間と点波長、s/p normal fluxの包絡を使用。指定光路の任意偏光包絡の積は本実装の包含論証で、PBRTと同じ区間APIを実装したという主張ではない |
| [Baraff, Rigid Body Simulation II, SIGGRAPH 1997 §6](https://www.cs.cmu.edu/~baraff/sigcourse/notesd2.pdf) | colliding contactの速度不連続とresting contactを支えるforceの区別 | W1衝撃と[SUPPORT.md](../SUPPORT.md)のread-only反力照会を分ける根拠。これだけで支持を保つ時間積分・摩擦・一般接触の受入完了とはしない |
| [Baraff, Fast Contact Force Computation for Nonpenetrating Rigid Bodies, 1994 §3](https://www.cs.cmu.edu/~baraff/papers/sig94.pdf) | 質量/幾何に依存するa=A f+b、反力・加速度と相補条件 | normal-onlyの独自PGS候補と区間残差監査を構成。論文のDantzig実装や摩擦アルゴリズムの転載ではなく、同論文の性能・対応範囲を継承したとも主張しない |

資料の閲覧・リンクと、素材の配布許諾は別に扱います。今回のPDF/書籍本文・図・コードは
リポジトリや製品へ同梱していません。光路/支持の本文・解析試験・SVG2枚は本プロジェクトで作成しました。
新規依存・校正済み材質値・処方表の導入はなく、本体のライセンスは未選定のままです。


## W2の時間積分・接触遷移（2026-11-03実読）

| 著者/公式の一次資料 | 本文を確認した範囲 | 今回の原著実装との関係・限界 |
|---|---|---|
| [Stewart–Trinkle, An Implicit Time-Stepping Scheme for Rigid Body Dynamics with Coulomb Friction](https://www.cse.lehigh.edu/~trink/Papers/STicra00.pdf) | §3.1の位置・速度・impulse、§3.3と§3.4の曲面幾何の更新 | 端点位置と速度だけで途中経路の安全を保証しないこと、固定法線一回のLCPを一般曲面へ延長しないことを比較。本文・code・friction solverの移植なし |
| [Acary, INRIA RR8602, Energy conservation and dissipation properties of time-integration methods for the nonsmooth elastodynamics with contact](https://arxiv.org/pdf/1410.2499) | §4.1のMoreau–Jean式・接触開始時の位置違反、§5の線形系の離散エネルギーと適用条件 | 速度相補だけでは位置違反があり得ることを確認。線形系の散逸条件を今回の非線形・接触切替・一般剛体全体の保存性証明へ流用しない |
| [McLachlanほか, Geometric Generalisations of SHAKE and RATTLE](https://arxiv.org/pdf/1207.3367) | §4.3–4.5の正則性・収束・対称性、§5.1.3の位置/速度拘束 | [CONSTRAINED.md](../CONSTRAINED.md)の固定active区間の設計を比較。片側衝撃・離脱driverの完成実装は導入せず、独自の非対称Newton/LU、stage符号と元離散式の区間監査を作成 |
| [Acary / Collins-Craft, On the Moreau–Jean scheme with the Frémond impact law, 2025](https://jtcam.episciences.org/15960/pdf) | 非線形Newton–Eulerの数値例が先行する線形系の証明範囲外であるという注意 | 近似としての動作と定理の保証範囲を区別する確認。Frémond摩擦則・Siconos・Bulletの実装や例の素材を取り込まず、今回も摩擦0のprofileを明示 |

上の本文確認から、[SUPPORTED_WORLD.md](../SUPPORTED_WORLD.md)の有限刻み支持・衝撃・離脱と、
[TRAJECTORY_GUARD.md](../TRAJECTORY_GUARD.md)の**定義済み候補放物線の幾何**を区別した。
後者は原入力からの区間四次式と被覆による別の原著核で、連続の真解を囲む積分器ではない。
粗細幅差も独立の誤差推定で、厳密な打切り誤差上限としない。
既存public read-only支持のstrict policyを維持し、private有限vn LCPの近似規約を別に記録する。
負行一括削除の反例、末尾衝撃の右連続snapshot、弱いvelocity_repairに小さい物理的新接触も含み得る点、
held_force_workがtorque仕事を含まない点も、実装モデルの限界として残す。

独立受入は床上等加速度・torque、質量の異なるstack、非直交接触、曲率球対、保持荷重下の衝撃/再接触と全tick保持。
候補軌道のFraction640例は原double bitsを厳密有理数へ復元し、曲面四次式を含む最小値と320負witnessを別実装で確認する。
Native24群とstandalone実WASM23群の差は、Nativeにだけ丸めmode変更拒否試験があるためである。
論文のPDF/本文/図/codeは配布物へ同梱せず、追加外部solver・依存・材質/形状データもない。
追加の原著概念SVGはsupported-world.svg（サイズ/hashは[素材台帳](ASSETS.md)）。ライセンスは未選定のまま。

## 静的複数面の最近傍（2026-11-03実読）

[PBRT第4版 §6.1.3](https://www.pbr-book.org/4ed/Shapes/Basic_Shape_Interface)で単一shapeの最初の交差とray parameter範囲の契約、[§7.1.1](https://www.pbr-book.org/4ed/Primitives_and_Intersection_Acceleration/Primitive_Interface_and_Geometric_Primitives)で手前が棄却されても奥の交差が残り得ることを確認。[§6.8冒頭](https://www.pbr-book.org/4ed/Shapes/Managing_Rounding_Error)で交点丸めと固定epsilonが自己交差や近傍の見落としを生む条件を確認した。

今回の独自selectionは、既存の全区間primitiveのhit/missを利用し、全競合が後方または閉prefix内missと証明できる場合だけ共通の面IDを返す。これは当該PBRTコードの転載・移植ではない。PBRTの開ray区間/点ray・誤差offsetの実装を、本エンジンの閉区間・独立ray族・self根保持の契約と混同しない。単一交点に関する誤差boundから、ray族全体の最近傍や生成面との相関を自動的に証明できるとはしない。本文・図版・コード・レンズ処方・測定データは配布しない。


## 有限瞳と幾何点像の調査（2026-11-03）

PBRT第3版[Realistic Cameras §6.4](https://pbr-book.org/3ed-2018/Camera_Models/Realistic_Cameras)の面列による屈折・有限開口と、同第4版[Radiometry §4.1](https://pbr-book.org/4ed/Radiometry,_Spectra,_and_Color/Radiometry)の光束/照度/放射輝度の区別を本文確認した。原著のoptical_spotでは有限ray集合の幾何位置と正の面積測度だけを集計し、throughputの包絡を光量と解釈しない。等r²層の等面積節点、有限OからPへのoutward差、厚レンズ近軸行列の比較は独立に作成。実レンズ処方、材質データ、図、コード、ライブラリは取り込まない。有限標本の収束と数値区間の幅、幾何点像と連続瞳の回折像は別の受入とする。

## 偏光経路とcoherency（2026-11-03実読）

- [Anche et al. 2023 §3](https://arxiv.org/html/2304.02079v1): global polarization ray-tracing matrix、各面の局所Jonesと世界基底変換、経路上の積。原著の区間POWERモデルへ適用し、当論文のコードは移植しない。
- [Gil 2014 §2](https://arxiv.org/pdf/1408.0312): 世界3成分のHermitian coherency、正半定値条件とtrace。本実装はray-tube POWER正規化で、電場強度/照度と単位を混同しない。
- [Mitsuba polarization documentation](https://mitsuba.readthedocs.io/en/stable/src/key_topics/polarization.html): s/p基底、時間/位相の符号、全反射の複素係数、flux正規化の比較。実装・図・ライブラリは導入しない。
- [BYU Optics §3.2–3.5, §6.7](https://optics.byu.edu/docs/opticsBook.pdf)、[UT Austin reflection](https://farside.ph.utexas.edu/teaching/em/lectures/node104.html)、[Means1972 pp2–4](https://ntrs.nasa.gov/api/citations/19720019517/downloads/19720019517.pdf): Fresnel/偏光/基底の一次資料。p符号は出射基底の選び方に依存するため数式だけを転記しない。
- [PBRT4 Radiometry](https://pbr-book.org/4ed/Radiometry,_Spectra,_and_Color/Radiometry): POWER、放射輝度、照度と測度を区別する。

出版社の取得待ちページや取得不能のDOIは本文確認の根拠に含めない。PDF/本文/図/code/材質測定データを配布物へ取り込まず、説明図・fixture・独立検査は独自作成。

有限POWERの節目（2026-11-03再読）: PBRT4 Radiometry §4.1.1のflux(W)とirradiance(W/m²)の区別、PBRT3 Realistic Cameras §6.4の屈折面列と有限開口を本文再確認した。今回の各packetに明示したWを理想吸収sensorで数えるモデルは、この区別に基づく独自の離散measure規約。PBRTの無偏光/カメラからの放射輝度weight実装は移植しない。多経路をcoherencyだけで干渉加算できるとはせず、同一の入射measureを2経路で別々に追った結果として表示する。外部コード/図/レンズ処方は取り込まない。

## 骨格と秒単位キー（2026-11-03実読）

[Khronos glTF 2.0 §3.5.3、§5.25、Appendix C.3–C.4](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)で階層の親子変換、局所TRS、時刻列、回転の最短経路と正規化を確認した。独自motionは親world×子localの行列を保持し、非一様scaleが作るshearをTRSへ分解し直さない。回転は最短NLERPに限定し、glTF rotation LINEARのSLERP・定速回転やglTF入出力互換を実装済みとはしない。本文・図・サンプルasset・コードを取り込まず、独自C++/JSと元データ、独立Python検査、原著SVGを作成した。新ライブラリの導入はない。

次段skin bindingの調査（2026-11-03）: 同Khronos glTF §3.7.3/§5.28でjoint配列とinverse bindの対応、重み付き変換、非負weight、skinned mesh node transformの規約を本文確認した。[SKINNING_PLAN.md](../SKINNING_PLAN.md)は独自のmesh-local=skeletonspace subsetの計画で、この調査だけを実装/互換の証拠にしない。外部のコード/図/assetは取り込まない。

位置skinningのcondition指標（2026-11-03）: [LAPACK DGECON Purpose](https://netlib.org/lapack/explore-html/d4/daf/group__gecon_ga4f9b830e19e12c7f082ddb497a57af18.html)のnormとinverse normの積によるconditionの定義を確認。LAPACKのLU推定器/コード/ライブラリは導入せず、3×3の自作scaled eliminationと明示inverseから点指標を作る。独立検査は別のFraction 4×4構成。資料の目的欄を数値保証や再配布許諾の代わりにしない。

位置skinningの共通SDK接続（2026-11-03）: 上記Khronosの座標/逆bind/重み付き変換とLAPACKのcondition定義について、既掲の本文確認範囲を継承する。SDKパケット、C++record getterとコピーsnapshot、原著Canvas操作ラボ、Native/main WASM再生は本プロジェクトで作成した。新しい外部実装・本文・図・モデル・モーション・データの導入はない。既に確認したEmscripten公式SDK/C-JS接続と既設6.0.13の原文通知を継続使用する。60実C++モデル結果と5明示host交換拒否、128oracleのbit比較と独立Fractionの点精度検査は別に記録し、参考仕様への適合・一般誤差包含・glTF取込み・binding原本codec/CLI往復・GPU描画の証拠と読み替えない。実装境界は[SKINNING.md](../SKINNING.md)と[SKINNING_SDK_PLAN.md](../SKINNING_SDK_PLAN.md)。

4要素整列のcompiler監査（2026-11-03実読）: [GCC Warning Options](https://gcc.gnu.org/onlinedocs/gcc/Warning-Options.html)のarray-bounds節、[GCC Instrumentation Options](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html)のaddress/undefinedとrecover節、[Microsoft AddressSanitizer](https://learn.microsoft.com/en-us/cpp/sanitizers/asan?view=msvc-170)の既存MSVC機能を確認した。GNU13.3が実際に出した警告は保存logを根拠とし、現行online文書と特定compilerの実挙動を混同しない。最大4要素の独自bounded insertionに替え、O2の-Werror=array-boundsとO1のASan/UBSan実行を別にする。Sanitizerで未検出であることは全入力の安全性証明ではない。外部コードや追加の配布runtimeを導入しない。MSVC/GCCの既設検証runtimeはlocal/CIだけで使用し、WebSDKには含めない。

所有bindingのJSON/原本往復（2026-11-03実読）: [RFC8259](https://www.rfc-editor.org/rfc/rfc8259.html)のobject名の一意性・number・Unicode/UTF-8・parserの制限を確認した。独自asset subsetは重複key、nonfinite/overflow、非zeroからzeroへのdecimal underflow、unpaired surrogateを拒否し、generatorで-0を保持する。全JSON実装の一般仕様と、この追加制限を混同しない。[RFC9923](https://www.rfc-editor.org/rfc/rfc9923.html)のFNV1a64定数と非暗号性を確認した。独立投稿のInformational RFCであり、暗号安全性や衝突なしの根拠にはしない。独自のprefix/geometry byte規約でfingerprintを作り、hash後も全形状比較を必須にする。RFCのcode/図/データは取り込まない。[Microsoft _open/_wopen](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/open-wopen?view=msvc-170)のcreate/exclusiveを確認し、Native CLIは全候補serialize後に新規出力だけを開く。既設の標準library/OS機能を使い、外部JSON/hashライブラリを導入しない。

2026-11-03 派生mesh初段: [WGSL §15.7 floating-point evaluation](https://www.w3.org/TR/WGSL/#floating-point-evaluation)と[MSVC /fp](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170)の本文を確認。CPU量子化geometryの区間監査とGPU算術の境界、strict buildの環境/縮約条件の根拠に用いる。source/図/ライブラリは移植しない。Native-only核は実装中で、公開受入済みの追加機能とはしない。

2026-11-03 派生mesh SDK接続: 上記WGSL/MSVCの実読範囲と既存Emscripten接続契約を継承し、原著ABI/コピーDTO/手動監査UIを追加した。新たな外部アルゴリズム実装・図・データを導入しない。NativeとWASMのbit一致だけに依存せず、実WASMの40結果にも既存Fraction参照・36負例を適用する。局所CPUの条件をGPU/描画全体の保証へ広げない。

2026-11-04 JST 任意の小mesh3D表示: 既掲の[WGSL floating-point evaluation](https://www.w3.org/TR/WGSL/#floating-point-evaluation)と[MSVC /fp](https://learn.microsoft.com/en-us/cpp/build/reference/fp-specify-floating-point-behavior?view=msvc-170)の実読範囲を継承する。今回は新しい資料を実読したという記録を追加しない。原著rendererのmodel/VP Float32演算・shader法線normalizeと、C++局所量子化geometryの誤差条件を分ける。validation/queue完了やmock GPUのbyte比較を、GPU算術・画素被覆の包含証明としない。外部コード・図・モデル・材質データは取り込まず、既存の原著SVGをCPU監査の概念図として再利用する。実装・受入の範囲は[DERIVED_MESH_RENDER.md](../DERIVED_MESH_RENDER.md)に記録する。

2026-11-04 JST 段階計測: [Node v24 Performance measurement APIs](https://nodejs.org/docs/latest-v24.x/api/perf_hooks.html#performancenow)のperformance.now/measure/timeOriginの本文を確認。nowはprocess開始を基準にした高分解能millisecond値、receiverをperformanceにする契約を継承する。閲覧online版は24.22.2で、実行環境の24.14.1/CI22系の実測と混同しない。timerifyの新aliasや外部profilerは使わず、元runtimeを変更しない原著wrapperと各試行のrawを作る。観測負荷をゼロと仮定せず、residualやbaselineとの差を純粋なkernel/JS費用と断定しない。本文/図/実装コードは取り込まない。

2026-11-04 JST ブラウザ計測: [W3C WebGPU CRD 2026-09-15 queue完了](https://www.w3.org/TR/2026/CRD-webgpu-20260915/#dom-gpuqueue-onsubmittedworkdone)、[error scope](https://www.w3.org/TR/2026/CRD-webgpu-20260915/#dom-gpudevice-poperrorscope)、[adapter info](https://www.w3.org/TR/2026/CRD-webgpu-20260915/#gpuadapterinfo)本文を実読。queue呼出時点までの処理完了とCPU/表示提示を区別し、元rendererのvalidation→queueの待機順を保つ。error scopeの解決順を仮定しない。driverのdescription文字列をhardware/software判定にparseせず、fallback属性だけでも実行機器を断定しない。実装中の専用原著wrapper/ラボの契約へ反映し、草案を完成規格とは扱わない。本文・例示code・図は取り込まない。

2026-11-04 まとめ読出し: 新C ABI packet/cacheは原著で、既存simulation_api.h/.cppとJS decoderの所有・status契約を基に設計した。外部solver/serializer/benchmark codeや図は取り込まない。比較の一次証拠はreports/2026-11-04-derived-readback.mdと原raw。呼出し回数の解析と有限実測を区別し、C++数値核・W3C GPU契約の保証範囲を拡大しない。新しい外部依存や権利条件の採用はない。

2026-11-04 JST ブラウザsingle/batch比較: 既掲のWebGPU queue/error scope/adapter情報とCPU/GPU算術の実読範囲を継承し、今回は新しい外部文献を実読したという記録を追加しない。原著のmode選択、schema2/trial2/summary1、call数とrecord数、取消世代と旧schema1互換の契約は、既存原著API/ラボと[ブラウザ比較契約](../DERIVED_MESH_BROWSER_READBACK.md)を根拠にする。別modeの同一性、CPUから観測する待時間、GPU状態を区別し、同一性照合を独立数学参照やGPU単独時間の証明にしない。外部本文/code/図/データ/packageを導入せず、実ブラウザと公開受入は統合後に別記録で確定する。


2026-11-04 JST ロボット背面カバー: 新しい外部資料を実読したという記録は追加せず、既掲の骨格/行列LBS、WGSLの算術境界、WebGPU error scope/queue完了とAnimation framesの実読範囲を継承する。原著Source、generator、`samples/back-cover.mjs` と既存rendererの実sourceを確認し、根拠と範囲を[ROBOT_BACK_COVER.md](../ROBOT_BACK_COVER.md)へ記録した。clip補間は最短NLERPであり一般の定速角速度とせず、33有限姿勢の品質確認を全パラメータ保証としない。120Hz固定状態・2tick更新予定・実query/遅延・CPU観測時間/GPU確認を分ける。0.1m/s以下のauthor idle bandは機構表示用の制御仕様であり、物理速度やFK/LBS精度へのtoleranceではない。新しいSource/context/SVGは原著で、外部文献の本文・図・実装・モデル・材質データを転載しない。熱・関節力学・接触/損傷の論文モデルを実装済みとせず、実ブラウザ/公開の受入は統合報告で別に確定する。


2026-11-04 JST 球と静的三角形: David Eberly, [Distance Between Point and Triangle in 3D](https://www.geometrictools.com/Documentation/DistancePoint3Triangle3.pdf) の§1–2を実読。三角形内の点との距離²の制約付き最小化と、最小点が内部または辺/頂点にある定式化を確認した。著者PDFは2020-09-11改訂、CC BY 4.0表示。本文・図・点値分岐codeを転載せず、determinantを絶対値化する点計算も包含判定へ移植しない。全7候補の否定不能集合を区間で保持/hullする原著方式と、既存の自作Interval/sqrtを使う。[SPHERE_TRIANGLE.md](../SPHERE_TRIANGLE.md)にNative-only・未検証の契約と境界を記録する。文献参照や資料のCC BY表示を、エンジン本体のライセンス選定・外部code導入・mesh/CCD/World統合の完成と扱わない。


2026-11-04 JST 球×三角形の共有SDK接続: 前掲の点–三角形距離の数学的定式化と既設Emscripten C/JS接続の確認範囲を継承し、新たな外部実装・本文・図・データは取り込まない。24/58/13のABI交換、候補ordinal、所有copy・検査・Native/WASM再生は原著。Native核とのbit一致と独立Fraction包含は別の根拠として記録する。新しい資料を実読したとの主張や、外部仕様全体への適合・一般の衝撃応答/CCD/mesh manifoldの完成とはしない。契約は../SPHERE_TRIANGLE_SDK.md、証拠はreports/2026-11-04-sphere-triangle-sdk.md。


2026-11-04 JST 球×三角形の手動ラボ: 既掲のNativeモデルと共通SDKの入力/出力契約を継承し、新たな外部資料を実読・転載したとはしない。13合成入力、区間の表示、候補診断、所有コピーとJSON保存、非同期読込み世代の検査は原著。全数値を実SDKから受け取り、JSで最近接距離・KKT分類を再実装しない。2D投影の描画値を物理の接触点や単位法線へ流用しない。


2026-11-04 JST 球×静的三角形集合（Native実装中・未検証）: 前掲Eberly §1–2の点–三角形最小化の実読範囲を継承し、新資料を実読したとの主張を追加しない。全行の包含が得られた場合の min_i L_i <= min_i d_i <= min_i U_i と、距離²下限が最小上限を超えた面だけを除く集計は原著。可能な最近接面を全保持し、異なる面の法線を平均しない。本文・図・code・材質/形状データを転載せず、[SPHERE_TRIANGLE_MESH.md](../SPHERE_TRIANGLE_MESH.md)と新原著SVGにモデル/未完を記録する。既存単一面核/SDKの受入と、この集合核の未確定の検証を区別する。本体ライセンス未選定を維持する。


2026-11-04 JST 球×静的三角形集合のローカル受入追記: Native/ASan各59群・48入力、独立Fraction2688 primitive+87 aggregate=2775成分と43改ざん拒否を確認した。真の複数winner13例・優劣10例・実64面1例を含み、labelや入力順から参照答えを選ばない。有限の参照比較と原著Interval構成の包含根拠、ASan/Nativeのbyte一致をそれぞれ区別する。新資料の実読や転載はなく、前掲の数学的定式化の範囲を継承する。統合recipeの旧checker呼出し失敗と訂正再実行を含む来歴は[統合報告](../../reports/2026-11-04-sphere-triangle-mesh.md)へ記録し、公開CI/Pagesは未確認とする。


2026-11-04 JST 球×三角形集合の共有SDK接続（実装中・未検証）: 前掲の単一面/集合の数学的定式化と既設Emscripten接続の確認範囲を継承し、新しい資料を実読したとの主張を追加しない。stage64、入力14/結果24/source14/row58/candidate13、全入力所有copyと全候補・ID・符号零・失敗保持の交換方式/図は原著。Native受入・Native/WASM一致・独立Fraction参照を分け、新WASMの検証結果はまだ確定していない。外部の実装・本文・図・データは転載せず、本体license未選定を維持する。[SDK契約](../SPHERE_TRIANGLE_MESH_SDK.md)。


2026-11-04 JST 球×三角形集合SDKのローカル受入追記: 実WASMの45モデルと3 host拒否を分け、packet27160/model20808 numeric bits・負の零4453件、独立2775成分/43改ざん拒否を確認した。破損snapshotを注入するdecoder試験は実モデルの数値照合とは別に記録する。pinned Emscripten6.0.13のlibcxx/src/algorithm.cpp冒頭と既存LIBCXX-LICENSE.txtを確認し、SPDX Apache-2.0 WITH LLVM-exceptionと既設標準libc++のsort用途を記録する。外部文献の図・本文・codeの転載ではなく、runtime原本の来歴監査である。[runtime監査](../../reports/sphere-triangle-mesh-sdk-runtime-audit.json)と[統合報告](../../reports/2026-11-04-sphere-triangle-mesh-sdk.md)を根拠とする。独立MSVC ASanはcompile未完了・runtime未実行のNOT_COMPLETEDで、成功と記録しない。公開CI/Pagesは未確認。


2026-11-04 JST 球×三角形集合の手動ラボ（実装中・操作未検証）: 既掲のNative集合モデルと74-export共有SDKの契約を継承する。新たな外部資料を実読・転載したとはしない。17合成比較例、全source/全row/面別候補とpossible IDsの表示、strict符号零保存、読込み世代の扱いは原著UIで、JSに距離/KKTの代替計算を追加しない。閲覧面のgeometryを集合nearestへ昇格せず、2D投影や区間inkを物理接触点/精度証明としない。操作・保存・公開受入はpendingで、先行SDKの数値成功をUIの成功へ流用しない。[ラボガイド](../SPHERE_TRIANGLE_MESH_LAB.md)。

2026-11-04 JST 集合手動ラボのローカル受入追記: 原著UI/図/17合成入力、専用18/全Node544・34CTest、実ブラウザ17例と実Blob2保存、42644数値bits/独立追加4578成分を確認。C++/SDK57原本/7通知/2artifact・全assets/sample原本不変を照合した。外部依存/資料転載/素材/有料serviceを追加しない。公開受入は別途確認待ち。根拠は reports/2026-11-04-sphere-triangle-mesh-lab.md と対応JSON。

2026-11-04 JST 集合手動ラボの公開受入追記: コード203c11aのLinux CI/Pages全工程成功、Node544/34CTest、新規warning0（既存36診断保持）、42公開ファイルbyte一致。実公開17例/実Blob2保存/42644数値bitsと独立追加4578成分を確認。先行の実装中記録に対する受入更新であり、新たな外部資料・依存・素材・ライセンス選定はない。詳細は reports/sphere-triangle-mesh-lab-public-verification.json。World/一般CCD/game mesh応答の完成ではない。


2026-11-04 JST 球×静的三角形集合の定義線分軌道guard（Native実装中・数値受入pending）: 三角不等式からd(c,S)−|x−c|<=d(x,S)<=d(c,S)+|x−c|を原著で導出し、既存原著Interval/sqrtと集合照会契約を再利用する。Rはcell全体、Eは厳密な中点pathと任意binary64 anchorのずれを囲み、strictな証明式・全closed leaf被覆・左prefix・事前予約/実work/例外certaintyを分ける。新しい外部文献の実読、既存文献からの実装・本文・図の転載は主張しない。独立有理数による全区間解析と負例は実行後に別記録へ確定する。点witnessをTOIや一般WorldのCCD・接触応答へ昇格しない。[モデルガイド](../SPHERE_TRIANGLE_MESH_TRAJECTORY.md)。本体license未選定。

2026-11-04 JST 定義線分軌道guardのローカル受入追記: Native69群/62入力、全35CTestと最終test-only拡張後専用1CTest、Node544skip0、独立48全path/4witness/297leaf/606audit・解析14/改ざん71を確認。保護98原本/SDK57source74exports/WASM638777B/7通知・既存assets/sampleはbyte不変。原著図と教材25記事を維持し、新しい外部資料/実装/依存/素材/有料serviceは追加しない。初回の回帰anchor想定誤りはrawと共に保持し訂正再実行、例外fault injectionやWorld/TOI/応答完成とはしない。公開CI/sanitizerは確認待ち。詳細は reports/2026-11-04-sphere-triangle-mesh-trajectory.md。

2026-11-04: 定義線分guardへ独立C ABI stage/recordと6exportsを追加し、共通WASMを再build。実80exports/59source-header、WASM674978B/glue56289B。既設pinned runtime linkedLibraryMembersは増減0、7通知hash不変、新package/外部数学・物理実装/素材/ライセンス選定なし。Native25交換群・36CTest、62入力の59model/3hostと全wire/19改ざん拒否、実WASM70278数値bits/2398負零照合をローカル確認。原著交換SVGとガイドSPHERE_TRIANGLE_MESH_TRAJECTORY_ABI.mdを追加。元の62 pure入力への独立有理数参照と、交換59modelの全DTO bit一致をscope分離し、host3をモデル実行と呼ばない。公開CI/Pagesは次に確認、所有JS wrapper/UI/World/TOI/応答は未接続。


2026-11-04 JST 定義線分guardの所有JS decoderローカル受入: 既存原著Native/Interval/sqrt/三角不等式と有界C ABIを継承し、新たな外部一次資料を実読したとは記録しない。全packetの型・count・optional・Work/被覆/診断linkをJS metadataとして監査するもので、独立な幾何/数値solverの追加ではない。実WASM由来59 owned DTOをpure Native全model bitsと照合し、host3のpure結果を明示補足したmixed62へFraction参照を実実行した。297leaf/606audit、self14/改ざん71の出自は混合corpusであり、全62件をWASMモデル実行と呼ばない。所有API・originalInput/snapshot別所有の原著図に文献本文/図/codeや外部画像/フォントを転載しない。[現行ガイド](../SPHERE_TRIANGLE_MESH_TRAJECTORY_JS.md)。公開受入・手動UI・World/TOI/応答と故意のNative例外注入は別。本体license未選定。

2026-11-04 手動trajectoryラボ: 既受入の原著Native線分guard/有界C ABI/所有JS APIと固定入力を再利用。新外部一次資料実読・図/本文/code転載なし。25presetは全input bitsが固定62corpusに一致し、実モデル24とhost65拒否1を分ける。UIの全owned DTO/保存照合は実ブラウザー直接SDK再照会との比較であり、独立数学検証は既存owned59＋明示pure補足host3のmixed62参照としてscopeを維持。原著説明投影を証明/TOI/World応答と扱わない。

2026-11-04 Native entry-window: 新たな外部文献の実読・本文/図/codeの転載なし。既存原著Interval・全path三角形距離参照を継承し、closed prefixのstrict正とexact path負点、外向きU−Lから侵入onsetの範囲を囲む条件を独自設計。独立参照は既存の可行face投影/closed edge clippingとFraction多項式をimportし、Production BFSやKKTマスク・dense samplingを証明として使わない。原著図の帯を実結果や許容幅の測定と呼ばない。数学/負例/Native/公開受入は実行後に別scopeで記録する。

2026-11-04 entry C ABIの原著packet mapと独立encoder/厳密bit照合を追加中。Nativeの距離・連続性証拠は既存実装/独立Fraction参照を継承し、新外部文献本文や図/コードを転載しない。metadata encoderを新しい数学solverや実機械軌道の証明と呼ばない。APIメモリ検査/純粋核メモリ検査/配布監査は別記録。

2026-11-04 entry所有decoderと全DTO独立照合を追加中。旧原著trajectory wrapperの所有方式を参照し、Nativeの全field/−0と初期証拠/partition/tailを維持する。metadata整合検査と数学的包含の独立Fractionを区別する。新外部コード/文献図本文の転載なし。

entry所有JS検証: 新しい外部資料実読/転載なし。62実decoderモデルを元Native全field bitsへenumだけ投影して比較し、host3を明示補足したmixed65の独立Fraction/90負例を成功。ブラウザ固定例は実Node/Native比対と区別して記録する。

2026-11-04 手動entry UI: 外部文献の実読・図/本文/code転載なし。原著旧trajectoryラボの所有/表示方式を参考にするが自動初期化moduleを再利用importせず、initial/window/全partitionを別契約として実装する。原著説明投影は数学包含やTOI/World応答の証明ではない。

手動entry UIの受入: 原著25presetの全input bitsを固定65へ照合。24自然モデルとhost1、13追加packetの所有/表示/直接SDK bits一致と2実Blob bytesを別に検証。追加viewは同一queryを共有でき、packet数を実query数と呼ばない。独立数学mixed65/90負例と説明投影を分ける。

2026-11-04 保持荷重球×mesh: 新外部文献の実読/引用・図/本文/code転載なし。二次coordinateの端点/内部停留点と、独立なface可行解+3clamped辺のFraction距離から原著証拠を検証する。一般quartic solverや全接触応答の完成とはしない。

2026-11-04 自由伝播guard: 新外部文献の実読/引用/図・本文・code転載なし。既存原著W1の誤差式をbridgeで再使用し、Fractionの整数RN/ties-evenと二次全域の独立参照で監査する。有限duration観測を全duration証明へ昇格せず、FMA/再結合の別graphを認証対象にしない。
