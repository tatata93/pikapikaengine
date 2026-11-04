"""Original local lesson and dependency record for the Native propagation guard."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/'docs/learn/index.html';text=p.read_text(encoding='utf-8');start=text.index('<article id="accelerated"');end=text.index('</article>',start)
assert 'sphere-triangle-mesh-free-flight-guard.svg' not in text
addition='<figure><img src="diagrams/sphere-triangle-mesh-free-flight-guard.svg" width="1060" height="740" alt="数学的な荷重の曲線と丸めた伝播位置の差を既存W1のBで囲み、上向きr+Bの全域非接触とHの完全候補を別に監査する。"><figcaption>原著の模式図。点の観測だけで全時刻を証明せず、時間進行と非接触guardを分けます。</figcaption></figure><p><a href="../SPHERE_TRIANGLE_MESH_FREE_FLIGHT_GUARD.md">丸め自由伝播を含むNative非接触guard</a>は、元bodyを各時刻で一度だけ進める並進の誤差を囲みます。実伝播も厳密FP・FMA無効の条件でビルドし、Hの候補の回転・角運動量までコピー上で検査します。元Worldと荷重は保持し、全Worldの衝突応答や新しいブラウザAPIは後続です。</p>'
p.write_text(text[:end]+addition+text[end:],encoding='utf-8',newline='\n')
paragraphs={
'docs/RESEARCH.md':'2026-11-04 丸め自由伝播のNative sphere×static mesh guardを追加中。既存W1 flightのoperation-graph ULPrecurrenceを同TU private bridgeで再使用し、実dynamics.cppもstrict/no-fast/contractionoffでビルドする。新しい数学solverを転載/導入せず、上向きr+Bの全域separatedとHの完全candidateを別監査。旧W1の全20入力/report/Worldbeforeafterと実SDKの20例（14success/5model拒否/1host拒否）を改修前に保存し、後で全bitsを検査する。SDKmaxContacts8192はNative既定16384と別profileとして明記する。新外部依存・有料serviceなし。',
'docs/legal/REFERENCES.md':'2026-11-04 自由伝播guard: 新外部文献の実読/引用/図・本文・code転載なし。既存原著W1の誤差式をbridgeで再使用し、Fractionの整数RN/ties-evenと二次全域の独立参照で監査する。有限duration観測を全duration証明へ昇格せず、FMA/再結合の別graphを認証対象にしない。',
'docs/legal/DEPENDENCIES.md':'2026-11-04 自由伝播guard: 新外部依存なし。共有W1 TUのprivate headerを正式SDK source provenanceへ登録し、固定Emscripten6.0.13・86exportsのまま再buildする。dynamics.cppにもcontractionoffを指定する。artifact byte変化・既存runtime/license・全回帰を実測し、未検証の不変を主張しない。本体license未選定。',
'docs/legal/ASSETS.md':'2026-11-04 docs/learn/diagrams/sphere-triangle-mesh-free-flight-guard.svg は原著1060×740のSVG。数学pathと表現可能durationの丸め位置、既存W1の誤差Bと上向きradius、Hの候補監査を模式的に示す。外部画像/font/model/図本文の流用なし。標本点は実データ/性能/実測誤差ではなく、表示QAは数値受入と別に記録する。'}
for name,line in paragraphs.items():
 p=root/name;old=p.read_text(encoding='utf-8');assert line not in old;p.write_text(old.rstrip()+'\n\n'+line+'\n',encoding='utf-8',newline='\n')
