"""Select the standalone owned coverage proof for the still-unimplemented World guard."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root/'docs/WORLD_STATIC_MESH_FLIGHT_PLAN.md'
text = path.read_text(encoding='utf-8')
changes = [
 ('`accelerated.hpp`は点のnominal加速度による四次/二次式の全時間除外を返す。`Kind::none`だけを全区間strict非接触証拠として使える。entry/unresolved、初期境界、点witnessは成功でない。',
  '`accelerated.hpp`の旧searchは点nominal加速度の四次/二次式を調べるが、全positive cellを返さない。後続World guardの正証拠には新しい[全closed-cell coverage](ACCELERATED_PAIR_COVERAGE.md)を単独採用する。全partitionのstrict positiveだけを全時間証拠とし、旧none summaryからcellを捏造しない。entry/unresolved、初期境界、点witnessは成功でない。'),
 ('両球の膨張和によるstrict `Kind::none` はnominal inflated pathsの全real秒非接触を証明し、',
  '両球の膨張和による新coverageの全leaf strict positiveはnominal inflated pathsの全real秒非接触を証明し、'),
 ('既存acceleratedのinflated sphere-plane全除外に加え、', 'public valueを使う新coverageのinflated sphere-plane全除外に加え、'),
 ('二つ目は上向きrGuardで呼ぶaccelerated noneが供給する。', '二つ目は上向きrGuardで呼ぶ新sphere-plane coverageが供給する。'),
 ('この案ではaccelerated searchのnone診断と、別coverageのvalue呼出しを両方行う。**二重評価の実費**を分けてWorkに計上し、どちらか失敗なら認証しない。positive coverageには新scene-globalのstored cell/audit上限1024を置き、heldの1024auditとは別枠にする。',
  '2026-11-04の依存設計更新では、新Native coverageを**単独の正証拠**として採用し、旧accelerated searchを内部で二重実行しない。新helperは各public value呼出しのattempt/returnと全audit/partition/frontier/currentを所有する。旧searchとの比較を後に行う場合は、別caller診断・別Workへ明示し、その費用を省略しない。positive coverageには新scene-globalのstored cell/audit上限1024を置き、heldの1024auditとは別枠にする。'),
 ('旧accelerated内部frontierを回収したと主張しない。性能整理で一方を省く場合は後続の別受入である。',
  '旧accelerated内部frontierを回収したと主張しない。新helper単独の受入を、World raw planeの追加predicate・B膨張・全pair予算・全候補の完成へ昇格させない。'),
 ('ローカル既存guard/accelerated設定、', 'ローカル既存mesh guard/新coverage設定、'),
 ('acceleratedはmax_evaluationsの返却countを加算し、必要なら残global内のexplicit per-call grantを診断へ保存する。これは呼出profileの明示grantであり、時間/品質条件を緩めない。呼ぶ前にfull grantを予約し、throwでResultを受け取れなければknown returned=0/upper=grant/workExact=falseとして全体停止する。これは実使用0ではない。既存searchはcount増加後の式評価/allocでthrowし得てpartial Resultを返さない。新value coverageのcallについてもattemptと正常返却を分け、未返却cellの証拠を作らない。',
  '新coverageは255evaluation/128leaf/depth32のhard範囲内でglobal残量にexplicit grantを与える。全retained audit/partition/frontier用capacityを呼出し前に予約・会計し、helperの正確なattempt/returnをglobalへ加算する。grantは時間/品質条件を緩めない。value例外ではattempt有り/value無し・current/全tailをそのまま返し、全体をnot_certifiedにする。旧searchを別比較に使う場合だけ、返却不能時のfull grant upper/workExact=falseが別に必要であり、known returned0を実使用0にしない。'),
 ('plane norm helperの既存private反復はaccelerated Resultに公開countが無いため、', 'plane norm helperの既存private反復はpublic valueから実countを得られないため、'),
 ('### acceleratedの返却しない情報と一時storage', '### 既存searchの監査履歴（新coverageの正証拠へ流用しない）')]
for before, after in changes:
    assert text.count(before)==1, before
    text = text.replace(before,after,1)
path.write_text(text,encoding='utf-8',newline='\n')
print('Selected owned value-only coverage for the future World guard; World integration remains unimplemented.')
