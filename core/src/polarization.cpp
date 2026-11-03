#include "pikapika/polarization.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Polarization reference requires strict floating point, no fast-math or contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise, on, push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optics::polarization {
namespace {
constexpr double frame_tolerance=2e-12;
constexpr double rounding=64*std::numeric_limits<double>::epsilon();
double dot(Vec3 a,Vec3 b) { return (a.x*b.x+a.y*b.y)+a.z*b.z; }
Vec3 cross(Vec3 a,Vec3 b) { return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x}; }
Vec3 times(Vec3 a,double b) { return {a.x*b,a.y*b,a.z*b}; }
Vec3 minus(Vec3 a,Vec3 b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
double length(Vec3 a) { return std::hypot(a.x,a.y,a.z); }
bool finite(Vec3 a) { return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z); }
Vec3 unit(Vec3 a) { return times(a,1/length(a)); }
void validate_vector(Vec3 a) {
    const double m=std::max({std::abs(a.x),std::abs(a.y),std::abs(a.z)});
    if(!finite(a)||m<1e-6||m>1e6)throw std::invalid_argument("Polarization vector scale must be in [1e-6,1e6]");
}
void validate_frame(const Frame& f) {
    if(!finite(f.direction)||!finite(f.first)||!finite(f.second)||
       std::abs(length(f.direction)-1)>frame_tolerance||std::abs(length(f.first)-1)>frame_tolerance||
       std::abs(length(f.second)-1)>frame_tolerance||std::abs(dot(f.direction,f.first))>frame_tolerance||
       std::abs(dot(f.direction,f.second))>frame_tolerance||std::abs(dot(f.first,f.second))>frame_tolerance||
       length(minus(cross(f.first,f.second),f.direction))>frame_tolerance)
        throw std::invalid_argument("Polarization frame must be right-handed orthonormal");
}
bool exact_collinear(Vec3 a,Vec3 b) {
    using interval::Interval;
    const std::array<Interval,3> x{Interval::point(a.x),Interval::point(a.y),Interval::point(a.z)};
    const std::array<Interval,3> y{Interval::point(b.x),Interval::point(b.y),Interval::point(b.z)};
    const std::array<Interval,3> c{x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]};
    for(const auto& v:c)if(v.lower()!=0||v.upper()!=0)return false;
    return true;
}
bool finite(std::complex<double> a) { return std::isfinite(a.real())&&std::isfinite(a.imag()); }
// Keep exponent range through coherency products: a tiny amplitude squared may
// underflow binary64 even though multiplication by incident power is normal.
// This is extended RANGE with ordinary-double significands, not an interval,
// arbitrary precision, or a correctly-rounded dot-product implementation.
struct Scaled { double fraction{};int exponent{}; };
Scaled normalize(double fraction,int exponent=0) {
    if(fraction==0)return {};
    int shift=0;const double f=std::frexp(fraction,&shift);return {f,exponent+shift};
}
Scaled multiply(Scaled a,Scaled b) { return normalize(a.fraction*b.fraction,a.exponent+b.exponent); }
Scaled add(Scaled a,Scaled b) {
    if(a.fraction==0)return b;if(b.fraction==0)return a;
    if(a.exponent<b.exponent)std::swap(a,b);
    return normalize(a.fraction+std::ldexp(b.fraction,b.exponent-a.exponent),a.exponent);
}
Scaled negative(Scaled a) { a.fraction=-a.fraction;return a; }
template<std::size_t N> Scaled sum(std::array<Scaled,N> terms) {
    // Cancel larger terms before adding smaller ones. Cancellation still has
    // the normal finite-significand conditioning limits documented for this API.
    std::sort(terms.begin(),terms.end(),[](Scaled a,Scaled b){return a.exponent>b.exponent;});
    Scaled result;for(const auto& t:terms)result=add(result,t);return result;
}
Scaled product(double a,double b,Scaled c) { return multiply(multiply(normalize(a),normalize(b)),c); }
double rounded(Scaled a) { return std::ldexp(a.fraction,a.exponent); }
}

void validate(const Stokes& s) {
    interval::require_environment();
    if(!std::isfinite(s.i)||!std::isfinite(s.q)||!std::isfinite(s.u)||!std::isfinite(s.v)||s.i<0||s.i>1e100)
        throw std::invalid_argument("Stokes components must be finite; power in [0,1e100]");
    if(s.i==0) {
        if(s.q!=0||s.u!=0||s.v!=0)throw std::invalid_argument("Zero power must have zero polarization");
    } else if(std::hypot(s.q/s.i,s.u/s.i,s.v/s.i)>1+rounding) {
        throw std::invalid_argument("Stokes state lies outside physical polarization cone");
    }
}
Frame make_frame(Vec3 direction,Vec3 reference) {
    interval::require_environment();validate_vector(direction);validate_vector(reference);
    const Vec3 d=unit(direction),r=unit(reference);
    const Vec3 transverse=minus(r,times(d,dot(r,d)));
    if(length(transverse)<1e-8)throw std::invalid_argument("Transverse reference is too parallel to ray");
    const Vec3 second=unit(cross(d,transverse)),first=unit(cross(second,d));
    const Frame f{d,first,second};validate_frame(f);return f;
}
Stokes reexpress(const Stokes& value,const Frame& from,const Frame& to) {
    validate(value);validate_frame(from);validate_frame(to);
    if(length(minus(from.direction,to.direction))>frame_tolerance)
        throw std::invalid_argument("Cannot rotate Stokes basis between different propagation directions");
    double c=dot(to.first,from.first),s=dot(to.first,from.second);
    const double h=std::hypot(c,s);c/=h;s/=h;
    const double c2=c*c-s*s,s2=2*c*s;
    const Stokes result{value.i,c2*value.q+s2*value.u,-s2*value.q+c2*value.u,value.v};
    validate(result);return result;
}
Stokes diagonal_jones(const Stokes& value,std::complex<double> a,std::complex<double> b) {
    validate(value);
    if(!finite(a)||!finite(b)||std::abs(a)>1+rounding||std::abs(b)>1+rounding)
        throw std::invalid_argument("Jones diagonal must be finite passive amplitudes");
    const Scaled xx=multiply(add(normalize(value.i),normalize(value.q)),normalize(.5));
    const Scaled yy=multiply(add(normalize(value.i),negative(normalize(value.q))),normalize(.5));
    const Scaled out_xx=sum(std::array{product(a.real(),a.real(),xx),product(a.imag(),a.imag(),xx)});
    const Scaled out_yy=sum(std::array{product(b.real(),b.real(),yy),product(b.imag(),b.imag(),yy)});
    const Scaled u=normalize(value.u),v=normalize(value.v);
    const Scaled out_u=sum(std::array{product(a.real(),b.real(),u),product(a.imag(),b.imag(),u),
        negative(product(a.imag(),b.real(),v)),product(a.real(),b.imag(),v)});
    const Scaled out_v=sum(std::array{product(a.imag(),b.real(),u),negative(product(a.real(),b.imag(),u)),
        product(a.real(),b.real(),v),product(a.imag(),b.imag(),v)});
    const Stokes result{rounded(add(out_xx,out_yy)),rounded(add(out_xx,negative(out_yy))),rounded(out_u),rounded(out_v)};
    validate(result);return result;
}
Split dielectric_split(const InterfaceInput& input,Vec3 reference,const Stokes& power) {
    validate(power);
    Split result;result.input_frame=make_frame(input.incident,reference);
    result.interface=dielectric_interface(input);
    const auto& boundary=result.interface;
    if(boundary.kind==InterfaceKind::uncertain) { result.failure=Failure::interface_uncertain;return result; }
    const Vec3 transverse=cross(boundary.normal_unit,boundary.incident_unit);
    Vec3 s;
    if(length(transverse)>=1e-8)s=unit(transverse);
    else if(input.index_incident==input.index_transmitted||exact_collinear(input.normal,input.incident))s=result.input_frame.first;
    else { result.failure=Failure::incidence_plane_uncertain;return result; }
    const Frame local=make_frame(boundary.incident_unit,s);
    const Stokes incident=reexpress(power,result.input_frame,local);
    const double ni=input.index_incident,nt=input.index_transmitted,ci=boundary.cosine_incident;
    std::complex<double> rs,rp,ts,tp;
    if(ni==nt) { rs=rp=0;ts=tp=1; }
    else if(boundary.kind==InterfaceKind::transmission) {
        const double ct=*boundary.cosine_transmitted;
        rs=(ni*ci-nt*ct)/(ni*ci+nt*ct);
        rp=(nt*ci-ni*ct)/(nt*ci+ni*ct);
        ts=std::sqrt(boundary.power->transmittance_s);tp=std::sqrt(boundary.power->transmittance_p);
    } else {
        const double sin_t=(ni/nt)*length(transverse);
        const double k2=std::fma(sin_t,sin_t,-1.0);
        if(!(k2>0)||!std::isfinite(k2)) { result.failure=Failure::numerical_output;return result; }
        const double k=std::sqrt(k2);
        // e^(i k.x-i wt), transmitted decay selects cos(theta_t)=+i*k.
        rs=std::complex<double>(ni*ci,-nt*k)/std::complex<double>(ni*ci,nt*k);
        rp=std::complex<double>(nt*ci,-ni*k)/std::complex<double>(nt*ci,ni*k);
    }
    if(!finite(rs)||!finite(rp)||!finite(ts)||!finite(tp)) { result.failure=Failure::numerical_output;return result; }
    try {
        result.reflected=Branch{make_frame(boundary.reflected,s),diagonal_jones(incident,rs,rp),rs,rp};
        if(boundary.transmitted)
            result.transmitted=Branch{make_frame(*boundary.transmitted,s),diagonal_jones(incident,ts,tp),ts,tp};
    } catch(const std::invalid_argument&) {
        result.reflected.reset();result.transmitted.reset();result.failure=Failure::numerical_output;
    }
    return result;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
