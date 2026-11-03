#include "pikapika/polarization.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace pikapika::optics;
using namespace pikapika::optics::polarization;
using pikapika::Vec3;
namespace {
unsigned groups=0,flux_cases=0,boundary_cases=0;
double max_energy_error=0,max_coherent_error=0,max_boundary_error=0;
void check(bool ok,const char* message) { if(!ok)throw std::runtime_error(message); }
void test(const char* name,const std::function<void()>& fn) { fn();++groups;std::cout<<"PASS "<<name<<'\n'; }
bool near(double a,double b,double tolerance=3e-13) { return std::abs(a-b)<=tolerance; }
void state_near(const Stokes& a,const Stokes& b,double tolerance=3e-13) {
    check(near(a.i,b.i,tolerance)&&near(a.q,b.q,tolerance)&&near(a.u,b.u,tolerance)&&near(a.v,b.v,tolerance),"Stokes reference");
}
void good(const Split& s) {
    check(s.failure==Failure::none&&s.reflected.has_value(),"successful polarized split");
    validate(s.reflected->power);if(s.transmitted)validate(s.transmitted->power);
}
template<class F> void rejects(F fn) { bool threw=false;try{fn();}catch(const std::invalid_argument&){threw=true;}check(threw,"input rejected"); }
InterfaceInput source(double angle,double ni=1,double nt=1.5) { return {{std::sin(angle),-std::cos(angle),0},{0,1,0},ni,nt,550e-9}; }
Stokes coherent(std::complex<double> a,std::complex<double> b) {
    const auto xy=a*std::conj(b);return {std::norm(a)+std::norm(b),std::norm(a)-std::norm(b),2*xy.real(),2*xy.imag()};
}
Vec3 combine(Vec3 a,double x,Vec3 b,double y) { return {a.x*x+b.x*y,a.y*x+b.y*y,a.z*x+b.z*y}; }
}
int main() {
try {
    test("physical cone accepts unpolarized pure partial and zero power",[]{
        for(const Stokes s:std::array<Stokes,6>{{{1,0,0,0},{1,1,0,0},{1,0,1,0},{1,0,0,-1},{1,.2,.3,.4},{0,0,0,0}}})validate(s);
        validate({1e-280,0,0,1e-280});validate({1e100,1e100,0,0});
    });
    test("nonphysical and nonfinite states are rejected",[]{
        rejects([]{validate({-1,0,0,0});});rejects([]{validate({0,1e-300,0,0});});
        rejects([]{validate({1,1.001,0,0});});rejects([]{validate({1,1,1,0});});
        rejects([]{validate({1,std::numeric_limits<double>::quiet_NaN(),0,0});});rejects([]{validate({1e101,0,0,0});});
    });
    test("frame projection scale and handedness",[]{
        const auto a=make_frame({0,0,10},{7,0,3}),b=make_frame({0,0,.01},{.7,0,.3});
        state_near(reexpress({1,.4,.3,-.2},a,b),{1,.4,.3,-.2});
        check(near(a.first.x,1)&&near(a.second.y,1)&&near(a.direction.z,1),"known projected basis");
        rejects([]{make_frame({0,0,1},{0,0,1});});rejects([]{make_frame({0,0,0},{1,0,0});});
        rejects([]{make_frame({0,0,1},{1e-10,0,1});});
    });
    test("passive basis rotations use twice the angle and retain circular state",[]{
        const auto a=make_frame({0,0,1},{1,0,0}),b=make_frame({0,0,1},{1,1,0});
        state_near(reexpress({1,1,0,0},a,b),{1,0,-1,0});
        state_near(reexpress({1,0,0,1},a,b),{1,0,0,1});
        const Stokes partial{1,.2,-.3,.4};state_near(reexpress(reexpress(partial,a,b),b,a),partial);
        auto wrong=a;wrong.second.y=-1;rejects([&]{reexpress(partial,wrong,a);});
        rejects([&]{reexpress(partial,a,make_frame({0,0,-1},{1,0,0}));});
    });
    test("Jones polarizer and retarder retain explicit phase sign",[]{
        state_near(diagonal_jones({},1,0),{.5,.5,0,0});
        state_near(diagonal_jones({1,0,1,0},1,std::complex<double>(0,1)),{1,0,0,-1});
        state_near(diagonal_jones({1,0,0,-1},1,std::complex<double>(0,-1)),{1,0,1,0});
        state_near(diagonal_jones({0,0,0,0},1,1),{0,0,0,0});
        rejects([]{diagonal_jones({},1.01,1);});
    });
    test("two polarizers satisfy Malus law with basis transport",[]{
        const auto fixed=make_frame({0,0,1},{1,0,0});
        for(double angle:{0.0,.2,.7,1.2,1.5707963267948966}) {
            const auto rotated=make_frame({0,0,1},{std::cos(angle),std::sin(angle),0});
            const auto first=diagonal_jones({},1,0);
            const auto second=diagonal_jones(reexpress(first,fixed,rotated),1,0);
            check(near(second.i,.5*std::cos(angle)*std::cos(angle)),"independent Malus intensity");
        }
    });
    test("Jones coherency transform agrees with independent field vector",[]{
        for(unsigned k=0;k<100;++k) {
            const std::complex<double> x{std::cos(k*.17),std::sin(k*.31)},y{std::sin(k*.11),std::cos(k*.27)};
            const std::complex<double> a=std::polar(.8,k*.13),b=std::polar(.3,-static_cast<double>(k)*.19);
            const auto result=diagonal_jones(coherent(x,y),a,b),expected=coherent(a*x,b*y);
            const double error=std::max({std::abs(result.i-expected.i),std::abs(result.q-expected.q),std::abs(result.u-expected.u),std::abs(result.v-expected.v)});
            max_coherent_error=std::max(max_coherent_error,error);state_near(result,expected);
        }
    });
    test("coherency products preserve representable power across intermediate exponent underflow",[]{
        const double power=0x1p300,amplitude=0x1p-600,expected=0x1p-900;
        const auto symmetric=diagonal_jones({power,0,0,0},amplitude,amplitude);
        check(symmetric.i==expected&&symmetric.q==0,"tiny amplitude squared times large power must survive");
        const auto pure=diagonal_jones({power,-power,0,0},1,amplitude);
        check(pure.i==expected&&pure.q==-expected,"unequal amplitudes must not cancel pure p output");
        const auto correlated=diagonal_jones({power,0,power,0},amplitude,amplitude);
        check(correlated.i==expected&&correlated.u==expected,"cross coherency must survive");
        const double tiny=std::numeric_limits<double>::denorm_min();
        const auto identity=diagonal_jones({tiny,0,0,0},1,1);
        check(identity.i==tiny&&identity.q==0,"subnormal half powers must recombine before rounding");
        const auto imaginary=diagonal_jones({power,0,power,0},{0,amplitude},amplitude);
        check(imaginary.i==expected&&imaginary.v==expected,"complex coherency must preserve exponent range");
    });
    test("normal incidence frame reversal yields isotropic physical electric reflection",[]{
        const auto r=dielectric_split(source(0),{1,0,0},{1,0,1,0});good(r);
        check(r.transmitted.has_value(),"normal transmission");
        state_near(r.reflected->power,{.04,0,-.04,0});state_near(r.transmitted->power,{.96,0,.96,0});
        check(near(r.reflected->amplitude_s.real(),-.2)&&near(r.reflected->amplitude_p.real(),.2),"signed Fresnel normal amplitudes");
        check(near(r.input_frame.second.z,1)&&near(r.reflected->frame.second.z,-1),"right-handed reflected basis reverses p");
        const auto circular=dielectric_split(source(0),{1,0,0},{1,0,0,1});good(circular);
        state_near(circular.reflected->power,{.04,0,0,-.04});
    });
    test("unpolarized normal split and homogeneous grazing limits",[]{
        const auto r=dielectric_split(source(0),{1,0,0});good(r);
        state_near(r.reflected->power,{.04,0,0,0});state_near(r.transmitted->power,{.96,0,0,0});
        const Stokes original{1,.2,.3,-.4};
        const auto homogeneous=dielectric_split({{1,0,0},{0,1,0},1,1,550e-9},{0,0,1},original);good(homogeneous);
        state_near(homogeneous.transmitted->power,original);state_near(homogeneous.reflected->power,{0,0,0,0});
        const auto near_normal=dielectric_split({{1e-10,-1,0},{0,1,0},1,1,550e-9},{0,0,1},original);good(near_normal);
        state_near(near_normal.transmitted->power,original);
        const auto oblique=dielectric_split({{1,-1,0},{0,1,0},1,1,550e-9},{1,1,0},original);good(oblique);
        state_near(reexpress(oblique.transmitted->power,oblique.transmitted->frame,oblique.input_frame),original);
        state_near(oblique.reflected->power,{0,0,0,0});
    });
    test("Brewster separates incoming s and p rather than averaging each time",[]{
        const auto in=source(std::atan(1.5));
        const auto s=dielectric_split(in,{0,0,-1},{1,1,0,0}),p=dielectric_split(in,{0,0,-1},{1,-1,0,0});good(s);good(p);
        check(near(s.reflected->power.i,25.0/169)&&p.reflected->power.i<1e-28,"known Brewster polarized intensity");
        check(near(s.reflected->power.i+s.transmitted->power.i,1)&&near(p.reflected->power.i+p.transmitted->power.i,1),"Brewster conservation");
    });
    test("two same-plane Brewster reflections retain generated polarization",[]{
        const double angle=std::atan(1.5),ci=std::cos(angle),si=std::sin(angle),rs=25.0/169;
        const auto first=dielectric_split(source(angle),{0,0,-1});good(first);
        const auto& beam=*first.reflected;
        InterfaceInput second{beam.frame.direction,combine(beam.frame.direction,-ci,beam.frame.second,si),1,1.5,550e-9};
        const auto result=dielectric_split(second,beam.frame.first,beam.power);good(result);
        check(near(result.reflected->power.i,rs*rs/2),"polarized two-reflection reference");
        check(std::abs(result.reflected->power.i-(rs/2)*(rs/2))>1e-3,"does not reaverage s/p power");
    });
    test("rotated second Brewster incidence plane extinguishes first reflected s",[]{
        const double angle=std::atan(1.5),ci=std::cos(angle),si=std::sin(angle);
        const auto first=dielectric_split(source(angle),{0,0,-1});good(first);
        const auto& beam=*first.reflected;
        InterfaceInput second{beam.frame.direction,combine(beam.frame.direction,-ci,beam.frame.first,si),1,1.5,550e-9};
        const auto result=dielectric_split(second,beam.frame.first,beam.power);good(result);
        check(result.reflected->power.i<1e-28,"independent crossed-plane Brewster extinction");
    });
    test("TIR retains independent complex phase and creates elliptic polarization",[]{
        const InterfaceInput in{{.8,-.6,0},{0,1,0},1.5,1,550e-9};
        const auto r=dielectric_split(in,{0,0,-1},{1,0,1,0});good(r);
        check(!r.transmitted&&r.interface.kind==InterfaceKind::total_internal_reflection,"TIR no propagating transmission");
        state_near(r.reflected->power,{1,0,53.0/75,16*std::sqrt(11.0)/75});
        check(near(r.reflected->amplitude_s.real(),37.0/125)&&near(r.reflected->amplitude_p.real(),-7.0/15),"independent exact TIR real amplitudes");
        check(near(std::abs(r.reflected->amplitude_s),1)&&near(std::abs(r.reflected->amplitude_p),1),"TIR unit amplitude");
    });
    test("power normalized transmission satisfies independent tangential Maxwell boundaries",[]{
        for(double ni:{1.0,1.5,2.0})for(double nt:{1.0,1.2,1.7})for(double angle:{0.0,.2,.5,.8,1.1,1.4}) {
            const auto r=dielectric_split(source(angle,ni,nt),{0,0,-1});good(r);
            if(!r.transmitted)continue;
            const double ci=r.interface.cosine_incident,ct=*r.interface.cosine_transmitted;
            const double flux=nt*ct/(ni*ci);
            const double ts=r.transmitted->amplitude_s.real()/std::sqrt(flux),tp=r.transmitted->amplitude_p.real()/std::sqrt(flux);
            const double rs=r.reflected->amplitude_s.real(),rp=r.reflected->amplitude_p.real();
            // Tangential E and H continuity in right-handed local ray frames.
            const double residual=std::max({std::abs(1+rs-ts),std::abs(ni*ci*(1-rs)-nt*ct*ts),
                std::abs(ci*(1-rp)-ct*tp),std::abs(ni*(1+rp)-nt*tp)});
            max_boundary_error=std::max(max_boundary_error,residual);check(residual<5e-13,"Maxwell tangential E/H boundary residual");++boundary_cases;
        }
    });
    test("critical and unresolved incidence plane never return stale branches",[]{
        const auto critical=dielectric_split({{3,-4,0},{0,1,0},5,3,550e-9},{0,0,1});
        check(critical.failure==Failure::interface_uncertain&&!critical.reflected&&!critical.transmitted,"critical uncertainty");
        const auto plane=dielectric_split({{1e-10,-1,0},{0,1,0},1,1.5,550e-9},{0,0,1});
        check(plane.failure==Failure::incidence_plane_uncertain&&!plane.reflected&&!plane.transmitted,"near-normal plane conditioning");
        rejects([]{dielectric_split({{0,1,0},{0,1,0},1,1.5,550e-9},{1,0,0});});
    });
    test("all polarized interface branches conserve power across angle and index corpus",[]{
        for(double ni:{1.0,1.3,1.5,2.0})for(double nt:{1.0,1.2,1.7})for(double angle:{0.0,.1,.4,.7,1.0,1.3,1.5})
            for(Stokes input:std::array<Stokes,5>{{{1,0,0,0},{1,1,0,0},{1,-1,0,0},{1,0,1,0},{1,.2,.3,-.4}}}) {
                const auto r=dielectric_split(source(angle,ni,nt),{0,0,-1},input);good(r);
                const double total=r.reflected->power.i+(r.transmitted?r.transmitted->power.i:0);
                const double error=std::abs(total-input.i);max_energy_error=std::max(max_energy_error,error);
                check(error<3e-13,"independent branch flux conservation");++flux_cases;
            }
    });
    std::cout<<std::setprecision(17)<<"Polarization: "<<groups<<" groups, "<<flux_cases<<" interface flux cases, "<<boundary_cases<<" Maxwell boundary cases; max energy error="<<max_energy_error<<", max coherent reference error="<<max_coherent_error<<", max boundary residual="<<max_boundary_error<<'\n';
    return 0;
} catch(const std::exception& e) { std::cerr<<"FAIL "<<e.what()<<'\n';return 1; }
}
