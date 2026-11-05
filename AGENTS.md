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
