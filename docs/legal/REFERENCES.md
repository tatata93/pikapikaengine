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

## 未調査・今後の確認

M2の追加調査は各モデルに式・適用条件と併記する。[DYNAMICS.md](../DYNAMICS.md) にBaraffの剛体講義・Cattoの接触反復法、[FLUID_MODELS.md](../FLUID_MODELS.md) にOpenStaxの静水圧/浮力・Purdueの発散定理・NASAの係数抗力、[CONTROL_DESIGN.md](../CONTROL_DESIGN.md) にMathWorksのsample time/IK設計を記録。実装は独自で、資料の本文・図・コードや外部ランタイムの同梱はない。モデリング教材は既掲WebGPU仕様の頂点バッファー節を確認し、外積・法線・境界を独自実装した。光学の新要件は研究待ちであり、フレア等を計算済みとはしない。

高度な光学、実測材質、室内反射・残響、気象音響、HRTF、空力、専門車両、外部モデル・モーションの取込みについて、この教材の参考資料だけで研究済み・実装済みとはしない。採用する機能ごとに原著・仕様の版と適用条件を追加する。
