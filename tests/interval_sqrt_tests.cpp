#include "pikapika/interval.hpp"
#include <cstdint>
#include <algorithm>
#include <bit>
#include <cfenv>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>
using namespace pikapika::interval;
namespace {
unsigned groups{};
void check(bool v,const char* m){if(!v)throw std::runtime_error(m);}
void test(const char* n,const std::function<void()>& f){f();++groups;std::cout<<"PASS "<<n<<'\n';}
template<class F>void rejects(F f){bool threw=false;try{f();}catch(const std::exception&){threw=true;}check(threw,"expected rejection");}
struct Input {double lo,hi;unsigned budget{128};};
std::vector<Input> inputs(){
    std::vector<Input> v{{0,0}};
    for(int e=-1074;e<=1023;++e){const double x=std::ldexp(1.,e);v.push_back({x,x});}
    const double t=std::numeric_limits<double>::denorm_min(),n=std::numeric_limits<double>::min(),m=std::numeric_limits<double>::max();
    for(Input x:std::initializer_list<Input>{{0,t},{t,2*t},{t,n},{n,m},{0,m},{m,m},{std::nextafter(n,0),n},{1,4},{2,3},{.25,1},{std::nextafter(1.,0),std::nextafter(1.,2)},{std::nextafter(4.,0),4}})v.push_back(x);
    std::uint64_t seed=0x743fea0c98152d67ULL;
    const auto random=[&](){seed^=seed<<13;seed^=seed>>7;seed^=seed<<17;return std::bit_cast<double>(seed&0x7fefffffffffffffULL);};
    for(unsigned j=0;j<512;++j){const double a=random(),b=random();v.push_back({a,a});v.push_back({std::min(a,b),std::max(a,b)});}
    for(unsigned j=0;j<64;++j){const double x=random();for(unsigned budget:{1U,2U,8U})v.push_back({x,x,budget});}
    return v;
}
void hex(double v){std::cout<<std::hex<<std::setfill('0')<<std::setw(16)<<std::bit_cast<std::uint64_t>(v)<<std::dec;}
void oracle(){std::cout<<"ordinal,inputLo,inputHi,budget,outputLo,outputHi,refinements,limited\n";unsigned j=0;for(const auto& x:inputs()){const auto r=sqrt_enclosure(Interval(x.lo,x.hi),x.budget);std::cout<<j++<<',';hex(x.lo);std::cout<<',';hex(x.hi);std::cout<<','<<x.budget<<',';hex(r.value.lower());std::cout<<',';hex(r.value.upper());std::cout<<','<<r.refinements<<','<<r.refinement_limited<<'\n';}}
}
int main(int argc,char** argv){try{
    if(argc==2&&std::string_view(argv[1])=="--oracle"){oracle();return 0;}
    test("zero and all exact power-of-four roots need no refinement",[]{for(int e=-1074;e<=1022;e+=2){const auto r=sqrt_enclosure(Interval::point(std::ldexp(1.,e)));const double exact=std::ldexp(1.,e/2);check(r.value.lower()==exact&&r.value.upper()==exact&&r.refinements==0&&!r.refinement_limited,"exact power square");}const auto z=sqrt_enclosure(Interval::point(0));check(z.value.contains(0)&&z.refinements==0,"zero root");});
    test("known rational roots remain enclosed rather than assumed libm exact",[]{for(const double root:{1.5,1.25,1.75,.75,.125,1024.}){const auto r=sqrt_enclosure(Interval::point(root*root));check(r.value.contains(root)&&!r.refinement_limited,"known dyadic rational root");}});
    test("full finite exponent range has finite ordered roots and measured small width",[]{for(const auto& x:inputs()){const auto r=sqrt_enclosure(Interval(x.lo,x.hi),x.budget);check(std::isfinite(r.value.lower())&&std::isfinite(r.value.upper())&&r.value.lower()>=0,"finite root endpoints");check(r.refinements<=2*x.budget,"bounded work");if(x.lo==x.hi&&x.budget==128){check(!r.refinement_limited,"full budget resolves point bracket");check(r.value.upper()-r.value.lower()<=r.value.upper()*1e-12,"finite point bracket width");}}});
    test("limited roots retain genuine nonzero enclosing width and recover",[]{const auto a=sqrt_enclosure(Interval::point(3),1);check(a.refinement_limited&&a.refinements==1&&a.value.lower()==1.5&&a.value.upper()==2,"one-step enclosure");const auto b=sqrt_enclosure(Interval::point(3));check(!b.refinement_limited&&b.value.lower()>=a.value.lower()&&b.value.upper()<=a.value.upper(),"refinement recovery");});
    test("interval monotonicity covers both zero and maximum input",[]{const auto r=sqrt_enclosure(Interval(0,std::numeric_limits<double>::max()));check(r.value.lower()==0&&r.value.upper()>1e154&&std::isfinite(r.value.upper()),"whole finite nonnegative family");});
    test("invalid domains and budgets throw without modifying an earlier result",[]{const auto a=sqrt_enclosure(Interval::point(2));rejects([]{sqrt_enclosure(Interval(-1,0));});rejects([]{sqrt_enclosure(Interval::whole());});rejects([]{sqrt_enclosure(Interval::point(2),0);});rejects([]{sqrt_enclosure(Interval::point(2),257);});const auto b=sqrt_enclosure(Interval::point(2));check(a.value.lower()==b.value.lower()&&a.value.upper()==b.value.upper(),"stateless recovery");});
#ifndef __EMSCRIPTEN__
    test("unsupported rounding mode is rejected and restored",[]{const int saved=std::fegetround();check(std::fesetround(FE_UPWARD)==0,"set rounding");bool threw=false;try{sqrt_enclosure(Interval::point(2));}catch(const std::exception&){threw=true;}std::fesetround(saved);check(threw,"unsupported mode rejection");check(!sqrt_enclosure(Interval::point(2)).refinement_limited,"environment recovery");});
#endif
    std::cout<<"Interval sqrt: "<<groups<<" groups\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
