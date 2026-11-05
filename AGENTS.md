# pikapikaengine

Read `docs/PLAN.md` for current state and the next acceptance criterion. The full product requirements are in `docs/PROJECT_SPEC.md`; direct user steering overrides the attached original instructions.

- Build the engine from original code and OS/GPU/browser APIs. No Unity/Unreal/Godot/Three/Babylon or finished math/physics/audio replacements.
- Keep reusable engine APIs in `engine/` and `core/`, game logic in `samples/`, native platform code in `platform/`.
- SI metres/seconds/kg, right handed, Y up. Simulation is fixed 120Hz; rendering interpolates. Explicitly report dropped simulation time.
- Preserve existing work, IDs, source assets, and compatibility. Use `Scene` editing APIs; test edits through save/reload.
- Normal commands: `npm test`, `npm run check`, `npm run build`, `npm start`, `./scripts/build-native.ps1`, `./scripts/smoke-native.ps1`. Run the web build before milestone pushes: it regenerates the inline import maps and asset URL build IDs, preventing mixed cached versions on Pages. Do not manually edit those generated blocks.
- Update relevant original diagrams/HTML lessons and the research/legal record when adding core capabilities. Never report unmeasured performance or untested outputs as verified.
- User authorizes milestone git commits/pushes and public launch links. No payment, paid service contracts, forum posts, or email operations. Avoid changes to billing or subscriptions. GitHub Pages uses the bounded `.github/workflows/pages.yml` distribution from public `main`; keep the existing site URL/HTTPS/domain and all proof originals in Git, validate actual archive bytes before deployment, and do not enable paid runners/storage.
- User additionally authorizes other sample games/simulators and necessary tools/libraries after research. Record purpose, alternatives, accuracy, license, transitive dependencies and distribution scope; routine researched additions do not need another confirmation. Preserve the independent-engine objective. New feature requests normally join the dependency order; switch priority for explicit requests such as "今やれ" or "至急".
- Latest additional scope: validated general rigid-body/contact, vehicle/aviation/rail models, air/water fluids, elastic/plastic damage, optional high-accuracy lens optics. See docs/PHYSICS_SCOPE.md, docs/OPTICS_SCOPE.md and the FK/IK/control-graph proposal docs/CONTROL_DESIGN.md. Never claim proxies/manual mesh edits prove those models complete.
- The engine license is undecided. Do not fabricate a copyright owner or silently choose a license. Only original procedural assets are currently included.
- Independent work may use parallel agents per the original user specification §12.1; define file ownership and integrate/test before pushing.
- Continue from the smallest unfinished milestone. The robot sample is original: never copy existing game names/assets/UI/data. Another chat may edit the sample; merge its work instead of replacing it.

Automation: a 30-minute heartbeat is configured for this chat. Keep status quiet when nothing changes, report meaningful milestones/failures/action needs. A heartbeat requires the app and execution environment to remain available; never promise uninterrupted indefinite execution.


追記: 2026-11-06 計算量・保持量・省略情報7型43memberを追加し合計29型149member。実MSVC19.51x64 fresh wfdl1 Release/真Debugの3706 byte、独立109leaf(U64 98/bool11)、802停止例外/2807再入、4丸めmode、232byte+3record拒否、15header+manifestの1受理18拒否が成功。旧12葉型/10設定型を再実行し3112/4587 byteと実行結果を全保持。登録61/59だが実行は各3CTestのみ、旧数値coreをbuild/linkせず20profile不変、Node693skip0/構文/Web25509ed4cc1d87e4・54modules成功。integration001はWindows標準libraryを過剰拒否し原記録を保存、列挙修正後fresh002で受入。前段設定source457be0aは実GNU13.3の16command/通常・真Debug・全新TU O1 ASan-UBSanで全4587 byte一致を受入、277+3改変/18schema拒否、decoded1019169Bとfinal JSON・26sourceをfeatureblob照合。Engine42070956777全6job/Pages42070956819成功。childraw/objectはrunner-local。新ledger GNU/全Report/C API pump/WASM/ゲームは未受入。次はguard::Work22member、interval端点・全audit/partition/frontier・最上位Report/未実行tail。旧核/owner/SDK/sampleと他チャット改変を保持。


追記: Work22memberの取得をNative有限受入、合計30型171member。新GNUは別受入待ち。実結果と次のInterval/SqrtResult対応はdocs/PLAN.md、docs/REPORT_WORK_WIRE.md、reports/diagnostic-wire-work-verification.jsonを参照。旧数値核/owner/SDK/sampleを保持する。


追記: Interval端点/SqrtResultの2型5項目をNative有限受入、合計32型176項目。実interval.cppは試験だけ、getterは再構築/演算/probeなし。実結果と次のCandidateAudit/Geometry対応はdocs/PLAN.mdとdocs/REPORT_INTERVALS_WIRE.md、reports/diagnostic-wire-intervals-verification.jsonを参照。


追記: 区間取得の初GNUはharnessのmisleading-indentationで停止。brace/改行だけの修正をfresh wfdin2で受入し旧1037byte/全出力/旧4fixture/20profileを保持。製品/数学核不変、新GNUは未受入。初失敗rawと全記録を保持。最新はdocs/PLAN.mdとdiagnostic-wire-intervals-verification.jsonを参照。


追記: CandidateAudit/Geometry2型17項目をNative有限受入、合計34型193項目。全固定配列を取得し人工診断と実queryを区別。新GNU/全Resultは未受入。実結果と次のResult optional/message取得はdocs/PLAN.mdとdocs/REPORT_GEOMETRY_WIRE.md、reports/diagnostic-wire-geometry-verification.jsonを参照。


追記: Result全10項目の取得をNative有限受入し合計35型203項目。新GNU/全Reportは未受入。最新はdocs/PLAN.md、docs/REPORT_RESULT_WIRE.mdとdiagnostic-wire-result-verification.json。次はmesh::Row/Nearest、旧核/owner/SDK/sampleを保持する。


追記: mesh Row/Nearest2型6項目の取得をNative有限受入、合計37型209項目。新GNU/mesh全Resultは別受入。最新はdocs/PLAN.md、docs/REPORT_MESH_VALUES_WIRE.mdとdiagnostic-wire-mesh-values-verification.json。旧数値核/owner/SDK/sampleを保持。


追記: mesh::Result全12項目の取得をNative有限受入、合計38型221項目。新GNU/最上位Reportは別受入。最新はdocs/PLAN.md、docs/REPORT_MESH_RESULT_WIRE.mdとdiagnostic-wire-mesh-result-verification.json。旧核/owner/SDK/sampleを保持。


追記: heldの原入力/Cell/選択body3型11項目をNative有限受入し合計41型232項目。新GNU/全held Resultは後続。最新はdocs/PLAN.md、docs/REPORT_HELD_SOURCE_VALUES_WIRE.mdとdiagnostic-wire-held-source-verification.json。新harnessもInterval TU/数値model library非link。旧核/owner/SDK/sampleを保持。


追記: held Snapshot/Work2型15項目をNative有限受入、合計43型247項目。新GNU/全held Resultは後続。最新はdocs/PLAN.md、docs/REPORT_HELD_SNAPSHOT_WORK_WIRE.mdとdiagnostic-wire-held-snapshot-work-verification.json。旧数値核/owner/SDK/sampleを保持。


追記: held小型証明4型18項目をNative有限受入、合計47型265項目。新GNU/全held Resultは後続。最新はdocs/PLAN.md、docs/REPORT_HELD_PROOFS_WIRE.mdとdiagnostic-wire-held-proofs-verification.json。旧数値核/owner/SDK/sampleを保持。


追記: held監査/区画2型22項目とoptional配列/enumをNative有限受入、合計49型287項目。新GNU/全held Resultは後続。最新はdocs/PLAN.md、docs/REPORT_HELD_AUDITS_WIRE.mdとdiagnostic-wire-held-audits-verification.json。旧数値核/owner/SDK/sampleを保持。


追記: held Result全25項目をNative有限受入、合計50型312項目。保持荷重13型98項目の保存範囲を対応。新GNU/最上位Reportは後続。最新はdocs/PLAN.md、docs/REPORT_HELD_RESULT_WIRE.mdとdiagnostic-wire-held-result-verification.json。旧数値核/owner/SDK/sampleを保持。


追記: 自由飛行Snapshot/Tube2型11項目をNative有限受入、合計52型323項目。新GNU/最上位Reportは後続。最新はdocs/PLAN.md、docs/REPORT_FLIGHT_SOURCE_TUBE_WIRE.mdとdiagnostic-wire-flight-source-tube-verification.json。旧数値核/owner/SDK/sampleを保持。


追記: 自由飛行EndpointAudit全9項目をNative有限受入、合計53型332項目。新GNU/最上位Reportは後続。最新はdocs/PLAN.md、docs/REPORT_FLIGHT_ENDPOINT_WIRE.mdとdiagnostic-wire-flight-endpoint-verification.json。旧数値核/owner/SDK/sampleを保持。
