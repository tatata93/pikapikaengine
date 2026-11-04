# World静的mesh自由伝播advanceの別ビルド試作

2026-11-05。次段のNative header/CPPと専用harnessを作成し、既存guardの成果物を変更しない別ビルドで実行した。**本体CMake未登録・新構成の実命令監査未完・公開未受入**。現在のguard機能やゲームへ統合済みとはしない。feature73の公開GNU監査失敗を先に修正し、本段は別の未commit作業として保持する。

## 実装とレビュー

`core/include/pikapika/world_static_mesh_flight_advance.hpp` と `core/src/world_static_mesh_flight_advance.cpp` は現在Worldからguardを一回だけ照会する。時計、全pair/candidateの完備、全原本bit、全宛先を検査し、私有body8bufferのみで全bodyの荷重を+0へ消去・validateする。全失敗可能処理と返却report準備の後、catchの外のnoexcept commitで既存body格納先とProgressを更新する。Body copy assignment、Progress copy、report move/destructionのnothrow条件をstatic_assertした。呼出し中の並行観測・変更はcallerが排除する契約であり、hardware/thread atomicな複数storeではない。

元guard候補・snapshotの力/トルクは診断として保持する。失敗時は全World、荷重、時計、格納先を維持し、advanced_dtは+0。古い外部certificateのcommit入口や旧World stepへの自動fallbackは作らない。FixedClockのvoid callbackへの接続、TOI/mesh衝撃応答、接触支持、SDK/JS入口は本段の対象外。

## 実行した有限検査

- `world-static-mesh-flight-advance-checks/run-20261105-default-001/`：最初のharnessで新TU未設定profileの実拒否・FE_UPWARD/FTZ/DAZ優先拒否を確認。旧guardのreadyだけでは新TUを許可しない。
- `.../run-20261105-default-002/`：clock fixture出力を追加した最終harnessで再度実拒否。新CPP/harnessをMSVC19.51x64の/W4 /WX /permissive- /fp:strictでコンパイルした。
- `.../run-20261105-configured-001/`：全40core CPPを別libraryへコンパイル。全41実compile commandの/fp:strict・/GL-、新CPP/harnessの/WXと宣言identityをtlogで確認。既存5source IDを再利用せず、86原本・compiler binary/facts・flagsから新しい実験構成identity `f9444505eb353f9864773d49bf99d0bda04125d12424ebc8675295fa035f9f3b` を作った。**これは実命令監査済みartifactを意味しない。**
- 同構成の`--run`で9群成功。非自明な2dynamic×2mesh+planeの7pair/9child、全候補bitとのcommit対応、独立した正確dyadic運動の既知値、E128のstatic荷重消費、時計不正、実guard失敗、失敗→再試行→次tick、所有証拠保持と実環境拒否を検査した。guard再照会はcommit対応の検査であり独立物理参照とは区別する。
- 同構成の`--clock-fixtures`で有限18例を原bitとともに保存。Empty Worldと有効mesh1個の限定入力で7成功/11時計拒否。整数quotient/remainder・ties-to-evenで計算したRN和/表現差、Fractionの和/差/丸め誤差包含、失敗時負零保持、成功時だけの一tickを照合した。
- `.../run-20261105-clock-controls-001/`：実Native時計原本から2正control（原本・順序/label変更）と20改変拒否。時計の元値・差・区間・store会計・型を改変し、Python -Oでもbool counter改変を拒否した。これはcheckerの人工改変試験であり、Native fault injectionではない。
- `world-static-mesh-flight-advance-clock-review/run-001/`：保存recipeからfresh実行し、42149 RN選択（unique exact入力35801、重複を含む）と11自己試験を、正確なVoronoiセル・偶数bit条件で別照合。元の未保存試行と区別した。全encoding網羅や一般overflow変換の検証とはしない。

default/configured両recipeは新原本と、旧accepted lib/exe/core.obj/map/profileの全byte hashが実行前後で不変であることを確認した。既存build/nativeを再configure/relinkせず、SDK・既存ゲーム・他チャットの原本を変更していない。割当失敗/child非返却の自然故障注入は未実行。

原著概念図と計画は`docs/WORLD_STATIC_MESH_FLIGHT_ADVANCE_PLAN.md`。実ローカル表示の記録は`world-static-mesh-flight-advance-local-browser/`へ置く。概念図表示はNativeの数値実行証拠とは別である。

次は前段GNU監査の具体的失敗理由を修正して公開受入を確定し、その後、この試作のexpanded source/configurationを本体の厳密FP宣言・実artifact/command監査・CTest/CIへ登録する。現成功を一般接触/CFD/材料損傷や完成したシミュレータの証明に昇格しない。
