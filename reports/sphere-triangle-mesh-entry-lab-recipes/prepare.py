from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=root/'docs/PLAN.md';s=p.read_text(encoding='utf-8');at=s.index('\n',s.index('再開位置:'))
note='\n\n進行中: 手動entryラボの実装を開始。25代表原入力/実API一回/全診断/strict JSON保存、全partitionとinitial/windowの別表示、編集・loader世代の消去を追加する。基準は公開受入66c6cf9、314保護原本/旧24HTML生成部を保存。UIの実行・公開受入は未確認。'
assert '進行中: 手動entryラボの実装を開始。' not in s;p.write_text(s[:at]+note+s[at:],encoding='utf-8',newline='\n')
for path,text in [
 ('docs/RESEARCH.md','2026-11-04 手動entryラボを実装中。既受入86-export owned APIと凍結65から25代表入力を選び、strict原入力/全診断保存とread-only投影を原著コードで接続する。JSで幾何solverや証拠を再計算しない。既存SDK/Native/game原本を保持し、新外部資料実読/依存/有料serviceなし。未検証を受入へ含めない。'),
 ('docs/legal/DEPENDENCIES.md','2026-11-04 手動entry UI: 新原著JS/HTML/SVGを追加中。既存自作strict-json/runtimeだけを使い、package/solver/font/model/有料serviceは追加しない。86exports/61source-header/719410B/58933B/runtime91/7通知の完全不変を検証後に確定する。本体license未選定。'),
 ('docs/legal/REFERENCES.md','2026-11-04 手動entry UI: 外部文献の実読・図/本文/code転載なし。原著旧trajectoryラボの所有/表示方式を参考にするが自動初期化moduleを再利用importせず、initial/window/全partitionを別契約として実装する。原著説明投影は数学包含やTOI/World応答の証明ではない。')]:
 p=root/path;p.write_text(p.read_text(encoding='utf-8')+'\n'+text+'\n',encoding='utf-8',newline='\n')
p=root/'docs/learn/index.html';s=p.read_text(encoding='utf-8');needle='entry窓の所有JavaScript API</a>です。';assert needle in s;s=s.replace(needle,'entry窓の所有JavaScript API</a>と、<a href="../../tools/sphere-triangle-mesh-entry-lab.html">侵入開始窓の手動ラボ（実装中）</a>です。',1);p.write_text(s,encoding='utf-8',newline='\n')
print('Next manual entry UI marked in progress; no acceptance claimed.')
