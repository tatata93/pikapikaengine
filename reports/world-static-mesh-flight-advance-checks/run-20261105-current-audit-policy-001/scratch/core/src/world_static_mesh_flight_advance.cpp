#include "pikapika/world_static_mesh_flight_advance.hpp"
#include <array>
#include <bit>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <limits>
#include <new>
#include <tuple>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error World static mesh flight advance requires strict floating point.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::world_static_mesh_flight_advance {
namespace {
namespace guard=world_static_mesh_flight_guard;
namespace prep=world_static_mesh_flight;
namespace flight=sphere_triangle_mesh_free_flight_guard;
namespace metric=accelerated_pair_coverage;
namespace plane=accelerated_plane_box_coverage;
namespace sphere=accelerated_sphere_box_coverage;
using I=interval::Interval;
using Body=dynamics::RigidBody;
using BodyBuffer=std::array<Body,hard_max_bodies>;
using Destinations=std::array<Body*,hard_max_bodies>;
inline constexpr std::size_t maximum_call_records=2*guard::hard_max_pair_records;
static_assert(sizeof(double)==8&&std::numeric_limits<double>::is_iec559&&std::numeric_limits<double>::digits==53&&FLT_EVAL_METHOD==0);
static_assert(std::is_nothrow_copy_constructible_v<Progress>&&std::is_nothrow_copy_assignable_v<Progress>);
static_assert(std::is_nothrow_copy_constructible_v<Body>&&std::is_nothrow_copy_assignable_v<Body>);
static_assert(std::is_nothrow_copy_constructible_v<GuardSettings>);
static_assert(std::is_nothrow_move_constructible_v<guard::GuardResult>);
static_assert(std::is_nothrow_move_constructible_v<AdvanceReport>);
static_assert(std::is_nothrow_destructible_v<AdvanceReport>);

struct Stop {
    Status status;
    Reason reason;
    Stage stage;
    std::optional<prep::FailureLocation> object;
    const char* text;
};
[[noreturn]] void stop(Status status,Reason reason,Stage stage,const char* text,
                       std::optional<prep::FailureLocation> object={}) {
    throw Stop{status,reason,stage,object,text};
}
void check(bool condition,Reason reason,Stage stage,const char* text,
           std::optional<prep::FailureLocation> object={}) {
    if(!condition) {stop(Status::numerical_failure,reason,stage,text,object);}
}
prep::FailureLocation location(prep::ObjectKind kind,std::optional<std::size_t> index={},
                               std::optional<std::size_t> face={}) noexcept {
    return {kind,index,face};
}
void fail(AdvanceReport& out,Status status,Reason reason,Stage stage,const char* text,
          std::optional<prep::FailureLocation> object={}) noexcept {
    out.status=status;out.reason=reason;out.committed=false;out.advanced_dt=0.0;
    out.work.body_assignments=0;out.work.progress_assignments=0;
    out.failure=Failure{stage,object};
    try {out.message=text;}catch(...) {out.message.clear();}
}
bool bits(double a,double b) noexcept {
    return std::bit_cast<std::uint64_t>(a)==std::bit_cast<std::uint64_t>(b);
}
bool same(Vec3 a,Vec3 b) noexcept {return bits(a.x,b.x)&&bits(a.y,b.y)&&bits(a.z,b.z);}
bool same(Quaternion a,Quaternion b) noexcept {
    return bits(a.x,b.x)&&bits(a.y,b.y)&&bits(a.z,b.z)&&bits(a.w,b.w);
}
bool same(dynamics::Material a,dynamics::Material b) noexcept {
    return bits(a.restitution,b.restitution)&&bits(a.friction,b.friction);
}
bool same(const Body& a,const Body& b) noexcept {
    return a.id==b.id&&a.is_static==b.is_static&&bits(a.mass,b.mass)&&same(a.inertia_diagonal,b.inertia_diagonal)&&
        bits(a.radius,b.radius)&&same(a.position,b.position)&&same(a.velocity,b.velocity)&&
        same(a.angular_momentum,b.angular_momentum)&&same(a.orientation,b.orientation)&&
        same(a.force,b.force)&&same(a.torque,b.torque)&&same(a.material,b.material);
}
bool same(const dynamics::Plane& a,const dynamics::Plane& b) noexcept {
    return a.id==b.id&&same(a.normal,b.normal)&&bits(a.offset,b.offset)&&same(a.material,b.material);
}
bool same(const sphere_triangle::StaticTriangle& a,const sphere_triangle::StaticTriangle& b) noexcept {
    if(a.id!=b.id) {return false;}
    for(std::size_t i=0;i<3;++i) {if(!same(a.vertices[i],b.vertices[i])) {return false;}}
    return true;
}
bool finite(const I& x) noexcept {return std::isfinite(x.lower())&&std::isfinite(x.upper());}
bool exact(const guard::Counter& count) noexcept {return count.exact&&count.known==count.upper;}
bool exact(const guard::Work& work) noexcept {
    const auto& h=work.held;
    return work.exact&&exact(h.mesh_queries)&&exact(h.primitive_queries)&&exact(h.candidates_examined)&&
        exact(h.primitive_sqrt_refinements)&&exact(h.enclosure_sqrt_refinements)&&exact(h.sqrt_refinements)&&
        exact(h.mesh_sqrt_limited_rows)&&exact(h.enclosure_sqrt_calls)&&exact(h.enclosure_sqrt_limited_calls)&&
        exact(work.propagation_attempts)&&exact(work.plane_metric_values)&&exact(work.box_values)&&
        exact(work.sphere_sqrt_refinements)&&exact(work.sqrt_refinements);
}

bool advance_binding_matches(const guard::BindingInfo& binding) noexcept {
#if defined(PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE) && PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE == 1 && defined(PIKAPIKA_WORLD_FLIGHT_BUILD_ID) && !defined(_M_ARM64EC) && !defined(__wasm__) && !defined(__clang__) && ((defined(_MSC_VER) && _MSC_VER == 1951 && defined(_M_X64)) || (defined(__GNUC__) && __GNUC__ == 13 && defined(__x86_64__) && defined(__SSE2__)))
    constexpr char identity[]=PIKAPIKA_WORLD_FLIGHT_BUILD_ID;
    if(sizeof(identity)!=65||!binding.checked||binding.mode!=guard::BindingMode::source_enforced||
       binding.profile!=1||binding.state!=guard::BindingState::ready) {return false;}
    for(std::size_t i=0;i<64;++i) {
        const char c=identity[i];
        if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))||binding.build_id[i]!=c) {return false;}
    }
    return binding.build_id[64]=='\0';
#else
    (void)binding;
    return false;
#endif
}

Status failed_guard_status(guard::Status status) noexcept {
    switch(status) {
    case guard::Status::not_certified:return Status::not_certified;
    case guard::Status::invalid_input:return Status::invalid_input;
    case guard::Status::unsupported_environment:return Status::unsupported_environment;
    case guard::Status::numerical_failure:return Status::numerical_failure;
    case guard::Status::certified_separated:return Status::numerical_failure;
    }
    return Status::numerical_failure;
}

void clock_preflight(AdvanceReport& out) {
    const auto& original=out.original_progress;
    const double h=out.requested_dt;
    if(!std::isfinite(h)||h<=0||h>maximum_horizon) {
        stop(Status::invalid_input,Reason::horizon,Stage::clock,"Horizon outside advance domain");
    }
    if(!std::isfinite(original.time)||original.time<0||original.time>maximum_time) {
        stop(Status::invalid_input,Reason::progress_time,Stage::clock,"Progress time outside advance domain");
    }
    if(original.ticks>maximum_ticks) {
        stop(Status::invalid_input,Reason::progress_ticks,Stage::clock,"Progress tick outside advance domain");
    }
    if(original.ticks==maximum_ticks) {
        stop(Status::invalid_input,Reason::tick_limit,Stage::clock,"Progress tick cannot advance");
    }
    // The new TU's strict binary64 build contract is an integration requirement,
    // not inherited merely because the old guard object has been audited.
    const double next=original.time+h;
    if(!std::isfinite(next)) {
        stop(Status::numerical_failure,Reason::time_overflow,Stage::clock,"Progress time sum is nonfinite");
    }
    if(next>maximum_time) {
        stop(Status::invalid_input,Reason::time_limit,Stage::clock,"Proposed time exceeds advance domain");
    }
    if(!(next>original.time)) {
        stop(Status::not_certified,Reason::time_resolution,Stage::clock,"Horizon absorbed by represented clock");
    }
    out.proposed_progress=Progress{next,original.ticks+1};
    const double represented=next-original.time;
    const auto sum=I::point(original.time)+I::point(h);
    const auto difference=I::point(next)-I::point(original.time);
    const auto error=I::point(next)-sum;
    check(std::isfinite(represented)&&represented>0&&finite(sum)&&finite(difference)&&finite(error)&&
          sum.contains(next)&&difference.contains(represented),Reason::clock_enclosure,Stage::clock,
          "Clock diagnostic enclosure is invalid");
    out.clock.emplace(ClockAudit{sum,difference,error,represented});
}

void check_ref(const prep::ColliderRef& ref,const prep::Snapshot& snapshot) {
    bool valid=false;
    switch(ref.kind) {
    case prep::ColliderKind::body:
        valid=ref.ordinal<snapshot.bodies.size()&&ref.id==snapshot.bodies[ref.ordinal].id&&ref.revision==0;
        break;
    case prep::ColliderKind::plane:
        valid=ref.ordinal<snapshot.planes.size()&&ref.id==snapshot.planes[ref.ordinal].id&&ref.revision==0;
        break;
    case prep::ColliderKind::mesh:
        valid=ref.ordinal<snapshot.meshes.size()&&ref.id==snapshot.meshes[ref.ordinal].id&&
            ref.revision==snapshot.meshes[ref.ordinal].revision;
        break;
    }
    check(valid,Reason::guard_incomplete,Stage::guard,"Prepared typed collider reference is inconsistent");
}

struct CallChecks {
    std::array<bool,maximum_call_records> seen{};
    std::size_t calls{},mesh{},metric{},plane{},sphere{};
};
template<class Call,class Accepted> void check_call(const Call& call,Accepted accepted,CallChecks& totals,AdvanceReport& out) {
    check(call.granted&&call.state==guard::CallState::returned&&call.attempt_ordinal&&call.result&&
          *call.attempt_ordinal<totals.seen.size(),Reason::guard_incomplete,Stage::guard,"Required numerical call did not return");
    const auto ordinal=*call.attempt_ordinal;
    check(!totals.seen[ordinal]&&accepted(*call.result),Reason::guard_incomplete,Stage::guard,
          "Required numerical call is duplicate or not certified");
    totals.seen[ordinal]=true;++totals.calls;++out.work.call_records_checked;
}

void guard_preflight(AdvanceReport& out) {
    check(out.guard.has_value(),Reason::guard_incomplete,Stage::guard,"Guard result missing");
    const auto& g=*out.guard;
    if(g.status!=guard::Status::certified_separated) {
        stop(failed_guard_status(g.status),Reason::guard_failed,Stage::guard,"Current World guard did not certify all pairs");
    }
    check(g.binding.mode==out.binding.mode&&g.binding.state==out.binding.state&&g.binding.checked==out.binding.checked&&
          g.binding.profile==out.binding.profile&&g.binding.build_id==out.binding.build_id,
          Reason::guard_incomplete,Stage::guard,"Guard/advance binding descriptors differ");
    check(g.reason==guard::Reason::none&&!g.failure&&g.original_settings&&g.preparation&&
          g.preparation->status==prep::Status::ready&&g.preparation->capture==prep::CaptureState::complete&&
          g.preparation->snapshot&&g.preparation->inventory&&g.candidate_bodies&&exact(g.work),
          Reason::guard_incomplete,Stage::guard,"Guard success lacks complete exact owned evidence");
    const auto& s=*g.preparation->snapshot;
    const auto& inventory=*g.preparation->inventory;
    check(bits(s.horizon,out.requested_dt)&&s.bodies.size()<=hard_max_bodies&&s.planes.size()<=prep::hard_max_planes&&
          s.meshes.size()>=1&&s.meshes.size()<=prep::hard_max_meshes&&g.bodies.size()==s.bodies.size()&&
          g.candidate_bodies->size()==s.bodies.size()&&g.pairs.size()==inventory.pairs.size()&&
          g.pairs.size()<=guard::hard_max_pair_records,Reason::guard_incomplete,Stage::guard,"Guard success source/count mismatch");
    std::size_t dynamic=0,statics=0,faces=0;
    for(const auto& b:s.bodies) {if(b.is_static) {++statics;}else {++dynamic;}}
    for(const auto& m:s.meshes) {check(m.triangles.size()<=prep::hard_max_faces,Reason::guard_incomplete,Stage::guard,"Mesh count outside guard bounds");faces+=m.triangles.size();}
    const auto b=s.bodies.size(),p=s.planes.size(),m=s.meshes.size(),n=b+p+m;
    const auto choose2=[](std::size_t count) noexcept {return count>0?count*(count-1)/2:0;};
    const auto required=dynamic*m+dynamic*p+choose2(b)-choose2(statics);
    const auto& excluded=inventory.excluded;
    check(faces<=prep::hard_max_faces&&inventory.total_faces==faces&&inventory.dynamic_bodies==dynamic&&inventory.static_bodies==statics&&
          inventory.colliders==n&&inventory.all_pairs==choose2(n)&&required==g.pairs.size()&&
          excluded.body_body==choose2(statics)&&excluded.body_plane==statics*p&&excluded.body_mesh==statics*m&&
          excluded.plane_plane==choose2(p)&&excluded.plane_mesh==p*m&&excluded.mesh_mesh==choose2(m)&&
          excluded.total==choose2(statics)+statics*p+statics*m+choose2(p)+p*m+choose2(m)&&
          inventory.all_pairs==required+excluded.total,Reason::guard_incomplete,Stage::guard,"Whole pair/exclusion accounting differs");
    std::optional<std::tuple<std::uint64_t,std::uint64_t,unsigned>> previous;
    CallChecks calls;
    for(std::size_t i=0;i<g.pairs.size();++i) {
        const auto& key=inventory.pairs[i];const auto& record=g.pairs[i];
        check_ref(key.first,s);check_ref(key.second,s);
        const auto lo=key.first.id<key.second.id?key.first.id:key.second.id;
        const auto hi=key.first.id<key.second.id?key.second.id:key.first.id;
        const auto order=std::tuple{lo,hi,static_cast<unsigned>(key.kind)};
        check(lo<hi&&(!previous||*previous<order)&&record.pair_ordinal==i&&record.state==guard::PairState::certified&&
              record.reason==guard::Reason::none&&record.execution_ordinal,Reason::guard_incomplete,Stage::guard,"Required pair is missing, duplicated or uncertified");
        previous=order;
        check(key.first.kind==prep::ColliderKind::body,Reason::guard_incomplete,Stage::guard,"Required pair first collider type");
        if(key.kind==prep::PairKind::body_mesh) {
            check(key.second.kind==prep::ColliderKind::mesh&&!s.bodies[key.first.ordinal].is_static&&std::holds_alternative<guard::MeshCall>(record.child),
                  Reason::guard_incomplete,Stage::guard,"Required mesh pair type");
            const auto& call=std::get<guard::MeshCall>(record.child);
            check_call(call,[](const flight::Result& r) noexcept {return r.status==flight::Status::certified_separated&&r.candidate&&r.snapshot&&r.tube&&r.endpoint&&r.inflated&&r.inflated->work.exact;},calls,out);
            check(record.execution_ordinal==call.attempt_ordinal,Reason::guard_incomplete,Stage::guard,"Mesh execution link");
            const auto& snapshot=*call.result->snapshot;
            check(same(snapshot.body,s.bodies[key.first.ordinal])&&same(snapshot.gravity,s.gravity)&&bits(snapshot.horizon,s.horizon)&&
                  snapshot.triangles.size()==s.meshes[key.second.ordinal].triangles.size()&&
                  same(*call.result->candidate,(*g.candidate_bodies)[key.first.ordinal]),Reason::candidate_mismatch,Stage::guard,"Mesh candidate/source common-flight link");
            for(std::size_t j=0;j<snapshot.triangles.size();++j) {
                check(same(snapshot.triangles[j],s.meshes[key.second.ordinal].triangles[j]),Reason::guard_incomplete,Stage::guard,"Mesh child source face differs");
            }
            ++calls.mesh;
        }else if(key.kind==prep::PairKind::body_plane) {
            check(key.second.kind==prep::ColliderKind::plane&&!s.bodies[key.first.ordinal].is_static&&std::holds_alternative<guard::PlaneCalls>(record.child),
                  Reason::guard_incomplete,Stage::guard,"Required plane pair type");
            const auto& call=std::get<guard::PlaneCalls>(record.child);
            check_call(call.metric,[](const metric::Result& r) noexcept {return r.status==metric::Status::certified;},calls,out);
            check_call(call.box,[](const plane::Result& r) noexcept {return r.status==plane::Status::certified;},calls,out);
            check(record.execution_ordinal==call.metric.attempt_ordinal,Reason::guard_incomplete,Stage::guard,"Plane execution link");
            ++calls.metric;++calls.plane;
        }else {
            check(key.kind==prep::PairKind::body_body&&key.second.kind==prep::ColliderKind::body&&key.first.id<key.second.id&&
                  !(s.bodies[key.first.ordinal].is_static&&s.bodies[key.second.ordinal].is_static)&&std::holds_alternative<guard::SphereCall>(record.child),
                  Reason::guard_incomplete,Stage::guard,"Required sphere pair type");
            const auto& call=std::get<guard::SphereCall>(record.child);
            check_call(call,[](const sphere::Result& r) noexcept {return r.status==sphere::Status::certified&&r.work.exact;},calls,out);
            check(record.execution_ordinal==call.attempt_ordinal,Reason::guard_incomplete,Stage::guard,"Sphere execution link");
            ++calls.sphere;
        }
        ++out.work.pair_records_checked;
    }
    for(std::size_t i=0;i<calls.seen.size();++i) {
        check(calls.seen[i]==(i<calls.calls),Reason::guard_incomplete,Stage::guard,"Child attempt ordinals are not complete");
    }
    const auto& w=g.work;
    check(w.child_calls_attempted==calls.calls&&w.child_calls_returned==calls.calls&&
          w.mesh_calls_attempted==calls.mesh&&w.mesh_calls_returned==calls.mesh&&
          w.plane_metric_calls_attempted==calls.metric&&w.plane_metric_calls_returned==calls.metric&&
          w.plane_box_calls_attempted==calls.plane&&w.plane_box_calls_returned==calls.plane&&
          w.sphere_box_calls_attempted==calls.sphere&&w.sphere_box_calls_returned==calls.sphere,
          Reason::guard_incomplete,Stage::guard,"Owned calls differ from exact outer accounting");
    for(std::size_t i=0;i<s.bodies.size();++i) {
        const auto& record=g.bodies[i];
        check(record.body_ordinal==i&&record.is_static==s.bodies[i].is_static,Reason::guard_incomplete,Stage::guard,"Original body record mapping");
        if(record.is_static) {
            check(record.state==guard::SeedState::static_copy&&!record.seed_pair_ordinal&&same((*g.candidate_bodies)[i],s.bodies[i]),
                  Reason::candidate_mismatch,Stage::guard,"Static candidate is not the original full body");
        }else {
            check(record.state==guard::SeedState::ready&&record.seed_pair_ordinal&&*record.seed_pair_ordinal<g.pairs.size(),
                  Reason::guard_incomplete,Stage::guard,"Dynamic seed is not ready");
            const auto& seed=inventory.pairs[*record.seed_pair_ordinal];
            check(seed.kind==prep::PairKind::body_mesh&&seed.first.ordinal==i,Reason::guard_incomplete,Stage::guard,"Dynamic seed typed pair");
            for(const auto& source:s.meshes) {check(seed.second.id<=source.id,Reason::guard_incomplete,Stage::guard,"Dynamic seed is not minimum stable mesh ID");}
        }
    }
}

void origin_preflight(dynamics::World& world,std::span<const StaticMeshSource> meshes,
                      Progress& progress,const AdvanceReport& out,CommitWork& work) {
    const auto& s=*out.guard->preparation->snapshot;
    const auto mismatch=[&](bool okay,prep::FailureLocation object,const char* text) {
        if(!okay) {stop(Status::not_certified,Reason::origin_mismatch,Stage::commit_preparation,text,object);}
    };
    mismatch(bits(progress.time,out.original_progress.time)&&progress.ticks==out.original_progress.ticks,
             location(prep::ObjectKind::world),"Progress changed since capture");
    mismatch(same(world.gravity,s.gravity)&&world.bodies().size()==s.bodies.size()&&world.planes().size()==s.planes.size()&&meshes.size()==s.meshes.size(),
             location(prep::ObjectKind::world),"World/source shape changed since guard snapshot");
    for(std::size_t i=0;i<s.bodies.size();++i) {
        ++work.origin_bodies_checked;
        mismatch(same(world.bodies()[i],s.bodies[i]),location(prep::ObjectKind::body,i),"World body changed since guard snapshot");
    }
    for(std::size_t i=0;i<s.planes.size();++i) {
        ++work.origin_planes_checked;
        mismatch(same(world.planes()[i],s.planes[i]),location(prep::ObjectKind::plane,i),"Raw plane changed since guard snapshot");
    }
    for(std::size_t i=0;i<s.meshes.size();++i) {
        const auto& a=meshes[i];const auto& b=s.meshes[i];
        ++work.origin_meshes_checked;
        mismatch(a.id==b.id&&a.revision==b.revision&&a.triangles.size()==b.triangles.size(),
                 location(prep::ObjectKind::mesh,i),"Mesh identity/revision/count changed since guard snapshot");
        for(std::size_t j=0;j<b.triangles.size();++j) {
            ++work.origin_faces_checked;
            mismatch(same(a.triangles[j],b.triangles[j]),location(prep::ObjectKind::face,i,j),"Mesh source face changed since guard snapshot");
        }
    }
}

void prepare_commit(dynamics::World& world,AdvanceReport& out,BodyBuffer& buffer,Destinations& destinations) {
    const auto& s=*out.guard->preparation->snapshot;
    const auto& candidates=*out.guard->candidate_bodies;
    out.storage={hard_max_bodies,hard_max_bodies,sizeof(BodyBuffer),sizeof(Destinations)};
    for(std::size_t i=0;i<candidates.size();++i) {
        const auto& candidate=candidates[i];const auto& original=s.bodies[i];
        check(candidate.id==original.id&&candidate.is_static==original.is_static&&bits(candidate.mass,original.mass)&&
              same(candidate.inertia_diagonal,original.inertia_diagonal)&&bits(candidate.radius,original.radius)&&same(candidate.material,original.material)&&
              same(candidate.force,original.force)&&same(candidate.torque,original.torque),
              Reason::candidate_mismatch,Stage::commit_preparation,"Candidate changed immutable/held-load source fields",location(prep::ObjectKind::body,i));
        buffer[i]=candidate;++out.work.candidates_copied;
        ++out.work.destination_lookups;
        auto* destination=world.find_body(original.id);
        check(destination&&destination==&world.bodies()[i],Reason::destination_mismatch,Stage::commit_preparation,
              "Destination ID/order/address mismatch",location(prep::ObjectKind::body,i));
        for(std::size_t j=0;j<i;++j) {
            check(destination!=destinations[j],Reason::destination_mismatch,Stage::commit_preparation,"Duplicate body destination",location(prep::ObjectKind::body,i));
        }
        destinations[i]=destination;++out.work.destinations_resolved;
    }
}

void validate_commit(AdvanceReport& out,BodyBuffer& buffer) {
    const auto count=out.guard->candidate_bodies->size();
    // Only the private buffer consumes loads. The complete owned proof/candidates
    // and every external World field are still untouched at this point.
    for(std::size_t i=0;i<count;++i) {
        buffer[i].force=Vec3{0.0,0.0,0.0};buffer[i].torque=Vec3{0.0,0.0,0.0};
        ++out.work.candidate_validations_attempted;
        try {buffer[i].validate();}
        catch(const std::bad_alloc&) {throw;}
        catch(...) {stop(Status::numerical_failure,Reason::candidate_validation,Stage::candidate_validation,
                        "Cleared-load candidate validation failed",location(prep::ObjectKind::body,i));}
        ++out.work.candidates_validated;
    }
}

// This is the ONLY external mutation. No allocation, lookup, interval arithmetic,
// validation, diagnostic generation or potentially throwing callback occurs here.
void commit(const BodyBuffer& bodies,const Destinations& destinations,std::size_t count,
            Progress& progress,const Progress& proposed) noexcept {
    for(std::size_t i=0;i<count;++i) {*destinations[i]=bodies[i];}
    progress=proposed;
}
}

AdvanceReport advance(dynamics::World& world,std::span<const StaticMeshSource> meshes,
                      double horizon_seconds,const GuardSettings& settings,Progress& progress) noexcept {
    AdvanceReport out;
    out.requested_dt=horizon_seconds;out.original_progress=progress;
    BodyBuffer buffer{};Destinations destinations{};
    Stage stage=Stage::environment;
    std::size_t count=0;
    try {
        if(const char* issue=interval::environment_issue()) {
            out.binding=guard::current_binding();
            stop(Status::unsupported_environment,Reason::environment,Stage::environment,issue);
        }
        stage=Stage::binding;out.binding=guard::current_binding();
        out.advance_profile_checked=true;out.advance_profile_matches=advance_binding_matches(out.binding);
        if(!out.advance_profile_matches) {
            stop(Status::unsupported_environment,Reason::binding_unsupported,Stage::binding,
                 "Advance TU lacks matching externally audited strict configuration");
        }
        stage=Stage::clock;clock_preflight(out);
        const GuardSettings captured_settings=settings;
        stage=Stage::guard;++out.work.guard_queries_attempted;
        auto result=guard::query(world,meshes,horizon_seconds,captured_settings);
        ++out.work.guard_queries_returned;
        out.guard.emplace(std::move(result));
        guard_preflight(out);
        stage=Stage::commit_preparation;
        origin_preflight(world,meshes,progress,out,out.work);
        prepare_commit(world,out,buffer,destinations);
        stage=Stage::candidate_validation;validate_commit(out,buffer);
        stage=Stage::commit_preparation;
        // Recheck full origin after all candidate validation and before preparing
        // terminal metadata. This is not a concurrent/reentrant mutation detector:
        // the caller excludes those operations for the whole synchronous call.
        origin_preflight(world,meshes,progress,out,out.work);
        count=out.guard->candidate_bodies->size();
        check(out.proposed_progress&&out.clock&&out.work.candidates_copied==count&&
              out.work.candidate_validations_attempted==count&&out.work.candidates_validated==count&&
              out.work.destination_lookups==count&&out.work.destinations_resolved==count,
              Reason::candidate_mismatch,Stage::commit_preparation,"Commit preparation incomplete");
        // Final report preparation is before the first external store. Returning
        // this local report needs only its statically no-throw move/destruction.
        out.status=Status::committed;out.reason=Reason::none;out.committed=true;out.advanced_dt=horizon_seconds;
        out.failure.reset();out.message.clear();
        out.work.body_assignments=count;out.work.progress_assignments=1;
    }catch(const Stop& failure) {
        fail(out,failure.status,failure.reason,failure.stage,failure.text,failure.object);return out;
    }catch(const std::bad_alloc&) {
        fail(out,Status::numerical_failure,Reason::allocation_failure,stage,"Advance preparation allocation failed");return out;
    }catch(...) {
        fail(out,Status::numerical_failure,Reason::unexpected_exception,stage,"Advance preparation failed");return out;
    }
    // Deliberately OUTSIDE the catch region: failure cannot be reported after a
    // partial external store. All code from here through return is no-throw.
    commit(buffer,destinations,count,progress,*out.proposed_progress);
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
