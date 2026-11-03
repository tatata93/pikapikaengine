#include "pikapika/optical_route.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Optical route requires strict floating point, no fast-math or contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optical_route {
namespace {
using I=Interval;
bool finite(I x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
void index_valid(I x){if(!finite(x)||x.lower()<1e-6||x.upper()>1e6)throw std::invalid_argument("Route index endpoints must lie in [1e-6,1e6]");}
void domain_valid(double lo,double hi){if(!std::isfinite(lo)||!std::isfinite(hi)||lo<0||lo>hi||hi>1e9)throw std::invalid_argument("Route parameter domain must lie in [0,1e9]");}
void vector_valid(const optical_bounds::Bounds3& v){for(I x:v)if(!finite(x)||x.lower()<-1e6||x.upper()>1e6)throw std::invalid_argument("Route ray endpoints must lie in [-1e6,1e6]");}
I nonnegative(I x){if(!finite(x)||x.upper()<0)throw std::domain_error("Nonfinite or inconsistent route length");return I(std::max(0.0,x.lower()),x.upper());}
I power(I x){if(!finite(x)||x.upper()<0||x.lower()>1)throw std::domain_error("Nonfinite or inconsistent route power");return I(std::max(0.0,x.lower()),std::min(1.0,x.upper()));}
I factor(const optical_bounds::Power& p,Branch branch){
    const I s=branch==Branch::reflected?p.reflectance_s:p.transmittance_s;
    const I t=branch==Branch::reflected?p.reflectance_p:p.transmittance_p;
    return power(I(std::min(s.lower(),t.lower()),std::max(s.upper(),t.upper())));
}
}
Result trace_route(const Input& input,const Settings& settings){
    Result result;
    try{
        interval::require_environment();
        if(settings.maximum_steps<1||settings.maximum_steps>64||settings.primitive.max_sqrt_refinements<1||settings.primitive.max_sqrt_refinements>256||!std::isfinite(settings.primitive.maximum_parameter_width)||settings.primitive.maximum_parameter_width<=0||settings.primitive.maximum_parameter_width>1e6)throw std::invalid_argument("Invalid route step/primitive budget");
        vector_valid(input.ray.origin);vector_valid(input.ray.direction);domain_valid(input.ray.minimum_parameter,input.ray.maximum_parameter);index_valid(input.index);
        if(!std::isfinite(input.vacuum_wavelength_m)||input.vacuum_wavelength_m<=0)throw std::invalid_argument("Route needs a positive finite vacuum wavelength");
        if(input.steps.size()>settings.maximum_steps){result.status=Status::budget_exceeded;result.message="Requested itinerary exceeds step budget";return result;}
        // Preflight scalar inputs, including unused other-side indices, so an
        // invalid later index cannot masquerade as an earlier geometric miss.
        for(std::size_t j=0;j<input.steps.size();++j){
            result.failed_step=unsigned(j);const auto& step=input.steps[j];
            index_valid(step.next_index);domain_valid(step.minimum_parameter,step.maximum_parameter);
            if(step.branch!=Branch::reflected&&step.branch!=Branch::transmitted)throw std::invalid_argument("Invalid route branch");
        }
        result.failed_step=0;
        optical_bounds::BoundedRay ray=input.ray;I current=input.index;Totals totals;
        result.segments.reserve(input.steps.size());
        for(const auto& step:input.steps){
            result.failed_step=result.completed_steps;
            ray.minimum_parameter=step.minimum_parameter;ray.maximum_parameter=step.maximum_parameter;
            result.segments.emplace_back();auto& segment=result.segments.back();
            segment.incoming=ray;segment.incident_index=current;segment.other_index=step.next_index;segment.branch=step.branch;
            segment.geometry=std::visit([&](const auto& surface){return optical_bounds::intersect(ray,surface,settings.primitive);},step.surface);
            if(segment.geometry.status!=optical_bounds::Status::hit){
                result.status=segment.geometry.status==optical_bounds::Status::miss?Status::geometry_miss:segment.geometry.reason==optical_bounds::Reason::refinement_budget?Status::budget_exceeded:Status::geometry_unresolved;
                result.message="Prescribed surface did not yield a certified family hit";return result;
            }
            const auto& hit=*segment.geometry.nearest;
            segment.interface=optical_bounds::dielectric_interface_bounds({ray.direction,hit.incident_normal,current,step.next_index,input.vacuum_wavelength_m},settings.primitive);
            const auto& interface=*segment.interface;
            if(interface.kind==optical_bounds::InterfaceKind::unresolved){result.status=interface.reason==optical_bounds::Reason::refinement_budget?Status::budget_exceeded:Status::interface_unresolved;result.message="Prescribed interface family unresolved";return result;}
            const auto& outgoing=step.branch==Branch::reflected?interface.reflected:interface.transmitted;
            if(!outgoing){result.status=Status::branch_unavailable;result.message="Prescribed branch unavailable (for example transmission during total internal reflection)";return result;}
            segment.factor=factor(*interface.power,step.branch);
            // Preserve every point of both boxes. In particular, no midpoint,
            // origin displacement, source-surface skip or hidden epsilon.
            try{segment.outgoing=optical_bounds::spawn_ray(hit,*outgoing,0,1e6);}
            catch(const std::invalid_argument&){result.status=Status::numerical_failure;result.message="Continued ray exceeds the supported bounded-ray domain";return result;}
            totals.distance=nonnegative(totals.distance+hit.physical_distance);
            totals.optical_path_length=nonnegative(totals.optical_path_length+current*hit.physical_distance);
            totals.throughput=power(totals.throughput * *segment.factor);
            segment.accumulated=totals;ray=*segment.outgoing;
            if(step.branch==Branch::transmitted)current=step.next_index;
            ++result.completed_steps;
        }
        result.failed_step=result.completed_steps;result.status=Status::completed;
        result.completion=Completion{ray,current,totals};return result;
    }catch(const std::invalid_argument& e){result.status=Status::invalid_input;result.message=e.what();}
    catch(const std::exception& e){result.status=Status::numerical_failure;result.message=e.what();}
    // An allocation failure may still propagate if recording the diagnostic
    // cannot allocate; the input and every external object remain untouched.
    result.completion.reset();return result;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
