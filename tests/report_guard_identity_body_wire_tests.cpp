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
void need(bool b) {if(!b) throw std::runtime_error("report guard identity/body assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace g=pikapika::world_static_mesh_flight_guard;
static_assert(std::is_same_v<std::underlying_type_t<g::BindingMode>,unsigned>);
static_assert(std::is_same_v<std::underlying_type_t<g::BindingState>,unsigned>);
static_assert(std::is_same_v<std::underlying_type_t<g::SeedState>,unsigned>);
struct GuardValues {
    std::array<g::BindingInfo,7> bindings{};
    std::array<g::BodyRecord,7> bodies{};
    GuardValues() {
        constexpr std::array<unsigned,7> modes{0,1,0x80000000u,UINT32_MAX,0,0,0};
        constexpr std::array<unsigned,7> profiles{0,UINT32_MAX,0x80000000u,1,17,UINT32_MAX-1,42};
        constexpr std::array<std::size_t,7> ordinals{0,9007199254740993ull,UINT64_MAX,1,0x8000000000000000ull,UINT64_MAX-1,42};
        for(unsigned j=0;j<7;++j) {
            auto& v=bindings[j];v.mode=static_cast<g::BindingMode>(modes[j]);
            v.state=static_cast<g::BindingState>(j<5?j:j==5?0x80000000u:UINT32_MAX);
            v.checked=j%2!=0;v.profile=profiles[j];
            // Fully initialized char arrays: bytes via bit_cast, independent of signed char.
            for(unsigned k=0;k<65;++k) {
                unsigned char byte=0;
                if(j==0 && k<64) byte=static_cast<unsigned char>("0123456789abcdef"[k%16]);
                if(j==2) byte=static_cast<unsigned char>(k==32?0:(k*37+11)%256);
                if(j==3) byte=255;
                if(j==4) byte=static_cast<unsigned char>((k*19+7)%256);
                if(j==5) byte=static_cast<unsigned char>(k==64?'Z':'a');
                if(j==6) byte=static_cast<unsigned char>(k==0?0xc0:k==1?0xff:k==64?0x80:0);
                v.build_id[k]=std::bit_cast<char>(byte);
            }
            auto& body=bodies[j];body.body_ordinal=ordinals[j];body.is_static=j%3==0;
            body.state=static_cast<g::SeedState>(j<5?j:j==5?0x80000000u:UINT32_MAX);
        }
        bodies[1].seed_pair_ordinal=0;bodies[2].seed_pair_ordinal=UINT64_MAX;
        bodies[3].seed_pair_ordinal=9007199254740993ull;bodies[5].seed_pair_ordinal=1;
        bodies[6].seed_pair_ordinal=UINT64_MAX-1;
    }
};
void fixture(d::Writer& w,const GuardValues& v) {
    ok(w.begin(0x52474231));ok(w.array());
    for(const auto& value:v.bindings) {ok(r::write(w,value));}
    for(const auto& value:v.bodies) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const GuardValues* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.bindings[c.calls%7])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.bodies[c.calls%7])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    GuardValues v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":9,\"fixtureRecords\":14,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":14,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            GuardValues values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
