# Entry-window raw C ABI / WASM交換受入

2026-11-04 JST。前段のNative entry proofを独立stage/recordと6exportsで共有SDKへ接続した。初期点・全partition/islands/frontier/tail・最良の負witness/窓・全audit/Work/lastMeshを最大64F64のpacketで交換する。入力拒否は旧stage/record/output/countを保持し、交換できたモデル失敗は新しい診断として公開する。[正式ABIガイド](../docs/SPHERE_TRIANGLE_MESH_ENTRY_ABI.md)参照。

## ローカル受入

- 新API専用24群と全38CTest、586Node skip0、教材12、構文/Web build成功。API/probe/全kernelの既存試験を維持した。
- 固定pure65入力から実model62/host拒否3を別集計。18separated/8entry窓/2初期貫通/34モデル失敗を保持。全1452audit/558証明葉/866partition/276frontier、lastMesh182行1256候補を交換した。実256audit/128partition/127frontier/64保守IDを確認。
- pure完全DTOから別実装のexpected encoderでNative全147638数値/3599負零を照合。実rawWASMとNative wireは146130bits/3525負零一致。WASM packetを同encoderへ別投入して全147638数値/3599負零も一致。packet改ざん27件を両backendで拒否。
- 元pure65の独立Fraction558葉1452audit3840mesh成分・17自己解析/90数学負例を別実行。これは62実行モデルの全fieldがpure診断へbit一致する証拠と組み合わせるが、host3をWASMモデル実行に含めず、新JS所有DTOの復元を実行したとも言わない。
- 旧owned59model3host/50663model bits・原入力3877bitsとmixed62独立数学/71負例、旧mesh/single/simulation回帰成功。
- 86exports/30翻訳単位/61source-header。WASM719410B SHA256 `d1ece57ca29df06e91cf10c7b598a9b073a86b63959d4ef76e2e0da5f84d5f58`、glue58933B SHA256 `7de3e5160b478aea5fcdc10cad4187e4641c592561414b1d99acaeb184562952`。runtime91部品の増減0、7通知hash不変。memory上限設定は旧64→256MiB/stack1MiBを維持し、実高水位の測定とはしない。
- 303保護原本はraw byte不変。旧59source/headerの変更はAPI h/cppの2つだけ、新entry h/cppを追加。24HTMLは生成import map/build queryだけを正規化して不変を確認。Web7999d8fe99c1f44d/49modules/24entries。
- 実local既存guardラボ既定入力/全owned結果324bits24負零が直接Node/WASM再照会と一致。新SDKでゲーム射撃/移動boost/撃破/一時停止、累計72照会全checked/validated・全記録completed・boostclip1/3常駐/error0を確認。新entryはゲーム接触へ適用していない。

初回ビルドは成功し新warning0。ただし初回API試験は3群後に『Later certified island disappeared into prefix』で失敗した。二面の例に、既存pure corpusでは単一面だけが持つislandを要求した試験の誤りである。二面の窓/全候補ID検査は保持し、単一面の実照会でislandを別に検査するようtestだけ訂正した。old ordinary meshの未query stage保持も同groupへ追加した。API/数値核/固定入力は期待へ合わせて変更していない。initial原stdout/stderrを残し、訂正後24群と全回帰を受け入れた。

初回WASM buildは全actual61source/headerの前後hash固定を検査して成功。その後の変更はWASMにcompileしない新Native API testだけで、現61hashもmanifest一致。test訂正を理由に実WASM sourceが変わったとは報告しない。Native probeの初回/最終全packet bytesも同一。ブラウザ最初の戦闘は2撃破後に敗北し、そのstate/reportも保持した。再出撃で1撃破後に停止。72は再出撃を含む累計である。

統合原出力は[checks](sphere-triangle-mesh-entry-abi-checks/)、[機械受入](sphere-triangle-mesh-entry-abi-local-verification.json)、[配布監査](sphere-triangle-mesh-entry-abi-artifacts.json)、[実ブラウザ](sphere-triangle-mesh-entry-abi-local-browser-verification.json)。新図は原著概念図であり数値証明ではない。

## 公開受入

コード[4b03f0c](https://github.com/tatata93/pikapikaengine/commit/4b03f0c7b785b05cce4851107007bbb3b9b159e3)の[Engine CI41777811708](https://github.com/tatata93/pikapikaengine/actions/runs/41777811708)と[Pages41777810766](https://github.com/tatata93/pikapikaengine/actions/runs/41777810766)は全job/step成功。GNU13.3で38CTest/586Node skip0、実Nativeと共有WASMの62model3host・全数値/−0と各27packet負例、元pure65 Fraction/90数学負例、旧SDK/所有/数学回帰が再成功した。

新test/probe各-Wall/-Wextra/-Wpedantic/-Werrorが成功。新API/testをinstrumentしたGNU ASan/UBSan24群（通常strict core archive）、別の全entry核ASan/UBSan76群とLinux Release/ASan fixture bytecmp、旧pure guard69群/API-test25群も成功した。既存36warningは前受入jobの診断multiset/出現数と一致。Windows sanitizerやNative故意allocation/未知work注入の成功は推定しない。

81公開ファイル2,276,534Bがfeature commit blobと完全一致。新原著図を公開ブラウザで目視し、既存ラボ既定入力/全owned DTOの324数値/24負零も直接Node/WASMと一致した。公開ゲームで射撃・移動boost・1撃破・一時停止を実行し、21照会全checked/validated・全completed/boostclip1/3常駐/error0を確認。これは旧証拠の継承ではなく新SDKでの別実操作で、新entryをゲーム接触へ適用した検証ではない。[停止画面](sphere-triangle-mesh-entry-abi-public-browser/game.jpg)と全表示JSONを保存した。

全工程/有限原log405行（全36warning・全Run command blockを含む）/配信/実ブラウザ/原本と配布hashを[公開機械受入](sphere-triangle-mesh-entry-abi-public-verification.json)へ保存。最初の集計はlog抽出にaudits1452の2原行が欠けていたため停止した。403行の初回抽出を別保存し、同一の原workflow logから2行を追加した405行で再集計PASS。CI・数値・source/期待値を変えて成功へ合わせたものではない。

## 次の最小段

[所有JS decoder案](../docs/SPHERE_TRIANGLE_MESH_ENTRY_JS_PLAN.md)に従い、全6能力を入力書込み前に確認し、入力一度capture/所有copy・全packet strict validation・旧80-export拒否/無fallbackを実装する。新entry UIはその後。起動先は既存[ロボットゲーム](https://tatata93.github.io/pikapikaengine/?v=4b03f0c)・[定義線分guardラボ](https://tatata93.github.io/pikapikaengine/tools/sphere-triangle-mesh-trajectory-lab.html?v=4b03f0c)。

有界raw交換を、単一根/厳密物理時刻/接触面法線/manifold/応答、World接続、流体/損傷/専門車両航空鉄道/IK制御/高精度撮像の完成へ広げない。故意allocation/未知work注入、自然parameter_resolution、Windows sanitizerは未検証。本体license未選定、外部solver/素材/課金なし。
