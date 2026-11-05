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
using namespace pikapika;
namespace {
static_assert(sizeof(std::size_t)==8 && sizeof(unsigned)==4);
void need(bool b) {if(!b) throw std::runtime_error("report ledger assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace g=world_static_mesh_flight_guard;
struct Ledgers {
    g::Counter counter{0,SIZE_MAX,false};
    g::HeldLedger held{
        {0,SIZE_MAX,false},{9007199254740993ull,0,true},{SIZE_MAX,1,false},
        {17,19,true},{23,29,false},{31,37,true},{41,43,false},{47,53,true},{59,61,false}};
    g::Retained retained{0,SIZE_MAX,9007199254740993ull,0x8000000000000000ull,5,7,11,13,17,19,23,29,31};
    g::WorkGrant granted{SIZE_MAX,9007199254740993ull,0,0x8000000000000000ull,37,41,43,47,53};
    g::Reservation reservation{retained,granted,{0,1,2,3,5,8,13,21,34}};
    g::Grant grant{retained,{55,89,144,233,377,610,987,1597,2584}};
    g::MessageOmission omission{SIZE_MAX,0,9007199254740993ull,true};
};
void fixture(d::Writer& w,const Ledgers& v) {
    ok(w.begin(0x524c4431));ok(w.array());
    ok(r::write(w,v.counter));ok(r::write(w,v.held));ok(r::write(w,v.retained));ok(r::write(w,v.granted));
    ok(r::write(w,v.reservation));ok(r::write(w,v.grant));ok(r::write(w,v.omission));ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const Ledgers* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            const std::array statuses{r::write(w,v.counter),r::write(w,v.held),r::write(w,v.retained),r::write(w,v.granted),
                r::write(w,v.reservation),r::write(w,v.grant),r::write(w,v.omission)};
            for(const auto x:statuses) {need(x==d::Status::reentrant);++c.reentries;}need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    Ledgers v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && std::equal(x.data.begin(),x.data.end(),base.data.begin()));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==7*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);
    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":7,\"mappedFields\":43,\"fixtureRecords\":7,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            Ledgers values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
