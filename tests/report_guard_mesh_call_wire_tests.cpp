#include "pikapika/report_values_wire.hpp"
#include <algorithm>
#include <cstring>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <limits>
#include <type_traits>
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
void need(bool b) {if(!b) throw std::runtime_error("report guard MeshCall assertion");}
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
namespace h=pikapika::sphere_triangle_mesh_free_flight_guard;
struct FlightValues {
    std::array<h::Snapshot,3> snapshots;
    std::vector<h::Tube> tubes;
    FlightValues() {
        Numbers f;
        sphere_triangle::StaticTriangle a{},b{};
        a.id=UINT64_MAX;b.id=9007199254740993ull;
        for(auto& vertex:a.vertices) {vertex=f.vec();}
        for(auto& vertex:b.vertices) {vertex=f.vec();}
        auto reversed=a;std::swap(reversed.vertices[0],reversed.vertices[2]);
        for(unsigned j=0;j<3;++j) {
            auto& v=snapshots[j];auto& body=v.body;body.id=j?9007199254740993ull:UINT64_MAX;body.is_static=j==0;
            body.mass=f.next();body.inertia_diagonal=f.vec();body.radius=f.next();body.position=f.vec();body.velocity=f.vec();
            body.angular_momentum=f.vec();body.orientation={f.next(),f.next(),f.next(),f.next()};
            body.force=f.vec();body.torque=f.vec();body.material=f.material();v.gravity=f.vec();v.horizon=f.next();
            auto& settings=v.settings.held_load;auto& primitive=settings.mesh.primitive;
            primitive.max_candidates=j;primitive.sqrt_refinements=UINT32_MAX-j;primitive.max_total_sqrt_refinements=0x80000002u+j;
            primitive.maximum_local_width=f.next();primitive.maximum_normal_width=f.next();primitive.minimum_sine_squared=f.next();
            settings.mesh.max_surfaces=UINT64_MAX-j;settings.time_tolerance=f.next();settings.max_evaluations=9007199254740993ull+j;
            settings.max_leaves=j;settings.max_depth=UINT32_MAX-j;settings.enclosure_sqrt_refinements=j;settings.max_total_sqrt_refinements=UINT64_MAX-17*j;
            v.settings.max_angular_increment=f.next();
        }
        snapshots[1].triangles={a,b,a};snapshots[2].triangles={b,reversed,a};need(f.n==123);
        constexpr std::array<std::array<std::uint64_t,2>,12> pairs{{
            {0,0},{0x8000000000000001ull,1},{1,0x0010000000000000ull},
            {0xffefffffffffffffull,0x7fefffffffffffffull},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0xfff0000000000000ull,0xbff0000000000000ull},{0x3ff0000000000000ull,0x7ff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff8000000000000ull},{0xbff0000000000000ull,0},
            {0,0x4000000000000000ull},{0xc000000000000000ull,0xbff0000000000000ull},
            {0x000fffffffffffffull,0x7fefffffffffffffull}}};
        unsigned n=0;
        const auto bound=[&]() {const auto pair=pairs[n++];return interval::Interval(std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1]));};
        for(unsigned j=0;j<2;++j) {
            const auto nominal=f.vec();
            const h::Bounds3 exact{bound(),bound(),bound()},difference{bound(),bound(),bound()};
            tubes.push_back({nominal,exact,difference,f.next(),f.next(),f.next()});
        }
        need(n==12 && f.n==135);
    }
};
struct FlightEndpoints {
    std::vector<h::EndpointAudit> audits;
    FlightEndpoints() {
        constexpr std::array<std::array<std::uint64_t,2>,8> pairs{{
            {0,0},{0x8000000000000001ull,1},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0xffefffffffffffffull,0x7fefffffffffffffull},{1,0x0010000000000000ull},
            {0x3ff0000000000000ull,0x7ff0000000000000ull},{0xfff0000000000000ull,0xbff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff8000000000000ull}}};
        unsigned n=0;
        const auto bound=[&]() {
            const auto k=n++;
            if(k<pairs.size()) {const auto pair=pairs[k];return interval::Interval(std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1]));}
            return interval::Interval(-static_cast<double>(1000+2*k),static_cast<double>(1000+3*k));
        };
        for(unsigned j=0;j<8;++j) {
            const h::Bounds3 nominal{bound(),bound(),bound()},nominal_allowed{bound(),bound(),bound()},
                exact{bound(),bound(),bound()},exact_allowed{bound(),bound(),bound()},difference{bound(),bound(),bound()};
            audits.push_back({nominal,nominal_allowed,exact,exact_allowed,difference,bound(),(j&1)!=0,(j&2)!=0,(j&4)!=0});
        }
        need(n==128);
    }
};
namespace l=pikapika::sphere_triangle_mesh_held_load;
struct NestedHeldValues {
    std::array<l::Snapshot,3> snapshots;
    std::array<l::Work,2> work{};
    NestedHeldValues() {
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
};
static_assert(std::is_same_v<std::underlying_type_t<dynamics::CcdFailure>,std::int32_t>);
struct FlightResults {
    std::vector<h::Result> results;
    FlightResults() {
        FlightValues inputs;FlightEndpoints endpoints;NestedHeldValues held_inputs;
        l::Result held;held.status=l::Status::invalid_input;held.reason=l::Reason::derived_domain;
        held.snapshot=held_inputs.snapshots[0];held.snapshot->input.radius=2.0;
        held.safe_prefix=std::array<double,2>{std::bit_cast<double>(0x8000000000000000ull),0.0};
        held.candidate_surface_ids={UINT64_MAX,9007199254740993ull,UINT64_MAX};
        held.frontier={{{std::bit_cast<double>(0x8000000000000000ull),0.0},0},{{1.0,-1.0},UINT32_MAX}};
        held.work=held_inputs.work[1];held.partition_leaves=UINT64_MAX;held.maximum_depth=UINT32_MAX;held.message=std::string("\0held\xff",6);
        constexpr std::array<std::size_t,10> sizes{0,1,3,255,256,257,16,513,2,4};
        std::array<unsigned,10> masks{};
        for(unsigned j=0;j<10;++j) {
            const unsigned mask=j==0?0u:j==1?255u:1u<<(j-2);masks[j]=mask;const bool first=j==1;
            h::Result v;v.status=static_cast<h::Status>(j);v.reason=static_cast<h::Reason>(0x80000000u+j);
            if(mask&1u) v.failed_index=first?0:UINT64_MAX;
            if(mask&2u) v.world_body=l::WorldBodySnapshot{inputs.snapshots[2].body,inputs.snapshots[0].gravity};
            if(mask&4u) {v.snapshot=inputs.snapshots[first?0:1];v.snapshot->body.radius=1.0;}
            if(mask&8u) {v.tube=inputs.tubes[first?0:1];v.tube->guard_radius=3.0;}
            if(mask&16u) v.flight_failure=static_cast<dynamics::CcdFailure>(first?-1:std::numeric_limits<std::int32_t>::min());
            v.candidate_evaluated=j%2!=0;
            if(mask&32u) v.endpoint=endpoints.audits[first?7:0];
            if(mask&64u) v.inflated=held;
            if(mask&128u) v.candidate=inputs.snapshots[2].body;
            for(std::size_t k=0;k<sizes[j];++k) {v.message.push_back(static_cast<char>((k*37+j*19)%256));}
            if(j==1) v.message=std::string("\0",1);
            if(j==2) v.message=std::string("\0\xff\xc0",3);
            results.push_back(v);
        }
        unsigned pairs=0;
        for(unsigned a=0;a<8;++a) for(unsigned b=a+1;b<8;++b) {
            unsigned seen=0;
            for(auto mask:masks) {seen|=1u<<(((mask>>a)&1u)|(((mask>>b)&1u)<<1));}
            need(seen==15);pairs+=4;
        }
        need(pairs==112);
        constexpr std::array<dynamics::CcdFailure,17> failures{
            dynamics::CcdFailure::none,dynamics::CcdFailure::invalid_input,dynamics::CcdFailure::initial_contact,
            dynamics::CcdFailure::query_unresolved,dynamics::CcdFailure::event_budget,dynamics::CcdFailure::segment_budget,
            dynamics::CcdFailure::query_budget,dynamics::CcdFailure::root_budget,dynamics::CcdFailure::geometric_guard,
            dynamics::CcdFailure::propagation_failure,dynamics::CcdFailure::solver_failure,
            dynamics::CcdFailure::sustained_contact_required,dynamics::CcdFailure::numerical_failure,
            static_cast<dynamics::CcdFailure>(-1),static_cast<dynamics::CcdFailure>(-2),
            static_cast<dynamics::CcdFailure>(std::numeric_limits<std::int32_t>::min()),
            static_cast<dynamics::CcdFailure>(std::numeric_limits<std::int32_t>::max())};
        for(auto failure:failures) {h::Result v;v.flight_failure=failure;results.push_back(v);}
        need(results.size()==27);
    }
};
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
struct MeshCallSources {
    std::array<g::MeshCall,16> values{};
    MeshCallSources() {
        FlightValues settings;FlightResults results;Ledgers ledgers;
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.state=static_cast<g::CallState>(kinds[i%6]);
            if(i&1) v.attempt_ordinal=counts[(i/2)%4];
            v.requested_settings=settings.snapshots[i%3].settings;
            v.used_settings=settings.snapshots[(i+1)%3].settings;
            v.granted=(i&4)!=0;v.grant=ledgers.grant;
            if(i&2) v.result=results.results[i==15?1:(i%4==3?2:(i%8==6?8:0))];
            v.messages={counts[i%4],counts[(i+1)%4],counts[(i+2)%4],(i&8)!=0};
        }
    }
};
void fixture(d::Writer& w,const MeshCallSources& v) {
    ok(w.begin(0x52474d43));ok(w.array());
    for(const auto& value:v.values) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const MeshCallSources* source=nullptr;
    Capture() {data.reserve(65536);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.values[c.calls%16])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.values[(c.calls+7)%16])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    MeshCallSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && (x.data.empty() || std::memcmp(x.data.data(),base.data.data(),x.data.size())==0));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==2*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);

    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":1,\"mappedFields\":8,\"fixtureRecords\":16,\"fixtureBytes\":"<<base.data.size()
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
            MeshCallSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
