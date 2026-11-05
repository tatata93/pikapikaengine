# tickごとの荷重列と、保持するframe時間

2026-11-05。次の最小Native計画。**このscheduler入口は未実装・未実行。**
単一tickのcontrolled APIは5df636aで通常CMakeへ登録しMSVCで局所受入した。
そのGNU13／全依存sanitizerの公開受入を先に確定する。
旧scheduler2源／advance7源／controlled tick2源／SDK／sampleを変更する計画ではない。

## 解く不足

旧Scheduler::pumpは成功した最初のtickで力を消費する。単一controlled APIなら
tickごとに別の絶対荷重を渡せるが、frameのelapsed、due数、成功prefixと入力の
消費をcallerが別々に管理する。両者を結ぶ、callbackを持たない入口が必要になる。

候補は独立した`world_static_mesh_flight_controlled_scheduler::Scheduler`。
一つの論理World／Progressへ排他的に用い、pumpへ最大8個のowned-data型
TickLoadPacketのspanを渡す。設定はstepとmax attemptsだけで不変、旧schedulerと
同じstep域[2^-20,.1]秒、elapsed/backlog上限1秒、最大8attemptを維持する。
既存pumpの名前・意味・源識別子を変えず、新wrapperの別識別子と受入を作る。
新wrapperのbindingには実controlled bindingと上流7源の対応を結び、旧schedulerの
受入済み時間会計から借りた式を、新wrapper全体の機械証明とは呼ばない。

## 時間とpacketの消費

環境／binding／hard counts→所有captureと全slot準備→elapsed admission→tick列の順。
全部を一frame transactionにして成功prefixまで巻き戻す方式ではない。

1. elapsedをbacklogへbinary64 RNで一度だけ加える。sequence上限、backlog上限、
   admissionと最大8減算の丸め誤差、予約費用を外部進行前に計算する。
   受理前の拒否なら時間もWorldも変えない。受理後の再試行はelapsed=0。
2. dueがある限り、そのpumpで次の未消費packetを**一つだけ**実controlled APIへ渡す。
   stepをHとし、packetは総force／torqueの置換、expected_tickをそのまま使う。
   未来のexpected_tickを自動修正せず、最後のpacketの力を次tickへ再利用しない。
3. 実childの外部commitが成功した場合だけ、対応するcredit減算とpacket消費を行う。
   committedTicksとpacketsConsumedは同数。実controlled Reportを丸ごと所有する。
4. child拒否ならそこで止める。成功prefixのWorld／Progressと減算済みcreditを残し、
   拒否packetと未実行tailを未消費にする。次pumpへ同じ未消費packet、または修正した
   同expected_tickのpacketを渡せる。すでに成功したpacketを再提出すればstale拒否。
5. dueは残るがpacketがない場合は`awaiting_input`として止める。力0のpacketを
   作ったり、旧advanceへfallbackしたりしない。due0なら入力は消費しない。
   packet数がdueより多いときの余剰tailも未使用のまま所有診断へ残す。

max attempts到達によるstep_budget、入力不足、実child拒否、due0のwaitingを分ける。
plannedAttemptsは時間とstep上限から決まり、実child数と区別する。packet不足で
呼ばなかったslotも未実行予約として記録する。droppedSecondsは常に+0。
hard packet count9はcapture／admission前拒否。許容数内の各packetのmode／ID／
荷重／expected_tickの意味検査は**その実tick**で行い、未使用未来tailの不正値を
「適用済み」とはしない。有限full JSONと非finite raw unitの範囲も分ける。

## 成功prefixを隠さない所有診断

source／packet列はadmission前に所有captureする。childはそのowned sourceとpacketを
使い、一回ずつ呼ぶ。入力spanやbody pointerを返却後へ借用しない。

PumpReportは設定、before/after backlogとsequence、requested elapsed、admission、
全queue plan／丸め誤差、元packet列と消費prefix、各実child Report、実World／Progress
の連続したbefore/after、未呼出tailと予約上界を残す。child.committedとその内部の
private child.committedを区別し、私有成功を外部tick成功へ読み替えない。

外側で投げ得る準備／捕捉／slot確保は最初の外部commit前に終える。
commit後の各境界の実World観測は最大8body／16planeの固定array等、代入がnothrowの
形式へ保存する。返却Reportのmove／destruct、実child移動、credit／count保存も
static assertionで固定する。後からvectorを伸ばす／文字列を作る／例外catchで
成功prefixを失敗前の状態へ戻したように報告する処理を入れない。
この固定観測の実装・sizeof・原順／負零保持は別に試験する。

予約は旧guardのsettled upper limits×時間上のplanned slotsだけを表す。
controlled copy／全snapshotのheapやallocator overhead、RSS、stack、deadlineまで
旧16MiB論理payloadへ含めない。外側のcapture／copy／store費用も別counterとする。

## 最初に通す受入

| 場面 | 実記録と独立参照 |
|---|---|
| 一frameに2tick | m=2、g=0、H=1/16、Fx=4→-4で最終x=1/128、vx=0。旧pumpの初回荷重だけの結果と区別する。 |
| 入力不足とretry0 | 2tick分時間、packet1個だけで1成功・1未呼出。次pumpのelapsed0と次packetだけで完走し、二重時間受理・力の再利用がない。 |
| 成功後の拒否 | 第1成功、第2guard拒否のWorld／Progress／credit／入力消費prefixを全保存。safe packetへ変えて同tickをretryする。 |
| packet不正と未使用tail | 重複ID／stale tick／static非零を実該当childで拒否。due0や余剰tailは未実行として残す。count9は受理前拒否。 |
| 予算と端数 | attempts1／8、fractional backlog、elapsed0、time上限／overflow／sequence上限、max attempts停止、毎pump丸め誤差を整数RN参照で検査する。 |
| 完全所有と後続操作 | caller編集で過去Report不変。全raw原順／負零とbody address安定、元mesh／settings不変、実World境界と各child originの連続を照合する。 |

full checkerは新しいpacket consumptionとcreditを独立に再構成し、各**実controlled
Reportだけ**を既存の純粋controlled参照へ渡す。合成のWorldAfter／pointer行、guardの
再照会、未返却childの補填を禁止する。label／scenario名を判定根拠にしない。
packet再利用／消費ずれ、elapsed二重受理、成功prefix消失、unknown work削除、負零と
型の改変をコピー負例として拒否し、実allocation fault注入と混同しない。

まず独立Native prototype→有限full／独立負例→正式CMake→GNU全依存sanitizerの順。
owned World session、世代handle、packetのpump間永続enqueue、SDK／WASM／ゲーム、
制御graph／PID、一般接触応答・流体・材料損傷は別の後続段階である。
外部実装／ライブラリ／素材の追加はない。
