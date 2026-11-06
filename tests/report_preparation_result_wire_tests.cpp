#include "pikapika/report_values_wire.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <stdexcept>
#include <string>
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
namespace leaf_sources {
void need(bool b) {if(!b) throw std::runtime_error("leaf source assertion");}
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
}
namespace pair_sources {
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
}
namespace failure_sources {
namespace g=pikapika::world_static_mesh_flight_guard;
namespace p=pikapika::world_static_mesh_flight;
void need(bool b) {if(!b) throw std::runtime_error("failure source assertion");}
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
}
namespace {
namespace g=pikapika::world_static_mesh_flight;
void need(bool b) {if(!b) throw std::runtime_error("prepare Snapshot/Inventory assertion");}
void ok(d::Status s) {need(s==d::Status::ok);}
struct SnapshotInventorySources {
    std::array<g::Snapshot,4> snapshots{};
    std::array<g::Inventory,4> inventories{};
    SnapshotInventorySources() {
        static_assert(sizeof(std::size_t)==8);
        leaf_sources::Values leaf;leaf_sources::Numbers numbers;pair_sources::PreparationValues pairs;
        constexpr std::array<std::size_t,5> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull,17};
        for(std::size_t i=0;i<4;++i) {
            auto& v=snapshots[i];v.gravity=numbers.vec();v.horizon=numbers.next();
            v.settings={counts[i%5],counts[(i+1)%5],counts[(i+2)%5],counts[(i+3)%5],counts[(i+4)%5]};
            auto& w=inventories[i];w.dynamic_bodies=counts[i%5];w.static_bodies=counts[(i+1)%5];w.total_faces=counts[(i+2)%5];w.colliders=counts[(i+3)%5];w.all_pairs=counts[(i+4)%5];w.excluded=pairs.excluded[i];
        }
        need(numbers.n==16);
        snapshots[1].bodies={leaf.body,leaf.body};snapshots[1].bodies[1].id=0;snapshots[1].bodies[1].is_static=false;
        snapshots[1].planes={leaf.plane,leaf.plane};snapshots[1].planes[1].id=0;snapshots[1].meshes={leaf.mesh,leaf.empty_mesh};
        snapshots[2].bodies={leaf.body};snapshots[2].bodies[0].id=9007199254740993ull;snapshots[2].bodies[0].mass=std::bit_cast<double>(0x8000000000000000ull);
        snapshots[2].meshes={leaf.empty_mesh,leaf.mesh,leaf.empty_mesh};snapshots[3].planes={leaf.plane};snapshots[3].planes[0].normal=leaf.vec;
        inventories[1].pairs={pairs.pairs[5],pairs.pairs[0],pairs.pairs[5]};inventories[2].pairs={pairs.pairs[4],pairs.pairs[2]};
        inventories[3].pairs={pairs.pairs[3],pairs.pairs[2],pairs.pairs[1],pairs.pairs[0]};
    }
};

struct PreparationResults {
    std::array<g::Result,30> results{};
    PreparationResults() {
        SnapshotInventorySources owned;failure_sources::FailureValues failures;
        std::array<std::string,4> messages{std::string{},std::string("prepare\0diagnostic",18),std::string("\xff\x80\0\xfe",4),std::string(513,'q')};
        messages[3][256]='\0';messages[3][511]='\0';
        constexpr std::array<unsigned,4> unknown{UINT32_MAX,0x80000000u,0x7fffffffu,UINT32_MAX-1};
        std::size_t fi=0,si=0,ii=0;
        for(std::size_t i=0;i<results.size();++i) {
            auto& v=results[i];const auto ordinal=static_cast<unsigned>(i);
            v.status=static_cast<g::Status>(i<26?ordinal%5:unknown[i-26]);
            v.reason=static_cast<g::Reason>(i<26?ordinal:unknown[i-26]);
            v.capture=static_cast<g::CaptureState>(i<26?ordinal%3:unknown[i-26]);
            if(i<16) {
                const auto mask=i%8;
                if(mask&1u) {v.failure=failures.locations[fi++];}
                if(mask&2u) {v.snapshot=owned.snapshots[si++%4];}
                if(mask&4u) {v.inventory=owned.inventories[ii++%4];}
            }
            v.message=messages[i%4];
        }
        need(fi==8 && si==8 && ii==8);
    }
};

void fixture(d::Writer& w,const PreparationResults& v) {
    ok(w.begin(0x52505253));ok(w.array());
    for(const auto& value:v.results) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const PreparationResults* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.results[c.calls%30])==d::Status::reentrant);++c.reentries;
            need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    PreparationResults v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":1,\"mappedFields\":7,\"fixtureRecords\":30,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":30,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            PreparationResults values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
