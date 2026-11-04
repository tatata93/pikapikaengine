#include "pikapika/world_static_mesh_flight_advance.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>
#include <utility>
#include <vector>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif

// Prototype harness only. No source profile is enabled by this file. A --run
// build requires matching configured expanded source identity for the NEW TU;
// actual artifact audit remains a separate acceptance gate.
// Actual guard re-query checks commit correspondence, not independent physics.
// The separate dyadic closed-form case does not use guard candidates as its
// expected position/velocity. No allocator/nonreturn fault injection is claimed.
namespace {
namespace a=pikapika::world_static_mesh_flight_advance;
namespace g=pikapika::world_static_mesh_flight_guard;
namespace d=pikapika::dynamics;
using Bits=std::vector<std::uint64_t>;
void require(bool okay,std::string_view message) {
    if(!okay) {throw std::runtime_error(std::string(message));}
}
std::uint64_t bits(double x) noexcept {return std::bit_cast<std::uint64_t>(x);}
void number(Bits& out,double x) {out.push_back(bits(x));}
void vector(Bits& out,pikapika::Vec3 v) {number(out,v.x);number(out,v.y);number(out,v.z);}
Bits body_bits(const d::RigidBody& b) {
    Bits out{b.id,b.is_static?1ULL:0ULL};number(out,b.mass);vector(out,b.inertia_diagonal);number(out,b.radius);
    vector(out,b.position);vector(out,b.velocity);vector(out,b.angular_momentum);
    number(out,b.orientation.x);number(out,b.orientation.y);number(out,b.orientation.z);number(out,b.orientation.w);
    vector(out,b.force);vector(out,b.torque);number(out,b.material.restitution);number(out,b.material.friction);return out;
}
Bits planes_bits(const std::vector<d::Plane>& planes) {
    Bits out{static_cast<std::uint64_t>(planes.size())};
    for(const auto& p:planes) {out.push_back(p.id);vector(out,p.normal);number(out,p.offset);number(out,p.material.restitution);number(out,p.material.friction);}
    return out;
}
Bits sources_bits(const std::vector<g::StaticMeshSource>& sources) {
    Bits out{static_cast<std::uint64_t>(sources.size())};
    for(const auto& m:sources) {
        out.push_back(m.id);out.push_back(m.revision);out.push_back(static_cast<std::uint64_t>(m.triangles.size()));
        for(const auto& t:m.triangles) {out.push_back(t.id);for(const auto& v:t.vertices) {vector(out,v);}}
    }
    return out;
}
template<class Settings> void coverage_bits(Bits& out,const Settings& s) {
    number(out,s.time_tolerance);out.push_back(s.max_evaluations);out.push_back(s.max_leaves);out.push_back(s.max_depth);
    if constexpr(requires {s.sqrt_refinements;}) {out.push_back(s.sqrt_refinements);}
}
Bits settings_bits(const g::GuardSettings& s) {
    Bits out{s.preparation.max_bodies,s.preparation.max_planes,s.preparation.max_meshes,s.preparation.max_total_faces,s.preparation.max_pairs};
    const auto& h=s.mesh.held_load;const auto& p=h.mesh.primitive;
    out.push_back(h.mesh.max_surfaces);out.push_back(p.max_candidates);out.push_back(p.sqrt_refinements);out.push_back(p.max_total_sqrt_refinements);
    number(out,p.maximum_local_width);number(out,p.maximum_normal_width);number(out,p.minimum_sine_squared);
    number(out,h.time_tolerance);out.push_back(h.max_evaluations);out.push_back(h.max_leaves);out.push_back(h.max_depth);out.push_back(h.enclosure_sqrt_refinements);out.push_back(h.max_total_sqrt_refinements);number(out,s.mesh.max_angular_increment);
    coverage_bits(out,s.plane_metric);coverage_bits(out,s.plane_box);coverage_bits(out,s.sphere_box);number(out,s.contact_margin);
    const auto& l=s.limits;
    for(auto n:{l.body_records,l.pair_records,l.held_audits,l.held_certified_leaves,l.held_partition,l.held_frontier,l.primitive_audits,l.primitive_partition,l.primitive_frontier,l.last_mesh_rows,l.primitive_candidates,l.retained_faces,l.mesh_queries,l.primitive_queries,l.candidates_examined,l.sqrt_refinements,l.plane_metric_values,l.box_values,l.propagations,l.logical_payload_bytes}) {out.push_back(n);}
    return out;
}
Bits progress_bits(a::Progress p) {return {bits(p.time),p.ticks};}
struct Input {
    d::World world;
    std::vector<g::StaticMeshSource> meshes;
    g::GuardSettings settings{.0625};
    double horizon=.0625;
};
g::StaticMeshSource mesh(std::uint64_t id,double y) {
    return {id,7,{{11,{{{-32,y,-32},{32,y,-32},{-32,y,32}}}}}};
}
Input minimal() {
    // Same small geometry/source conventions as the accepted guard fixture
    // factory; independently authored input data, no copied expected result.
    Input x;x.world.gravity={-0.,-1,-0.};
    for(std::uint64_t id:{101ULL,102ULL}) {
        auto b=d::make_sphere(id,.25,2,{id==101?-2.:2.,3,1});b.inertia_diagonal={1,1,1};
        b.velocity={id==101?.25:-.25,-0.,0};b.angular_momentum={.01,-.02,.03};b.orientation={.5,.5,.5,.5};
        b.force={-0.,.125,-0.};b.torque={.001,-.002,.001};b.material={-0.,.625};x.world.add_body(b);
    }
    x.world.add_plane({201,{-0.,1,-0.},-0.,{-0.,.75}});x.meshes={mesh(302,-4),mesh(301,-0.)};return x;
}
struct Frozen {
    std::vector<Bits> bodies;
    std::vector<const d::RigidBody*> addresses;
    Bits planes,sources,settings,progress,gravity;
    const d::Plane* plane_data;
    const g::StaticMeshSource* source_data;
    std::vector<const pikapika::sphere_triangle::StaticTriangle*> face_data;
    Frozen(const Input& x,a::Progress clock):planes(planes_bits(x.world.planes())),sources(sources_bits(x.meshes)),settings(settings_bits(x.settings)),progress(progress_bits(clock)),plane_data(x.world.planes().data()),source_data(x.meshes.data()) {
        vector(gravity,x.world.gravity);
        for(const auto& b:x.world.bodies()) {bodies.push_back(body_bits(b));addresses.push_back(&b);}
        for(const auto& m:x.meshes) {face_data.push_back(m.triangles.data());}
    }
    void fixed(const Input& x) const {
        require(planes_bits(x.world.planes())==planes&&sources_bits(x.meshes)==sources&&settings_bits(x.settings)==settings,"All raw plane/material/source/ID/revision/settings bits preserved");
        Bits actual;vector(actual,x.world.gravity);require(actual==gravity,"All gravity bits preserved");
        require(x.world.bodies().size()==addresses.size()&&x.world.planes().data()==plane_data&&x.meshes.data()==source_data,"Storage count/address unchanged");
        for(std::size_t i=0;i<addresses.size();++i) {require(&x.world.bodies()[i]==addresses[i],"Existing body address and original order preserved");}
        for(std::size_t i=0;i<face_data.size();++i) {require(x.meshes[i].triangles.data()==face_data[i],"Borrowed source storage is never changed");}
    }
    void unchanged(const Input& x,a::Progress clock) const {
        fixed(x);require(progress_bits(clock)==progress,"Failure preserves ALL Progress bits/ticks");
        for(std::size_t i=0;i<bodies.size();++i) {require(body_bits(x.world.bodies()[i])==bodies[i],"Failure preserves every body field/load/NaN payload/signed zero");}
    }
};
void failed(const Input& x,a::Progress clock,const Frozen& original,const a::AdvanceReport& r) {
    original.unchanged(x,clock);require(!r.committed&&r.status!=a::Status::committed,"Failed report cannot claim commit");
    require(bits(r.requested_dt)==bits(x.horizon)&&bits(r.advanced_dt)==bits(0.),"Failed advanced_dt is +0 and requested_dt keeps original bits");
    require(progress_bits(r.original_progress)==original.progress,"Original clock diagnostics retain all bits");
    require(r.work.body_assignments==0&&r.work.progress_assignments==0,"No store phase on ANY failure");
}
void clear_loads(d::RigidBody& b) noexcept {b.force={0.,0.,0.};b.torque={0.,0.,0.};}
void origin_evidence(const g::GuardResult& r,const Frozen& original,const Input& x) {
    require(r.preparation&&r.preparation->snapshot,"Complete owned preparation snapshot");const auto& s=*r.preparation->snapshot;
    require(s.bodies.size()==original.bodies.size(),"Complete original body snapshot");
    for(std::size_t i=0;i<s.bodies.size();++i) {require(body_bits(s.bodies[i])==original.bodies[i],"Guard retains original held loads/body bits after commit");}
    require(planes_bits(s.planes)==original.planes&&sources_bits(s.meshes)==original.sources,"Guard owns full original raw sources");
    require(r.original_settings&&settings_bits(*r.original_settings)==original.settings,"Guard owns original settings");
    require(bits(s.horizon)==bits(x.horizon),"Guard uses full requested H, no shrinking");
}
void successful(Input& x,a::Progress& clock,const Frozen& original,const g::GuardResult& independently_queried,const a::AdvanceReport& r) {
    require(r.committed&&r.status==a::Status::committed&&r.reason==a::Reason::none&&!r.failure,"Complete successful transaction");
    require(r.advance_profile_checked&&r.advance_profile_matches&&r.binding.state==g::BindingState::ready,"New TU and old guard require matching configured expanded identity; actual artifact audit separate");
    require(r.guard&&r.guard->status==g::Status::certified_separated&&r.guard->candidate_bodies&&independently_queried.candidate_bodies,"Actual full guard candidate, no external-certificate input");
    const auto& candidates=*independently_queried.candidate_bodies;require(candidates.size()==x.world.bodies().size(),"All candidates, no prefix");
    original.fixed(x);origin_evidence(*r.guard,original,x);
    require(r.guard->work.child_calls_attempted==independently_queried.work.child_calls_attempted&&r.guard->pairs.size()==independently_queried.pairs.size(),"Fresh guard query complete call/pair correspondence");
    for(std::size_t i=0;i<candidates.size();++i) {
        require(body_bits(r.guard->candidate_bodies->at(i))==body_bits(candidates[i]),"Every owned guard candidate bit matches separate actual query");
        auto expected=candidates[i];clear_loads(expected);require(body_bits(x.world.bodies()[i])==body_bits(expected),"Committed body differs from certified candidate ONLY by consumed +0 loads");
    }
    require(bits(r.requested_dt)==bits(x.horizon)&&bits(r.advanced_dt)==bits(x.horizon)&&progress_bits(r.original_progress)==original.progress,"Full H and original clock recorded");
    require(r.proposed_progress&&r.clock&&progress_bits(*r.proposed_progress)==progress_bits(clock)&&clock.ticks==original.progress[1]+1,"Clock and bodies commit together once");
    const auto count=x.world.bodies().size();std::size_t faces=0;for(const auto& m:x.meshes) {faces+=m.triangles.size();}
    require(r.work.guard_queries_attempted==1&&r.work.guard_queries_returned==1,"Exactly one owned guard query inside advance");
    require(r.work.origin_bodies_checked==2*count&&r.work.origin_planes_checked==2*x.world.planes().size()&&r.work.origin_meshes_checked==2*x.meshes.size()&&r.work.origin_faces_checked==2*faces,"Two full original-state comparison passes");
    require(r.work.candidates_copied==count&&r.work.candidate_validations_attempted==count&&r.work.candidates_validated==count&&r.work.destination_lookups==count&&r.work.destinations_resolved==count,"All candidates validated/all destinations prepared before stores");
    require(r.work.pair_records_checked==r.guard->pairs.size()&&r.work.call_records_checked==r.guard->work.child_calls_attempted,"Accepted proof metadata checks counted separately");
    require(r.work.body_assignments==count&&r.work.progress_assignments==1,"All-or-none final stores");
    require(r.storage.body_buffer_slots==8&&r.storage.destination_slots==8&&r.storage.body_buffer_sizeof_bytes==8*sizeof(d::RigidBody)&&r.storage.destination_buffer_sizeof_bytes==8*sizeof(d::RigidBody*),"Fixed local payload observation, not used heap/stack bound");
}

void unsupported_profile() {
    auto x=minimal();x.settings.contact_margin=-1;x.horizon=-0.;a::Progress clock{-0.,a::maximum_ticks};const Frozen before(x,clock);
    const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);failed(x,clock,before,r);
    require(r.status==a::Status::unsupported_environment&&r.reason==a::Reason::binding_unsupported&&r.failure&&r.failure->stage==a::Stage::binding,"Default NEW TU profile refuses before invalid clock/settings");
    require(r.advance_profile_checked&&!r.advance_profile_matches&&!r.guard&&!r.clock&&!r.proposed_progress&&r.work.guard_queries_attempted==0&&r.work.guard_queries_returned==0,"Ready old guard alone cannot unlock a new TU");
}
void minimal_success() {
    auto x=minimal();a::Progress clock{-0.,7};const Frozen before(x,clock);const auto expected=g::query(x.world,x.meshes,x.horizon,x.settings);
    require(expected.status==g::Status::certified_separated&&expected.pairs.size()==7&&expected.work.child_calls_attempted==9,"Existing small guard case is independently nonvacuous");
    const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);successful(x,clock,before,expected,r);
    require(bits(clock.time)==bits(.0625)&&clock.ticks==8&&bits(r.clock->represented_dt)==bits(.0625),"Exact dyadic initial -0 clock step");
    require(r.clock->time_sum.contains(.0625)&&r.clock->represented_difference.contains(.0625)&&r.clock->sum_rounding_error.contains(0.),"Exact dyadic clock enclosures");
}
void closed_form_motion() {
    auto x=minimal();x.world=d::World{};x.world.gravity={0.,-1.,0.};auto b=d::make_sphere(101,.25,2,{2.,4.,1.});
    b.inertia_diagonal={1.,1.,1.};b.velocity={.5,-.25,.125};b.angular_momentum={0.,0.,0.};b.orientation={0.,0.,0.,1.};b.force={2.,4.,-2.};b.torque={0.,0.,0.};x.world.add_body(b);
    a::Progress clock{0.,0};const Frozen before(x,clock);const auto expected=g::query(x.world,x.meshes,x.horizon,x.settings);require(expected.status==g::Status::certified_separated,"Closed-form source must actually certify");
    const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);successful(x,clock,before,expected,r);
    const auto& actual=x.world.bodies().front();
    // Independently evaluated exact dyadics: A=(1,1,-1), H=1/16.
    const pikapika::Vec3 p{1041./512.,2041./512.,515./512.},v{9./16.,-3./16.,1./16.};Bits pb,vb,pa,va;vector(pb,p);vector(vb,v);vector(pa,actual.position);vector(va,actual.velocity);
    require(pa==pb&&va==vb,"Exact closed-form position/velocity, not copied from guard candidate");
    require(bits(actual.orientation.x)==bits(0.)&&bits(actual.orientation.y)==bits(0.)&&bits(actual.orientation.z)==bits(0.)&&bits(actual.orientation.w)==bits(1.),"Zero torque/L identity orientation retained");
}
void mixed_static() {
    auto x=minimal();auto fixed=d::make_sphere(103,.25,2,{10.,3.,1.},true);fixed.inertia_diagonal={1.,1.,1.};fixed.force={.5,-0.,-.25};fixed.torque={-0.,.125,.25};fixed.velocity={std::numeric_limits<double>::denorm_min(),-0.,0.};fixed.angular_momentum={-0.,0.,std::numeric_limits<double>::denorm_min()};x.world.add_body(fixed);
    x.settings.plane_metric.max_evaluations=128;x.settings.plane_box.max_evaluations=128;x.settings.sphere_box.max_evaluations=128;
    a::Progress clock{.0625,9};const Frozen before(x,clock);const auto expected=g::query(x.world,x.meshes,x.horizon,x.settings);require(expected.status==g::Status::certified_separated,"Explicit E128 static/full candidate nonvacuity");
    const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);successful(x,clock,before,expected,r);
    auto copied=fixed;clear_loads(copied);require(body_bits(x.world.bodies().back())==body_bits(copied),"Static subnormal V/L/material/mass retained; loads consumed once only");
}
void clock_failure(Input x,a::Progress clock,a::Reason reason) {
    const Frozen before(x,clock);const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);failed(x,clock,before,r);
    require(r.reason==reason&&r.failure&&r.failure->stage==a::Stage::clock&&!r.guard&&r.work.guard_queries_attempted==0&&r.work.guard_queries_returned==0,"Invalid/nonprogressing clock never queries guard");
}
void invalid_clocks() {
    for(double h:{0.,-0.,-.0625,std::nextafter(.1,1.),std::numeric_limits<double>::infinity(),std::bit_cast<double>(0x7ff8000000004321ULL)}) {auto x=minimal();x.horizon=h;clock_failure(std::move(x),{.25,3},a::Reason::horizon);}
    for(double t:{-std::numeric_limits<double>::denorm_min(),std::nextafter(1e9,std::numeric_limits<double>::infinity()),std::numeric_limits<double>::infinity(),std::bit_cast<double>(0x7ff8000000001234ULL)}) {clock_failure(minimal(),{t,3},a::Reason::progress_time);}
    clock_failure(minimal(),{0.,a::maximum_ticks+1},a::Reason::progress_ticks);clock_failure(minimal(),{0.,a::maximum_ticks},a::Reason::tick_limit);
    clock_failure(minimal(),{1e9,3},a::Reason::time_limit);auto tiny=minimal();tiny.horizon=0x1p-60;clock_failure(std::move(tiny),{1.,3},a::Reason::time_resolution);
}
void represented_clock_difference() {
    auto x=minimal();x.horizon=.1;a::Progress clock{1.,a::maximum_ticks-1};const Frozen before(x,clock);const auto expected=g::query(x.world,x.meshes,x.horizon,x.settings);require(expected.status==g::Status::certified_separated,"Maximum-H source actually certifies");
    const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);successful(x,clock,before,expected,r);
    require(bits(clock.time)==0x3ff199999999999aULL&&clock.ticks==a::maximum_ticks,"RN(1+binary64(.1)) fixed independent expected bits and last valid tick");
    require(bits(r.clock->represented_dt)==0x3fb99999999999a0ULL&&bits(r.advanced_dt)==0x3fb999999999999aULL,"Represented clock delta is NOT the performed horizon");
    require(r.clock->time_sum.lower()<=0x1.1999999999999p+0&&r.clock->time_sum.upper()>=0x1.199999999999ap+0&&r.clock->sum_rounding_error.contains(0x1.8p-54),"Exact rational known sum bounds and rounding error");
}
void guard_failure(Input x) {
    a::Progress clock{.25,11};const Frozen before(x,clock);const auto expected=g::query(x.world,x.meshes,x.horizon,x.settings);require(expected.status!=g::Status::certified_separated,"Directed source must actually fail its guard");
    const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);failed(x,clock,before,r);
    require(r.reason==a::Reason::guard_failed&&r.failure&&r.failure->stage==a::Stage::guard&&r.guard&&r.guard->status==expected.status&&r.guard->reason==expected.reason,"Actual failed owned guard is retained");
    require(r.work.guard_queries_attempted==1&&r.work.guard_queries_returned==1&&r.proposed_progress&&r.clock,"Exactly one failed guard, proposal is not an advance");
    require(r.guard->pairs.size()==expected.pairs.size()&&r.guard->work.child_calls_attempted==expected.work.child_calls_attempted&&!r.guard->candidate_bodies,"All failure pair tail/work remains, no candidate prefix commit");
}
void failures_preserve_everything() {
    auto x=minimal();x.settings.limits.held_audits=255;guard_failure(std::move(x));
    x=minimal();x.settings.limits.propagations=1;guard_failure(std::move(x));
    x=minimal();x.settings.limits.primitive_audits=1020;guard_failure(std::move(x));
    x=minimal();x.world.find_body(101)->mass=0;guard_failure(std::move(x));
    x=minimal();x.meshes[0].id=201;guard_failure(std::move(x));
    x=minimal();x.meshes[0].triangles.front().vertices={pikapika::Vec3{1,3,0},pikapika::Vec3{3,3,0},pikapika::Vec3{1,3,2}};guard_failure(std::move(x));
    x=minimal();x.meshes[1].triangles.front().vertices={pikapika::Vec3{-3,3,0},pikapika::Vec3{-1,3,0},pikapika::Vec3{-3,3,2}};guard_failure(std::move(x));
    x=minimal();x.world.find_body(102)->position.x=-2+.53125;for(auto id:{101ULL,102ULL}) {x.world.find_body(id)->velocity={};}guard_failure(std::move(x));
    x=minimal();x.world.gravity={};x.world.find_body(101)->force={};x.world.find_body(101)->radius=1;x.world.find_body(101)->position.y=1+0x1p-31;
    const_cast<d::Plane&>(x.world.planes().front()).normal.y=1-0x1p-30;x.meshes={mesh(302,-8),mesh(301,-4)};guard_failure(std::move(x));
    x=minimal();x.world.find_body(101)->position.z=std::bit_cast<double>(0x7ff8000000009876ULL);guard_failure(std::move(x));
}
void retry_then_next_tick() {
    auto x=minimal();x.settings.limits.propagations=1;a::Progress clock{-0.,20};const Frozen initial(x,clock);
    auto denied=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);failed(x,clock,initial,denied);require(denied.guard&&denied.guard->work.child_calls_attempted==1,"Real earlier seed work before later global budget failure");
    const auto old_original=body_bits(denied.guard->preparation->snapshot->bodies.front());x.settings.limits.propagations=32;
    const Frozen retry_origin(x,clock);const auto expected=g::query(x.world,x.meshes,x.horizon,x.settings);const auto first=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);successful(x,clock,retry_origin,expected,first);
    const auto first_candidate=body_bits(first.guard->candidate_bodies->front());const Frozen next_origin(x,clock);const auto expected_next=g::query(x.world,x.meshes,x.horizon,x.settings);const auto next=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);successful(x,clock,next_origin,expected_next,next);
    require(clock.ticks==22&&bits(clock.time)==bits(.125),"Failed try consumes neither time nor tick, two successes consume exactly two");
    require(body_bits(denied.guard->preparation->snapshot->bodies.front())==old_original&&body_bits(first.guard->candidate_bodies->front())==first_candidate,"Old failed/successful evidence survives retry and next tick");
    for(const auto& b:next.guard->preparation->snapshot->bodies) {Bits load;vector(load,b.force);vector(load,b.torque);require(std::all_of(load.begin(),load.end(),[](auto v){return v==0;}),"Next tick freshly captures loads consumed to +0 after previous success");}
}
void ownership() {
    auto x=minimal();a::Progress clock{0.,0};auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);require(r.committed&&r.guard&&r.guard->candidate_bodies,"Owned successful report exists");
    auto copy=r;const auto owned=body_bits(copy.guard->candidate_bodies->front());const auto source=sources_bits(copy.guard->preparation->snapshot->meshes);
    x.world.find_body(101)->force.y=17;x.meshes[0].triangles[0].vertices[0].x=12;r.guard->candidate_bodies->front().torque.y=19;r.guard->preparation->snapshot->meshes[0].triangles[0].id=99;
    require(body_bits(copy.guard->candidate_bodies->front())==owned&&sources_bits(copy.guard->preparation->snapshot->meshes)==source,"Caller/other report mutation cannot alter full owned snapshots/candidates");
}
void environment_first() {
    auto x=minimal();x.settings.contact_margin=-1;x.horizon=-1;a::Progress clock{-0.,0};const Frozen before(x,clock);const int mode=std::fegetround();require(mode==FE_TONEAREST&&std::fesetround(FE_UPWARD)==0,"Set unsupported rounding control");
    const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);const int after=std::fegetround();const int restored=std::fesetround(mode);require(restored==0&&after==FE_UPWARD,"Caller rounding control retained/restored by test");failed(x,clock,before,r);
    require(r.reason==a::Reason::environment&&r.failure&&r.failure->stage==a::Stage::environment&&!r.guard&&!r.clock&&!r.advance_profile_checked&&r.work.guard_queries_attempted==0,"Environment precedes new binding/invalid clock/settings");
#if defined(_M_X64) || defined(__x86_64__)
    const auto csr=_mm_getcsr();_mm_setcsr(csr|0x8040U);const auto flushed=a::advance(x.world,x.meshes,x.horizon,x.settings,clock);const auto retained=_mm_getcsr();_mm_setcsr(csr);failed(x,clock,before,flushed);
    require((retained&0x8040U)==0x8040U&&flushed.reason==a::Reason::environment&&!flushed.guard&&!flushed.advance_profile_checked,"FTZ/DAZ refusal preserves caller controls; not all exception flags proof");
#endif
}
std::string hex(double value) {
    std::ostringstream out;out<<std::hex<<std::setfill('0')<<std::setw(16)<<bits(value);return out.str();
}
const char* status(a::Status value) {
    switch(value) {
        case a::Status::committed:return "committed";
        case a::Status::not_certified:return "not_certified";
        case a::Status::invalid_input:return "invalid_input";
        case a::Status::unsupported_environment:return "unsupported_environment";
        case a::Status::numerical_failure:return "numerical_failure";
    }
    throw std::runtime_error("Unknown actual advance status");
}
const char* reason(a::Reason value) {
    switch(value) {
        case a::Reason::none:return "none";
        case a::Reason::environment:return "environment";
        case a::Reason::binding_unsupported:return "binding_unsupported";
        case a::Reason::horizon:return "horizon";
        case a::Reason::progress_time:return "progress_time";
        case a::Reason::progress_ticks:return "progress_ticks";
        case a::Reason::tick_limit:return "tick_limit";
        case a::Reason::time_overflow:return "time_overflow";
        case a::Reason::time_limit:return "time_limit";
        case a::Reason::time_resolution:return "time_resolution";
        case a::Reason::clock_enclosure:return "clock_enclosure";
        case a::Reason::guard_failed:return "guard_failed";
        case a::Reason::guard_incomplete:return "guard_incomplete";
        case a::Reason::origin_mismatch:return "origin_mismatch";
        case a::Reason::candidate_mismatch:return "candidate_mismatch";
        case a::Reason::candidate_validation:return "candidate_validation";
        case a::Reason::destination_mismatch:return "destination_mismatch";
        case a::Reason::allocation_failure:return "allocation_failure";
        case a::Reason::unexpected_exception:return "unexpected_exception";
    }
    throw std::runtime_error("Unknown actual advance reason");
}
void interval_json(const pikapika::interval::Interval& value) {
    std::cout<<"[\""<<hex(value.lower())<<"\",\""<<hex(value.upper())<<"\"]";
}
void clock_fixtures() {
    struct Case {const char* name;double time,horizon;std::uint64_t ticks;};
    const std::array<Case,18> cases{{
        {"zero-dyadic",0.,.0625,0},
        {"negative-zero-original",-0.,.0625,7},
        {"one-plus-point-one-rounding",1.,.1,9},
        {"minimum-positive-horizon",0.,std::numeric_limits<double>::denorm_min(),0},
        {"last-valid-tick",0.,.0625,a::maximum_ticks-1},
        {"time-limit-exceeded",1e9,.1,2},
        {"time-resolution-at-limit",1e9,std::numeric_limits<double>::denorm_min(),2},
        {"time-resolution-at-one",1.,0x1p-60,2},
        {"zero-horizon",.25,0.,3},
        {"negative-zero-horizon",.25,-0.,3},
        {"negative-horizon",.25,-.0625,3},
        {"horizon-above-cap",.25,std::nextafter(.1,1.),3},
        {"negative-time",-std::numeric_limits<double>::denorm_min(),.0625,3},
        {"time-above-cap",std::nextafter(1e9,std::numeric_limits<double>::infinity()),.0625,3},
        {"ticks-at-limit",-0.,.0625,a::maximum_ticks},
        {"ticks-outside-domain",0.,.0625,a::maximum_ticks+1},
        {"nonzero-exact-dyadic",.125,.0625,17},
        {"time-limit-equality",1e9-.0625,.0625,3}
    }};
    std::cout<<"{\"schema\":1,\"kind\":\"world-static-mesh-flight-advance-clock-fixtures\",\"cases\":[";
    for(std::size_t i=0;i<cases.size();++i) {
        const auto& c=cases[i];Input x;x.world.gravity={0.,0.,0.};x.meshes={mesh(301,-4.)};x.horizon=c.horizon;
        a::Progress progress{c.time,c.ticks};const Frozen original(x,progress);const auto r=a::advance(x.world,x.meshes,x.horizon,x.settings,progress);
        require(r.advance_profile_checked&&r.advance_profile_matches,"Clock fixtures require configured expanded source identity; actual artifact audit separate");
        original.fixed(x);
        if(!r.committed) {failed(x,progress,original,r);require(!r.guard&&r.work.guard_queries_attempted==0&&r.work.guard_queries_returned==0,"Clock failure cases must stop before the empty-World guard");}
        else {require(r.guard&&r.guard->status==g::Status::certified_separated&&r.work.guard_queries_attempted==1&&r.work.guard_queries_returned==1&&r.work.body_assignments==0&&r.work.progress_assignments==1,"Valid-clock empty World still executes its own complete guard exactly once");}
        if(i!=0) {std::cout<<',';}
        std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"timeBits\":\""<<hex(c.time)<<"\",\"horizonBits\":\""<<hex(c.horizon)<<"\",\"ticks\":"<<c.ticks<<"},\"output\":{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"committed\":"<<(r.committed?"true":"false")<<",\"advancedDtBits\":\""<<hex(r.advanced_dt)<<"\",\"actualTimeBits\":\""<<hex(progress.time)<<"\",\"actualTicks\":"<<progress.ticks;
        std::cout<<",\"originalTimeBits\":\""<<hex(r.original_progress.time)<<"\",\"originalTicks\":"<<r.original_progress.ticks<<",\"requestedDtBits\":\""<<hex(r.requested_dt)<<"\",\"advanceProfileChecked\":"<<(r.advance_profile_checked?"true":"false")<<",\"advanceProfileMatches\":"<<(r.advance_profile_matches?"true":"false");
        std::cout<<",\"proposedTimeBits\":";
        if(r.proposed_progress) {std::cout<<'"'<<hex(r.proposed_progress->time)<<'"';}else {std::cout<<"null";}
        std::cout<<",\"proposedTicks\":";if(r.proposed_progress) {std::cout<<r.proposed_progress->ticks;}else {std::cout<<"null";}
        std::cout<<",\"clock\":";
        if(r.clock) {std::cout<<"{\"sum\":";interval_json(r.clock->time_sum);std::cout<<",\"difference\":";interval_json(r.clock->represented_difference);std::cout<<",\"error\":";interval_json(r.clock->sum_rounding_error);std::cout<<",\"representedDtBits\":\""<<hex(r.clock->represented_dt)<<"\"}";}else {std::cout<<"null";}
        std::cout<<",\"guardQueriesAttempted\":"<<r.work.guard_queries_attempted<<",\"guardQueriesReturned\":"<<r.work.guard_queries_returned<<",\"bodyAssignments\":"<<r.work.body_assignments<<",\"progressAssignments\":"<<r.work.progress_assignments<<"}}";
    }
    std::cout<<"]}\n";
}
static_assert(std::is_nothrow_copy_assignable_v<d::RigidBody>);
static_assert(std::is_nothrow_copy_assignable_v<a::Progress>);
static_assert(std::is_nothrow_move_constructible_v<a::AdvanceReport>);
static_assert(noexcept(a::advance(std::declval<d::World&>(),std::declval<std::span<const g::StaticMeshSource>>(),.0625,std::declval<const g::GuardSettings&>(),std::declval<a::Progress&>())));
}
int main(int argc,char** argv) {
    try {
        require(argc==2,"Usage: world advance tests --run | --unsupported-profile | --clock-fixtures");const std::string_view mode(argv[1]);
        if(mode=="--unsupported-profile") {unsupported_profile();environment_first();std::cout<<"World static mesh flight advance: actual default NEW TU refusal and environment-priority checks PASS; no successful advance/clock artifact acceptance claimed.\n";return 0;}
        require(mode=="--run"||mode=="--clock-fixtures","Unknown CLI mode");require(g::current_binding().state==g::BindingState::ready,"Prototype requires matching configured expanded source identity; actual artifact audit separate");
        if(mode=="--clock-fixtures") {clock_fixtures();return 0;}
        minimal_success();closed_form_motion();mixed_static();invalid_clocks();represented_clock_difference();failures_preserve_everything();retry_then_next_tick();ownership();environment_first();
        std::cout<<"World static mesh flight advance: 9 directed groups PASS. Actual commit/candidate correspondence and independent exact dyadic motion/clock examples; no response/TOI/FixedClock/SDK integration or allocator/nonreturn injection.\n";return 0;
    } catch(const std::exception& error) {std::cerr<<"World static mesh flight advance FAIL: "<<error.what()<<'\n';return 1;}
}
