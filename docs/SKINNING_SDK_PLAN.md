# 次の最小受入: skinningの共通SDK接続

2026-11-03時点の次段設計。未実装。公開SDKは59exportsのままで、この文書を利用可能なABIとして扱わない。

## 有界な最初の照会

Native核の65536頂点上限と、現C ABIの49152 double入力を区別する。第一段SDKは一照会2048頂点・128bone・8192 influenceまでを明示上限とし、勝手なbatch分割や頂点の省略をしない。さらに小さいSettings予算はそのままC++へ渡す。大meshを扱う次段は、全入力検査と失敗時の全体保持を保った別のchunk契約として設計する。

候補は4exports: bind/queryとそのrecord getter、deform/queryとそのrecord getter。API版1/output64と既存のinput/output領域を保持し、motion/world/光学recordへ干渉しない。resetは新recordも消す。まだ関数名・layoutをfrozen public APIとはしない。

bindは全rest IDとmat4、Settingsを送ってC++ `skinning::bind` を呼ぶ。summary後のjoint getterはID/rest16/inverse16（33値）、diagnostic getterはID/condition有無・値/residual有無・値/pivot flag（6値）を返す。failureのdiagnostic prefixとcompleted jointsを別kindとし、未完成jointsを公開しない。

deform header案は12値（joint/pose/vertex/influence数、Settings5値、予約0を3値）。joint33値×128、pose17値×128、vertexのposition3とinfluence数の4値×2048、influenceのID/weight2値×8192で最大30988 double。49152内に収まる。jointとposeは別々のID列を送って、callerの重複や欠損をJSのMap化で隠さない。

summaryはstatus/位置の有無/position数/diagnostic数/weight residual数等の固定長。record getterはposition3、diagnostic6、weight残差1をkindで分ける。返値は全copy snapshotで、NaN sentinelを使わずoptional flagsを保持する。不正count/enum/予約値/getterは以前のrecordとoutputを保持する。受理したモデルの失敗は新しいno-positions recordとなる。

## 必要な検証

- 既存65fixturesはNativeとSDKの受理域の違いを先に分類する。Nativeだけ65536頂点を扱える試験をSDKの成功として数えない。主SDKで128bone/2048vertex/8192influenceの同時境界と1超過、設定/欠損/重複、raw入力の破損を確認する。
- 通常rest、1骨・2骨、shear、巨大weight/subnormal拒否、既知translation相殺、imported inverseの残差を主WASMへ再生する。Nativeのbinary64 snapshotsと主SDKを照合し、Fraction参照の点比較とbit一致の意味を分ける。
- failed query/getter後の以前output/record、retry、copied results、既存motion・光学・World snapshotとclock、resetを確認する。
- SDKの実source/header/strict flags/runtime通知とartifact hashを再生成・照合する。任意入力の精度やFloat32/GPU描画、material damageの完成とはしない。

その次にstable scene ID/mesh fingerprint/bone IDを持つbinding原本とNativeCLI/JSON/portable往復を追加し、小さな自作メッシュで法線/三角形/Float32検査と描画へつなぐ。現在のmesh v1は頂点配列indexであり、topology変更時のID維持を暗黙に保証しない。
