#include "pikapika/world_static_mesh_session_packet_wire.hpp"
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
namespace {
namespace w=pikapika::world_static_mesh_session_packet_wire;
void need(bool v,const char* m) {if(!v) {throw std::runtime_error(m);}}
std::uint64_t bits(double v) {return std::bit_cast<std::uint64_t>(v);}
struct Case {std::string name;std::vector<double> f;std::vector<std::uint32_t> u;int rounding=FE_TONEAREST;};
Case base(std::string name,unsigned packets,unsigned loads) {
    Case c{std::move(name),{},{packets}};
    for(unsigned i=0;i<packets;++i) {
        c.u.insert(c.u.end(),{0,0xffffffffU-i,0xffffffffU,loads});
        for(unsigned j=0;j<loads;++j) {
            c.u.insert(c.u.end(),{j==0?0xffffffffU:j==1?0U:1000U-j,j==0?0xffffffffU:0U});
            const double k=static_cast<double>(i*8+j)/16.;c.f.insert(c.f.end(),{1+k,-0.,3+k,4+k,5+k,-0.});
        }
    }
    return c;
}
std::vector<Case> cases() {
    std::vector<Case> out{base("empty",0,0),base("one-empty",1,0),base("one-load",1,1),base("maximum",8,8),base("all-empty",8,0)};
    auto c=base("raw-mode-full32",1,2);c.u[1]=0xffffffffU;out.push_back(c);
    c=base("duplicate-raw-id",1,2);c.u[7]=c.u[5];c.u[8]=c.u[6];out.push_back(c);
    c=base("finite-extremes",1,1);c.f[0]=std::numeric_limits<double>::denorm_min();c.f[2]=std::numeric_limits<double>::max();c.f[3]=-std::numeric_limits<double>::max();c.f[4]=-std::numeric_limits<double>::denorm_min();out.push_back(c);
    for(const auto& mode:std::array<std::pair<const char*,int>,3>{{{"upward",FE_UPWARD},{"downward",FE_DOWNWARD},{"toward-zero",FE_TOWARDZERO}}}) {c=base(mode.first,2,2);c.rounding=mode.second;c.f[0]=std::numeric_limits<double>::denorm_min();c.f[2]=std::numeric_limits<double>::max();c.f[3]=-std::numeric_limits<double>::max();c.f[4]=-std::numeric_limits<double>::denorm_min();out.push_back(c);}
    c=base("missing-count",0,0);c.u.clear();out.push_back(c);
    c=base("too-many-packets",0,0);c.u[0]=9;out.push_back(c);
    c=base("wide-packet-count",0,0);c.u[0]=0xffffffffU;out.push_back(c);
    c=base("too-many-words",8,8);c.u.push_back(0);out.push_back(c);
    c=base("short-packet-header",1,0);c.u.pop_back();out.push_back(c);
    c=base("missing-id-high",1,1);c.u.pop_back();out.push_back(c);
    c=base("extra-word",1,1);c.u.push_back(0);out.push_back(c);
    c=base("too-many-loads",1,0);c.u[4]=9;out.push_back(c);
    c=base("wide-load-count",1,0);c.u[4]=0xffffffffU;out.push_back(c);
    c=base("short-floats",1,1);c.f.pop_back();out.push_back(c);
    c=base("extra-float",1,1);c.f.push_back(0);out.push_back(c);
    c=base("nonfinite-first-force",1,1);c.f[0]=std::numeric_limits<double>::infinity();out.push_back(c);
    c=base("nonfinite-last-torque",2,2);c.f.back()=std::bit_cast<double>(0x7ff8000000001234ULL);out.push_back(c);
    return out;
}
template<class V> void numbers(const V& v) {std::cout<<'[';bool comma=false;for(const auto n:v) {if(comma) {std::cout<<',';}comma=true;std::cout<<n;}std::cout<<']';}
void optional(std::optional<std::size_t> v) {if(v) {std::cout<<*v;}else {std::cout<<"null";}}
const char* rounding_name(int m) {if(m==FE_UPWARD) {return "upward";}if(m==FE_DOWNWARD) {return "downward";}if(m==FE_TOWARDZERO) {return "toward-zero";}return "nearest";}
void lifetime() {
    auto c=base("owned",2,2);const auto expected=bits(c.f[0]);auto result=w::decode(c.f,c.u);need(result.status==w::Status::ok&&result.packets&&result.packets->size()==2,"Actual packet admission");
    c.f[0]=999;c.u[2]=1;c.f.clear();c.u.clear();auto copied=result;auto moved=std::move(result);result.packets.reset();
    moved.packets->at(0).loads[0].force_newtons.x=-321;need(bits(copied.packets->at(0).loads[0].force_newtons.x)==expected&&copied.packets->at(0).expected_tick==std::numeric_limits<std::uint64_t>::max(),"Copied packets alias caller or moved result");moved.packets.reset();
    need(copied.packets->at(0).loads[0].body_id==std::numeric_limits<std::uint64_t>::max()&&bits(copied.packets->at(0).loads[0].force_newtons.y)==(std::uint64_t{1}<<63),"Owned full64 ID or negative zero lost");
}
void fixtures() {
    std::cout<<"{\"schema\":1,\"kind\":\"session-packet-wire-fixtures\",\"version\":1,\"rows\":[";bool comma=false;
    for(const auto& c:cases()) {
        const auto prior=std::fegetround();need(prior==FE_TONEAREST&&std::fesetround(c.rounding)==0,"Actual FPU fixture mode");const auto observed=std::fegetround();auto r=w::decode(c.f,c.u);const auto after=std::fegetround();need(std::fesetround(prior)==0&&observed==c.rounding&&after==observed,"Restore unchanged observed FPU mode");
        std::vector<std::uint64_t> f;for(auto v:c.f) {f.push_back(bits(v));}
        if(comma) {std::cout<<',';}comma=true;std::cout<<"{\"name\":\""<<c.name<<"\",\"floatBits\":";numbers(f);std::cout<<",\"words\":";numbers(c.u);std::cout<<",\"actualEnvironment\":\""<<rounding_name(observed)<<"\",\"status\":"<<static_cast<unsigned>(r.status)<<",\"packet\":";optional(r.packet);std::cout<<",\"row\":";optional(r.row);std::cout<<",\"component\":";optional(r.component);std::cout<<",\"packets\":";
        if(!r.packets) {std::cout<<"null";}else {
            std::cout<<'[';bool pc=false;for(const auto& p:*r.packets) {
                if(pc) {std::cout<<',';}pc=true;std::cout<<"{\"mode\":"<<static_cast<unsigned>(p.mode)<<",\"expectedTick\":"<<p.expected_tick<<",\"loads\":[";bool lc=false;
                for(const auto& l:p.loads) {if(lc) {std::cout<<',';}lc=true;std::cout<<"{\"bodyId\":"<<l.body_id<<",\"forceBits\":";numbers(std::array<std::uint64_t,3>{bits(l.force_newtons.x),bits(l.force_newtons.y),bits(l.force_newtons.z)});std::cout<<",\"torqueBits\":";numbers(std::array<std::uint64_t,3>{bits(l.torque_newton_meters.x),bits(l.torque_newton_meters.y),bits(l.torque_newton_meters.z)});std::cout<<'}';}std::cout<<"]}";
            }std::cout<<']';
        }std::cout<<'}';
    }
    std::cout<<"],\"actualRows\":24}\n";
}
}
int main(int argc,char** argv) {
    try {need(argc==2,"Use --run or --fixtures");lifetime();if(std::string_view(argv[1])=="--fixtures") {fixtures();}else {need(std::string_view(argv[1])=="--run","Unknown mode");std::cout<<"Owned Native packet vectors survive caller edit, copy/move and source destruction PASS\n";}return 0;}
    catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
