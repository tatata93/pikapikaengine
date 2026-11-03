#include "pikapika/optical_selection.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <type_traits>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Optical selection requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optical_selection {
namespace {
using I=interval::Interval;
bool finite(I v){return std::isfinite(v.lower())&&std::isfinite(v.upper());}
void vector_valid(const optical_bounds::Bounds3& v){
    for(I a:v)if(!finite(a)||a.lower()<-1e6||a.upper()>1e6)throw std::invalid_argument("Selection vector endpoints must be finite within +/-1e6");
}
void position_valid(Vec3 v){vector_valid(optical_bounds::enclose(v));}
void axis_valid(Vec3 v){
    position_valid(v);
    if(std::max({std::abs(v.x),std::abs(v.y),std::abs(v.z)})<1e-6)throw std::invalid_argument("Selection shape axis max component must be >=1e-6");
}
void radius_valid(double radius){
    if(!std::isfinite(radius)||radius<1e-6||radius>1e6)throw std::invalid_argument("Selection radius/aperture outside [1e-6,1e6]");
}
void surface_valid(const Surface& surface){
    if(surface.valueless_by_exception())throw std::invalid_argument("Valueless selection surface");
    std::visit([](const auto& s){
        using T=std::decay_t<decltype(s)>;
        if constexpr(std::is_same_v<T,optical_geometry::PlaneDisk>){position_valid(s.center);axis_valid(s.normal);radius_valid(s.aperture_radius);}
        else if constexpr(std::is_same_v<T,optical_geometry::FullSphere>){position_valid(s.center);radius_valid(s.radius);}
        else{position_valid(s.vertex);axis_valid(s.axis);radius_valid(std::abs(s.signed_radius));radius_valid(s.aperture_radius);
             if(s.aperture_radius>std::abs(s.signed_radius))throw std::invalid_argument("Selection cap aperture exceeds radius");}
    },surface);
}
void settings_valid(const Settings& s){
    if(s.max_surfaces<1||s.max_surfaces>1024||s.max_queries<1||s.max_queries>4096||s.max_sqrt_refinements<1||s.max_sqrt_refinements>1000000||
       !std::isfinite(s.primitive.maximum_parameter_width)||s.primitive.maximum_parameter_width<=0||s.primitive.maximum_parameter_width>1e6||
       s.primitive.max_sqrt_refinements<1||s.primitive.max_sqrt_refinements>256)throw std::invalid_argument("Invalid selection budget/primitive settings");
}
void ray_valid(const optical_bounds::BoundedRay& ray){
    vector_valid(ray.origin);vector_valid(ray.direction);
    if(!std::isfinite(ray.minimum_parameter)||!std::isfinite(ray.maximum_parameter)||ray.minimum_parameter<0||ray.minimum_parameter>ray.maximum_parameter||ray.maximum_parameter>1e9)throw std::invalid_argument("Invalid selection closed ray domain");
}
bool refinement_budget(const optical_bounds::Result& r){return r.status==optical_bounds::Status::unresolved&&r.reason==optical_bounds::Reason::refinement_budget;}
}

Result find_nearest(const optical_bounds::BoundedRay& ray,std::span<const SurfaceRecord> input,const Settings& settings){
    Result result;bool preflight_complete=false;
    try{
        interval::require_environment();settings_valid(settings);ray_valid(ray);
        if(input.size()>settings.max_surfaces){result.status=Status::budget_exceeded;result.message="Selection surface budget exceeded before queries";return result;}
        std::vector<const SurfaceRecord*> ordered;ordered.reserve(input.size());
        for(const auto& record:input){
            if(record.id==0)throw std::invalid_argument("Selection IDs must be positive");
            surface_valid(record.surface);ordered.push_back(&record);
        }
        std::sort(ordered.begin(),ordered.end(),[](const auto* a,const auto* b){return a->id<b->id;});
        for(std::size_t j=1;j<ordered.size();++j)if(ordered[j-1]->id==ordered[j]->id)throw std::invalid_argument("Duplicate selection surface ID");
        preflight_complete=true;
        // A zero direction is representable input but cannot certify a ray.
        const auto& d=ray.direction;
        if(!((interval::square(d[0])+interval::square(d[1]))+interval::square(d[2])).strictly_positive()){
            result.status=Status::unresolved;result.message="Selection direction is not certified nonzero";return result;
        }
        result.surfaces.reserve(ordered.size());
        for(std::size_t j=0;j<ordered.size();++j)result.surfaces.push_back({ordered[j]->id,unsigned(j),{},{},false});
        const auto query=[&](std::size_t index,const optical_bounds::BoundedRay& domain,bool prefix){
            if(result.queries>=settings.max_queries){result.status=Status::budget_exceeded;result.message="Selection query budget exhausted";return false;}
            ++result.queries;if(prefix)++result.prefix_queries;
            auto geometry=std::visit([&](const auto& surface){return optical_bounds::intersect(domain,surface,settings.primitive);},ordered[index]->surface);
            result.sqrt_refinements+=geometry.sqrt_refinements;result.refinement_limited=result.refinement_limited||geometry.refinement_limited;
            auto& diagnostic=result.surfaces[index];
            if(prefix)diagnostic.prefix=std::move(geometry);else diagnostic.geometry=std::move(geometry);
            if(result.sqrt_refinements>settings.max_sqrt_refinements){result.status=Status::budget_exceeded;result.message="Selection total actual sqrt work exceeds budget";return false;}
            return true;
        };
        std::optional<std::size_t> candidate;bool all_miss=true,original_budget=false;
        for(std::size_t j=0;j<ordered.size();++j){
            if(!query(j,ray,false))return result;
            const auto& geometry=*result.surfaces[j].geometry;
            all_miss=all_miss&&geometry.status==optical_bounds::Status::miss;
            original_budget=original_budget||refinement_budget(geometry);
            if(geometry.status==optical_bounds::Status::hit){
                if(!geometry.nearest)throw std::logic_error("Primitive hit lacks hit bounds");
                if(!candidate||geometry.nearest->parameter.upper()<result.surfaces[*candidate].geometry->nearest->parameter.upper())candidate=j;
            }
        }
        if(all_miss){result.status=Status::miss;return result;}
        if(!candidate){result.status=original_budget?Status::budget_exceeded:Status::unresolved;result.message="No uniform primitive hit certifies a candidate";return result;}
        const auto& hit=*result.surfaces[*candidate].geometry->nearest;
        bool blocked=false,blocked_budget=false;
        for(std::size_t j=0;j<ordered.size();++j){
            if(j==*candidate)continue;
            auto& diagnostic=result.surfaces[j];const auto& geometry=*diagnostic.geometry;
            if(geometry.status==optical_bounds::Status::miss)continue;
            if(geometry.status==optical_bounds::Status::hit&&hit.parameter.upper()<geometry.nearest->parameter.lower())continue;
            if(settings.allow_prefix_exclusion){
                auto prefix=ray;prefix.maximum_parameter=hit.parameter.upper();
                if(!query(j,prefix,true))return result;
                if(diagnostic.prefix->status==optical_bounds::Status::miss){diagnostic.excluded_by_prefix=true;continue;}
            }
            blocked=true;blocked_budget=blocked_budget||refinement_budget(geometry)||(diagnostic.prefix&&refinement_budget(*diagnostic.prefix));
        }
        if(blocked){result.status=blocked_budget?Status::budget_exceeded:Status::unresolved;result.message="A rival surface is not certified strictly later or absent on the closed prefix";return result;}
        result.status=Status::hit;result.nearest=Selection{ordered[*candidate]->id,hit};return result;
    }catch(const std::invalid_argument& e){result.status=preflight_complete?Status::numerical_failure:Status::invalid_input;result.message=e.what();}
    catch(const std::exception& e){result.status=Status::numerical_failure;result.message=e.what();}
    result.nearest.reset();return result;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
