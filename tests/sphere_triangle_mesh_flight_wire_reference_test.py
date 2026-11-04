"""Synthetic codec tests. These do NOT execute or claim Native/WASM exchange."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('flight_wire',ROOT/'scripts/verify-sphere-triangle-mesh-flight-native-sdk.py')
wire=importlib.util.module_from_spec(spec);spec.loader.exec_module(wire)
FILES=[('held',0,'reports/sphere-triangle-mesh-held-load-checks/run-20261104-002/native-fixtures.json'),
       ('guard',1,'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-002/native-fixtures.json'),
       ('supplemental',1,'reports/sphere-triangle-mesh-free-flight-guard-checks/run-20261104-002/supplemental-fixtures.json')]


def synthetic(corpus):
    rows=[];prior=[];accepted=0
    for cohort,f,mode in corpus:
        source=f['input'];begin,appends,status,phase=wire.host_path(source,mode)
        q=wire.query_values(source,mode);tri=wire.source_values(source)
        r={'cohort':cohort,'name':f['name'],'mode':mode,'input':q,'inputBits':list(map(wire.bits,q)),
           'triangles':tri,'triangleBits':[list(map(wire.bits,t)) for t in tri],
           'beginStatus':begin,'appendStatuses':appends,'exchangeStatus':status,'failedPhase':phase,
           'hostFailurePreserved':True if phase else None,'summary':None,'summaryBits':None,'packets':[],
           'lastMeshSummary':None,'lastMeshSummaryBits':None,'lastMeshRows':[],
           'outputBefore':prior,'outputBeforeBits':list(map(wire.bits,prior)),
           'outputAfter':prior,'outputAfterBits':list(map(wire.bits,prior))}
        if not phase:
            accepted+=1;s,ps,ms,mr=wire.expected_wire(source,mode,f['result'])
            r.update(summary=s,summaryBits=list(map(wire.bits,s)),packets=ps,lastMeshSummary=ms,
                     lastMeshSummaryBits=None if ms is None else list(map(wire.bits,ms)),lastMeshRows=mr)
            last=ps[-1]['values'] if ps else s
            if ms is not None:last=ms
            for row in mr:
                if row['packet'] is not None:last=row['packet']
                if row['candidates']:last=row['candidates'][-1]
            r['outputAfter']=last;r['outputAfterBits']=list(map(wire.bits,last));prior=last
        rows.append(r)
    return {'schema':1,'kind':'sphere-triangle-mesh-flight-sdk-packets','fixtureCount':len(rows),
            'accepted':accepted,'hostRejected':len(rows)-accepted,'fixtures':rows}


class SyntheticCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=[]
        for cohort,mode,name in FILES:
            data=wire.held.load(ROOT/name)
            cls.corpus.extend((cohort,f,mode) for f in data['fixtures'])

    def test_independent_decode_all_frozen_pure_fields(self):
        # Synthetic encoding ONLY tests layout/decoder against pure observables.
        # It is intentionally separate from actual probe/WASM provenance.
        for cohort,f,mode in self.corpus:
            if wire.host_path(f['input'],mode)[3] is not None:continue
            raw=synthetic([(cohort,f,mode)])['fixtures'][0]
            source,result=wire.decode(raw)
            wire.Compare().equal(source,f['input'],'synthetic decoded input')
            wire.Compare().equal(result,f['result'],'synthetic decoded pure result')
        report,models=wire.verify_packets(self.corpus,synthetic(self.corpus))
        self.assertEqual(report['fixtureCount'],183)
        self.assertEqual(report['accepted'],len(models))
        self.assertGreater(report['hostRejected'],0)

    def test_record_padding_corruption(self):
        item=next(x for x in self.corpus if wire.host_path(x[1]['input'],x[2])[3] is None)
        raw=synthetic([item])['fixtures'][0]
        p=next(p for p in raw['packets'] if p['kind']==3);p['values'][47]=-0.;p['bits'][47]=wire.bits(-0.)
        with self.assertRaises(AssertionError):wire.decode(raw)

    def test_missing_and_duplicate_packet_rejected(self):
        item=next(x for x in self.corpus if wire.host_path(x[1]['input'],x[2])[3] is None)
        for duplicate in [False,True]:
            raw=synthetic([item])['fixtures'][0]
            if duplicate:raw['packets'].append(copy.deepcopy(raw['packets'][-1]))
            else:raw['packets'].pop()
            with self.assertRaises(AssertionError):wire.decode(raw)

    def test_body_layout_keeps_all_native_fields(self):
        item=next(x for x in self.corpus if x[2]==1 and x[1]['result']['candidate'] is not None and any(x[1]['input']['body']['torque']))
        b=item[1]['input']['body'];decoded=wire.body_decode(wire.body_values(b))
        wire.Compare().equal(decoded,b,'body28 complete')
        self.assertNotIn('time',decoded);self.assertNotIn('angularVelocity',decoded)

    def test_original_minus_zero_metadata_canonicalizes_only_typed_input(self):
        item=next(x for x in self.corpus if x[2]==1 and x[1]['result']['candidate'] is not None)
        values=wire.query_values(item[1]['input'],1);values[1]=-0.;values[42]=-0.
        decoded=wire.input_decode(values,1,item[1]['input']['triangles'],raw=True)
        self.assertIs(decoded['body']['isStatic'],False);self.assertEqual(decoded['settings']['heldLoad']['maxDepth'],0)
        self.assertEqual(wire.bits(values[1]),'8000000000000000')
        with self.assertRaises(AssertionError):wire.input_decode(values,1,item[1]['input']['triangles'])

    def test_host_rejects_never_have_fabricated_model(self):
        item=next(x for x in self.corpus if wire.host_path(x[1]['input'],x[2])[3] is not None)
        raw=synthetic([item]);report,models=wire.verify_packets([item],raw)
        self.assertEqual(report['accepted'],0);self.assertEqual(models,[])
        raw['fixtures'][0]['summary']=[0]*24;raw['fixtures'][0]['summaryBits']=[wire.bits(0)]*24
        with self.assertRaises(AssertionError):wire.verify_packets([item],raw)


if __name__=='__main__':
    wire.need(__debug__,'run synthetic wire tests without Python -O')
    unittest.main()
