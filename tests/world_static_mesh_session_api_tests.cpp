#include "pikapika/world_static_mesh_session_api.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string_view>
#include <vector>
extern "C" std::uint32_t pp_ws_c_header_smoke(void);
namespace {
void need(bool v,const char* message) {if(!v) {throw std::runtime_error(message);}}
using Context=std::unique_ptr<pp_ws_context,decltype(&pp_ws_context_delete)>;
Context context(std::uint32_t limit=0xffffffffU,std::uint32_t high=0x1fffffU) {Context c(pp_ws_context_create(limit,high),pp_ws_context_delete);need(bool(c),"Actual context create");return c;}
struct Input {std::vector<double> f;std::vector<std::uint32_t> w;};
Input input(unsigned bodies,unsigned planes) {
    Input a{{-0.,-9.,0.,.25,-0.,1./120.},{bodies,planes,4,0xffffffffU,0xffffffffU}};
    for(unsigned i=0;i<bodies;++i) {
        const double k=static_cast<double>(i)/16.;
        const std::array<double,26> f{2+k,.5+k,11+k,12+k,13+k,21+k,22+k,-0.,31+k,32+k,33+k,34+k,41+k,42+k,43+k,51+k,52+k,53+k,61+k,-0.,63+k,71+k,72+k,73+k,81+k,91+k};
        a.f.insert(a.f.end(),f.begin(),f.end());
        // Full64 max, zero and descending/duplicate raw IDs remain data.
        a.w.insert(a.w.end(),{i==0?0xffffffffU:i==1?0U:1000U-3*i,i==0?0xffffffffU:0U,i%2});
    }
    if(bodies) {a.f[24]=std::numeric_limits<double>::denorm_min();}
    for(unsigned i=0;i<planes;++i) {
        a.f.insert(a.f.end(),{-0.,1.,0.,i==0?-0.:static_cast<double>(i)/8.,.5,.25});a.w.insert(a.w.end(),{i+1,0});
    }
    return a;
}
pp_ws_result stage(pp_ws_context* c,const Input& a) {
    std::copy(a.f.begin(),a.f.end(),pp_ws_input_f64(c));std::copy(a.w.begin(),a.w.end(),pp_ws_input_u32(c));
    return pp_ws_stage(c,static_cast<std::uint32_t>(a.f.size()),static_cast<std::uint32_t>(a.w.size()));
}
pp_ws_result make(pp_ws_context* c,pp_ws_result s) {return pp_ws_create(c,s.revision[0],s.revision[1]);}
pp_ws_result read(pp_ws_context* c,pp_ws_result t) {return pp_ws_read(c,t.token[0],t.token[1],t.token[2]);}
pp_ws_result destroy(pp_ws_context* c,pp_ws_result t) {return pp_ws_destroy(c,t.token[0],t.token[1],t.token[2]);}
pp_ws_result reset(pp_ws_context* c,pp_ws_result s,pp_ws_result t) {return pp_ws_reset(c,s.revision[0],s.revision[1],t.token[0],t.token[1],t.token[2]);}
std::uint64_t bits(double v) {return std::bit_cast<std::uint64_t>(v);}
void equal(pp_ws_context* c,const Input& a) {
    const auto info=pp_ws_snapshot_info_get(c);need(info.available==1&&info.float_count==a.f.size()&&info.word_count==a.w.size(),"Exact whole read counts");
    for(std::size_t i=0;i<a.f.size();++i) {need(bits(pp_ws_snapshot_f64(c)[i])==bits(a.f[i]),"Read F64 mapped bit/order");}
    for(std::size_t i=0;i<a.w.size();++i) {need(pp_ws_snapshot_u32(c)[i]==a.w[i],"Read U32 full64 field/order");}
    need(bits(info.backlog)==0&&info.sequence[0]==0&&info.sequence[1]==0,"Unpumped clock metadata");
}
void lifecycle() {
    need(pp_ws_c_header_smoke()==0,"Actual separately compiled C caller");
    need(!pp_ws_context_create(0,0)&&!pp_ws_context_create(0,0x200000U),"Invalid context generation limits");
    pp_ws_context_delete(nullptr);need(pp_ws_stage(nullptr,0,0).host==PP_WS_NULL_CONTEXT&&pp_ws_read(nullptr,0,1,0).host==PP_WS_NULL_CONTEXT,"Null host gates");
    need(!pp_ws_input_f64(nullptr)&&!pp_ws_input_u32(nullptr)&&!pp_ws_snapshot_f64(nullptr)&&!pp_ws_snapshot_u32(nullptr)&&pp_ws_snapshot_info_get(nullptr).available==0,"Null buffer/info views");
    auto c=context();need(pp_ws_snapshot_info_get(c.get()).available==0,"No invented initial read");need(pp_ws_create(c.get(),1,0).host==PP_WS_NO_SOURCE,"No implicit source");
    const auto original=input(8,16);const auto s=stage(c.get(),original);need(s.host==0&&s.revision[0]==1&&s.revision[1]==0,"First explicit source revision");
    pp_ws_input_f64(c.get())[11]=999.;pp_ws_input_u32(c.get())[5]=123;
    auto t=make(c.get(),s);need(t.host==0&&t.token[0]==0&&t.token[1]==1,"Create owned copied source");need(read(c.get(),t).host==0,"Actual read");equal(c.get(),original);
    need(pp_ws_stage(c.get(),513,257).host==PP_WS_INPUT_COUNT&&make(c.get(),s).host==PP_WS_NO_SOURCE,"Failed count stage invalidates old source");equal(c.get(),original);
    auto invalid=input(1,0);invalid.f[0]=std::numeric_limits<double>::infinity();auto bad=stage(c.get(),invalid);
    need(bad.host==PP_WS_SOURCE_REJECTED&&bad.source==PP_WS_SOURCE_NONFINITE&&bad.index==0&&bad.owner==PP_WS_NOT_CALLED,"Source failure has no owner call");
    need(make(c.get(),s).host==PP_WS_NO_SOURCE&&read(c.get(),t).host==0,"Source failure preserves active owner");equal(c.get(),original);
    auto next=input(2,1);next.f[11]=-321.;auto s2=stage(c.get(),next);need(s2.revision[0]==2&&make(c.get(),s).host==PP_WS_SOURCE_REVISION,"Old explicit source revision refused");
    auto fresh=reset(c.get(),s2,t);need(fresh.host==0&&fresh.token[1]==2,"Reset publishes next owner generation");equal(c.get(),original);
    auto stale=read(c.get(),t);need(stale.host==PP_WS_OWNER_REJECTED&&stale.owner==PP_WS_OWNER_STALE,"Old owner generation refused");equal(c.get(),original);
    need(read(c.get(),fresh).host==0,"Read replacement owner");equal(c.get(),next);
    auto invalid_clock=next;invalid_clock.f[5]=0;const auto sc=stage(c.get(),invalid_clock);need(sc.host==0,"Raw clock data stage admission");auto denied=reset(c.get(),sc,fresh);
    need(denied.host==PP_WS_OWNER_REJECTED&&denied.owner==PP_WS_OWNER_SETTINGS,"Owner rejection separate from source admission");need(read(c.get(),fresh).host==0,"Invalid reset preserves owner generation");equal(c.get(),next);
    auto token_bad=pp_ws_read(c.get(),4,1,0);need(token_bad.host==PP_WS_TOKEN_REJECTED&&token_bad.owner==PP_WS_NOT_CALLED,"Invalid token syntax no owner");
    need(pp_ws_read(c.get(),0,0,0).host==PP_WS_TOKEN_REJECTED&&pp_ws_read(c.get(),0,1,0x200000U).host==PP_WS_TOKEN_REJECTED,"Zero/wide generation refused");equal(c.get(),next);
    need(destroy(c.get(),fresh).host==0,"Destroy owner");equal(c.get(),next);
    need(read(c.get(),fresh).host==PP_WS_OWNER_REJECTED,"Destroyed owner not alive");equal(c.get(),next);
    std::vector<double> owned_f(pp_ws_snapshot_f64(c.get()),pp_ws_snapshot_f64(c.get())+next.f.size());std::vector<std::uint32_t> owned_w(pp_ws_snapshot_u32(c.get()),pp_ws_snapshot_u32(c.get())+next.w.size());c.reset();
    for(std::size_t i=0;i<owned_f.size();++i) {need(bits(owned_f[i])==bits(next.f[i]),"Caller owned read after context deletion");}need(owned_w==next.w,"Caller owned words after context deletion");
    c=context(2,0);s2=stage(c.get(),input(0,0));std::array<pp_ws_result,4> tokens{};
    for(unsigned i=0;i<4;++i) {tokens[i]=make(c.get(),s2);need(tokens[i].host==0&&tokens[i].token[0]==i,"Independent slots");}
    need(make(c.get(),s2).owner==PP_WS_OWNER_FULL,"Full registry");auto renewed=reset(c.get(),s2,tokens[0]);need(renewed.host==0&&renewed.token[1]==2,"Last configured generation");
    need(reset(c.get(),s2,renewed).owner==PP_WS_OWNER_RETIRED,"Retirement boundary no wrap");need(destroy(c.get(),renewed).host==0&&make(c.get(),s2).owner==PP_WS_OWNER_FULL,"Retired slot cannot be reused");
    need(destroy(c.get(),tokens[1]).host==0,"Destroy second slot");auto reused=make(c.get(),s2);need(reused.host==0&&reused.token[0]==1&&reused.token[1]==2,"Other reusable slot increments");
    need(read(c.get(),tokens[1]).owner==PP_WS_OWNER_STALE&&read(c.get(),tokens[2]).host==0,"Same generation other slot remains live");
    auto independent=context();need(read(independent.get(),tokens[2]).owner==PP_WS_OWNER_STALE,"Token not an authentication capability across contexts");
    const auto before=std::fegetround();need(before==FE_TONEAREST&&std::fesetround(FE_UPWARD)==0,"Actual upward environment");auto env=stage(c.get(),input(0,0));need(std::fesetround(before)==0,"Restore environment");need(env.host==PP_WS_SOURCE_REJECTED&&env.source==PP_WS_SOURCE_ENVIRONMENT,"Environment admission refusal");
}
template<class V> void numbers(const V& values) {std::cout<<'[';bool comma=false;for(const auto v:values) {if(comma) {std::cout<<',';}comma=true;std::cout<<v;}std::cout<<']';}
void fixtures() {
    std::cout<<"{\"schema\":1,\"kind\":\"native-session-c-api-read\",\"rows\":[";bool comma=false;
    for(unsigned b=0;b<=8;++b) {
        const auto a=input(b,b==8?16:b);auto c=context();const auto s=stage(c.get(),a);const auto t=make(c.get(),s);need(s.host==0&&t.host==0&&read(c.get(),t).host==0,"Fixture actual C ABI lifecycle");equal(c.get(),a);
        const auto info=pp_ws_snapshot_info_get(c.get());std::vector<std::uint64_t> in,out;for(auto f:a.f) {in.push_back(bits(f));}for(std::size_t i=0;i<a.f.size();++i) {out.push_back(bits(pp_ws_snapshot_f64(c.get())[i]));}
        if(comma) {std::cout<<',';}comma=true;std::cout<<"{\"bodies\":"<<b<<",\"planes\":"<<a.w[1]<<",\"inputFloatBits\":";numbers(in);std::cout<<",\"inputWords\":";numbers(a.w);std::cout<<",\"readFloatBits\":";numbers(out);std::cout<<",\"readWords\":";numbers(std::vector<std::uint32_t>(pp_ws_snapshot_u32(c.get()),pp_ws_snapshot_u32(c.get())+info.word_count));std::cout<<",\"token\":";numbers(info.token);std::cout<<",\"sequence\":";numbers(info.sequence);std::cout<<",\"backlogBits\":"<<bits(info.backlog)<<'}';
    }
    std::cout<<"],\"actualRows\":9}\n";
}
}
int main(int argc,char** argv) {
    try {need(argc==2,"Use --run or --fixtures");lifecycle();if(std::string_view(argv[1])=="--fixtures") {fixtures();}else {need(std::string_view(argv[1])=="--run","Unknown mode");std::cout<<"Native C caller; explicit staging; owned 8body/16plane reads; invalidation; lifecycle/retirement/environment PASS\n";}return 0;}
    catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
