#include "pikapika/report_values_wire.hpp"
#include "report_coverage_pair_result_wire_sources.hpp"
#include <algorithm>
#include <limits>
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
namespace metric_sources {
static_assert(sizeof(std::size_t)==8);
void need(bool b) {if(!b) throw std::runtime_error("report guard PlaneMetricCall assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace p=pikapika::accelerated_pair_coverage;
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
struct PlaneMetricCallSources {
    std::array<g::PlaneMetricCall,16> values{};
    PlaneMetricCallSources() {
        pikapika_report_pair_result_sources::SnapshotSources settings;
        pikapika_report_pair_result_sources::ResultSources results;Ledgers ledgers;
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.state=static_cast<g::CallState>(kinds[i%6]);
            if(i&1) v.attempt_ordinal=counts[(i/2)%4];
            v.requested_settings=settings.values[i%16].settings;
            v.used_settings=settings.values[(i+1)%16].settings;
            v.granted=(i&4)!=0;v.grant=ledgers.grant;
            if(i&2) v.result=results.values[i==15?16:(i%4==3?1:(i%8==6?5:0))];
            v.messages={counts[i%4],counts[(i+1)%4],counts[(i+2)%4],(i&8)!=0};
        }
    }
};
}
namespace box_sources {

static_assert(sizeof(std::size_t)==8);
void need(bool b) {if(!b) throw std::runtime_error("report guard PlaneBoxCall assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace p=pikapika::accelerated_plane_box_coverage;
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
struct PlaneSources {
    static p::Input input(std::size_t index) {
        Numbers values;values.n=3*index;
        a::Sphere sphere{};sphere.center=values.vec();sphere.velocity=values.vec();sphere.acceleration=values.vec();sphere.radius=values.next();
        a::StaticPlane plane{};plane.normal=values.vec();plane.offset=values.next();
        const double error=values.next(),margin=values.next();
        return p::Input(sphere,plane,error,margin);
    }
    static p::Snapshot snapshot(std::size_t index) {
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,4> depths{0,32,0x80000000u,UINT32_MAX};
        Numbers values;values.n=index;
        const double horizon=values.next(),tolerance=values.next();
        return {input(index+8),horizon,{tolerance,counts[index%4],counts[(index+1)%4],depths[index%4]}};
    }
    std::array<p::Input,8> inputs{input(0),input(1),input(2),input(3),input(4),input(5),input(6),input(7)};
    std::array<p::Snapshot,8> snapshots{snapshot(0),snapshot(1),snapshot(2),snapshot(3),snapshot(4),snapshot(5),snapshot(6),snapshot(7)};
};
struct AuditPartitionSources {
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

    std::array<p::Audit,20> audits{};
    std::array<p::PartitionLeaf,12> leaves{};
    AuditPartitionSources() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<unsigned,4> depths{0,UINT32_MAX,31,32};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        auto reason=[](std::size_t n) {const auto k=n%19;return static_cast<p::Reason>(k<17?static_cast<unsigned>(k):(k==17?0x80000000u:UINT32_MAX));};
        for(std::size_t i=0;i<audits.size();++i) {
            auto& value=audits[i];value.cell.time_bounds={std::bit_cast<double>(bits[2*i%16]),std::bit_cast<double>(bits[(2*i+1)%16])};value.cell.depth=depths[i%4];
            if(i&4) value.cell.parent_audit=static_cast<std::size_t>(counts[i%4]);
            value.call_attempted=(i&8)!=0;
            if(i&1) value.evaluation=AuditPartitionSources::value(i/2);
            value.outcome=static_cast<p::Outcome>(kinds[i%6]);value.blocked_reason=reason(i);
            if(i&2) value.split_time=std::bit_cast<double>(bits[(i+3)%16]);
        }
        for(std::size_t i=0;i<leaves.size();++i) {
            auto& value=leaves[i];value.cell.time_bounds={std::bit_cast<double>(bits[(2*i+3)%16]),std::bit_cast<double>(bits[(2*i+4)%16])};value.cell.depth=depths[(i+1)%4];
            if(i&2) value.cell.parent_audit=static_cast<std::size_t>(counts[(i/4+i)%4]);
            value.state=static_cast<p::LeafState>(kinds[i%6]);
            if(i&1) value.audit_index=static_cast<std::size_t>(counts[(i/2)%4]);
            value.blocked_reason=reason(i+7);
        }
    }
};
struct ResultSources {
    std::array<p::Result,32> values{};
    ResultSources() {
        PlaneSources snapshots;AuditPartitionSources proof;
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.status=static_cast<p::Status>(kinds[i%6]);
            const auto reason=i%19;v.reason=static_cast<p::Reason>(reason<17?static_cast<unsigned>(reason):(reason==17?0x80000000u:UINT32_MAX));
            if(i&1) v.snapshot=snapshots.snapshots[(i/2)%8];
            v.snapshot_validated=(i&8)!=0;
            if(i&2) v.failed_input=counts[(i/4+i)%4];
            v.partition_complete=(i&16)!=0;
            if(i==2) {v.audits={proof.audits[2],proof.audits[3]};v.partition={proof.leaves[4],proof.leaves[5]};v.frontier={proof.audits[6].cell,proof.audits[7].cell};}
            if(i==6) v.partition={proof.leaves[9],proof.leaves[3],proof.leaves[9]};
            if(i==7) v.audits={proof.audits[5],proof.audits[3],proof.audits[5]};
            if(i && i%7==0 && i!=7) {v.audits={proof.audits[i%20]};v.partition={proof.leaves[i%12]};v.frontier={proof.audits[(i+3)%20].cell};}
            if(i==31) {v.audits.assign(proof.audits.begin(),proof.audits.end());v.partition.assign(proof.leaves.begin(),proof.leaves.end());v.frontier={proof.audits[0].cell,proof.audits[7].cell,proof.audits[0].cell};}
            if(i&4) v.current=proof.audits[i%20].cell;
            v.work={counts[(i+1)%4],counts[(i+2)%4]};
            if(i) {const std::array<unsigned char,6> body{0x41,static_cast<unsigned char>(i),0,255,128,0x42};v.message.assign(reinterpret_cast<const char*>(body.data()),body.size());}
            if(i==31) {v.message.clear();for(unsigned j=0;j<256;++j) v.message.push_back(static_cast<char>(j));v.message.push_back('\0');}
        }
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
struct PlaneBoxCallSources {
    std::array<g::PlaneBoxCall,16> values{};
    PlaneBoxCallSources() {
        PlaneSources settings;ResultSources results;Ledgers ledgers;
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.state=static_cast<g::CallState>(kinds[i%6]);
            if(i&1) v.attempt_ordinal=counts[(i/2)%4];
            v.requested_settings=settings.snapshots[i%8].settings;
            v.used_settings=settings.snapshots[(i+1)%8].settings;
            v.granted=(i&4)!=0;v.grant=ledgers.grant;
            if(i&2) v.result=results.values[i==2?0:(i==15?31:(i%4==3?7:(i%8==6?6:2)))];
            v.messages={counts[i%4],counts[(i+1)%4],counts[(i+2)%4],(i&8)!=0};
        }
    }
};
}
namespace plane_sources {
namespace g=world_static_mesh_flight_guard;
namespace p=accelerated_pair_coverage;
void need(bool b) {if(!b) throw std::runtime_error("report guard PlaneCalls assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
struct PlaneCallsSources {
    std::array<g::PlaneCalls,8> values{};
    PlaneCallsSources() {
        metric_sources::PlaneMetricCallSources metric;
        box_sources::PlaneBoxCallSources box;
        constexpr std::array<std::size_t,8> indices{0,1,2,3,4,5,14,15};
        for(std::size_t i=0;i<values.size();++i) {
            values[i].metric=metric.values[indices[i]];
            values[i].box=box.values[indices[7-i]];
        }
    }
};
}
namespace mesh_sources {

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
}
namespace sphere_sources {

static_assert(sizeof(std::size_t)==8);
void need(bool b) {if(!b) throw std::runtime_error("report guard SphereCall assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace p=pikapika::accelerated_sphere_box_coverage;
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
struct AuditPartitionSources {
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
        const auto start=7*index;
        constexpr std::array<unsigned,4> counts{0,1,0x80000000u,UINT32_MAX};
        return {{part(start),part(start+1),part(start+2)},
                {part(start+3),part(start+4),part(start+5)},
                {part(start+6),part(start+7),part(start+8)},
                part(start+9),part(start+10),
                {part(start+11),counts[index%4],(index&4)!=0},
                part(start+12),part(start+13),part(start+14)};
    }

    std::array<p::Audit,20> audits{};
    std::array<p::PartitionLeaf,12> leaves{};
    AuditPartitionSources() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<unsigned,4> depths{0,UINT32_MAX,31,32};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        auto reason=[](std::size_t n) {const auto k=n%18;return static_cast<p::Reason>(k<16?static_cast<unsigned>(k):(k==16?0x80000000u:UINT32_MAX));};
        for(std::size_t i=0;i<audits.size();++i) {
            auto& value=audits[i];value.cell.time_bounds={std::bit_cast<double>(bits[2*i%16]),std::bit_cast<double>(bits[(2*i+1)%16])};value.cell.depth=depths[i%4];
            if(i&4) value.cell.parent_audit=static_cast<std::size_t>(counts[i%4]);
            value.call_attempted=(i&8)!=0;
            if(i&1) value.evaluation=AuditPartitionSources::value(i/2);
            value.outcome=static_cast<p::Outcome>(kinds[i%6]);value.blocked_reason=reason(i);
            if(i&2) value.split_time=std::bit_cast<double>(bits[(i+3)%16]);
        }
        for(std::size_t i=0;i<leaves.size();++i) {
            auto& value=leaves[i];value.cell.time_bounds={std::bit_cast<double>(bits[(2*i+3)%16]),std::bit_cast<double>(bits[(2*i+4)%16])};value.cell.depth=depths[(i+1)%4];
            if(i&2) value.cell.parent_audit=static_cast<std::size_t>(counts[(i/4+i)%4]);
            value.state=static_cast<p::LeafState>(kinds[i%6]);
            if(i&1) value.audit_index=static_cast<std::size_t>(counts[(i/2)%4]);
            value.blocked_reason=reason(i+7);
        }
    }
};
struct ResultSources {
    std::array<p::Result,32> values{};
    ResultSources() {
        SphereSources snapshots;AuditPartitionSources proof;
        constexpr std::array<std::size_t,8> failed_inputs{0,1,2,3,4,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.status=static_cast<p::Status>(kinds[i%6]);
            const auto reason=i%18;v.reason=static_cast<p::Reason>(reason<16?static_cast<unsigned>(reason):(reason==16?0x80000000u:UINT32_MAX));
            if(i&1) v.snapshot=snapshots.snapshots[(i/2)%8];
            v.snapshot_validated=(i&8)!=0;
            if(i&2) v.failed_input=failed_inputs[(i/4+i)%8];
            v.partition_complete=(i&16)!=0;
            if(i==2) {v.audits={proof.audits[2],proof.audits[3]};v.partition={proof.leaves[4],proof.leaves[5]};v.frontier={proof.audits[6].cell,proof.audits[7].cell};}
            if(i==6) v.partition={proof.leaves[9],proof.leaves[3],proof.leaves[9]};
            if(i==7) v.audits={proof.audits[5],proof.audits[3],proof.audits[5]};
            if(i && i%7==0 && i!=7) {v.audits={proof.audits[i%20]};v.partition={proof.leaves[i%12]};v.frontier={proof.audits[(i+3)%20].cell};}
            if(i==31) {v.audits.assign(proof.audits.begin(),proof.audits.end());v.partition.assign(proof.leaves.begin(),proof.leaves.end());v.frontier={proof.audits[0].cell,proof.audits[7].cell,proof.audits[0].cell};}
            if(i&4) v.current=proof.audits[i%20].cell;
            v.work={counts[(i+1)%4],counts[(i+2)%4],counts[(i+3)%4],counts[(i+4)%4],counts[(i+5)%4],counts[(i+6)%4],((i+1)&4)!=0};
            if(i) {const std::array<unsigned char,6> body{0x41,static_cast<unsigned char>(i),0,255,128,0x42};v.message.assign(reinterpret_cast<const char*>(body.data()),body.size());}
            if(i==31) {v.message.clear();for(unsigned j=0;j<256;++j) v.message.push_back(static_cast<char>(j));v.message.push_back('\0');}
        }
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
struct SphereCallSources {
    std::array<g::SphereCall,16> values{};
    SphereCallSources() {
        SphereSources settings;ResultSources results;Ledgers ledgers;
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.state=static_cast<g::CallState>(kinds[i%6]);
            if(i&1) v.attempt_ordinal=counts[(i/2)%4];
            v.requested_settings=settings.snapshots[i%8].settings;
            v.used_settings=settings.snapshots[(i+1)%8].settings;
            v.granted=(i&4)!=0;v.grant=ledgers.grant;
            if(i&2) v.result=results.values[i==2?0:(i==15?31:(i%4==3?7:(i%8==6?6:2)))];
            v.messages={counts[i%4],counts[(i+1)%4],counts[(i+2)%4],(i&8)!=0};
        }
    }
};
}
namespace {
namespace g=world_static_mesh_flight_guard;
void need(bool b) {if(!b) throw std::runtime_error("report guard Child variant assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
struct ChildSources {
    std::array<g::Child,6> values{};
    ChildSources() {
        mesh_sources::MeshCallSources mesh;plane_sources::PlaneCallsSources plane;sphere_sources::SphereCallSources sphere;
        values={g::Child{mesh.values[0]},g::Child{plane.values[3]},g::Child{sphere.values[0]},
                g::Child{mesh.values[15]},g::Child{plane.values[7]},g::Child{sphere.values[15]}};
    }
};
void fixture(d::Writer& w,const ChildSources& v) {
    ok(w.begin(0x52474348));ok(w.array());
    for(const auto& value:v.values) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const ChildSources* source=nullptr;
    const g::Child* empty=nullptr;
    std::size_t empty_reentries=0;
    Capture() {data.reserve(32768);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.values[c.calls%3])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.values[3+c.calls%3])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
            if(c.empty) {need(r::write(w,*c.empty)==d::Status::reentrant);need(w.status()==d::Status::ok);++c.empty_reentries;}
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
struct ConversionFailure {};
struct ThrowMesh {operator g::MeshCall() const {throw ConversionFailure{};}};
struct ThrowPlane {operator g::PlaneCalls() const {throw ConversionFailure{};}};
struct ThrowSphere {operator g::SphereCall() const {throw ConversionFailure{};}};
struct Reachability {std::size_t empty=0,retained=0,phases=0,reentries=0,sticky_cases=0;};
Reachability valueless_checks(const ChildSources& original,std::size_t callback_count) {
    Reachability result;
    for(unsigned old=0;old<3;++old) for(unsigned target=0;target<3;++target) {
        g::Child value=original.values[old];
        Capture before;d::Writer bw(Capture::sink,&before);ok(bw.begin(1));ok(r::write(bw,value));ok(bw.finish());
        bool caught=false;
        try {if(target==0) value.emplace<0>(ThrowMesh{});else if(target==1) value.emplace<1>(ThrowPlane{});else value.emplace<2>(ThrowSphere{});}
        catch(const ConversionFailure&) {caught=true;}
        need(caught);
        if(!value.valueless_by_exception()) {
            Capture after;d::Writer aw(Capture::sink,&after);ok(aw.begin(1));ok(r::write(aw,value));ok(aw.finish());
            need(value.index()==old && before.data==after.data);++result.retained;continue;
        }
        need(value.index()==std::variant_npos);++result.empty;
        for(unsigned phase=0;phase<6;++phase) {
            Capture c;d::Writer w(Capture::sink,&c);
            if(phase) ok(w.begin(1));
            if(phase==1) ok(w.array());
            if(phase==2) {ok(w.object());ok(w.key({}));}
            if(phase==3) ok(w.present());
            if(phase==4) ok(w.variant(0));
            if(phase==5) {ok(w.null_value());ok(w.finish());}
            const auto data=c.data;const auto calls=c.calls;const auto complete=w.complete();
            need(r::write(w,value)==d::Status::invalid_state && w.status()==d::Status::invalid_state);
            need(c.data==data && c.calls==calls && w.complete()==complete && complete==(phase==5));
            need(w.finish()==d::Status::invalid_state && c.data==data && c.calls==calls);++result.phases;
        }
        for(unsigned prior=0;prior<5;++prior) {
            Capture c;d::Writer w(prior==2?nullptr:Capture::sink,&c);d::Status expected=d::Status::invalid_state;
            if(prior==0) need(w.finish()==expected);
            if(prior==1) {ok(w.begin(1));for(std::size_t i=0;i<64;++i) ok(w.array());expected=d::Status::depth_limit;need(w.array()==expected);}
            if(prior==2) {expected=d::Status::missing_sink;need(w.begin(1)==expected);}
            if(prior==3) {c.fail_at=1;expected=d::Status::sink_stopped;need(w.begin(1)==expected);}
            if(prior==4) {c.throw_at=1;expected=d::Status::sink_exception;need(w.begin(1)==expected);}
            const auto data=c.data;const auto calls=c.calls;
            need(r::write(w,value)==expected && w.status()==expected && c.calls==calls && c.data==data);++result.sticky_cases;
        }
        Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&original;re.empty=&value;fixture(rw,original);
        need(re.empty_reentries==callback_count && value.valueless_by_exception());result.reentries+=re.empty_reentries;
    }
    need(result.empty+result.retained==9);return result;
}
void run() {
    need(std::fegetround()==FE_TONEAREST);
    ChildSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
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
    const auto reach=valueless_checks(v,base.calls);
    std::cout<<"{\"common\":{\"status\":\"PASS\",\"mappedRecordTypes\":0,\"mappedFields\":0,\"mappedVariants\":1,\"fixtureRecords\":6,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":6,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true},\"reachability\":{\"attempts\":9,\"valuelessCases\":"<<reach.empty<<",\"retainedCases\":"<<reach.retained<<",\"byteFreePhaseCases\":"<<reach.phases<<",\"existingStickyFailureCases\":"<<reach.sticky_cases<<",\"valuelessReentryRefusals\":"<<reach.reentries<<",\"privateBytesModified\":false}}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            ChildSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
