import pathlib,json,math
p=pathlib.Path('build/sphere-triangle-mesh-sdk-core');src=json.loads(pathlib.Path('build/sphere-triangle-mesh-core/fixtures.stdout.bin').read_bytes(),parse_int=lambda t:-0.0 if t=='-0' else int(t))
def tok(v):return '-0' if v==0 and math.copysign(1,v)<0 else str(v)
lines=['pikapika_sphere_triangle_mesh_sdk 1','cases '+str(len(src['fixtures']))]
for c in src['fixtures']:
 i=c['input'];s=i['settings'];primitive=s['primitive'];q=i['sphere']['center']+[i['sphere']['radius'],s['maxSurfaces']]+[primitive[k] for k in ['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared']]+[0]*3
 lines.append(json.dumps(c['name'])+' '+str(len(i['triangles']))+' '+' '.join(map(tok,q)))
 for t in i['triangles']:lines.append(' '.join(map(tok,[t['id']]+[v for xyz in t['vertices'] for v in xyz])))
(p/'input.rows').write_bytes(('\n'.join(lines)+'\n').encode('ascii'));print(len(lines),'lines',len((p/'input.rows').read_bytes()),'bytes')
