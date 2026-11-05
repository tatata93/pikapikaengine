#include "pikapika/report_values_wire.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <vector>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
namespace r=pikapika::report_values_wire;
namespace d=pikapika::diagnostic_wire;
namespace c=pikapika::world_static_mesh_flight_controlled_tick;
namespace s=pikapika::world_static_mesh_flight_scheduler;
using namespace pikapika;
namespace {
static_assert(sizeof(std::size_t)==8);
void need(bool b) {if(!b) throw std::runtime_error("report held audits and partition assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
struct Numbers {
    std::size_t n=0;
    double next() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        return std::bit_cast<double>(bits[n++%bits.size()]);
    }
    Vec3 vec() {return {next(),next(),next()};}
    dynamics::Material material() {return {next(),next()};}
};
namespace h=pikapika::sphere_triangle_mesh_held_load;
struct Builder {
    unsigned next=0;
    interval::Interval bound() {
        constexpr std::array<std::array<std::uint64_t,2>,8> bits{{
            {0,0},{0x8000000000000001ull,1},{1,0x0010000000000000ull},
            {0xffefffffffffffffull,0x7fefffffffffffffull},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0xfff0000000000000ull,0xbff0000000000000ull},{0x3ff0000000000000ull,0x7ff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff8000000000000ull}}};
        const auto pair=bits[next++%bits.size()];return {std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1])};
    }
    h::Bounds3 bounds() {return {bound(),bound(),bound()};}
};
struct HeldAudits {
    std::vector<h::CellAudit> audits;
    std::vector<h::PartitionLeaf> partition;
    HeldAudits() {
        Builder b;Numbers f;
        for(unsigned j=0;j<14;++j) {
            const unsigned mask=j==0?0u:j==1?4095u:1u<<(j-2);
            h::CellAudit v;
            v.kind=static_cast<h::AuditKind>(j?UINT32_MAX-j:0);v.cell={{f.next(),f.next()},j?UINT32_MAX-j:0};v.time=f.next();
            v.outcome=static_cast<h::Outcome>(0x80000000u+j);v.mesh_queried=j%2!=0;
            if(mask&1u) v.path_bounds=b.bounds();
            if(mask&2u) v.point_bounds=b.bounds();
            if(mask&4u) v.anchor=f.vec();
            if(mask&8u) v.mesh_status=static_cast<sphere_triangle_mesh::Status>(UINT32_MAX-j);
            if(mask&16u) v.mesh_reason=static_cast<sphere_triangle_mesh::Reason>(0x80000000u+j);
            if(mask&32u) v.distance=b.bound();
            if(mask&64u) v.displacement_squared_bound=b.bound();
            if(mask&128u) v.error_squared_bound=b.bound();
            if(mask&256u) v.displacement_root=b.bound();
            if(mask&512u) v.error_root=b.bound();
            if(mask&1024u) v.clearance_certificate=b.bound();
            if(mask&2048u) v.penetration_certificate=b.bound();
            v.work={j,UINT64_MAX-j,9007199254740993ull+j,0x8000000000000000ull+j,100u+j,200u+j,300u+j,400u+j,500u+j,600u+j,j%2==0};
            audits.push_back(v);
        }
        for(unsigned j=0;j<4;++j) {
            h::PartitionLeaf v;v.cell={{f.next(),f.next()},j?UINT32_MAX-j:0};
            v.state=static_cast<h::LeafState>(j?UINT32_MAX-j:0);v.blocked_reason=static_cast<h::Reason>(0x80000000u+j);
            if(j) v.audit_index=j==1?0:j==2?9007199254740993ull:UINT64_MAX;
            partition.push_back(v);
        }
        need(b.next==26 && f.n==56);
    }
};
void fixture(d::Writer& w,const HeldAudits& v) {
    ok(w.begin(0x52484131));ok(w.array());
    for(const auto& value:v.audits) {ok(r::write(w,value));}
    for(const auto& value:v.partition) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const HeldAudits* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.audits[c.calls%14])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.partition[c.calls%4])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    HeldAudits v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && std::equal(x.data.begin(),x.data.end(),base.data.begin()));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==2*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);

    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":22,\"fixtureRecords\":18,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":18,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            HeldAudits values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
