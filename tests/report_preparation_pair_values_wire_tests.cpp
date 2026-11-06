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
void need(bool b) {if(!b) throw std::runtime_error("report preparation pair values assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace g=pikapika::world_static_mesh_flight;
static_assert(std::is_same_v<std::underlying_type_t<g::ColliderKind>,unsigned>);
static_assert(std::is_same_v<std::underlying_type_t<g::PairKind>,unsigned>);
struct PreparationValues {
    std::array<g::ColliderRef,6> refs{};
    std::array<g::Pair,6> pairs{};
    std::array<g::StaticOnlyCounts,4> excluded{};
    PreparationValues() {
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<std::size_t,7> totals{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull,17,42,UINT64_MAX-1};
        for(std::size_t i=0;i<refs.size();++i) {
            refs[i]={static_cast<g::ColliderKind>(kinds[i]),counts[i%4],static_cast<std::size_t>(counts[(i+1)%4]),counts[(i+2)%4]};
        }
        for(std::size_t i=0;i<pairs.size();++i) pairs[i]={static_cast<g::PairKind>(kinds[i]),refs[i],refs[5-i]};
        for(std::size_t i=0;i<excluded.size();++i) excluded[i]={totals[i%7],totals[(i+1)%7],totals[(i+2)%7],totals[(i+3)%7],totals[(i+4)%7],totals[(i+5)%7],totals[(i+6)%7]};
    }
};
void fixture(d::Writer& w,const PreparationValues& v) {
    ok(w.begin(0x52505056));ok(w.array());
    for(const auto& value:v.refs) {ok(r::write(w,value));}
    for(const auto& value:v.pairs) {ok(r::write(w,value));}
    for(const auto& value:v.excluded) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const PreparationValues* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.refs[c.calls%6])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.pairs[c.calls%6])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.excluded[c.calls%4])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    PreparationValues v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && std::equal(x.data.begin(),x.data.end(),base.data.begin()));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==3*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);

    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":3,\"mappedFields\":14,\"fixtureRecords\":16,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":16,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            PreparationValues values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
