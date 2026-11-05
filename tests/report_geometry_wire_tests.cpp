#include "pikapika/report_values_wire.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
namespace r=pikapika::report_values_wire;
namespace d=pikapika::diagnostic_wire;
using namespace pikapika;
namespace {
static_assert(sizeof(std::size_t)==8 && sizeof(unsigned)==4);
void need(bool b) {if(!b) throw std::runtime_error("report geometry assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace i=pikapika::interval;
namespace st=pikapika::sphere_triangle;
struct Builder {
    unsigned next=0;
    i::Interval bound() {
        constexpr std::array<std::array<std::uint64_t,2>,8> bits{{
            {0,0},{0x8000000000000001ull,1},{1,0x0010000000000000ull},
            {0xffefffffffffffffull,0x7fefffffffffffffull},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0xfff0000000000000ull,0xbff0000000000000ull},{0x3ff0000000000000ull,0x7ff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff8000000000000ull}}};
        const auto pair=bits[next++%bits.size()];return {std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1])};
    }
    st::Bounds3 bounds() {return {bound(),bound(),bound()};}
};
struct GeometryValues {
    st::CandidateAudit first,second;
    st::Geometry geometry,other;
    GeometryValues() {
        Builder b;
        first={st::Feature::vertex_c,st::Disposition::kkt_violated,b.bounds(),{b.bound(),b.bound()},0};
        second={static_cast<st::Feature>(UINT32_MAX),static_cast<st::Disposition>(0x80000001u),b.bounds(),{b.bound(),b.bound()},UINT32_MAX};
        geometry.surface_id=UINT64_MAX;geometry.surviving_features=UINT32_MAX;
        geometry.barycentric=b.bounds();geometry.closest_local=b.bounds();geometry.closest=b.bounds();geometry.delta=b.bounds();
        geometry.normal=b.bounds();geometry.sphere_point=b.bounds();geometry.squared_distance=b.bound();geometry.distance=b.bound();geometry.gap=b.bound();
        geometry.relation=static_cast<st::Relation>(UINT32_MAX);
        other=geometry;other.surface_id=9007199254740993ull;other.surviving_features=0;other.normal=b.bounds();other.distance=b.bound();other.relation=st::Relation::boundary_unresolved;
        need(b.next==35);
    }
};
void fixture(d::Writer& w,const GeometryValues& v) {
    ok(w.begin(0x52475431));ok(w.array());
    ok(r::write(w,v.first));ok(r::write(w,v.second));ok(r::write(w,v.geometry));ok(r::write(w,v.other));
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const GeometryValues* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.first)==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.geometry)==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);i::require_environment();
    GeometryValues v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":17,\"fixtureRecords\":4,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":4,\"actualGeometryQueries\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            GeometryValues values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
