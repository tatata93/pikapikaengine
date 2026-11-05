# Worldと時計を所有するNative session

2026-11-05。**隔離MSVCの全77操作と独立owner protocol／数学参照を受入。正式main／GNU／SDKは未受入。**
実装は`world_static_mesh_session::Registry`。既存の実controlled schedulerを呼ぶ別ownerで、
旧計算核やIDを変更しない。[設計](WORLD_STATIC_MESH_SESSION_PLAN.md)は当初の契約と残件を示す。

## 寿命と所有

Registryは最大4sessionを保持する。各sessionはWorld、全静的mesh、guard設定、Progress、
Schedulerを所有し、create時に実Worldをそのままcopyする。add_bodyへ渡し直す正規化を挟まず、
原順・全field・負零を保存する。readは所有値copyを返し、mutableな内部参照を返さない。
caller原本や返却snapshotの後続編集はactive ownerへ届かない。

createが成功することと物理入力が進められることは別である。body8／plane16／mesh4／face64を
越える所有を拒否するが、範囲内のraw数値は保持し、モデルの不正は実pumpの診断へ任せる。
NaNのraw bit所有は単体assertion1件を確認しただけで、有限JSON codecの完成ではない。

## 入力の世代と呼出し先

Tokenはregistry内slotとgeneration。世代は1から始まり最大2^53−1、wrapしない。
RegistrySettingsのgeneration_limitはこの上限以下へ制限でき、退役境界の直接試験にも用いる。
reset成功とdestroy後のslot再利用で世代が進む。destroy直後はinactiveで拒否し、世代上限の
inactive slotは再利用せず退役する。上限を大きくし直すAPIはない。

`pump(target, Request{owner, elapsed, packets})`は呼出し先targetとrequest側のownerタグを
別に照合する。有効targetでもownerのslotが異なればforeign_session、世代が異なれば
stale_generation。物理計算も時間受理も行わず、scheduler_calls=0、reportなしを返す。
同じtick番号の2sessionでも、この外側照合を省略しない。

タグはcallerが明示する取り違え検出用データで、callerが意図的に付け替えた荷重の由来を
認証しない。別Registry／processのtoken照合、永続ID、security capabilityではない。
一つのRegistryへの排他的な同期アクセスと、呼出し中にRegistryを破棄しないことが前提。
busy gateは実装したが、reentrant allocatorやthread競合の実注入試験はまだない。

## resetと実pump

resetは新World／source／設定／時計を私有Sessionへ構築後、unique_ptrのswapと整数世代の
更新で全体交換する。invalid clockやhard countで失敗した場合は旧原本・世代・creditを保持。
成功時は新しいProgressと新規clockへ切り替えるので、旧backlogは持ち越さない。
旧返却snapshotとReportは所有物で、reset／destroy後も変わらない。

owner gateを通れば実Scheduler::pumpを一回だけ呼び、そのReportを移動して返す。
ownerのStatus::okは「委譲した」であり、tick成功ではない。モデルの拒否や入力不足、
成功prefixを実reportのまま残す。post-child catchで進行済み状態を失敗前へ読み替えない。
返却Pump／Read／実PumpReportのmoveと、Snapshot／Sessionの破棄のnothrow条件を型検査した。
自然allocation／nonreturn／post-child faultや全commit命令の証明ではない。

## 今回の有限検証

fresh build/wfo1でconfigure／strict Release build／directed／default-model refusalの4commandが成功。
13lifecycle群と5実numerical群で、原本copy・負零・read独立、2owner同tickのforeign拒否、
stale／destroy／reuse、固定4slot、世代上限退役、reset失敗時保持、4種類のhard境界を検査。
実m=2／H=1/16／Fx4→−4の2tickでx=1/128、vx=0、成功後拒否→retry0、入力不足とreset、
raw不正入力と実FE_UPWARD拒否も確認した。元のWorldやcandidateを実観測の代用品にしない。

accepted wfcqm2の実4library／9serializer objectと、wfcq3の実default parentをread-onlyでlink。
同一MSVC19.51/x64のABIと3新tlogのstrict／WX／非LTOを確認した。1938保護pathは全体前後不変。
defaultは実Release default parentのモデル拒否で、実Debug ownerの受入ではない。
新ownerの独立構成ID／全記録・metadata参照／GNU全依存sanitizer／SDK／ゲーム接続は次段。
既存計算核・CMake・SDK・サンプルは変更しない。外部実装・ライブラリ・素材は追加していない。


## 全履歴と独立参照

fresh build/wfof3で3commandが成功し、8scenario／77操作の実履歴4,433,326Bを保存した。
17回のowner pumpのうち10回だけ実schedulerを呼び、18実controlled／17成功tick、18実guardを
返した。独立参照は整数世代と4slotの状態機械から各status／所有原本／reset／destroy／退役を
導き、10実Reportの54数学child（flight18／metric18／planeBox18）も検算した。
183回のpublic readと28実固定境界bodyを区別し、ownerの外側pointer／lookup行を作らない。

knownLiveSlotReadsのnullはharnessに現行tokenがないという意味で、非active heapの観測ではない。
各実read値と過去に返ったSnapshot／Pumpをそのまま所有保存し、後続操作・reset／destroy後も
全field／原順／負零／数値型を照合する。candidateから観測Worldを作り直す処理やguard再queryはない。
caller編集は外生入力で、元sessionに届かないことを確認する。

最後のscenarioでは8body／16plane／4mesh／64faceを同時に保持し、readの独立性を検査した。
これは所有値の上限試験であり、この最大Worldを物理advanceしたという意味ではない。
World::add_body/add_planeはID順へ整列する。初回maxケースの「未整列」という正例条件が
満たされず停止した記録を保持し、fresh full003では入力構築後に公開mutable body APIで
unique IDの置換を行い、入力Worldの実順を変えてからcaptureした。観測ownerをadd_bodyで
再構築せず、owner実装は変更していない。

65コピー改変拒否、scenario改名と文書逆順、3つの実Fraction閉形式、120Hzの実非零丸め誤差、
実-O拒否が成功。削除した小さいコピーcohortがprotocol／数学的には有効でも、固定77入力の
coverage gateで拒否することを確認した。最初のcollectorはAssertionErrorを取りこぼして停止し、
collectorだけを修正した。72操作／57拒否の先行成功とmax追加時の停止も別rawに保持する。

共有scheduler codecは実Report／clock／meshのwriterだけをexportし、library-only時にmainを外す。
純粋verify_pump入口には実read由来の入力値を渡す。旧full-rowの外側pointer検査は保持した。
fresh bridge002の6commandで旧84全文raw一致、独立279数学child／80拒否と、実waiting pumpの
codec／実before-after Progress読取を確認した。新Kernelの精度／thread atomicityの証明へ拡張しない。

正本: [全履歴の受入](../reports/world-static-mesh-session-full-verification.json)、
[codec／純粋参照の回帰](../reports/world-static-mesh-flight-controlled-scheduler-codec-reference-verification.json)。
owner全体の構成ID、実busy／allocator／post-child fault注入、正式CMake／実Debug／GNU全依存sanitizer、
SDK／WASM／ゲーム接続、全clock／commit命令やwhole-heap／deadline証明は未完。
