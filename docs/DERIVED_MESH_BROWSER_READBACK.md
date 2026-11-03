# ブラウザの単件・まとめ読出し比較

2026-11-04 JST。**実装・ローカル受入済み、公開確認は別記録**。[検証記録](../reports/2026-11-04-derived-browser.md)に全実行数、失敗、照合結果と配信確認を対応付ける。

対象は [小メッシュ計測ラボ](../tools/derived-gpu-lab.html)、その専用試験と `scripts/verify-derived-gpu-lab.mjs`。既存の [まとめ読出しAPI](DERIVED_MESH_BATCH_READ.md)、SDK66 / ABI v1 / F64 output64を使い、C++数値核・原本・rendererの資源契約は変えない。[計画](DERIVED_MESH_BROWSER_READBACK_PLAN.md)から、明示mode・記録version・同条件照合を実装する段階である。

## 手動実行の範囲

読出しselectorの既定はsingle。batchは利用者が明示して比較する。mode変更やページ読込みだけでは数値計算・GPU描画を開始しない。baselineとinstrumentedは、どちらも選択した**同じmode**で実行する。baselineをsingle、instrumentedをbatchに分けた差分を計器の費用として扱わない。

1 runは4・64・512面のうち1 case、1 modeだけ。初回1組・warmup1組・measure3組を固定し、各組の通常/計器付き順を交互にする。上限は10 prepare、20 checked draw、10 fresh upload、10 cache再描画。正常な比較受入の予定は3 case×2 modeの6 run、合計60 prepare / 120 drawであり、自動無制限反復を追加しない。GPU不在・取消・時計異常等で未実行になった件数は別に残す。

入力とSource、model/camera、解像度はmodeで変えず、共有case settingsを変更しない。run開始時にmodeと `{...settings, readback}` を所有snapshot化する。run中はcase/mode/run/reload操作を無効化し、終了後に次の明示操作を受け付ける。

## 能力判定と世代

不正modeと、batch指定で新export `pp_sim_derived_mesh_records` が無い場合はGPU初期化・入力交換・queryより前に明示拒否する。旧SDKのsingle能力は維持する。存在するbatchが不正packetや実行errorを返したときは失敗にし、singleへのfallbackや旧DTOの表示で隠さない。モデル失敗とhost能力拒否を区別する。

mode/case変更では旧表・report・export対象・previewをstale消去し、run世代を進める。原本は保持する。disabledなselectorへのprogrammatic変更、pagehide/hidden、再読込みやdisposeでも取消を通し、各await後の世代確認で古いPromise/callbackによるready/completed復活を拒否する。modeをawait後にDOMから読み直さない。

記録のcohort識別は次の3値とする。

- `sessionId`: 初期化ごとのunique string。
- `runtimeGeneration`: 正常なruntime再読込みごとに増える正整数。mode切替だけでは変えない。
- `runOrdinal`: 同sessionで試行ごとに増える正整数。host拒否や取消も含む。

6 runの比較ではsessionとruntimeGenerationが一致し、ordinalは重複してはならない。途中の失敗・取消による欠番は許し、実行順と欠番を検査結果へ残す。case/modeをファイルの並びだけから推測しない。再読込みを挟んだ記録を同じruntimeの性能対として混ぜない。

## 新schemaと過去記録

新出力は次のversion識別を必須とする。

```js
{
  schema: 2,
  kind: 'derived-mesh-browser-profile',
  trialSchema: 2,
  summarySchema: 1,
  readback: 'single', // または明示batch
  settings: { /* 従来の数値設定と同じkey/値 */ readback: 'single' },
  sessionId: '...', runtimeGeneration: 1, runOrdinal: 1
}
```

top-level readbackとsettings.readbackは一致し、1 runにmodeを混在させない。`trialSchema:2` はmode別の実call数と実record数の計時会計を追加する。`summarySchema:1` は従来のphase/kind/group/stage/expected/valid/unavailable/statisticsの行構造と予定1/1/3を維持する。全DTOの `tagged-exact-v1` encodingは変更しない。

旧schema1の4・64・512面＋再読込み後4面という4 runは、当時のbyte/hashとともに不変で保持する。readback不在は「旧版・暗黙single」と分類し、新fieldや過去のgetterRecords実測値を捏造しない。旧4 raw指定はschema1専用、新6 raw指定はschema2専用の検査分岐とし、未知schema・旧新混在を拒否する。旧rawの現SDK数値再生は互換試験であり、新しい同一SDK cohortの性能比較とは別である。

## 数値の同一性とcall会計

各組で全DTOの型、object key/配列順、binary64 bits、全TypedArray bytes、signed zeroを通常/計器付きでexact比較する。最初の組は両方の全encoded DTOを保存し、後続の全比較も省略しない。取得可能なdigestは全trialへ保存し、取得不能はunknownとする。正常な公開受入では全digest取得を要求し、取得不能の故障回帰と分ける。入力・数値settings・author Sourceの不変を監査した後だけCPU行をcompletedへ確定する。

`getterKinds[4]` はkind別ABI call数、`getterRecords[4]` は要求record数。lengthと全4要素をdenseに確認し、疎配列の穴をskipしない。N頂点・T面のcompleted結果では次の期待値を使う。

| 項目 | single | batch |
|---|---|---|
| getterKinds | `[N,T,T,T]` | `[ceil(N/20),ceil(T/20),ceil(T/3),ceil(T/2)]` |
| getterRecords | `[N,T,T,T]` | `[N,T,T,T]` |
| cppGetter.calls | getterKindsの和 | getterKindsの和 |
| outputCopy.calls | 1 + cppGetter.calls | 1 + cppGetter.calls |

F64/U32交換とqueryは各1回。成功した4/64/512面のgetter総数はsingleが18/384/2048、batchが6/68/479という形式上の件数であり、時間短縮率ではない。geometry-nullの失敗prefixはrecord数 `[0,0,0,A]`、入力前host拒否は交換/query/getter/outputが0回。部分auditを成功geometryへ昇格させない。

5 stageは `f64Exchange / u32Exchange / cppQuery / cppGetter / outputCopy`。有限非負の時間と、stage和が全体以下であること、直接の `unassignedMs === elapsedMs - stageSum` を監査する。浮動小数点の逆演算で `stageSum + unassignedMs === elapsedMs` を要求しない。異常時計を0ms成功へ置換しない。

## 同じcohortとNode実SDKの照合

新検査分岐は各caseにsingle/batchを1つずつ要求し、重複・不足・unknown modeを拒否する。入力とSource全文、readbackだけを除いた全settingsのkey/型/値、camera/model、browser/viewport/DPR/visibility、SDK artifact/manifestと配信build markerを照合する。取得不能な識別情報を確認済みとせず、manifestの申告だけで配信byte一致を保証しない。影響ファイルの実配信hashは別の親側手順で確認する。

各modeのfirstPair両DTOを全比較し、別modeとも一致させる。Nodeでも同じ主WASMを実際にsingleとbatchで照会し、全型/key順/bits/bytesと各取得済みdigestへ照合する。Nodeの照会数は別集計とし、ブラウザの60 prepareへ加えない。片方のmodeの結果をもう片方へ補填しない。比較は互換性検査であり、既存Native/主WASM/Fractionの独立数学参照を置き換えない。

## GPU状態・待時間・保存

各runに専用rendererを作り、constructor由来の初期queue完了は別の初期化時間にする。各組の両kindで新しい所有tokenを作ってfresh→同token cacheの順にchecked drawする。freshは `72*T` bytes、cacheは0B。最初のfreshは旧buffer退役0、以後1ずつ、cacheは0。最後のdisposeで残る1bufferを破棄し、所有した専用deviceだけをdestroyする。全転送/退役監査後だけdrawをcompletedへ確定する。

GPU作成/validation/deviceLost/queue error・dispose失敗と、CPUモデル結果・入力原本を別に記録する。GPU利用不能でもCPU数値と原本を保持し、CPU成功をGPU成功としない。callbackや取消後に解決したPromiseで成功へ戻さず、finallyで資源解放を試みる。dispose失敗で「解放完了」と表示しない。

CPU全体・5 stage・未分類残差、token生成、同期render、validation待ち、queue待ちを別々に保存する。queue待ちは呼出時点以前の処理についてCPUが観測した待時間であり、当該meshのGPU単独時間や画面提示時間ではない。adapter情報からhardware実行を断定しない。初回/warmup/measureとfresh/cacheを分け、失敗や無効時計を成功統計へ混ぜない。measure3標本の中央値/nearest-rank p95/最大を残し、中央値同士を足したりbaselineとの差を純粋なwrapper費用へ読み替えない。

rawの保存とexportはsigned zeroを保持するserializerを使う。実ブラウザの収集ではDOMのraw文字列をそのまま保存し、parse→通常JSON.stringifyで-0を消さない。全比較・hash・JSON化は計時外でも次の観測へ影響し得る。

## 現時点の停止線

UI/validatorの回帰とNode468試験が成功した。ローカルの実6 runは60 prepare / 120 draw / 60新規転送 / 60 cache、270,940数値と全typed bytesが別集計の実Node6 queryへ一致した。旧schema1の4記録も136,460数値を再照合した。公開CI/Pages・配信byte一致は検証記録で別に確定する。batchの既定採用、最大容量の実時間アニメーション、robotの更新頻度・ゲーム適用、一般物理/流体/損傷/IK/高精度光学の完成を含めない。既定singleを維持し、性能採用は別の根拠と受入で判断する。

実ブラウザではGPU featureの列挙順が変わるため、検査器はadapter/device featureの取得statusと重複のないstring集合を照合する。この2一覧の順序だけをcopy上で正規化し、rawは変更しない。feature欠損・重複・型/status・他のGPU属性の違いは拒否する。

既存原著図 [derived-readback.svg](learn/diagrams/derived-readback.svg)をbyte不変で再利用する。新しい外部図・素材・packageは導入せず、本体ライセンスは未選定のままとする。外部文献の新規実読をこの実装作業の成果として記載しない。

次は[ロボット背面カバーへの適用案](DERIVED_MESH_SAMPLE_PLAN.md)に沿って、実Source/FK/LBSとゲーム内の更新・資源寿命を小単位で受け入れる。この計画は未実装である。
