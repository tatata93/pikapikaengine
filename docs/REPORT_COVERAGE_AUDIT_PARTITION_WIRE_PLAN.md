# pair coverageのAuditとPartitionLeafを保存する次段

2026-11-06。Cell/Work後の未実装計画。既存65record型379項目と別variant1型に、Audit6項目とPartitionLeaf4項目を追加する。

Auditはcell、call_attempted、value、outcome、blocked_reason、split_timeを宣言順に取得する。valueは未返却や例外時のなしと、実際に返ったIntervalの両端を区別する。split_timeはなしと負零・非有限値を含む元の秒を分ける。Outcome/Reasonは実enum tagを使い、未知ordinalも黙って既知値へ修復しない。

PartitionLeafはcell、state、audit_index、blocked_reasonを保存する。audit_indexのなし・0・全64bit、所属先とparentを区別する。全root/optional maskと名前付きchild順・全byteを独立仕様で比較する。人工の不整合値を実モデルが生成したとは呼ばない。

Interval人工構築に必要な既存interval.cppは試験専用TUへ明示し、getterには演算/query/model libraryを追加しない。optionalのなし/null/0、enum→U32、実stop/exception/reentry、4丸めmode、17header gateと旧全fixture/20profile/保護原本を確認する。その後、全Result12項目と全監査行・区画・frontier/currentへ進む。

次段の人工source設計（まだ取得試験を実行した結果ではない）:

| source | 件数案 | 独立仕様で保持する組合せ |
| --- | ---: | --- |
| Audit | 20 | 最初の16件でvalue有無・split有無・cell親有無・call_attemptedの全16組合せ |
| PartitionLeaf | 12 | parent/audit_index有無の全4組合せ、全既知state4種と未知2値 |
| Outcome | Auditで巡回 | 既知0..3と0x80000000、0xffffffff |
| Reason | Auditで巡回 | 既知0..14と未知2値。欠落理由をnoneへ修復しない |

Cellの端点とsplit_timeは既存16 binary64 bitパターンから独立に割り当て、splitの負零・非有限値を含める。parentとaudit_indexの値あり側は0、UINT64_MAX、2^53+1、2^63をすべて含むように巡回を設計する。有無maskだけでは値の境界が揃わないため、最終typed oracleで各集合の被覆も数える。

optional Intervalは正当なpublic constructorだけで作る。point(0)、whole、有限の正負区間、subnormal端点を含め、NaN/private byte破壊や逆転区間を作らない。既存constructorは下端の零を-0、上端を+0へ正規化するため、独立期待値も構築後の実保存値を比較する。元Cell端点・split_timeのraw負零保持と、Intervalの既存契約を混同しない。

call_attempted=falseでもvalueあり等の人工的不整合をあえて含め、getterが補正しないことを調べる。この保存検査で、その組合せを実coverageモデルが生成したと報告しない。全scalar/key byte・全optional wrapper・enum tag・端点/所属位置の交換を独立比較し、全Result/配列の原順保持は次段として残す。

割当の具体案: Auditの最初の16件はiのbit0=value、bit1=split、bit2=parent、bit3=call_attemptedとする。値ありparentは境界count配列のi%4番を使う。splitは既存16bit配列の(i+3)%16番にすれば、値あり側にも負零・無限・NaNを含められる。区画12件のparent有無はbit1、audit_index有無はbit0、値ありparentはcount[(i/4+i)%4]、audit_indexはcount[(i/2)%4]（除算は整数）とする。いずれも値あり側の集合が4種類すべてを含むことを独立checkerで再計数する。これは実装の指示案で、Native/GNU受入前の試験値設計である。
