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
namespace a=world_static_mesh_flight_advance;
void need(bool b) {if(!b) throw std::runtime_error("advance CommitWork/CommitStorage assertion");}
void ok(d::Status s) {need(s==d::Status::ok);}
struct AdvanceLedgerValues {
    std::vector<a::CommitWork> work;
    std::vector<a::CommitStorage> storage;
    AdvanceLedgerValues() {
        static_assert(sizeof(std::size_t)==8);
        constexpr std::array<std::uint64_t,8> values{0,1,9007199254740993ull,UINT64_MAX,0x8000000000000000ull,UINT64_MAX-1,42,0xffffffffull};
        work.reserve(16);storage.reserve(16);
        for(std::size_t i=0;i<16;++i) {
            a::CommitWork w;
            w.guard_queries_attempted=values[(i+0)%8];
            w.guard_queries_returned=values[(i+1)%8];
            w.pair_records_checked=values[(i+2)%8];
            w.call_records_checked=values[(i+3)%8];
            w.origin_bodies_checked=values[(i+4)%8];
            w.origin_planes_checked=values[(i+5)%8];
            w.origin_meshes_checked=values[(i+6)%8];
            w.origin_faces_checked=values[(i+7)%8];
            w.candidates_copied=values[(i+8)%8];
            w.candidate_validations_attempted=values[(i+9)%8];
            w.candidates_validated=values[(i+10)%8];
            w.destination_lookups=values[(i+11)%8];
            w.destinations_resolved=values[(i+12)%8];
            w.body_assignments=values[(i+13)%8];
            w.progress_assignments=values[(i+14)%8];
            work.push_back(w);a::CommitStorage s;
            s.body_buffer_slots=values[(i+3)%8];
            s.destination_slots=values[(i+4)%8];
            s.body_buffer_sizeof_bytes=values[(i+5)%8];
            s.destination_buffer_sizeof_bytes=values[(i+6)%8];
            storage.push_back(s);
        }
    }
};

void fixture(d::Writer& w,const AdvanceLedgerValues& v) {
    ok(w.begin(0x52415753));ok(w.array());
    for(const auto& value:v.work) {ok(r::write(w,value));}
    for(const auto& value:v.storage) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const AdvanceLedgerValues* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.work[c.calls%16])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.storage[c.calls%16])==d::Status::reentrant);++c.reentries;
            need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    AdvanceLedgerValues v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":19,\"fixtureRecords\":32,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":32,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            AdvanceLedgerValues values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
