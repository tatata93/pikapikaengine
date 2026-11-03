#include "pikapika/optical_selection.hpp"
#include <algorithm>
#include <bit>
#include <cfenv>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
using namespace pikapika;
namespace s=pikapika::optical_selection;
namespace b=pikapika::optical_bounds;
namespace g=pikapika::optical_geometry;
using I=pikapika::interval::Interval;
namespace {
unsigned groups=0;
I p(double v){return I::point(v);}
void check(bool v,const char* message){if(!v)throw std::runtime_error(message);}
void test(const char* name,const std::function<void()>& f){f();++groups;std::cout<<"PASS "<<name<<'\n';}
s::SurfaceRecord disk(std::uint64_t id,double z,double radius=10){return {id,g::PlaneDisk{{0,0,z},{0,0,-1},radius}};}
b::BoundedRay axial(Vec3 origin={},Vec3 direction={0,0,1}){return {b::enclose(origin),b::enclose(direction),0,20};}
struct Case {std::string name;b::BoundedRay ray=axial();std::vector<s::SurfaceRecord> surfaces{disk(20,1),disk(10,3)};s::Settings settings;};
std::vector<Case> cases(){
    std::vector<Case> all;const auto add=[&](std::string name){all.push_back({});all.back().name=std::move(name);return &all.back();};
    add("two-planes");
    auto c=add("all-miss");c->surfaces={disk(1,-1),disk(2,-3)};
    c=add("empty");c->surfaces.clear();
    c=add("sphere-front");c->surfaces={{1,g::FullSphere{{0,0,3},1}},disk(2,4)};
    c=add("cap-second");c->ray=axial({0,0,5},{0,0,-1});c->surfaces={{1,g::SphericalCap{{},{0,0,1},2,1}},disk(2,-1)};
    c=add("self-zero");c->surfaces={disk(1,0),disk(2,1)};
    c=add("sphere-exit");c->ray=axial({0,0,1},{0,0,-1});c->ray.minimum_parameter=1e-6;c->surfaces={{1,g::FullSphere{{},1}}};
    c=add("tiny-neighbor");c->surfaces={disk(1,std::ldexp(1.,-30)),disk(2,1)};
    c=add("explicit-cutoff");c->ray.minimum_parameter=std::ldexp(1.,-29);c->surfaces={disk(1,std::ldexp(1.,-30)),disk(2,1)};
    c=add("order-swap");c->ray.origin[0]=I(-.25,.25);c->surfaces={{1,g::PlaneDisk{{0,0,1},{1,0,1},10}},{2,g::PlaneDisk{{0,0,1},{-1,0,1},10}}};
    c=add("correlated-order");c->ray.direction[2]=I(1,2);c->surfaces={disk(1,2),disk(2,3)};
    c=add("aperture-mixed");c->ray.origin[0]=I(.9,1.1);c->surfaces={disk(1,1,1),disk(2,2)};
    c=add("aperture-outside");c->ray.origin[0]=p(1);c->surfaces={disk(1,1,.5),disk(2,2)};
    c=add("coincident");c->surfaces={disk(1,1),disk(2,1)};
    c=add("tangent");c->surfaces={{1,g::FullSphere{{1,0,1},1}},disk(2,2)};
    c=add("rear-aperture-uncertain");c->ray.origin[0]=I(.9,1.1);c->surfaces={disk(1,1),disk(2,4,1)};
    c=add("prefix-disabled");c->ray.origin[0]=I(.9,1.1);c->surfaces={disk(1,1),disk(2,4,1)};c->settings.allow_prefix_exclusion=false;
    c=add("rear-tangent-uncertain");c->surfaces={disk(1,1),{2,g::FullSphere{{1,0,5},1}}};
    c=add("query-budget");c->settings.max_queries=1;
    c=add("prefix-budget");c->ray.origin[0]=I(.9,1.1);c->surfaces={disk(1,1),disk(2,4,1)};c->settings.max_queries=2;
    c=add("surface-budget");c->settings.max_surfaces=1;
    c=add("total-sqrt-budget");c->ray.direction[0]=p(.125);c->surfaces={{1,g::FullSphere{{0,0,3},1}}};c->settings.max_sqrt_refinements=1;
    c=add("primitive-refinement-budget");c->ray.direction[0]=p(.125);c->surfaces={{1,g::FullSphere{{0,0,3},1}}};c->settings.primitive.max_sqrt_refinements=1;c->settings.primitive.maximum_parameter_width=.01;
    c=add("parameter-width");c->settings.primitive.maximum_parameter_width=1e-20;
    c=add("same-id");c->surfaces={disk(1,1),disk(1,3)};
    c=add("zero-id");c->surfaces[1].id=0;
    c=add("invalid-later-shape");c->surfaces.push_back({30,g::FullSphere{{},-1}});
    c=add("invalid-settings");c->settings.max_queries=0;
    c=add("empty-invalid-ray");c->surfaces.clear();c->ray.minimum_parameter=-1;
    c=add("empty-zero-direction");c->surfaces.clear();c->ray.direction=b::enclose({});
    c=add("parallel-miss");c->surfaces={{1,g::PlaneDisk{{1,0,0},{1,0,0},1}}};
    c=add("upper-boundary");c->ray.maximum_parameter=1;c->surfaces={disk(1,1)};
    c=add("back-face");c->surfaces={{1,g::PlaneDisk{{0,0,1},{0,0,1},1}}};
    return all;
}
const Case& named(const std::vector<Case>& all,const char* name){const auto i=std::find_if(all.begin(),all.end(),[&](const auto& c){return c.name==name;});check(i!=all.end(),"case exists");return *i;}
s::Result run(const std::vector<Case>& all,const char* name){const auto& c=named(all,name);return s::find_nearest(c.ray,c.surfaces,c.settings);}
const s::Selection& selected(const s::Result& r,std::uint64_t id){check(r.status==s::Status::hit&&r.nearest&&r.nearest->id==id,"unique selected surface ID");return *r.nearest;}
void status(const s::Result& r,s::Status expected){check(r.status==expected,"expected status");if(expected!=s::Status::hit)check(!r.nearest,"failed/unresolved query has no selection");}
void tests(){const auto all=cases();
    test("front disk wins independently of stable ID order",[&]{const auto r=run(all,"two-planes");check(selected(r,20).hit.parameter.contains(1),"known t");check(r.surfaces[0].id==10&&r.surfaces[1].id==20&&r.queries==2,"canonical diagnostics");});
    test("permuting caller order preserves geometry and work",[&]{auto c=named(all,"two-planes");const auto a=s::find_nearest(c.ray,c.surfaces);std::reverse(c.surfaces.begin(),c.surfaces.end());const auto z=s::find_nearest(c.ray,c.surfaces);check(a.status==z.status&&a.queries==z.queries&&a.sqrt_refinements==z.sqrt_refinements&&a.nearest->id==z.nearest->id,"permutation invariance");check(a.nearest->hit.parameter.lower()==z.nearest->hit.parameter.lower()&&a.nearest->hit.parameter.upper()==z.nearest->hit.parameter.upper(),"same bounds");});
    test("only all absent surfaces or a validated empty scene miss",[&]{status(run(all,"all-miss"),s::Status::miss);status(run(all,"empty"),s::Status::miss);status(run(all,"parallel-miss"),s::Status::miss);});
    test("sphere nearest is a proved hit not a candidate interval",[&]{check(selected(run(all,"sphere-front"),1).hit.parameter.contains(2),"sphere entry");});
    test("cap rejects first hemisphere root and selects second valid root",[&]{const auto r=run(all,"cap-second");check(selected(r,1).hit.parameter.contains(5),"cap second t");const auto& g=*r.surfaces[0].geometry;check(g.candidates[0].state==b::CandidateState::rejected_cap&&g.candidates[1].state==b::CandidateState::accepted,"cap root diagnostics");});
    test("self plane zero and the same sphere exit are both retained",[&]{check(selected(run(all,"self-zero"),1).hit.parameter.contains(0),"self zero");check(selected(run(all,"sphere-exit"),1).hit.parameter.contains(2),"exit after explicit domain");auto c=named(all,"sphere-exit");c.ray.minimum_parameter=0;status(s::find_nearest(c.ray,c.surfaces),s::Status::unresolved);});
    test("tiny neighbor is visible and explicit cutoff only changes domain",[&]{check(selected(run(all,"tiny-neighbor"),1).hit.parameter.contains(std::ldexp(1.,-30)),"tiny hit");check(selected(run(all,"explicit-cutoff"),2).hit.parameter.contains(1),"cutoff result scoped");});
    test("family order changes cannot be stable ID tie broken",[&]{status(run(all,"order-swap"),s::Status::unresolved);status(run(all,"coincident"),s::Status::unresolved);});
    test("genuine correlated order can remain conservatively unresolved",[&]{status(run(all,"correlated-order"),s::Status::unresolved);});
    test("partial aperture and tangent rivals block a later surface",[&]{status(run(all,"aperture-mixed"),s::Status::unresolved);status(run(all,"tangent"),s::Status::unresolved);check(selected(run(all,"aperture-outside"),2).hit.parameter.contains(2),"uniform aperture miss");});
    test("closed prefix excludes only a proved absent rear uncertainty",[&]{const auto r=run(all,"rear-aperture-uncertain");selected(r,1);check(r.queries==3&&r.prefix_queries==1&&r.surfaces[1].geometry->status==b::Status::unresolved&&r.surfaces[1].prefix->status==b::Status::miss&&r.surfaces[1].excluded_by_prefix,"prefix certificate");status(run(all,"prefix-disabled"),s::Status::unresolved);status(run(all,"rear-tangent-uncertain"),s::Status::unresolved);});
    test("query and surface budgets do not leave a successful unchecked rival",[&]{auto r=run(all,"query-budget");status(r,s::Status::budget_exceeded);check(r.queries==1&&r.surfaces[0].geometry&&!r.surfaces[1].geometry,"unqueried diagnostic");status(run(all,"surface-budget"),s::Status::budget_exceeded);r=run(all,"prefix-budget");status(r,s::Status::budget_exceeded);check(r.queries==2&&r.prefix_queries==0&&!r.surfaces[1].prefix,"prefix not invoked");});
    test("total actual sqrt work and primitive refinement budget fail explicitly",[&]{auto r=run(all,"total-sqrt-budget");status(r,s::Status::budget_exceeded);check(r.sqrt_refinements>1&&r.queries==1&&r.surfaces[0].geometry,"actual work preserved");r=run(all,"primitive-refinement-budget");status(r,s::Status::budget_exceeded);check(r.refinement_limited,"primitive budget diagnosed");});
    test("precision width and parameter boundary are not misses",[&]{status(run(all,"parameter-width"),s::Status::unresolved);status(run(all,"upper-boundary"),s::Status::unresolved);});
    test("all input IDs shapes and settings are preflighted before queries",[&]{for(const char* n:{"same-id","zero-id","invalid-later-shape","invalid-settings","empty-invalid-ray"}){const auto r=run(all,n);status(r,s::Status::invalid_input);check(r.queries==0,"preflight no primitive work");}});
    test("zero direction is unresolved even in an empty scene",[&]{status(run(all,"empty-zero-direction"),s::Status::unresolved);});
    test("back face is a geometric hit rather than implicit culling",[&]{check(!selected(run(all,"back-face"),1).hit.front_face,"back face retained");});
    test("settings domains nonfinite shapes and maximum IDs",[&]{auto c=named(all,"two-planes");c.surfaces[0].id=std::numeric_limits<std::uint64_t>::max();selected(s::find_nearest(c.ray,c.surfaces),c.surfaces[0].id);c.surfaces[1].surface=g::FullSphere{{},std::numeric_limits<double>::infinity()};status(s::find_nearest(c.ray,c.surfaces),s::Status::invalid_input);c=named(all,"two-planes");c.settings.max_surfaces=1025;status(s::find_nearest(c.ray,c.surfaces,c.settings),s::Status::invalid_input);c.settings={};c.settings.max_sqrt_refinements=1000001;status(s::find_nearest(c.ray,c.surfaces,c.settings),s::Status::invalid_input);});
    test("success never mutates caller ray surface or budget settings",[&]{auto c=named(all,"two-planes");for(unsigned k=0;k<3;++k){selected(s::find_nearest(c.ray,c.surfaces,c.settings),20);check(c.surfaces[0].id==20&&c.surfaces[1].id==10&&c.ray.maximum_parameter==20&&c.settings.max_queries==512,"read only/reuse");}});
#if !defined(__EMSCRIPTEN__)
    test("unsupported rounding environment is numerical failure and reusable",[&]{const int old=std::fegetround();check(std::fesetround(FE_UPWARD)==0,"set rounding");const auto r=run(all,"two-planes");std::fesetround(old);status(r,s::Status::numerical_failure);check(r.queries==0,"no unsupported arithmetic");selected(run(all,"two-planes"),20);});
#endif
}
void emit(I i){std::cout<<'['<<i.lower()<<','<<i.upper()<<']';}
void emit(const b::Bounds3& v){std::cout<<'[';for(unsigned k=0;k<3;++k){if(k)std::cout<<',';emit(v[k]);}std::cout<<']';}
void emit(Vec3 v){std::cout<<'['<<v.x<<','<<v.y<<','<<v.z<<']';}
void emit(const b::Hit& h){std::cout<<"{\"parameter\":";emit(h.parameter);std::cout<<",\"distance\":";emit(h.physical_distance);std::cout<<",\"position\":";emit(h.position);std::cout<<",\"geometricNormal\":";emit(h.geometric_normal);std::cout<<",\"incidentNormal\":";emit(h.incident_normal);std::cout<<",\"frontFace\":"<<(h.front_face?"true":"false")<<'}';}
void emit(const b::Result& r){std::cout<<"{\"status\":"<<int(r.status)<<",\"reason\":"<<int(r.reason)<<",\"rootCount\":"<<r.root_count<<",\"consideredCount\":"<<r.considered_count<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"refinementLimited\":"<<(r.refinement_limited?"true":"false")<<",\"discriminant\":";if(r.discriminant)emit(*r.discriminant);else std::cout<<"null";std::cout<<",\"nearest\":";if(r.nearest)emit(*r.nearest);else std::cout<<"null";std::cout<<",\"candidates\":[";for(unsigned j=0;j<2;++j){if(j)std::cout<<',';const auto& c=r.candidates[j];std::cout<<"{\"parameter\":";emit(c.parameter);std::cout<<",\"state\":"<<int(c.state)<<",\"reason\":"<<int(c.reason)<<'}';}std::cout<<"]}";}
void emit(const s::Result& r){std::cout<<"{\"status\":"<<int(r.status)<<",\"queries\":"<<r.queries<<",\"prefixQueries\":"<<r.prefix_queries<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"refinementLimited\":"<<(r.refinement_limited?"true":"false")<<",\"nearest\":";if(r.nearest){std::cout<<"{\"id\":"<<r.nearest->id<<",\"hit\":";emit(r.nearest->hit);std::cout<<'}';}else std::cout<<"null";std::cout<<",\"surfaces\":[";for(std::size_t j=0;j<r.surfaces.size();++j){if(j)std::cout<<',';const auto& d=r.surfaces[j];std::cout<<"{\"id\":"<<d.id<<",\"ordinal\":"<<d.ordinal<<",\"excludedByPrefix\":"<<(d.excluded_by_prefix?"true":"false")<<",\"geometry\":";if(d.geometry)emit(*d.geometry);else std::cout<<"null";std::cout<<",\"prefix\":";if(d.prefix)emit(*d.prefix);else std::cout<<"null";std::cout<<'}';}std::cout<<"]}";}
void fixtures(){std::cout<<std::setprecision(17)<<"{\"version\":1,\"model\":\"uniform static optical surface selection\",\"fixtures\":[";bool first=true;for(const auto& c:cases()){if(!first)std::cout<<',';first=false;std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"ray\":{\"origin\":";emit(c.ray.origin);std::cout<<",\"direction\":";emit(c.ray.direction);std::cout<<",\"minimumParameter\":"<<c.ray.minimum_parameter<<",\"maximumParameter\":"<<c.ray.maximum_parameter<<"},\"settings\":{\"maximumParameterWidth\":"<<c.settings.primitive.maximum_parameter_width<<",\"primitiveMaxSqrtRefinements\":"<<c.settings.primitive.max_sqrt_refinements<<",\"maxSurfaces\":"<<c.settings.max_surfaces<<",\"maxQueries\":"<<c.settings.max_queries<<",\"maxSqrtRefinements\":"<<c.settings.max_sqrt_refinements<<",\"allowPrefixExclusion\":"<<(c.settings.allow_prefix_exclusion?"true":"false")<<"},\"surfaces\":[";bool first_s=true;for(const auto& record:c.surfaces){if(!first_s)std::cout<<',';first_s=false;std::cout<<"{\"id\":"<<record.id<<",\"kind\":"<<record.surface.index()<<",\"center\":";std::visit([](const auto& shape){using T=std::decay_t<decltype(shape)>;if constexpr(std::is_same_v<T,g::PlaneDisk>){emit(shape.center);std::cout<<",\"axis\":";emit(shape.normal);std::cout<<",\"radius\":0,\"aperture\":"<<shape.aperture_radius;}else if constexpr(std::is_same_v<T,g::FullSphere>){emit(shape.center);std::cout<<",\"axis\":[0,0,1],\"radius\":"<<shape.radius<<",\"aperture\":0";}else{emit(shape.vertex);std::cout<<",\"axis\":";emit(shape.axis);std::cout<<",\"radius\":"<<shape.signed_radius<<",\"aperture\":"<<shape.aperture_radius;}},record.surface);std::cout<<'}';}std::cout<<"]},\"result\":";emit(s::find_nearest(c.ray,c.surfaces,c.settings));std::cout<<'}';}std::cout<<"]}\n";}
void hex(double value){std::cout<<std::hex<<std::setfill('0')<<std::setw(16)<<std::bit_cast<std::uint64_t>(value)<<std::dec;}
void oracle(){std::cout<<"kind,k,originLo,originHi,directionLo,directionHi,target,selectedID,status,tLo,tHi,distanceLo,distanceHi,zLo,zHi\n";
    for(unsigned kind=0;kind<3;++kind)for(unsigned k=1;k<=64;++k){const bool cap=kind==2;const double base=double(k+40)/8,lo=cap?base:-base,hi=lo+1./65536,mag=double(k%7+4)/8;const double dl=cap?-mag-1./65536:mag,dh=dl+1./65536;const double target=kind==0?double(k%3+1)/4:kind==1?-double(k%3+1)/4:0;
        b::BoundedRay ray{{p(0),p(0),I(lo,hi)},{p(0),p(0),I(dl,dh)},0,100};std::vector<s::SurfaceRecord> surfaces{disk(2,cap?-4:4)};
        if(kind==0)surfaces.push_back(disk(1,target));else if(kind==1)surfaces.push_back({1,g::FullSphere{{},-target}});else surfaces.push_back({1,g::SphericalCap{{},{0,0,1},2,1}});
        const auto result=s::find_nearest(ray,surfaces);const auto& h=selected(result,1).hit;
        std::cout<<"PSC"[kind]<<','<<k;for(double v:{lo,hi,dl,dh,target}){std::cout<<',';hex(v);}std::cout<<','<<result.nearest->id<<','<<int(result.status);for(I v:{h.parameter,h.physical_distance,h.position[2]}){std::cout<<',';hex(v.lower());std::cout<<',';hex(v.upper());}std::cout<<'\n';
    }
}
}
int main(int argc,char** argv){try{if(argc==2&&std::string(argv[1])=="--fixtures")fixtures();else if(argc==2&&std::string(argv[1])=="--oracle")oracle();else{tests();std::cout<<"Optical selection: "<<groups<<" groups\n";}return 0;}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
