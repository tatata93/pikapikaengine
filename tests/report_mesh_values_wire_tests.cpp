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
void need(bool b) {if(!b) throw std::runtime_error("report mesh values assertion");}
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
struct ResultValues {
    std::array<st::Result,8> results;
    ResultValues() {
        GeometryValues g;Builder b;
        constexpr std::array<unsigned,8> counts{0,1,2,3,0,2,1,3};
        constexpr std::array<unsigned,8> sizes{0,3,255,256,257,1,16,513};
        for(unsigned j=0;j<8;++j) {
            auto& v=results[j];v.status=static_cast<st::Status>(j==7?UINT32_MAX:j);
            v.reason=static_cast<st::Reason>(0x80000000u+j);
            if(j&1) v.geometry=(j&2)?g.other:g.geometry;
            const auto cross=b.bound(),sine=b.bound();
            if(j&2) v.squared_cross=cross;
            if(j&4) v.sine_squared=sine;
            for(unsigned k=0;k<counts[j];++k) v.candidates.push_back(((j+k)&1)?g.second:g.first);
            v.candidates_examined=UINT32_MAX-j;v.sqrt_refinements=0x80000000u+j;
            v.sqrt_refinement_limited=bool(j&1);
            for(unsigned k=0;k<sizes[j];++k) v.message.push_back(std::bit_cast<char>(static_cast<unsigned char>((k*37+j*19)&255)));
            if(j==1) v.message=std::string("\0\xff\xc0",3);
            if(j==5) v.message=std::string(1,'\0');
        }
    }
};
namespace mesh=pikapika::sphere_triangle_mesh;
struct MeshValues {
    std::array<mesh::Row,3> rows;
    std::array<mesh::Nearest,3> nearest;
    MeshValues() {
        ResultValues values;Builder b;
        constexpr std::array<std::uint64_t,9> bits{0x8000000000000000ull,1,0x8000000000000001ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,
            0xfff0000000000000ull,0x7ff8000000000042ull,0x3ff0000000000000ull};
        constexpr std::array<std::uint64_t,3> ids{UINT64_MAX,9007199254740993ull,0};
        for(unsigned j=0;j<3;++j) {
            auto& triangle=rows[j].triangle;triangle.id=ids[j];
            for(unsigned k=0;k<3;++k) {
                const unsigned n=((k+j)%3)*3;
                triangle.vertices[k]={std::bit_cast<double>(bits[n]),std::bit_cast<double>(bits[n+1]),std::bit_cast<double>(bits[n+2])};
            }
            nearest[j].squared_distance=b.bound();nearest[j].distance=b.bound();nearest[j].gap=b.bound();
        }
        rows[1].query=values.results[6];rows[2].query=values.results[7];
        nearest[1].possible_surface_ids={0,UINT64_MAX,9007199254740993ull,UINT64_MAX};
        nearest[2].possible_surface_ids={9007199254740993ull,UINT64_MAX,0,UINT64_MAX};
    }
};
void fixture(d::Writer& w,const MeshValues& v) {
    ok(w.begin(0x524d5631));ok(w.array());
    for(const auto& row:v.rows) {ok(r::write(w,row));}
    for(const auto& nearest:v.nearest) {ok(r::write(w,nearest));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const MeshValues* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.rows[c.calls%3])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.nearest[c.calls%3])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);i::require_environment();
    MeshValues v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":6,\"fixtureRecords\":6,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":6,\"rowRecords\":3,\"nearestRecords\":3,\"actualGeometryQueries\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            MeshValues values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
