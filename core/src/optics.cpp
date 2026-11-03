#include "pikapika/optics.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Optics reference kernel requires strict floating point, no fast-math or contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise, on, push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optics {
namespace {
using interval::Interval;
using IVec=std::array<Interval,3>;
double dot(Vec3 a,Vec3 b) { return std::fma(a.x,b.x,std::fma(a.y,b.y,a.z*b.z)); }
Vec3 plus(Vec3 a,Vec3 b) { return {a.x+b.x,a.y+b.y,a.z+b.z}; }
Vec3 times(Vec3 a,double b) { return {a.x*b,a.y*b,a.z*b}; }
Vec3 cross(Vec3 a,Vec3 b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
double length(Vec3 a) { return std::hypot(a.x,a.y,a.z); }
bool finite(Vec3 a) { return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z); }
Vec3 unit(Vec3 a) { return times(a,1/length(a)); }
void validate_vector(Vec3 a) {
    if(!finite(a))throw std::invalid_argument("Optical direction/normal must be finite");
    const double scale=std::max({std::abs(a.x),std::abs(a.y),std::abs(a.z)});
    if(scale<1e-6||scale>1e6)throw std::invalid_argument("Optical vector scale must be in [1e-6,1e6]");
}
IVec exact(Vec3 a) { return {Interval::point(a.x),Interval::point(a.y),Interval::point(a.z)}; }
Interval dot(const IVec& a,const IVec& b) { return (a[0]*b[0]+a[1]*b[1])+a[2]*b[2]; }
Interval norm_squared(const IVec& a) { return (interval::square(a[0])+interval::square(a[1]))+interval::square(a[2]); }
IVec cross(const IVec& a,const IVec& b) {
    return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};
}
InterfaceResult uncertain(InterfaceResult result,Uncertainty why) {
    result.kind=InterfaceKind::uncertain;result.uncertainty=why;
    result.transmitted.reset();result.power.reset();result.cosine_transmitted.reset();
    return result;
}
bool probability(double value) { return std::isfinite(value)&&value>=0&&value<=1; }
double rounded_probability(double value) {
    constexpr double tolerance=32*std::numeric_limits<double>::epsilon();
    if(!std::isfinite(value)||value < -tolerance||value > 1+tolerance)
        return std::numeric_limits<double>::quiet_NaN();
    // This is a small ROUNDING clamp on approximate power outputs, never a
    // critical-angle sign test or a claimed interval enclosure.
    return std::clamp(value,0.0,1.0);
}
// Power T is evaluated from normal-flux conservation's explicit Fresnel form,
// NOT assigned as 1-R. This also avoids dividing by grazing incident cosine.
std::array<double,2> power_pair(double a,double b) {
    const double denominator=a+b;
    const double r=(a-b)/denominator;
    const double x=a/denominator,y=b/denominator;
    return {rounded_probability(r*r),rounded_probability(4*x*y)};
}
}

InterfaceResult dielectric_interface(const InterfaceInput& input) {
    interval::require_environment();
    validate_vector(input.incident);validate_vector(input.normal);
    const double ni=input.index_incident,nt=input.index_transmitted;
    if(!std::isfinite(ni)||!std::isfinite(nt)||ni<1e-6||ni>1e6||nt<1e-6||nt>1e6)
        throw std::invalid_argument("Optical real indices must be in [1e-6,1e6]");
    if(!std::isfinite(input.vacuum_wavelength_m)||input.vacuum_wavelength_m<=0)
        throw std::invalid_argument("Vacuum wavelength must be finite positive metres");

    const IVec i=exact(input.incident),n=exact(input.normal);
    const Interval nii=Interval::point(ni),nti=Interval::point(nt);
    InterfaceResult result;
    result.incident_dot=dot(i,n);
    // No normalized/scalar approximation is used to form this certificate.
    result.discriminant=interval::square(nti)*(norm_squared(i)*norm_squared(n))-
        interval::square(nii)*norm_squared(cross(i,n));
    result.vacuum_wavelength_m=input.vacuum_wavelength_m;
    result.incident_unit=unit(input.incident);result.normal_unit=unit(input.normal);
    const double cosine=-dot(result.incident_unit,result.normal_unit);
    result.cosine_incident=std::clamp(cosine,0.0,1.0);
    result.reflected=unit(plus(result.incident_unit,times(result.normal_unit,2*result.cosine_incident)));

    if(result.incident_dot.strictly_positive())
        throw std::invalid_argument("Normal must point into incident medium: incident dot normal <= 0");
    result.exact_grazing=result.incident_dot.lower()==0 && result.incident_dot.upper()==0;
    if(!result.incident_dot.strictly_negative()&&!result.exact_grazing)
        return uncertain(result,Uncertainty::incident_side);
    constexpr double tolerance=32*std::numeric_limits<double>::epsilon();
    if(!std::isfinite(cosine)||cosine < -tolerance||cosine > 1+tolerance||!finite(result.reflected))
        return uncertain(result,Uncertainty::numerical_output);
    // Input-derived exact equality, not a tolerance on refractive indices.
    // Orientation must be resolved first, even when media are homogeneous.
    if(ni==nt) {
        result.kind=InterfaceKind::transmission;
        result.transmitted=result.incident_unit;
        result.cosine_transmitted=result.cosine_incident;
        result.power=PowerSplit{0,1,0,1,0,1};
        return result;
    }
    if(result.discriminant.strictly_negative()) {
        result.kind=InterfaceKind::total_internal_reflection;
        result.power=PowerSplit{1,0,1,0,1,0};
        return result;
    }
    if(!result.discriminant.strictly_positive())return uncertain(result,Uncertainty::critical_angle);

    // All following values are ordinary double approximations. Near critical
    // incidence the classification can be certified while direction evaluation
    // is ill-conditioned. Fail explicitly if the scalar evaluation loses it.
    const double eta=ni/nt;
    const double sin_t=eta*length(cross(result.incident_unit,result.normal_unit));
    const double cos_t_squared=std::fma(-sin_t,sin_t,1.0);
    if(!(cos_t_squared>0)||!std::isfinite(cos_t_squared))return uncertain(result,Uncertainty::numerical_output);
    const double ct=std::sqrt(cos_t_squared),ci=result.cosine_incident;
    const Vec3 tangent=plus(result.incident_unit,times(result.normal_unit,ci));
    const Vec3 transmitted=unit(plus(times(tangent,eta),times(result.normal_unit,-ct)));
    if(!finite(transmitted))return uncertain(result,Uncertainty::numerical_output);
    const auto s=power_pair(ni*ci,nt*ct),p=power_pair(nt*ci,ni*ct);
    PowerSplit power{s[0],s[1],p[0],p[1],(s[0]+p[0])*0.5,(s[1]+p[1])*0.5};
    for(const double value:{power.reflectance_s,power.transmittance_s,power.reflectance_p,
        power.transmittance_p,power.reflectance_unpolarized,power.transmittance_unpolarized})
        if(!probability(value))return uncertain(result,Uncertainty::numerical_output);
    result.kind=InterfaceKind::transmission;result.transmitted=transmitted;
    result.cosine_transmitted=ct;result.power=power;
    return result;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
