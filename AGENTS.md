# pikapikaengine

Read `docs/PLAN.md` for current state and the next acceptance criterion. The full product requirements are in `docs/PROJECT_SPEC.md`; direct user steering overrides the attached original instructions.

- Build the engine from original code and OS/GPU/browser APIs. No Unity/Unreal/Godot/Three/Babylon or finished math/physics/audio replacements.
- Keep reusable engine APIs in `engine/` and `core/`, game logic in `samples/`, native platform code in `platform/`.
- SI metres/seconds/kg, right handed, Y up. Simulation is fixed 120Hz; rendering interpolates. Explicitly report dropped simulation time.
- Preserve existing work, IDs, source assets, and compatibility. Use `Scene` editing APIs; test edits through save/reload.
- Normal commands: `npm test`, `npm run check`, `npm run build`, `npm start`, `./scripts/build-native.ps1`, `./scripts/smoke-native.ps1`. Run the web build before milestone pushes: it regenerates the inline import maps and asset URL build IDs, preventing mixed cached versions on Pages. Do not manually edit those generated blocks.
- Update relevant original diagrams/HTML lessons and the research/legal record when adding core capabilities. Never report unmeasured performance or untested outputs as verified.
- User authorizes milestone git commits/pushes and public launch links. No payment, paid service contracts, forum posts, or email operations. Avoid changes to billing or subscriptions. GitHub Pages is configured for this public repo on `main` root; do not enable paid runners/storage.
- The engine license is undecided. Do not fabricate a copyright owner or silently choose a license. Only original procedural assets are currently included.
- Independent work may use parallel agents per the original user specification §12.1; define file ownership and integrate/test before pushing.
- Continue from the smallest unfinished milestone. The robot sample is original: never copy existing game names/assets/UI/data. Another chat may edit the sample; merge its work instead of replacing it.

Automation: a 30-minute heartbeat is configured for this chat. Keep status quiet when nothing changes, report meaningful milestones/failures/action needs. A heartbeat requires the app and execution environment to remain available; never promise uninterrupted indefinite execution.
