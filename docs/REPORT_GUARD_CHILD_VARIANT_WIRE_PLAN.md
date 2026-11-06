# World guardのChild variantを取得する次段

2026-11-06。PlaneCallsの次は、実宣言`world_static_mesh_flight_guard::Child`の別variant境界を取得する。recordの項目数とは分けて数える。宣言順はMeshCall=0、PlaneCalls=1、SphereCall=2である。

既存のInput variantと同じv1のvariant tag・32bit ordinal・実active child・endを出力する。`std::get_if`で実active alternativeを取得し、受入済みの各const getterを呼ぶ。実値なしは`reject_invalid_value()`へ渡す。private representation、架空のvariant ordinal、強制的な値なし状態を作らない。既存primitive／WriterとInputの取得契約は保持する。

人工fixtureでは全3alternativeを構成し、それぞれの元Call、全Resultまたは欠損、設定・試行位置・Grant・省略計数と未処理tailを保存する。独立仕様は対応する全child仕様から組み立て、wrapper ordinalと全childの型・値・順序を照合する。fixtureの具体的な組数・byte数・検査分割数は実測後に固定し、本文だけで成功としない。

停止／例外の全callback境界、親・子のsink再入、4丸めmodeを検査する。正当な公開emplaceで3元alternative×3変換先を試し、実値なしと旧値保持を分けて記録する。値なし時は送信前の拒否と既存sticky失敗の維持を、begin前・複数の入れ子位置・finish後で確かめる。拒否時に既に送信された外側prefixを取り消したと解釈しない。MSVCとGNUの到達状態は別に測定する。

全ordinal byteの変化、variantをoptionalへ変更、wrapper除去、child交換、全field・配列・本文の異なる有効文法変更を照合し、同値交換は分離する。旧全fixture／全実行出力／20profile／保護原本と17header gate、旧43＋新1の各44選択CTestを維持する。数値model libraryは結合しない。実oracle module graphを再帰的に列挙し、Mesh／PlaneCalls／Sphereのどの枝もprovenanceから落とさない。

受入後の予定範囲は89record型522項目＋別variant2型（既存Input、新Child）。Native、GNU、配信archive、HTTPと実UIは別受入。PairRecord全5項目、準備Resultの未対応依存、GuardResult全14項目、最上位World ReportとC API pump、今回取得のWASM・ゲーム接続は後続。この計画は実装・実行成功の証拠ではない。
