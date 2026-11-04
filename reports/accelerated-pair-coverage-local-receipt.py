"""Publish truthful local acceptance prose from the completed aggregate."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]
proof = json.loads((root/'reports/accelerated-pair-coverage-local-verification.json').read_text(encoding='utf-8'))
assert proof['status']=='PASS' and proof['ctest']==43 and proof['node']==684
assert proof['selfTestGroups']==14 and proof['negativeControls']==53
assert proof['independentReference']['returnedIntervals']==1913

def replace(name, before, after):
    path = root/name
    text = path.read_text(encoding='utf-8')
    assert text.count(before)==1, (name,before)
    path.write_text(text.replace(before,after,1),encoding='utf-8',newline='\n')

replace('docs/ACCELERATED_PAIR_COVERAGE.md',
        '**厳密MSVCの単独ビルド・専用試験まで実行済み。独立Fraction監査、全体への統合、公開確認は未完**。',
        '**ローカル受入済み：Native43CTest/専用69群・独立Fractionの全1913区間・自己14群/拒否53・Node684 skip0。公開Linux CI/Pages・GNU warning/sanitizerは次に確認する**。')
replace('docs/ACCELERATED_PAIR_COVERAGE.md','保存Iが真の式の全rangeを含むか検査する予定。','保存Iが真の式の全rangeを含むか検査する。')
replace('docs/ACCELERATED_PAIR_COVERAGE.md',
        '原ログは `reports/accelerated-pair-coverage-native-development/run-001/`。独立Fraction・統合回帰・GNU/sanitizer・公開受入の成功はまだ主張しない。',
        '初回単独ログは `reports/accelerated-pair-coverage-native-development/run-001/`、正式なローカル集計は [local-verification](../reports/accelerated-pair-coverage-local-verification.json)。全43CTest・Node684/skip0・構文/Web cd45c7f1ac2ba5e5が成功し、独立Fractionは全1913区間（sphere1223/plane690）と全1040leaf・128未照会cellを監査した。14自己群/53拒否（Python -Oを含む）が成功。GNU/sanitizer・公開受入は未実施。')
with (root/'docs/ACCELERATED_PAIR_COVERAGE.md').open('a',encoding='utf-8',newline='\n') as stream:
    stream.write('''

この入力域の .1 上限はC++のbinary64定数 .1 と同じ点値であり、参照もその厳密有理数と比較する。数学的な有理数1/10へ入力を再解釈しない。time_toleranceは未証明区間の分割停止条件であり、接触を許す誤差ではない。

```cpp
#include "pikapika/accelerated_pair_coverage.hpp"
using namespace pikapika;
accelerated::Sphere first{}, second{};
first.radius = second.radius = 0.5;
second.center = {4, 0, 0};
second.velocity = {-1, 0, 0};
auto proof = accelerated_pair_coverage::sphere_sphere(first, second, 1.0 / 120.0);
// certified のときだけ、与えた点係数の全 [0,H] 非接触として読む。
// Worldを進める呼出しではない。その他のstatusでは診断と全未知tailを読む。
```

最大例のinline Result＋返却capacity×sizeofは39256B（440＋24480＋9216＋5120）。SnapshotはResult内なので重複加算しない。actual corpusでのeven-square-factor除去は0件、四次Bernsteinは46証明/50node/最大3nodeだった。gcd偶数因子・非有理重根・有限proof予算拒否は別の自己試験で確認し、実65入力で観測したと混同しない。数学的にvalidな広いIと人工nonreturnの整合正例も検査器の試験であり、Nativeの自然throw実行ではない。
''')
replace('docs/ACCELERATED_PAIR_COVERAGE_PLAN.md',
        '**承認済みNative契約。新cppの実装へ進む段階で、未ビルド・未検証**。',
        '**契約設計と受入方針。実装はローカル受入済み、公開GNU/sanitizer確認は次段**。')
replace('docs/ACCELERATED_PAIR_COVERAGE_PLAN.md','## 次の受入','## 受入手順と残件')
replace('docs/ACCELERATED_PAIR_COVERAGE_PLAN.md',
        '新cpp・専用Native fixtures・独立checkerを別所有で実装する。',
        '新cpp・専用Native fixtures・独立checkerを別所有で実装し、Native43CTest/69群/65入力、全1913区間の独立数学、自己14群/拒否53、Node684/skip0でローカル受入した。')
replace('docs/ACCELERATED_PAIR_COVERAGE_PLAN.md',
        '既存SDKやゲームを更新しておらず、新helperのローカル/公開成功もまだない。',
        '既存SDKやゲームを更新しておらず、公開確認は未実施。ローカルの原本・実行・失敗履歴は [受入記録](../reports/2026-11-04-accelerated-pair-coverage.md)に保存する。')

path = root/'docs/PLAN.md'
text = path.read_text(encoding='utf-8')
assert text.count('再開位置:')==1
start = text.index('再開位置:')
new = '再開位置: 新Native accelerated_pair_coverage の球対/平面全closed-cell核をローカル受入した。原入力・全audit/partition/current/frontierを所有し、全leafのvalue.lower()>0だけを認証する。Native43CTest/専用69群/65有限入力、1913実public value全端点bitと独立Fractionの全1913区間、14自己群/53拒否/-O、Node684 skip0・構文/Web cd45/54modules26entriesが成功。362既存raw・旧26HTML・92export SDK/32TU/runtime91/7通知を保持。数学的にvalidな広いIと実返却bitsの由来を分け、人工nonreturnは自然faultではない。次は公開Linux CI/GNU warning/sanitizer/Pagesと84件（83Pages+workflow原本1）のfeature blob照合を確認し、その後に全World guardのB膨張・plane追加条件・global予算・全候補へ接続する。[契約](ACCELERATED_PAIR_COVERAGE.md)・[記録](../reports/2026-11-04-accelerated-pair-coverage.md)。一般接触応答・流体/材料損傷・専門モデル・IK制御・高精度撮像は未完。\n\n'
text = text[:start]+new+text[start:].replace('再開位置:','直前の公開基盤（当時の次段を含む）:',1)
path.write_text(text,encoding='utf-8',newline='\n')

report = '''# Native加速球対・平面の全closed-cell coverage

2026-11-04。baseは公開準備記録41c9cc2d28817e3491b8ab8e47922cc5cc153ae5。ローカル受入PASS、公開Linux CI/Pages・GNU/sanitizerは未実施。[契約](../docs/ACCELERATED_PAIR_COVERAGE.md) / [設計](../docs/ACCELERATED_PAIR_COVERAGE_PLAN.md) / [集計](accelerated-pair-coverage-local-verification.json)。

新Native sphere_sphere / sphere_planeは点binary64を厳密実数とする球対四次式とraw plane二次式の全closed[0,H]を調べる。旧searchを二重実行せず、既存public valueの返却Iをそのまま所有する。全leaf strict positiveだけをcertifiedにし、全audit・親/分割・全partition・current・未照会tailを保持する。H/設定/invalid原本/負零をcaptureし、環境拒否を先に区別する。点witness/entry/TOI/運動候補/World更新/力消費は行わない。

## 実行と独立監査

- 全43CTest成功、専用69群（有限65＋nonvacuity/所有/非有限/環境の4群）。43件の実時間228.94秒、収集wall229.02秒。性能保証ではない。
- 有限65は18certified/19not_certified/28invalid。CMake実fixture649028B、SHA946262e5eecc4c575c69956f24881a5b3513adbf5e91fe8e90633533f8bcfcb7、単独buildとbyte一致。
- 全1913返却Iで既存public value両端bitsが一致。実−0 interval端点は0件、原入力/snapshot−0保持とは別scope。
- 独立Fractionが全1913区間（球対1223/平面690）、全1040partition・128frontier・2currentの組会計/BFS/停止順/Workを監査。原入力multiset fingerprint867fef69e55cf8461310b07f0144c8d2288987ab68311d6d86a04b01e8cca85eはscalar type/bit/全配列を含み、label/fixture順に依存しない。
- 四次は有理Bernstein46証明/50node/最大3node。actualのsquare-factor除去は0。gcd偶数因子・非有理重根・負leading/内部極小・有限proof予算拒否は14自己群で別に確認した。
- 改変拒否53（Python -Oを含む）、label/order独立、数学的validな広いIの受入と人工nonreturn整合の正例が成功。これを自然なallocation/value-throw fault注入としない。
- 安全な球対は21audit11leaf、平面は15audit8leafへ実分割。255audit128leafと、評価127時のpartition128/frontier127/current1を観測。2subnormal秒でwidth_limit/time_resolutionを区別し、tiny normal・FE_UPWARD/FTZDAZ拒否と復帰・所有を検査した。
- Node684/skip0・構文・Web build cd45c7f1ac2ba5e5/54modules26entriesが成功。362既存raw・26生成HTMLを保持し、CMake14/CI14/byte保存規約2の追加だけを元Git blobへ復元確認。SDK92exports/67source-header/32TU/runtime91/7通知、WASM800982B/glue61661Bは同一。新APIのNative/WASM parityではない。

## 費用と範囲

attempt/returnはwrapperの実回数。planeのprivate normはcalls≤attempts/loop≤64×attemptsの上界だけで実反復数ではない。MSVC x64のResult440/Snapshot208/Cell40/Audit96/PartitionLeaf72Bと、capacity255/128/128から得た保持payloadは39256B。Snapshotはinline Result内で二重加算しない。allocator overhead・一時buffer・stack・RSS/使用heap・portable hard-byte/16MiB保証は含まない。自然allocation/value-throw faultは未注入。FP試験は対象制御の拒否/復帰で、全compiler/全exception flagの一般証明ではない。

## 履歴と表示

数学run001はchecker-only PASSで、実行済み自己試験失敗ではない。−0 successorは静的レビューで発見しrun002前に正準化した。run002は14自己群PASS後、control-harnessが24整数→24.0の変更をF64等値で無変更扱いして停止した。型も区別する検出へ直し、製品・固定入力を変えずrun003と親reference001で全再実行した。全元command/stdout/stderr/source前後hashを保持する。

ローカルLastTest.logはignore規約で配布されないため、元rawと同bytesのLastTest.txtを保存した。古いrecorder hashを書き換えず、書出拡張子一箇所だけの変更を保存原本と照合した。Nodeログのcp932表示だけのUnicodeEncodeErrorも別の収集メモに残し、成功したNode実行の失敗へ読み替えない。

原著1120×780 SVGと埋込教材を実ブラウザで確認し、2viewportで全文字・区画・未認証境界・費用上界を目視した。図は概念で実測数値ではなく、ブラウザで新Native APIを実行した証拠ではない。初期設計/実装後、[著者のMIT教材1.3.1](https://web.mit.edu/hyperbook/Patrikalakis-Maekawa-Cho/node9.html)で基底非負性・partition of unityを確認した。外部code/図/本文を転載せず、新依存/素材/有料service/本体license選定は無い。

次は公開全23段の実行、通常と全依存5source ASan/UBSan fixtureのbyte一致/各独立参照、旧GNU warning比較、83Pages+GitHub原本1の配信一致、図/教材/既存ゲームの公開実操作を確認する。全WorldのB/plane追加predicate・global予算・全body候補、接触応答・摩擦・流体・材料損傷・専門モデル・IK制御・高精度撮像は未完。
'''
(root/'reports/2026-11-04-accelerated-pair-coverage.md').write_text(report,encoding='utf-8',newline='\n')
with (root/'docs/RESEARCH.md').open('a',encoding='utf-8',newline='\n') as stream:
    stream.write('\n\ncoverageローカル受入: 43CTest/69群/65入力、1913実返却bit＋独立Fraction全区間、14自己/53拒否、684Node skip0が成功。全362raw/26HTML/SDKを保持。raw履歴のrun001はchecker-only成功、run002は14自己成功後のcontrol型同値誤停止、run003と親で全再実行。自然faultと人工nonreturnを分け、39256Bはsizeof×返却capacity観測。公開CI/GNU/sanitizer/Pagesは次に確認する。\n')
print(json.dumps({'status':'PASS','ctest':43,'node':684,'self':14,'negativeControls':53,'publicPending':True}))
