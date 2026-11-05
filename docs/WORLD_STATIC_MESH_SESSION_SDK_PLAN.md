# 所有World sessionをC ABIへ接続する次段の契約案

2026-11-05。**設計案であり、ABI／WASM／ゲームへの実装・受入ではない。**
最初はNativeの有界交換を独立した追加能力として実装する。
先行する整数token codec v1は[Native単体受入](../reports/world-static-mesh-session-token-wire-verification.json)まで進んだ。
C ABI本体への接続は後続である。既存92 exportsや既存Worldを
新sessionへ読み替えない。Native ownerのGNU受入は専用jobの実結果で先に確定する。

## 現在の実コードから確認した境界

| 実体 | 現在の契約 | 次段で必要なこと |
|---|---|---|
| `simulation_api.h` | `pp_sim_handle`はuint32。既存World16／Hull32、World最大128body／8plane。 | ownerの4session／8body／16planeと同じ型・上限だと扱わない。 |
| `simulation_api.cpp` lookup／encode | 低8bitのslot、23bitの世代、Hull種別tag。上限世代は退役。 | 旧型のbit割当てや意味を変更せず、owner用の独立token交換を設計する。 |
| `world_static_mesh_session.hpp` | slot uint32＋generation uint64、最大2^53−1、非wrap。 | 32bitへの切捨て禁止。wireで整数幅・境界・退役を直接試験する。 |
| 旧交換buffer | F64入力49152／U32入力98304、F64出力64。body出力だけで34値。 | 最大ownerの全readや実Reportを64値へ切り詰めない。有界getterで全fieldを回収する。 |
| 旧body／plane ID入力 | 有限・整数・1..2^53−1のdoubleを要求。 | 新wireで受け入れるID域とuint64交換を明記し、Native全域を無言で丸めない。 |
| `scripts/build-simulation.mjs` | 既存SDK用のsource／header一覧を固定。 | ownerと新数値親を入れた証拠ではない。source・export・artifact原本を別に更新する。 |
| controlled scheduler／advance binding | runtime条件で`__wasm__`とClangを明示除外。 | 既存のブラウザREADYを新ownerの数値進行へ転用しない。 |

根拠はリポジトリ内の[旧C ABI header](../core/include/pikapika/simulation_api.h)、
[実装](../core/src/simulation_api.cpp)、[新owner header](../core/include/pikapika/world_static_mesh_session.hpp)、
[scheduler実binding](../core/src/world_static_mesh_flight_controlled_scheduler.cpp)、
[advance実binding](../core/src/world_static_mesh_flight_advance.cpp)、
[既存WASM builder](../scripts/build-simulation.mjs)。外部仕様を読んだとする記録ではない。

## wireを固定する前に決めること

Tokenは旧handleへ詰めず、slotとgenerationを独立して運ぶ。先行する整数codec v1はslot U32と、generationの
low32／high21をそれぞれU32 wordへ保持する。上位wordの許容域を含めて明示し、整数以外・上限超過・旧世代・退役・
別sessionを実試験する。JavaScript Numberを使う場合も最大世代境界を直接往復し、
Native uint64の全値をNumberで扱えるとは言わない。数値ID／tickカウンタのwire域はtokenと別に決める。

原本はWorld／全mesh／guard／Progress／clock設定をstageしてからcreate／resetへ渡す。
stageの不正入力や交換長超過でactive ownerを変更しない。元のWorld handleをborrowしたまま
保持しない。原本の配列順は実値で比較し、World::add_bodyのID整列を「元順保持」と呼ばない。
旧Worldからのimportを採る場合は8planeという共通subsetを明記する。16planeの新原本stageは
別経路として検証する。未選択の形式を現時点でABIとして固定しない。

Hostの交換失敗、owner Status、実scheduler／controlled／guard診断を別々に返す。
ownerのokは実pumpを委譲したことを示し、tick成功ではない。foreign／stale拒否では
時間受理0／追加model call0、入力不足や物理拒否では実Reportの成功prefixをそのまま保持する。

実pump後に結果保存用allocationが失敗して進行を隠す設計を避ける。返却格納先は実pump前に
準備し、実返却Pumpは検証したnothrow moveで保持する。既存の汎用guarded catchを
「進行済みWorldも巻き戻った」という意味へ広げない。所有結果の保持／getterはcontext操作と
寿命を分け、reset／destroy後も過去結果が読めることを実値で試験する。

全readと全Reportは有界record getterで回収する。offset／index／count／overflow／不足bufferを
検証し、未知fieldや未使用固定slotを捨てない。F64負零、整数型、body／plane／mesh／face順、
全boundaries、実childとguard、元入力と保持結果の全値をNative独立参照へ戻す。
交換bufferやWASM linear memoryのviewはJS APIへ公開し続けず、返却値を所有copyする。

## 最小受入の順序

1. ABIのversion／能力照会、token整数wire、stage／create／read／reset／destroyをNativeで固定。
   旧SDKの全交換・export・旧handleを保持し、同世代別slot、退役、失敗時保持と原本編集を実照合する。
2. Nativeのpump／保持結果getterを接続。実77履歴と独立参照へ往復し、全field／順／bitを比較する。
   Host交換拒否とowner／model拒否を混同せず、実allocator故障と単なるwire改変コピーも分ける。
3. WASMを追加する場合は新しいターゲットのsource／compiler／FP／artifact条件を先に研究・検証する。
   既存`!__wasm__`条件や設定IDだけを外して数値能力を有効にしない。未対応なら明示拒否を保持する。
4. 実WASMのbounded交換、memory成長、失敗復帰、複数instanceと過去結果寿命、全履歴の独立比較を実行。
   その後に所有JavaScript APIと操作ラボ、ゲーム／editorからの接続を別に受入する。

全allocator経路、thread atomicity、全clock／commit命令、whole-heap／deadline、一般接触応答、
流体・材料損傷、航空／車両／鉄道モデルや撮像の完成を、このABI設計や既存READYから主張しない。


## Native整数token codec v1の先行実装

`world_static_mesh_session_wire.hpp`のencode_token／decode_tokenが、token_version=1、
U32[slot, generation low32, generation high21]を定義する。exact3word、slot0..3、
世代1..2^53−1を要求し、high wordの上位11bitを拒否する。wordは整数列であり、
C++ Tokenのメモリ配置やbyte endiannessをmemcpyした形式ではない。

decodeの拒否順はword数→slot→世代範囲→世代0。失敗時は全出力word／token fieldを保持。
宣言spanが実際に読める有効なstorageを指すことが前提で、Hostのpointer／buffer検査は次段。
コードは整数演算と固定配列の代入だけを使う。encode／decodeのokは形式が有効という意味で、
active Registryへの所属・世代照合や入力由来の認証は行わない。

fresh main wfow1で旧20構成JSONがraw一致、Release53／Debug52は旧一覧＋新整数test1件。
実行したのは新testだけで、旧52全件を再実行したとは報告しない。実Release／Debugの各77整数入力は
全文raw一致し、24既知word列、独立Pythonのdivmod／整数和、UINT64_MAX・最大世代・2^32境界・
不正word数・slot・上位bit・0世代と全出力保持、実-O拒否を確認した。
この77入力はWorldの77操作履歴と別である。新wireのGNU実行、C ABI／JS／WASM接続は未受入。


## Native plain-source wire v1の先行実装

`world_static_mesh_session_source_wire.hpp/.cpp`は、body≤8／plane≤16のplain Worldを
有界spanから復元する。meshを持たない独立した形式で、任意の全guard設定のcodecではない。
contact marginだけを明示し、他のGuardSettingsは同buildのNative既定値を使う。

F64列はgravityXYZ／初期時刻／margin／stepの6値、bodyごと26値、planeごと6値。
U32列はbody数／plane数／maxAttempts／tick low32／tick high32の5word、
bodyごとID low32／high32／static flag、planeごとID low32／high32を持つ。
最大310 F64／61 U32で、宣言countは計算した長さに完全一致を要求する。
bodyとtickはfull uint64を保持し、tokenの53bit世代制限と混同しない。

有限F64、static flag0/1と、既存World APIで合法な昇順のplane IDを要求する。
平面の順序不正を自動整列せず拒否し、normal／offset／materialは実World::add_planeの
admissionへ渡す。bodyは有効なplaceholderを確保し、最後の挿入後に全pointerを捕捉してから
元順のraw fieldを代入する。World::add_bodyのID整列で原順を失わない。
Raw bodyの物理的不正や不正clockが形式上有限なら、復元とowner／モデル判定を分ける。
環境は既存intervalのruntime probeで確認し、probe成功をcompiler／全命令の証明とはしない。

全入力をWorld allocation前に固定配列へcopyし、成功時だけ所有PlainSourceを返す。
途中の拒否はsourceなし。デコーダが返したWorldから、実Registryへのcreate／read、
caller編集・decoded source破棄・owner破棄後の過去read寿命をNative assertionで検査した。

fresh main wfop1でRelease／Debugを実build。新source CTestだけを各実行した。
登録はRelease54／Debug53、旧20構成原本raw一致、旧53全件を再実行したとは報告しない。
27ケースの8admit／19refuseを独立参照へ照合し、604 mapped float bits、72負零入力、
最小subnormal、full64 body ID／tick、同時8body16plane、13コピー拒否、実-O拒否を確認した。
両buildの全rawと、名称・文書順の独立性も確認。平面の参照は固定corpusの正確なunit-axisと
norm-twoに限り、一般の1e-8丸め境界の証明ではない。
[局所受入](../reports/world-static-mesh-session-source-wire-verification.json)。
このdecoderの新GNU実行、全allocator故障、mesh、C ABI／JS／WASM、物理stepは次段。


## Source／tokenの実GNU有限受入

2026-11-05 source 77a363bの実GNU13.3 x86-64 job127265818652を有限受入。旧owner親21commandとaddon22commandが成功し、45 production＋2 wire harnessのO1 ASan-UBSan／真Debug／通常版で27source・77tokenの全文raw一致（正規化なし）を確認。source独立604 bit値／各比較13改変拒否と実-O拒否、source・compiler・normalおよび親artifact不変も成功。decoded実job log114737Bと実final JSONを保存し、child raw/objectはrunner-localとして区別する。全portable jobはこの観測時進行中。C ABI／JS／WASM／model step、全allocatorや一般平面境界の完成を意味しない。外部資料・実装・依存・素材・有料操作の追加なし。
[実GNU受入記録](../reports/world-static-mesh-session-wire-gnu-verification.json)。上の「未受入」は各先行段階の履歴で、この段階はC ABI実装へはまだ進んでいない。


## Native lifecycle C APIの有限受入

2026-11-05 Native plain-source C API v1を実装・正式mainへ追加。独立libraryで原本stage/revision、実owner create/read/reset/destroyと固定所有readを公開し、旧pp_sim_handle/SDK/core40/数値profile/sampleを変更しない。fresh wfocm1の実MSVC Release/DebugでCとC++ callerをcompile、両新CTest/各9入力1254 F64 bit値・142負零/全U32の独立参照、12コピー改変拒否と実-O、旧20profile全文一致が成功。stage失敗の旧原本失効/active保持、旧世代/reset/destroy/read寿命、full64 ID/tick、4slot/退役を試験。登録Release55/Debug54だが実行は新CTestだけで旧54全再実行ではない。新C APIのGNU/sanitizer/全allocator故障、pump/mesh/任意全guard/JS/WASM/ゲーム接続は未受入。
[利用契約](WORLD_STATIC_MESH_SESSION_C_API.md)／[受入記録](../reports/world-static-mesh-session-c-api-verification.json)。


## C/C++実GNUと限定故障経路の受入

2026-11-05 C APIの実GNU13.3 C/C++をsource57d8bd8/job127285493025で有限受入。15command、全46production+2harness（C1）の通常/真Debug/明示C+C++ O1 ASan-UBSanで各9/1254bit/142負零と全U32/rawが正規化なし一致、実-O/source/normal/parent/compiler不変も成功。decoded137908B/実JSON保存、child raw/objectはrunner-local。全6Engine/Pages成功・manifest2018件61150288BのGit照合も確認。別のNative Release故障試験はcontext1+stage14/create3/reset3/read2の実bad_alloc23地点と4outer×5再入20、初期捕捉/全過去cache/active owner/世代/復帰/非確保getterを確認。fresh wfocam1 mainでも2CTest・旧20profile・旧9/1254bit/全故障raw一致が成功。登録Release56/Debug54、Debugは一覧だけ・旧54全再実行ではない。最初のMSVC NDEBUG表記parser失敗を保持し、fresh wfoca2で補正。新故障testのGNUは別1command driverと14コピー拒否/実Windows拒否0commandまでで未実行。全allocator/OS OOM/aligned/CRT/thread/post-pump faultやpump/mesh/full guard/JS/WASM/ゲームの完成ではない。
[実GNU](../reports/world-static-mesh-session-c-api-gnu-verification.json)／[Native故障](../reports/world-static-mesh-session-c-api-allocation-verification.json)。


## 所有packet入力のNative有限受入

2026-11-06 Native所有tick荷重packet wire v1を追加。最大8packet×8load/384F64/161U32をallocation前に捕捉し、実Native packet/vectorへ所有copy。full64 ID/tick・full32 raw mode・原順・負零を保持し、未知mode/重複ID等をモデル検証から分ける。fresh wfopk2とmain wfopkm1の実Release/Debug各24（11admit13refuse）/27packet82load/492bit164負零・4実丸めmode保持・copy/move寿命が成功。独立16改変拒否/名称順序独立/実-O、旧20profile/全raw一致。登録Release57/Debug55だが実行は新CTestのみ、oldcore/modelをbuild/linkしない。新packetのGNU/allocator故障/C ABI pump/全Report/WASM/ゲームは未受入。有限極値追加前producer001と参照setup失敗も履歴保存。
[packet契約](WORLD_STATIC_MESH_SESSION_PACKET_WIRE.md)。先行aa0e367の実GNU normal C API故障はjob127299536652で1command成功。context1+stage9/create3/reset3/read2=18実故障地点/20再入/全cache・active owner・復帰を確認。Native23とのSTL差を正規化しない。別の親21/22/15commandと全6Engine/Pages成功。decoded141908Bと実final JSON保存、child raw/objectはrunner-local。新packet decoderの受入とは別。


## 全Report取得を先に固定する

2026-11-06 source b01610bの実GNU13.3 packetを有限受入。owner job127340156639/465秒、親21/22/15/1に続く新11command成功。1production+1harnessの通常/真Debug/O1 ASan-UBSanで各24ケース/492個F64 bit表現/164負零・full64・rawmode・4実丸めmode・copy/move寿命が全文raw一致。数値coreをlinkせず、normal/parent全object/library/compiler/sourceは不変。decoded156356Bと実final JSONを保存、child raw/objectはrunner-local。range-loop Werror失敗455ea31と修正wfopkw1は別原本。新packet allocator故障、C ABI pump/全Report取得/WASM/ゲームの受入ではない。
[次段pump/全Report契約](WORLD_STATIC_MESH_SESSION_PUMP_WIRE_PLAN.md)は設計案。旧test writerのfinite制約・境界一時vector・cout全体差替えを確認し、製品には直接流用しない。旧pp_ws_resultのlayoutを保ち、実Reportの所有cacheと別取得エラーを設計する。
