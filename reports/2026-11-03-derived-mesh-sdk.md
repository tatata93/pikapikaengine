# 原本から派生Float32メッシュを監査する

2026-11-03。既存Native核を共有SDKへ接続し、原本の実FK/LBSから派生メッシュへ進む経路を追加した。原本制作ラボの「Float32位置と法線を監査」で操作できる。コード公開と公開検証の結果は追記する。

## 実装とローカル検証

API version1と既存63関数・入出力容量を保ち、2関数を追加した。最大2048頂点/32768面。JSは交換と検査・コピーだけを行い、法線やLBSの代替計算は持たない。summary20/audit26、空配列・不正設定のモデル結果と不正交換の区別は[ABI](../docs/SIMULATION_ABI.md)と[接続契約](../docs/DERIVED_MESH_SDK_PLAN.md)に記載した。受理したモデル失敗はgeometryなしの新snapshotとなり、不正交換/getterは前snapshotと出力を保持する。

- MSVC19.51 strict buildで全739群/CTest30成功。ABIは65群、既存純粋派生核は54群。Native最大65536頂点/131072面の再実行も既存CTestに含む。
- Node24.14.1は369/369、skip0。新SDK10群とラボ追加4群を含む。実WASMでは2048頂点/32768面の同時上限、1超過、全展開buffer、原入力・snapshot・独立record・resetを検査した。最大容量は参照計算の受入で、60fpsの達成ではない。
- 固定40例は全て実C++ WASMのモデル結果で、host側の失敗合成は0。Nativeと1272数値のbit一致。既存40の入力fingerprintと数学条件は変更していない。
- 新Native probeの原本11例は、正常5時刻・実LBS退化・派生予算/法線未確定・weight underflow・inverse品質・stale restを分ける。原本再保存不変と前段/後段を保ち、WASMとの差1569数値bit一致。計2841数値。等weightの180度回転では、実LBS completedから全頂点(1,0,0)となり、派生核はdegenerate/zero_crossを返す。
- 実WASMの40結果にも独立Fractionのexact Float32丸め/cross/Q/平方不等式による法線参照を適用した。16completed/24期待失敗、成功17面/法線51成分、最大認証誤差上限2.384185870951683e-8。診断prefix1面/3成分は描画成功に数えない。Native/main-wasm各backendで7自己群・2受入・36負例が成功。backend追加はmetadataと子commandの引数だけで、数学条件を弱めていない。
- 既存motion4105 bits、位置skinning5288 bitsの再生と、既存物理・光学の別23回帰commandも成功した。syntaxとWeb build、教材の更新を検証した。

ラボは原本/時刻/Scene変更で古い派生結果を破棄する。派生失敗でも原本保存を許し、前段の数値失敗時には監査ボタンを無効にする。表示するJSONは最初32頂点/32面のpreviewで、照会は全入力を扱う。ローカル実ブラウザ12観測に正常・予算不足/復帰・時刻/原本変更・実LBS退化・前段失敗/復帰を含む。OSファイル選択や実download handlerを今回新たに検証したとはしない。

## 配布物と再現記録

Emscripten6.0.13固定、26 C++/全53 source・header、7通知、2artifactの全hashを照合した。WASM590964B SHA256 `67daefd24c39af1aefa516d28b35c11808684604bed457c1e16eed15b64e8f73`、glue50029B SHA256 `c787373497549b18cfa8bf1fdb8d39195ca0f2d0d456ce42e2debccb960cc0a4`。manifestはdirty buildのbase revisionと実source hashを記録しており、後から清浄なbuildを装わない。旧51source/headerのうちAPI2件以外は同じで、派生核2件を追加した。通知7件はbyte不変。

tracked sampleと他のasset6件は前HEADとbyte不変。SDK3配布物は意図的に更新した。外部package/素材/有料serviceは追加せず、本体ライセンスは未選定。Web build `ebfa843cac6779cc`、39 modules、教材25記事。

`derived-mesh-sdk-verification.json`がSDK全hashとrootのraw/command対応、`derived-mesh-sdk-core-*`がNative ABI/実原本probe9command、`derived-mesh-sdk-js-*`がSDK10試験と独立検証、`derived-mesh-sdk-reference-*`が各backendの全負例command/logを持つ。`derived-mesh-sdk-recipes/`に元の実行用scriptとsource bytesを保持する。CMakeのraw cp932 CTestと別UTF-8変換、全build/test log、実バイナリのhashを残し、exe/lib/obj/toolchainは配布しない。negative変異入力は公開control scriptから再生成できる。

最初のJS試験は旧sensorの必須kindをtest入力から落とし9/10となった。test入力のみ修正して10/10成功し、初回logも保持した。rootの最初の回帰recipeには過去のoracle名の誤記があり、正しい履歴ファイルへ直して全最終commandを再成功した。standalone compile recipeの最初の/Fo quote失敗もignored buildに保持した。失敗や未実行を成功へ数えていない。

## 範囲と次段

監査は量子化したmesh-local CPU geometryに限定する。Canvasは従来のdouble位置の線で、監査済みbufferの3D描画ではない。GPU upload/算術、world/view/clip、画面被覆、自己交差、接触/材料損傷の保証へ拡張しない。次は小さい成功bufferを既存3D rendererへ接続し、変更/失敗時に古いgeometryを表示しない受入へ進む。
