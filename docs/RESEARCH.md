# 調査と検証の入口

2026-11-03。資料を読んだことと、理論・製品性能・配布権を検証したことは別に記録する。

本文と適用範囲の台帳は [docs/legal/REFERENCES.md](legal/REFERENCES.md)、依存版と配布境界は [DEPENDENCIES.md](legal/DEPENDENCIES.md)、素材は [ASSETS.md](legal/ASSETS.md)、配信条件は [HOSTING.md](legal/HOSTING.md)。原本の図・コード・モデルを転載していない。

| ID | 一次資料 | 採用範囲 / 状態 / 実装 |
|---|---|---|
| GPU-01 | W3C [WebGPU](https://www.w3.org/TR/webgpu/)、[WGSL](https://www.w3.org/TR/WGSL/) | GPUDevice/canvas/shader/セキュアコンテキスト。本文参照・直接API接続。`engine/renderer.mjs`。全ブラウザ版の互換性調査は未完 |
| AUDIO-01 | W3C [Web Audio 1.1](https://www.w3.org/TR/webaudio/) | AudioContext開始・標準発音/出力基盤。`engine/audio.mjs`。自前コードがd/cと1/rを計算。反射/ドップラー/聴感検証は未完 |
| TIME-01 | WHATWG [webapp APIs](https://html.spec.whatwg.org/multipage/webappapis.html) | 描画機会/非表示状態/rAFと提示回数の区別。`engine/time.mjs`。実ディスプレイの提示測定は未完 |
| BRDF-01 | Walterほか, 2007, [Microfacet Models for Refraction through Rough Surfaces](https://www.cs.cornell.edu/~srm/publications/EGSR07-btdf.pdf) | GGX分布の理解。適用の詳細は台帳。`renderer.mjs`、反射の参照積分・エネルギー試験は未完 |
| DIST-01 | 球面エネルギー保存の独立導出 | 一様自由音場、点音源、音速343m/s仮定、d/c、振幅基準距離/r。倍距離の既知比と数値比較。実測建材値なし |
| CONTACT-TRI-01 | David Eberly, [Distance Between Point and Triangle in 3D](https://www.geometrictools.com/Documentation/DistancePoint3Triangle3.pdf), 2020-09-11改訂、§1–2 | 三角形上の距離²最小化の定式化を実読。文献本文/図/code転用なし。原著の全否定不能KKT候補保持・既存Interval包含と、独立Fraction最小化でNative初段をローカル検証。SDK/World/CCD/mesh manifoldは未接続。詳細はSPHERE_TRIANGLE.mdと法務台帳 |
| DEPLOY-01 | GitHub [Pages API](https://docs.github.com/en/rest/pages/pages)、[Pages利用条件](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)、[Actions課金](https://docs.github.com/en/billing/concepts/product-billing/github-actions) | 公開repoのPagesと標準runner。本文確認、設定実行。課金設定変更なし |

数値単位と仮定はコード・教材・ADRに明記する。高度分野や専門モデルを、これだけで研究済みとはしない。アクセスできなかったLLVM資料は確認済み台帳に入れていない。


2026-11-04 JST 三角形集合の手動ラボ（実装中・操作/公開未検証）: [ラボガイド](SPHERE_TRIANGLE_MESH_LAB.md)と[原著概念図](diagrams/sphere-triangle-mesh-lab.svg)に、原本sourceと実query済みrow、集合nearestと面別診断を分ける読み方を記録する。先行Native/共有SDKの数値受入と、UI編集・世代管理・全候補表示・signed zero JSON/実ダウンロードの受入は別で、後者はpending。新しい一次資料の実読や外部実装/本文/図の転載を主張せず、既存CONTACT-TRI-01の数学的定式化と原著SDKの確認範囲を継承する。依存・素材・配布境界は既存legal台帳を用い、本体license未選定・World/CCD/game未接続を維持する。
