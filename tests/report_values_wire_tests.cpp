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
void need(bool b) {if(!b) throw std::runtime_error("report values assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
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
    dynamics::Material material() {return {next(),next()};}
};
struct Values {
    dynamics::RigidBody body;
    dynamics::Plane plane;
    sphere_triangle::StaticTriangle triangle;
    world_static_mesh_flight::StaticMeshSource mesh,empty_mesh;
    c::BodyLoad load;
    c::TickLoadPacket packet{static_cast<c::LoadMode>(UINT32_MAX),UINT64_MAX,{}};
    c::TickLoadPacket empty_packet{c::LoadMode::replace_total_world_loads,0,{}};
    world_static_mesh_flight_advance::Progress progress;
    s::Settings settings;
    s::Snapshot snapshot;
    Vec3 vec;
    Quaternion quaternion;
    Values() {
        Numbers f;
        body.id=UINT64_MAX;body.is_static=true;body.mass=f.next();body.inertia_diagonal=f.vec();body.radius=f.next();
        body.position=f.vec();body.velocity=f.vec();body.angular_momentum=f.vec();body.orientation={f.next(),f.next(),f.next(),f.next()};
        body.force=f.vec();body.torque=f.vec();body.material=f.material();need(f.n==26);
        plane.id=9007199254740993ull;plane.normal=f.vec();plane.offset=f.next();plane.material=f.material();
        triangle.id=0;for(auto& v:triangle.vertices) v=f.vec();
        mesh.id=UINT64_MAX;mesh.revision=9007199254740993ull;mesh.triangles={triangle,triangle};
        std::reverse(mesh.triangles[1].vertices.begin(),mesh.triangles[1].vertices.end());
        empty_mesh.id=0;empty_mesh.revision=UINT64_MAX;
        for(const auto id:std::array<std::uint64_t,3>{0,UINT64_MAX,0}) packet.loads.push_back({id,f.vec(),f.vec()});
        load=packet.loads.front();vec=f.vec();quaternion={f.next(),f.next(),f.next(),f.next()};
        progress={f.next(),UINT64_MAX};settings={f.next(),SIZE_MAX};snapshot={{f.next(),0},f.next(),UINT64_MAX,true};
        need(f.n==70);
    }
};
void fixture(d::Writer& w,const Values& v) {
    ok(w.begin(0x52564c31));ok(w.array());
    ok(r::write(w,v.body));ok(r::write(w,v.plane));ok(r::write(w,v.triangle));ok(r::write(w,v.mesh));
    ok(r::write(w,v.load));ok(r::write(w,v.packet));ok(r::write(w,v.progress));ok(r::write(w,v.settings));
    ok(r::write(w,v.snapshot));ok(r::write(w,v.vec));ok(r::write(w,v.quaternion));ok(r::write(w,v.body.material));
    ok(r::write(w,v.empty_mesh));ok(r::write(w,v.empty_packet));ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const Values* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            const std::array statuses{r::write(w,v.body),r::write(w,v.plane),r::write(w,v.triangle),r::write(w,v.mesh),
                r::write(w,v.load),r::write(w,v.packet),r::write(w,v.progress),r::write(w,v.settings),
                r::write(w,v.snapshot),r::write(w,v.vec),r::write(w,v.quaternion),r::write(w,v.body.material)};
            for(const auto x:statuses) {need(x==d::Status::reentrant);++c.reentries;}
            need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    Values v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            const auto expected=throws?d::Status::sink_exception:d::Status::sink_stopped;
            need(out.status()==expected && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size());
            need(std::equal(x.data.begin(),x.data.end(),base.data.begin()));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);
    need(re.data==base.data && re.reentries==12*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);
        need(std::fegetround()==mode && x.data==base.data);
    }
    need(std::fesetround(saved)==0);
    Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    const auto retained=base.data;v.packet.loads.clear();v.mesh.triangles.clear();v.body.id=0;need(base.data==retained);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":12,\"fixtureRecords\":14,\"mappedFloatBitValues\":96,\"fixtureBytes\":"<<base.data.size()
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
            Values values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
