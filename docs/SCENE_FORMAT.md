# Scene formats v1 and v2

The native CLI and Windows renderer read this portable UTF-8 text format. The
browser uses JSON internally and imports/exports the same portable records through
`engine/portable-scene.mjs`. Existing v1 scenes remain valid. Scenes containing an
editable indexed mesh use v2; exports without meshes use v1.

```text
pikapika-scene 1
units m s kg
axes right-handed y-up
entity 4 "camera" "Main camera" 0 18 65 0 0 0 1 1 1 1 0
entity 5 "source" "Direct sound source" -20 5 -10 0 0 0 1 1 1 1 0
entity 6 "listener" "Direct sound listener" 0 5 30 0 0 0 1 1 1 1 0
```

Each entity line contains `entity`, stable numeric ID, quoted type, quoted name,
position `px py pz` in metres, normalized quaternion `qx qy qz qw`, positive scale
`sx sy sz`, and collider radius in metres. IDs are integers from 1 through
9007199254740991. Names escape quotation marks and backslashes with a backslash.

Supported types are `box`, `plane`, `robot`, `camera`, `source`, and `listener`,
plus `mesh` in v2.
Camera, source, and listener are typed transforms with **no geometry**. Their final
radius field is reserved and must be zero: it is not a field of view, volume,
directivity, or hearing radius. Source and listener positions can feed the existing
ideal direct-path delay and attenuation model. This does not add room reflections,
material acoustics, or production camera settings.

`pikapika init example.scene` creates three geometry records and these three typed
records. `pikapika audio-scene example.scene direct.wav` uses the first source and
listener positions to write a 48 kHz mono PCM reference impulse. It errors when
either type is absent. The default pair is 44.7214 m apart, giving approximately
0.130383 s direct-path delay at 343 m/s; gain is an ideal pressure ratio at a
one-metre reference distance.

The Windows viewer takes its initial position and look direction from the first
camera record. It skips source/listener geometry. The browser currently supports
Y-axis rotations only and rejects other portable rotations explicitly. Native
geometry supports general quaternions. Native camera preview derives yaw/pitch
from the quaternion's forward direction; camera roll is not currently displayed.
The original quaternion remains in the scene data. Native preview projection remains fixed
(60 degree vertical field of view, 1280 x 720 render target).

Browser geometry imports map native `robot` and `plane` to preview boxes while
retaining `sourceType`. A plane's preview thickness is adjusted by 0.02 and reversed
on export. This is a geometry preview approximation. New browser string IDs receive
a deterministic 53-bit numeric identity; existing native IDs are preserved exactly.
Collisions stop export. `# browser-meta` comments preserve original browser string
IDs and colors through native editing. Native load/save preserves bounded opaque
comment lines; it does not interpret those colors for its current preview shading.

Native limits: 100000 entities, 100000 comment lines, and 4096 characters per line.
The browser subset additionally limits files to 2 MB and scenes to 4096 entities.
Unsupported types, malformed fields, duplicate IDs, nonfinite values, and invalid
rotations fail explicitly. Stable IDs and transforms are editable through the same
native `Scene` API used by the CLI.

## Editable indexed meshes (v2)

```text
pikapika-scene 2
units m s kg
axes right-handed y-up
entity 7 "mesh" "Editable triangle" 0 0 0 0 0 0 1 1 1 1 0
mesh 7 3 1
vertex 0 0 0
vertex 1 0 0
vertex 0 1 0
triangle 0 1 2
```

Each mesh entity requires exactly one complete geometry block. `mesh ID V T`
must refer to an earlier mesh entity and is followed by exactly V `vertex x y z`
records, then exactly T `triangle i j k` records. Vertex indices are zero-based
and remain stable during vertex-position editing. The writer places each block
immediately after its entity. Comments and other records cannot interrupt a
geometry block. Unknown, duplicate, missing, truncated, and malformed blocks
fail explicitly. Mesh records are rejected in v1.

The browser equivalent is `type: "mesh"` with
`mesh: {version: 1, positions: [[x,y,z], ...], triangles: [[i,j,k], ...]}`.
The outer browser scene version is 2. Source positions and triangle indices,
numeric native IDs, original browser IDs, and color metadata survive portable
export, native editing, and browser reload. Arbitrary quaternion geometry remains
supported natively; browser portable imports still reject rotations outside Y.

Per-mesh authoring limits are 3..65536 vertices and 1..131072 triangles. Scene
totals cannot exceed 262144 mesh vertices or 524288 mesh triangles. Coordinates
must be finite with each component within +/-1000000 m. Faces require three
distinct in-range indices and squared cross-product length greater than
1e-24 m^4. A face must also retain nonzero area after local positions are rounded
to Float32, because the renderer consumes that representation. Large world
offsets can still lose rendering precision; origin shifting is not implemented.
The browser also enforces its separate file and real-time rendering budgets.
Browser source transforms require position components within +/-1000000 m and
positive scale components in [0.000001,1000000]. The current game editor/import
profile reserves space for dynamic gameplay: at most 3000 authored entities,
128 meshes, and 252144 source triangles; the renderer has a separate total
262144-triangle limit. These are explicit implementation limits, not precision
or performance guarantees. Source snapshots are immutable; edits replace them
through Scene so bounds and GPU geometry cannot silently become stale.

`pikapika mesh-init editable.scene` generates an indexed eight-vertex,
twelve-triangle box plus a floor and camera. For example:

```powershell
pikapika mesh-vertex editable.scene 1 6 2 7 2 edited.scene
pikapika roundtrip edited.scene reloaded.scene
pikapika-viewer --scene reloaded.scene
```

`Scene::set_mesh_vertex` validates a candidate before replacing the source mesh.
An invalid edit leaves the original geometry unchanged. Native and browser
renderers expand the indexed source into actual flat-shaded triangles and derive
face normals from the edited positions; neither substitutes a bounding box for
rendering. The native preview currently uses its own fixed mesh color and light,
while portable comments retain browser material colors. Mesh collision is a
separate capability: the current browser controller uses conservative bounds,
not per-triangle contacts. No topology edit, UV, texture, skin, morph, external
model import, or production mesh optimization is implied by this stage.
