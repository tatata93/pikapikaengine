# Scene format v1

The native CLI and Windows renderer read this portable UTF-8 text format. The
browser uses JSON internally and imports/exports the same portable records through
`engine/portable-scene.mjs`. Existing v1 scenes remain valid.

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

Supported types are `box`, `plane`, `robot`, `camera`, `source`, and `listener`.
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
native `Scene` API used by the CLI; the format version remains 1.
