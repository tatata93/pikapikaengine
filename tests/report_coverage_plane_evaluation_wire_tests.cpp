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
void need(bool b) {if(!b) throw std::runtime_error("report coverage plane Evaluation assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace p=pikapika::accelerated_plane_box_coverage;
struct EvaluationSources {
    static interval::Interval part(std::size_t index) {
        constexpr std::array<std::array<std::uint64_t,2>,12> bits{{
            {0,0},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff0000000000000ull},{0xc000000000000000ull,0xbff0000000000000ull},
            {1,2},{0x8000000000000002ull,0x8000000000000001ull},
            {0,1},{0x8000000000000001ull,0},
            {0xfff0000000000000ull,0xbff0000000000000ull},{0x3ff0000000000000ull,0x7ff0000000000000ull},
            {0x7fefffffffffffffull,0x7fefffffffffffffull},{0x0010000000000000ull,0x0020000000000000ull}
        }};
        const auto& pair=bits[index%bits.size()];
        return interval::Interval(std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1]));
    }
    static p::Evaluation value(std::size_t index) {
        const auto start=5*index;
        return {{part(start),part(start+1),part(start+2)},part(start+3),part(start+4),part(start+5)};
    }
    std::array<p::Evaluation,8> values{value(0),value(1),value(2),value(3),value(4),value(5),value(6),value(7)};
};
void fixture(d::Writer& w,const EvaluationSources& v) {
    ok(w.begin(0x52434531));ok(w.array());
    for(const auto& value:v.values) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const EvaluationSources* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.values[c.calls%8])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.values[(c.calls+3)%8])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    EvaluationSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":1,\"mappedFields\":4,\"fixtureRecords\":8,\"fixtureBytes\":"<<base.data.size()
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
            EvaluationSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
