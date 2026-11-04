# 球と静的三角形mesh: 次のNative有限受入案

2026-11-04 JST。**Native実装・ローカル受入済み、公開CI/Pages確認待ち**。[実装契約](SPHERE_TRIANGLE_MESH.md)と[検証記録](../reports/2026-11-04-sphere-triangle-mesh.md)に結果を保存した。以下は受入時の設計であり、主SDK/World/CCD/衝撃応答やゲームをこの段階へ含めない。

最初は最大64枚の静的な両面三角形を所有copyする小さい集合を対象にする。各面は正のsafe整数のstable surface IDと、元順の3頂点を持ち、ID重複・非有限・入力域外・空集合・容量超過を全件検査する。shared vertexの同一性や閉固体内部を推測しない。原本のsigned zeroと順序を保持し、入力/Worldを変更しない。ファイルcodecやC ABI resource handleはNative段階の受入後に別途設計する。

各面へ既存の実C++ queryをそのまま呼び、全rowのstatus/reason・候補prefix・Geometry・作業件数を保持する。初段は全列挙とし、AABBによる省略は入れない。1枚でも未解決/退化/モデル失敗があれば、集合全体のnearestを成功として公開しない。途中までの診断と、全件完了の意味を区別する。最大64×7候補・64×512平方根更新の上限と実使用数を明示し、性能達成の主張にしない。

全rowがcompletedの場合だけ、距離や距離²の最小値を区間で囲む。各面の真値d_iにL_i≤d_i≤U_iがあるとき、min(L_i)≤min(d_i)≤min(U_i)なので、追加の近似sqrtは不要。nearestの可能性がある面は、その距離²下限が全上限の最小値以下のものをすべて残す。厳密に大きい下限の面だけを除き、等号や境界の未確定をstable ID順の1面へ潰さない。

返すのは最小距離の区間と可能なsurface ID集合、および各面固有のGeometryである。異なる面のbarycentric/local座標を一つへ混ぜない。複数の最近接点や法線を、平均や区間中点で一つの接触点/単位法線へ昇格しない。各面の返却値があっても、contact manifoldや摩擦支持拘束を生成したとはしない。

受入は、孤立1面と既存核のbit一致、2面の明確な優劣、共有辺/頂点での同率、左右の離れた面での多重最近接、裏側、入力面順の置換、stable IDの対応、巨大共通offset、幅/条件/予算失敗・1面失敗の伝播、空/重複ID/65枚拒否、所有copy・再試行を含む。独立有理数参照は各三角形の真の最近接点から有限集合の最小値と必要な候補を求め、故意のwinner削除・符号零/区間/ID改ざんを拒否する。Native通常/strict/sanitizerを別記録し、その後に有界SDK・ブラウザ・ゲームへの接続順を判断する。

外部solver/geometry library・package/素材を追加せず、既存の原著Interval/sqrtと数学的包含を使う。これからの実装と検証で本案の妥当性を確認する。高速broadphase、隣接面処理、閉固体内部、World/CCD/manifold、一般接触応答・流体/損傷・専門シミュレータは未完のまま維持する。
