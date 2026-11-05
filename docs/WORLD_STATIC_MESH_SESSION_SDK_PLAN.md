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
