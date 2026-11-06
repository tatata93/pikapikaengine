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
void need(bool b) {if(!b) throw std::runtime_error("report coverage sphere source/snapshot assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace a=pikapika::accelerated;
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
};
namespace p=pikapika::accelerated_sphere_box_coverage;
struct SphereSources {
    static p::Input input(std::size_t index) {
        Numbers values;values.n=3*index;
        a::Sphere sphere{};sphere.center=values.vec();sphere.velocity=values.vec();sphere.acceleration=values.vec();sphere.radius=values.next();
        a::Sphere second{};second.center=values.vec();second.velocity=values.vec();second.acceleration=values.vec();second.radius=values.next();
        const double first_error=values.next(),second_error=values.next(),margin=values.next();
        return p::Input(sphere,second,first_error,second_error,margin);
    }
    static p::Snapshot snapshot(std::size_t index) {
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,4> depths{0,32,0x80000000u,UINT32_MAX};
        Numbers values;values.n=index;
        const double horizon=values.next(),tolerance=values.next();
        return {input(index+8),horizon,{tolerance,counts[index%4],counts[(index+1)%4],depths[index%4],depths[(index+2)%4]}};
    }
    std::array<p::Input,8> inputs{input(0),input(1),input(2),input(3),input(4),input(5),input(6),input(7)};
    std::array<p::Snapshot,8> snapshots{snapshot(0),snapshot(1),snapshot(2),snapshot(3),snapshot(4),snapshot(5),snapshot(6),snapshot(7)};
};
void fixture(d::Writer& w,const SphereSources& v) {
    ok(w.begin(0x52435342));ok(w.array());
    for(const auto& value:v.inputs) {ok(r::write(w,value));}
    for(const auto& value:v.snapshots) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const SphereSources* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.inputs[c.calls%8])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.snapshots[c.calls%8])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    SphereSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":2,\"mappedFields\":8,\"fixtureRecords\":16,\"fixtureBytes\":"<<base.data.size()
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
            SphereSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
