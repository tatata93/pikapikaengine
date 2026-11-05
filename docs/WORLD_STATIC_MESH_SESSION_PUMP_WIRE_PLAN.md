# C API pumpと全Report取得の次段契約

2026-11-06。**設計案。新しいpumpやReport exportの実装・受入ではない。**
現在のC API v1はplain-sourceのstage/create/read/reset/destroy。
所有packet wire v1は独立C++層で、数値stepを呼ばない。
段階1の独立primitive/sinkは[診断wire v1](DIAGNOSTIC_WIRE.md)で実Native有限受入。
これは全Report field対応やC API pumpの受入ではなく、次は段階2へ進む。
最上位の実memberと未完箇所は[対応台帳](WORLD_STATIC_MESH_REPORT_EXPORT_INVENTORY.md)に保持する。
旧simulation API／既存WASMのexportと、既存の数値binding拒否条件を保持する。

## 実コードから確認した点

| 実体 | 確認した契約 | 新APIで必要な扱い |
|---|---|---|
| owner::Pump | status、target token、scheduler_calls、optional実PumpReport | owner gate拒否とモデル拒否を混同しない。reportなしを成功Reportで埋めない。 |
| owner::Registry::pump | target→origin slot/generation→実scheduler一回。進行後をcatchで隠さない。 | wrapperで再queryや「rollbackした」という代替結果を作らない。 |
| q::PumpReport | before/after、elapsed、rounding interval、progress、original、9boundary、8queue plan、8attempt、budget/work/storage | headerの成功tick数だけへ切り詰めず、全active prefixとoptional／未実行を取得する。 |
| ControlledReport→AdvanceReport→GuardResult | 私有成功と外側commitは別。guardに全pair、variant child、requested/used settings、known/upper/exact、message omissionがある。 | 実childと費用・拒否・成功prefixをそのまま残す。精度が不明な値をexactへ変えない。 |
| q fixture number() | finiteを要求してからdecimal化 | NaN/Infinityを含む不正elapsedの実診断を、既存finite fixture writerでexportしない。 |
| q fixture boundary() | 固定prefixから一時vectorを確保 | getterはcached Reportを直接辿る。active World再読込・再構築やguard再実行で補完しない。 |
| guard fixture CoutTo | 一部childでstd::cout.rdbufを全体差替え | 製品の出力は専用sinkへ渡し、process全体の出力を変更しない。 |

根拠はrepositoryの`world_static_mesh_session.hpp/.cpp`、
`world_static_mesh_flight_controlled_scheduler.hpp`、`world_static_mesh_flight_controlled_tick.hpp`、
`world_static_mesh_flight_advance.hpp`、`world_static_mesh_flight_guard.hpp`と対応fixture writer。
外部資料や既存製品の実装を読んだという記録ではない。旧writer原本は変更せず比較のoracleとして保持する。

## 非破壊のAPI追加

既存pp_ws_resultのfield順／サイズや関数signatureを変えない。
pump専用の別result型でHost、packet admission、token syntax、owner、actual modelを分ける。
Host交換拒否は下位owner/model未呼出しとして返す。入力修復や旧packetへのfallbackはしない。
targetとrequest-originの3word tokenは別々に渡す。
elapsedは別のF64で、非finiteも実owner／モデル判定との順序を定める。
body ID／expected tickはfull64、generationは既存53bit、source revisionとreport受領番号は別の整数。

packet decoderの全確保はdelegationより前。現4sessionのWorld／clockは実Registryだけが所有する。
実pump後にallocating read/log/serializationを実行しない。
std::optional<owner::Pump>と提出envelope/packetの所有値を、検証したnothrow moveでcacheする。
cache受領番号が上限なら、実pumpより前に拒否してwrapを防ぐ。
提出原本と実Report.original／capture partialは別の領域として保持し、未観測を原本から埋めない。

read cacheとpump cacheは独立。既存readは次の成功readまで保持し、pumpで暗黙更新しない。
reset/destroy後にも過去pumpを読める寿命を定める。context削除前にcallerが所有copyする。
Host拒否で前回cacheを残す場合は、新規cacheの有無と受領番号を明示し、前回結果を今回の成功に見せない。

## 全fieldを返す取得経路

最初はNativeの完全な独立取得経路を作り、対応fieldと順序のinventoryを固定する。
F64はbit word pair、u64/tick/size_tもword pairなど、非finite・負零・53bit超を失わない形式を選ぶ。
enum ordinal／bool／optional／variant種別と全原本・保持結果を区別する。
数値bindingの64hexは構成識別であり、新しいruntime unlockや全artifactの証明ではない。

取得はcached const Reportだけを参照する。chunk callbackまたは有界record getterで容量・停止・
再入・範囲外を検査し、失敗した途中documentを完成DTOとして公開しない。
取得中の確保／sink失敗は取得エラーとして返し、既に進行したWorldを失敗前へ戻ったと報告しない。
全body／plane／packet／face／pair／child／audit／partition／frontierと、拒否後の未実行tailも対象。
schema対象headerが変わったとき、未対応fieldを黙って捨てるserializerを有効にしない。

## 受入順序

1. 完全Report取得用のprimitive/type/schemaと専用sinkをNativeで固定する。非finite／負零／full64／
   UTF-8またはbyte保持、sink停止と再入を実値で検証する。
2. 所有cacheの全Reportを新取得経路へ通し、旧finite writerの全値へ独立復号して照合する。
   正規化は既に許可した数値構成IDの特定pathだけ。名前／順序／全typed値・bitを比較する。
3. C API pumpを追加し、実commit／拒否／prefix／retry elapsed0／stale／foreign／所有寿命を試す。
   plain-source subsetと、既存77操作全体のmesh/guard付き領域を区別する。
4. Native MSVCとGNUの通常／真Debug拒否／全依存ASan-UBSan、実allocator故障とpost-child条件を別に確認。
5. その後にWASMのsource/compiler/FP/artifact条件、所有JSと操作ラボ、ゲームへの接続を検証する。

この案をC API pump、全allocator経路、thread atomicity、全clock/commit命令、一般接触応答、
流体・材料損傷・車両航空鉄道・IK制御・高精度撮像の完成として扱わない。
