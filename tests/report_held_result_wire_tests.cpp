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
void need(bool b) {if(!b) throw std::runtime_error("report complete held Result assertion");}
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
namespace h=pikapika::sphere_triangle_mesh_held_load;
struct Builder {
    unsigned next=0;
    interval::Interval bound() {
        constexpr std::array<std::array<std::uint64_t,2>,8> bits{{
            {0,0},{0x8000000000000001ull,1},{1,0x0010000000000000ull},
            {0xffefffffffffffffull,0x7fefffffffffffffull},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0xfff0000000000000ull,0xbff0000000000000ull},{0x3ff0000000000000ull,0x7ff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff8000000000000ull}}};
        const auto pair=bits[next++%bits.size()];return {std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1])};
    }
    h::Bounds3 bounds() {return {bound(),bound(),bound()};}
};
struct HeldSources {
    std::array<h::HeldSphere,2> spheres;
    std::array<h::Cell,2> cells;
    std::array<h::WorldBodySnapshot,2> worlds;
    HeldSources() {
        Numbers f;
        for(unsigned j=0;j<2;++j) {
            auto& v=spheres[j];v.id=j?9007199254740993ull:UINT64_MAX;
            v.position=f.vec();v.velocity=f.vec();v.mass=f.next();v.force=f.vec();v.gravity=f.vec();v.radius=f.next();
        }
        need(f.n==28);
        cells[0]={{std::bit_cast<double>(0x8000000000000000ull),0.0},0};
        cells[1]={{1.0,-1.0},UINT32_MAX};
        for(unsigned j=0;j<2;++j) {
            auto& v=worlds[j];auto& body=v.body;body.id=j?UINT64_MAX-1:0;body.is_static=j==0;
            body.mass=f.next();body.inertia_diagonal=f.vec();body.radius=f.next();body.position=f.vec();body.velocity=f.vec();
            body.angular_momentum=f.vec();body.orientation={f.next(),f.next(),f.next(),f.next()};
            body.force=f.vec();body.torque=f.vec();body.material=f.material();v.gravity=f.vec();
        }
        need(f.n==86);
    }
};struct HeldValues {
    std::array<h::Snapshot,3> snapshots;
    std::array<h::Work,2> work{};
    HeldValues() {
        Numbers f;
        sphere_triangle::StaticTriangle a{},b{};
        a.id=UINT64_MAX;b.id=9007199254740993ull;
        for(auto& vertex:a.vertices) {vertex=f.vec();}
        for(auto& vertex:b.vertices) {vertex=f.vec();}
        auto reversed=a;std::swap(reversed.vertices[0],reversed.vertices[2]);
        for(unsigned j=0;j<3;++j) {
            auto& v=snapshots[j];auto& input=v.input;input.id=j?9007199254740993ull:UINT64_MAX;
            input.position=f.vec();input.velocity=f.vec();input.mass=f.next();input.force=f.vec();input.gravity=f.vec();input.radius=f.next();v.horizon=f.next();
            auto& settings=v.settings;auto& primitive=settings.mesh.primitive;
            primitive.max_candidates=j;primitive.sqrt_refinements=UINT32_MAX-j;primitive.max_total_sqrt_refinements=0x80000002u+j;
            primitive.maximum_local_width=f.next();primitive.maximum_normal_width=f.next();primitive.minimum_sine_squared=f.next();
            settings.mesh.max_surfaces=UINT64_MAX-j;settings.time_tolerance=f.next();settings.max_evaluations=9007199254740993ull+j;
            settings.max_leaves=j;settings.max_depth=UINT32_MAX-j;settings.enclosure_sqrt_refinements=j;settings.max_total_sqrt_refinements=UINT64_MAX-17*j;
        }
        snapshots[1].triangles={a,b,a};snapshots[2].triangles={b,reversed,a};need(f.n==75);
        work[1]={0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull,1,UINT64_MAX-17,9007199254740995ull,255,256,257,false};
    }
};struct HeldProofs {
    std::vector<h::InitialProof> initial;
    std::vector<h::CertifiedLeaf> leaves;
    std::vector<h::Witness> witnesses;
    std::vector<h::EntryWindow> windows;
    HeldProofs() {
        Builder b;Numbers f;
        for(unsigned j=0;j<2;++j) {initial.push_back({b.bound(),b.bound(),j?UINT64_MAX:0});}
        for(unsigned j=0;j<2;++j) {
            const h::Cell cell{{f.next(),f.next()},j?UINT32_MAX:0};
            leaves.push_back({cell,b.bound(),j?0x8000000000000000ull:9007199254740993ull});
        }
        for(unsigned j=0;j<2;++j) {
            const h::Cell cell{{f.next(),f.next()},j?UINT32_MAX-1:1};
            witnesses.push_back({cell,f.next(),b.bounds(),f.vec(),f.next(),b.bound(),j?1:UINT64_MAX-1});
        }
        for(unsigned j=0;j<2;++j) {
            windows.push_back({{f.next(),f.next()},b.bound(),b.bounds(),b.bound(),j?256u:255u});
        }
        need(b.next==24 && f.n==22);
    }
};struct HeldAudits {
    std::vector<h::CellAudit> audits;
    std::vector<h::PartitionLeaf> partition;
    HeldAudits() {
        Builder b;Numbers f;
        for(unsigned j=0;j<14;++j) {
            const unsigned mask=j==0?0u:j==1?4095u:1u<<(j-2);
            h::CellAudit v;
            v.kind=static_cast<h::AuditKind>(j?UINT32_MAX-j:0);v.cell={{f.next(),f.next()},j?UINT32_MAX-j:0};v.time=f.next();
            v.outcome=static_cast<h::Outcome>(0x80000000u+j);v.mesh_queried=j%2!=0;
            if(mask&1u) v.path_bounds=b.bounds();
            if(mask&2u) v.point_bounds=b.bounds();
            if(mask&4u) v.anchor=f.vec();
            if(mask&8u) v.mesh_status=static_cast<sphere_triangle_mesh::Status>(UINT32_MAX-j);
            if(mask&16u) v.mesh_reason=static_cast<sphere_triangle_mesh::Reason>(0x80000000u+j);
            if(mask&32u) v.distance=b.bound();
            if(mask&64u) v.displacement_squared_bound=b.bound();
            if(mask&128u) v.error_squared_bound=b.bound();
            if(mask&256u) v.displacement_root=b.bound();
            if(mask&512u) v.error_root=b.bound();
            if(mask&1024u) v.clearance_certificate=b.bound();
            if(mask&2048u) v.penetration_certificate=b.bound();
            v.work={j,UINT64_MAX-j,9007199254740993ull+j,0x8000000000000000ull+j,100u+j,200u+j,300u+j,400u+j,500u+j,600u+j,j%2==0};
            audits.push_back(v);
        }
        for(unsigned j=0;j<4;++j) {
            h::PartitionLeaf v;v.cell={{f.next(),f.next()},j?UINT32_MAX-j:0};
            v.state=static_cast<h::LeafState>(j?UINT32_MAX-j:0);v.blocked_reason=static_cast<h::Reason>(0x80000000u+j);
            if(j) v.audit_index=j==1?0:j==2?9007199254740993ull:UINT64_MAX;
            partition.push_back(v);
        }
        need(b.next==26 && f.n==56);
    }
};
struct HeldResults {
    std::vector<h::Result> results;
    HeldResults() {
        HeldSources original;HeldValues inputs;HeldProofs proofs;HeldAudits records;Builder b;
        std::array<sphere_triangle_mesh::Result,2> meshes;
        auto& mesh=meshes[0];mesh.status=static_cast<sphere_triangle_mesh::Status>(UINT32_MAX);mesh.reason=static_cast<sphere_triangle_mesh::Reason>(0x80000001u);
        mesh.failed_index=UINT64_MAX;mesh.first_failed_row=0;
        mesh.rows={{inputs.snapshots[1].triangles[0],std::nullopt},{inputs.snapshots[1].triangles[1],std::nullopt}};
        mesh.nearest=sphere_triangle_mesh::Nearest{b.bound(),b.bound(),b.bound(),{UINT64_MAX,9007199254740993ull,UINT64_MAX}};
        mesh.queries=1;mesh.candidates_examined=9007199254740993ull;mesh.sqrt_refinements=UINT64_MAX;mesh.sqrt_limited_rows=255;mesh.failed_rows=256;mesh.message=std::string("\0\xff\xc0",3);
        auto& other=meshes[1];other.status=static_cast<sphere_triangle_mesh::Status>(0x80000002u);other.reason=static_cast<sphere_triangle_mesh::Reason>(UINT32_MAX-1);
        other.first_failed_row=UINT64_MAX;other.queries=17;other.candidates_examined=18;other.sqrt_refinements=19;other.sqrt_limited_rows=20;other.failed_rows=21;other.message=std::string("mesh\0x",6);
        constexpr std::array<std::size_t,15> sizes{0,1,3,255,256,257,16,513,2,4,8,32,64,128,260};
        for(unsigned j=0;j<15;++j) {
            const unsigned mask=j==0?0u:j==1?8191u:1u<<(j-2);const bool first=j==1;
            h::Result v;v.status=static_cast<h::Status>(j==14?UINT32_MAX:j);v.reason=static_cast<h::Reason>(0x80000000u+j);
            if(mask&1u) v.failed_index=first?0:UINT64_MAX;
            if(mask&2u) v.snapshot=inputs.snapshots[first?0:1];
            if(mask&4u) v.world_body=original.worlds[first?0:1];
            if(mask&8u) v.acceleration=b.bounds();
            if(mask&16u) v.whole_path_bounds=b.bounds();
            if(mask&32u) v.whole_velocity_bounds=b.bounds();
            if(mask&64u) v.initial=proofs.initial[first?0:1];
            v.initial_separation_proven=j%2!=0;
            if(mask&128u) v.safe_prefix=first?std::array<double,2>{std::bit_cast<double>(0x8000000000000000ull),0.0}:std::array<double,2>{1.0,-1.0};
            if(mask&256u) v.best_witness=proofs.witnesses[first?0:1];
            if(mask&512u) v.window=proofs.windows[first?0:1];
            if(mask&1024u) v.current=original.cells[first?0:1];
            if(mask&2048u) v.last_mesh=meshes[first?0:1];
            if(mask&4096u) v.last_mesh_audit_index=first?9007199254740993ull:UINT64_MAX;
            const unsigned count=j==1?3u:j==2?2u:0u;
            for(unsigned k=0;k<count;++k) {
                const unsigned index=count==3 && k==2?0:(j==2?1u-k:k);
                v.certified_leaves.push_back(proofs.leaves[index]);v.candidate_surface_ids.push_back(index?9007199254740993ull:UINT64_MAX);
                v.partition.push_back(records.partition[index?3:0]);v.frontier.push_back(original.cells[index]);v.audits.push_back(records.audits[index]);
            }
            v.work={11u+j,UINT64_MAX-j,9007199254740993ull+j,0x8000000000000000ull+j,100u+j,200u+j,300u+j,400u+j,500u+j,600u+j,j%2==0};
            v.partition_leaves=j?UINT64_MAX-j:0;v.maximum_depth=UINT32_MAX-j;
            for(std::size_t k=0;k<sizes[j];++k) {v.message.push_back(static_cast<char>((k*37+j*19)%256));}
            if(j==1) v.message=std::string("\0",1);
            if(j==2) v.message=std::string("\0\xff\xc0",3);
            results.push_back(v);
        }
        need(b.next==21);
    }
};
void fixture(d::Writer& w,const HeldResults& v) {
    ok(w.begin(0x52485231));ok(w.array());
    for(const auto& value:v.results) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const HeldResults* source=nullptr;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.results[c.calls%15])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    HeldResults v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":1,\"mappedFields\":25,\"fixtureRecords\":15,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":15,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            HeldResults values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
