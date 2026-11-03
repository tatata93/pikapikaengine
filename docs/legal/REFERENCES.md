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
