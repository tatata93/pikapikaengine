#include "pikapika/sphere_triangle_mesh_free_flight_guard.hpp"
#include "dynamics_internal.hpp"
#include "free_flight_internal.hpp"
#include <algorithm>
#include <cmath>
#include <new>
#include <stdexcept>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Free-flight certification requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::sphere_triangle_mesh_free_flight_guard {
namespace {
using I=interval::Interval;
namespace held=sphere_triangle_mesh_held_load;
namespace tri=sphere_triangle;
struct Stop {Status status;Reason reason;const char* message;};
void need(bool condition,Status status,Reason reason,const char* message) {
    if(!condition) {throw Stop{status,reason,message};}
}
bool finite(I value) {return std::isfinite(value.lower())&&std::isfinite(value.upper());}
I checked(I value) {
    need(finite(value),Status::numerical_failure,Reason::nonfinite_intermediate,"Nonfinite free-flight interval");return value;
}
bool bounded(Vec3 value,double limit) {
    return std::isfinite(value.x)&&std::isfinite(value.y)&&std::isfinite(value.z)&&
        std::max({std::abs(value.x),std::abs(value.y),std::abs(value.z)})<=limit;
}
bool bounded(const Bounds3& value,double limit) {
    return std::all_of(value.begin(),value.end(),[limit](I x) {return finite(x)&&x.lower()>=-limit&&x.upper()<=limit;});
}
Bounds3 point(Vec3 value) {return {I::point(value.x),I::point(value.y),I::point(value.z)};}
Bounds3 exact_acceleration(const dynamics::RigidBody& body,Vec3 gravity) {
    const auto f=point(body.force),g=point(gravity);const auto mass=I::point(body.mass);
    return {checked(g[0]+f[0]/mass),checked(g[1]+f[1]/mass),checked(g[2]+f[2]/mass)};
}
Bounds3 endpoint_position(Vec3 position,Vec3 velocity,const Bounds3& acceleration,double horizon) {
    const auto p=point(position),v=point(velocity);const auto t=I::point(horizon),half=I::point(.5),t2=interval::square(t);
    // Same nominal endpoint expression used by W1's actual-candidate audit.
    return {checked(p[0]+v[0]*t+acceleration[0]*half*t2),
            checked(p[1]+v[1]*t+acceleration[1]*half*t2),
            checked(p[2]+v[2]*t+acceleration[2]*half*t2)};
}
Bounds3 expanded(const Bounds3& value,double radius) {
    const I error(-radius,radius);
    return {checked(value[0]+error),checked(value[1]+error),checked(value[2]+error)};
}
I absolute(I value) {
    if(value.lower()>=0) {return value;}
    if(value.upper()<=0) {return -value;}
    return I(0,std::max(-value.lower(),value.upper()));
}
bool contains(const Bounds3& bounds,Vec3 value) {
    return bounds[0].contains(value.x)&&bounds[1].contains(value.y)&&bounds[2].contains(value.z);
}
bool profile(const Settings& settings) {
    const auto& s=settings.held_load;const auto& p=s.mesh.primitive;
    return std::isfinite(settings.max_angular_increment)&&settings.max_angular_increment>0&&settings.max_angular_increment<=3.141592653589793&&
        s.mesh.max_surfaces>=1&&s.mesh.max_surfaces<=64&&p.max_candidates>=1&&p.max_candidates<=7&&p.sqrt_refinements>=1&&p.sqrt_refinements<=256&&
        p.max_total_sqrt_refinements>=1&&p.max_total_sqrt_refinements<=1024&&std::isfinite(p.maximum_local_width)&&p.maximum_local_width>0&&p.maximum_local_width<=1e6&&
        std::isfinite(p.maximum_normal_width)&&p.maximum_normal_width>0&&p.maximum_normal_width<=2&&std::isfinite(p.minimum_sine_squared)&&p.minimum_sine_squared>0&&p.minimum_sine_squared<=1&&
        std::isfinite(s.time_tolerance)&&s.time_tolerance>0&&s.time_tolerance<=.1&&s.max_evaluations>=1&&s.max_evaluations<=256&&s.max_leaves>=1&&s.max_leaves<=128&&
        s.max_depth<=32&&s.enclosure_sqrt_refinements>=1&&s.enclosure_sqrt_refinements<=256&&s.max_total_sqrt_refinements>=1&&s.max_total_sqrt_refinements<=16777216;
}
void fail(Result& out,Status status,Reason reason,const char* message) noexcept {
    out.status=status;out.reason=reason;out.candidate.reset();
    try {out.message=message;}catch(...) {out.message.clear();}
}
void validate_body(const dynamics::RigidBody& body) {
    try {body.validate();}
    catch(const std::bad_alloc&) {throw;}
    catch(const std::exception&) {throw Stop{Status::invalid_input,Reason::body_invalid,"Invalid free-flight body"};}
}
EndpointAudit audit_endpoint(const dynamics::RigidBody& original,const dynamics::RigidBody& candidate,const Tube& tube,double horizon) {
    auto nominal=endpoint_position(original.position,original.velocity,point(tube.nominal_acceleration),horizon);
    auto nominal_allowed=expanded(nominal,tube.roundoff);
    auto exact=endpoint_position(original.position,original.velocity,tube.exact_acceleration,horizon);
    auto exact_allowed=expanded(exact,tube.position_error);const auto actual=point(candidate.position);
    Bounds3 difference{checked(actual[0]-exact[0]),checked(actual[1]-exact[1]),checked(actual[2]-exact[2])};
    I l1=I::point(0);
    for(const auto& component:difference) {l1=checked(l1+absolute(component));}
    const bool nominal_contained=contains(nominal_allowed,candidate.position),exact_contained=contains(exact_allowed,candidate.position);
    const bool l1_within_tube=l1.upper()<=tube.position_error;
    return {std::move(nominal),std::move(nominal_allowed),std::move(exact),std::move(exact_allowed),std::move(difference),l1,
        nominal_contained,exact_contained,l1_within_tube};
}
}

Result query(const dynamics::RigidBody& input_body,Vec3 gravity,std::span<const tri::StaticTriangle> triangles,double horizon,const Settings& settings) {
    Result out;
    try {
        if(const char* issue=interval::environment_issue()) {fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        const held::WorldBodySnapshot captured{input_body,gravity};out.world_body=captured;const auto& body=captured.body;
        need(profile(settings),Status::invalid_input,Reason::settings,"Invalid free-flight guard settings");
        validate_body(body);
        need(std::isfinite(horizon)&&horizon>0&&horizon<=.1&&bounded(gravity,1e9),Status::invalid_input,Reason::input_domain,"Invalid free-flight horizon/gravity");
        need(!triangles.empty()&&triangles.size()<=64,Status::invalid_input,Reason::surface_count,"Free-flight guard requires 1..64 triangles");
        for(std::size_t i=0;i<triangles.size();++i) {
            out.failed_index=i;const auto& triangle=triangles[i];
            need(triangle.id>0&&triangle.id<=9007199254740991ULL,Status::invalid_input,Reason::surface_id,"Invalid free-flight source ID");
            for(std::size_t previous=0;previous<i;++previous) {
                need(triangles[previous].id!=triangle.id,Status::invalid_input,Reason::duplicate_id,"Duplicate free-flight source ID");
            }
            need(std::all_of(triangle.vertices.begin(),triangle.vertices.end(),[](Vec3 vertex) {return bounded(vertex,1e12);}),
                Status::invalid_input,Reason::input_domain,"Free-flight triangle outside finite domain");
        }
        out.failed_index.reset();out.snapshot=Snapshot{body,gravity,horizon,{triangles.begin(),triangles.end()},settings};
        need(!body.is_static,Status::not_certified,Reason::unsupported_body,"Free-flight guard supports dynamic sphere proxies only");
        need(triangles.size()<=settings.held_load.mesh.max_surfaces,Status::not_certified,Reason::surface_budget,"Free-flight source exceeds mesh budget");

        // The original W1 recurrence is called ONCE, through its same-TU bridge.
        auto flight=dynamics::detail::enclose_free_flight(body,gravity,horizon);
        if(!flight.tube) {
            out.flight_failure=flight.failure;
            need(flight.failure!=dynamics::CcdFailure::none,Status::numerical_failure,Reason::coverage_inconsistent,"Free-flight bridge failed without classification");
            fail(out,flight.failure==dynamics::CcdFailure::numerical_failure?Status::numerical_failure:Status::not_certified,
                Reason::flight_tube_failure,flight.message.c_str());return out;
        }
        need(flight.failure==dynamics::CcdFailure::none,Status::numerical_failure,Reason::coverage_inconsistent,"Free-flight bridge returned success and failure");
        const auto& f=*flight.tube;
        need(bounded(f.nominal_acceleration,1e12)&&std::isfinite(f.position_error)&&std::isfinite(f.roundoff)&&std::isfinite(f.guard_radius)&&
            f.position_error>=0&&f.roundoff>=0&&f.position_error>=f.roundoff&&f.guard_radius>0,
            Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid W1 free-flight tube values");
        auto exact=exact_acceleration(body,gravity);const auto nominal=point(f.nominal_acceleration);
        Bounds3 difference{checked(exact[0]-nominal[0]),checked(exact[1]-nominal[1]),checked(exact[2]-nominal[2])};
        out.tube=Tube{f.nominal_acceleration,std::move(exact),std::move(difference),f.position_error,f.roundoff,f.guard_radius};
        need(bounded(out.tube->exact_acceleration,1e12),Status::not_certified,Reason::derived_domain,"Exact free-flight acceleration enclosure exceeds domain");
        const auto radius_sum=checked(I::point(body.radius)+I::point(f.position_error));
        need(f.guard_radius==radius_sum.upper(),Status::numerical_failure,Reason::coverage_inconsistent,"W1 guard radius is not the original outward sum");
        need(f.guard_radius<=1e9,Status::not_certified,Reason::inflated_radius_domain,"Inflated free-flight radius exceeds held-load domain");

        auto candidate=body;out.candidate_evaluated=true;
        try {dynamics::detail::propagate_free(candidate,gravity,horizon,settings.max_angular_increment);}
        catch(const std::bad_alloc&) {throw;}
        catch(const std::exception&) {throw Stop{Status::not_certified,Reason::propagation_failure,"Full free-flight candidate propagation failed"};}
        try {candidate.validate();}
        catch(const std::bad_alloc&) {throw;}
        catch(const std::exception&) {throw Stop{Status::not_certified,Reason::candidate_invalid,"Full free-flight candidate left the body domain"};}
        out.endpoint=audit_endpoint(body,candidate,*out.tube,horizon);
        need(out.endpoint->nominal_contained&&out.endpoint->exact_contained&&out.endpoint->l1_within_tube,
            Status::not_certified,Reason::endpoint_tube_failure,"Actual free-flight endpoint failed the independent tube audit");

        const held::HeldSphere inflated{body.id,body.position,body.velocity,body.mass,body.force,gravity,f.guard_radius};
        out.inflated=held::query(inflated,out.snapshot->triangles,horizon,settings.held_load);
        if(out.inflated->status==held::Status::unsupported_environment) {
            fail(out,Status::unsupported_environment,Reason::environment,"Inflated held-load environment rejected");return out;
        }
        if(out.inflated->status==held::Status::numerical_failure) {
            fail(out,Status::numerical_failure,Reason::held_load_not_separated,"Inflated held-load numerical failure");return out;
        }
        need(out.inflated->status!=held::Status::invalid_input,Status::numerical_failure,Reason::coverage_inconsistent,"Prevalidated inflated query rejected structural input");
        need(out.inflated->status==held::Status::separated&&out.inflated->work.exact,
            Status::not_certified,Reason::held_load_not_separated,"Inflated held-load path is not certified separated");
        static_assert(std::is_nothrow_copy_assignable_v<dynamics::RigidBody>);
        out.candidate=candidate;out.status=Status::certified_separated;out.reason=Reason::none;
    }catch(const Stop& failure) {fail(out,failure.status,failure.reason,failure.message);}
    catch(const std::bad_alloc&) {fail(out,Status::numerical_failure,Reason::allocation_failure,"Free-flight guard diagnostic allocation failed");}
    catch(const std::exception& error) {fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,error.what());}
    catch(...) {fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Unknown free-flight guard failure");}
    return out;
}

Result query_body(const dynamics::World& world,std::uint64_t body_id,std::span<const tri::StaticTriangle> triangles,double horizon,const Settings& settings) {
    Result out;
    try {
        if(const char* issue=interval::environment_issue()) {fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        need(body_id>0&&body_id<=9007199254740991ULL,Status::invalid_input,Reason::body_invalid,"Invalid free-flight body lookup ID");
        const auto* body=world.find_body(body_id);
        need(body!=nullptr,Status::invalid_input,Reason::body_not_found,"Free-flight body lookup failed");
        return query(*body,world.gravity,triangles,horizon,settings);
    }catch(const Stop& failure) {fail(out,failure.status,failure.reason,failure.message);}
    catch(const std::bad_alloc&) {fail(out,Status::numerical_failure,Reason::allocation_failure,"Free-flight adapter allocation failed");}
    catch(const std::exception& error) {fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,error.what());}
    catch(...) {fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Unknown free-flight adapter failure");}
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
