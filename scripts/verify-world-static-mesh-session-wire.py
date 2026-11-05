"""Independent integer reference for actual bounded session token wire fixtures."""
from collections import Counter
from pathlib import Path
import argparse
import json
import sys

if not __debug__:raise RuntimeError('Token wire verification requires normal Python; -O is refused')
MAX32=2**32-1
MAX64=2**64-1
MAXGEN=2**53-1
KNOWN=[1,2**32-1,2**32,2**32+1,2**52,MAXGEN]
BAD=[[],[0],[0,1],[0,1,0,0],[0,1,0,0,0],[0,1,0,0,0,0],
     [4,1,0],[MAX32,1,0],[0,0,0],[3,0,0],[0,1,2**21],[1,42,MAX32],[99,0,2**21]]


def need(ok,message):
    if not ok:raise ValueError(message)


def fields(value,keys):need(type(value) is dict and set(value)==set(keys),'Exact complete object fields')
def uint(value,limit):need(type(value) is int and 0<=value<=limit,'Exact unsigned integer type/range')
def token(value):
    fields(value,['slot','generation']);uint(value['slot'],MAX32);uint(value['generation'],MAX64)
def words(value,count=None):
    need(type(value) is list and len(value)<=32 and (count is None or len(value)==count),'Bounded integer word array')
    for word in value:uint(word,MAX32)


def verify(data):
    fields(data,['schema','kind','tokenVersion','rows','actualRows']);need(type(data['schema']) is int and data['schema']==1 and data['kind']=='world-static-mesh-session-token-wire-fixtures','Known exact wire envelope')
    uint(data['tokenVersion'],1);need(data['tokenVersion']==1,'Known token version');need(type(data['rows']) is list and len(data['rows'])==77,'Complete77 integer-wire rows, not World histories');uint(data['actualRows'],77);need(data['actualRows']==77,'Actual bounded row count')
    encoded=[];decoded=[];counts=Counter();success=0
    for row in data['rows']:
        fields(row,['kind','input','prior','status','output']);uint(row['status'],4)
        if row['kind']=='encode':
            token(row['input']);words(row['prior'],3);words(row['output'],3);slot=row['input']['slot'];generation=row['input']['generation'];encoded.append((slot,generation))
            status=2 if slot>=4 else 4 if generation>MAXGEN else 3 if generation==0 else 0
            high,low=divmod(generation,2**32);expected=[slot,low,high] if status==0 else row['prior']
        else:
            need(row['kind']=='decode','Known operation');words(row['input']);token(row['prior']);token(row['output']);decoded.append(tuple(row['input']))
            status=1 if len(row['input'])!=3 else 2 if row['input'][0]>=4 else 0
            if status==0:
                generation=row['input'][1]+row['input'][2]*2**32
                status=4 if generation>MAXGEN else 3 if generation==0 else 0
            expected={'slot':row['input'][0],'generation':generation} if status==0 else row['prior']
        need(row['status']==status and row['output']==expected,'Independent divmod/integer-sum result or whole output retention')
        counts[status]+=1;success+=int(status==0)
    expected_encode=[(s,g) for s in range(4) for g in KNOWN]+[(s,g) for s in [0,3,4,MAX32] for g in [0,1,2**53,MAX64]]
    expected_decode=[(s,g%(2**32),g//(2**32)) for s in range(4) for g in KNOWN]+[tuple(x) for x in BAD]
    need(Counter(encoded)==Counter(expected_encode) and Counter(decoded)==Counter(expected_decode),'Complete authored integer boundaries, widths and invalid-count corpus')
    need(counts=={0:50,1:6,2:11,3:4,4:6},'All five status boundaries independently counted')
    return {'status':'PASS','rows':77,'encoded':len(encoded),'decoded':len(decoded),'successful':success,'refused':77-success,'statusCounts':dict(counts),'maximumGeneration':MAXGEN,
            'scope':'Actual integer syntax/bit-width/retained-output wire only. No live Registry/session authorization, C ABI, JS, WASM, allocator or numerical model acceptance.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('fixture',type=Path);args=parser.parse_args();need(args.fixture.stat().st_size<=131072,'Bounded wire document')
    with args.fixture.open(encoding='utf8') as stream:data=json.load(stream,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    print(json.dumps(verify(data)))
