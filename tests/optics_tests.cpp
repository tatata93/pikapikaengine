#include "pikapika/optics.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>

using pikapika::Vec3;
using namespace pikapika::optics;
namespace {
unsigned passed=0,flux_cases=0;
double max_energy_error=0,max_flux_error=0,max_snell_error=0;
void check(bool yes,const char* message) { if(!yes)throw std::runtime_error(message); }
void test(const char* name,const std::function<void()>& body) { body();++passed;std::cout<<"PASS "<<name<<'\n'; }
bool near(double a,double b,double tolerance=2e-14) { return std::abs(a-b)<=tolerance; }
Vec3 negative(Vec3 a) { return {-a.x,-a.y,-a.z}; }
double dot(Vec3 a,Vec3 b) { return a.x*b.x+a.y*b.y+a.z*b.z; }
double length(Vec3 a) { return std::sqrt(dot(a,a)); }
void vector_near(Vec3 a,Vec3 b,double tolerance=2e-14) { check(length({a.x-b.x,a.y-b.y,a.z-b.z})<=tolerance,"known direction"); }
InterfaceInput input(Vec3 i={0,-1,0},Vec3 n={0,1,0},double ni=1,double nt=1.5) { return {i,n,ni,nt,550e-9}; }
template<class Error=std::exception> void rejects(const std::function<void()>& body) {
    bool threw=false;try{body();}catch(const Error&){threw=true;}check(threw,"expected rejection");
}
void successful(const InterfaceResult& r) {
    check(r.kind!=InterfaceKind::uncertain&&r.uncertainty==Uncertainty::none,"expected determined interface");
    check(r.power.has_value(),"determined power");
    check(near(length(r.incident_unit),1)&&near(length(r.normal_unit),1)&&near(length(r.reflected),1),"unit outputs");
    for(double v:{r.power->reflectance_s,r.power->transmittance_s,r.power->reflectance_p,r.power->transmittance_p,
        r.power->reflectance_unpolarized,r.power->transmittance_unpolarized})
        check(std::isfinite(v)&&v>=0&&v<=1,"power probability");
    if(r.kind==InterfaceKind::transmission)check(r.transmitted&&r.cosine_transmitted&&near(length(*r.transmitted),1),"transmitted unit output");
    else check(!r.transmitted&&!r.cosine_transmitted,"TIR has no propagating transmitted ray");
}
void unresolved(const InterfaceResult& r,Uncertainty why) {
    check(r.kind==InterfaceKind::uncertain&&r.uncertainty==why,"expected uncertainty reason");
    check(!r.power&&!r.transmitted&&!r.cosine_transmitted,"uncertain must not supply success values");
}
// Independent EM normal-flux formula: E-field amplitude t is NOT power T.
// This is deliberately not T=1-R, nor the implementation's 4*x*y expression.
void check_flux(const InterfaceInput& source,const InterfaceResult& r) {
    successful(r);check(r.kind==InterfaceKind::transmission,"flux transmitted");
    const double ci=-dot(r.incident_unit,r.normal_unit),ct=-dot(*r.transmitted,r.normal_unit);
    check(ci>0&&ct>0,"positive crossing angles");
    const double ni=source.index_incident,nt=source.index_transmitted;
    const double ts=2*ni*ci/(ni*ci+nt*ct),tp=2*ni*ci/(nt*ci+ni*ct);
    const double factor=nt*ct/(ni*ci);
    const double error=std::max(std::abs(r.power->transmittance_s-factor*ts*ts),std::abs(r.power->transmittance_p-factor*tp*tp));
    max_flux_error=std::max(max_flux_error,error);check(error<8e-14,"independent normal flux");
    const auto& p=*r.power;
    const double energy=std::max(std::abs(p.reflectance_s+p.transmittance_s-1),std::abs(p.reflectance_p+p.transmittance_p-1));
    max_energy_error=std::max(max_energy_error,energy);check(energy<2e-14,"independent R+T energy");
    check(near(p.reflectance_unpolarized,(p.reflectance_s+p.reflectance_p)/2),"unpolarized R");
    check(near(p.transmittance_unpolarized,(p.transmittance_s+p.transmittance_p)/2),"unpolarized T");
    const double si=std::sqrt(std::max(0.0,1-ci*ci)),st=std::sqrt(std::max(0.0,1-ct*ct));
    const double snell=std::abs(ni*si-nt*st);max_snell_error=std::max(max_snell_error,snell);
    check(snell<2e-12,"independent Snell angle relation");++flux_cases;
}

void oracle_row(const InterfaceInput& in) {
    const auto r=dielectric_interface(in);
    const auto bits=[](double v){return std::bit_cast<std::uint64_t>(v);};
    std::cout<<std::hex<<bits(in.incident.x)<<','<<bits(in.incident.y)<<','<<bits(in.incident.z)<<','
        <<bits(in.normal.x)<<','<<bits(in.normal.y)<<','<<bits(in.normal.z)<<','
        <<bits(in.index_incident)<<','<<bits(in.index_transmitted)<<','
        <<bits(r.discriminant.lower())<<','<<bits(r.discriminant.upper())<<','
        <<bits(r.incident_dot.lower())<<','<<bits(r.incident_dot.upper())<<std::dec<<','
        <<static_cast<int>(r.kind)<<','<<static_cast<int>(r.uncertainty)<<'\n';
}
int oracle() {
    // Exact critical configuration D=9-x^2; adjacent doubles have opposite
    // mathematical signs, while a conservative interval may remain unresolved.
    for(double x:{3.0,std::nextafter(3.0,0.0),std::nextafter(3.0,4.0),3.0-1e-6,3.0+1e-6})
        oracle_row(input({x,-4,0},{0,1,0},1.25,0.75));
    std::uint64_t state=0x4f707469637331ULL;
    auto next=[&]() {state^=state<<13;state^=state>>7;state^=state<<17;return state;};
    // Rational source values in all 3 axes. normal=-incident+(small tangent)
    // stays on the incident side; indices vary above and below each other.
    for(unsigned j=0;j<512;++j) {
        const double x=static_cast<int>(next()%4096)-2048,y=static_cast<int>(next()%4096)-2048,z=static_cast<int>(next()%4096)-2048;
        Vec3 i{x/1024,-2-std::abs(y)/1024,z/1024};
        const double ni=(512+next()%2048)/1024.0,nt=(512+next()%2048)/1024.0;
        oracle_row(input(i,{0,1,0},ni,nt));
        oracle_row(input(i,{-i.x+0.5,-i.y,-i.z-0.25},ni,nt));
    }
    return 0;
}
}

int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string_view(argv[1])=="--oracle")return oracle();
        test("normal incidence analytic four percent",[]{
            const auto in=input();const auto r=dielectric_interface(in);successful(r);
            check(r.kind==InterfaceKind::transmission,"normal transmission");
            vector_near(r.reflected,{0,1,0});vector_near(*r.transmitted,{0,-1,0});
            check(near(r.power->reflectance_s,1.0/25)&&near(r.power->reflectance_p,1.0/25),"R=1/25");
            check(near(r.power->transmittance_s,24.0/25)&&near(r.power->transmittance_p,24.0/25),"T=24/25");
            check_flux(in,r);
        });
        test("normal incidence reverse index has same power",[]{
            const auto in=input({0,-1,0},{0,1,0},1.5,1);const auto r=dielectric_interface(in);check_flux(in,r);
            check(near(r.power->reflectance_unpolarized,0.04),"reverse normal four percent");
        });
        test("equal media analytic identity at oblique incidence",[]{
            const auto in=input({3,-4,2},{0,2,0},1.25,1.25);const auto r=dielectric_interface(in);successful(r);
            vector_near(*r.transmitted,r.incident_unit);
            check(r.power->reflectance_s==0&&r.power->reflectance_p==0&&r.power->transmittance_unpolarized==1,"homogeneous medium");
            check_flux(in,r);
        });
        test("known three-four-five Snell construction",[]{
            const auto in=input({3,-4,0});const auto r=dielectric_interface(in);check_flux(in,r);
            vector_near(r.reflected,{0.6,0.8,0});
            vector_near(*r.transmitted,{0.4,-std::sqrt(21.0)/5,0});
        });
        test("Brewster p reflection zero with independent rational s",[]{
            const auto in=input({1.5,-1,0});const auto r=dielectric_interface(in);check_flux(in,r);
            check(r.power->reflectance_p<1e-28,"Brewster R_p=0");
            check(near(r.power->reflectance_s,25.0/169),"Brewster R_s=25/169");
            check(near(r.power->transmittance_s,144.0/169),"Brewster T_s=144/169");
            check(std::abs(dot(r.reflected,*r.transmitted))<2e-14,"Brewster orthogonal rays");
        });
        test("total internal reflection no propagating transmission",[]{
            const auto r=dielectric_interface(input({4,-3,0},{0,1,0},1.5,1));successful(r);
            check(r.kind==InterfaceKind::total_internal_reflection&&r.discriminant.strictly_negative(),"TIR certificate");
            check(r.power->reflectance_s==1&&r.power->reflectance_p==1&&r.power->transmittance_unpolarized==0,"TIR power");
            vector_near(r.reflected,{0.8,0.6,0});
        });
        test("reciprocal transmitted path and power",[]{
            const auto in=input({3,-4,0});const auto forward=dielectric_interface(in);successful(forward);
            const auto reverse_in=input(negative(*forward.transmitted),negative(in.normal),1.5,1);
            const auto reverse=dielectric_interface(reverse_in);check_flux(reverse_in,reverse);
            vector_near(*reverse.transmitted,negative(forward.incident_unit));
            check(near(forward.power->reflectance_s,reverse.power->reflectance_s)&&near(forward.power->reflectance_p,reverse.power->reflectance_p),"reciprocal R");
            check(near(forward.power->transmittance_s,reverse.power->transmittance_s)&&near(forward.power->transmittance_p,reverse.power->transmittance_p),"reciprocal power T");
        });
        test("normal convention reversal and propagation reversal reject",[]{
            rejects<std::invalid_argument>([]{dielectric_interface(input({0,-1,0},{0,-1,0}));});
            rejects<std::invalid_argument>([]{dielectric_interface(input({0,1,0},{0,1,0}));});
            const auto r=dielectric_interface(input({0,1,0},{0,-1,0},1.5,1));successful(r);vector_near(*r.transmitted,{0,1,0});
        });
        test("input vector scale invariance and three-dimensional rotation",[]{
            const auto base=dielectric_interface(input({3,-4,0}));
            const auto scaled=dielectric_interface(input({3000,-4000,0},{0,1e-3,0}));successful(scaled);
            vector_near(scaled.reflected,base.reflected);vector_near(*scaled.transmitted,*base.transmitted);
            check(near(scaled.power->reflectance_s,base.power->reflectance_s),"scale invariant power");
            const auto rotated=dielectric_interface(input({0,3,-4},{0,0,1}));successful(rotated);
            vector_near(*rotated.transmitted,{0,0.4,-std::sqrt(21.0)/5});
        });
        test("exact grazing one-sided limit and equal-index ordering",[]{
            auto r=dielectric_interface(input({1,0,0}));successful(r);check(r.exact_grazing,"exact grazing certificate");
            check(r.power->reflectance_s==1&&r.power->reflectance_p==1&&r.power->transmittance_s==0,"grazing limit");
            r=dielectric_interface(input({1,0,0},{0,1,0},1,1));successful(r);
            check(r.exact_grazing&&r.power->reflectance_unpolarized==0&&r.power->transmittance_unpolarized==1,"homogeneous grazing limit");
            // Cancellation 1-1 is not a zero singleton under this conservative
            // enclosure. Equal media must not bypass unresolved orientation.
            unresolved(dielectric_interface(input({1,-1,0},{1,1,0},1,1)),Uncertainty::incident_side);
        });
        test("exact critical and adjacent binary inputs stay unresolved",[]{
            for(double x:{3.0,std::nextafter(3.0,0.0),std::nextafter(3.0,4.0)}) {
                const auto r=dielectric_interface(input({x,-4,0},{0,1,0},1.25,0.75));
                unresolved(r,Uncertainty::critical_angle);check(r.discriminant.contains_zero(),"critical interval contains zero");
            }
        });
        test("separated sides of critical angle certify opposite kinds",[]{
            const auto lower=dielectric_interface(input({3-1e-6,-4,0},{0,1,0},1.25,0.75));
            successful(lower);check(lower.kind==InterfaceKind::transmission&&lower.discriminant.strictly_positive(),"below critical");
            const auto upper=dielectric_interface(input({3+1e-6,-4,0},{0,1,0},1.25,0.75));
            successful(upper);check(upper.kind==InterfaceKind::total_internal_reflection&&upper.discriminant.strictly_negative(),"above critical");
        });
        test("angle and index sweep checks independent normal flux",[]{
            for(const auto indices:std::array<std::array<double,2>,4>{{{1,1.5},{1.5,1},{1,1.25},{1.25,1.75}}})
                for(unsigned degrees=1;degrees<90;++degrees) {
                    const double angle=degrees*std::acos(-1.0)/180;
                    const auto in=input({std::sin(angle),-std::cos(angle),0},{0,1,0},indices[0],indices[1]);
                    const auto r=dielectric_interface(in);successful(r);
                    if(r.kind==InterfaceKind::transmission)check_flux(in,r);
                }
        });
        test("wavelength is explicit metadata not invented dispersion",[]{
            auto a=input(),b=input();a.vacuum_wavelength_m=450e-9;b.vacuum_wavelength_m=650e-9;
            const auto x=dielectric_interface(a),y=dielectric_interface(b);successful(x);successful(y);
            check(x.vacuum_wavelength_m==a.vacuum_wavelength_m&&y.vacuum_wavelength_m==b.vacuum_wavelength_m,"wavelength retained");
            check(x.power->reflectance_unpolarized==y.power->reflectance_unpolarized,"same given indices same result");
        });
        test("finite scale boundaries and unresolved subnormal incidence",[]{
            for(const auto indices:std::array<std::array<double,2>,2>{{{1e-6,1e6},{1e6,1e-6}}}) {
                const auto r=dielectric_interface(input({0,-1e-6,0},{0,1e6,0},indices[0],indices[1]));
                successful(r);check(r.kind==InterfaceKind::transmission,"extreme normal incidence");
                vector_near(*r.transmitted,{0,-1,0});
                check(r.power->transmittance_s>0,"small finite transmitted power retained");
            }
            const double tiny=std::numeric_limits<double>::denorm_min();
            // Exact finite negative/positive dot, but a one-ulp enclosure
            // reaches zero. Do not assume orientation from a rounded cosine.
            unresolved(dielectric_interface(input({1,-tiny,0})),Uncertainty::incident_side);
            unresolved(dielectric_interface(input({1,tiny,0})),Uncertainty::incident_side);
        });
        test("invalid finite domain and nonfinite inputs reject",[]{
            const double nan=std::numeric_limits<double>::quiet_NaN(),inf=std::numeric_limits<double>::infinity();
            for(const Vec3 v:std::array<Vec3,5>{{{0,0,0},{1e-7,0,0},{1e7,0,0},{nan,0,0},{0,-1,inf}}}) {
                rejects<std::invalid_argument>([&]{dielectric_interface(input(v));});
                rejects<std::invalid_argument>([&]{dielectric_interface(input({0,-1,0},v));});
            }
            for(double value:{-1.0,0.0,1e-7,1e7,nan,inf}) {
                rejects<std::invalid_argument>([&]{dielectric_interface(input({0,-1,0},{0,1,0},value,1));});
                rejects<std::invalid_argument>([&]{dielectric_interface(input({0,-1,0},{0,1,0},1,value));});
            }
            for(double value:{-1.0,0.0,nan,inf}) {
                auto in=input();in.vacuum_wavelength_m=value;rejects<std::invalid_argument>([&]{dielectric_interface(in);});
            }
        });
        std::cout<<"OPTICS PASS "<<passed<<" groups; flux cases "<<flux_cases
            <<"; max energy error "<<std::setprecision(17)<<max_energy_error
            <<"; max flux error "<<max_flux_error<<"; max Snell error "<<max_snell_error<<'\n';
        return 0;
    } catch(const std::exception& error) {std::cerr<<"OPTICS FAIL: "<<error.what()<<'\n';return 1;}
}
