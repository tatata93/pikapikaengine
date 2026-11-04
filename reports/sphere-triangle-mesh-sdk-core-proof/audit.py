import pathlib,json,struct,hashlib
r=pathlib.Path.cwd();o=r/'build/sphere-triangle-mesh-sdk-core'
def load(p):return json.loads(p.read_bytes(),parse_int=lambda t:-0.0 if t=='-0' else int(t))
def bits(x):return struct.pack('>d',x).hex()
def flatten(v):return [x for pair in v for x in pair]
native=load(o/'probe.json');pure=load(r/'build/sphere-triangle-mesh-core/fixtures.stdout.bin');checked=0;last=[]
def compare(values,hexes,expected):
 global checked
 assert len(values)==len(hexes)==len(expected)
 assert [bits(x) for x in values]==hexes==[bits(x) for x in expected]
 checked+=len(values)
def single_packet(q,id):
 g=q['geometry'];a=[0.]*58;a[:11]=[q['status'],q['reason'],int(g is not None),id,g['survivingFeatures'] if g else 0,g['relation'] if g else 0,len(q['candidates']),q['candidatesExamined'],q['sqrtRefinements'],int(q['sqrtRefinementLimited']),int(q['squaredCross'] is not None)]
 if q['squaredCross'] is not None:a[11:13]=q['squaredCross']
 a[13]=int(q['sineSquared'] is not None)
 if q['sineSquared'] is not None:a[14:16]=q['sineSquared']
 if g:
  for index,key in [(16,'barycentric'),(22,'closestLocal'),(28,'closest'),(34,'delta'),(40,'normal'),(46,'spherePoint')]:a[index:index+6]=flatten(g[key])
  a[52:54]=g['squaredDistance'];a[54:56]=g['distance'];a[56:58]=g['gap']
 return a
assert native['fixtureCount']==len(native['fixtures'])==len(pure['fixtures'])==48
rejections=[];model=0
for actual,c in zip(native['fixtures'],pure['fixtures']):
 assert actual['name']==c['name'];i=c['input'];s=i['settings'];p=s['primitive'];q=i['sphere']['center']+[i['sphere']['radius'],s['maxSurfaces']]+[p[k] for k in ['maxCandidates','sqrtRefinements','maxTotalSqrtRefinements','maximumLocalWidth','maximumNormalWidth','minimumSineSquared']]+[0]*3
 compare(actual['input'],actual['inputBits'],q)
 triangles=[[t['id']]+[x for v in t['vertices'] for x in v] for t in i['triangles']]
 assert len(actual['triangles'])==len(actual['triangleBits'])==len(triangles)
 for a,b,t in zip(actual['triangles'],actual['triangleBits'],triangles):compare(a,b,t)
 assert [bits(x) for x in actual['outputBefore']]==actual['outputBeforeBits']==last
 if actual['exchangeStatus']!=0:
  assert actual['hostFailurePreserved'] is True and actual['summary'] is None and actual['summaryBits'] is None and actual['sources']==actual['sourceBits']==actual['rows']==[]
  assert (len(triangles)==65 and actual['failedPhase']=='begin') or (any(t[0] in [0,9007199254740992] for t in triangles) and actual['failedPhase']=='append')
  rejections.append({'name':c['name'],'phase':actual['failedPhase'],'exchangeStatus':actual['exchangeStatus']})
 else:
  model+=1;assert actual['hostFailurePreserved'] is None and actual['failedPhase'] is None and actual['beginStatus']==0 and all(x==0 for x in actual['appendStatuses'])
  result=c['result'];nearest=result['nearest'];a=[0.]*24;a[:15]=[result['status'],result['reason'],int(nearest is not None),len(triangles),len(result['rows']),int(result['failedIndex'] is not None),result['failedIndex'] or 0,int(result['firstFailedRow'] is not None),result['firstFailedRow'] or 0,result['queries'],result['candidatesExamined'],result['sqrtRefinements'],result['sqrtLimitedRows'],result['failedRows'],len(nearest['possibleSurfaceIds']) if nearest else 0]
  if nearest:a[15:17]=nearest['squaredDistance'];a[17:19]=nearest['distance'];a[19:21]=nearest['gap']
  compare(actual['summary'],actual['summaryBits'],a)
  assert len(actual['sources'])==len(actual['sourceBits'])==len(triangles)
  for index,(v,h,t) in enumerate(zip(actual['sources'],actual['sourceBits'],triangles)):
   hasrow=index<len(result['rows']);hasquery=hasrow and result['rows'][index]['query'] is not None
   compare(v,h,[index]+t+[int(hasrow),int(hasquery),int(nearest is not None and t[0] in nearest['possibleSurfaceIds'])])
  assert len(actual['rows'])==len(result['rows'])
  for index,(row,expected) in enumerate(zip(actual['rows'],result['rows'])):
   assert row['rowOrdinal']==index
   q=expected['query']
   if q is None:assert row['packet'] is None and row['bits'] is None and row['candidates']==row['candidateBits']==[];continue
   compare(row['packet'],row['bits'],single_packet(q,expected['triangle']['id']))
   assert len(row['candidates'])==len(row['candidateBits'])==len(q['candidates'])
   for values,hexes,candidate in zip(row['candidates'],row['candidateBits'],q['candidates']):compare(values,hexes,[candidate['feature'],candidate['disposition'],candidate['kktCount']]+flatten(candidate['barycentric'])+flatten(candidate['kkt']))
  if actual['rows']:
   row=actual['rows'][-1];last=row['candidateBits'][-1] if row['candidateBits'] else row['bits']
  elif actual['sources']:last=actual['sourceBits'][-1]
  else:last=actual['summaryBits']
 assert [bits(x) for x in actual['outputAfter']]==actual['outputAfterBits']==last
assert model==native['accepted']==45 and len(rejections)==native['hostRejected']==3
result={'status':'PASS','fixtures':48,'acceptedModelAttempts':model,'hostRejections':rejections,'numericBitsCompared':checked,'sourceSignedZeroAndUnusedKKTBits':True,'outputHistoryAndCapturedHexValidated':True,'layoutComparedAgainstFrozenNativeKernel':True,'independentGeometryOracle':False,'probeSHA256':hashlib.sha256((o/'probe.json').read_bytes()).hexdigest()}
(o/'transport-audit.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
