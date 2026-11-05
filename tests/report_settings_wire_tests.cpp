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
void need(bool b) {if(!b) throw std::runtime_error("report settings assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
struct Inputs {
    unsigned nf=9,nu=0,nc=0;
    double f() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        return std::bit_cast<double>(bits[nf++%16]);
    }
    unsigned u() {const auto n=nu++;return n==0?0u:n==1?UINT32_MAX:n==2?0x80000002u:UINT32_MAX-17u*n;}
    std::size_t count() {
        const auto n=nc++;
        return n==0?0:n==1?SIZE_MAX:n==2?9007199254740993ull:n==3?0x8000000000000000ull:SIZE_MAX-17ull*n;
    }
};
struct Settings {
    sphere_triangle::Settings primitive;
    sphere_triangle_mesh::Settings mesh;
    sphere_triangle_mesh_held_load::Settings held;
    sphere_triangle_mesh_free_flight_guard::Settings free;
    accelerated_pair_coverage::Settings metric;
    accelerated_plane_box_coverage::Settings plane;
    accelerated_sphere_box_coverage::Settings sphere;
    world_static_mesh_flight::Settings preparation;
    world_static_mesh_flight_guard::Limits limits;
    world_static_mesh_flight_guard::GuardSettings guard{0};
    Settings() {
        Inputs n;
        primitive={n.u(),n.u(),n.u(),n.f(),n.f(),n.f()};
        mesh={n.count(),primitive};
        held={mesh,n.f(),n.count(),n.count(),n.u(),n.u(),n.count()};
        free={held,n.f()};
        metric={n.f(),n.count(),n.count(),n.u()};
        plane={n.f(),n.count(),n.count(),n.u()};
        sphere={n.f(),n.count(),n.count(),n.u(),n.u()};
        preparation={n.count(),n.count(),n.count(),n.count(),n.count()};
        limits={n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),
                n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count(),n.count()};
        guard.preparation=preparation;guard.mesh=free;guard.plane_metric=metric;guard.plane_box=plane;guard.sphere_box=sphere;
        guard.contact_margin=n.f();guard.limits=limits;need(n.nf==18 && n.nu==9 && n.nc==35);
    }
};
void fixture(d::Writer& w,const Settings& v) {
    ok(w.begin(0x52535431));ok(w.array());
    ok(r::write(w,v.primitive));ok(r::write(w,v.mesh));ok(r::write(w,v.held));ok(r::write(w,v.free));
    ok(r::write(w,v.metric));ok(r::write(w,v.plane));ok(r::write(w,v.sphere));ok(r::write(w,v.preparation));
    ok(r::write(w,v.limits));ok(r::write(w,v.guard));ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const Settings* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            const std::array statuses{r::write(w,v.primitive),r::write(w,v.mesh),r::write(w,v.held),r::write(w,v.free),r::write(w,v.metric),
                r::write(w,v.plane),r::write(w,v.sphere),r::write(w,v.preparation),r::write(w,v.limits),r::write(w,v.guard)};
            for(const auto x:statuses) {need(x==d::Status::reentrant);++c.reentries;}need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    Settings v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && std::equal(x.data.begin(),x.data.end(),base.data.begin()));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==10*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);
    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":10,\"mappedFields\":62,\"fixtureRecords\":10,\"fixtureBytes\":"<<base.data.size()
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
            Settings values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
