"""Validate existing public captures; do not operate UI or invent observations."""
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
import json
import math
import re
import subprocess
import sys

if not __debug__:
    raise SystemExit('Run without Python -O')
ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'world-static-mesh-preparation'
assert len(sys.argv)==2, 'Usage: browser-record.py FULL_FEATURE_COMMIT'
FEATURE = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}',FEATURE)
assert subprocess.check_output(['git','rev-parse',FEATURE+'^{commit}'],cwd=ROOT,text=True).strip()==FEATURE
DIRECTORY = ROOT/f'reports/{PREFIX}-public-browser'
assert DIRECTORY.is_dir()


def relative(path):
    p = Path(path)
    p = (p if p.is_absolute() else ROOT/p).resolve()
    assert p.is_relative_to(ROOT)
    return p.relative_to(ROOT).as_posix()


def stamp(raw):
    assert len(raw)<=16*1024*1024
    return {'bytes':len(raw),'sha256':sha256(raw).hexdigest()}


def digest(path):
    return stamp((ROOT/relative(path)).read_bytes())


def read(path):
    raw = (ROOT/relative(path)).read_bytes();stamp(raw)
    def floating(token):
        value = float(token)
        assert math.isfinite(value) and not (value==0 and any(c in '123456789' for c in token.lower().split('e')[0]))
        return value
    def pairs(items):
        result = {}
        for key,value in items:
            assert key not in result,key
            result[key] = value
        return result
    return json.loads(raw.decode('utf-8-sig'),parse_float=floating,parse_int=lambda t:-0.0 if t=='-0' else int(t),
                      parse_constant=lambda t:(_ for _ in ()).throw(AssertionError(t)),object_pairs_hook=pairs)


def feature_blob(path):
    return subprocess.check_output(['git','show',FEATURE+':'+path],cwd=ROOT)


def public_url(url,path):
    parsed = urlsplit(url)
    assert parsed.scheme=='https' and parsed.netloc=='tatata93.github.io'
    assert unquote(parsed.path)=='/pikapikaengine/'+path
    assert parse_qs(parsed.query)=={'v':[FEATURE[:7]]}


def jpeg_dimensions(raw):
    assert raw[:2]==b'\xff\xd8';at = 2
    while at+4<=len(raw):
        assert raw[at]==255
        marker = raw[at+1];at += 2
        length = int.from_bytes(raw[at:at+2],'big')
        assert length>=2 and at+length<=len(raw)
        if marker in (192,193,194):
            assert length>=7
            return int.from_bytes(raw[at+5:at+7],'big'),int.from_bytes(raw[at+3:at+5],'big')
        at += length
    raise AssertionError('No JPEG frame')


class ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.parts = []

    def handle_data(self,text):
        self.parts.append(text)


public = read(f'reports/{PREFIX}-public-bytes.json')
assert public['schema']==1 and public['status']=='PASS' and public['commit']==FEATURE
assert public['build']=='cd45c7f1ac2ba5e5' and public['channels']=={'pages':73,'githubSource':1}
assert len(public['files'])==len({row['path'] for row in public['files']})==74
published = {row['path']:row for row in public['files']}
observations = read(DIRECTORY/'observations.json')
assert type(observations['schema']) is int and observations['schema']==1
assert set(observations['observedURL'])=={'diagram','lesson','game'}
capture_names = ['diagram.jpg','diagram-ax.txt','lesson.jpg','lesson-ax.txt','lesson-article.txt',
                 'public-game.jpg','public-game-ax.txt','public-game-cover-report.json','observations.json']
evidence = {relative(DIRECTORY/name):digest(DIRECTORY/name) for name in capture_names}
assert all(row['bytes']>0 for row in evidence.values())
expected_files = {relative(DIRECTORY/name) for name in capture_names if name!='observations.json'}
assert type(observations['files']) is list and len(observations['files'])==len(set(observations['files']))
assert set(observations['files'])==expected_files
sources = {};screens = {}
for key,path in [('diagram','docs/learn/diagrams/world-static-mesh-preparation.svg'),('lesson','docs/learn/index.html')]:
    public_url(observations['observedURL'][key],path)
    raw = feature_blob(path);record = published[path]
    assert record['distribution']=='pages' and stamp(raw)=={'bytes':record['bytes'],'sha256':record['sha256']}
    sources[key] = {'path':path,'url':observations['observedURL'][key],
                    'screenshot':relative(DIRECTORY/(key+'.jpg')),'accessibility':relative(DIRECTORY/(key+'-ax.txt')),
                    'source':stamp(raw)}
    width,height = jpeg_dimensions((DIRECTORY/(key+'.jpg')).read_bytes())
    assert 200<=width<=4096 and 100<=height<=4096
    screens[key] = {'width':width,'height':height}
lesson = feature_blob(sources['lesson']['path']).decode('utf-8')
articles = [m for m in re.finditer(r'<article\b([^>]*)>(.*?)</article>',lesson,re.S)
            if 'world-static-mesh-preparation.svg' in m[2]]
assert len(articles)==1
article = articles[0];parser = ArticleText();parser.feed(article[0]);parser.close()
article_text = (DIRECTORY/'lesson-article.txt').read_text(encoding='utf-8-sig')
assert re.sub(r'\s+','',article_text)==re.sub(r'\s+','',''.join(parser.parts))
assert observations['lessonArticleFile']==relative(DIRECTORY/'lesson-article.txt')
assert re.findall(r'<img\b[^>]*\bsrc="([^"]*world-static-mesh-preparation\.svg)"',article[2])==[observations['lessonImage']['src']]
assert observations['lessonImage']['src']=='diagrams/world-static-mesh-preparation.svg'
assert observations['lessonImage']['complete'] is True
assert type(observations['lessonImage']['naturalWidth']) is int and type(observations['lessonImage']['naturalHeight']) is int
assert (observations['lessonImage']['naturalWidth'],observations['lessonImage']['naturalHeight'])==(1120,780)
assert re.findall(r'<a\b[^>]*\bhref="([^"]*WORLD_STATIC_MESH_PREPARATION\.md)"',article[2])==[observations['guideHref']]
assert observations['guideHref']=='../WORLD_STATIC_MESH_PREPARATION.md'
game_url = urlsplit(observations['observedURL']['game'])
assert game_url.scheme=='https' and game_url.netloc=='tatata93.github.io'
assert game_url.path in {'/pikapikaengine/','/pikapikaengine/index.html'} and parse_qs(game_url.query)=={'v':[FEATURE[:7]]}
game = read(DIRECTORY/'public-game-cover-report.json')
state = (DIRECTORY/'public-game-ax.txt').read_text(encoding='utf-8-sig')
assert game['state']=='ready' and game['failure'] is None and game['pending'] is None and game['errors']==[]
assert '一時停止 / Pで再開' in state
kills = re.search(r'撃破\s+(\d+)',state);assert kills and int(kills[1])>0
queries = game['counts']['queries']
assert type(queries) is int and queries>0 and queries==game['counts']['checked']==game['counts']['validated']==len(game['records'])
assert all(r['state']=='completed' for r in game['records']) and any(r['clipSeconds']==1 for r in game['records'])
assert game['renderer']['residentMeshes']==3 and game['renderer']['lost'] is False and game['renderer']['disposed'] is False
assert game['startup']['diagnostics']['buildId']==public['build'] and game['startup']['diagnostics']['wasmBytes']==800982
assert published['assets/pikapika-simulation.wasm']['bytes']==800982
asset = urlsplit(game['startup']['assetURL'])
assert asset.scheme=='https' and asset.netloc=='tatata93.github.io' and asset.path=='/pikapikaengine/assets/robot-back-cover.skin.json'
assert parse_qs(asset.query)=={'build':[public['build']]}
width,height = jpeg_dimensions((DIRECTORY/'public-game.jpg').read_bytes())
assert 200<=width<=4096 and 100<=height<=4096
screens['game'] = {'width':width,'height':height}
report = {'schema':1,'status':'PASS','phase':'public','commit':FEATURE,'checked':datetime.now(timezone.utc).isoformat(),
          'buildId':public['build'],'wasmBytes':800982,
          'scope':'Native-only preparation: public diagram/lesson display and existing game compatibility; no browser preparation query.',
          'diagram':sources['diagram'],'lesson':sources['lesson'],'screens':screens,
          'game':{'paused':True,'kills':int(kills[1]),'coverQueries':queries,'allCompleted':True,'boostClip1Observed':True,'residentMeshes':3},
          'recipe':{'path':relative(__file__),**digest(__file__)},'evidence':evidence,
          'publicByteReceipt':{'path':f'reports/{PREFIX}-public-bytes.json',**digest(f'reports/{PREFIX}-public-bytes.json')},
          'observationScope':'This recipe reads existing observations, original captures and exact-feature byte receipts. It does not open a browser, execute a preparation query or infer screenshot readability. Independent visual QA is performed by the parent before final public acceptance.'}
output = DIRECTORY/'browser-verification.json'
if output.exists():
    previous = read(output)
    assert {k:v for k,v in previous.items() if k!='checked'}=={k:v for k,v in report.items() if k!='checked'}
    report = previous
else:
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'commit':FEATURE,'capturedEvidence':len(evidence),
                  'buildId':report['buildId'],'gameQueries':queries,'scope':report['scope']}))
