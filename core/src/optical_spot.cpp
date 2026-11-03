#include "pikapika/optical_spot.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <type_traits>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Optical spot requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optical_spot {
namespace {
using I=Interval;
I p(double v){return I::point(v);}
bool finite(I i){return std::isfinite(i.lower())&&std::isfinite(i.upper());}
void vector_valid(const Bounds3& v){for(I x:v)if(!finite(x)||x.lower()<-1e6||x.upper()>1e6)throw std::invalid_argument("Spot vector endpoints must be finite within +/-1e6");}
void position_valid(Vec3 v){vector_valid(optical_bounds::enclose(v));}
void axis_valid(Vec3 v){position_valid(v);if(std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<1e-6)throw std::invalid_argument("Spot shape axis max component must be >=1e-6");}
void radius_valid(double r){if(!std::isfinite(r)||r<1e-6||r>1e6)throw std::invalid_argument("Spot shape radius/aperture outside [1e-6,1e6]");}
void domain_valid(double lo,double hi){if(!std::isfinite(lo)||!std::isfinite(hi)||lo<0||lo>hi||hi>1e9)throw std::invalid_argument("Spot ray closed domain outside [0,1e9]");}
void ray_valid(const optical_bounds::BoundedRay& ray){vector_valid(ray.origin);vector_valid(ray.direction);domain_valid(ray.minimum_parameter,ray.maximum_parameter);}
void index_valid(I i){if(!finite(i)||i.lower()<1e-6||i.upper()>1e6)throw std::invalid_argument("Spot phase index outside [1e-6,1e6]");}
void disk_valid(const optical_geometry::PlaneDisk& d){position_valid(d.center);axis_valid(d.normal);radius_valid(d.aperture_radius);}
void surface_valid(const optical_route::Surface& surface){
    if(surface.valueless_by_exception())throw std::invalid_argument("Valueless spot route surface");
    std::visit([](const auto& s){using T=std::decay_t<decltype(s)>;
        if constexpr(std::is_same_v<T,optical_geometry::PlaneDisk>)disk_valid(s);
        else if constexpr(std::is_same_v<T,optical_geometry::FullSphere>){position_valid(s.center);radius_valid(s.radius);}
        else{position_valid(s.vertex);axis_valid(s.axis);radius_valid(std::abs(s.signed_radius));radius_valid(s.aperture_radius);if(s.aperture_radius>std::abs(s.signed_radius))throw std::invalid_argument("Spot cap aperture exceeds radius");}
    },surface);
}
void settings_valid(const Settings& s){
    if(s.max_samples<1||s.max_samples>1024||s.max_evaluations<1||s.max_evaluations>1024||s.max_sqrt_refinements<1||s.max_sqrt_refinements>4000000||s.route.maximum_steps<1||s.route.maximum_steps>64||
       !std::isfinite(s.route.primitive.maximum_parameter_width)||s.route.primitive.maximum_parameter_width<=0||s.route.primitive.maximum_parameter_width>1e6||s.route.primitive.max_sqrt_refinements<1||s.route.primitive.max_sqrt_refinements>256)throw std::invalid_argument("Invalid spot route/sample/work budget");
}
RouteSummary summarize(const optical_route::Result& route){
    RouteSummary out;out.status=route.status;out.completed_steps=route.completed_steps;out.failed_step=route.failed_step;out.completion=route.completion;
    out.geometry_queries=unsigned(route.segments.size());
    for(const auto& segment:route.segments){out.sqrt_refinements+=segment.geometry.sqrt_refinements;out.refinement_limited=out.refinement_limited||segment.geometry.refinement_limited;
        if(segment.interface){++out.interface_queries;out.sqrt_refinements+=segment.interface->sqrt_refinements;out.refinement_limited=out.refinement_limited||segment.interface->refinement_limited;}}
    return out;
}
SampleStatus route_status(optical_route::Status status){
    switch(status){
        case optical_route::Status::completed:return SampleStatus::accepted;
        case optical_route::Status::geometry_miss:return SampleStatus::route_miss;
        case optical_route::Status::branch_unavailable:return SampleStatus::branch_unavailable;
        case optical_route::Status::geometry_unresolved:case optical_route::Status::interface_unresolved:return SampleStatus::route_unresolved;
        case optical_route::Status::budget_exceeded:return SampleStatus::budget_exceeded;
        case optical_route::Status::invalid_input:return SampleStatus::invalid_input;
        default:return SampleStatus::numerical_failure;
    }
}
void count(Result& result,SampleStatus status){
    switch(status){
        case SampleStatus::accepted:++result.accepted;--result.unknown;break;
        case SampleStatus::route_miss:++result.route_misses;--result.unknown;break;
        case SampleStatus::branch_unavailable:++result.branch_unavailable;--result.unknown;break;
        case SampleStatus::sensor_miss:++result.sensor_misses;--result.unknown;break;
        default:break;
    }
}
Stats aggregate(const Result& result){
    Stats stats;Bounds3 weighted{p(0),p(0),p(0)};std::optional<Bounds3> hull;
    for(const auto& record:result.records){const I weight=p(record.weight);stats.total_weight=stats.total_weight+weight;
        if(record.status!=SampleStatus::accepted)continue;
        stats.accepted_weight=stats.accepted_weight+weight;const auto& position=record.sensor->nearest->position;
        for(unsigned k=0;k<3;++k)weighted[k]=weighted[k]+weight*position[k];
        if(!hull)hull=position;else for(unsigned k=0;k<3;++k)(*hull)[k]=interval::hull((*hull)[k],position[k]);
    }
    if(!hull)return stats;
    if(!stats.accepted_weight.strictly_positive())throw std::domain_error("Spot accepted weight not certified positive");
    Moments moments;moments.hull=*hull;
    for(unsigned k=0;k<3;++k)moments.centroid[k]=weighted[k]/stats.accepted_weight;
    I variance=p(0);
    for(const auto& record:result.records)if(record.status==SampleStatus::accepted){const auto& position=record.sensor->nearest->position;I distance2=p(0);
        for(unsigned k=0;k<3;++k)distance2=distance2+interval::square(position[k]-moments.centroid[k]);
        variance=variance+p(record.weight)*distance2;
    }
    variance=variance/stats.accepted_weight;
    if(!finite(variance)||variance.upper()<0)throw std::domain_error("Nonfinite spot variance enclosure");
    moments.mean_squared_radius=I(std::max(0.0,variance.lower()),variance.upper());stats.moments=moments;return stats;
}
}

optical_bounds::BoundedRay make_launch_ray(const Source& source,Vec3 launch,double lo,double hi){
    interval::require_environment();position_valid(source.reference);position_valid(launch);domain_valid(lo,hi);
    optical_bounds::BoundedRay ray;ray.minimum_parameter=lo;ray.maximum_parameter=hi;
    if(source.kind==SourceKind::finite_point){ray.origin=optical_bounds::enclose(source.reference);const auto point=optical_bounds::enclose(launch);for(unsigned k=0;k<3;++k)ray.direction[k]=point[k]-ray.origin[k];}
    else if(source.kind==SourceKind::parallel_beam){ray.origin=optical_bounds::enclose(launch);ray.direction=optical_bounds::enclose(source.reference);}
    else throw std::invalid_argument("Invalid spot source kind");
    ray_valid(ray);return ray;
}

Result evaluate(const Input& input,const Settings& settings){
    Result result;bool preflight_complete=false;Record* active_record=nullptr;
    try{
        interval::require_environment();settings_valid(settings);index_valid(input.initial_index);disk_valid(input.sensor);domain_valid(input.sensor_minimum_parameter,input.sensor_maximum_parameter);
        if(!std::isfinite(input.vacuum_wavelength_m)||input.vacuum_wavelength_m<=0)throw std::invalid_argument("Spot wavelength must be finite and positive");
        if(input.samples.size()>settings.max_samples||input.steps.size()>settings.route.maximum_steps){result.status=Status::budget_exceeded;result.message="Spot sample/step count exceeds budget before evaluations";return result;}
        for(const auto& step:input.steps){surface_valid(step.surface);index_valid(step.next_index);domain_valid(step.minimum_parameter,step.maximum_parameter);if(step.branch!=optical_route::Branch::reflected&&step.branch!=optical_route::Branch::transmitted)throw std::invalid_argument("Invalid spot route branch");}
        for(const auto& sample:input.samples){ray_valid(sample.ray);if(!std::isfinite(sample.weight)||sample.weight<1e-12||sample.weight>1e6)throw std::invalid_argument("Spot geometric weight outside [1e-12,1e6]");}
        preflight_complete=true;
        result.records.reserve(input.samples.size());result.unknown=unsigned(input.samples.size());
        for(std::size_t j=0;j<input.samples.size();++j)result.records.push_back({unsigned(j),input.samples[j].weight,SampleStatus::not_examined,{},{}});
        bool limited=false,numerical=false;
        for(std::size_t j=0;j<input.samples.size();++j){
            if(result.evaluations>=settings.max_evaluations){limited=true;result.message="Spot sample evaluation budget exhausted";break;}
            ++result.evaluations;auto& record=result.records[j];active_record=&record;const auto& sample=input.samples[j];
            record.route=summarize(optical_route::trace_route({sample.ray,input.initial_index,input.vacuum_wavelength_m,input.steps},settings.route));
            result.geometry_queries+=record.route->geometry_queries;result.interface_queries+=record.route->interface_queries;result.sqrt_refinements+=record.route->sqrt_refinements;result.refinement_limited=result.refinement_limited||record.route->refinement_limited;
            record.status=route_status(record.route->status);
            if(record.route->status==optical_route::Status::completed){
                if(!record.route->completion)throw std::logic_error("Completed spot route lacks output ray");
                auto ray=record.route->completion->ray;ray.minimum_parameter=input.sensor_minimum_parameter;ray.maximum_parameter=input.sensor_maximum_parameter;
                ++result.geometry_queries;record.sensor=optical_bounds::intersect(ray,input.sensor,settings.route.primitive);
                result.sqrt_refinements+=record.sensor->sqrt_refinements;result.refinement_limited=result.refinement_limited||record.sensor->refinement_limited;
                switch(record.sensor->status){
                    case optical_bounds::Status::hit:if(!record.sensor->nearest)throw std::logic_error("Spot sensor hit lacks bounds");record.status=SampleStatus::accepted;break;
                    case optical_bounds::Status::miss:record.status=SampleStatus::sensor_miss;break;
                    default:record.status=record.sensor->reason==optical_bounds::Reason::refinement_budget?SampleStatus::budget_exceeded:SampleStatus::sensor_unresolved;break;
                }
            }
            if(result.sqrt_refinements>settings.max_sqrt_refinements){record.status=SampleStatus::budget_exceeded;limited=true;result.message="Spot total reported sqrt work exceeds budget";break;}
            count(result,record.status);
            limited=limited||record.status==SampleStatus::budget_exceeded;
            numerical=numerical||record.status==SampleStatus::invalid_input||record.status==SampleStatus::numerical_failure;
            active_record=nullptr;
        }
        if(numerical){result.status=Status::numerical_failure;result.message="A preflighted sample route returned an input/numerical failure";return result;}
        if(limited){result.status=Status::budget_exceeded;return result;}
        if(result.unknown){result.status=Status::unresolved;result.message="Unknown samples prohibit final geometric statistics";return result;}
        result.final_stats=aggregate(result);result.status=Status::completed;return result;
    }catch(const std::invalid_argument& e){result.status=preflight_complete?Status::numerical_failure:Status::invalid_input;result.message=e.what();}
    catch(const std::exception& e){result.status=Status::numerical_failure;result.message=e.what();}
    if(active_record)active_record->status=SampleStatus::numerical_failure;
    result.final_stats.reset();return result;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
