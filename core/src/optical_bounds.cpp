#include "pikapika/optical_bounds.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Bounded optics requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise, on, push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optical_bounds {
namespace {
using I=Interval;using V=Bounds3;
I p(double a){return I::point(a);}
V add(const V& a,const V& b){return {a[0]+b[0],a[1]+b[1],a[2]+b[2]};}
V sub(const V& a,const V& b){return {a[0]-b[0],a[1]-b[1],a[2]-b[2]};}
V mul(const V& a,I b){return {a[0]*b,a[1]*b,a[2]*b};}
V div(const V& a,I b){return {a[0]/b,a[1]/b,a[2]/b};}
I dot(const V& a,const V& b){return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2];}
I norm2(const V& a){return (interval::square(a[0])+interval::square(a[1]))+interval::square(a[2]);}
V cross(const V& a,const V& b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
bool finite(I a){return std::isfinite(a.lower())&&std::isfinite(a.upper());}
double largest(I a){return std::max(std::abs(a.lower()),std::abs(a.upper()));}
bool zero(I a){return a.lower()==0&&a.upper()==0;}
I meet(I a,I b){const auto r=interval::intersection(a,b);if(!r)throw std::logic_error("Inconsistent bounded optical enclosure");return *r;}
I unit_range(I a){return meet(a,I(-1,1));}
V unit_range(V a){for(auto& v:a)v=unit_range(v);return a;}
I positive_range(I a){return meet(a,I(0,std::max(0.0,a.upper())));}
I power_range(I a){return meet(a,I(0,1));}
void vector_valid(const V& a){for(I x:a)if(!finite(x)||largest(x)>1e6)throw std::invalid_argument("Optical vector endpoints must be finite within +/-1e6");}
void position_valid(Vec3 a){vector_valid(enclose(a));}
void axis_valid(Vec3 a){position_valid(a);if(std::max({std::abs(a.x),std::abs(a.y),std::abs(a.z)})<1e-6)throw std::invalid_argument("Optical axis max component must be >=1e-6");}
void radius_valid(double r){if(!std::isfinite(r)||r<1e-6||r>1e6)throw std::invalid_argument("Optical radius/aperture outside [1e-6,1e6]");}
void settings_valid(const Settings& s){
    interval::require_environment();
    if(!std::isfinite(s.maximum_parameter_width)||s.maximum_parameter_width<=0||s.maximum_parameter_width>1e6||s.max_sqrt_refinements<1||s.max_sqrt_refinements>256)throw std::invalid_argument("Invalid bounded optical precision/budget");
}
void valid(const BoundedRay& ray,const Settings& s){
    settings_valid(s);vector_valid(ray.origin);vector_valid(ray.direction);
    if(!std::isfinite(ray.minimum_parameter)||!std::isfinite(ray.maximum_parameter)||ray.minimum_parameter<0||ray.maximum_parameter<ray.minimum_parameter||ray.maximum_parameter>1e9)throw std::invalid_argument("Invalid bounded ray closed parameter domain");
}
struct Work {
    const Settings& settings;
    unsigned refinements{};bool limited{};
    // Endpoint monotonicity plus an independently proved scalar sqrt bracket.
    // No libm sqrt or rounded midpoint is assumed exact.
    I scalar_sqrt(double x){
        if(x==0||x==1)return p(x);
        double lo=0,hi=std::max(1.0,x);const I target=p(x);
        for(unsigned j=0;j<settings.max_sqrt_refinements;++j){
            ++refinements;const double m=std::midpoint(lo,hi);
            if(m==lo||m==hi)return {lo,hi};
            const I m2=interval::square(p(m));
            if(m2.upper()<x)lo=m;
            else if(m2.lower()>x)hi=m;
            else{
                const I delta=target-m2,denominator=p(lo)+p(m);
                if(denominator.strictly_positive()){
                    const double difference=std::max(std::abs(delta.lower()),std::abs(delta.upper()));
                    const double e=(I(0,difference)/denominator).upper();
                    if(std::isfinite(e))return meet(I(lo,hi),meet(p(m)+I(-e,e),I(0,hi)));
                }
                return {lo,hi};
            }
        }
        limited=true;return {lo,hi};
    }
    I sqrt(I x){
        if(!finite(x)||x.lower()<0)throw std::domain_error("Bounded optical sqrt needs finite nonnegative domain");
        const I a=scalar_sqrt(x.lower());
        if(x.lower()==x.upper())return a;
        const I b=scalar_sqrt(x.upper());return {a.lower(),b.upper()};
    }
    I norm(const V& v){
        unsigned count=0,index=0;for(unsigned k=0;k<3;++k)if(!zero(v[k])){++count;index=k;}
        if(count==1){
            const I a=v[index];
            if(a.lower()>=0)return a;
            if(a.upper()<=0)return -a;
            return {0,largest(a)};
        }
        return sqrt(positive_range(norm2(v)));
    }
    std::optional<V> normalized(const V& v){
        unsigned count=0,index=0;for(unsigned k=0;k<3;++k)if(!zero(v[k])){++count;index=k;}
        if(count==1&&(v[index].strictly_positive()||v[index].strictly_negative())){
            V r{p(0),p(0),p(0)};r[index]=p(v[index].strictly_positive()?1:-1);return r;
        }
        const I n=norm(v);if(!n.strictly_positive())return std::nullopt;
        return unit_range(div(v,n));
    }
    Reason why(Reason ordinary)const{return limited?Reason::refinement_budget:ordinary;}
};
struct Shape {
    V center,axis,aperture_center;
    double radius{},aperture{},signed_radius{};bool sphere{},cap{};
};
void diagnostics(Result& r,const Work& w){r.sqrt_refinements=w.refinements;r.refinement_limited=w.limited;}
Result unknown(Result r,Work& w,Reason reason){r.status=Status::unresolved;r.reason=w.why(reason);r.nearest.reset();diagnostics(r,w);return r;}
Result miss(Result r,Work& w,Reason reason){r.status=Status::miss;r.reason=reason;r.nearest.reset();diagnostics(r,w);return r;}
Result select(const BoundedRay& ray,const Shape& s,Result r,Work& w){
    for(unsigned j=0;j<r.root_count;++j){
        auto& c=r.candidates[j];++r.considered_count;const I t=c.parameter;
        const auto unresolved=[&](Reason reason){c.state=CandidateState::unresolved;c.reason=w.why(reason);return unknown(r,w,reason);};
        if(t.upper()<ray.minimum_parameter||t.lower()>ray.maximum_parameter){c.state=CandidateState::rejected_parameter;continue;}
        if(t.lower()<ray.minimum_parameter||t.upper()>ray.maximum_parameter)return unresolved(Reason::parameter_boundary);
        V position=add(ray.origin,mul(ray.direction,t));
        if(!s.sphere){
            // Every actual root satisfies the plane equation. Contract a box
            // coordinate using that exact constraint, never project a midpoint.
            // Even with interval normalized axes this remains an inclusion.
            for(unsigned k=0;k<3;++k)if(!s.axis[k].contains_zero()){
                I sum=p(0);for(unsigned i=0;i<3;++i)if(i!=k)sum=sum+s.axis[i]*(position[i]-s.center[i]);
                position[k]=meet(position[k],s.center[k]-sum/s.axis[k]);
            }
        }
        if(s.cap){
            const I hemisphere=dot(sub(position,s.center),mul(s.axis,p(s.signed_radius)));
            if(hemisphere.strictly_positive()){c.state=CandidateState::rejected_cap;continue;}
            if(!hemisphere.strictly_negative())return unresolved(Reason::cap_boundary);
        }
        if(s.aperture>0){
            const V offset=sub(position,s.aperture_center);
            const I radial=norm2(cross(offset,s.axis));
            const I edge=radial-interval::square(p(s.aperture));
            if(edge.strictly_positive()){c.state=CandidateState::rejected_aperture;continue;}
            if(!edge.strictly_negative())return unresolved(Reason::aperture_boundary);
        }
        if(!finite(t)||(p(t.upper())-p(t.lower())).upper()>w.settings.maximum_parameter_width)return unresolved(Reason::precision_limit);
        const V normal=s.sphere?unit_range(div(sub(position,s.center),p(s.radius))):s.axis;
        const I facing=dot(ray.direction,normal);
        if(!facing.strictly_negative()&&!facing.strictly_positive())return unresolved(Reason::orientation);
        Hit hit;hit.parameter=t;hit.position=position;hit.geometric_normal=normal;hit.front_face=facing.strictly_negative();
        hit.incident_normal=hit.front_face?normal:mul(normal,p(-1));hit.physical_distance=t*w.norm(ray.direction);
        if(!finite(hit.physical_distance))return unresolved(Reason::numerical_domain);
        c.state=CandidateState::accepted;r.status=Status::hit;r.reason=Reason::none;r.nearest=hit;diagnostics(r,w);return r;
    }
    return miss(r,w,Reason::none);
}
Result sphere(const BoundedRay& ray,const Shape& s,Work& w){
    Result r;const V offset=sub(ray.origin,s.center);
    const I a=norm2(ray.direction);if(!a.strictly_positive())return unknown(r,w,Reason::zero_direction);
    const I h=dot(offset,ray.direction),c=norm2(offset)-interval::square(p(s.radius));
    const I discriminant=interval::square(h)-a*c;r.discriminant=discriminant;
    if(discriminant.strictly_negative())return miss(r,w,Reason::no_real_roots);
    if(!discriminant.strictly_positive())return unknown(r,w,Reason::tangent_or_discriminant);
    const I root=w.sqrt(discriminant);I low=p(0),high=p(0);
    if(h.strictly_negative()){const I q=-h+root;high=q/a;low=c/q;}
    else if(h.strictly_positive()){const I q=-h-root;low=q/a;high=c/q;}
    else{low=(-h-root)/a;high=(-h+root)/a;}
    r.root_count=2;r.candidates[0].parameter=low;r.candidates[1].parameter=high;
    return select(ray,s,r,w);
}
}
Bounds3 enclose(Vec3 v){return {p(v.x),p(v.y),p(v.z)};}
BoundedRay enclose_ray(const optical_geometry::Ray& r){return {enclose(r.origin),enclose(r.direction),r.minimum_parameter,r.maximum_parameter};}
BoundedRay spawn_ray(const Hit& h,const Bounds3& outgoing,double lo,double hi){
    BoundedRay r{h.position,outgoing,lo,hi};valid(r,{});return r;
}
Result intersect(const BoundedRay& ray,const optical_geometry::PlaneDisk& disk,const Settings& settings){
    valid(ray,settings);position_valid(disk.center);axis_valid(disk.normal);radius_valid(disk.aperture_radius);
    Work w{settings};Result r;
    if(!norm2(ray.direction).strictly_positive())return unknown(r,w,Reason::zero_direction);
    const V raw_normal=enclose(disk.normal),center=enclose(disk.center);
    const I denominator=dot(ray.direction,raw_normal),numerator=dot(sub(center,ray.origin),raw_normal);
    if(denominator.contains_zero()){
        if(zero(denominator)&&!numerator.contains_zero())return miss(r,w,Reason::none);
        return unknown(r,w,Reason::parallel_or_coplanar);
    }
    const auto normal=w.normalized(raw_normal);if(!normal)return unknown(r,w,Reason::zero_normal);
    r.root_count=1;r.candidates[0].parameter=numerator/denominator;
    return select(ray,{center,*normal,center,0,disk.aperture_radius,0,false,false},r,w);
}
Result intersect(const BoundedRay& ray,const optical_geometry::FullSphere& surface,const Settings& settings){
    valid(ray,settings);position_valid(surface.center);radius_valid(surface.radius);Work w{settings};
    const V center=enclose(surface.center);return sphere(ray,{center,enclose({0,0,1}),center,surface.radius,0,0,true,false},w);
}
Result intersect(const BoundedRay& ray,const optical_geometry::SphericalCap& cap,const Settings& settings){
    valid(ray,settings);position_valid(cap.vertex);axis_valid(cap.axis);radius_valid(std::abs(cap.signed_radius));radius_valid(cap.aperture_radius);
    if(cap.aperture_radius>std::abs(cap.signed_radius))throw std::invalid_argument("Cap aperture cannot exceed radius");
    Work w{settings};Result r;const auto axis=w.normalized(enclose(cap.axis));
    if(!axis)return unknown(r,w,Reason::zero_normal);
    const V vertex=enclose(cap.vertex),center=add(vertex,mul(*axis,p(cap.signed_radius)));
    return sphere(ray,{center,*axis,vertex,std::abs(cap.signed_radius),cap.aperture_radius,cap.signed_radius,true,true},w);
}
InterfaceResult dielectric_interface(const InterfaceInput& input,const Settings& settings){
    return dielectric_interface_bounds({input.incident,input.normal,p(input.index_incident),p(input.index_transmitted),input.vacuum_wavelength_m},settings);
}
InterfaceResult dielectric_interface_bounds(const IndexBoundsInterfaceInput& input,const Settings& settings){
    settings_valid(settings);vector_valid(input.incident);vector_valid(input.normal);
    const auto index_valid=[](I n){return finite(n)&&n.lower()>=1e-6&&n.upper()<=1e6;};
    if(!index_valid(input.index_incident)||!index_valid(input.index_transmitted)||!std::isfinite(input.vacuum_wavelength_m)||input.vacuum_wavelength_m<=0)throw std::invalid_argument("Invalid bounded dielectric indices/wavelength");
    Work w{settings};InterfaceResult r;r.vacuum_wavelength_m=input.vacuum_wavelength_m;
    const auto done=[&](){r.sqrt_refinements=w.refinements;r.refinement_limited=w.limited;return r;};
    const auto unresolved=[&](Reason reason){r.kind=InterfaceKind::unresolved;r.reason=w.why(reason);r.reflected.reset();r.transmitted.reset();r.power.reset();return done();};
    const I a=norm2(input.incident),b=norm2(input.normal);
    if(!a.strictly_positive())return unresolved(Reason::zero_direction);
    if(!b.strictly_positive())return unresolved(Reason::zero_normal);
    r.incident_dot=dot(input.incident,input.normal);
    if(r.incident_dot.strictly_positive())throw std::invalid_argument("Bounded optical normal points away from incident medium");
    r.exact_grazing=zero(r.incident_dot);
    if(!r.incident_dot.strictly_negative()&&!r.exact_grazing)return unresolved(Reason::incident_side);
    r.incident_unit=w.normalized(input.incident);r.normal_unit=w.normalized(input.normal);
    if(!r.incident_unit)return unresolved(Reason::zero_direction);
    if(!r.normal_unit)return unresolved(Reason::zero_normal);
    const I denominator=w.sqrt(positive_range(a*b));
    if(!denominator.strictly_positive())return unresolved(Reason::zero_normal);
    const I cross2=norm2(cross(input.incident,input.normal));
    const I sine2=meet(cross2/(a*b),I(0,1));
    // Intersect two independently valid expressions. The cross-product form
    // preserves exactly axial families whose raw vector lengths vary widely.
    const I ci=meet(meet(-r.incident_dot/denominator,I(0,1)),w.sqrt(meet(p(1)-sine2,I(0,1))));r.cosine_incident=ci;
    const V reflected=unit_range(add(*r.incident_unit,mul(*r.normal_unit,p(2)*ci)));
    const I ni=input.index_incident,nt=input.index_transmitted,ni2=interval::square(ni),nt2=interval::square(nt);
    r.discriminant=nt2*a*b-ni2*cross2;
    if(ni.lower()==ni.upper()&&nt.lower()==nt.upper()&&ni.lower()==nt.lower()){
        r.kind=InterfaceKind::transmission;r.reflected=reflected;r.transmitted=r.incident_unit;r.cosine_transmitted=ci;
        Power power;power.transmittance_s=power.transmittance_p=power.transmittance_unpolarized=p(1);r.power=power;return done();
    }
    if(r.discriminant->strictly_negative()){
        r.kind=InterfaceKind::total_internal_reflection;r.reflected=reflected;
        Power power;power.reflectance_s=power.reflectance_p=power.reflectance_unpolarized=p(1);r.power=power;return done();
    }
    if(!r.discriminant->strictly_positive())return unresolved(Reason::critical_angle);
    const I cos2=meet(meet(*r.discriminant/(nt2*a*b),p(1)-(ni2/nt2)*sine2),I(0,1)),ct=w.sqrt(cos2),eta=ni/nt;
    const I ds=ni*ci+nt*ct,dp=nt*ci+ni*ct;
    if(!ds.strictly_positive()||!dp.strictly_positive())return unresolved(Reason::numerical_domain);
    const I rs=(ni*ci-nt*ct)/ds,rp=(nt*ci-ni*ct)/dp;
    Power power;power.reflectance_s=power_range(interval::square(rs));power.reflectance_p=power_range(interval::square(rp));
    const I flux=p(4)*ni*nt*ci*ct;
    power.transmittance_s=power_range(flux/interval::square(ds));power.transmittance_p=power_range(flux/interval::square(dp));
    power.reflectance_unpolarized=power_range((power.reflectance_s+power.reflectance_p)*p(.5));
    power.transmittance_unpolarized=power_range((power.transmittance_s+power.transmittance_p)*p(.5));
    r.kind=InterfaceKind::transmission;r.reflected=reflected;r.transmitted=unit_range(add(mul(*r.incident_unit,eta),mul(*r.normal_unit,eta*ci-ct)));
    r.cosine_transmitted=ct;r.power=power;return done();
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
