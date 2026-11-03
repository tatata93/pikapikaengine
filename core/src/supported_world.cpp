#include "pikapika/supported_world.hpp"
#include "pikapika/interval.hpp"
#include "dynamics_internal.hpp"
#include "support_internal.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <numeric>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Supported World requires strict floating point.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::supported {
namespace {
using I=interval::Interval;
using Body=dynamics::RigidBody;
constexpr std::size_t absent=dynamics::detail::absent_body;
struct Stop {Failure failure;const char* message;};
void need(bool value,Failure failure,const char* message){if(!value)throw Stop{failure,message};}
I point(double x){return I::point(x);}
double component(Vec3 v,unsigned k){return k==0?v.x:k==1?v.y:v.z;}
double magnitude(I x){return std::max(std::abs(x.lower()),std::abs(x.upper()));}
bool finite(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);}
double energy(std::span<const Body> b,Vec3 g){double e=0;for(const auto& x:b)if(!x.is_static)e+=x.kinetic_energy()-x.mass*g.dot(x.position);return e;}
double kinetic(std::span<const Body> b){double e=0;for(const auto& x:b)if(!x.is_static)e+=x.kinetic_energy();return e;}
// sqrt/hypot only seed the search. Squared outward intervals CHECK endpoints.
I length(I sum,double estimate){
    need(std::isfinite(estimate)&&estimate>0,Failure::initial_geometry,"undefined contact normal");
    double lo=estimate,hi=estimate;
    for(unsigned k=0;k<256;++k){
        bool a=interval::square(point(lo)).upper()<=sum.lower(),b=interval::square(point(hi)).lower()>=sum.upper();
        if(a&&b)return I(lo,hi);
        if(!a)lo=std::nextafter(lo,0.0);if(!b)hi=std::nextafter(hi,std::numeric_limits<double>::infinity());
    }
    throw Stop{Failure::initial_geometry,"contact distance enclosure exhausted"};
}
struct Near {
    constrained::Pair pair;
    std::size_t a{absent},b{},plane{absent};
    Vec3 normal{};
    I gap{point(0)};
    double vn{};
};
Near at_state(Near c,std::span<const Body> b,std::span<const dynamics::Plane> planes){
    if(c.a==absent){const auto& p=planes[c.plane];I squared=point(0),offset=point(-p.offset);
        for(unsigned k=0;k<3;++k){squared=squared+interval::square(point(component(p.normal,k)));offset=offset+point(component(p.normal,k))*point(component(b[c.b].position,k));}
        double l=std::hypot(p.normal.x,p.normal.y,p.normal.z);auto bound=length(squared,l);c.normal=p.normal*(1/l);c.gap=offset/bound-point(b[c.b].radius);c.vn=c.normal.dot(b[c.b].velocity);
    }else{I squared=point(0);for(unsigned k=0;k<3;++k)squared=squared+interval::square(point(component(b[c.b].position,k))-point(component(b[c.a].position,k)));
        Vec3 d=b[c.b].position-b[c.a].position;double l=std::hypot(d.x,d.y,d.z);auto bound=length(squared,l);c.normal=d*(1/l);c.gap=bound-point(b[c.a].radius)-point(b[c.b].radius);c.vn=c.normal.dot(b[c.b].velocity-b[c.a].velocity);}
    return c;
}
std::vector<constrained::Pair> initial_set(std::span<const Body> b,std::span<const dynamics::Plane> planes,Vec3 gravity,const Settings& s,Report& report){
    need(report.pair_queries<s.max_pair_queries,Failure::pair_budget,"W2 support-selection pair budget exhausted");
    dynamics::World snapshot;snapshot.gravity=gravity;for(const auto& x:b)snapshot.add_body(x);for(const auto& p:planes)snapshot.add_plane(p);
    support::Settings settings;settings.gap_tolerance=s.spatial_tolerance;settings.max_contacts=s.constraint.max_contacts;
    settings.velocity_interval_tolerance=s.velocity_tolerance;settings.max_pair_queries=std::min<std::size_t>(1000000,s.max_pair_queries-report.pair_queries);
    auto solved=support::detail::solve_finite_velocity(snapshot,settings,s.velocity_tolerance,s.contact_band);report.pair_queries+=solved.pair_queries;
    report.first_id=solved.first_id;report.second_id=solved.second_id;
    need(solved.success,solved.failure==support::Failure::pair_budget?Failure::pair_budget:Failure::constraint_failure,"W2 instantaneous unilateral support selection failed");
    std::vector<constrained::Pair> active;
    for(const auto& row:solved.constraints)if(row.phase==support::Phase::resting&&row.lambda>0)active.push_back({row.first_id,row.second_id});
    return active;
}
std::vector<Near> collect(std::span<const Body> b,std::span<const dynamics::Plane> planes,
                          const Settings& s,Report& report){
    std::vector<Near> near;
    const auto append=[&](Near c){
        report.first_id=c.pair.first_id;report.second_id=c.pair.second_id;
        need(report.pair_queries<s.max_pair_queries,Failure::pair_budget,"W2 pair-query budget exhausted");++report.pair_queries;
        need(c.gap.lower()>=-s.spatial_tolerance,Failure::initial_geometry,"current geometry exceeds W2 tolerated penetration");
        if(c.gap.lower()>s.contact_band)return;
        // A LOWER bound within contact_band is eligible, including an
        // enclosure straddling that edge. Its WHOLE gap box must still fit
        // spatial_tolerance. No midpoint replaces the input geometry.
        need(c.gap.upper()<=s.spatial_tolerance,Failure::initial_geometry,"contact-band classification is uncertain");
        need(near.size()<s.impulse.max_contacts&&near.size()<s.constraint.max_contacts,Failure::contact_budget,"W2 near-contact budget exhausted");
        near.push_back(c);
    };
    for(std::size_t i=0;i<b.size();++i){
        if(!b[i].is_static)for(std::size_t p=0;p<planes.size();++p){
            const auto& plane=planes[p];I squared=point(0),offset=point(-plane.offset);
            for(unsigned k=0;k<3;++k){squared=squared+interval::square(point(component(plane.normal,k)));offset=offset+point(component(plane.normal,k))*point(component(b[i].position,k));}
            const double l=std::hypot(plane.normal.x,plane.normal.y,plane.normal.z);I bound=length(squared,l);
            Near c;c.b=i;c.plane=p;c.pair={plane.id,b[i].id};c.normal=plane.normal*(1/l);c.gap=offset/bound-point(b[i].radius);c.vn=c.normal.dot(b[i].velocity);append(c);
        }
        for(std::size_t j=i+1;j<b.size();++j)if(!b[i].is_static||!b[j].is_static){
            I squared=point(0);for(unsigned k=0;k<3;++k)squared=squared+interval::square(point(component(b[j].position,k))-point(component(b[i].position,k)));
            Vec3 d=b[j].position-b[i].position;double l=std::hypot(d.x,d.y,d.z);I bound=length(squared,l);
            Near c;c.a=i;c.b=j;c.pair={b[i].id,b[j].id};c.normal=d*(1/l);c.gap=bound-point(b[i].radius)-point(b[j].radius);c.vn=c.normal.dot(b[j].velocity-b[i].velocity);append(c);
        }
    }
    return near;
}
void valid(double dt,const dynamics::World& w,const Settings& s){
    const auto positive=[](double x,double max){return std::isfinite(x)&&x>0&&x<=max;};
    need(positive(dt,.1)&&dt>=2e-12&&finite(w.gravity)&&std::max({std::abs(w.gravity.x),std::abs(w.gravity.y),std::abs(w.gravity.z)})<=1e9,Failure::invalid_input,"invalid W2 time/gravity");
    need(positive(s.spatial_tolerance,1e-3)&&positive(s.contact_band,s.spatial_tolerance)&&positive(s.velocity_tolerance,1e-3)&&
         positive(s.maximum_substep,.1)&&s.maximum_substep>=2e-12&&positive(s.minimum_substep,s.maximum_substep)&&s.minimum_substep>=2e-12&&
         positive(s.position_error_tolerance,1)&&positive(s.velocity_error_tolerance,1)&&positive(s.orientation_error_tolerance,.1)&&
         std::isfinite(s.relative_impact_energy_tolerance)&&s.relative_impact_energy_tolerance>=0&&s.relative_impact_energy_tolerance<=1e-3,
         Failure::invalid_input,"invalid W2 error/substep contract");
    need(s.max_attempts>0&&s.max_attempts<=1000000&&s.max_segments>0&&s.max_segments<=100000&&s.max_events>0&&s.max_events<=16384&&
         s.max_pair_queries>0&&s.max_pair_queries<=16000000&&s.max_guard_evaluations>0&&s.max_guard_evaluations<=64000000,
         Failure::invalid_input,"invalid W2 bounded budgets");
    dynamics::detail::validate_solver_settings(s.impulse);
    need(s.impulse.position_correction==0&&s.impulse.restitution_velocity_threshold==0,Failure::invalid_input,"W2 impacts prohibit projection and a hidden restitution threshold");
    need(s.constraint.initial_gap_tolerance>=s.spatial_tolerance&&s.constraint.initial_velocity_tolerance>=s.velocity_tolerance&&
         s.constraint.position_tolerance<s.contact_band&&s.constraint.velocity_tolerance<=s.velocity_tolerance,
         Failure::invalid_input,"W2 driver and constraint tolerances must be explicitly compatible");
    std::uint64_t previous=0;
    for(const auto& b:w.bodies()){
        b.validate();need(b.id>previous,Failure::invalid_input,"W2 body IDs/order changed after insertion");previous=b.id;
        need(b.material.friction==0,Failure::invalid_input,"W2 normal-only profile requires explicit zero friction");
        need(s.spatial_tolerance<=b.radius*1e-3,Failure::invalid_input,"W2 spatial tolerance exceeds 0.001 radius");
        for(const auto& p:w.planes())need(p.id!=b.id,Failure::invalid_input,"W2 body ID duplicates a plane");
    }
    for(const auto& p:w.planes())need(p.material.friction==0,Failure::invalid_input,"W2 normal-only planes require explicit zero friction");
}
void add_event(Report& r,Event e,const Settings& s){need(r.events.size()<s.max_events,Failure::event_budget,"W2 event budget exhausted");r.events.push_back(e);}
bool resolve_impacts(std::vector<Body>& current,std::span<const dynamics::Plane> planes,std::span<const Near> near,double elapsed,const Settings& settings,Report& report){
    bool closing=false,strong=false;
    for(const auto& c:near){closing=closing||c.vn<0;strong=strong||c.vn<-settings.velocity_tolerance;report.maximum_near_contact_gap=std::max(report.maximum_near_contact_gap,magnitude(c.gap));}
    if(closing){
        std::vector<dynamics::detail::ImpactContact> contacts;contacts.reserve(near.size());
        for(const auto& c:near){
            dynamics::detail::ImpactContact row;row.a=c.a;row.b=c.b;row.normal=c.normal;row.material_b=current[c.b].material;
            row.material_a=c.a==absent?planes[c.plane].material:current[c.a].material;
            row.point=c.a==absent?current[c.b].position-c.normal*current[c.b].radius:
                (current[c.a].position+c.normal*current[c.a].radius+current[c.b].position-c.normal*current[c.b].radius)*.5;
            // Existing resting rows must participate in the same island
            // solve, with zero bounce. Only incoming rows carry Newton e.
            if(c.vn>=0||(elapsed>0&&c.vn>=-settings.velocity_tolerance)){row.material_a.restitution=0;row.material_b.restitution=0;}
            contacts.push_back(row);
        }
        const double before=kinetic(current);auto impact=settings.impulse;
        const auto stats=dynamics::detail::solve_selected_impacts(current,contacts,impact);
        const double after=kinetic(current);
        need(std::isfinite(before)&&std::isfinite(after)&&after<=before+settings.relative_impact_energy_tolerance*std::max(1.0,before),Failure::energy_failure,"W2 simultaneous Newton impulse increased kinetic energy beyond tolerance");
        need(stats.max_closing_residual<=settings.velocity_tolerance,Failure::impulse_failure,"W2 coupled impulse closing residual exceeds tolerance");
        Event e;e.kind=strong?EventKind::impact:EventKind::velocity_repair;e.at=elapsed;
        e.contacts=near.size();e.impulse_sum=stats.normal_impulse_sum;e.kinetic_before=before;e.kinetic_after=after;e.maximum_gap=report.maximum_near_contact_gap;
        for(const auto& c:near)if(c.vn<0){e.first_id=c.pair.first_id;e.second_id=c.pair.second_id;e.normal=c.normal;break;}
        add_event(report,e,settings);report.impact_impulse_sum+=stats.normal_impulse_sum;
    }
    return closing;
}
}

Report step(dynamics::World& world,double dt,const Settings& settings){
    Report report;
    try{
        interval::require_environment();
        try{valid(dt,world,settings);}catch(const Stop&){throw;}catch(const std::exception&){throw Stop{Failure::invalid_input,"invalid W2 body or impulse settings"};}
        auto current=world.bodies();const auto& planes=world.planes();
        report.initial_mechanical_energy=energy(current,world.gravity);
        double elapsed=0;I integrated=point(0);std::vector<constrained::Pair> previous_active;
        while(elapsed<dt){
            report.candidate_time=elapsed;
            auto near=collect(current,planes,settings,report);
            if(resolve_impacts(current,planes,near,elapsed,settings,report))near=collect(current,planes,settings,report);
            const auto initial_active=initial_set(current,planes,world.gravity,settings,report);
            const double remaining=dt-elapsed;
            double h=remaining/std::ceil(remaining/settings.maximum_substep);
            bool accepted=false;
            while(!accepted){
                need(report.attempts<settings.max_attempts,Failure::attempt_budget,"W2 retry budget exhausted");++report.attempts;
                need(h>=std::min(settings.minimum_substep,remaining)&&h>=2e-12&&elapsed+h>elapsed,Failure::minimum_step,"W2 minimum resolvable substep reached");
                auto active=initial_active;std::vector<constrained::Pair> released;
                for(const auto& pair:previous_active)if(std::find(active.begin(),active.end(),pair)==active.end())released.push_back(pair);
                constrained::Result candidate;bool retry=false;
                for(std::size_t restart=0;;++restart){
                    if(restart>=4*(near.size()+1)){retry=true;break;}
                    ++report.constraint_solves;candidate=constrained::advance(current,planes,world.gravity,h,active,settings.constraint);
                    report.last_constraint_failure=candidate.failure;
                    if(candidate.success){
                        bool added=false;
                        try{for(const auto& row:near)if(std::abs(row.vn)<=settings.velocity_tolerance&&std::find(active.begin(),active.end(),row.pair)==active.end()){
                            const auto end=at_state(row,candidate.candidate_bodies,planes);
                            if(end.gap.lower()<-settings.constraint.position_tolerance||(end.gap.upper()<=settings.contact_band&&end.vn<-settings.velocity_tolerance)){
                                active.push_back(row.pair);released.erase(std::remove(released.begin(),released.end(),row.pair),released.end());added=true;break;}
                        }}catch(const Stop&){retry=true;break;}
                        if(added)continue;
                        break;
                    }
                    need(candidate.failure!=constrained::Failure::invalid_input,Failure::constraint_failure,"invalid W2 constraint settings/input");
                    if(candidate.failure!=constrained::Failure::release_required){retry=true;break;}
                    need(!candidate.release_pairs.empty(),Failure::constraint_failure,"W2 release report lacked a pair");
                    // Removing all negative bilateral rows is NOT a unilateral
                    // active-set solve: a row can become compressive after a
                    // different row is released. Pivot one most-negative stage
                    // coefficient, restart from the original snapshot, and
                    // re-add any inactive endpoint constraint that is violated.
                    const constrained::Constraint* remove=nullptr;double least=0;
                    for(const auto& c:candidate.constraints){double x=std::min(c.impulse_position,c.impulse_velocity);
                        if(x<least&&std::find(active.begin(),active.end(),c.pair)!=active.end()){least=x;remove=&c;}}
                    need(remove!=nullptr,Failure::constraint_failure,"W2 negative multiplier had no active row");
                    active.erase(std::find(active.begin(),active.end(),remove->pair));released.push_back(remove->pair);
                }
                if(!retry){
                    // Step doubling compares the same active-set numerical
                    // formula. It is a convergence diagnostic, not a proof of
                    // the continuous flow or the time of an active-set switch.
                    ++report.constraint_solves;auto half=constrained::advance(current,planes,world.gravity,h*.5,active,settings.constraint);
                    if(half.success){++report.constraint_solves;auto fine=constrained::advance(half.candidate_bodies,planes,world.gravity,h*.5,active,settings.constraint);
                        if(fine.success){
                            double ep=0,ev=0,eq=0;
                            for(std::size_t i=0;i<current.size();++i){const auto& a=candidate.candidate_bodies[i];const auto& b=fine.candidate_bodies[i];
                                ep=std::max(ep,(a.position-b.position).length());ev=std::max(ev,(a.velocity-b.velocity).length());
                                const double dx=a.orientation.x-b.orientation.x,dy=a.orientation.y-b.orientation.y,dz=a.orientation.z-b.orientation.z,dw=a.orientation.w-b.orientation.w;
                                const double px=a.orientation.x+b.orientation.x,py=a.orientation.y+b.orientation.y,pz=a.orientation.z+b.orientation.z,pw=a.orientation.w+b.orientation.w;
                                eq=std::max(eq,std::sqrt(std::min(dx*dx+dy*dy+dz*dz+dw*dw,px*px+py*py+pz*pz+pw*pw)));}
                            retry=!std::isfinite(ep)||!std::isfinite(ev)||!std::isfinite(eq)||ep>settings.position_error_tolerance||ev>settings.velocity_error_tolerance||eq>settings.orientation_error_tolerance;
                            if(!retry){report.maximum_position_error_estimate=std::max(report.maximum_position_error_estimate,ep);report.maximum_velocity_error_estimate=std::max(report.maximum_velocity_error_estimate,ev);report.maximum_orientation_error_estimate=std::max(report.maximum_orientation_error_estimate,eq);}
                        }else retry=true;
                    }else retry=true;
                }
                trajectory_guard::Result audit;
                if(!retry){
                    auto guard=settings.guard;guard.spatial_tolerance=settings.spatial_tolerance;guard.include_static_pairs=false;
                    need(report.pair_queries<settings.max_pair_queries,Failure::pair_budget,"W2 total sweep pair budget exhausted");
                    need(report.guard_evaluations<settings.max_guard_evaluations,Failure::guard_budget,"W2 total sweep evaluation budget exhausted");
                    guard.max_pair_queries=std::min(guard.max_pair_queries,settings.max_pair_queries-report.pair_queries);
                    guard.max_evaluations=std::min(guard.max_evaluations,settings.max_guard_evaluations-report.guard_evaluations);
                    audit=trajectory_guard::audit(current,candidate.candidate_bodies,planes,h,guard);
                    report.pair_queries+=audit.pair_queries;report.guard_evaluations+=audit.evaluations;report.certified_intervals+=audit.certified_intervals;report.last_guard_failure=audit.failure;
                    need(audit.failure!=trajectory_guard::Failure::invalid_input,Failure::trajectory_failure,"invalid W2 trajectory guard settings/input");
                    if(!audit.success){report.first_id=audit.first_id;report.second_id=audit.second_id;retry=true;}
                }
                if(retry){++report.rejected_attempts;h*=.5;continue;}
                need(report.accepted_segments<settings.max_segments,Failure::segment_budget,"W2 accepted-segment budget exhausted");
                for(const auto& pair:released){Event e;e.kind=EventKind::release;e.at=elapsed;e.first_id=pair.first_id;e.second_id=pair.second_id;
                    for(const auto& c:near)if(c.pair==pair){e.normal=c.normal;break;}add_event(report,e,settings);}
                report.maximum_gap_residual=std::max(report.maximum_gap_residual,candidate.residuals.final_gap);
                report.maximum_velocity_residual=std::max(report.maximum_velocity_residual,candidate.residuals.final_normal_velocity);
                for(const auto& c:candidate.constraints)report.support_impulse_sum+=c.impulse_position+c.impulse_velocity;
                for(std::size_t i=0;i<current.size();++i)if(!current[i].is_static)report.held_force_work+=current[i].force.dot(candidate.candidate_bodies[i].position-current[i].position);
                current=std::move(candidate.candidate_bodies);integrated=integrated+point(h);++report.accepted_segments;
                previous_active=std::move(active);
                report.minimum_accepted_substep=report.accepted_segments==1?h:std::min(report.minimum_accepted_substep,h);
                elapsed=h==remaining?dt:elapsed+h;accepted=true;
            }
        }
        // Right-continuous tick-end state: close a terminal near-impact now,
        // rather than publishing incoming velocity until the next caller tick.
        report.candidate_time=dt;const auto terminal=collect(current,planes,settings,report);
        resolve_impacts(current,planes,terminal,dt,settings,report);
        report.time_roundoff=magnitude(integrated-point(dt));
        need(report.time_roundoff<=1e-12,Failure::numerical_failure,"W2 represented segment clock exceeds time tolerance");
        report.final_mechanical_energy=energy(current,world.gravity);report.mechanical_energy_change=report.final_mechanical_energy-report.initial_mechanical_energy;
        need(std::isfinite(report.final_mechanical_energy)&&std::isfinite(report.held_force_work),Failure::numerical_failure,"nonfinite W2 work/energy diagnostics");
        // All checks precede a no-allocation commit to preserve body addresses.
        for(auto& b:current){b.force={};b.torque={};b.validate();}
        for(const auto& b:current)*world.find_body(b.id)=b;
        report.success=true;report.failure=Failure::none;report.advanced_dt=dt;report.candidate_time=dt;report.first_id=0;report.second_id=0;
    }catch(const Stop& e){report.failure=e.failure;report.message=e.message;}
    catch(const std::exception& e){report.failure=Failure::numerical_failure;report.message=e.what();}
    return report;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
