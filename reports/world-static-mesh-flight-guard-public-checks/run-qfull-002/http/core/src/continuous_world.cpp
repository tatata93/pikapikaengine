#include "pikapika/dynamics.hpp"
#include "pikapika/accelerated.hpp"
#include "dynamics_internal.hpp"
#include "free_flight_internal.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace pikapika::dynamics {
namespace {
using I=interval::Interval;
constexpr double infinity=std::numeric_limits<double>::infinity();
struct Stop { CcdFailure failure;const char* message; };
void need(bool value,CcdFailure failure,const char* message) {if(!value)throw Stop{failure,message};}
I point(double x) {return I::point(x);}
double magnitude(I x) {return std::max(std::abs(x.lower()),std::abs(x.upper()));}
double component(Vec3 v,unsigned i) {return i==0?v.x:i==1?v.y:v.z;}
bool bounded(Vec3 v,double bound) {return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&
    std::abs(v.x)<=bound&&std::abs(v.y)<=bound&&std::abs(v.z)<=bound;}
double upper_sum(double a,double b) {return (point(a)+point(b)).upper();}

// A library hypot estimate is NOT trusted as a proof. The endpoint squares must
// enclose the interval sum of squares. Failure to certify in 128 neighbours fails
// the tick; it does not silently substitute an approximate normal/distance.
I length_bound(Vec3 v) {
    const I squared=interval::square(point(v.x))+interval::square(point(v.y))+interval::square(point(v.z));
    if(squared.upper()==0)return point(0);
    double low=std::hypot(v.x,v.y,v.z),high=low;
    need(std::isfinite(low)&&low>0,CcdFailure::numerical_failure,"uncertifiable vector length");
    for(unsigned n=0;n<128;++n) {
        const bool lo=interval::square(point(low)).upper()<=squared.lower();
        const bool hi=interval::square(point(high)).lower()>=squared.upper();
        if(lo&&hi)return I(low,high);
        if(!lo)low=std::nextafter(low,0.0);
        if(!hi)high=std::nextafter(high,infinity);
    }
    throw Stop{CcdFailure::numerical_failure,"vector norm proof exhausted"};
}
Vec3 unit(Vec3 v) {
    const auto norm=length_bound(v);need(norm.lower()>0,CcdFailure::numerical_failure,"undefined impact normal");
    const double n=std::hypot(v.x,v.y,v.z);return {v.x/n,v.y/n,v.z/n};
}
// At most one adjacent representable spacing bounds each rounded primitive with
// result magnitude <= bound (including gradual underflow). Choosing the ULP at
// the upper magnitude is conservative at binade boundaries as well.
double ulp_bound(double bound) {
    need(std::isfinite(bound)&&bound>=0,CcdFailure::geometric_guard,"nonfinite propagation error bound");
    const double next=std::nextafter(bound,infinity);
    need(std::isfinite(next),CcdFailure::geometric_guard,"propagation error overflow");
    return (point(next)-point(bound)).upper();
}
struct Flight {
    accelerated::Sphere shape;
    double error{},roundoff{},guard_radius{};
};
Flight flight(const RigidBody& b,Vec3 gravity,double h) {
    Flight f;f.shape={b.position,b.velocity,{},b.radius};
    f.guard_radius=b.radius;
    if(b.is_static)return f;
    const auto acceleration=gravity+b.force*b.inverse_mass();f.shape.acceleration=acceleration;
    need(bounded(acceleration,1e12),CcdFailure::propagation_failure,"W1 acceleration component exceeds 1e12 m/s^2");
    const I time(0,h),half=point(0.5),hh=point(h),hh2=interval::square(hh);
    I total_error=point(0),total_roundoff=point(0);
    for(unsigned k=0;k<3;++k) {
        const double p=component(b.position,k),v=component(b.velocity,k),a=component(acceleration,k);
        const I exact_a=point(component(gravity,k))+point(component(b.force,k))/point(b.mass);
        const I position=point(p)+point(v)*time+exact_a*half*interval::square(time);
        const I velocity=point(v)+exact_a*time;
        need(magnitude(position)<=1e12&&magnitude(velocity)<=1e9,CcdFailure::propagation_failure,
            "continuous free trajectory leaves rigid-body numerical domain");
        // Error recurrence for the established propagator's EXACT operation
        // graph: q=fl(.5*t), s=fl(q*t), u=fl(a*s), z=fl(v*t),
        // x=fl(p+z), p'=fl(x+u). Each local RN error is bounded by one ULP
        // at a proved magnitude bound. Outward interval sums propagate errors,
        // including subnormal intermediates, without a relative-error shortcut.
        const auto rounding=[](I bound) {return point(ulp_bound(bound.upper()));};
        const I aa=point(std::abs(a)),vv=point(std::abs(v)),pp=point(std::abs(p));
        const I q=half*hh,s=half*hh2;
        const I eq=rounding(q);
        const I es=eq*hh+rounding((q+eq)*hh);
        const I eu=aa*es+rounding(aa*(s+es));
        const I ez=rounding(vv*hh);
        const I ex=ez+rounding(pp+vv*hh+ez);
        const I roundoff=ex+eu+rounding(pp+vv*hh+aa*s+ex+eu);
        const I acceleration_error=point(magnitude(exact_a-point(a)))*half*hh2;
        total_error=total_error+roundoff+acceleration_error;
        total_roundoff=total_roundoff+roundoff;
    }
    // L1 bounds Euclidean position error. No rounded square root is needed.
    f.error=total_error.upper();f.roundoff=total_roundoff.upper();
    f.guard_radius=(point(b.radius)+point(f.error)).upper();
    return f;
}
struct Query {
    std::size_t a{detail::absent_body},b{},plane{detail::absent_body};
    accelerated::Result result;
    double error{};
    double time_tolerance{};
};
I held_position(const RigidBody& body,const Flight& f,Vec3 gravity,unsigned k,double t) {
    if(body.is_static)return point(component(f.shape.center,k));
    const I a=point(component(gravity,k))+point(component(body.force,k))/point(body.mass);
    return point(component(f.shape.center,k))+point(component(f.shape.velocity,k))*point(t)+
        a*point(0.5)*interval::square(point(t));
}
// Confirm a negative witness using exact REAL F/m+g, rather than treating the
// rounded acceleration from the TOI search as physically exact. Near tangencies
// or tiny coefficient uncertainty can legitimately fail this extra certificate.
I held_witness(const Query& q,const std::vector<RigidBody>& bodies,const std::vector<Flight>& flights,
    const std::vector<Plane>& planes,Vec3 gravity,double t) {
    if(q.a==detail::absent_body) {
        const auto& p=planes[q.plane];I value=point(-p.offset);
        for(unsigned k=0;k<3;++k)value=value+point(component(p.normal,k))*held_position(bodies[q.b],flights[q.b],gravity,k,t);
        return value-point(bodies[q.b].radius)*length_bound(p.normal);
    }
    I square_sum=point(0);
    for(unsigned k=0;k<3;++k) {
        const auto acceleration=[&](std::size_t i) {return bodies[i].is_static?point(0):
            point(component(gravity,k))+point(component(bodies[i].force,k))/point(bodies[i].mass);};
        // Subtract exact INPUT coordinates first: separately enclosing both
        // absolute trajectories would lose common world translation needlessly.
        const I p=point(component(flights[q.b].shape.center,k))-point(component(flights[q.a].shape.center,k));
        const I v=point(component(flights[q.b].shape.velocity,k))-point(component(flights[q.a].shape.velocity,k));
        const I a=acceleration(q.b)-acceleration(q.a);
        const I d=p+v*point(t)+a*point(.5)*interval::square(point(t));
        square_sum=square_sum+interval::square(d);
    }
    return square_sum-interval::square(point(bodies[q.a].radius)+point(bodies[q.b].radius));
}
void identify(CcdReport& r,const Query& q,const std::vector<RigidBody>& bodies,const std::vector<Plane>& planes) {
    r.first_id=q.a==detail::absent_body?planes[q.plane].id:bodies[q.a].id;r.second_id=bodies[q.b].id;
}
double gap_upper(const Query& q,const std::vector<RigidBody>& b,const std::vector<Plane>& planes) {
    if(q.a==detail::absent_body) {
        const auto& p=planes[q.plane];const auto& body=b[q.b];
        const I norm=length_bound(p.normal);
        const I distance=point(p.normal.x)*point(body.position.x)+point(p.normal.y)*point(body.position.y)+
            point(p.normal.z)*point(body.position.z)-point(p.offset);
        const I gap=distance/norm-point(body.radius);
        need(gap.lower()>0,CcdFailure::geometric_guard,"rounded impact state is not provably separated from plane");
        return gap.upper();
    }
    const Vec3 delta=b[q.b].position-b[q.a].position;
    // Subtraction above is rounded; enclose its error from the exact centres.
    I square_sum=point(0);
    for(unsigned k=0;k<3;++k) {
        const I d=point(component(b[q.b].position,k))-point(component(b[q.a].position,k));
        square_sum=square_sum+interval::square(d);
    }
    const I n=length_bound(delta);
    const I radii=point(b[q.a].radius)+point(b[q.b].radius);
    // A norm error bound from |D^2-N^2|/(D+N), with certified positive denominator.
    need(n.lower()>0,CcdFailure::geometric_guard,"coincident impact centres");
    const double err=(point(magnitude(square_sum-interval::square(n)))/point(n.lower())).upper();
    const I gap=n+I(-err,err)-radii;
    need(gap.lower()>0,CcdFailure::geometric_guard,"rounded impact spheres are not provably separated");
    return gap.upper();
}
detail::ImpactContact contact(const Query& q,const std::vector<RigidBody>& b,const std::vector<Plane>& planes) {
    detail::ImpactContact c;c.a=q.a;c.b=q.b;c.material_b=b[q.b].material;
    if(q.a==detail::absent_body) {
        const auto& plane=planes[q.plane];c.normal=unit(plane.normal);c.material_a=plane.material;
        c.point=b[q.b].position-c.normal*b[q.b].radius;
    } else {
        c.normal=unit(b[q.b].position-b[q.a].position);c.material_a=b[q.a].material;
        c.point=(b[q.a].position+c.normal*b[q.a].radius+b[q.b].position-c.normal*b[q.b].radius)*0.5;
    }
    return c;
}
double normal_speed(const detail::ImpactContact& c,const std::vector<RigidBody>& b) {
    const auto point_velocity=[&](std::size_t i) {return i==detail::absent_body?Vec3{}:
        b[i].velocity+b[i].angular_velocity().cross(c.point-b[i].position);};
    return (point_velocity(c.b)-point_velocity(c.a)).dot(c.normal);
}
double kinetic_energy(const std::vector<RigidBody>& b) {
    double e=0;for(const auto& body:b)e+=body.kinetic_energy();return e;
}
void settings_valid(double dt,Vec3 gravity,const CcdSettings& s) {
    need(std::isfinite(dt)&&dt>0&&dt<=0.1&&bounded(gravity,1e9),CcdFailure::invalid_input,"invalid W1 timestep or gravity");
    try {detail::validate_solver_settings(s.solver);}
    catch(const std::exception&) {throw Stop{CcdFailure::invalid_input,"invalid W1 impulse-solver settings"};}
    need(s.solver.position_correction==0,CcdFailure::invalid_input,"W1 prohibits position projection");
    need(std::isfinite(s.time_tolerance)&&s.time_tolerance>=1e-12&&s.time_tolerance<=1e-3&&
        std::isfinite(s.spatial_tolerance)&&s.spatial_tolerance>=1e-12&&s.spatial_tolerance<=1e-2&&
        std::isfinite(s.minimum_impact_speed)&&s.minimum_impact_speed>0&&s.minimum_impact_speed<=1&&
        std::isfinite(s.closing_residual_tolerance)&&s.closing_residual_tolerance>=0&&s.closing_residual_tolerance<=1&&
        std::isfinite(s.relative_energy_tolerance)&&s.relative_energy_tolerance>=0&&s.relative_energy_tolerance<=1e-3,
        CcdFailure::invalid_input,"invalid W1 tolerances");
    need(s.max_event_batches>0&&s.max_event_batches<=1024&&s.max_free_segments>0&&s.max_free_segments<=2049&&
        s.max_pair_queries>0&&s.max_pair_queries<=1000000&&s.max_root_evaluations>0&&s.max_root_evaluations<=16000000&&
        s.query_evaluations>0&&s.query_evaluations<=1000000&&s.query_frontier>0&&s.query_frontier<=65536&&s.query_depth<=128,
        CcdFailure::invalid_input,"invalid W1 bounded budgets");
}
}

CcdReport World::step_continuous(double dt,const CcdSettings& settings) {
    CcdReport report;
    try {
        interval::require_environment();settings_valid(dt,gravity,settings);
        auto candidates=bodies_;
        std::uint64_t previous_id=0;
        for(const auto& body:candidates) {
            try {body.validate();}catch(const std::exception&) {throw Stop{CcdFailure::invalid_input,"invalid W1 input body"};}
            need(body.id>previous_id,CcdFailure::invalid_input,"W1 body stable IDs were changed or duplicated after insertion");
            for(const auto& plane:planes_)need(body.id!=plane.id,CcdFailure::invalid_input,"W1 body ID duplicates a plane ID");
            previous_id=body.id;
            need(settings.spatial_tolerance<=body.radius*1e-3,CcdFailure::invalid_input,
                "W1 spatial tolerance must not exceed 0.001 of any sphere radius");
        }
        double elapsed=0;I integrated_time=point(0);
        const auto advance=[&](double duration,const std::vector<Flight>& flights) {
            if(duration==0)return;
            need(report.free_segments<settings.max_free_segments,CcdFailure::segment_budget,"W1 free-segment budget exhausted");
            double largest_roundoff=0;
            for(std::size_t i=0;i<candidates.size();++i) {
                try {
                    detail::propagate_free(candidates[i],gravity,duration,settings.solver.max_angular_increment);
                    candidates[i].validate();
                } catch(const std::exception&) {throw Stop{CcdFailure::propagation_failure,"free propagation/rotation left the supported numerical domain"};}
                if(!candidates[i].is_static)for(unsigned k=0;k<3;++k) {
                    const auto& source=flights[i].shape;
                    const I endpoint=point(component(source.center,k))+point(component(source.velocity,k))*point(duration)+
                        point(component(source.acceleration,k))*point(0.5)*interval::square(point(duration));
                    const I allowed=endpoint+I(-flights[i].roundoff,flights[i].roundoff);
                    need(allowed.contains(component(candidates[i].position,k)),CcdFailure::geometric_guard,
                        "compiled free propagation violates its position operation-graph enclosure");
                }
                largest_roundoff=std::max(largest_roundoff,flights[i].roundoff);
            }
            report.accumulated_position_roundoff=upper_sum(report.accumulated_position_roundoff,largest_roundoff);
            need(report.accumulated_position_roundoff<=settings.spatial_tolerance/16,CcdFailure::geometric_guard,
                "accumulated propagation roundoff exceeds W1 guard budget");
            integrated_time=integrated_time+point(duration);++report.free_segments;
        };
        while(elapsed<dt) {
            report.candidate_time=elapsed;
            const double remaining=dt-elapsed;
            std::vector<Flight> flights;flights.reserve(candidates.size());
            for(const auto& body:candidates) {
                flights.push_back(flight(body,gravity,remaining));
                report.maximum_propagation_error=std::max(report.maximum_propagation_error,flights.back().error);
                need(flights.back().error<=settings.spatial_tolerance/32,CcdFailure::geometric_guard,
                    "local propagation enclosure exceeds W1 spatial guard budget");
            }
            std::vector<Query> queries;
            const auto evaluate=[&](const Query& q,double horizon,bool guarded,accelerated::Settings rs) {
                identify(report,q,candidates,planes_);
                need(report.pair_queries<settings.max_pair_queries,CcdFailure::query_budget,"W1 pair-query budget exhausted");
                need(report.root_evaluations<settings.max_root_evaluations,CcdFailure::root_budget,"W1 root-evaluation budget exhausted");
                rs.max_evaluations=std::min(rs.max_evaluations,settings.max_root_evaluations-report.root_evaluations);
                auto b=flights[q.b].shape;if(guarded)b.radius=flights[q.b].guard_radius;
                accelerated::Result result;
                if(q.a==detail::absent_body) {
                    const auto& p=planes_[q.plane];result=accelerated::sphere_plane(b,{p.normal,p.offset},horizon,rs);
                } else {
                    auto a=flights[q.a].shape;if(guarded)a.radius=flights[q.a].guard_radius;
                    result=accelerated::sphere_sphere(a,b,horizon,rs);
                }
                ++report.pair_queries;report.root_evaluations+=result.evaluations;
                need(!(result.kind==accelerated::Kind::unresolved&&result.reason==accelerated::Reason::evaluation_budget&&
                    report.root_evaluations==settings.max_root_evaluations),CcdFailure::root_budget,"W1 total root-evaluation budget exhausted");
                return result;
            };
            const auto query=[&](Query q) {
                Vec3 relative_v=flights[q.b].shape.velocity,relative_a=flights[q.b].shape.acceleration;
                if(q.a!=detail::absent_body) {
                    relative_v=relative_v-flights[q.a].shape.velocity;
                    relative_a=relative_a-flights[q.a].shape.acceleration;
                }
                I speed_bound=point(0);
                for(unsigned k=0;k<3;++k)speed_bound=speed_bound+point(std::abs(component(relative_v,k)))+
                    point(std::abs(component(relative_a,k)))*point(remaining);
                q.time_tolerance=settings.time_tolerance/4;
                if(speed_bound.upper()>0)q.time_tolerance=std::min(q.time_tolerance,
                    (point(settings.spatial_tolerance)/(point(16)*point(speed_bound.upper()))).lower());
                need(q.time_tolerance>0,CcdFailure::geometric_guard,"unrepresentable spatially bounded query tolerance");
                accelerated::Settings rs;rs.time_tolerance=q.time_tolerance;
                rs.max_evaluations=settings.query_evaluations;
                rs.max_frontier=settings.query_frontier;rs.max_depth=settings.query_depth;
                q.result=evaluate(q,remaining,false,rs);
                q.error=q.a==detail::absent_body?flights[q.b].error:upper_sum(flights[q.a].error,flights[q.b].error);
                need(q.result.initial_separation_proven,CcdFailure::initial_contact,
                    "W1 requires strictly separated initial candidate states; boundary/support/overlap is unsupported");
                queries.push_back(std::move(q));
            };
            for(std::size_t i=0;i<candidates.size();++i) {
                if(!candidates[i].is_static)for(std::size_t p=0;p<planes_.size();++p)query({detail::absent_body,i,p});
                for(std::size_t j=i+1;j<candidates.size();++j)if(!candidates[i].is_static||!candidates[j].is_static)query({i,j});
            }
            const auto certify_guard=[&](double duration) {
                for(const auto& q:queries) {
                    accelerated::Settings rs;rs.time_tolerance=q.time_tolerance;rs.max_evaluations=settings.query_evaluations;
                    rs.max_frontier=settings.query_frontier;rs.max_depth=settings.query_depth;
                    const auto guarded=evaluate(q,duration,true,rs);
                    need(guarded.kind==accelerated::Kind::none,CcdFailure::geometric_guard,
                        "cannot certify rounded free propagation with expanded-radius guard");
                }
            };
            std::size_t first=queries.size();
            for(std::size_t i=0;i<queries.size();++i)if(queries[i].result.kind==accelerated::Kind::entry_bracket&&
                (first==queries.size()||queries[i].result.bracket->lower()<queries[first].result.bracket->lower()))first=i;
            if(first==queries.size()) {
                for(const auto& q:queries)if(q.result.kind!=accelerated::Kind::none) {
                    identify(report,q,candidates,planes_);throw Stop{CcdFailure::query_unresolved,"W1 cannot certify the entire remaining interval"};
                }
                certify_guard(remaining);advance(remaining,flights);elapsed=dt;break;
            }
            need(report.events.size()<settings.max_event_batches,CcdFailure::event_budget,"W1 event-batch budget exhausted");
            const auto& earliest=queries[first];const I first_bracket=*earliest.result.bracket;
            // Step back from the PROVED safe endpoint. This is bounded early
            // response, not a fake exact impact or a geometric projection.
            double backoff=earliest.time_tolerance;
            for(const auto& q:queries)if(q.result.kind==accelerated::Kind::entry_bracket&&
                q.result.bracket->lower()<=first_bracket.upper())backoff=std::min(backoff,q.time_tolerance);
            const double event_time=std::max(0.0,first_bracket.lower()-backoff);
            std::vector<std::size_t> batch;
            for(std::size_t i=0;i<queries.size();++i) {
                const auto& q=queries[i];
                if(q.result.kind==accelerated::Kind::none)continue;
                if(q.result.kind==accelerated::Kind::unresolved) {
                    if(q.result.safe_until<=first_bracket.upper()) {
                        identify(report,q,candidates,planes_);throw Stop{CcdFailure::query_unresolved,"unresolved pair precedes or overlaps the first impact batch"};
                    }
                } else if(q.result.bracket->lower()<=first_bracket.upper())batch.push_back(i);
                need(q.result.safe_until>=event_time,CcdFailure::query_unresolved,"uncertified pair before selected event time");
            }
            certify_guard(event_time);advance(event_time,flights);elapsed+=event_time;report.candidate_time=elapsed;
            identify(report,earliest,candidates,planes_);
            CcdEvent event;event.responded_at=elapsed;event.entry_lower=infinity;event.entry_upper=0;
            event.first_id=report.first_id;event.second_id=report.second_id;event.contacts=batch.size();
            std::vector<detail::ImpactContact> contacts;contacts.reserve(batch.size());
            for(const auto index:batch) {
                const auto& q=queries[index];identify(report,q,candidates,planes_);
                need(held_witness(q,candidates,flights,planes_,gravity,*q.result.negative_witness).strictly_negative(),
                    CcdFailure::query_unresolved,"nominal entry lacks a negative witness after enclosing real held-load acceleration");
                const double time_guard=(point(q.result.bracket->upper())-point(event_time)).upper();
                need(time_guard<=settings.time_tolerance,CcdFailure::geometric_guard,"overlapping impact batch exceeds W1 time guard");
                const double gap=gap_upper(q,candidates,planes_);
                const double spatial_guard=(point(gap)+point(q.error)+point(2)*point(report.accumulated_position_roundoff)).upper();
                need(spatial_guard<=settings.spatial_tolerance,CcdFailure::geometric_guard,"early impact exceeds W1 spatial guard");
                event.maximum_gap=std::max(event.maximum_gap,spatial_guard);event.propagation_error=std::max(event.propagation_error,q.error);
                // Rounded-acceleration isolation chooses the batch. The enlarged
                // free-prefix proof and real-load witness certify THIS bracket.
                event.entry_lower=std::min(event.entry_lower,integrated_time.lower());
                event.entry_upper=std::max(event.entry_upper,(integrated_time+(point(q.result.bracket->upper())-point(event_time))).upper());
                contacts.push_back(contact(q,candidates,planes_));
                need(normal_speed(contacts.back(),candidates)<-settings.minimum_impact_speed,
                    CcdFailure::sustained_contact_required,"impact normal speed is too small for the W1 impact model");
            }
            const double before=kinetic_energy(candidates);
            StepStats stats;
            try {stats=detail::solve_selected_impacts(candidates,contacts,settings.solver);}
            catch(const std::exception&) {throw Stop{CcdFailure::solver_failure,"selected impact solver failed or exhausted its contact budget"};}
            const double after=kinetic_energy(candidates);
            need(std::isfinite(after)&&after<=before+settings.relative_energy_tolerance*std::max(1.0,before),
                CcdFailure::solver_failure,"impact batch increases kinetic energy beyond configured audit tolerance");
            need(stats.max_closing_residual<=settings.closing_residual_tolerance,CcdFailure::solver_failure,
                "impact batch closing/restitution residual exceeds tolerance");
            for(const auto& c:contacts) {
                Vec3 a=flights[c.b].shape.acceleration;
                if(c.a!=detail::absent_body)a=a-flights[c.a].shape.acceleration;
                double radial_acceleration=a.dot(c.normal);
                if(c.a!=detail::absent_body) {
                    const auto dv=candidates[c.b].velocity-candidates[c.a].velocity;
                    const double vn=dv.dot(c.normal);const auto tangent=dv-c.normal*vn;
                    radial_acceleration+=tangent.dot(tangent)/std::hypot(
                        candidates[c.b].position.x-candidates[c.a].position.x,
                        candidates[c.b].position.y-candidates[c.a].position.y,
                        candidates[c.b].position.z-candidates[c.a].position.z);
                }
                need(!(normal_speed(c,candidates)<=settings.minimum_impact_speed&&radial_acceleration<0),
                    CcdFailure::sustained_contact_required,"inelastic impact with inward acceleration requires W2 support forces");
            }
            report.impact_stats.contacts+=stats.contacts;
            report.impact_stats.velocity_iterations+=stats.velocity_iterations;
            report.impact_stats.normal_impulse_sum+=stats.normal_impulse_sum;
            report.impact_stats.friction_impulse_sum+=stats.friction_impulse_sum;
            report.impact_stats.max_closing_residual=std::max(report.impact_stats.max_closing_residual,stats.max_closing_residual);
            report.events.push_back(event);
        }
        report.time_roundoff=magnitude(integrated_time-point(dt));
        need(report.time_roundoff<=settings.time_tolerance/16,CcdFailure::geometric_guard,"integrated segment-time roundoff exceeds W1 budget");
        for(auto& body:candidates){body.force={};body.torque={};body.validate();}
        report.success=true;report.advanced_dt=dt;report.candidate_time=dt;report.first_id=report.second_id=0;
        std::copy(candidates.begin(),candidates.end(),bodies_.begin());
    } catch(const Stop& stop) {report.failure=stop.failure;report.message=stop.message;}
      catch(const std::exception& error) {report.failure=CcdFailure::numerical_failure;report.message=error.what();}
    return report;
}

detail::FreeFlightTubeResult detail::enclose_free_flight(const RigidBody& body,Vec3 gravity,double horizon) noexcept {
    FreeFlightTubeResult out;
    const auto reject=[&](CcdFailure failure,const char* message) noexcept {
        out.tube.reset();out.failure=failure;
        try {out.message=message;}catch(...) {out.message.clear();}
    };
    try {
        interval::require_environment();
        const auto original=flight(body,gravity,horizon);
        out.tube=FreeFlightTube{original.shape.acceleration,original.error,original.roundoff,original.guard_radius};
    }catch(const Stop& stop) {
        reject(stop.failure,stop.message);
    }catch(const std::exception& error) {
        reject(CcdFailure::numerical_failure,error.what());
    }catch(...) {
        reject(CcdFailure::numerical_failure,"Unknown W1 free-flight enclosure failure");
    }
    return out;
}
}
