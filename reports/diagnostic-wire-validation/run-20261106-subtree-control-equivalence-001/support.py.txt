"""Exact scoped comparison for grammar-valid mutations; keep original context/depth.

The complete original document MUST already equal the independent specification.
Outside the declared node every byte must remain identical. Original ancestor
depth is reproduced with present wrappers. All scoped baselines are decoded and
compared first. This does not discard any mutation; optional whole-document dual
decodes audit the equivalence. No model or production decoder is used.
"""
class SubtreeControls:
    def __init__(self,wire,data,expected,spans):
        self.wire=wire;self.data=data;self.expected=expected;self.spans=spans
        self.checked={};self.scoped=0;self.whole=0;self.dual=0
    def need(self,v,m):
        if not v:raise ValueError(m)
    def encloser(self,start,end):
        choices=[(b-a,path) for path,(a,b,_,_) in self.spans.items() if a<=start and end<=b]
        self.need(bool(choices),'Actual enclosing node');return min(choices)[1]
    def differs(self,changed,scope='',dual=False):
        if not scope:
            self.whole+=1
            return not self.wire.typed_equal(self.wire.decode(changed),self.expected)
        start,end,node,depth=self.spans[scope];delta=len(changed)-len(self.data)
        self.need(changed[:start]==self.data[:start] and changed[end+delta:]==self.data[end:] and end+delta>=start,'Every byte outside scoped replacement exact')
        before=b'\x0c'*depth;after=b'\x0e'*depth+b'\0';wrapped=node
        for _ in range(depth):wrapped=('present',wrapped)
        expected=(self.expected[0],wrapped)
        if scope not in self.checked:
            original=self.data[:12]+before+self.data[start:end]+after
            self.need(self.wire.typed_equal(self.wire.decode(original),expected),'Scoped baseline must equal independently indexed node at original depth')
            self.checked[scope]=True
        decoded=self.wire.decode(self.data[:12]+before+changed[start:end+delta]+after)
        different=not self.wire.typed_equal(decoded,expected);self.scoped+=1
        if dual:
            whole=not self.wire.typed_equal(self.wire.decode(changed),self.expected)
            self.need(different==whole,'Scoped and whole exact typed comparisons disagree');self.dual+=1
        return different
    def receipt(self):
        return dict(scopedComparisons=self.scoped,wholeComparisons=self.whole,wholeDocumentDualComparisons=self.dual,independentScopedBaselinesChecked=len(self.checked),outsideScopeWholeBytesCompared=True,originalAncestorDepthReproduced=True,mutationsDropped=False)
