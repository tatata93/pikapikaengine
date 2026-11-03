# ブラウザでsingle / batchを比較する最小受入案

2026-11-04 JST。**設計のみ・UI未実装**。対象は既存 `tools/derived-gpu-lab.html` / `.mjs` と専用試験・記録検査器の次の変更案である。この文書だけを追加し、今回UI・engine・renderer・SDK・既存記録は変更しない。

[まとめ読出しの実装契約](DERIVED_MESH_BATCH_READ.md)はローカル受入済み。66 exports / ABI v1 / output64、明示 `readback:'batch'` と既定singleを前提にする。公開コードef01017のCI/Pagesと既存singleの互換動作は別の統合報告で確認済みであり、本計画の完成や実ブラウザの両mode性能受入とは同一視しない。既存Node比較でも64面の通常経路に一貫した短縮はなく、batchを既定へ変更する根拠は得ていない。

## 変更する入口と有限な回数

既存ラボへ読出しのselectorを1つだけ加える。

- 初期値: 「単件（single・既定）」。もう一方は「まとめ読出し（batch・比較用）」と表示する。
- 1 runは選択caseと選択modeだけを実行する。run中は両selector・run・runtime再読込を無効にする。ロードやmode変更だけでprepareやGPU描画を始めない。
- 従来どおり初回1組、warmup1組、measure3組。各組の通常baseline / 計器付きinstrumentedの順序を交互にする。**baselineとinstrumentedは同じreadback**を使い、通常をsingle・計器付きをbatchに分けない。
- 1 runは10 prepare、20 checked draw、10新token転送、10同token cache再描画。GPU/時計/監査失敗時の未実行は別に数える。
- 正常受入は4・64・512面 × single / batchの**6 run、60 prepare、120 draw、60新転送、60 cache再描画**に限定する。各runは個別の明示操作とし、6 runを自動開始・無制限反復する機能を足さない。

実操作順は、例えば4面 single→batch、64面 batch→single、512面 single→batchとし、case/modeと実行ordinalを全記録へ残す。同一ページのruntimeと同じ生成済みcaseを使い、各runには専用rendererを新規作成する。順序を交互にしても温度・ブラウザ負荷・JIT・GPU cache等の影響は除去できない。run順や再読込の有無を伏せず、因果を証明した比較と呼ばない。

## modeを通す場所と能力検査

run開始時にcaseの元settingsを所有copyし、`{...settings,readback:selectedMode}` を通常・計器付き両方へ渡す。数値原本・triangles・座標・源Source・camera・model・解像度はmode変更で変えない。caseの共有settings自体へreadbackを書き込まない。

modeの不正値と、batch選択時の新export欠如は**GPU初期化・入力交換・queryより前**に明示拒否する。旧65-export SDKでもsingleを実行できることは保つ。batchが存在するのに不正header/payloadや実行errorを返した場合は失敗を記録し、singleへfallbackしない。旧結果・部分DTOを表示して成功へ見せない。能力拒否と受理後のC++モデル失敗は別に保持する。

## schemaと過去4 runの互換性

既存公開ラボは `schema:1` でreadbackを持たず、singleのgetter件数を前提にしている。新modeを同じschemaへ黙って追加せず、新規出力は **`schema:2`** とする。推奨する明示識別は次のとおり。

```js
{
  schema: 2,
  kind: 'derived-mesh-browser-profile',
  trialSchema: 2,
  summarySchema: 1,
  readback: 'single', // settings.readbackと必ず一致
  settings: {maxVertices: 2048, maxTriangles: 32768,
             sqrtRefinements: 128, readback: 'single'},
  // input, sourcePreparation, trials, firstPair, summary等は従来の配置
}
```

`summarySchema:1` は既存のphase/kind/group/stage/expected/valid/unavailable/statisticsの行形状と、初回1・warmup1・measure3の意味を維持する。1 run内にmodeを混在させず、各行はtop-level readbackに所属する。画面では選択modeと完了記録のmodeを明示する。`trialSchema:2` ではCPU計時に実測 `getterRecords[4]` が存在することとmode別call会計を要求する。DTOの `tagged-exact-v1` encodingは別の既存契約で、変更しない。

既存の4/64/512面＋再読込後4面の4 run rawと当時の検査器は、byte/hash付きでそのまま保持する。新検査器はschema1とschema2を明示分岐し、未知schemaを拒否する。CLIは既存の4 rawパス指定をそのままschema1専用として保持し、新しい6 rawパス指定をschema2の別branchにする案とする。ファイル数だけで内容を推測せず全schema/case/modeを検査し、旧新混在を拒否する。

- schema1は「旧版・暗黙single」と分類する。mode不在をbatchやautoと推測しない。
- schema1にgetterRecordsが無い場合、過去の測定値を捏造して追記しない。必要な理論record数は「既知inputから導いた期待値」として別項目で扱う。
- 旧4 runをschema2に書き換えたり、SDK/buildの異なる旧値を新6 runの性能対として混ぜない。旧記録の互換再生と、新しい同一SDK cohortの比較は別の受入である。
- 旧rawの全DTOを現Node SDKで再照合する場合も、数値互換の試験と明記する。旧SDK/配信hashの不一致を消して「同条件の性能比較」としない。

実装時にfield名を変える必要があれば先に契約を更新し、rawを生成する前にUI・検査器・試験で同じversionを固定する。

## 1 run内の数値と会計

既存の原著exact serializerを使い、各組で全DTOの型tag、key/配列順、binary64 bits、全TypedArray bytes、signed zeroを通常と計器付きの間で比較する。最初の組は全encoded DTOを両方保存し、以後も全比較を省略しない。digestは取得可能な場合に全trialへ記録し、未取得ならunknownとする。hashの一致だけで、実行中の全比較や入力不変監査を省略しない。

completedのN頂点・T面では実record数が `[N,T,T,T]`。singleの実call数はこれと同じ。batchの実call数は次のとおり。

```text
[ceil(N/20), ceil(T/20), ceil(T/3), ceil(T/2)]
```

`getterKinds` はkind別ABI call数、`getterRecords` はkind別に要求したrecord数として区別する。どちらもdenseな期待側から全4要素とlengthを監査し、疎配列のeveryによる穴skipを許さない。これらのcounter自体を成功件数とは扱わない。

| 正常case | single calls | batch calls | 実record数 |
|---|---|---|---|
| 4面/6頂点 | `[6,4,4,4]` | `[1,1,2,2]` | `[6,4,4,4]` |
| 64面/192頂点 | `[192,64,64,64]` | `[10,4,22,32]` | `[192,64,64,64]` |
| 512面/512頂点 | `[512,512,512,512]` | `[26,26,171,256]` | `[512,512,512,512]` |

完了時はF64/U32交換・query各1、`cppGetter.calls=sum(getterKinds)`、`outputCopy.calls=1+cppGetter.calls`。5段階の有限非負時間、sum<=elapsedと、直接の `unassignedMs===elapsedMs-sum` を確認する。逆演算の `sum+unassigned===elapsed` は要求しない。失敗prefixはgeometry-nullのまま `[0,0,0,A]` recordであり、一般の成功式へ押し込まない。入力前host拒否は各stage0である。

C++ model completedと、全bit/入力/Sourceの監査成功を分け、監査完了後だけCPU行をcompletedへ確定する。数値不一致や入力mutation、転送監査失敗、無効時計を有効な成功summaryへ混ぜない。GPU不在でもCPU数値・原本を保持し、CPU成功だけでGPU成功としない。

## 別mode間とNode実SDKの照合

新しい6 runをcase/modeで一意に照合する検査を追加する。順序はrawに保持するが、ファイル位置だけでcaseを推測しない。各caseについてsingleとbatchを必ず1つずつ要求し、重複・不足・unknown modeを拒否する。

1. 同一cohort内のSDK artifact SHA/manifest、配信build marker、browser環境・解像度/DPR/可視状態・camera/modelを監査する。source/hashを取得不能ならunknownを記録し、同条件を確認済みとしない。配信byteの確認は既存の親側手順を使い、run中へ53原本の全fetchを持ち込まない。
2. `input` とauthor Sourceの全文をexact比較し、共通settingsはreadbackだけを明示的に除いた全key/値/型で比較する。単にsettings全体を無視したり、hashだけで形状一致としない。readbackはtop-levelとも一致を要求する。
3. 各modeのfirstPair両encoded DTOを全比較し、別mode同士も一致を確認する。取得済みの全trial digestは同じ全DTOのSHAへ一致を要求する。digest不取得の場合は別modeのfirstPair全比較と各run内の全比較記録を残し、後続trialの外部hash再検証は未取得として明記する。
4. Nodeで**同じ主WASMの実queryを両modeで実行**し、browser firstPairの全型/key順/bit/bytesと各digestへ照合する。Node query数は別集計で、ブラウザの60prepareへ加えない。Native結果やsingleの結果をbatchへ補填しない。
5. 初回/warmup/measure、通常/計器付き、fresh/cacheを分離した全raw・summaryを検査する。各phaseの予定1/1/3を固定し、早期終了で未実行が減った場合も不足件数を隠さない。

`crypto.subtle` が取得できる通常の公開受入では全digestを揃え、取得不能の故障回帰とは分類を分ける。snapshotの数値正しさは既存Native/主WASM/Fraction受入を継続し、browserの同一性比較だけを独立数学参照へ読み替えない。

## GPU・時計・世代の既存契約

専用rendererを各runで作り、constructor由来の初期queue完了を待って別の初期化時間へ含める。各組の両kindに別の新tokenを作り、同じIDでfresh→同token cacheを描く。新tokenのfactory費用も別計測とする。

- freshのuploadは毎回 `72*T` bytes、cacheは0B。各drawのafter drawCalls=1、triangles=Tと全buffer末尾を既存renderer回帰で維持する。後者の全byte/末尾監査は既存の転送stub回帰であり、実ブラウザでGPUメモリを読み戻した証拠とはしない。
- 1 runのfresh10回では最初の旧buffer退役0、以後1ずつ。cacheは退役0。最後のdisposeで残り1を破棄し、所有した専用deviceだけをdestroyする。全転送/退役監査後だけdrawをcompletedへ確定する。
- renderer作成/初期queue/checked drawの各await後にcurrent世代・dispose・GPU callbackを再検査する。callback後に解決したPromiseでready/completedへ戻さない。常にfinallyでdisposeし、GPU error時にも数値原本を消さない。
- selector変更は旧report・表・export対象・previewをstale消去し、epochを進める。通常はrun中disabledだが、試験からのprogrammatic変更やpagehide/hiddenでもcancelが働き、古いcallbackが新modeへ復活しないことを確認する。実行中のmodeはrun開始時に所有snapshot化し、await後にDOM値を読み直さない。
- runtime/GPU初期化、Source準備、CPU/GPU helper・factoryの時計throw/非有限/後退/差overflowとhelper固有clockErrorを保持する。実処理が完了しても無効時間はnull、成功時間の0へ置換しない。dispose失敗で資源解放完了を表示しない。
- 画面のJSONとユーザー操作によるexportは既存のsigned-zeroを保持するserializerを使う。ブラウザ記録の収集もDOM raw文字列を保存し、parse→通常JSON.stringifyで原本の-0を消さない。読み込んだだけの自動実行は追加しない。

queue waitは呼出時点以前の全queue処理についてのCPU観測待ちであり、当該meshだけのGPU時間・display提示時間ではない。adapterのfallbackフラグやdescriptionからhardware実行を断定しない。計器・Promise scheduling・時計・全DTO比較・hash/encodeの観測負荷は未較正である。

## 影響のある受入へ絞る

旧公開の操作数をそのまま再現することを目的にせず、今回変わるtransport選択・会計・世代・schemaを中心に試験する。既存の数値核/rendererの細部は変更しないので、その独立試験を継続し、同じ大容量prepareをいたずらに増やさない。

| 層 | 必要な確認 | 根拠 |
|---|---|---|
| UI stub＋実SDK | 既定single、明示batch、3caseの全DTO比較、ceil callsと実records、mode変更時stale消去 | selectorとsettings経路・telemetry監査が直接変わる |
| 失敗注入 | 旧SDKbatchの交換前拒否、不正mode、batch不正packet/ABI error→fallbackなし、次の明示single/batch正常復帰 | エラーで比較条件が変わることを防ぐ |
| 非同期・時計 | mode変更/hidden/pagehide時のcreate・queue・draw待ち取消、旧callback、時計/残差異常、dispose失敗 | mode selector追加で既存の世代境界を壊さない |
| raw検査器 | schema1の既存4runを不変で再生、新schema2の6run、重複/欠落/mode/settings/getter/digest/bit/転送/timing変異の拒否 | 過去互換と新しい両mode比較の取りこぼしを検出する |
| 実ブラウザ | 初期未実行→手動6run、全120draw/60upload/60cacheと解放、保存raw→Node実SDK照合 | stubだけではWebGPU・実イベント・配信整合を確認できない |

実ブラウザでは先に1caseで新modeの基本動作を確認し、その後に有限6runを取得する。受入rawの失敗や再試行は消さず別runとして分類し、正常6runへ黙って置換しない。公開配信のcode/SDK/importmap整合と影響ファイルのbyte検査を別に行う。

## 効果の扱いと停止線

数値・所有・呼出し会計・GPU資源の正しい動作が第一の受入であり、時間短縮を必須の成功条件にして失敗データを除外しない。measure3の通常SDK全体と5段階のraw/中央値/nearest-rank p95/最大をcase別・mode別に表示する。中央値の和やbaselineとの差から純粋なwrapper費用を捏造しない。header増加・cache/slice・所有copy・温度/負荷/順序も解釈に残す。

6runの有限比較は一般性能の保証ではない。GPU単独時間、60fps維持、最大32768面の実時間アニメーション、robot更新頻度/ゲームへの適用、一般物理・流体・損傷・IK/光学の完成を主張しない。一貫した効果が未確認またはbatchが遅いcaseがあれば、**既定singleを維持**し明示比較機能として残す。既定変更は別の根拠と受入が必要である。

## 読取した既存原本

この設計ではAGENTS、PLAN末尾のまとめ読出し記録、DERIVED_MESH_BATCH_READ.mdと、その計画、既存 `tools/derived-gpu-lab.mjs` / `.html`、`tools/derived-profile.mjs`、`tools/derived-gpu-profile.mjs`、`tests/derived-gpu-lab.test.mjs` / `derived-gpu-profile.test.mjs`、`scripts/verify-derived-gpu-lab.mjs`を参照した。新しい外部文献・実装・画像・libraryを導入した段階ではない。今後の実装所有は着手前に分け、原本mesh・C++数値核・renderer・SDK ABIをこのUI追加の都合で変更しない。
