"""Integrate original coverage teaching and dependency records without game edits."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
path = root/'docs/learn/index.html'
text = path.read_text(encoding='utf-8')
article = re.search(r'<article id="accelerated".*?</article>', text, re.S)
assert article and 'accelerated-pair-coverage.svg' not in text
addition = '''<h3>全時間の証拠を、未知の末尾まで残す</h3><p>球同士と静的平面の非接触は、端点だけでは決まりません。原global秒の閉区間を幅優先で分け、全leafで式の下限が正と証明できた場合だけ、全時間の非接触を認証します。接線や狭い未知区間、予算切れは成功へ変えません。</p><figure><img src="diagrams/accelerated-pair-coverage.svg" width="1120" height="780" alt="全closed時間を幅優先で分割し、全leafのstrict positiveだけを認証する。blocked・current・全未照会tail、実返却bitsの由来と独立数学、norm費用上界を別に保持する。"><figcaption>原著の概念図。セル・色・配置は説明用で、実測軌道や性能ではありません。</figcaption></figure><p><a href="../ACCELERATED_PAIR_COVERAGE.md">加速球対・平面の全時間coverageのNative契約 →</a>では、全audit・親と分割点・全partition・未照会tailを所有します。実public valueの返却bitsをそのまま残す検査と、独立Fractionによる全時間の数学的包含を分けます。図の表示を数値証拠の代用にせず、検証した範囲はガイドに記録します。Worldの丸めtube・半径膨張・全pair候補・接触応答と、ブラウザへの数値接続は後続です。</p>'''
text = text[:article.end()-len('</article>')]+addition+text[article.end()-len('</article>'):]
before = '現在は92-export SDKと所有APIの接続をローカル受入しています。公開CI/Pagesは別途確認します。Worldの衝突応答や手動編集UIは後続です。'
after = '現在は92-export SDKと所有APIを機能8035f93で公開受入し、機能788ac1bの手動UIも公開確認済みです。Worldの衝突応答は後続です。'
assert text.count(before)==1
path.write_text(text.replace(before,after,1),encoding='utf-8',newline='\n')
records = {
 'docs/legal/ASSETS.md':'2026-11-04 docs/learn/diagrams/accelerated-pair-coverage.svg: この開発で記述した原著1120×780 SVG。closed root/shared midpoint/BFS、全partitionの認証・blocked/current/未照会tail、由来bitsと独立数学、private norm費用上界を説明する概念図。実測・性能・ゲームassetではなく、外部画像/font/商用作品素材を使用しない。本体license未選定。',
 'docs/legal/DEPENDENCIES.md':'2026-11-04 Native accelerated pair coverage: 新外部package/solver/素材/有料service無し。既存独自Interval/public valueを再使用し、owned全closed-cell診断を新C++で追加する。独立Pythonはstdlib Fractionのみ、SDKは新export/TUを追加せず92exports/32TU/runtime91/7通知を保持。数学検査とactual返却bitsの由来、sizeof/capacityとheap実使用を区別する。本体license未選定。',
 'docs/legal/REFERENCES.md':'2026-11-04 Native accelerated pair coverage: 新外部資料の実読・引用・図/codeの移植はない。既存原著accelerated.cpp/interval.cppの全operation graphを読み、公開valueのInterval保存と独立有理多項式/平方比較を設計する。原著BFS/全partitionの組合せ監査と数学的全時間包含、public value再照会の全endpoint bitsを独立した検査として扱う。有限参照予算の未解決を成功へ昇格しない。',
 'docs/RESEARCH.md':'2026-11-04 加速球対・平面coverageを追加中。既存searchはpositive cellを返さないため、新核はpublic valueだけを呼び、原入力・全closed partition/audit/current/frontierを所有する。単独strict MSVCでは69群/65有限入力/1913実public value全endpoint bitsが成功し、独立Fraction・統合・公開は別途確認する。全leaf strict positiveだけを認証し、private norm費用64upperを実反復としない。原著ガイド/SVGを追加、新外部資料/依存/素材/有料service無し。'
}
for name, addition in records.items():
    with (root/name).open('a',encoding='utf-8',newline='\n') as stream:
        stream.write('\n\n'+addition+'\n')
print('Original coverage teaching and four research/legal records integrated; no game or SDK change.')
