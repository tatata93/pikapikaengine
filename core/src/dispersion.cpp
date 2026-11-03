#include "pikapika/dispersion.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
#include <stdexcept>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Dispersion enclosures require strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise, on, push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::optics::dispersion {
namespace {
using I=interval::Interval;
I p(double x){return I::point(x);}
bool finite(const I& x){return std::isfinite(x.lower())&&std::isfinite(x.upper());}
void band_valid(Band x){
    if(!std::isfinite(x.minimum)||!std::isfinite(x.maximum)||x.minimum<1e-12||x.maximum>1||x.minimum>x.maximum)
        throw std::invalid_argument("Dispersion wavelength band must lie in [1e-12,1] metres");
}
void valid(Band declared,Band requested,const Settings& s){
    interval::require_environment();band_valid(declared);band_valid(requested);
    if(requested.minimum<declared.minimum||requested.maximum>declared.maximum)
        throw std::invalid_argument("Dispersion extrapolation outside declared band");
    if(!std::isfinite(s.maximum_phase_width)||s.maximum_phase_width<=0||s.max_sqrt_refinements<1||s.max_sqrt_refinements>256)
        throw std::invalid_argument("Invalid dispersion precision/budget");
}
void coefficient(double x){if(!std::isfinite(x)||std::abs(x)>1e12)throw std::invalid_argument("Dispersion coefficient outside finite +/-1e12 domain");}
Result failure(Result r,Status status,Reason reason){r.status=status;r.reason=reason;r.values.reset();return r;}
Result finish(Result r,const I& n,const I& derivative,const I& group,const Settings& s){
    if(!finite(n)||!finite(derivative)||!finite(group))return failure(r,Status::unresolved,Reason::numerical_range);
    if(n.upper()<=0)return failure(r,Status::nonphysical,Reason::nonpositive_phase);
    if(n.lower()<=0)return failure(r,Status::unresolved,Reason::positivity_uncertain);
    if((p(n.upper())-p(n.lower())).upper()>s.maximum_phase_width)
        return failure(r,Status::unresolved,Reason::phase_width);
    r.status=Status::resolved;r.reason=Reason::none;
    r.values=Values{n,derivative,group,n.lower()>=1e-6&&n.upper()<=1e6};return r;
}
// All decisions use enclosure arithmetic, never an assumed libm sqrt rounding.
// The exponent supplies a power-of-two upper bound; interval squares and the
// identity |sqrt(x)-m|=|x-m*m|/(sqrt(x)+m) preserve enclosure at every refinement.
I square_root_endpoint(double endpoint,unsigned budget,Result& r){
    const I x=p(endpoint);
    int exponent=0;std::frexp(x.upper(),&exponent);
    const int half=exponent>0?(exponent+1)/2:exponent/2;
    double lo=0,hi=std::ldexp(1.0,half);
    for(unsigned j=0;j<budget;++j){
        ++r.sqrt_refinements;const double m=std::midpoint(lo,hi);
        if(m==lo||m==hi)return {lo,hi};
        const I m2=interval::square(p(m));
        if(m2.upper()<x.lower())lo=m;
        else if(m2.lower()>x.upper())hi=m;
        else {
            const I delta=x-m2,denominator=p(lo)+p(m);
            const double difference=std::max(std::abs(delta.lower()),std::abs(delta.upper()));
            if(denominator.strictly_positive()){
                const double error=(I{0,difference}/denominator).upper();
                if(std::isfinite(error)){
                    const auto clipped=interval::intersection(I{lo,hi},p(m)+I{-error,error});
                    if(!clipped)throw std::logic_error("Inconsistent dispersion sqrt bounds");
                    return *clipped;
                }
            }
            return {lo,hi};
        }
    }
    r.reason=Reason::refinement_budget;return {lo,hi};
}
I square_root(const I& x,unsigned budget,Result& r){
    const I lower=square_root_endpoint(x.lower(),budget,r);
    if(r.reason==Reason::refinement_budget)return lower;
    const I upper=square_root_endpoint(x.upper(),budget,r);
    return {lower.lower(),upper.upper()};
}
}
Result evaluate(const Cauchy& model,Band band,const Settings& settings){
    valid(model.valid_band,band,settings);coefficient(model.a);coefficient(model.b);coefficient(model.c);
    Result r;
    if(model.b==0&&model.c==0)return finish(r,p(model.a),p(0),p(model.a),settings);
    const I wavelength{band.minimum,band.maximum},squared=interval::square(wavelength);
    const I b=p(model.b)/squared,c=p(model.c)/interval::square(squared);
    const I phase=(p(model.a)+b)+c;
    const I derivative=-(p(2)*b+p(4)*c)/wavelength;
    // Algebraically simplified derivative formula retains lambda correlation.
    const I group=(p(model.a)+p(3)*b)+p(5)*c;
    return finish(r,phase,derivative,group,settings);
}
Result evaluate(const Sellmeier& model,Band band,const Settings& settings){
    valid(model.valid_band,band,settings);
    if(model.count>model.terms.size())throw std::invalid_argument("At most eight Sellmeier oscillators");
    for(unsigned j=0;j<model.count;++j){coefficient(model.terms[j].b);coefficient(model.terms[j].c);}
    Result r;const I wavelength{band.minimum,band.maximum},squared=interval::square(wavelength);
    I q=p(1),q_derivative=p(0);
    for(unsigned j=0;j<model.count;++j){
        const auto term=model.terms[j];
        if(term.b==0)continue; // absent oscillator: its nominal pole is removable
        if(term.c==0){q=q+p(term.b);continue;} // lambda>0, exact constant term
        const I denominator=squared-p(term.c);
        if(denominator.contains_zero())return failure(r,Status::unresolved,Reason::pole_not_excluded);
        // lambda^2/(lambda^2-C)=1+C/(lambda^2-C). This exact
        // identity removes a repeated wavelength occurrence, without sampling.
        q=(q+p(term.b))+(p(term.b)*p(term.c))/denominator;
        q_derivative=q_derivative-((p(2)*p(term.b))*p(term.c)*wavelength)/interval::square(denominator);
    }
    r.squared_phase=q;
    if(!finite(q)||!finite(q_derivative))return failure(r,Status::unresolved,Reason::numerical_range);
    if(q.upper()<=0)return failure(r,Status::nonphysical,Reason::nonpositive_squared_phase);
    if(q.lower()<=0)return failure(r,Status::unresolved,Reason::positivity_uncertain);
    const I phase=square_root(q,settings.max_sqrt_refinements,r);
    if(r.reason==Reason::refinement_budget)return failure(r,Status::unresolved,Reason::refinement_budget);
    if(!phase.strictly_positive())return failure(r,Status::unresolved,Reason::positivity_uncertain);
    const I derivative=q_derivative/(p(2)*phase),group=phase-wavelength*derivative;
    return finish(r,phase,derivative,group,settings);
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
