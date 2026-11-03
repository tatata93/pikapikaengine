#include "pikapika/polarized_route.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>
using namespace pikapika;
namespace pr=polarized_route;namespace rt=optical_route;namespace ob=optical_bounds;
using I=interval::Interval;
namespace {
I p(double x){return I::point(x);}
void require(bool ok,const char* message){if(!ok)throw std::runtime_error(message);}
struct Case {
    std::string name;ob::BoundedRay ray;I index=p(1);pr::Stokes stokes;Vec3 reference{1,0,0};std::vector<rt::Step> steps;pr::Settings settings;
    pr::Result run()const{return pr::trace_route({{ray,index,550e-9,steps},stokes,reference},settings);}
};
rt::Step disk(Vec3 center,Vec3 normal,rt::Branch branch,double next){return {optical_geometry::PlaneDisk{center,normal,100},branch,p(next),0,1e6};}
Case simple(std::string name,pr::Stokes state={},rt::Branch branch=rt::Branch::transmitted){Case c;c.name=name;c.stokes=state;c.ray.origin=ob::enclose({0,0,-1});c.steps={disk({0,0,0},{0,0,-1},branch,1.5)};return c;}
Case rational(std::string name,pr::Stokes state){Case c;c.name=name;c.index=p(25);c.reference={0,-1,0};c.stokes=state;c.steps={disk({0,0,1},{3,0,-4},rt::Branch::reflected,39),disk({24,0,-6},{-543,300,-76},rt::Branch::reflected,39)};return c;}
Case tir(std::string name,pr::Stokes state){Case c;c.name=name;c.index=p(1.5);c.reference={0,0,-1};c.stokes=state;c.ray.direction=ob::enclose({4,-3,0});c.steps={disk({4,-3,0},{0,1,0},rt::Branch::reflected,1),disk({8,0,0},{-96,3,80},rt::Branch::reflected,1)};return c;}
std::vector<Case> cases(){
    std::vector<Case> cs;
    Case empty;empty.name="identity-unpolarized";cs.push_back(empty);
    for(auto pair:std::vector<std::pair<std::string,pr::Stokes>>{{"q-plus",{1,1,0,0}},{"q-minus",{1,-1,0,0}},{"u-plus",{1,0,1,0}},{"u-minus",{1,0,-1,0}},{"v-plus",{1,0,0,1}},{"v-minus",{1,0,0,-1}},{"mixed",{2,.25,.5,.75}}})cs.push_back(simple("normal-transmit-"+pair.first,pair.second));
    cs.push_back(simple("normal-reflect-u",{1,0,1,0},rt::Branch::reflected));
    auto homogeneous=simple("homogeneous-transmit",{1,0,0,1});homogeneous.steps[0].next_index=p(1);cs.push_back(homogeneous);homogeneous.name="homogeneous-reflect";homogeneous.steps[0].branch=rt::Branch::reflected;cs.push_back(homogeneous);
    cs.push_back(rational("noncoplanar-unpolarized",{}));cs.push_back(rational("noncoplanar-u",{1,0,1,0}));cs.push_back(rational("noncoplanar-v",{1,0,0,1}));
    cs.push_back(tir("two-tir-u",{1,0,1,0}));cs.push_back(tir("two-tir-v",{1,0,0,1}));
    auto bad=simple("invalid-cone");bad.stokes={1,1,.01,0};cs.push_back(bad);
    bad=simple("uncertain-cone");bad.stokes={5,3,4,0};cs.push_back(bad);
    bad=simple("invalid-reference");bad.reference.x=std::numeric_limits<double>::infinity();cs.push_back(bad);
    bad=simple("parallel-reference");bad.reference={0,0,1};cs.push_back(bad);
    bad=rational("sqrt-budget",{});bad.settings.max_total_sqrt_refinements=1;cs.push_back(bad);
    bad=rational("low-refinement",{});bad.settings.max_sqrt_refinements=1;cs.push_back(bad);
    bad=simple("geometry-miss");bad.steps[0].surface=optical_geometry::PlaneDisk{{1000,0,0},{0,0,-1},1};cs.push_back(bad);
    bad=tir("tir-transmission-unavailable",{});bad.steps[0].branch=rt::Branch::transmitted;cs.push_back(bad);
    bad=simple("near-normal-family");bad.ray.direction[0]=I(-1e-12,1e-12);cs.push_back(bad);
    bad=simple("invalid-later-shape");bad.steps.push_back(disk({0,0,1},{0,0,0},rt::Branch::transmitted,1));cs.push_back(bad);
    bad=simple("zero-power",{0,0,0,0});cs.push_back(bad);
    bad=rational("index-family",{});bad.index=I(25,25.00001);bad.steps[0].next_index=I(39,39.00001);bad.steps[1].next_index=I(39,39.00001);cs.push_back(bad);
    bad=simple("full-sphere");bad.steps[0].surface=optical_geometry::FullSphere{{0,0,0},.5};cs.push_back(bad);
    bad=simple("spherical-cap");bad.steps[0].surface=optical_geometry::SphericalCap{{0,0,0},{0,0,1},.5,.25};cs.push_back(bad);
    bad=simple("completed-power-prefix");bad.steps.push_back(disk({1000,0,1},{0,0,-1},rt::Branch::transmitted,1));cs.push_back(bad);
    bad=simple("subnormal-v-transmit",{std::numeric_limits<double>::denorm_min(),0,0,std::numeric_limits<double>::denorm_min()});cs.push_back(bad);
    bad.name="subnormal-v-identity";bad.steps.clear();cs.push_back(bad);
    return cs;
}
void bound(I x){std::cout<<'['<<x.lower()<<','<<x.upper()<<']';}
void vec(const ob::Bounds3&v){std::cout<<'[';for(unsigned k=0;k<3;++k){if(k)std::cout<<',';bound(v[k]);}std::cout<<']';}
void point(Vec3 v){std::cout<<'['<<v.x<<','<<v.y<<','<<v.z<<']';}
void z(pr::ComplexBounds x){std::cout<<'[';bound(x.real);std::cout<<',';bound(x.imag);std::cout<<']';}
void state(const pr::State&s){std::cout<<"{\"power\":";bound(s.power);std::cout<<",\"diagonal\":[";for(unsigned k=0;k<3;++k){if(k)std::cout<<',';bound(s.coherency.diagonal[k]);}std::cout<<"],\"upper\":[";for(unsigned k=0;k<3;++k){if(k)std::cout<<',';z(s.coherency.upper[k]);}std::cout<<"]}";}
void json(const std::vector<Case>&cs){std::cout<<std::setprecision(17)<<"{\"schema\":1,\"fixtures\":[";bool first=true;for(const auto&c:cs){if(c.name=="invalid-reference")continue;const auto r=c.run();if(!first)std::cout<<',';first=false;std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"origin\":";vec(c.ray.origin);std::cout<<",\"direction\":";vec(c.ray.direction);std::cout<<",\"domain\":["<<c.ray.minimum_parameter<<','<<c.ray.maximum_parameter<<"],\"index\":";bound(c.index);std::cout<<",\"wavelength\":5.5e-7,\"stokes\":["<<c.stokes.i<<','<<c.stokes.q<<','<<c.stokes.u<<','<<c.stokes.v<<"],\"reference\":";point(c.reference);std::cout<<",\"steps\":[";
        for(unsigned j=0;j<c.steps.size();++j){if(j)std::cout<<',';const auto&s=c.steps[j];std::cout<<"{\"kind\":"<<s.surface.index();std::visit([](const auto&d){using T=std::decay_t<decltype(d)>;if constexpr(std::is_same_v<T,optical_geometry::PlaneDisk>){std::cout<<",\"center\":";point(d.center);std::cout<<",\"normal\":";point(d.normal);std::cout<<",\"aperture\":"<<d.aperture_radius;}else if constexpr(std::is_same_v<T,optical_geometry::FullSphere>){std::cout<<",\"center\":";point(d.center);std::cout<<",\"radius\":"<<d.radius;}else{std::cout<<",\"vertex\":";point(d.vertex);std::cout<<",\"axis\":";point(d.axis);std::cout<<",\"radius\":"<<d.signed_radius<<",\"aperture\":"<<d.aperture_radius;}},s.surface);std::cout<<",\"branch\":"<<int(s.branch)<<",\"nextIndex\":";bound(s.next_index);std::cout<<",\"domain\":["<<s.minimum_parameter<<','<<s.maximum_parameter<<"]}";}
        std::cout<<"],\"settings\":["<<c.settings.route.primitive.maximum_parameter_width<<','<<c.settings.route.primitive.max_sqrt_refinements<<','<<c.settings.route.maximum_steps<<','<<c.settings.max_sqrt_refinements<<','<<c.settings.max_total_sqrt_refinements<<"]},\"result\":{\"status\":"<<int(r.status)<<",\"powerFailure\":"<<int(r.power_failure)<<",\"geometryStatus\":"<<(r.geometry?int(r.geometry->status):-1)<<",\"completedPowerSteps\":"<<r.completed_power_steps<<",\"failedPowerStep\":"<<r.failed_power_step<<",\"counters\":["<<r.geometry_queries<<','<<r.interface_queries<<','<<r.geometry_sqrt_refinements<<','<<r.power_sqrt_refinements<<"],\"limited\":"<<(r.refinement_limited?"true":"false")<<",\"initial\":";if(r.initial_state)state(*r.initial_state);else std::cout<<"null";std::cout<<",\"segments\":[";
        for(unsigned j=0;j<r.segments.size();++j){if(j)std::cout<<',';const auto&s=r.segments[j];std::cout<<"{\"ordinal\":"<<s.ordinal<<",\"branch\":"<<int(s.branch)<<",\"exactNormal\":"<<(s.exact_normal?"true":"false")<<",\"homogeneous\":"<<(s.homogeneous?"true":"false")<<",\"s\":";if(s.s)z(*s.s);else std::cout<<"null";std::cout<<",\"p\":";if(s.p)z(*s.p);else std::cout<<"null";std::cout<<",\"state\":";if(s.outgoing)state(*s.outgoing);else std::cout<<"null";std::cout<<'}';}
        std::cout<<"],\"completion\":";if(r.completion){std::cout<<"{\"state\":";state(r.completion->state);std::cout<<",\"origin\":";vec(r.completion->ray.origin);std::cout<<",\"direction\":";vec(r.completion->ray.direction);std::cout<<",\"index\":";bound(r.completion->index);std::cout<<'}';}else std::cout<<"null";std::cout<<"}}";
    }std::cout<<"]}\n";}
void oracle(){
    std::cout<<"id,I,Q,U,V,frame,powerLo,powerHi,xxLo,xxHi,yyLo,yyHi,zzLo,zzHi,xyReLo,xyReHi,xyImLo,xyImHi,xzReLo,xzReHi,xzImLo,xzImHi,yzReLo,yzReHi,yzImLo,yzImHi\n"<<std::hexfloat;
    for(unsigned j=0;j<128;++j){Case c;c.stokes={1+double(j)/128,(int(j%7)-3)/16.0,(int(j%5)-2)/16.0,(int(j%3)-1)/16.0};if(j%2){c.ray.direction=ob::enclose({3,4,0});c.reference={0,0,1};}const auto r=c.run();require(r.status==pr::Status::completed,"Identity oracle corpus failed");const auto&s=r.completion->state;
        std::cout<<j<<','<<c.stokes.i<<','<<c.stokes.q<<','<<c.stokes.u<<','<<c.stokes.v<<','<<j%2;auto emit=[](I x){std::cout<<','<<x.lower()<<','<<x.upper();};emit(s.power);for(I x:s.coherency.diagonal)emit(x);for(auto z:s.coherency.upper){emit(z.real);emit(z.imag);}std::cout<<'\n';
    }
}
}
int main(int argc,char**argv){try{const auto cs=cases();if(argc==2&&std::string(argv[1])=="--fixtures"){json(cs);return 0;}if(argc==2&&std::string(argv[1])=="--oracle"){oracle();return 0;}
    unsigned passed=0;for(const auto&c:cs){const auto r=c.run();if(c.name=="invalid-cone"||c.name=="invalid-reference"||c.name=="invalid-later-shape")require(r.status==pr::Status::invalid_input,"Invalid domain accepted");
        else if(c.name=="uncertain-cone"||c.name=="parallel-reference"||c.name=="near-normal-family")require(r.status==pr::Status::power_unresolved&&!r.completion,"Uncertain input gained completion");
        else if(c.name=="sqrt-budget")require(r.status==pr::Status::budget_exceeded&&!r.completion,"Budget accepted");
        else if(c.name=="geometry-miss"||c.name=="tir-transmission-unavailable"||c.name=="completed-power-prefix"){require(r.status==pr::Status::geometry_failed&&!r.completion,"Geometry failure accepted");if(c.name=="completed-power-prefix")require(r.completed_power_steps==1&&r.segments[0].outgoing.has_value(),"Completed power prefix lost");}
        else if(c.name=="low-refinement")require(r.refinement_limited,"Limited sqrt not reported");
        else {if(r.status!=pr::Status::completed)std::cerr<<c.name<<": "<<int(r.status)<<' '<<r.message<<'\n';require(r.status==pr::Status::completed&&r.completion.has_value(),"Expected completion");require(r.completion->state.power.lower()>=0&&r.completion->state.power.upper()<=c.stokes.i,"Passivity violated");
            if(c.name=="noncoplanar-unpolarized")require(r.completion->state.power.contains(42544.0/17294403.0),"Noncoplanar exact power missing");
            if(c.name=="noncoplanar-u")require(r.completion->state.power.contains(322768.0/259416045.0),"Noncoplanar U exact power missing");
            if(c.name=="two-tir-u"||c.name=="two-tir-v")require(r.completion->state.power.contains(1),"TIR lost power");
            if(c.name=="normal-reflect-u")require(r.completion->state.coherency.upper[0].real.contains(.02),"Normal world U sign flipped");
            if(c.name=="homogeneous-reflect"||c.name=="zero-power")require(r.completion->state.power.upper()==0,"Zero branch gained power");
            if(c.name=="subnormal-v-transmit"||c.name=="subnormal-v-identity")require(r.completion->state.coherency.upper[0].imag.upper()>0,"Subnormal physical half intensity clipped inward");
        }
        ++passed;
    }
    const auto one=rational("reuse",{});require(one.run().status==pr::Status::completed&&one.run().status==pr::Status::completed,"Reuse failed");++passed;
    for(pr::Stokes s:std::vector<pr::Stokes>{{1,1,0,0},{1,-1,0,0},{1,0,1,0},{1,0,0,1}}){auto r=rational("energy",s);r.steps.resize(1);auto t=r;t.steps[0].branch=rt::Branch::transmitted;const auto rr=r.run(),tr=t.run();require(rr.completion&&tr.completion,"Energy branches unresolved");require((rr.completion->state.power+tr.completion->state.power).contains(1),"Reflected/transmitted energy absent");}++passed;
    auto base=rational("basis",{1,0,1,0}),rotated=base;rotated.reference={1,0,0};rotated.stokes.u=-1;const auto br=base.run(),ro=rotated.run();require(ro.completion&&ro.completion->state.power.contains(322768.0/259416045.0),"Rotated source basis changed physical power");for(unsigned k=0;k<3;++k){require(interval::intersection(br.completion->state.coherency.diagonal[k],ro.completion->state.coherency.diagonal[k]).has_value(),"Rotated source basis changed world diagonal");require(interval::intersection(br.completion->state.coherency.upper[k].real,ro.completion->state.coherency.upper[k].real).has_value(),"Rotated source basis changed world real coherence");}++passed;
    const auto circular=simple("normal-reflect-v",{1,0,0,1},rt::Branch::reflected).run();require(circular.completion&&circular.completion->state.coherency.upper[0].imag.contains(.02),"Normal reflection changed world circular sign");++passed;
    std::cout<<"polarized-route: "<<passed<<" groups PASS\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
