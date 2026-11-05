# Worldと時計を同じ寿命で所有するNative session

2026-11-05。次の設計案。**未実装・未実行。** controlled schedulerの正式MSVC受入は
`WORLD_STATIC_MESH_FLIGHT_CONTROLLED_SCHEDULER.md`、実GNUの受入は別gateである。
旧計算核・旧SDKを変更せず、新しいNative owner wrapperとして先に検証する。

## 解く不足と所有

現在のpumpはcallerのWorld／Progressと静的sourceを受ける。一つの論理Worldへ排他的に
呼ぶ条件はcallerの責任で、別Worldと同じtick番号のpacketを取り違える可能性がある。
ownerはWorld、全StaticMeshSource、GuardSettings、Progress、immutable clock設定と
実controlled Schedulerを同じ寿命に保持する。永続packet queueやcallbackは最初に加えない。

最初のNative入口は実Worldからの所有copyを使う。bodyをadd_bodyへ渡し直してraw値を
正規化するDTO変換を挟まない。原順、全field、負零とstatic sourceを保持し、callerの
後続編集から独立させる。所有copyができたことと、その物理入力がadvanceできることは別。
入力のhard countを越える所有を拒否し、数値／モデルの不正は実pumpの診断として扱う。
原本・非finiteの扱いを将来の有限JSON wire codecへ暗黙に転用しない。

公開操作からmutable World／Progress／Schedulerの参照を返さない。読み出しは所有値copyとし、
allocation失敗を状態更新へすり替えない。authoring用の編集は最初はresetによる全体交換だけ。
一般接触、支持・摩擦や航空／流体／損傷モデルを追加した意味ではない。

## 世代と拒否順

packet列の外側にsession tokenを持つrequestを新設し、既存TickLoadPacketは変えない。
tokenはregistry slotとgenerationを明示する。小さな固定上限で複数ownerを管理し、
slotはdestroy後に再利用できてもgenerationは再利用しない。上限到達時はwrapせずslotを
退役させる。数値幅と上限はNative実装・wire計画で別々に固定する。

foreign token、destroy済みtoken、reset前token、busy/reentrantを実child呼出しとelapsed受理の
前に拒否する。違うsessionでtick番号が一致してもtokenを代用しない。tokenは同じregistry内の
取り違え検出用で、別registry／別processの認証・永続ID・security capabilityとは呼ばない。
最初のAPIはregistryへの同期・排他的アクセスを前提にし、thread atomicityを主張しない。

resetは新World／source／設定／Progress／clockを私有stagingへ所有copyしてから全体交換する。
世代を進め、以前のpacketと時計creditを無効にする。copyや構築が失敗したら現session／世代／
World／creditは保持する。成功後に失敗し得るgetter／log確保を足さず、commitのnothrowな操作を
実コードの型検査と直接試験で限定する。destroyはowned objectを終え、同じtokenへアクセスしない。

## 実pumpと返却診断

有効sessionでは既存Scheduler::pumpを一回だけ呼び、その実Reportを所有して返す。
ownerの外側エラーと、モデル拒否・入力不足・成功prefixを混ぜない。中の実commitが進んだ後に
outer catchで「何も進まなかった」と書き換えない。allocationを伴う外側準備は呼出し前へ置き、
返却wrapperとchild Reportのmove／destructはnothrow条件を実確認する。

snapshot copyは将来操作によって変わらず、ownerからborrowしたpointerを寿命の証拠にしない。
同一sessionのpump中に維持する実body addressと、reset/destroyを越えたpointerの無効化は別。
ownerが追加するcopy／境界／token検査の費用と、既存guardの論理payload予約を区別する。
registry／allocator overhead／stack／RSS／deadlineまで旧予約から保証しない。

## 最初の有限受入

| 場面 | 実証拠 |
|---|---|
| caller寿命 | create後に元World／source／設定を編集し、owner原本と以前の所有snapshotが不変。 |
| 同じtickの2session | 異なるWorld、同じtick番号へforeign tokenを渡し、child0／時間受理0／全状態保持。 |
| 成功prefix | 2packetの第1成功・第2拒否、retry0と入力不足を実controlled Report／実境界で保存。 |
| reset | 新原本／clock／世代を全体交換し、古いtokenを拒否。失敗時は旧原本とcreditを保持。 |
| destroyとslot再利用 | 旧tokenを拒否し新tokenだけ有効。上限時の退役を実小さな試験設定で観測しwrapしない。 |
| default/env拒否 | 実Debug/default bindingと不正FP環境でchild0。owner生成と数値進行の可否を分ける。 |

有限full producerと独立metadata／数学参照は、実返却childと実owner境界を使う。
架空のWorldAfter／lookup行やguardの再照会を追加しない。改変コピー負例は実allocation／
post-child fault注入と区別する。最初の実装ではresetの自然allocation fault未試験なら明記する。

GNU／全依存sanitizerとNative owner受入の後、bounded getters、generation wire幅、Host拒否と
モデル拒否、destroy/reset後のReport寿命、実WASM binding／linear-memory成長を別ABI計画にする。
既存92 exportsや現在のブラウザREADYを新World sessionの成功へ転用しない。
外部資料・実装・ライブラリ・素材の追加はない。
