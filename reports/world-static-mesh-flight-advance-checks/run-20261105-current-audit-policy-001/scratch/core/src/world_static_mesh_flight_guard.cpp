#include "pikapika/world_static_mesh_flight_guard.hpp"
#include <algorithm>
#include <bit>
#include <cfloat>
#include <cmath>
#include <cstdint>
#include <limits>
#include <new>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error World static mesh flight guard requires strict floating point.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif
#if defined(PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE) && PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE == 1
#ifndef PIKAPIKA_WORLD_FLIGHT_BUILD_ID
#error An audited profile requires its externally audited build configuration identity.
#endif
namespace pikapika::detail {
unsigned world_predicate_binding_profile() noexcept;
const char* world_predicate_binding_build_id() noexcept;
}
#endif

namespace pikapika::world_static_mesh_flight_guard {
namespace {
namespace prep=world_static_mesh_flight;
namespace flight=sphere_triangle_mesh_free_flight_guard;
namespace held=sphere_triangle_mesh_held_load;
namespace mesh=sphere_triangle_mesh;
namespace tri=sphere_triangle;
namespace metric=accelerated_pair_coverage;
namespace plane=accelerated_plane_box_coverage;
namespace sphere=accelerated_sphere_box_coverage;
static_assert(sizeof(double)==8&&std::numeric_limits<double>::is_iec559&&std::numeric_limits<double>::digits==53&&FLT_EVAL_METHOD==0);
static_assert(std::is_nothrow_copy_constructible_v<GuardSettings>);
static_assert(std::is_nothrow_move_constructible_v<GuardResult>);
static_assert(std::is_nothrow_move_constructible_v<flight::Result>);
static_assert(std::is_nothrow_move_constructible_v<metric::Result>);
static_assert(std::is_nothrow_move_constructible_v<plane::Result>);
static_assert(std::is_nothrow_move_constructible_v<sphere::Result>);
struct Stop {Status status;Reason reason;const char* text;};
void need(bool yes,const char* text) {if(!yes) {throw Stop{Status::numerical_failure,Reason::metadata_inconsistent,text};}}
std::size_t add(std::size_t a,std::size_t b) {need(b<=std::numeric_limits<std::size_t>::max()-a,"Guard count addition overflow");return a+b;}
std::size_t mul(std::size_t a,std::size_t b) {need(a==0||b<=std::numeric_limits<std::size_t>::max()/a,"Guard count multiplication overflow");return a*b;}
void fail(GuardResult& out,Status status,Reason reason,const char* text) noexcept {
    out.status=status;out.reason=reason;out.candidate_bodies.reset();
    try {out.message=text;}catch(...) {out.message.clear();}
}
bool bits(double a,double b) noexcept {return std::bit_cast<std::uint64_t>(a)==std::bit_cast<std::uint64_t>(b);}
bool same(Vec3 a,Vec3 b) noexcept {return bits(a.x,b.x)&&bits(a.y,b.y)&&bits(a.z,b.z);}
bool same(const Quaternion& a,const Quaternion& b) noexcept {return bits(a.x,b.x)&&bits(a.y,b.y)&&bits(a.z,b.z)&&bits(a.w,b.w);}
bool same(dynamics::Material a,dynamics::Material b) noexcept {return bits(a.restitution,b.restitution)&&bits(a.friction,b.friction);}
bool same(const dynamics::RigidBody& a,const dynamics::RigidBody& b) noexcept {
    return a.id==b.id&&a.is_static==b.is_static&&bits(a.mass,b.mass)&&same(a.inertia_diagonal,b.inertia_diagonal)&&bits(a.radius,b.radius)&&
        same(a.position,b.position)&&same(a.velocity,b.velocity)&&same(a.angular_momentum,b.angular_momentum)&&same(a.orientation,b.orientation)&&same(a.force,b.force)&&same(a.torque,b.torque)&&same(a.material,b.material);
}
bool same(const tri::StaticTriangle& a,const tri::StaticTriangle& b) noexcept {
    if(a.id!=b.id) {return false;}
    for(unsigned i=0;i<3;++i) {if(!same(a.vertices[i],b.vertices[i])) {return false;}}
    return true;
}
bool same(const interval::Interval& a,const interval::Interval& b) noexcept {return bits(a.lower(),b.lower())&&bits(a.upper(),b.upper());}
bool same(const tri::Bounds3& a,const tri::Bounds3& b) noexcept {
    for(unsigned i=0;i<3;++i) {if(!same(a[i],b[i])) {return false;}}
    return true;
}
bool same(const tri::Settings& a,const tri::Settings& b) noexcept {
    return a.max_candidates==b.max_candidates&&a.sqrt_refinements==b.sqrt_refinements&&a.max_total_sqrt_refinements==b.max_total_sqrt_refinements&&
        bits(a.maximum_local_width,b.maximum_local_width)&&bits(a.maximum_normal_width,b.maximum_normal_width)&&bits(a.minimum_sine_squared,b.minimum_sine_squared);
}
bool same(const held::Settings& a,const held::Settings& b) noexcept {
    return a.mesh.max_surfaces==b.mesh.max_surfaces&&same(a.mesh.primitive,b.mesh.primitive)&&bits(a.time_tolerance,b.time_tolerance)&&a.max_evaluations==b.max_evaluations&&
        a.max_leaves==b.max_leaves&&a.max_depth==b.max_depth&&a.enclosure_sqrt_refinements==b.enclosure_sqrt_refinements&&a.max_total_sqrt_refinements==b.max_total_sqrt_refinements;
}
bool same(const flight::Settings& a,const flight::Settings& b) noexcept {return same(a.held_load,b.held_load)&&bits(a.max_angular_increment,b.max_angular_increment);}
template<class T> bool same_coverage_settings(const T& a,const T& b) noexcept {
    bool yes=bits(a.time_tolerance,b.time_tolerance)&&a.max_evaluations==b.max_evaluations&&a.max_leaves==b.max_leaves&&a.max_depth==b.max_depth;
    if constexpr(requires {a.sqrt_refinements;}) {yes=yes&&a.sqrt_refinements==b.sqrt_refinements;}
    return yes;
}
bool same(const accelerated::Sphere& a,const accelerated::Sphere& b) noexcept {return same(a.center,b.center)&&same(a.velocity,b.velocity)&&same(a.acceleration,b.acceleration)&&bits(a.radius,b.radius);}
bool same(const accelerated::StaticPlane& a,const accelerated::StaticPlane& b) noexcept {return same(a.normal,b.normal)&&bits(a.offset,b.offset);}
bool finite(const interval::Interval& x) noexcept {return std::isfinite(x.lower())&&std::isfinite(x.upper());}
bool valid_mesh_profile(const flight::Settings& x) noexcept {
    const auto& s=x.held_load;const auto& p=s.mesh.primitive;
    return s.mesh.max_surfaces>=1&&s.mesh.max_surfaces<=64&&p.max_candidates>=1&&p.max_candidates<=7&&p.sqrt_refinements>=1&&p.sqrt_refinements<=256&&
        p.max_total_sqrt_refinements>=1&&p.max_total_sqrt_refinements<=1024&&std::isfinite(p.maximum_local_width)&&p.maximum_local_width>0&&p.maximum_local_width<=1e6&&
        std::isfinite(p.maximum_normal_width)&&p.maximum_normal_width>0&&p.maximum_normal_width<=2&&std::isfinite(p.minimum_sine_squared)&&p.minimum_sine_squared>0&&p.minimum_sine_squared<=1&&
        std::isfinite(s.time_tolerance)&&s.time_tolerance>0&&s.time_tolerance<=.1&&s.max_evaluations>=1&&s.max_evaluations<=256&&s.max_leaves>=1&&s.max_leaves<=128&&s.max_depth<=32&&
        s.enclosure_sqrt_refinements>=1&&s.enclosure_sqrt_refinements<=256&&s.max_total_sqrt_refinements>=1&&s.max_total_sqrt_refinements<=16777216&&
        std::isfinite(x.max_angular_increment)&&x.max_angular_increment>0&&x.max_angular_increment<=3.141592653589793238462643383279502884;
}
template<class T> bool valid_coverage(const T& s) noexcept {
    bool yes=std::isfinite(s.time_tolerance)&&s.time_tolerance>0&&s.time_tolerance<=.1&&s.max_evaluations>=1&&s.max_evaluations<=255&&s.max_leaves>=1&&s.max_leaves<=128&&s.max_depth<=32;
    if constexpr(requires {s.sqrt_refinements;}) {yes=yes&&s.sqrt_refinements>=1&&s.sqrt_refinements<=256;}
    return yes;
}
bool valid_limits(const Limits& x) noexcept {
    return x.body_records>=1&&x.body_records<=8&&x.pair_records>=1&&x.pair_records<=256&&
        x.held_audits>=1&&x.held_audits<=1024&&x.held_certified_leaves>=1&&x.held_certified_leaves<=1024&&x.held_partition>=1&&x.held_partition<=1024&&x.held_frontier>=1&&x.held_frontier<=1024&&
        x.primitive_audits>=1&&x.primitive_audits<=1024&&x.primitive_partition>=1&&x.primitive_partition<=1024&&x.primitive_frontier>=1&&x.primitive_frontier<=1024&&
        x.last_mesh_rows>=1&&x.last_mesh_rows<=512&&x.primitive_candidates>=1&&x.primitive_candidates<=3584&&x.retained_faces>=1&&x.retained_faces<=1600&&
        x.mesh_queries>=1&&x.mesh_queries<=1024&&x.primitive_queries>=1&&x.primitive_queries<=65536&&x.candidates_examined>=1&&x.candidates_examined<=458752&&
        x.sqrt_refinements>=1&&x.sqrt_refinements<=16777216&&x.plane_metric_values>=1&&x.plane_metric_values<=1048576&&x.box_values>=1&&x.box_values<=1048576&&
        x.propagations>=1&&x.propagations<=32&&x.logical_payload_bytes>=1&&x.logical_payload_bytes<=hard_max_logical_payload;
}
#define RETAINED_FIELDS(X) X(body_records) X(pair_records) X(held_audits) X(held_certified_leaves) X(held_partition) X(held_frontier) X(primitive_audits) X(primitive_partition) X(primitive_frontier) X(last_mesh_rows) X(primitive_candidates) X(retained_faces) X(logical_payload_bytes)
#define GRANT_FIELDS(X) X(mesh_queries) X(primitive_queries) X(candidates_examined) X(sqrt_refinements) X(propagations) X(plane_metric_values) X(box_values) X(plane_norm_loop_iterations_upper) X(bridge_calls_upper)
Retained sum(Retained a,const Retained& b) {
#define PLUS(f) a.f=add(a.f,b.f);
    RETAINED_FIELDS(PLUS)
#undef PLUS
    return a;
}
WorkGrant sum(WorkGrant a,const WorkGrant& b) {
#define PLUS(f) a.f=add(a.f,b.f);
    GRANT_FIELDS(PLUS)
#undef PLUS
    return a;
}
WorkGrant replace(WorkGrant a,const WorkGrant& old,const WorkGrant& now) {
#define CHANGE(f) need(a.f>=old.f&&now.f<=old.f,"Returned work exceeds its reserved grant");a.f=add(a.f-old.f,now.f);
    GRANT_FIELDS(CHANGE)
#undef CHANGE
    return a;
}
bool fits(const Retained& x,const Limits& l) noexcept {
    bool ok=true;
#define CHECK(f) ok=ok&&x.f<=l.f;
    RETAINED_FIELDS(CHECK)
#undef CHECK
    return ok;
}
bool fits(const WorkGrant& x,const Limits& l) noexcept {
    return x.mesh_queries<=l.mesh_queries&&x.primitive_queries<=l.primitive_queries&&x.candidates_examined<=l.candidates_examined&&x.sqrt_refinements<=l.sqrt_refinements&&
        x.propagations<=l.propagations&&x.plane_metric_values<=l.plane_metric_values&&x.box_values<=l.box_values&&x.plane_norm_loop_iterations_upper<=64*l.plane_metric_values&&x.bridge_calls_upper<=32;
}
Counter counter(std::size_t known,std::size_t upper,bool exact) {need(known<=upper&&(!exact||known==upper),"Invalid returned known/upper work");return {known,upper,exact};}
void accumulate(Counter& a,const Counter& b) {a.known=add(a.known,b.known);a.upper=add(a.upper,b.upper);a.exact=a.exact&&b.exact;}
void sync(GuardResult& out) {
    out.work.sqrt_refinements=out.work.held.sqrt_refinements;accumulate(out.work.sqrt_refinements,out.work.sphere_sqrt_refinements);
    out.work.exact=out.work.exact&&out.work.held.mesh_queries.exact&&out.work.held.primitive_queries.exact&&out.work.held.candidates_examined.exact&&out.work.held.sqrt_refinements.exact&&
        out.work.propagation_attempts.exact&&out.work.plane_metric_values.exact&&out.work.box_values.exact&&out.work.sphere_sqrt_refinements.exact;
}
void charge(GuardResult& out,const Grant& g) {
    const auto storage=sum(out.reservation.retained,g.retained);const auto work=sum(out.reservation.charged,g.work);
    if(!fits(storage,out.original_settings->limits)) {throw Stop{Status::not_certified,Reason::storage_budget,"Guard retained storage budget exhausted"};}
    if(!fits(work,out.original_settings->limits)) {throw Stop{Status::not_certified,Reason::work_budget,"Guard work reservation exhausted"};}
    out.reservation.retained=storage;out.reservation.charged=work;out.reservation.granted=sum(out.reservation.granted,g.work);
}
void settle(GuardResult& out,const Grant& g,const WorkGrant& actual) {out.reservation.charged=replace(out.reservation.charged,g.work,actual);}
void strip(std::string& text,MessageOmission& m) {
    m.fields=add(m.fields,1);m.bytes=add(m.bytes,text.size());
    if(!text.empty()) {m.nonempty_fields=add(m.nonempty_fields,1);m.omitted=true;}
    std::string{}.swap(text);
}
void strip(mesh::Result& x,MessageOmission& m) {strip(x.message,m);for(auto& row:x.rows) {if(row.query) {strip(row.query->message,m);}}}
void strip(flight::Result& x,MessageOmission& m) {strip(x.message,m);if(x.inflated) {strip(x.inflated->message,m);if(x.inflated->last_mesh) {strip(*x.inflated->last_mesh,m);}}}
void payload(Retained& r,std::size_t count,std::size_t size) {r.logical_payload_bytes=add(r.logical_payload_bytes,mul(count,size));}
Retained initial_request(const prep::Snapshot& s,const prep::Inventory& inv) {
    Retained r;r.body_records=s.bodies.size();r.pair_records=inv.pairs.size();r.retained_faces=inv.total_faces;r.logical_payload_bytes=sizeof(GuardResult);
    payload(r,s.bodies.size(),sizeof(BodyRecord)+2*sizeof(dynamics::RigidBody));
    payload(r,s.planes.size(),sizeof(dynamics::Plane));payload(r,s.meshes.size(),sizeof(StaticMeshSource));
    payload(r,inv.pairs.size(),sizeof(PairRecord)+sizeof(prep::Pair));payload(r,inv.total_faces,sizeof(tri::StaticTriangle));return r;
}
Grant mesh_grant(std::size_t n,const flight::Settings& s) {
    Grant g;const auto e=s.held_load.max_evaluations,l=s.held_load.max_leaves;
    auto& r=g.retained;r.held_audits=e;r.held_certified_leaves=l;r.held_partition=l;r.held_frontier=l;r.last_mesh_rows=n;r.primitive_candidates=mul(n,7);r.retained_faces=mul(n,3);
    payload(r,e,sizeof(held::CellAudit));payload(r,l,sizeof(held::CertifiedLeaf)+sizeof(held::PartitionLeaf)+sizeof(held::Cell));
    payload(r,n,sizeof(mesh::Row)+2*sizeof(tri::StaticTriangle)+2*sizeof(std::uint64_t));
    payload(r,mul(n,7),sizeof(tri::CandidateAudit));
    g.work.mesh_queries=e;g.work.primitive_queries=mul(e,n);g.work.candidates_examined=mul(g.work.primitive_queries,7);
    g.work.sqrt_refinements=std::min(s.held_load.max_total_sqrt_refinements,mul(e,add(mul(n,512),1024)));g.work.propagations=1;g.work.bridge_calls_upper=1;return g;
}
template<class Coverage> Grant coverage_grant(std::size_t e,std::size_t leaves) {
    Grant g;g.retained.primitive_audits=e;g.retained.primitive_partition=leaves;g.retained.primitive_frontier=leaves;
    payload(g.retained,e,sizeof(typename Coverage::audit_type));payload(g.retained,leaves,sizeof(typename Coverage::leaf_type)+sizeof(typename Coverage::cell_type));return g;
}
struct MetricTypes {using audit_type=metric::Audit;using leaf_type=metric::PartitionLeaf;using cell_type=metric::Cell;};
struct PlaneTypes {using audit_type=plane::Audit;using leaf_type=plane::PartitionLeaf;using cell_type=plane::Cell;};
struct SphereTypes {using audit_type=sphere::Audit;using leaf_type=sphere::PartitionLeaf;using cell_type=sphere::Cell;};
std::size_t remaining(std::size_t limit,std::size_t used) {need(used<=limit,"Guard reservation exceeds its limit");return limit-used;}
std::size_t grant_e(const GuardResult& out,std::size_t requested,bool is_metric,unsigned ref=0) {
    const auto& l=out.original_settings->limits;const auto& r=out.reservation;
    auto e=std::min(requested,remaining(l.primitive_audits,r.retained.primitive_audits));
    e=std::min(e,is_metric?remaining(l.plane_metric_values,r.charged.plane_metric_values):remaining(l.box_values,r.charged.box_values));
    if(ref) {e=std::min(e,remaining(l.sqrt_refinements,r.charged.sqrt_refinements)/(2*static_cast<std::size_t>(ref)));}
    return e;
}
const prep::Snapshot& snapshot(const GuardResult& out) {return *out.preparation->snapshot;}
const prep::Pair& pair_source(const GuardResult& out,std::size_t i) {return out.preparation->inventory->pairs[i];}
void same_triangles(std::span<const tri::StaticTriangle> expected,std::span<const tri::StaticTriangle> actual) {
    need(actual.size()==expected.size(),"Child source count changed");
    for(std::size_t i=0;i<expected.size();++i) {need(same(expected[i],actual[i]),"Child source bits/order/ID changed");}
}
void validate_mesh_source(const flight::Result& x,const prep::Snapshot& s,const prep::Pair& p,const flight::Settings& settings) {
    const auto& body=s.bodies[p.first.ordinal];const auto& source=s.meshes[p.second.ordinal].triangles;
    need(x.world_body&&same(x.world_body->body,body)&&same(x.world_body->gravity,s.gravity),"Child selected-body original differs");
    if(x.snapshot) {
        need(same(x.snapshot->body,body)&&same(x.snapshot->gravity,s.gravity)&&bits(x.snapshot->horizon,s.horizon)&&same(x.snapshot->settings,settings),"Child snapshot/profile differs");
        same_triangles(source,x.snapshot->triangles);
    }
    if(x.inflated) {
        need(x.tube&&x.snapshot,"Inflated child has no original/tube");
        if(x.inflated->snapshot) {
            const auto& q=*x.inflated->snapshot;const auto& a=q.input;
            need(a.id==body.id&&same(a.position,body.position)&&same(a.velocity,body.velocity)&&bits(a.mass,body.mass)&&same(a.force,body.force)&&same(a.gravity,s.gravity)&&bits(a.radius,x.tube->guard_radius),"Inflated input/original radius ownership differs");
            need(bits(q.horizon,s.horizon)&&same(q.settings,settings.held_load),"Inflated horizon/profile changed");same_triangles(source,q.triangles);
        }
        if(x.inflated->last_mesh) {
            const auto& last=*x.inflated->last_mesh;need(last.rows.size()<=source.size(),"Last mesh source count overflow");
            for(std::size_t i=0;i<last.rows.size();++i) {need(same(last.rows[i].triangle,source[i]),"Last mesh row source bits differ");}
            need(x.inflated->last_mesh_audit_index&&*x.inflated->last_mesh_audit_index<x.inflated->audits.size()&&x.inflated->audits[*x.inflated->last_mesh_audit_index].mesh_queried,"Last mesh audit ownership/link missing");
        }else {need(!x.inflated->last_mesh_audit_index,"Last mesh absent with audit link");}
    }
    if(x.status==flight::Status::certified_separated) {
        need(x.snapshot&&x.tube&&x.endpoint&&x.candidate_evaluated&&x.candidate&&x.inflated&&x.inflated->snapshot&&x.inflated->status==held::Status::separated&&x.inflated->work.exact,
             "Certified mesh child lacks full exact proof/candidate");
        need(x.endpoint->nominal_contained&&x.endpoint->exact_contained&&x.endpoint->l1_within_tube,"Certified endpoint flags are not all true");
        need(x.candidate->id==body.id&&!x.candidate->is_static&&bits(x.candidate->mass,body.mass)&&same(x.candidate->inertia_diagonal,body.inertia_diagonal)&&bits(x.candidate->radius,body.radius)&&same(x.candidate->force,body.force)&&same(x.candidate->torque,body.torque)&&same(x.candidate->material,body.material),"Candidate changed immutable body/load fields");
    }else {need(!x.candidate,"Failed mesh child published candidate");}
}
bool same_flight(const flight::Result& a,const flight::Result& b) noexcept {
    if(!a.tube||!b.tube||!a.endpoint||!b.endpoint||!a.candidate||!b.candidate) {return false;}
    const auto& x=*a.tube;const auto& y=*b.tube;const auto& e=*a.endpoint;const auto& f=*b.endpoint;
    return same(x.nominal_acceleration,y.nominal_acceleration)&&same(x.exact_acceleration,y.exact_acceleration)&&same(x.acceleration_difference,y.acceleration_difference)&&
        bits(x.position_error,y.position_error)&&bits(x.roundoff,y.roundoff)&&bits(x.guard_radius,y.guard_radius)&&same(e.nominal_position,f.nominal_position)&&same(e.nominal_allowed,f.nominal_allowed)&&
        same(e.exact_position,f.exact_position)&&same(e.exact_allowed,f.exact_allowed)&&same(e.exact_difference,f.exact_difference)&&same(e.l1_error_bound,f.l1_error_bound)&&
        e.nominal_contained==f.nominal_contained&&e.exact_contained==f.exact_contained&&e.l1_within_tube==f.l1_within_tube&&same(*a.candidate,*b.candidate);
}
void mesh_work(GuardResult& out,const MeshCall& call,bool returned) {
    const auto& g=call.grant;const held::Work* w=returned&&call.result->inflated?&call.result->inflated->work:nullptr;
    const bool exact=returned&&(!w||w->exact);const auto n=g.retained.last_mesh_rows,e=g.retained.held_audits;
    const auto primitive_bound=std::min(g.work.sqrt_refinements,mul(mul(e,n),512)),enclosure_bound=std::min(g.work.sqrt_refinements,mul(e,1024));
    auto add_counter=[&](Counter& target,std::size_t known,std::size_t upper) {accumulate(target,counter(known,upper,exact));};
    auto known=[&](std::size_t held::Work::*field) {return w?w->*field:0;};
    const auto mq=known(&held::Work::mesh_queries),pq=known(&held::Work::primitive_queries),ce=known(&held::Work::candidates_examined);
    const auto sr=known(&held::Work::sqrt_refinements),su=returned?(w?w->sqrt_refinements_upper:0):g.work.sqrt_refinements;
    need(mq<=g.work.mesh_queries&&pq<=g.work.primitive_queries&&ce<=g.work.candidates_examined&&sr<=su&&su<=g.work.sqrt_refinements,"Mesh returned work exceeds reserved bound");
    add_counter(out.work.held.mesh_queries,mq,exact?mq:g.work.mesh_queries);
    add_counter(out.work.held.primitive_queries,pq,exact?pq:g.work.primitive_queries);
    add_counter(out.work.held.candidates_examined,ce,exact?ce:g.work.candidates_examined);
    const auto ps=known(&held::Work::primitive_sqrt_refinements),es=known(&held::Work::enclosure_sqrt_refinements);
    need(add(ps,es)==sr,"Returned held sqrt known decomposition differs");
    add_counter(out.work.held.primitive_sqrt_refinements,ps,exact?ps:primitive_bound);
    add_counter(out.work.held.enclosure_sqrt_refinements,es,exact?es:enclosure_bound);
    add_counter(out.work.held.sqrt_refinements,sr,su);
    const auto lr=known(&held::Work::mesh_sqrt_limited_rows),ec=known(&held::Work::enclosure_sqrt_calls),el=known(&held::Work::enclosure_sqrt_limited_calls);
    add_counter(out.work.held.mesh_sqrt_limited_rows,lr,exact?lr:mul(e,n));
    add_counter(out.work.held.enclosure_sqrt_calls,ec,exact?ec:mul(e,2));
    add_counter(out.work.held.enclosure_sqrt_limited_calls,el,exact?el:mul(e,2));
    const std::size_t propagations=returned&&call.result->candidate_evaluated?1U:0U;
    accumulate(out.work.propagation_attempts,counter(propagations,returned?propagations:1,returned));out.work.bridge_calls_upper=add(out.work.bridge_calls_upper,1);
    WorkGrant actual=g.work;actual.mesh_queries=exact?mq:g.work.mesh_queries;actual.primitive_queries=exact?pq:g.work.primitive_queries;actual.candidates_examined=exact?ce:g.work.candidates_examined;actual.sqrt_refinements=su;actual.propagations=returned?propagations:1;
    settle(out,g,actual);sync(out);
}
void mark_call(GuardResult& out,PairRecord& p,std::optional<std::size_t>& ordinal) {
    ordinal=out.work.child_calls_attempted;if(!p.execution_ordinal) {p.execution_ordinal=ordinal;}++out.work.child_calls_attempted;
}
void run_mesh(GuardResult& out,std::size_t index) {
    auto& record=out.pairs[index];auto& call=std::get<MeshCall>(record.child);const auto& s=snapshot(out);const auto& pair=pair_source(out,index);
    call.grant=mesh_grant(s.meshes[pair.second.ordinal].triangles.size(),call.used_settings);charge(out,call.grant);call.granted=true;
    mark_call(out,record,call.attempt_ordinal);++out.work.mesh_calls_attempted;call.state=CallState::nonreturned;
    try {
        auto child=flight::query(s.bodies[pair.first.ordinal],s.gravity,s.meshes[pair.second.ordinal].triangles,s.horizon,call.used_settings);
        ++out.work.child_calls_returned;++out.work.mesh_calls_returned;call.state=CallState::returned;call.result.emplace(std::move(child));
    }catch(...) {mesh_work(out,call,false);out.work.exact=false;throw Stop{Status::not_certified,Reason::child_exception,"Mesh guard child did not return"};}
    mesh_work(out,call,true);strip(*call.result,call.messages);
    if(call.result->status==flight::Status::unsupported_environment) {throw Stop{Status::unsupported_environment,Reason::child_environment,"Mesh child environment rejected"};}
    validate_mesh_source(*call.result,s,pair,call.used_settings);
    if(!out.work.exact) {throw Stop{Status::not_certified,Reason::unknown_work,"Mesh child has unknown reserved work"};}
    if(call.result->status==flight::Status::numerical_failure) {throw Stop{Status::numerical_failure,Reason::mesh_not_separated,"Mesh child numerical failure"};}
    const bool safe=call.result->status==flight::Status::certified_separated;record.state=safe?PairState::certified:PairState::not_certified;record.reason=safe?Reason::none:Reason::mesh_not_separated;
}
const flight::Result& seed(const GuardResult& out,std::size_t body) {
    const auto index=out.bodies[body].seed_pair_ordinal;need(index&&out.bodies[body].state==SeedState::ready,"Missing ready seed dependency");
    const auto& call=std::get<MeshCall>(out.pairs[*index].child);need(call.result.has_value(),"Missing seed child result");return *call.result;
}
struct Motion {accelerated::Sphere sphere;double bound{};};
Motion motion(const GuardResult& out,std::size_t body,bool metric_radius=false) {
    const auto& original=snapshot(out).bodies[body];if(original.is_static) {return {{original.position,{},{},original.radius},0};}
    const auto& f=seed(out,body);return {{original.position,original.velocity,f.tube->nominal_acceleration,metric_radius?f.tube->guard_radius:original.radius},f.tube->position_error};
}
template<class R> void validate_coverage(const R& r,double horizon,bool certified) {
    need(r.snapshot&&bits(r.snapshot->horizon,horizon),"Coverage source horizon missing/changed");
    need(r.audits.size()==r.work.value_calls_attempted&&r.work.value_calls_returned<=r.work.value_calls_attempted,"Coverage exact wrapper counters differ");
    std::size_t returned=0;
    for(const auto& a:r.audits) {
        need(a.call_attempted,"Coverage audit missing actual attempt");bool has=false;
        if constexpr(requires {a.value;}) {has=a.value.has_value();if(has) {need(finite(*a.value),"Coverage returned nonfinite value");}}
        else {has=a.evaluation.has_value();if(has) {need(finite(a.evaluation->gap),"Coverage returned nonfinite gap");}}
        if(has) {++returned;}
    }
    need(returned==r.work.value_calls_returned,"Coverage returned payload count differs");
    if(certified) {
        need(r.snapshot_validated&&r.partition_complete&&!r.partition.empty()&&r.frontier.empty()&&!r.current&&returned==r.audits.size(),"Certified coverage incomplete");
        need(r.partition.front().cell.time_bounds[0]==0&&bits(r.partition.back().cell.time_bounds[1],horizon),"Coverage root endpoints differ");
        for(std::size_t i=0;i<r.partition.size();++i) {
            const auto& leaf=r.partition[i];need(static_cast<unsigned>(leaf.state)==1&&leaf.audit_index&&*leaf.audit_index<r.audits.size(),"Certified coverage has unknown leaf/link");
            const auto& a=r.audits[*leaf.audit_index];need(a.cell.time_bounds==leaf.cell.time_bounds&&a.cell.depth==leaf.cell.depth&&a.cell.parent_audit==leaf.cell.parent_audit,"Coverage leaf/audit link differs");
            need(leaf.cell.time_bounds[0]<leaf.cell.time_bounds[1]&&(i==0||r.partition[i-1].cell.time_bounds[1]==leaf.cell.time_bounds[0]),"Coverage closed partition has gap");
            if constexpr(requires {a.value;}) {need(a.value&&a.value->strictly_positive(),"Certified metric cell is not strict positive");}
            else {need(a.evaluation&&a.evaluation->gap.strictly_positive(),"Certified box cell is not strict positive");}
        }
    }
}
Reason empty_grant_reason(const GuardResult& out) noexcept {
    return out.reservation.retained.primitive_audits==out.original_settings->limits.primitive_audits?Reason::storage_budget:Reason::work_budget;
}
void run_metric(GuardResult& out,std::size_t index) {
    auto& pair=out.pairs[index];auto& call=std::get<PlaneCalls>(pair.child).metric;const auto& s=snapshot(out);const auto& key=pair_source(out,index);
    call.used_settings.max_evaluations=grant_e(out,call.requested_settings.max_evaluations,true);
    if(call.used_settings.max_evaluations==0) {throw Stop{Status::not_certified,empty_grant_reason(out),"No plane metric value grant remains"};}
    call.grant=coverage_grant<MetricTypes>(call.used_settings.max_evaluations,call.used_settings.max_leaves);call.grant.work.plane_metric_values=call.used_settings.max_evaluations;call.grant.work.plane_norm_loop_iterations_upper=mul(64,call.used_settings.max_evaluations);
    charge(out,call.grant);call.granted=true;
    const auto m=motion(out,key.first.ordinal,true);const auto& raw=s.planes[key.second.ordinal];const accelerated::StaticPlane p{raw.normal,raw.offset};
    mark_call(out,pair,call.attempt_ordinal);++out.work.plane_metric_calls_attempted;call.state=CallState::nonreturned;
    try {
        auto child=metric::sphere_plane(m.sphere,p,s.horizon,call.used_settings);++out.work.child_calls_returned;++out.work.plane_metric_calls_returned;call.state=CallState::returned;call.result.emplace(std::move(child));
    }catch(...) {
        accumulate(out.work.plane_metric_values,counter(0,call.grant.work.plane_metric_values,false));out.work.plane_norm_calls_upper=add(out.work.plane_norm_calls_upper,call.used_settings.max_evaluations);
        out.work.plane_norm_loop_iterations_upper=add(out.work.plane_norm_loop_iterations_upper,call.grant.work.plane_norm_loop_iterations_upper);out.work.exact=false;
        throw Stop{Status::not_certified,Reason::child_exception,"Plane metric child did not return"};
    }
    const auto& r=*call.result;WorkGrant actual=call.grant.work;actual.plane_metric_values=r.work.value_calls_attempted;settle(out,call.grant,actual);
    accumulate(out.work.plane_metric_values,counter(actual.plane_metric_values,actual.plane_metric_values,true));
    out.work.plane_norm_calls_upper=add(out.work.plane_norm_calls_upper,r.work.plane_norm_calls_upper);out.work.plane_norm_loop_iterations_upper=add(out.work.plane_norm_loop_iterations_upper,r.work.plane_norm_loop_iterations_upper);strip(call.result->message,call.messages);
    if(r.status==metric::Status::unsupported_environment) {throw Stop{Status::unsupported_environment,Reason::child_environment,"Plane metric environment rejected"};}
    need(r.snapshot&&same_coverage_settings(r.snapshot->settings,call.used_settings),"Plane metric profile changed");
    const auto* input=std::get_if<metric::SpherePlane>(&r.snapshot->input);need(input&&same(input->sphere,m.sphere)&&same(input->plane,p),"Plane metric original inputs differ");
    validate_coverage(r,s.horizon,r.status==metric::Status::certified);
    need(r.work.plane_norm_calls_upper==r.work.value_calls_attempted&&r.work.plane_norm_loop_iterations_upper==mul(64,r.work.value_calls_attempted),"Private norm upper units differ");
    if(r.work.value_calls_attempted!=r.work.value_calls_returned) {out.work.exact=false;throw Stop{Status::not_certified,Reason::child_exception,"Plane metric value did not return"};}
}
void run_plane_box(GuardResult& out,std::size_t index) {
    auto& pair=out.pairs[index];auto& call=std::get<PlaneCalls>(pair.child).box;const auto& s=snapshot(out);const auto& key=pair_source(out,index);
    call.used_settings.max_evaluations=grant_e(out,call.requested_settings.max_evaluations,false);
    if(call.used_settings.max_evaluations==0) {throw Stop{Status::not_certified,empty_grant_reason(out),"No plane box value grant remains"};}
    call.grant=coverage_grant<PlaneTypes>(call.used_settings.max_evaluations,call.used_settings.max_leaves);call.grant.work.box_values=call.used_settings.max_evaluations;charge(out,call.grant);call.granted=true;
    const auto m=motion(out,key.first.ordinal);const auto& p=s.planes[key.second.ordinal];const plane::Input input{m.sphere,{p.normal,p.offset},m.bound,out.original_settings->contact_margin};
    mark_call(out,pair,call.attempt_ordinal);++out.work.plane_box_calls_attempted;call.state=CallState::nonreturned;
    try {auto child=plane::query(input,s.horizon,call.used_settings);++out.work.child_calls_returned;++out.work.plane_box_calls_returned;call.state=CallState::returned;call.result.emplace(std::move(child));}
    catch(...) {accumulate(out.work.box_values,counter(0,call.grant.work.box_values,false));out.work.exact=false;throw Stop{Status::not_certified,Reason::child_exception,"Plane box child did not return"};}
    const auto& r=*call.result;WorkGrant actual=call.grant.work;actual.box_values=r.work.value_calls_attempted;settle(out,call.grant,actual);
    accumulate(out.work.box_values,counter(actual.box_values,actual.box_values,true));strip(call.result->message,call.messages);
    if(r.status==plane::Status::unsupported_environment) {throw Stop{Status::unsupported_environment,Reason::child_environment,"Plane box environment rejected"};}
    need(r.snapshot&&same_coverage_settings(r.snapshot->settings,call.used_settings),"Plane box profile changed");
    const auto& a=r.snapshot->input;need(same(a.sphere,input.sphere)&&same(a.plane,input.plane)&&bits(a.position_error,input.position_error)&&bits(a.contact_margin,input.contact_margin),"Plane box source/B/margin changed");
    validate_coverage(r,s.horizon,r.status==plane::Status::certified);
    if(r.work.value_calls_attempted!=r.work.value_calls_returned) {out.work.exact=false;throw Stop{Status::not_certified,Reason::child_exception,"Plane box value did not return"};}
}
void run_sphere(GuardResult& out,std::size_t index) {
    auto& pair=out.pairs[index];auto& call=std::get<SphereCall>(pair.child);const auto& s=snapshot(out);const auto& key=pair_source(out,index);
    call.used_settings.max_evaluations=grant_e(out,call.requested_settings.max_evaluations,false,call.used_settings.sqrt_refinements);
    if(call.used_settings.max_evaluations==0) {throw Stop{Status::not_certified,empty_grant_reason(out),"No sphere box root/value grant remains"};}
    call.grant=coverage_grant<SphereTypes>(call.used_settings.max_evaluations,call.used_settings.max_leaves);call.grant.work.box_values=call.used_settings.max_evaluations;call.grant.work.sqrt_refinements=mul(mul(2,call.used_settings.max_evaluations),call.used_settings.sqrt_refinements);
    charge(out,call.grant);call.granted=true;
    const auto a=motion(out,key.first.ordinal),b=motion(out,key.second.ordinal);const sphere::Input input{a.sphere,b.sphere,a.bound,b.bound,out.original_settings->contact_margin};
    mark_call(out,pair,call.attempt_ordinal);++out.work.sphere_box_calls_attempted;call.state=CallState::nonreturned;
    try {auto child=sphere::query(input,s.horizon,call.used_settings);++out.work.child_calls_returned;++out.work.sphere_box_calls_returned;call.state=CallState::returned;call.result.emplace(std::move(child));}
    catch(...) {
        accumulate(out.work.box_values,counter(0,call.grant.work.box_values,false));accumulate(out.work.sphere_sqrt_refinements,counter(0,call.grant.work.sqrt_refinements,false));out.work.exact=false;sync(out);
        throw Stop{Status::not_certified,Reason::child_exception,"Sphere box child did not return"};
    }
    const auto& r=*call.result;WorkGrant actual=call.grant.work;actual.box_values=r.work.value_calls_attempted;actual.sqrt_refinements=r.work.sqrt_refinements_upper;
    settle(out,call.grant,actual);accumulate(out.work.box_values,counter(actual.box_values,actual.box_values,true));accumulate(out.work.sphere_sqrt_refinements,counter(r.work.sqrt_refinements_returned,r.work.sqrt_refinements_upper,r.work.exact));
    out.work.sphere_root_results_returned=add(out.work.sphere_root_results_returned,r.work.sqrt_results_returned);out.work.sphere_root_limited_returns=add(out.work.sphere_root_limited_returns,r.work.sqrt_limited_returns);sync(out);strip(call.result->message,call.messages);
    if(r.status==sphere::Status::unsupported_environment) {throw Stop{Status::unsupported_environment,Reason::child_environment,"Sphere box environment rejected"};}
    need(r.snapshot&&same_coverage_settings(r.snapshot->settings,call.used_settings),"Sphere box profile changed");
    const auto& q=r.snapshot->input;need(same(q.first,input.first)&&same(q.second,input.second)&&bits(q.first_position_error,input.first_position_error)&&bits(q.second_position_error,input.second_position_error)&&bits(q.contact_margin,input.contact_margin),"Sphere box original radii/B/margin changed");
    validate_coverage(r,s.horizon,r.status==sphere::Status::certified);
    std::size_t roots=0,refinements=0,limited=0;
    for(const auto& audit:r.audits) {
        if(audit.evaluation) {const auto& e=*audit.evaluation;need(same(e.distance,e.root.value)&&e.root.refinements<=2*call.used_settings.sqrt_refinements,"Sphere root copy/count differs");++roots;refinements=add(refinements,e.root.refinements);limited+=e.root.refinement_limited?1U:0U;}
    }
    need(roots==r.work.sqrt_results_returned&&refinements==r.work.sqrt_refinements_returned&&limited==r.work.sqrt_limited_returns,"Sphere returned root work differs");
    if(!r.work.exact) {throw Stop{Status::not_certified,Reason::unknown_work,"Sphere box root block is unknown"};}
    if(r.work.value_calls_attempted!=r.work.value_calls_returned) {out.work.exact=false;throw Stop{Status::not_certified,Reason::child_exception,"Sphere box value did not return"};}
    const bool safe=r.status==sphere::Status::certified;pair.state=safe?PairState::certified:PairState::not_certified;pair.reason=safe?Reason::none:Reason::box_not_separated;
}
bool ready(const GuardResult& out,std::size_t i) noexcept {return out.bodies[i].state==SeedState::ready||out.bodies[i].state==SeedState::static_copy;}
void dependencies(GuardResult& out) noexcept {
    if(!out.preparation||!out.preparation->inventory||!out.preparation->snapshot) {return;}
    for(auto& row:out.pairs) {
        if(row.state!=PairState::unexamined) {continue;}
        const auto& p=out.preparation->inventory->pairs[row.pair_ordinal];if(p.kind==prep::PairKind::body_mesh) {continue;}
        const bool first_failed=out.bodies[p.first.ordinal].state==SeedState::failed;
        const bool second_failed=p.kind==prep::PairKind::body_body&&out.bodies[p.second.ordinal].state==SeedState::failed;
        if(first_failed||second_failed) {row.state=PairState::dependency_failed;row.reason=Reason::dependency_failed;}
    }
}
bool accounting(const GuardResult& out) noexcept {
    const auto& w=out.work;const auto& c=out.reservation.charged;
    return w.child_calls_attempted==w.mesh_calls_attempted+w.plane_metric_calls_attempted+w.plane_box_calls_attempted+w.sphere_box_calls_attempted&&
        w.child_calls_returned==w.mesh_calls_returned+w.plane_metric_calls_returned+w.plane_box_calls_returned+w.sphere_box_calls_returned&&w.child_calls_returned==w.child_calls_attempted&&
        c.mesh_queries==w.held.mesh_queries.upper&&c.primitive_queries==w.held.primitive_queries.upper&&c.candidates_examined==w.held.candidates_examined.upper&&
        c.sqrt_refinements==w.sqrt_refinements.upper&&c.propagations==w.propagation_attempts.upper&&c.plane_metric_values==w.plane_metric_values.upper&&c.box_values==w.box_values.upper&&
        c.bridge_calls_upper==w.bridge_calls_upper&&c.plane_norm_loop_iterations_upper>=w.plane_norm_loop_iterations_upper;
}
#undef RETAINED_FIELDS
#undef GRANT_FIELDS
}

BindingInfo current_binding() noexcept {
    BindingInfo out;out.checked=true;
    if(interval::environment_issue()) {out.state=BindingState::environment_unsupported;return out;}
#if defined(PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE) && PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE == 1
#if !defined(_M_ARM64EC) && !defined(__wasm__) && !defined(__clang__) && ((defined(_MSC_VER) && defined(_M_X64)) || (defined(__GNUC__) && defined(__x86_64__) && defined(__SSE2__)))
    constexpr char identity[]=PIKAPIKA_WORLD_FLIGHT_BUILD_ID;
    if(sizeof(identity)!=65) {out.state=BindingState::identity_mismatch;return out;}
    for(std::size_t i=0;i<64;++i) {
        const char c=identity[i];if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))) {out.state=BindingState::identity_mismatch;return out;}
        out.build_id[i]=c;
    }
    const char* actual=detail::world_predicate_binding_build_id();
    if(detail::world_predicate_binding_profile()!=1||actual==nullptr) {out.state=BindingState::identity_mismatch;return out;}
    for(std::size_t i=0;i<65;++i) {if(actual[i]!=identity[i]) {out.state=BindingState::identity_mismatch;return out;}}
    out.profile=1;out.state=BindingState::ready;
#else
    out.state=BindingState::unsupported_target;
#endif
#endif
    return out;
}

GuardResult query(const dynamics::World& world,std::span<const StaticMeshSource> sources,double horizon,const GuardSettings& settings) noexcept {
    GuardResult out;
    if(const char* issue=interval::environment_issue()) {fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
    out.binding=current_binding();
    if(out.binding.state!=BindingState::ready) {fail(out,Status::unsupported_environment,Reason::binding_unsupported,"World predicate artifact binding is unavailable");return out;}
    out.original_settings=settings;
    std::optional<std::size_t> active_pair;
    try {
        out.preparation=prep::prepare(world,sources,horizon,out.original_settings->preparation);strip(out.preparation->message,out.preparation_messages);
        if(out.preparation->status!=prep::Status::ready) {
            out.failure=Failure{out.preparation->failure,{},{}};
            const auto status=out.preparation->status==prep::Status::invalid_input?Status::invalid_input:
                out.preparation->status==prep::Status::unsupported_environment?Status::unsupported_environment:
                out.preparation->status==prep::Status::numerical_failure?Status::numerical_failure:Status::not_certified;
            fail(out,status,Reason::preparation_failed,"Owned World preparation failed");return out;
        }
        const auto& profile=*out.original_settings;
        if(!valid_mesh_profile(profile.mesh)||!valid_coverage(profile.plane_metric)||!valid_coverage(profile.plane_box)||!valid_coverage(profile.sphere_box)||!valid_limits(profile.limits)||
           !std::isfinite(profile.contact_margin)||profile.contact_margin<0||profile.contact_margin>.1) {throw Stop{Status::invalid_input,Reason::settings,"Invalid complete World guard profile/margin"};}
        const auto& s=snapshot(out);const auto& inv=*out.preparation->inventory;out.initial_request=initial_request(s,inv);charge(out,Grant{*out.initial_request,{}});
        out.bodies.reserve(s.bodies.size());out.pairs.reserve(inv.pairs.size());
        std::size_t min_mesh=0;
        for(std::size_t i=1;i<s.meshes.size();++i) {if(s.meshes[i].id<s.meshes[min_mesh].id) {min_mesh=i;}}
        for(std::size_t i=0;i<s.bodies.size();++i) {
            BodyRecord b{i,s.bodies[i].is_static,s.bodies[i].is_static?SeedState::static_copy:SeedState::unexamined,{}};
            if(!b.is_static) {
                for(std::size_t k=0;k<inv.pairs.size();++k) {const auto& p=inv.pairs[k];if(p.kind==prep::PairKind::body_mesh&&p.first.ordinal==i&&p.second.ordinal==min_mesh) {b.seed_pair_ordinal=k;break;}}
                need(b.seed_pair_ordinal.has_value(),"Dynamic body seed pair missing");
            }
            out.bodies.push_back(b);
        }
        for(std::size_t i=0;i<inv.pairs.size();++i) {
            PairRecord record;record.pair_ordinal=i;
            if(inv.pairs[i].kind==prep::PairKind::body_mesh) {auto& c=std::get<MeshCall>(record.child);c.requested_settings=profile.mesh;c.used_settings=profile.mesh;}
            else if(inv.pairs[i].kind==prep::PairKind::body_plane) {auto& p=record.child.emplace<PlaneCalls>();p.metric.requested_settings=profile.plane_metric;p.metric.used_settings=profile.plane_metric;p.box.requested_settings=profile.plane_box;p.box.used_settings=profile.plane_box;}
            else {auto& c=record.child.emplace<SphereCall>();c.requested_settings=profile.sphere_box;c.used_settings=profile.sphere_box;}
            out.pairs.push_back(std::move(record));
        }
        // Fixed small insertion order; no variable-end array std::sort warning.
        std::array<std::size_t,8> order{};std::size_t count=0;
        for(std::size_t i=0;i<s.bodies.size();++i) {
            if(s.bodies[i].is_static) {continue;}
            std::size_t at=count;while(at>0&&s.bodies[order[at-1]].id>s.bodies[i].id) {order[at]=order[at-1];--at;}
            order[at]=i;++count;
        }
        for(std::size_t n=0;n<count;++n) {
            const auto i=order[n];active_pair=out.bodies[i].seed_pair_ordinal;out.bodies[i].state=SeedState::pending;run_mesh(out,*active_pair);
            out.bodies[i].state=out.pairs[*active_pair].state==PairState::certified?SeedState::ready:SeedState::failed;
        }
        for(std::size_t i=0;i<out.pairs.size();++i) {
            if(inv.pairs[i].kind!=prep::PairKind::body_mesh||std::get<MeshCall>(out.pairs[i].child).state!=CallState::unexamined) {continue;}
            active_pair=i;run_mesh(out,i);const auto body=inv.pairs[i].first.ordinal;
            if(out.pairs[i].state==PairState::certified&&out.bodies[body].state==SeedState::ready) {need(same_flight(seed(out,body),*std::get<MeshCall>(out.pairs[i].child).result),"Independent mesh child changed common flight bits");}
        }
        for(std::size_t i=0;i<out.pairs.size();++i) {
            const auto& p=inv.pairs[i];if(p.kind==prep::PairKind::body_mesh) {continue;}active_pair=i;
            if(!ready(out,p.first.ordinal)||(p.kind==prep::PairKind::body_body&&!ready(out,p.second.ordinal))) {out.pairs[i].state=PairState::dependency_failed;out.pairs[i].reason=Reason::dependency_failed;continue;}
            if(p.kind==prep::PairKind::body_body) {run_sphere(out,i);}
            else {
                run_metric(out,i);run_plane_box(out,i);const auto& c=std::get<PlaneCalls>(out.pairs[i].child);
                const bool m=c.metric.result->status==metric::Status::certified,b=c.box.result->status==plane::Status::certified;
                out.pairs[i].state=m&&b?PairState::certified:PairState::not_certified;out.pairs[i].reason=!m?Reason::metric_not_separated:!b?Reason::box_not_separated:Reason::none;
            }
        }
        active_pair.reset();sync(out);need(accounting(out),"Final World guard work accounting differs");bool all=out.work.exact;
        for(const auto& p:out.pairs) {all=all&&p.state==PairState::certified;}
        for(const auto& b:out.bodies) {all=all&&(b.state==SeedState::ready||b.state==SeedState::static_copy);}
        if(!all) {
            Reason reason=Reason::seed_failed;for(const auto& p:out.pairs) {if(p.state!=PairState::certified) {reason=p.reason;break;}}
            fail(out,Status::not_certified,reason,"At least one required World pair is not certified");return out;
        }
        std::vector<dynamics::RigidBody> candidates;candidates.reserve(s.bodies.size());
        for(std::size_t i=0;i<s.bodies.size();++i) {candidates.push_back(s.bodies[i].is_static?s.bodies[i]:*seed(out,i).candidate);}
        out.candidate_bodies.emplace(std::move(candidates));out.status=Status::certified_separated;out.reason=Reason::none;out.failure.reset();
    }catch(const Stop& stop) {
        if(active_pair&&*active_pair<out.pairs.size()) {auto& p=out.pairs[*active_pair];p.reason=stop.reason;if(p.execution_ordinal) {p.state=PairState::not_certified;}out.failure=Failure{{},{},active_pair};}
        fail(out,stop.status,stop.reason,stop.text);
    }catch(const std::bad_alloc&) {fail(out,Status::numerical_failure,Reason::allocation_failure,"World guard storage allocation failed");}
    catch(...) {fail(out,Status::numerical_failure,Reason::metadata_inconsistent,"World guard processing failed");}
    for(auto& body:out.bodies) {
        if(body.state==SeedState::pending&&body.seed_pair_ordinal&&*body.seed_pair_ordinal<out.pairs.size()) {
            const auto& call=std::get<MeshCall>(out.pairs[*body.seed_pair_ordinal].child);
            body.state=call.state==CallState::unexamined?SeedState::unexamined:SeedState::failed;
        }
    }
    dependencies(out);return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
