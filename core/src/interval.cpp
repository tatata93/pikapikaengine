#include "pikapika/interval.hpp"
#include <algorithm>
#include <array>
#include <cfenv>
#include <cfloat>
#include <cmath>
#include <limits>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Interval arithmetic requires strict floating point, no fast-math or contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise, on, push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#define PIKA_INTERVAL_NOINLINE __declspec(noinline)
#elif defined(__clang__) || defined(__GNUC__)
#define PIKA_INTERVAL_NOINLINE __attribute__((noinline))
#if defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif
#else
#define PIKA_INTERVAL_NOINLINE
#endif

#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#define PIKA_INTERVAL_X64 1
#endif

namespace pikapika::interval {
namespace {
using Limits = std::numeric_limits<double>;
constexpr double inf = Limits::infinity();
static_assert(sizeof(double)==8 && Limits::is_iec559 && Limits::radix==2 &&
    Limits::digits==53 && Limits::min_exponent==-1021 && Limits::max_exponent==1024 &&
    Limits::has_denorm==std::denorm_present && FLT_EVAL_METHOD==0,
    "Interval arithmetic requires binary64 with binary64 expression evaluation.");

// Each isolated operation is stored as binary64 before nextafter. No expression
// here contains a multiply AND an add; no FMA is needed or permitted by the build.
PIKA_INTERVAL_NOINLINE double raw_add(double a,double b) { volatile double r=a+b; return r; }
PIKA_INTERVAL_NOINLINE double raw_sub(double a,double b) { volatile double r=a-b; return r; }
PIKA_INTERVAL_NOINLINE double raw_mul(double a,double b) { volatile double r=a*b; return r; }
PIKA_INTERVAL_NOINLINE double raw_div(double a,double b) { volatile double r=a/b; return r; }
double down(double rounded) {
    if(std::isnan(rounded))throw std::runtime_error("NaN in interval endpoint operation");
    return std::nextafter(rounded,-inf);
}
double up(double rounded) {
    if(std::isnan(rounded))throw std::runtime_error("NaN in interval endpoint operation");
    return std::nextafter(rounded,inf);
}
bool zero(const Interval& a) { return a.lower()==0 && a.upper()==0; }
struct Bounds { double lower,upper; };
Bounds product(double a,double b) {
    // Endpoint infinity denotes an unbounded limit of finite reals. Thus 0*inf
    // as a bound is zero, rather than IEEE's indeterminate scalar expression.
    if(a==0 || b==0)return {0,0};
    if(std::isinf(a) || std::isinf(b)) {
        const double result=std::signbit(a)!=std::signbit(b)?-inf:inf;
        return {result,result};
    }
    const double r=raw_mul(a,b);
    return {down(r),up(r)};
}
double reciprocal_down(double a) { return std::isinf(a)?std::copysign(0.0,a):down(raw_div(1,a)); }
double reciprocal_up(double a) { return std::isinf(a)?std::copysign(0.0,a):up(raw_div(1,a)); }
}

Interval::Interval(double lower,double upper):lower_(lower),upper_(upper) {
    // DAZ can change even comparisons with zero; reject before validation or
    // signed-zero canonicalization could accidentally erase a subnormal input.
    require_environment();
    if(std::isnan(lower)||std::isnan(upper)||lower>upper||lower==inf||upper==-inf)
        throw std::invalid_argument("Interval needs ordered nonempty finite-real bounds");
    // Both signs denote the same real zero. Canonical bounds simplify output.
    if(lower_==0)lower_=-0.0;
    if(upper_==0)upper_=0.0;
}
Interval Interval::point(double value) {
    if(!std::isfinite(value))throw std::invalid_argument("Interval point must be finite");
    return {value,value};
}
Interval Interval::whole() { return {-inf,inf}; }
bool Interval::contains(double value) const noexcept { return std::isfinite(value)&&lower_<=value&&value<=upper_; }
bool Interval::contains(const Interval& other) const noexcept { return lower_<=other.lower_&&other.upper_<=upper_; }
bool Interval::contains_zero() const noexcept { return lower_<=0 && upper_>=0; }
Sign sign(const Interval& a) noexcept {
    if(a.strictly_positive())return Sign::positive;
    if(a.strictly_negative())return Sign::negative;
    if(a.lower()==0 && a.upper()==0)return Sign::zero;
    if(a.lower()==0)return Sign::nonnegative;
    if(a.upper()==0)return Sign::nonpositive;
    return Sign::mixed;
}
std::optional<Interval> intersection(const Interval& a,const Interval& b) {
    require_environment();
    const double lo=std::max(a.lower(),b.lower()),hi=std::min(a.upper(),b.upper());
    if(lo>hi)return std::nullopt;
    return Interval{lo,hi};
}
Interval hull(const Interval& a,const Interval& b) {
    require_environment();
    return {std::min(a.lower(),b.lower()),std::max(a.upper(),b.upper())};
}

const char* environment_issue() noexcept {
#if defined(PIKA_INTERVAL_X64)
    // SSE exception masks 7..12 must all be set. FTZ bit15 and DAZ bit6 must be
    // clear. Reject BEFORE probes which could otherwise trap or flush values.
    const unsigned control=_mm_getcsr();
    if((control&0x1f80u)!=0x1f80u)return "floating-point exceptions must be masked";
    if(control&0x8040u)return "FTZ/DAZ must be disabled (gradual underflow required)";
    if(control&0x6000u)return "SSE round-to-nearest ties-to-even required";
#elif !defined(__wasm__)
    return "unvalidated target: this kernel supports x64 SSE2 and WebAssembly";
#endif
    if(std::fegetround()!=FE_TONEAREST)return "round-to-nearest ties-to-even required";
    const double tiny=Limits::denorm_min(),normal=Limits::min(),maximum=Limits::max();
    if(raw_mul(tiny,1)!=tiny || raw_add(tiny,tiny)!=std::nextafter(tiny,inf) ||
       raw_mul(normal,0.5)!=0x1p-1023 || raw_div(normal,2)!=0x1p-1023)
        return "subnormal input/output probes failed";
    if(raw_add(1,0x1p-53)!=1 || raw_sub(1,0x1p-54)!=1)
        return "binary64 nearest-even arithmetic probes failed";
    if(std::nextafter(0.0,inf)!=tiny || std::nextafter(0.0,-inf)!=-tiny ||
       std::nextafter(tiny,0.0)!=0 || std::nextafter(-tiny,0.0)!=0 ||
       std::nextafter(1.0,inf)!=0x1.0000000000001p0 ||
       std::nextafter(1.0,-inf)!=0x1.fffffffffffffp-1 ||
       std::nextafter(inf,0.0)!=maximum || std::nextafter(-inf,0.0)!=-maximum ||
       std::nextafter(maximum,inf)!=inf)
        return "nextafter adjacent-value probes failed";
    return nullptr;
}
void require_environment() {
    if(const char* issue=environment_issue())throw std::runtime_error(issue);
}
Interval negate(const Interval& a) {
    require_environment();
    return {-a.upper(),-a.lower()};
}
Interval add(const Interval& a,const Interval& b) {
    require_environment();
    if(zero(a))return b;
    if(zero(b))return a;
    const double lo=a.lower()==-inf||b.lower()==-inf?-inf:down(raw_add(a.lower(),b.lower()));
    const double hi=a.upper()==inf||b.upper()==inf?inf:up(raw_add(a.upper(),b.upper()));
    return {lo,hi};
}
Interval sub(const Interval& a,const Interval& b) {
    require_environment();
    if(zero(b))return a;
    const double lo=a.lower()==-inf||b.upper()==inf?-inf:down(raw_sub(a.lower(),b.upper()));
    const double hi=a.upper()==inf||b.lower()==-inf?inf:up(raw_sub(a.upper(),b.lower()));
    return {lo,hi};
}
Interval mul(const Interval& a,const Interval& b) {
    require_environment();
    const std::array<Bounds,4> corners{product(a.lower(),b.lower()),product(a.lower(),b.upper()),
        product(a.upper(),b.lower()),product(a.upper(),b.upper())};
    double lo=inf,hi=-inf;
    for(const Bounds& p:corners) { lo=std::min(lo,p.lower);hi=std::max(hi,p.upper); }
    return {lo,hi};
}
Interval divide(const Interval& a,const Interval& b) {
    require_environment();
    if(b.contains_zero())throw std::domain_error("Interval division denominator contains zero");
    if(zero(a))return Interval::point(0);
    // Two inclusion steps, not direct quotient rounding: enclose reciprocal,
    // then enclose the product. May be wider than a correctly directed quotient.
    const Interval reciprocal{reciprocal_down(b.upper()),reciprocal_up(b.lower())};
    return mul(a,reciprocal);
}
Interval square(const Interval& a) {
    require_environment();
    const Bounds left=product(a.lower(),a.lower()),right=product(a.upper(),a.upper());
    const double hi=std::max(left.upper,right.upper);
    if(a.contains_zero())return {0,hi};
    const double lo=a.strictly_positive()?left.lower:right.lower;
    // A positive exact square that underflows must never get a negative bound.
    return {std::max(0.0,lo),hi};
}
Interval polynomial(std::span<const Interval> coefficients,const Interval& x) {
    require_environment();
    if(coefficients.empty())throw std::invalid_argument("Polynomial needs at least one coefficient");
    Interval result=coefficients.front();
    for(std::size_t i=1;i<coefficients.size();++i)result=add(mul(result,x),coefficients[i]);
    return result;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
