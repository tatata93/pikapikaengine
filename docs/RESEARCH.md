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


2026-11-04 JST 定義線分guardの所有JavaScript APIをローカル受入: [所有APIガイド](SPHERE_TRIANGLE_MESH_TRAJECTORY_JS.md)に入力一度copy・全getter所有copy・完全DTOの型/enum/optional/予約零・被覆/link/Work整合監査を記録した。このmetadata監査は幾何やInterval包含をJSで解き直す数学solverではない。専用22/全Node566skip0、実WASM ownedモデル59の50663数値bits/2144負零とoriginalInput3877bits/100負零をpure結果へ照合し、明示pure Native補足host3と合わせたmixed62を独立Fraction参照（297leaf/606audit・self14/改ざん71）へ実投入した。前段raw wire比較・host3・人工例外packetの試験scopeを混ぜない。C++/既存80-export WASMと依存/通知を変更せず、新しい外部資料実読・実装/図/本文の転載・外部素材・有料service・本体license選定もない。新owned.svgは原著概念図で、SDKの公開CI/Pagesと次の手動trajectoryラボは別受入。

公開受入追記: owned JSコード5ff5723のCI/Pages全工程・36CTest/Node566、mixed数学検証、API/test sanitizer25群＋pure guard全核69群、56配信blob一致、実公開324bits24負零と既存ゲーム操作を確認。新依存/Native/WASM/通知変更なし。reports/sphere-triangle-mesh-trajectory-js-public-verification.jsonにscopeと有限証拠を保持し、手動trajectory UIは次段。

2026-11-04: 定義線分guardの手動ラボをローカル受入。既受入Native62から全input bits一致の25例、実owned APIで24model＋65面host拒否1を明示。専用20/全Node586・36CTest・構文/Web d70b5d9b4436650f（49module/24entry）、実UI100742bits3896負零と2Blob保存が成功。JSは表示/入力/所有保存のみで幾何solverを追加せず、旧owned59＋明示host補足3のmixed数学scopeを継承。Native/engine/WASM/game等249保護原本不変、旧web-build試験のentry期待1箇所23→24だけ変更し初回失敗rawを保持。原著図/本文のみ、新外部資料実読/依存/素材/有料serviceなし。公開受入は次に確認。

手動線分ラボ公開追記: 656f59dの全CI/Pages・36CTest/586Node/独立参照/sanitizer、64配信byte一致と実公開全25/7追加/2Blobを確認。原13試験fileのACLによるGit読取り問題はbyte不変archive77e03caで解決。次段Native entry windowは安全prefix/strict負witness/幅包含と連続性を使う設計のみで、新外部solver/文献実読/依存を追加せずSPHERE_TRIANGLE_MESH_ENTRY_PLAN.mdへ条件を記録した。

2026-11-04 Native-only sphere×static mesh entry window: 原著Interval/mesh queryと距離の連続性から、初期strict正・closed安全prefix・E補正strict負witness・外向き窓幅を全て揃えるproof objectを追加中。幅優先の全partition128/初期含む256照会を事前固定し、未知の狭さやwitness nearestを最初の接触/単一面へ転用しない。旧276保護原本/主SDK80exports59source/WASM674978B・7通知/gameを維持。初回MSVC厳密FP76群/65入力成功、独立参照/負例・全回帰/公開は別に確認。新外部資料実読・solver/package/有料serviceなし。新CPP/testにGNU個別-Werror・全核ASan/UBSanとRelease/sanitizer packet比較のCI工程を追加し、既存工程を保ってtimeout上限を15分へ拡張した。

ローカル受入追記: 最終76群/65入力と独立Fraction558葉1452audit3840成分・17解析/90改ざん拒否が成功。37CTest/586Node skip0・旧SDK数値/数学/所有回帰、276原本/80exports59source/674978B/7通知不変を機械監査した。独立test初回構文失敗と訂正、初回Native/数学PASSを別保存。公開GNU/Pages/配信は未確定。

公開受入追記: Native entryコード058a919のEngine41774681284/Pages41774680814全job/step成功。37CTest/586Node・65独立/90負例、GNU新cpp/test各-Werror・全核ASan/UBSan76群/Release bytecmp、旧回帰/36warning不変、73配信2078382Bを確認。新図の実目視と同一80sourceを根拠にした旧操作の継承を分け、未再操作を再実行としない。次は未実装のSPHERE_TRIANGLE_MESH_ENTRY_SDK_PLAN.mdに従う独立C ABI/全診断の有界交換。新依存/素材/有料service/本体license選定なし。

2026-11-04 entry-windowの独立stage/C ABIを実装・検証中。既受入Native核と全診断を保持し、24入力・最大64F64内の全packet・host拒否原子性を設計した。交換expected encoderとFraction数学参照を別に受け入れる。新外部資料実読/solver/依存/素材/有料serviceなし。本体license未選定。公開GNU/Pagesと再生成SDKのruntime/通知監査は実行後に確定する。

entry raw交換ローカル追記: 専用24群/38CTest/586Node、62model3host/147638数値3599負零と実WASM146130bits3525負零・各27改ざん拒否、元pure65 Fraction/90負例と旧SDK回帰成功。SDK86/61source/719410B/glue58933B・runtime91増減0・7通知不変を実生成で監査。303原本保護、初回test fixture誤期待だけ訂正し原失敗を保持。実ローカルゲーム/旧ラボ結果は新SDKで観測し、以前のSDK byte不変による継承とはしない。公開受入は未確定。

entry raw公開追記: 4b03f0cのEngine41777811708/Pages41777810766全工程成功。新API/test GNU ASan24と別全核76/fixture bytecmp・新test/probe-Werror、全38CTest/586Node、全packet/数学/旧SDK回帰・既存36warning不変を確認。81配信2276534B blob一致、実公開旧guard324bits24負零とゲーム1撃破/21正常照会を確認し、以前の操作の継承としない。finite原log初回抽出2行漏れの集計停止は403原行を保持し同原log405行で訂正、source/モデルを変えて成功にしていない。新依存/素材/有料service/本体license選定なし。次の所有JS decoderは計画のみ。

2026-11-04 entry-windowの所有JavaScript decoderを実装・検証中。既存86-export raw C ABIの全fieldと元入力をcopyし、metadataと所有を検査する。JSで幾何やsqrtを代替せず、実WASMモデルDTOのbit一致と出自付きmixed65 Fraction/90負例を別受入にする。Native/C ABI/SDK artifacts/7通知/gameは保持し、新外部資料実読/solver/依存/有料service/本体license選定なし。

entry所有JSローカル受入: 専用24群/610Node skip0/38CTest、実62model3host・全DTO/負零と出自付きmixed65 Fraction/90負例が成功。新法線/幾何solverをJSへ追加せず、交換metadata/所有と独立数学を分けた。312保護原本/SDK86・61source・719410B・runtime91/7通知不変、原著図を実ブラウザ目視。初回の合法負subnormal過剰拒否と無変異test、browser比較のenum投影漏れを記録し、核や数学原本は変えない。公開受入は次段。

entry所有JS公開受入: 578895dのEngine41781369977/Pages41781369241全工程成功。38CTest/610Node・62実owned全bits/負零と明示補足mixed65/90負例、旧回帰・既存36warning multiset不変、API/test ASan24と全核別76/fixture bytecmp成功。88配信2387746B blob一致、新APIとゲームを公開画面で実操作し完全JSON照合。312保護原本/SDK86・61source・719410B・runtime91/7通知不変。新外部資料実読/依存/転載素材/有料service/本体license選定なし。次の手動entry UIは計画・依存調査のみ。

2026-11-04 手動entryラボを実装中。既受入86-export owned APIと凍結65から25代表入力を選び、strict原入力/全診断保存とread-only投影を原著コードで接続する。JSで幾何solverや証拠を再計算しない。既存SDK/Native/game原本を保持し、新外部資料実読/依存/有料serviceなし。未検証を受入へ含めない。

手動entry UIローカル受入: 専用21群/631Node/38CTest、25代表入力の24実モデル＋host1、全画面JSON/追加13view入力packet/2実Blob=180165数値bits5061負零が直接SDKと一致。fresh62model3hostの全DTO bitsと明示補足mixed65 Fraction/90負例も成功。314保護原本/SDK/通知を維持し、旧SDK回帰は前公開受入とsource/artifact同一を確認して継承。driver上限/hiddenerror観測の原失敗と訂正を保持。公開受入は次段。

手動entry UI公開受入:263d531のEngine41785159270/Pages41785158716全job/step成功。38CTest/631Node・全owned/数学/旧回帰・既存36warning不変、93配信2506249B blob一致。実公開25例/追加13packet/2実Blob=180165bits5061負零・ゲーム1撃破22照会を別実行。rootdriverの保存先混線は5原byteを別保持してfeature/localhashへ復元し、公開証拠を再取得した。数値/受入条件は不変。新依存/外部資料転載/有料service/本体license選定なし。次の保持荷重・秒時間Native照会は元コード/反例を読取調査して設計文書のみ追加、実装やWorld応答の成功とはしない。

2026-11-04 保持荷重の球×静的三角形メッシュ照会をNative-onlyで追加中。元binary64のF/m+gを区間のまま二次経路へ通し、global秒時間・R/E補正・閉prefix/負witness・全partitionを監査する。外部solver、追加ライブラリ/推移依存、転載コード/図/材質データは使わない。新しい外部文献を実読したという主張はせず、既存原著核とFractionによる独立極値/最短距離の導出を検証する。Worldの通常double伝播や反力・摩擦・流体・塑性損傷の完成と区別する。

保持荷重Nativeのローカル受入: 79入力を厳密Fractionの二次全域極値・独立距離・R/E二乗/全prefix/partitionで監査し、13entry/8separatedを非vacuousに確認。2028audit/748leaf、16self/63負例（-O拒否含む）/label-order独立、専用92/39CTest/631Node skip0成功。FP/品質/予算不足を成功へ変えず、一般四次最小化/World伝播/衝撃応答/実fault注入は別受入とする。公開GNU strictとメモリ検査は未確認。

保持荷重7844b46の公開受入: Engine41790729060/Pages41790728378全job/step成功、GNU39CTest/631Node skip0/79Fraction/16self63負例、旧SDK・専門核回帰、3新TUのWerrorと新核/interval/mesh/dynamics/新tests全ASan-UBSan、Release-sanitized fixture同byteも成功。既存36warning診断multiset不変。33公開file1627338BがGitblob一致し、原著図も実公開表示を確認。次は新外部依存を増やさずW1の既存operation-graph上界をprivate bridgeで再使用するNative-only guardを計画する。共有cpp変更時は旧bit回帰とSDK provenance再生成を別受入に含め、今回の数学path成功をWorld応答へ昇格しない。
