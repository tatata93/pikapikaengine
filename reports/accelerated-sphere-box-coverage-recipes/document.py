"""Record completed local acceptance; never promote it to public CI acceptance."""
from hashlib import sha256
from pathlib import Path
import json

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'accelerated-sphere-box-coverage'
SOURCE = ROOT/f'reports/{PREFIX}-checks/run-20261104-summary-002/acceptance.json'
TARGET = ROOT/f'reports/{PREFIX}-local-verification.json'
RECORD = ROOT/f'reports/2026-11-04-{PREFIX}.md'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def stamp(path):
    raw = path.read_bytes()
    return {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}


def main():
    need(SOURCE.is_file(), 'Completed aggregate acceptance.json is required; do not execute before root acceptance.')
    raw = SOURCE.read_bytes()
    report = json.loads(raw)
    need(report['schema'] == 1 and report['status'] == 'PASS', 'Only completed local PASS may be documented.')
    need(not TARGET.exists() and not RECORD.exists(), 'Preserve existing receipt/report; do not overwrite.')
    independent = report['independentReference']
    root = report['rootWork']
    storage = report['storageObservation']
    need(independent['status'] == 'PASS', 'Independent mathematical acceptance required.')
    need(report['finiteFixtures'] == independent['fixtures'] == independent['certified'] + independent['notCertified'] + independent['invalidInputs'], 'Complete finite classifications required.')
    need(report['nativePublicValueFullEvaluationReplays'] == independent['returnedEvaluations'] == root['returnedResults'], 'Provenance and returned-root counts must agree.')
    need(report['nativeEndpointBitComparisons'] == 30 * report['nativePublicValueFullEvaluationReplays'], 'All fifteen interval fields, including the copied root.value/distance, are required.')
    need(report['nativeRootDiagnosticComparisons'] == 2 * root['returnedResults'], 'Both returned root diagnostics required.')
    need(root['returnedRefinements'] == independent['sqrtRefinementsReturned'] == root['sumUpper'], 'Observed root accounting required.')
    need(root['allNaturalWorkExact'] is True and root['privateRootAttemptCount'] is None, 'Do not invent private root attempts.')
    need(report['skipped'] == 0 and report['ctest'] > 0 and report['node'] > 0, 'Completed regressions with no skipped Node tests required.')
    components = storage['sizeofCapacityComponents']
    inline = components['inlineResult']
    vector_payload = sum(value for key, value in components.items() if key != 'inlineResult')
    need(vector_payload + inline == storage['sizeofCapacityBytes'], 'Count the inline Result exactly once.')
    fixture_path = f'reports/{PREFIX}-checks/run-20261104-native-001/native-fixtures.json'
    fixture = report['evidence'][fixture_path]
    need(stamp(ROOT/fixture_path) == fixture, 'Canonical fixture bytes must match the aggregate.')

    # These seven code sources and original display materials are read-only here.
    frozen = dict(report['newSources'])
    frozen.update(report['localBrowser']['observations']['sourceHashes'])
    for name, expected in frozen.items():
        need(stamp(ROOT/name) == {key: expected[key] for key in ['bytes', 'sha256']}, 'Frozen source changed: ' + name)

    paragraph = f"""再開位置: Native accelerated_sphere_box_coverage をローカル受入した。両方の宣言B・元radius・明示marginから全closed-cellのdelta/dot/sqrt/左閾値を囲み、全leaf gap.lower()>0と全返却/root会計整合だけを認証する。{report['ctest']}CTest/専用{report['nativeGroups']}群/{report['finiteFixtures']}有限入力、{report['nativePublicValueFullEvaluationReplays']}全Evaluationの{report['nativeEndpointBitComparisons']}端点bit（{report['nativeNegativeZeroEndpoints']}負零）と{report['nativeRootDiagnosticComparisons']}root診断再照会、独立Fractionの6座標quadratic±Bとrecorded-boxからの整数RN/root平方包含、{report['selfTestGroups']}自己/{report['negativeControls']}改変拒否、Node{report['node']} skip0・構文/Web {report['webBuild']}・{report['modules']}module/26entryが成功。{report['protectedFilesUnchanged']}既存raw/{report['generatedEntriesUnchanged']}HTMLと92export SDK/32TU/runtime91/7通知は保持。公開GNU/Linux CI・ASan/UBSan・Pagesは未確認で次に受入する。actual B導出、外部std::sqrtのsource_enforced binding、全pair/candidateを結ぶWorld guardは未実装の別featureで、今回公開へ含めない。[契約](ACCELERATED_SPHERE_BOX_COVERAGE.md)・[受入記録](../reports/2026-11-04-accelerated-sphere-box-coverage.md)。一般接触応答・流体損傷・専門モデル・IK制御・高精度撮像は未完。"""
    plan_path = ROOT/'docs/PLAN.md'
    plan = plan_path.read_text(encoding='utf-8')
    start = plan.index('再開位置:')
    end = plan.index('\n', start)
    plan = plan[:start] + paragraph + plan[end:]

    sphere_path = ROOT/'docs/ACCELERATED_SPHERE_BOX_COVERAGE_PLAN.md'
    sphere = sphere_path.read_text(encoding='utf-8')
    old = '2026-11-04。**次段のNative契約。新cppと専用試験は著述済みだが、Native実行、独立数学参照、実測容量、公開受入は未実施**。[新header](../core/include/pikapika/accelerated_sphere_box_coverage.hpp)と本書は現在のplane-box公開受入から除外する。既存World/核/SDKの変更や、World数値guardの実装は開始しない。'
    need(sphere.count(old) == 1, 'Expected original proposal status must be preserved before exact replacement.')
    sphere = sphere.replace(old, '2026-11-04。**Native単体核をローカル受入済み。公開GNU/Linux CI・ASan/UBSan・Pagesの受入は未確認**。[header](../core/include/pikapika/accelerated_sphere_box_coverage.hpp)・[ローカル原本](../reports/accelerated-sphere-box-coverage-local-verification.json)・[受入記録](../reports/2026-11-04-accelerated-sphere-box-coverage.md)を分けて保持する。現在のplane-box公開receiptは変更しない。将来のWorld guard契約・外部sqrt/compiler bindingは未実装で、今回のsphere-box公開対象へ含めない。')
    sphere = sphere.replace('## 未実施の受入', '## 独立受入の契約と残る公開確認')
    old_end = '予定例は両B/片B/両0、margin差、位置差/dot/sqrt/閾値の上記丸め差、巨大共通offset/取消、接線/途中通過、実subdivision成功、tiny/−0、全255audit/128leaf/127tail＋current、ref1/128/256、設定/原本所有/環境復帰。全counter/root/result/link/leafを改変する負例、strict/GNU/sanitizer、全fixture通常/計装一致も必要。故意nonreturn自己例を自然なC++ faultとは呼ばない。現時点の件数、成功、性能、sizeof/capacity、heap上限はいずれも未測定である。'
    need(sphere.count(old_end) == 1, 'Expected acceptance proposal paragraph required.')
    sphere = sphere.replace(old_end, f"""両B/片B/両0、5種類のpredicate反例、巨大共通offset/取消、接線/途中通過、B>0の実subdivision成功、tiny/−0、全255audit/128leaf/127tail＋current、ref1/128/256、設定/所有/環境復帰をローカルで確認した。実{report['finiteFixtures']}入力はcertified{independent['certified']} / not_certified{independent['notCertified']} / invalid{independent['invalidInputs']}。{report['nativeGroups']}専用群と{report['ctest']}CTest、全{root['returnedResults']}返却rootの平方包含・{root['returnedRefinements']}観測精錬、limitedでも正の{root['limitedPositiveEvaluations']}例、{report['selfTestGroups']}自己/{report['negativeControls']}拒否が成功した。座標の独立参照は真のquadratic extrema±Bであり、座標生成I-ASTの全RN選択を独立列挙したとはしない。recorded boxesからのdelta以降を整数RNで監査し、全15I/root診断のactual返却由来は別のNative再照会gateとする。人工nonreturn/広い有効rootの正例と改変拒否は自然なC++故障注入ではない。sizeof×capacityはvector部分{vector_payload}B＋inline Result{inline}B＝{storage['sizeofCapacityBytes']}Bの観測で、heap/stack/allocator上限ではない。公開GNU warning/sanitizerと通常/計装全fixture一致・配信確認は未実施で、成功扱いにしない。""")

    record = f"""# 2026-11-04 二つの宣言位置boxによる球接触式coverage

Native専用の単体核をローカル受入した。公開GNU/Linux CI・ASan/UBSan・Pagesは未確認で、後続の受入を別に記録する。旧World/SDK/gameの数値経路は変更していない。

## 条件と返却内容

必須5引数 `Input(firstSphere,secondSphere,firstB,secondB,contactMargin)` を使う。元の両radiusへBを重複加算せず、各宣言位置boxを一度ずつ膨らませる。閉秒区間ごとに両方の全3座標box、delta、生の左結合二乗距離、下端だけ0へ切り詰めた非負区間、全SqrtResult、distance、左結合の元radius/margin閾値、gapを所有する。全15区間にはroot.valueと同bitsのdistanceコピーをそれぞれ数える。

全leafでgap.lower()>0、全時間被覆、返却とroot会計の整合が揃う場合だけcertifiedとする。低精錬でlimitedでも包含と正のgapが有効なら認証できる。全query上界130560は反復予約枠で、実heapやstack使用量ではない。valueが返らなければwrapperの正確なattempt/returnを残し、private rootの実行を推測せず2×refのunknown上界・exact=false・currentと全tailを保持する。

この核は宣言されたBに条件付けられる。actual bodyのB導出、外部std::sqrt/compiler binding、全World pair/candidate、応答・TOI・clock/load更新を認証しない。将来のsource_enforced Native x64 World guard契約は未実装の別段であり、このfeatureと公開receiptへ含めない。

## 実測したローカル受入

| 検査 | 実結果 |
|---|---|
| strict MSVC standalone / CMake | {report['nativeGroups']}専用群・{report['finiteFixtures']}有限入力、{report['ctest']}CTest成功 |
| 分類 | certified {independent['certified']} / not_certified {independent['notCertified']} / invalid {independent['invalidInputs']} |
| actual public value由来 | {report['nativePublicValueFullEvaluationReplays']}全Evaluation、{report['nativeEndpointBitComparisons']}端点bits（{report['nativeNegativeZeroEndpoints']}負零）と{report['nativeRootDiagnosticComparisons']}root診断が再照会一致 |
| 独立包含 | {independent['returnedIntervals']}区間、{independent['coordinateRangeProofs']}座標全域極値±B、{independent['rootSquareProofs']}root平方包含、{independent['astNodePairs']} downstream整数RN node-pairs |
| root観測 | 返却{root['returnedResults']} / 精錬{root['returnedRefinements']} / limited {root['limitedResults']}（正の認証{root['limitedPositiveEvaluations']}） / 全自然Work exact |
| 完全metadata | {independent['partitionLeaves']} partition / {independent['frontierCells']} frontier / {independent['currentCells']} current、最大{independent['maximumAudits']} audit / {independent['maximumPartition']} leaf / {independent['maximumFrontier']} tail |
| 参照controls | {report['selfTestGroups']}自己群・{report['negativeControls']}改変拒否、Python -O拒否、label/order非依存 |
| 既存Web | Node{report['node']}成功・skip{report['skipped']}、構文、build {report['webBuild']} / {report['modules']} module / 26entry |
| 原本保持 | {report['protectedFilesUnchanged']}既存raw、{report['generatedEntriesUnchanged']}生成HTML、SDK {report['exports']} exports / {report['sourceHeaders']} source-header / {report['compiledTranslationUnits']} TU / runtime{report['runtimeMembers']} / {report['licenseNoticesUnchanged']}通知 |

Canonical fixture {fixture['bytes']}B SHA256 `{fixture['sha256']}` は初回standaloneとbyte一致。全入力fingerprintは `{independent['inputFingerprint']}`。margin、位置差、dot、sqrt、閾値加算順の5反例、双方B、非自明な安全放物線の分割、全容量/未知tail、subnormal、環境拒否と復帰を実行した。

独立Fractionの6座標検査は**真のquadratic全域極値±各B**であり、座標生成I-AST全nodeのRN選択を列挙したものではない。recorded boxesからdelta・square・左和・閾値・gapを整数binary64 RNで検査し、sqrtは非負端点の平方不等式とRNの単調性・端点固定性で監査する。通常libm sqrtを真値として使わない。全15Iとroot診断のNative再照会は由来の別gateであり、この数学検査の代わりではない。

MSVC x64のsizeof×返却capacity観測はvector {vector_payload}B＋inline Result {inline}B＝**{storage['sizeofCapacityBytes']}B**。初回standaloneの{vector_payload}Bだけを全保持payloadとしない。Snapshotは既にResult内なので二重加算しない。allocator overhead・一時buffer・stack/RSS・使用heapやpeakの上限ではない。全CTestのreal {report['nativeCtestSeconds']:.2f}sは当該実行の所要時間で、一般性能保証ではない。

## 証拠・試行履歴

[集約原本]({PREFIX}-local-verification.json) は完成した `checks/run-20261104-summary-002/acceptance.json` のbyteexactコピー。canonical native/regressions/reference/summary各ディレクトリに元command/stdout/stderr/前後hashを保持する。図と教材のローカル表示は{report['localBrowser']['capturedDisplayFiles']}captureとobservationsに保存し、ブラウザで新Native APIを実照会したとはしない。

Native初回standalone・canonical・数学包含は成功。正式集約summary001はstandalone streamのrun-local basenameをROOT直下へ誤解決した収集pathエラーで停止し、原stderrを保持した。解決pathとstream hash監査を訂正したsummary002を今回の正式原本とする。参照run003はchecker成功後、negative suiteの開始前にPython IndentationErrorで止まった。run004/005と親canonicalの成功を別に保持し、製品入力/閾値や数学基準を弱めていない。最初の統合script著述時のSyntaxErrorも実行前のstatic parse失敗で、製品や実統合実行の失敗へ付け替えない。人工unknown nonreturnの整合正例、数学的に有効な広いroot正例、コピー改変拒否は、自然なC++ allocator/value/root故障注入と区別する。

## 調査と配布

今回実読した一次資料は [Microsoft sqrt API](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/sqrt-sqrtf-sqrtl?view=msvc-170) と [GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)。前者は戻り値/domainの説明であり、外部stdlib全体の正しいRNやactual linked SQRT命令を証明する資料ではない。後者のcompiler flag説明も現artifactのmachine binding検査を代用しない。将来のintrinsics/実命令調査は今回の実装/受入へ混ぜない。

新外部library/package/完成solver/有料契約/転載素材を追加せず、原著C++・Python stdlib Fractionと既存独自Intervalを使う。本体licenseは未選定のまま。92-export SDK/WASM/glue/build manifest、runtime91memberと既存7通知は保持した。一般接触応答・流体・材料損傷・専門シミュレータ・IK制御・高精度撮像の完成ではない。
"""
    additions = {
        'docs/legal/ASSETS.md': '2026-11-04 球box coverage: docs/learn/diagrams/accelerated-sphere-box-coverage.svg は本repoで原著制作した1120×760のvector概念図で、軌道/性能の実測plotや外部図の転載ではない。教材追加文も原著。既存sample素材を保持し、新外部素材/有料契約/本体license選択はない。',
        'docs/RESEARCH.md': f"2026-11-04 球box coverageローカル受入: {report['ctest']}CTest/{report['nativeGroups']}群/{report['finiteFixtures']}入力、{root['returnedResults']}全Evaluationの{report['nativeEndpointBitComparisons']}端点bitと{report['nativeRootDiagnosticComparisons']}root診断再照会、独立Fractionの6真quadratic extrema±Bとrecorded boxes以降の整数RN/root平方包含、{report['selfTestGroups']}自己/{report['negativeControls']}拒否、Node{report['node']} skip0成功。観測root精錬{root['returnedRefinements']}、limited正認証{root['limitedPositiveEvaluations']}。{report['protectedFilesUnchanged']}原本/26HTML/SDKを保持。公開GNU CI/sanitizer/Pagesとactual std::sqrt/compiler binding・World guardは未受入。Microsoft sqrt API/GCC Optimize Optionsを実読したがAPI説明を外部RN保証へ昇格しない。原著図/教材・自作Interval/Fraction、新依存/素材転載/有料serviceなし。初期Python構文失敗rawを保存し製品/数学基準を変えず再検証した。",
        'docs/legal/REFERENCES.md': '2026-11-04 球box coverage: [Microsoft sqrt API](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/sqrt-sqrtf-sqrtl?view=msvc-170) と [GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) を実読。sqrt APIのdomain/戻り値説明から外部std::sqrtの全binary64 RNを保証しない。原著の端点平方不等式/RN単調性導出、recorded boxesからの整数RN参照とNative返却bit由来を分ける。外部code/図/本文/式画像の転載なし。将来World実binding・intrinsics調査は今回受入の証拠へ含めない。',
        'docs/legal/DEPENDENCIES.md': '2026-11-04 球box coverage: 原著C++/Python stdlib Fractionと既存独自Intervalを使用。新外部package/完成数学・物理solver/transitive dependency/有料service/転載素材なし。Native専用でSDKを再buildせず、92exports/32TU/WASM-glue-manifest bytes/runtime91members/7通知を保持。本体license未選定を維持。将来source_enforced World guardは未実装の別feature。',
    }
    writes = {plan_path: plan, sphere_path: sphere, RECORD: record}
    for name, addition in additions.items():
        path = ROOT/name
        text = path.read_text(encoding='utf-8')
        need(addition not in text, 'Do not append the same receipt twice: ' + name)
        writes[path] = text.rstrip() + '\n\n' + addition + '\n'
    # All checks/rendering of prose complete before the first mutation.
    TARGET.write_bytes(raw)
    for path, text in writes.items():
        path.write_text(text, encoding='utf-8', newline='\n')
    need(TARGET.read_bytes() == raw, 'Local receipt must remain byteexact.')
    for name, expected in frozen.items():
        need(stamp(ROOT/name) == {key: expected[key] for key in ['bytes', 'sha256']}, 'Read-only code/display source changed: ' + name)
    print(json.dumps({'status': 'PASS', 'localRecordCopiedExactly': True,
                      'acceptance': stamp(SOURCE), 'localReceipt': stamp(TARGET),
                      'report': RECORD.relative_to(ROOT).as_posix(),
                      'scope': 'Local acceptance only; public CI/ASan/UBSan/Pages and actual World binding remain unverified.',
                      'updated': [path.relative_to(ROOT).as_posix() for path in writes]}))


if __name__ == '__main__':
    main()
