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
void need(bool b) {if(!b) throw std::runtime_error("report flight endpoint assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace h=pikapika::sphere_triangle_mesh_free_flight_guard;
struct FlightEndpoints {
    std::vector<h::EndpointAudit> audits;
    FlightEndpoints() {
        constexpr std::array<std::array<std::uint64_t,2>,8> pairs{{
            {0,0},{0x8000000000000001ull,1},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0xffefffffffffffffull,0x7fefffffffffffffull},{1,0x0010000000000000ull},
            {0x3ff0000000000000ull,0x7ff0000000000000ull},{0xfff0000000000000ull,0xbff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff8000000000000ull}}};
        unsigned n=0;
        const auto bound=[&]() {
            const auto k=n++;
            if(k<pairs.size()) {const auto pair=pairs[k];return interval::Interval(std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1]));}
            return interval::Interval(-static_cast<double>(1000+2*k),static_cast<double>(1000+3*k));
        };
        for(unsigned j=0;j<8;++j) {
            const h::Bounds3 nominal{bound(),bound(),bound()},nominal_allowed{bound(),bound(),bound()},
                exact{bound(),bound(),bound()},exact_allowed{bound(),bound(),bound()},difference{bound(),bound(),bound()};
            audits.push_back({nominal,nominal_allowed,exact,exact_allowed,difference,bound(),(j&1)!=0,(j&2)!=0,(j&4)!=0});
        }
        need(n==128);
    }
};
void fixture(d::Writer& w,const FlightEndpoints& v) {
    ok(w.begin(0x52464531));ok(w.array());
    for(const auto& value:v.audits) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const FlightEndpoints* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.audits[c.calls%8])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    FlightEndpoints v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && std::equal(x.data.begin(),x.data.end(),base.data.begin()));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);

    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":1,\"mappedFields\":9,\"fixtureRecords\":8,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":8,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            FlightEndpoints values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
