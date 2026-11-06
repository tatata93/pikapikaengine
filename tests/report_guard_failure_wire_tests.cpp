#include "pikapika/report_values_wire.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <vector>
#include <type_traits>
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
void need(bool b) {if(!b) throw std::runtime_error("report guard failure assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace g=pikapika::world_static_mesh_flight_guard;
namespace p=pikapika::world_static_mesh_flight;
static_assert(std::is_same_v<std::underlying_type_t<p::ObjectKind>,unsigned>);
struct FailureValues {
    std::array<p::FailureLocation,8> locations{};
    std::array<g::Failure,8> failures{};
    FailureValues() {
        constexpr std::array<p::ObjectKind,8> kinds{p::ObjectKind::settings,p::ObjectKind::world,p::ObjectKind::body,p::ObjectKind::plane,p::ObjectKind::mesh,p::ObjectKind::face,static_cast<p::ObjectKind>(0x80000000u),static_cast<p::ObjectKind>(UINT32_MAX)};
        unsigned location_masks=0,failure_masks=0;
        for(unsigned j=0;j<8;++j) {
            const auto mask=j%4;auto& v=locations[j];v.kind=kinds[j];location_masks|=1u<<mask;
            if(mask&1u) v.index=j==1?0:j==3?UINT64_MAX:j==5?9007199254740993ull:42;
            if(mask&2u) v.face_index=j==2?UINT64_MAX:j==3?0:j==6?9007199254740993ull:UINT64_MAX-1;
        }
        for(unsigned j=0;j<8;++j) {
            auto& v=failures[j];failure_masks|=1u<<j;
            if(j&1u) v.preparation=locations[j>>1];
            if(j&2u) v.body_ordinal=j==2?0:j==3?9007199254740993ull:j==6?UINT64_MAX:1;
            if(j&4u) v.pair_ordinal=j==4?0:j==5?UINT64_MAX:j==6?9007199254740993ull:42;
        }
        need(location_masks==15 && failure_masks==255);
    }
};
void fixture(d::Writer& w,const FailureValues& v) {
    ok(w.begin(0x52474631));ok(w.array());
    for(const auto& value:v.locations) {ok(r::write(w,value));}
    for(const auto& value:v.failures) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const FailureValues* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.locations[c.calls%8])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.failures[c.calls%8])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    FailureValues v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":6,\"fixtureRecords\":16,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":16,\"actualModelCalls\":0,\"locationPresenceMasks\":4,\"guardPresenceMasks\":8,\"knownObjectKinds\":6,\"artificialUnknownObjectKinds\":2,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            FailureValues values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
