// Normal-only test replacement. Controlled scalar/array global-new failures,
// not OS OOM, aligned/CRT allocation interception or all allocator paths.
#include "pikapika/world_static_mesh_session_api.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <new>
#include <stdexcept>
#include <string_view>
#include <vector>
namespace api_allocation_probe {
struct State {bool active{};long long remaining=-1;std::size_t seen{};void (*callback)() noexcept=nullptr;};
constinit thread_local State state;
void begin(long long fail=-1,void (*callback)() noexcept=nullptr) noexcept {state={true,fail,0,callback};}
std::size_t end() noexcept {state.active=false;state.callback=nullptr;return state.seen;}
void* allocate(std::size_t size) {
    if(state.active) {
        ++state.seen;const auto callback=state.callback;state.callback=nullptr;if(callback) {callback();}
        if(state.remaining==0) {throw std::bad_alloc();}if(state.remaining>0) {--state.remaining;}
    }
    if(void* p=std::malloc(size?size:1)) {return p;}throw std::bad_alloc();
}
}
void* operator new(std::size_t n) {return api_allocation_probe::allocate(n);}
void* operator new[](std::size_t n) {return api_allocation_probe::allocate(n);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}
namespace {
void need(bool v,const char* m) {if(!v) {throw std::runtime_error(m);}}
using Context=std::unique_ptr<pp_ws_context,decltype(&pp_ws_context_delete)>;
std::uint64_t bits(double v) noexcept {return std::bit_cast<std::uint64_t>(v);}
struct Input {std::array<double,310> f{};std::array<std::uint32_t,61> w{};std::uint32_t nf=6,nw=5;};
Input input(unsigned bodies,unsigned planes,double time) {
    Input a;a.f[0]=-0.;a.f[1]=-9.;a.f[3]=time;a.f[4]=-0.;a.f[5]=1./120.;a.w[0]=bodies;a.w[1]=planes;a.w[2]=4;a.w[3]=0xffffffffU;a.w[4]=0xffffffffU;
    for(unsigned i=0;i<bodies;++i) {
        const double k=static_cast<double>(i)/16.;const std::array<double,26> f{2+k,.5+k,11+k,12+k,13+k,21+k,22+k,-0.,31+k,32+k,33+k,34+k,41+k,42+k,43+k,51+k,52+k,53+k,61+k,-0.,63+k,71+k,72+k,73+k,81+k,91+k};
        std::copy(f.begin(),f.end(),a.f.begin()+a.nf);a.nf+=26;a.w[a.nw++]=0xffffffffU-i;a.w[a.nw++]=0xffffffffU;a.w[a.nw++]=i%2;
    }
    for(unsigned i=0;i<planes;++i) {const std::array<double,6> f{-0.,1.,0.,static_cast<double>(i)/8.,.5,.25};std::copy(f.begin(),f.end(),a.f.begin()+a.nf);a.nf+=6;a.w[a.nw++]=i+1;a.w[a.nw++]=0;}
    return a;
}
void exchange(pp_ws_context* c,const Input& a) {std::copy(a.f.begin(),a.f.end(),pp_ws_input_f64(c));std::copy(a.w.begin(),a.w.end(),pp_ws_input_u32(c));}
pp_ws_result stage(pp_ws_context* c,const Input& a) {exchange(c,a);return pp_ws_stage(c,a.nf,a.nw);}
pp_ws_result make(pp_ws_context* c,pp_ws_result s) {return pp_ws_create(c,s.revision[0],s.revision[1]);}
pp_ws_result read(pp_ws_context* c,pp_ws_result t) {return pp_ws_read(c,t.token[0],t.token[1],t.token[2]);}
pp_ws_result reset(pp_ws_context* c,pp_ws_result s,pp_ws_result t) {return pp_ws_reset(c,s.revision[0],s.revision[1],t.token[0],t.token[1],t.token[2]);}
struct Capture {
    pp_ws_snapshot_info info{};std::array<std::uint64_t,310> f{};std::array<std::uint32_t,61> w{};
    explicit Capture(pp_ws_context* c):info(pp_ws_snapshot_info_get(c)) {
        need(info.available==1&&info.float_count<=f.size()&&info.word_count<=w.size(),"Actual bounded cache");
        for(std::size_t i=0;i<info.float_count;++i) {f[i]=bits(pp_ws_snapshot_f64(c)[i]);}std::copy_n(pp_ws_snapshot_u32(c),info.word_count,w.begin());
    }
    bool same(const Capture& b) const noexcept {
        return info.available==b.info.available&&info.float_count==b.info.float_count&&info.word_count==b.info.word_count&&std::equal(std::begin(info.token),std::end(info.token),std::begin(b.info.token))&&std::equal(std::begin(info.sequence),std::end(info.sequence),std::begin(b.info.sequence))&&bits(info.backlog)==bits(b.info.backlog)&&f==b.f&&w==b.w;
    }
    void equals(const Input& a) const {
        need(info.float_count==a.nf&&info.word_count==a.nw,"Exact cache source counts");for(std::size_t i=0;i<a.nf;++i) {need(f[i]==bits(a.f[i]),"Actual cache float bits");}for(std::size_t i=0;i<a.nw;++i) {need(w[i]==a.w[i],"Actual cache full64 words/order");}
    }
};
enum class Operation {stage,create,reset,read};
const char* name(Operation op) {switch(op) {case Operation::stage:return "stage";case Operation::create:return "create";case Operation::reset:return "reset";case Operation::read:return "read";}return "invalid";}
struct Scenario {
    Context c{pp_ws_context_create(0xffffffffU,0x1fffffU),pp_ws_context_delete};Input old=input(1,1,.25),next=input(8,16,.5);pp_ws_result source{},target{},original{};
    explicit Scenario(Operation op) {
        need(bool(c),"Actual setup context");const auto s=stage(c.get(),old);need(s.host==0,"Actual setup old source");target=make(c.get(),s);original=target;need(target.host==0&&read(c.get(),target).host==0,"Actual setup old owner/read");
        if(op==Operation::stage) {source=s;exchange(c.get(),next);}
        else {source=stage(c.get(),next);need(source.host==0,"Actual setup replacement source");if(op==Operation::read) {target=make(c.get(),source);need(target.host==0&&target.token[0]==1,"Actual setup second read target");}}
    }
    pp_ws_result call(Operation op) noexcept {
        switch(op) {case Operation::stage:return pp_ws_stage(c.get(),next.nf,next.nw);case Operation::create:return make(c.get(),source);case Operation::reset:return reset(c.get(),source,target);case Operation::read:return read(c.get(),target);}return {};
    }
};
struct Row {Operation op;std::size_t position{},attempts{};};
std::size_t measure(Operation op) {Scenario s(op);api_allocation_probe::begin();const auto r=s.call(op);const auto n=api_allocation_probe::end();need(r.host==0&&n>0&&n<=32,"Finite actual operation allocation inventory");return n;}
Row inject(Operation op,std::size_t position) {
    Scenario s(op);const Capture before(s.c.get());api_allocation_probe::begin(static_cast<long long>(position));const auto r=s.call(op);const auto attempts=api_allocation_probe::end();
    need(attempts==position+1,"Actual injected allocation position observed");need(before.same(Capture(s.c.get())),"Failed operation changed previous complete cache");
    need(read(s.c.get(),s.original).host==0,"Failed operation damaged original live owner");Capture(s.c.get()).equals(s.old);
    if(op==Operation::stage) {
        need(r.host==PP_WS_SOURCE_REJECTED&&r.source==PP_WS_SOURCE_ALLOCATION&&r.owner==PP_WS_NOT_CALLED,"Actual stage bad_alloc source status");need(make(s.c.get(),s.source).host==PP_WS_NO_SOURCE,"Failed stage left old source reusable");need(read(s.c.get(),s.target).host==0,"Failed stage damaged active owner");Capture(s.c.get()).equals(s.old);
        const auto next=stage(s.c.get(),s.next);need(next.host==0&&next.revision[0]==s.source.revision[0]+1,"Failed stage consumed revision or broke recovery");auto made=make(s.c.get(),next);need(made.host==0&&made.token[0]==1&&made.token[1]==1,"Failed stage published hidden owner");need(read(s.c.get(),made).host==0,"Read recovered stage");Capture(s.c.get()).equals(s.next);
    }else {
        need(r.host==PP_WS_OWNER_REJECTED&&r.owner==PP_WS_OWNER_ALLOCATION,"Actual owner bad_alloc status separated from host/source");
        if(op!=Operation::read) {need(read(s.c.get(),s.target).host==0,"Failed create/reset damaged active owner");Capture(s.c.get()).equals(s.old);}
        const auto retry=s.call(op);need(retry.host==0,"Actual post-failure recovery");const auto token=op==Operation::read?s.target:retry;
        if(op==Operation::create) {need(token.token[0]==1&&token.token[1]==1,"Failed create consumed slot/generation");}
        if(op==Operation::reset) {need(token.token[0]==0&&token.token[1]==2,"Failed reset changed generation");}
        need(read(s.c.get(),token).host==0,"Recovered owned read");Capture(s.c.get()).equals(s.next);
    }
    return {op,position,attempts};
}
struct Callback {pp_ws_context* c{};pp_ws_result source{},target{};std::array<std::uint32_t,5> statuses{};unsigned calls{};};
constinit thread_local Callback callback;
void reenter() noexcept {
    ++callback.calls;auto* c=callback.c;const auto s=callback.source,t=callback.target;
    callback.statuses={pp_ws_stage(c,6,5).host,make(c,s).host,reset(c,s,t).host,read(c,t).host,pp_ws_destroy(c,t.token[0],t.token[1],t.token[2]).host};
    // Happens only at the first allocation, after the source decoder's complete
    // fixed input capture. Later buffer edits must not change staged values.
    pp_ws_input_f64(c)[3]=999.;pp_ws_input_u32(c)[5]=123;
}
void busy(Operation op) {
    Scenario s(op);const Capture before(s.c.get());callback={s.c.get(),s.source,s.target,{},0};api_allocation_probe::begin(-1,reenter);const auto r=s.call(op);const auto n=api_allocation_probe::end();need(r.host==0&&n>0&&callback.calls==1&&std::all_of(callback.statuses.begin(),callback.statuses.end(),[](auto v){return v==PP_WS_BUSY;}),"Actual allocator callback busy gates");
    if(op!=Operation::read) {need(before.same(Capture(s.c.get())),"Non-read callback operation changed previous cache");}
    auto t=op==Operation::read?s.target:r;if(op==Operation::stage) {t=make(s.c.get(),r);need(t.host==0,"Actual captured stage create");}need(read(s.c.get(),t).host==0,"Actual outer callback operation recovery");Capture(s.c.get()).equals(s.next);
}
}
int main(int argc,char** argv) {
    try {
        need(argc==2&&std::string_view(argv[1])=="--run","Use --run");
        api_allocation_probe::begin();auto* baseline=pp_ws_context_create(0xffffffffU,0x1fffffU);const auto context_count=api_allocation_probe::end();need(baseline&&context_count>0&&context_count<=8,"Actual context allocation count");pp_ws_context_delete(baseline);
        for(std::size_t i=0;i<context_count;++i) {api_allocation_probe::begin(static_cast<long long>(i));auto* failed=pp_ws_context_create(0xffffffffU,0x1fffffU);const auto seen=api_allocation_probe::end();need(!failed&&seen==i+1,"Actual context creation allocation refusal");}
        std::vector<Row> rows;std::array<std::size_t,4> counts{};const std::array<Operation,4> ops{Operation::stage,Operation::create,Operation::reset,Operation::read};
        for(std::size_t j=0;j<ops.size();++j) {counts[j]=measure(ops[j]);for(std::size_t i=0;i<counts[j];++i) {rows.push_back(inject(ops[j],i));}busy(ops[j]);}
        Scenario getters(Operation::read);const Capture prior(getters.c.get());api_allocation_probe::begin(0);const auto info=pp_ws_snapshot_info_get(getters.c.get());const auto* f=pp_ws_snapshot_f64(getters.c.get());const auto* w=pp_ws_snapshot_u32(getters.c.get());const auto allocations=api_allocation_probe::end();need(info.available&&f&&w&&allocations==0&&prior.same(Capture(getters.c.get())),"Cache getters allocated or changed state");
        std::cout<<"{\"schema\":1,\"kind\":\"native-session-api-actual-allocation\",\"contextAllocationFailures\":"<<context_count<<",\"operationAllocations\":[";
        for(std::size_t i=0;i<counts.size();++i) {if(i) {std::cout<<',';}std::cout<<counts[i];}
        std::cout<<"],\"rows\":[";bool comma=false;for(const auto& row:rows) {if(comma) {std::cout<<',';}comma=true;std::cout<<"{\"operation\":\""<<name(row.op)<<"\",\"failAfter\":"<<row.position<<",\"actualAttempts\":"<<row.attempts<<",\"wholePreviousCacheRetained\":true,\"activeOwnerRetained\":true,\"recoveryValid\":true}";}
        std::cout<<"],\"allocatorCallbackOuterOperations\":4,\"actualBusyReentryChecks\":20,\"stageInputCapturedBeforeAllocation\":true,\"cachedGetterAllocations\":0,\"normalOnly\":true}\n";return 0;
    }catch(const std::exception& e) {api_allocation_probe::end();std::cerr<<e.what()<<'\n';return 1;}
}
