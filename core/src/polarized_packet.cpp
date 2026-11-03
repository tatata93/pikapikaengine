#include "pikapika/polarized_packet.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <type_traits>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Polarized packet requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::polarized_packet {
namespace {
using I=Interval;namespace pr=polarized_route;namespace rt=optical_route;namespace ob=optical_bounds;
I p(double x){return I::point(x);}
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
void vector_valid(const ob::Bounds3& v){for(I x:v)if(!finite(x)||x.lower()<-1e6||x.upper()>1e6)throw std::invalid_argument("Packet vector endpoints outside finite +/-1e6 domain");}
void position_valid(Vec3 v){vector_valid(ob::enclose(v));}
void axis_valid(Vec3 v){position_valid(v);if(std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<1e-6)throw std::invalid_argument("Packet shape axis max component below 1e-6");}
void radius_valid(double x){if(!std::isfinite(x)||x<1e-6||x>1e6)throw std::invalid_argument("Packet radius/aperture outside [1e-6,1e6]");}
void domain_valid(double a,double b){if(!std::isfinite(a)||!std::isfinite(b)||a<0||a>b||b>1e9)throw std::invalid_argument("Packet parameter domain outside [0,1e9]");}
void index_valid(I x){if(!finite(x)||x.lower()<1e-6||x.upper()>1e6)throw std::invalid_argument("Packet index endpoints outside [1e-6,1e6]");}
void disk_valid(const optical_geometry::PlaneDisk& d){position_valid(d.center);axis_valid(d.normal);radius_valid(d.aperture_radius);}
void surface_valid(const rt::Surface& surface){
    if(surface.valueless_by_exception())throw std::invalid_argument("Valueless packet route surface");
    std::visit([](const auto&s){using T=std::decay_t<decltype(s)>;
        if constexpr(std::is_same_v<T,optical_geometry::PlaneDisk>)disk_valid(s);
        else if constexpr(std::is_same_v<T,optical_geometry::FullSphere>){position_valid(s.center);radius_valid(s.radius);}
        else{position_valid(s.vertex);axis_valid(s.axis);radius_valid(std::abs(s.signed_radius));radius_valid(s.aperture_radius);if(s.aperture_radius>std::abs(s.signed_radius))throw std::invalid_argument("Packet cap aperture exceeds radius");}
    },surface);
}
void power_valid(const pr::Stokes& s){
    for(double x:{s.i,s.q,s.u,s.v})if(!std::isfinite(x)||std::abs(x)>1e12)throw std::invalid_argument("Packet Stokes watts outside finite +/-1e12 domain");
    if(s.i<0||(s.i==0&&(s.q!=0||s.u!=0||s.v!=0)))throw std::invalid_argument("Packet Stokes outside physical cone");
    const unsigned nonzero=unsigned(s.q!=0)+unsigned(s.u!=0)+unsigned(s.v!=0);
    if(nonzero==0||(nonzero==1&&(std::abs(s.q)==s.i||std::abs(s.u)==s.i||std::abs(s.v)==s.i)))return;
    const I delta=interval::square(p(s.i))-interval::square(p(s.q))-interval::square(p(s.u))-interval::square(p(s.v));
    if(delta.upper()<0)throw std::invalid_argument("Packet Stokes provably outside exact physical cone");
    // A mixed interval is NOT admitted as proven physical. The unchanged route
    // kernel retains initial_state_uncertain and this batch has no final tally.
}
void settings_valid(const Settings& s){
    const auto&pr=s.route;const auto&rt=pr.route;const auto&ob=rt.primitive;
    if(s.max_packets<1||s.max_packets>1024||s.max_evaluations<1||s.max_evaluations>1024||s.max_total_sqrt_refinements<1||s.max_total_sqrt_refinements>4000000||pr.max_sqrt_refinements<1||pr.max_sqrt_refinements>256||pr.max_total_sqrt_refinements<1||pr.max_total_sqrt_refinements>4000000||rt.maximum_steps<1||rt.maximum_steps>64||ob.max_sqrt_refinements<1||ob.max_sqrt_refinements>256||!std::isfinite(ob.maximum_parameter_width)||ob.maximum_parameter_width<=0||ob.maximum_parameter_width>1e6)throw std::invalid_argument("Invalid packet route/batch budgets");
}
PacketStatus classify(const pr::Result& r){
    switch(r.status){
        case pr::Status::completed:return PacketStatus::accepted;
        case pr::Status::power_unresolved:return PacketStatus::power_unresolved;
        case pr::Status::budget_exceeded:return PacketStatus::budget_exceeded;
        case pr::Status::invalid_input:return PacketStatus::invalid_input;
        case pr::Status::numerical_failure:return PacketStatus::numerical_failure;
        default:break;
    }
    if(!r.geometry)return PacketStatus::numerical_failure;
    switch(r.geometry->status){
        case rt::Status::geometry_miss:return PacketStatus::route_miss;
        case rt::Status::branch_unavailable:return PacketStatus::branch_unavailable;
        case rt::Status::geometry_unresolved:case rt::Status::interface_unresolved:return PacketStatus::route_unresolved;
        case rt::Status::budget_exceeded:return PacketStatus::budget_exceeded;
        default:return PacketStatus::numerical_failure;
    }
}
void count(Result& out,PacketStatus status){
    switch(status){
        case PacketStatus::accepted:++out.accepted;--out.unknown;break;
        case PacketStatus::route_miss:++out.route_misses;--out.unknown;break;
        case PacketStatus::branch_unavailable:++out.branch_unavailable;--out.unknown;break;
        case PacketStatus::sensor_miss:++out.sensor_misses;--out.unknown;break;
        default:break;
    }
}
bool over_budget(const Result& out,const Settings& s){return out.geometry_sqrt_refinements+out.power_sqrt_refinements+out.sensor_sqrt_refinements>s.max_total_sqrt_refinements;}
I nonnegative(I x){if(!finite(x)||x.upper()<0)throw std::domain_error("Nonfinite or inconsistent packet POWER sum");return I(std::max(0.0,x.lower()),x.upper());}
Stats aggregate(const Result& out){
    Stats s;
    for(const auto&r:out.records){s.total_source_power=nonnegative(s.total_source_power+p(r.power.i));if(r.status!=PacketStatus::accepted)continue;
        s.accepted_source_power=nonnegative(s.accepted_source_power+p(r.power.i));
        if(!r.sensor_power)throw std::logic_error("Accepted packet lacks sensor POWER");
        s.detected_power=nonnegative(s.detected_power+*r.sensor_power);
    }
    // Each term is a passive ray-tube POWER. Intersect only physically proven
    // inequalities, with outward source bounds, never ordinary rounded sums.
    const auto accepted=interval::intersection(s.accepted_source_power,I(0,s.total_source_power.upper()));
    if(!accepted)throw std::domain_error("Inconsistent accepted source POWER");s.accepted_source_power=*accepted;
    const auto detected=interval::intersection(s.detected_power,I(0,s.accepted_source_power.upper()));
    if(!detected)throw std::domain_error("Inconsistent detected POWER");s.detected_power=*detected;return s;
}
}

Result evaluate(const Input& input,const Settings& settings){
    Result out;bool checked=false;Record* active=nullptr;
    try{
        interval::require_environment();settings_valid(settings);index_valid(input.initial_index);disk_valid(input.sensor);domain_valid(input.sensor_minimum_parameter,input.sensor_maximum_parameter);
        if(!std::isfinite(input.vacuum_wavelength_m)||input.vacuum_wavelength_m<=0)throw std::invalid_argument("Packet vacuum wavelength must be positive finite");
        if(input.packets.size()>settings.max_packets||input.steps.size()>settings.route.route.maximum_steps){out.status=Status::budget_exceeded;out.message="Packet/step count exceeds admitted budget before work";return out;}
        for(const auto&step:input.steps){surface_valid(step.surface);index_valid(step.next_index);domain_valid(step.minimum_parameter,step.maximum_parameter);if(step.branch!=rt::Branch::reflected&&step.branch!=rt::Branch::transmitted)throw std::invalid_argument("Invalid packet route branch");}
        for(const auto&packet:input.packets){vector_valid(packet.ray.origin);vector_valid(packet.ray.direction);domain_valid(packet.ray.minimum_parameter,packet.ray.maximum_parameter);position_valid(packet.transverse_reference);power_valid(packet.power);}
        checked=true;out.records.reserve(input.packets.size());out.unknown=unsigned(input.packets.size());
        for(unsigned j=0;j<input.packets.size();++j)out.records.push_back({j,input.packets[j].power});
        bool budget=false,numerical=false;
        for(unsigned j=0;j<input.packets.size();++j){
            if(out.evaluations>=settings.max_evaluations){budget=true;out.message="Packet evaluation budget exhausted";break;}
            const auto&packet=input.packets[j];auto&record=out.records[j];active=&record;++out.evaluations;
            record.route=pr::trace_route({{packet.ray,input.initial_index,input.vacuum_wavelength_m,input.steps},packet.power,packet.transverse_reference},settings.route);
            const auto&route=*record.route;out.geometry_queries+=route.geometry_queries;out.interface_queries+=route.interface_queries;
            out.geometry_sqrt_refinements+=route.geometry_sqrt_refinements;out.power_sqrt_refinements+=route.power_sqrt_refinements;out.refinement_limited=out.refinement_limited||route.refinement_limited;
            record.status=classify(route);
            if(route.status==pr::Status::completed){
                if(!route.completion)throw std::logic_error("Completed packet route lacks completion");
                auto ray=route.completion->ray;ray.minimum_parameter=input.sensor_minimum_parameter;ray.maximum_parameter=input.sensor_maximum_parameter;
                ++out.sensor_queries;record.sensor=ob::intersect(ray,input.sensor,settings.route.route.primitive);
                out.sensor_sqrt_refinements+=record.sensor->sqrt_refinements;out.refinement_limited=out.refinement_limited||record.sensor->refinement_limited;
                switch(record.sensor->status){
                    case ob::Status::hit:
                        if(!record.sensor->nearest)throw std::logic_error("Packet sensor hit lacks position");
                        record.status=PacketStatus::accepted;record.sensor_power=route.completion->state.power;break;
                    case ob::Status::miss:record.status=PacketStatus::sensor_miss;break;
                    default:record.status=record.sensor->reason==ob::Reason::refinement_budget?PacketStatus::budget_exceeded:PacketStatus::sensor_unresolved;break;
                }
            }
            if(over_budget(out,settings)){record.status=PacketStatus::budget_exceeded;record.sensor_power.reset();budget=true;out.message="Packet total reported sqrt work exceeds batch budget";break;}
            count(out,record.status);
            if(record.status==PacketStatus::budget_exceeded){budget=true;out.message="Packet route/sensor budget exhausted";break;}
            if(record.status==PacketStatus::invalid_input||record.status==PacketStatus::numerical_failure){numerical=true;record.sensor_power.reset();out.message="Preflighted packet failed numerically";break;}
            active=nullptr;
        }
        if(numerical){out.status=Status::numerical_failure;return out;}
        if(budget){out.status=Status::budget_exceeded;return out;}
        if(out.unknown){out.status=Status::unresolved;out.message="Unknown packets prohibit final POWER tally";return out;}
        out.final_stats=aggregate(out);out.status=Status::completed;return out;
    }catch(const std::invalid_argument&e){out.status=checked?Status::numerical_failure:Status::invalid_input;out.message=e.what();}
    catch(const std::exception&e){out.status=Status::numerical_failure;out.message=e.what();}
    if(active){active->status=PacketStatus::numerical_failure;active->sensor_power.reset();}
    out.final_stats.reset();return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
