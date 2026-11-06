# pair coverageのCellとWorkを取得する次段

2026-11-06。Snapshot取得後の未実装計画。既存63record型372項目＋variant1型に、2record型7項目を追加する。

| 型 | 宣言順の保存項目 | 区別する値 |
| --- | --- | --- |
| Cell | time_bounds, depth, parent_audit | global秒の両端、U32深さ、U64所属indexのなし・0・全64bit |
| Work | value_calls_attempted, value_calls_returned, plane_norm_calls_upper, plane_norm_loop_iterations_upper | wrapperの実attempted/returnedと、private normの計数上限 |

time_boundsの両端は原順のbinary64 bitで保存し、depthやhorizonから復元しない。根のparentなしとindex0を区別する。人工の不正順・非有限値・負零も修復しない。

Workは4項目ともU64として保存する。attemptedとreturnedは例外で異なり得る。private norm helperは計装されていないため、上限を実測呼出数や実ループ消費量と呼ばない。getterで64倍計算を行わず、保存済みの各値を独立に取得する。

独立typed仕様と全byte比較、全scalar/key byte改変、端点交換・optionalのなし/null/0・4件数交換、callback停止/例外/再入、4丸めmodeを検査する。新harnessは2data TU＋1harness TU、Interval TU/model libraryなし。17header gate、旧全fixture・実行出力・20profile・保護原本を維持する。Nativeと実GNUを分けて受け入れる。

次はAudit/PartitionLeaf、全Result、その後plane box/sphere boxの依存を満たす。全Report/C API pumpまでを本段の完了とは呼ばない。
