#include "pikapika/optical_geometry.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Optical geometry requires strict floating point, no fast-math or contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise, on, push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optical_geometry {
namespace {
using I=interval::Interval;using IV=Bounds3;
I p(double x){return I::point(x);}
IV exact(Vec3 a){return {p(a.x),p(a.y),p(a.z)};}
IV add(const IV& a,const IV& b){return {a[0]+b[0],a[1]+b[1],a[2]+b[2]};}
IV sub(const IV& a,const IV& b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
IV mul(const IV& a,const I& b){return {a[0]*b,a[1]*b,a[2]*b};}
IV divide(const IV& a,const I& b){return {a[0]/b,a[1]/b,a[2]/b};}
I dot(const IV& a,const IV& b){return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2];}
I norm2(const IV& a){return (interval::square(a[0])+interval::square(a[1]))+interval::square(a[2]);}
IV cross(const IV& a,const IV& b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
Vec3 plus(Vec3 a,Vec3 b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
Vec3 times(Vec3 a,double b){return {a.x*b,a.y*b,a.z*b};}
Vec3 minus(Vec3 a,Vec3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
bool finite(Vec3 a){return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z);}
double magnitude(Vec3 a){return std::hypot(a.x,a.y,a.z);}
Vec3 unit(Vec3 a){return times(a,1/magnitude(a));}
void position_valid(Vec3 a){if(!finite(a)||std::max({std::abs(a.x),std::abs(a.y),std::abs(a.z)})>1e6)throw std::invalid_argument("Optical position outside finite +/-1e6 metres");}
void direction_valid(Vec3 a){position_valid(a);if(std::max({std::abs(a.x),std::abs(a.y),std::abs(a.z)})<1e-6)throw std::invalid_argument("Optical direction/axis max component must be >=1e-6");}
void radius_valid(double r){if(!std::isfinite(r)||r<1e-6||r>1e6)throw std::invalid_argument("Optical radius/aperture must be in [1e-6,1e6] metres");}
void valid(const Ray& r,const Settings& s){
    interval::require_environment();position_valid(r.origin);direction_valid(r.direction);
    if(!std::isfinite(r.minimum_parameter)||!std::isfinite(r.maximum_parameter)||r.minimum_parameter<0||r.minimum_parameter>r.maximum_parameter||r.maximum_parameter>1e9)
        throw std::invalid_argument("Invalid closed optical ray parameter domain");
    if(!std::isfinite(s.parameter_tolerance)||s.parameter_tolerance<=0||s.parameter_tolerance>1e6||s.max_sqrt_refinements<1||s.max_sqrt_refinements>256)
        throw std::invalid_argument("Invalid optical geometry precision/refinement budget");
}
bool finite(const I& a){return std::isfinite(a.lower())&&std::isfinite(a.upper());}
I intersect_bounds(const I& a,const I& b){const auto value=interval::intersection(a,b);if(!value)throw std::logic_error("Inconsistent optical bounds");return *value;}
struct Work {
    const Ray& ray;const Settings& settings;Result result;
    // sqrt enclosure needs no assumption about libm sqrt's rounding. Invariant:
    // lo<=sqrt(x)<=hi for every real x in the input interval. Comparisons of
    // interval squares prove all refinements; an overlap uses the identity
    // |sqrt(x)-m|=|x-m^2|/(sqrt(x)+m), with denominator >= lo+m.
    I sqrt_bounds(const I& x){
        if(x.lower()<0||!finite(x))throw std::domain_error("Nonnegative finite optical square-root domain required");
        if(x.upper()==0)return p(0);
        double lo=0,hi=std::max(1.0,x.upper());
        for(unsigned j=0;j<settings.max_sqrt_refinements;++j){
            ++result.sqrt_refinements;
            const double mid=std::midpoint(lo,hi);
            if(mid==lo||mid==hi)return {lo,hi};
            const I m2=interval::square(p(mid));
            if(m2.upper()<x.lower())lo=mid;
            else if(m2.lower()>x.upper())hi=mid;
            else {
                const I delta=x-m2,denominator=p(lo)+p(mid);
                const double difference=std::max(std::abs(delta.lower()),std::abs(delta.upper()));
                if(denominator.strictly_positive()){
                    const double error=(I{0,difference}/denominator).upper();
                    if(std::isfinite(error))return intersect_bounds({lo,hi},intersect_bounds(p(mid)+I{-error,error},{0,hi}));
                }
                return {lo,hi};
            }
        }
        result.refinement_limited=true;return {lo,hi};
    }
    I magnitude_bounds(Vec3 v){
        const double a[3]{std::abs(v.x),std::abs(v.y),std::abs(v.z)};
        unsigned count=0;double single=0;for(double x:a)if(x!=0){++count;single=x;}
        if(count==1)return p(single); // exact one-axis Euclidean norm
        return sqrt_bounds(norm2(exact(v)));
    }
    IV axis_bounds(Vec3 a){
        unsigned count=0,index=0;const double values[3]{a.x,a.y,a.z};
        for(unsigned j=0;j<3;++j)if(values[j]!=0){++count;index=j;}
        if(count==1){IV n{p(0),p(0),p(0)};n[index]=p(values[index]>0?1:-1);return n;}
        const I length=magnitude_bounds(a);
        if(!length.strictly_positive())return {I{-1,1},I{-1,1},I{-1,1}};
        return divide(exact(a),length);
    }
    Reason uncertain_reason(Reason ordinary) const{return result.refinement_limited?Reason::refinement_budget:ordinary;}
    Result unresolved(Reason reason){result.status=Status::unresolved;result.reason=uncertain_reason(reason);result.nearest.reset();return result;}
    Result miss(Reason reason){result.status=Status::miss;result.reason=reason;return result;}
};
struct ShapeData {
    IV center,axis,aperture_center;Vec3 center_estimate{},plane_normal_estimate{};
    double sphere_radius{},aperture_radius{},signed_radius{};
    bool sphere{},cap{};
};
// Returns at the first accepted or unresolved root. Rejected earlier roots are
// retained so choosing the second sphere root never silently ignores a blocker.
Result select(Work& w,const ShapeData& s){
    const IV origin=exact(w.ray.origin),direction=exact(w.ray.direction);
    for(unsigned j=0;j<w.result.root_count;++j){
        auto& c=w.result.candidates[j];++w.result.considered_count;
        const I t=c.parameter;
        const auto unknown=[&](Reason reason){c.state=CandidateState::unresolved;c.reason=w.uncertain_reason(reason);return w.unresolved(reason);};
        if(t.upper()<w.ray.minimum_parameter||t.lower()>w.ray.maximum_parameter){c.state=CandidateState::rejected_parameter;continue;}
        if(t.lower()<w.ray.minimum_parameter||t.upper()>w.ray.maximum_parameter)return unknown(Reason::parameter_boundary);
        const IV point=add(origin,mul(direction,t));
        if(s.cap){
            const I hemisphere=dot(sub(point,s.center),mul(s.axis,p(s.signed_radius)));
            if(hemisphere.strictly_positive()){c.state=CandidateState::rejected_cap;continue;}
            if(!hemisphere.strictly_negative())return unknown(Reason::cap_boundary);
        }
        if(s.aperture_radius>0){
            // Disk points lie in its plane. Cap apertures are measured by
            // projection onto the plane perpendicular to its REAL unit axis.
            const IV offset=sub(point,s.aperture_center);
            const I radial=s.cap?norm2(cross(offset,s.axis)):norm2(offset);
            const I edge=radial-interval::square(p(s.aperture_radius));
            if(edge.strictly_positive()){c.state=CandidateState::rejected_aperture;continue;}
            if(!edge.strictly_negative())return unknown(Reason::aperture_boundary);
        }
        const I width=p(t.upper())-p(t.lower());
        if(!finite(t)||width.upper()>w.settings.parameter_tolerance)return unknown(Reason::precision_limit);
        const IV geometric=s.sphere?divide(sub(point,s.center),p(s.sphere_radius)):s.axis;
        const I incidence=dot(direction,geometric);
        if(!incidence.strictly_negative()&&!incidence.strictly_positive())return unknown(Reason::orientation);
        Hit hit;hit.parameter=t;hit.position=point;hit.geometric_normal=geometric;hit.front_face=incidence.strictly_negative();
        hit.incident_normal=hit.front_face?geometric:mul(geometric,p(-1));
        hit.parameter_estimate=std::midpoint(t.lower(),t.upper());
        hit.position_estimate=plus(w.ray.origin,times(w.ray.direction,hit.parameter_estimate));
        hit.geometric_normal_estimate=s.sphere?unit(minus(hit.position_estimate,s.center_estimate)):unit(s.plane_normal_estimate);
        hit.incident_normal_estimate=hit.front_face?hit.geometric_normal_estimate:times(hit.geometric_normal_estimate,-1);
        const I length=w.magnitude_bounds(w.ray.direction);
        hit.physical_distance=t*length;hit.physical_distance_estimate=hit.parameter_estimate*magnitude(w.ray.direction);
        if(!finite(hit.position_estimate)||!finite(hit.geometric_normal_estimate)||!finite(hit.incident_normal_estimate)||!finite(hit.physical_distance))return unknown(Reason::numerical_output);
        c.state=CandidateState::accepted;w.result.status=Status::hit;w.result.reason=Reason::none;w.result.nearest=hit;return w.result;
    }
    return w.miss(Reason::filtered_roots);
}
Result sphere(Work& w,const ShapeData& s){
    const IV offset=sub(exact(w.ray.origin),s.center),direction=exact(w.ray.direction);
    const I a=norm2(direction),h=dot(offset,direction),c=norm2(offset)-interval::square(p(s.sphere_radius));
    const I discriminant=interval::square(h)-a*c;w.result.discriminant=discriminant;
    if(discriminant.strictly_negative())return w.miss(Reason::no_real_roots);
    if(!discriminant.strictly_positive())return w.unresolved(Reason::tangent_or_discriminant);
    const I root=w.sqrt_bounds(discriminant);
    I low=p(0),high=p(0);
    if(h.strictly_negative()){
        const I q=-h+root;high=q/a;low=c/q;
    }else if(h.strictly_positive()){
        const I q=-h-root;low=q/a;high=c/q;
    }else{low=(-h-root)/a;high=(-h+root)/a;}
    w.result.root_count=2;w.result.candidates[0].parameter=low;w.result.candidates[1].parameter=high;
    return select(w,s);
}
}

Result intersect(const Ray& ray,const PlaneDisk& disk,const Settings& settings){
    valid(ray,settings);position_valid(disk.center);direction_valid(disk.normal);radius_valid(disk.aperture_radius);
    Work w{ray,settings,{}};
    const I denominator=dot(exact(ray.direction),exact(disk.normal));
    const I numerator=dot(sub(exact(disk.center),exact(ray.origin)),exact(disk.normal));
    if(denominator.contains_zero()){
        if(denominator.lower()==0&&denominator.upper()==0&&!numerator.contains_zero())return w.miss(Reason::parallel);
        return w.unresolved(Reason::parallel_or_coplanar);
    }
    w.result.root_count=1;w.result.candidates[0].parameter=numerator/denominator;
    const IV axis=w.axis_bounds(disk.normal);
    return select(w,{exact(disk.center),axis,exact(disk.center),disk.center,disk.normal,0,disk.aperture_radius,0,false,false});
}
Result intersect(const Ray& ray,const FullSphere& surface,const Settings& settings){
    valid(ray,settings);position_valid(surface.center);radius_valid(surface.radius);Work w{ray,settings,{}};
    return sphere(w,{exact(surface.center),exact({0,0,1}),exact(surface.center),surface.center,{},surface.radius,0,0,true,false});
}
Result intersect(const Ray& ray,const SphericalCap& cap,const Settings& settings){
    valid(ray,settings);position_valid(cap.vertex);direction_valid(cap.axis);radius_valid(std::abs(cap.signed_radius));radius_valid(cap.aperture_radius);
    if(cap.aperture_radius>std::abs(cap.signed_radius))throw std::invalid_argument("Cap aperture cannot exceed spherical radius");
    Work w{ray,settings,{}};const IV axis=w.axis_bounds(cap.axis),center=add(exact(cap.vertex),mul(axis,p(cap.signed_radius)));
    const Vec3 approximate_center=plus(cap.vertex,times(unit(cap.axis),cap.signed_radius));
    return sphere(w,{center,axis,exact(cap.vertex),approximate_center,{},std::abs(cap.signed_radius),cap.aperture_radius,cap.signed_radius,true,true});
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
