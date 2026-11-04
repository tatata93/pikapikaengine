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

2026-11-04 JST 集合手動ラボの公開受入追記: コード203c11aのLinux CI/Pages全工程成功、Node544/34CTest、新規warning0（既存36診断保持）、42公開ファイルbyte一致。実公開17例/実Blob2保存/42644数値bitsと独立追加4578成分を確認。先行の実装中記録に対する受入更新であり、新たな外部資料・依存・素材・ライセンス選定はない。詳細は reports/sphere-triangle-mesh-lab-public-verification.json。World/一般CCD/game mesh応答の完成ではない。


2026-11-04 JST 静的三角形集合の定義線分軌道guard（Native実装中・受入pending）: [モデルガイド](SPHERE_TRIANGLE_MESH_TRAJECTORY.md)は、原著の三角不等式から距離のLipschitz上下界を導き、既存Interval/sqrt/全mesh行成功の契約を再利用する。任意binary64 anchorからのcell上界Rと厳密な中点pathへの誤差上界E、strictな全区間非接触/点貫通witness/未認証を区別する。closed dyadic leaf全被覆・左safePrefix、sqrt block事前予約と返却実work/例外時work.exact=falseの区別も原著。新たな外部一次資料を実読したとは記録せず、外部実装・図・本文を転載しない。有限corpusの独立Fraction全区間参照と改ざん拒否は実行待ちで、Native受入・共有SDK/UI・World/CCD/応答の完成と混ぜない。新依存・素材・有料service・本体license選定はない。

2026-11-04 JST 定義線分軌道guardのローカル受入追記: Native69群/62入力、全35CTestと最終test-only拡張後専用1CTest、Node544skip0、独立48全path/4witness/297leaf/606audit・解析14/改ざん71を確認。保護98原本/SDK57source74exports/WASM638777B/7通知・既存assets/sampleはbyte不変。原著図と教材25記事を維持し、新しい外部資料/実装/依存/素材/有料serviceは追加しない。初回の回帰anchor想定誤りはrawと共に保持し訂正再実行、例外fault injectionやWorld/TOI/応答完成とはしない。公開CI/sanitizerは確認待ち。詳細は reports/2026-11-04-sphere-triangle-mesh-trajectory.md。

2026-11-04: 定義線分guardへ独立C ABI stage/recordと6exportsを追加し、共通WASMを再build。実80exports/59source-header、WASM674978B/glue56289B。既設pinned runtime linkedLibraryMembersは増減0、7通知hash不変、新package/外部数学・物理実装/素材/ライセンス選定なし。Native25交換群・36CTest、62入力の59model/3hostと全wire/19改ざん拒否、実WASM70278数値bits/2398負零照合をローカル確認。原著交換SVGとガイドSPHERE_TRIANGLE_MESH_TRAJECTORY_ABI.mdを追加。元の62 pure入力への独立有理数参照と、交換59modelの全DTO bit一致をscope分離し、host3をモデル実行と呼ばない。公開CI/Pagesは次に確認、所有JS wrapper/UI/World/TOI/応答は未接続。

公開受入追記: 84afb8cの全CI/Pages・新test/probe-Werror・API/test sanitizer25群/pure guard別69群・50配信byteを確認。初回GNU4新規診断/gate停止、数値不変の訂正と全根拠は reports/2026-11-04-sphere-triangle-mesh-trajectory-abi.md と公開検証JSONに保持。数学scopeとraw wire・所有JS未接続を分離。
