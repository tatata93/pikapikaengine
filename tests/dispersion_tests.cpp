#include "pikapika/dispersion.hpp"
#include <bit>
#include <cstdint>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>

using namespace pikapika::optics::dispersion;
using I=pikapika::interval::Interval;
namespace {
unsigned passed=0;
void check(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
void test(const char* name,const std::function<void()>& body){body();++passed;std::cout<<"PASS "<<name<<'\n';}
void contains(const I& bound,double expected){check(bound.contains(expected),"known analytic value enclosed");}
const Values& resolved(const Result& r){check(r.status==Status::resolved&&r.values.has_value(),"expected resolved");return *r.values;}
void unresolved(const Result& r,Reason why){check(r.status==Status::unresolved&&r.reason==why&&!r.values,"explicit unresolved without values");}
template<class F> void rejects(F&& body){bool threw=false;try{body();}catch(const std::invalid_argument&){threw=true;}check(threw,"invalid input rejected");}
Sellmeier single(double b,double c){Sellmeier m;m.count=1;m.terms[0]={b,c};return m;}
constexpr double wavelength=0x1p-20;
constexpr Band point{wavelength,wavelength};
void bit(double value){std::cout<<std::hex<<std::setfill('0')<<std::setw(16)<<std::bit_cast<std::uint64_t>(value)<<std::dec;}
void emit(unsigned id,unsigned kind,Band band,const Cauchy& c,const Sellmeier& s){
    const auto r=kind==0?evaluate(c,band):evaluate(s,band);
    check(r.status==Status::resolved,"oracle must resolve");
    std::cout<<id<<','<<kind;for(double x:{band.minimum,band.maximum,c.a,c.b,c.c,s.terms[0].b,s.terms[0].c}){std::cout<<',';bit(x);}
    for(const I& x:{r.values->phase,r.values->derivative,r.values->group}){std::cout<<',';bit(x.lower());std::cout<<',';bit(x.upper());}
    std::cout<<'\n';
}
void oracle(){
    std::cout<<"id,kind,lambda_lo,lambda_hi,a,b,c,sell_b,sell_c,n_lo,n_hi,d_lo,d_hi,g_lo,g_hi\n";
    unsigned id=0;
    for(unsigned j=0;j<80;++j){
        const double l=std::ldexp(1.0,-22)+j*std::ldexp(1.0,-29);
        Cauchy c{1.25+j/256.0,std::ldexp(1.0,-46),std::ldexp(1.0,-92)};
        emit(id++,0,{l,l},c,{});emit(id++,0,{l,l+std::ldexp(1.0,-32)},c,{});
    }
    for(unsigned j=0;j<80;++j){
        const double l=std::ldexp(1.0,-20)+j*std::ldexp(1.0,-27);
        const auto s=single(.75+j/128.0,std::ldexp(1.0,-44));
        emit(id++,1,{l,l},{},s);emit(id++,1,{l,l+std::ldexp(1.0,-30)},{},s);
    }
}
}
int main(int argc,char** argv){try{
    if(argc==2&&std::string_view(argv[1])=="--oracle"){oracle();return 0;}
    test("vacuum and exact constant Cauchy",[]{const auto r=evaluate(Cauchy{},Band{400e-9,700e-9});const auto& v=resolved(r);check(v.phase.lower()==1&&v.phase.upper()==1&&v.derivative.lower()==0&&v.group.lower()==1,"exact constant identity");});
    test("binary rational Cauchy phase derivative group",[]{const auto r=evaluate(Cauchy{1.5,0x1p-44,0x1p-88},point);const auto& v=resolved(r);contains(v.phase,401.0/256);contains(v.derivative,-147456);contains(v.group,437.0/256);check(v.within_interface_domain,"interface domain");});
    test("binary rational Sellmeier",[]{const auto r=evaluate(single(2.25,0x1p-42),point);const auto& v=resolved(r);contains(v.phase,2);contains(v.derivative,-0x1p19);contains(v.group,2.5);contains(*r.squared_phase,4);});
    test("Cauchy monotonic whole-band endpoints",[]{const Band b{0x1p-20,0x1p-19};const auto r=evaluate(Cauchy{1.5,0x1p-44,0},b);const auto& v=resolved(r);contains(v.phase,25.0/16);contains(v.phase,97.0/64);contains(v.derivative,-131072);contains(v.derivative,-16384);contains(v.group,27.0/16);contains(v.group,99.0/64);});
    test("absent oscillator does not create pole",[]{const auto r=evaluate(single(0,0x1p-42),{0x1p-21,0x1p-21});const auto& v=resolved(r);contains(v.phase,1);contains(v.derivative,0);contains(v.group,1);});
    test("zero C oscillator is constant",[]{const auto r=evaluate(single(3,0),{1e-12,1});const auto& v=resolved(r);contains(v.phase,2);contains(v.derivative,0);contains(v.group,2);});
    test("exact and crossing resonance rejected",[]{const auto m=single(1,0x1p-42);unresolved(evaluate(m,{0x1p-21,0x1p-21}),Reason::pole_not_excluded);unresolved(evaluate(m,{0x1p-22,0x1p-20}),Reason::pole_not_excluded);});
    test("nonpositive phase models",[]{auto r=evaluate(Cauchy{-1,0,0},point);check(r.status==Status::nonphysical&&!r.values,"negative Cauchy");r=evaluate(single(-2,0),point);check(r.status==Status::nonphysical&&r.reason==Reason::nonpositive_squared_phase&&!r.values,"negative squared index");});
    test("mixed positivity is unresolved",[]{unresolved(evaluate(Cauchy{-.5,0x1p-40,0},{0x1p-20,0x1p-19}),Reason::positivity_uncertain);});
    test("precision and sqrt budgets fail explicitly",[]{Settings s;s.maximum_phase_width=1e-4;unresolved(evaluate(Cauchy{1.5,0x1p-44,0},{0x1p-20,0x1p-19},s),Reason::phase_width);s={};s.max_sqrt_refinements=1;unresolved(evaluate(single(.75,0x1p-42),point,s),Reason::refinement_budget);});
    test("declared validity forbids extrapolation",[]{Cauchy c;c.valid_band={400e-9,700e-9};rejects([&]{evaluate(c,{399e-9,500e-9});});resolved(evaluate(c,{400e-9,700e-9}));});
    test("invalid bands coefficients budgets",[]{rejects([]{evaluate(Cauchy{},Band{0,1});});rejects([]{evaluate(Cauchy{},Band{1,1e-6});});rejects([]{evaluate(Cauchy{std::numeric_limits<double>::infinity(),0,0},point);});rejects([]{auto m=single(1,1);m.count=9;evaluate(m,point);});rejects([]{Settings s;s.max_sqrt_refinements=0;evaluate(Cauchy{},point,s);});});
    test("phase outside interface domain is not clamped",[]{const auto r=evaluate(Cauchy{1e7,0,0},point);const auto& v=resolved(r);check(!v.within_interface_domain&&v.phase.lower()==1e7,"no clamp");});
    test("signed group is retained as mathematical model",[]{const auto r=evaluate(Cauchy{2,-0x1p-40,0},point);const auto& v=resolved(r);contains(v.phase,1);contains(v.group,-1);});
    std::cout<<passed<<" dispersion groups passed\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
