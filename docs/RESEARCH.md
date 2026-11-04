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

2026-11-04 丸め自由伝播のNative sphere×static mesh guardを追加中。既存W1 flightのoperation-graph ULPrecurrenceを同TU private bridgeで再使用し、実dynamics.cppもstrict/no-fast/contractionoffでビルドする。新しい数学solverを転載/導入せず、上向きr+Bの全域separatedとHの完全candidateを別監査。旧W1の全20入力/report/Worldbeforeafterと実SDKの20例（14success/5model拒否/1host拒否）を改修前に保存し、後で全bitsを検査する。SDKmaxContacts8192はNative既定16384と別profileとして明記する。新外部依存・有料serviceなし。

自由伝播guardローカル受入: Native114群/固定100と別固定4、Fraction12self/50負例、40CTest631Node skip0成功。元100に試験都合の変更をせず、中心binade3とcoarseTol.1での膨張entry反例を補足として分離。実dynamics.cppもstrict/no-contractionへ統一し、旧20Native全report/state byteと既存SDK保存20例4520数値/24負零が前後一致。再build WASM719396Bへ変化、86exports/62source-header/runtime91/7通知を正式provenanceで確認。新外部文献実読/依存追加を主張せず、公開GNU/メモリ検査は別判定とする。

自由伝播guard公開受入: Engine run41796183673/job126460730559、Pages41796182644の全job/step成功。GNU旧World前後20例byte比較・SDK保存20例bit比較・独立Fraction100＋4・12self50負例・新核全依存ASan/UBSanと両fixture byte一致を確認。公開43原本/SDK/gameファイル1779473Bをfeature blobへ一致確認。実公開ゲーム51照会/2撃破/boost/停止と原著図の上下を保存。40警告のうち追加4は旧World同一診断の別target再コンパイルであり、無警告とは報告しない。次段は未実装の両mode SDK接続計画に全field所有・host/model境界・原子的拒否とメモリ実測を定義した。外部依存/料金/転載素材の追加なし。

保持荷重/自由伝播guardのraw SDK接続を実装中。既存の原著Native核・全診断を6つのmode付きC ABIで運び、純79/100/別4の完全入力からhost/model分類・全packet bit比較・実WASM由来の独立Fraction監査を分ける。新数学solverや外部文献の実読を主張せず、原本を保持して転送する実装の検証を追加する。

raw flight SDKローカル受入: 新92exports/67source-header/32TUを正式再buildし、173実モデルと10host拒否の出自を分離。全wire/decoded数学診断・原入力fingerprint・16改ざんと-O拒否を確認した。HEAP64MiB容量と12915view再取得の観測を、allocator使用量・stack高水位・実growthの測定と取り違えない。初回synthetic参照のhelper名誤りと、prebuilt baseline実行中の未使用APIheader編集を原記録に残す。公開GNU/メモリ検査は別受入。

raw flight SDK公開受入: Engine run41802495271/job126481408910、Pages run41802494450の全job/step成功。183交換の173実モデルだけを独立Fractionへ送り、API/probe計装・Release/sanitized packet byte比較と既存純核別計装を区別して確認。公開45ファイル1946157Bが正確なfeature blobと一致。実公開ゲーム2撃破/21完了照会/boost/停止、原著SVG全表示を保存した。48警告は既存40件と旧APIを追加2targetで再コンパイルした同一診断8件で、新しいunused helperは公開前に削除して再検証した。raw交換の受入をJS所有/World応答やheap使用量/stack高水位の測定へ拡張しない。次段は未実装の所有JS計画。

2026-11-04 保持荷重/自由伝播guardの所有JS APIを実装・検証中。原入力の一度captureと全診断の所有copy、metadataの検査を追加し、実WASM由来DTOと固定Nativeのbit一致・独立Fraction監査を別々に記録する。query summaryは後続getterが共有出力を上書きするため所有API後のraw readback対象外であり、Native補填・export置換・隠れた再queryで埋めない。新しい数学solver/外部資料実読/転載/依存/有料serviceなし。本体license未選定、World応答は後続。

所有flight JSローカル受入追記: 30専用/661Node skip0/41CTestと173実ownedモデルの全DTO/原本/getter bit照合・独立Fraction/15負例/-O拒否が成功。10hostを実モデルへ補填せず、summary24のpost-return取得不能を明示した。345原本/SDK/WASM/runtime91/7通知を保持、原著図の表示と固定API2例・既存ゲームを実ブラウザ確認。candidate q監査漏れと証拠パス型誤りは原失敗を保持して訂正全再実行。公開CI/Pagesは次に確認する。

所有flight JS公開受入: feature8035f93のEngine41808775958/Pages41808775975全job/step成功。Linux661Node/41CTest/173実owned全bitsとFraction15負例・-O拒否、200ABI/183 Release-sanitized packet byte比較と既存純核別計装を確認。旧48warning multiset不変、新診断0。52配信2077380B blob一致と実公開API3891bits66負零、既存ゲーム2撃破/22正常照会を保存。初回自動承認拒否は全indexの345原本/25HTML本文不変監査を提示して解決し、承認を迂回しない。次段の未公開手動ラボと本feature受入を分け、新外部資料実読/依存/素材/有料service/本体license選定なし。

2026-11-04 保持荷重/自由伝播guardの手動ラボを統合中。原著owned APIと固定Native183入力から出自付き30例を使用し、秒のclosed全区画・証明島・未知tail・原半径とinflated所属をそのまま表示する。UIへF/m・距離・KKT・sqrt・接触solverを追加しない。専用23群と実SDK30照会29model/1hostは個別段で成功、統合/実Blob/公開受入は別に確認する。新外部文献実読/実装転載/依存/素材/有料service/本体license選定なし。

手動flight labローカル受入: 専用23/684Node skip0・54module26entry、実30照会29model1host、source/model/saved全bitsと全30可視JSON・2実Blobの実file/表示/保存bytes/負零/LF一致が成功。349原本と92SDK/runtime91/7通知を保持し、旧41Native/173Fractionは前段証拠継承と明示。cached retryの空表示は未観測falseとし、遅延generation/pagehide/query0はNode別scope。初回mode setup/新HTMLnormalizerの失敗rawを残し、final-002で全再実行した。新外部資料/solver/依存/転載素材/有料serviceなし、World応答は後続。


### 2026-11-04 手動flightラボの公開受入と次の全World境界

機能788ac1bのCI全21段/Pages・62file2242364B・実公開30入力とBlob2件・旧ゲーム操作を確認した。41CTest/Node684/skip0、既存数値核/SDK/他チャットsample349原本は保持。詳細・失敗履歴・48既存GNU警告の同一性は reports/2026-11-04-sphere-triangle-mesh-flight-lab.md。追加外部資料/package/solverはない。次の docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md は既存coreソースの読取設計で未実装。raw plane二契約、acceleratedの非公開cellとthrow時unknown Work、seed順、vector size/保持capacity、source返却3N/実行中4Nを区別し、全pair数値保証へ飛躍させない。まず所有snapshotと全pair一覧を確定するNative前提から進める。


### 2026-11-04 Native World/static-mesh原本と必要pair準備

新prepareは既存World/SDK/gameを変更せず、bounded原本copy後に全検証と全必要pairを確定する。独立全collider二元部分集合から最大188必要＋190静的除外＝378を照合し、有限84/自己12/改変拒否45、Native42CTest/新89群、Node684/skip0・構文/Web54/26をローカルで確認した。355原本とSDK artifactを保持。初回CTest待ち120秒timeoutは残し、製品を変えず300秒枠で完走した。MSVC19.51x64のsizeof×実capacityによる21880Bは保持payload観測でheap/stack上限ではない。Vec3::dotは外部core.cppでstrict source指定外のため、有限x64整合をFMA可全targetの別RN保証にしない。static subnormal/FPcontrol/NaN分類の受入scopeと未実施allocationfault等は docs/WORLD_STATIC_MESH_PREPARATION.md。新外部文献/library/素材/有料service無し、原著SVG/教材を追加。全pair数値認証・伝播・応答は次段である。


Native prepare公開受入6608bc3: Engine41820304200全22段/Pages成功。通常84と全依存source ASan/UBSan84はbyte一致・各独立参照成功、42CTest/684Node skip0、Werror新3TU・旧48warning multiset不変。73Pages＋GitHub完全commit workflow1の74件2430924B一致。実公開図/教材とゲーム2撃破/boost/停止/23正常照会を確認した。初回workflow Pages404とANSI done抜粋漏れの失敗rawを残し、取得経路と抜粋だけを修正して全件受入。新外部資料/依存/素材/有料service無し、prepareはNative専用で数値全pair guard/World更新ではない。次は全closed-cell証拠を所有する球対/平面coverage核。
