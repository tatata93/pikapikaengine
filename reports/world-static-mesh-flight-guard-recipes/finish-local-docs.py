"""Record completed local acceptance; never promote pending public checks."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'docs/PLAN.md';raw=p.read_bytes();s=raw.decode('utf8')
for before,after in [
 ('再開位置: Native accelerated_sphere_box_coverage','直前の公開受入: Native accelerated_sphere_box_coverage'),
 ('次は正確なmanifestでcommit/pushし、GNU13実命令','次はGNU13実命令')]:
 assert s.count(before)==1
 s=s.replace(before,after)
p.write_bytes(s.encode('utf8'))
paragraph='2026-11-05 World全組flight guardをNativeローカル受入。58群51入力・184全child再照会と独立数学/所有/会計、12自己/138改変拒否/order独立、actual MSVC19.51x64の3leaf命令とcaller call先・strict command、46CTest/684Node skip0、旧Native3byte/SDK20bitsと全7交換、更新SDKの実ゲーム35正常照会を確認。正式local-verificationとsummary003は377326B/SHAa402bbe8998c9ecfcd39a420ab776920d906d4e795b0c29a094a0a96beee765cで同byte。caller全体をsymbolic証明したとはしない。collectorの旧HTML混在改行再構成と旧-O拒否object schemaを訂正した2失敗、CTest空引数の2失敗、初期専用期待訂正・UI収集失敗もraw保持。GNU/ASan-UBSan/公開CI/Pages/配信は未確認。新外部実装/素材/有料serviceはなくlicense未選定、一般応答/流体損傷/専門モデル/IK/撮像は後続。'
p=ROOT/'docs/RESEARCH.md';raw=p.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';assert paragraph.encode() not in raw;p.write_bytes(raw+nl+nl+paragraph.encode()+nl)
paragraph='最終集計はsummary001で、旧2HTMLの混在改行を一律LF/CRLFだけで再構成しようとして停止した。BASE041のbodyをCRLFへ変え、生成inline import-mapの行末だけLFへ戻すと、保存済raw hashへ完全一致することを確認した。本文の例外を許さず、その有限な再構成だけをcollectorへ追加した。summary002では旧raw SDKのoptimizedPythonRejectedがboolではなくPASS/非零exitCodeを持つobjectであるため停止し、実schemaへの検査だけを訂正した。旧receipt・入力・数学・製品sourceを変えず、fresh summary003の全718証拠集計が成功した。001/002のstdout/stderr/failureも同梱する。'
p=ROOT/'reports/2026-11-05-world-static-mesh-flight-guard.md';raw=p.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';assert paragraph.encode() not in raw;p.write_bytes(raw+nl+nl+paragraph.encode()+nl)
print('Local documentation finalized; public checks remain pending.')
