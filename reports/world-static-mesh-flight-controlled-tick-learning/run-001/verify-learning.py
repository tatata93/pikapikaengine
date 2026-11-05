"""Original learning material structure/source preservation, not Native proof."""
from pathlib import Path
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
def need(ok, text):
    if not ok:
        raise ValueError(text)
def stamp(p):
    b=p.read_bytes()
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
before=(HERE/'learn-index-before.html.txt').read_bytes()
current=(ROOT/'docs/learn/index.html').read_bytes()
old=before.decode('utf-8'); new=current.decode('utf-8')
pattern=r'<article\b[^>]*id="([^"]+)"[\s\S]*?</article>'
old_articles={m[1]:m[0] for m in re.finditer(pattern,old)}
new_articles={m[1]:m[0] for m in re.finditer(pattern,new)}
need(len(old_articles)==25 and len(new_articles)==26,'One new article')
need(set(new_articles)-set(old_articles)=={'controlled-tick'},'Only intended article added')
need(all(new_articles[k]==v for k,v in old_articles.items()),'All old article text bytes unchanged')
toc='<a href="#controlled-tick">一tickの荷重置換</a>'
reversed_new=new.replace(new_articles['controlled-tick'],'',1).replace(toc,'',1).replace('role="status">26項目。','role="status">25項目。',1)
need(reversed_new.encode('utf-8')==before,'Only new article/TOC/initial count changed; generated blocks unchanged')
ids=re.findall(r'\bid="([^"]+)"',new)
need(len(ids)==len(set(ids)),'HTML IDs unique')
article=new_articles['controlled-tick']
links=[]
for attribute,target in re.findall(r'\b(href|src)="([^"]+)"',article):
    if target.startswith('#'):
        need(target[1:] in ids,'Local fragment target exists')
    else:
        p=(ROOT/'docs/learn'/target).resolve()
        need(ROOT in p.parents and p.is_file(),'Existing local new-article link: '+target)
    links.append(target)
svg=ROOT/'docs/learn/diagrams/world-static-mesh-flight-controlled-tick.svg'
tree=ET.fromstring(svg.read_bytes())
need(tree.attrib.get('viewBox')=='0 0 1120 820','Declared original diagram dimensions')
need(not any(k.split('}')[-1]=='href' for n in tree.iter() for k in n.attrib),'No external SVG assets')
guide=(ROOT/'docs/WORLD_STATIC_MESH_FLIGHT_CONTROLLED_TICK.md').read_text(encoding='utf-8')
need('PROTOTYPE_ACCEPTANCE_PENDING' in guide,'Honest pending status')
for target in re.findall(r'\]\(([^)]+)\)',guide):
    if ':' not in target:
        need((ROOT/'docs'/target).resolve().is_file(),'Existing guide link: '+target)
inputs=json.loads((HERE/'inputs.json').read_text(encoding='utf-8'))['inputs']
observed=[]
for rel, saved in inputs.items():
    if rel!='docs/learn/index.html':
        now=stamp(ROOT/rel)
        observed.append({'path':rel,'stable':now==saved,'before':saved,'after':now})
        need(now==saved,'Source-reading input changed: '+rel)
result={'schema':1,'status':'PASS','oldArticlesPreserved':25,'newArticles':1,'articleCount':26,'uniqueIds':len(ids),'newArticleLinks':links,'svgXml':'PASS','svgExternalAssets':0,'onlyArticleTocAndInitialCountChanged':True,'sourceInputsStable':observed,'outputs':{p:stamp(ROOT/p) for p in ['docs/WORLD_STATIC_MESH_FLIGHT_CONTROLLED_TICK.md','docs/learn/diagrams/world-static-mesh-flight-controlled-tick.svg','docs/learn/index.html']},'nativeExecuted':False,'webBuildExecuted':False,'browserVisualVerified':False,'scope':'HTML structure, exact old article preservation, local links and original SVG XML only. No Native/model, rendering or public acceptance.'}
with (HERE/'learning-verification.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(result,f,ensure_ascii=False,indent=2); f.write('\n')
print(json.dumps({'status':'PASS','oldArticlesPreserved':25,'articleCount':26,'sourceInputsStable':True}))
