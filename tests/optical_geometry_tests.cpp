#include "pikapika/optical_geometry.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>

using pikapika::Vec3;using namespace pikapika::optical_geometry;
namespace {
unsigned passed=0;
void check(bool v,const char* why){if(!v)throw std::runtime_error(why);}
void test(const char* name,const std::function<void()>& f){f();++passed;std::cout<<"PASS "<<name<<'\n';}
template<class E=std::exception> void rejects(const std::function<void()>& f){bool threw=false;try{f();}catch(const E&){threw=true;}check(threw,"expected rejection");}
bool near(double a,double b,double tolerance=2e-11){return std::abs(a-b)<=tolerance;}
void vec(Vec3 a,Vec3 b){check(near(a.x,b.x)&&near(a.y,b.y)&&near(a.z,b.z),"known vector");}
const Hit& hit(const Result& r,double t){
    check(r.status==Status::hit&&r.reason==Reason::none&&r.nearest.has_value(),"expected certified nearest hit");
    check(r.nearest->parameter.contains(t),"known real parameter in enclosure");
    return *r.nearest;
}
void unknown(const Result& r,Reason reason){check(r.status==Status::unresolved&&r.reason==reason&&!r.nearest,"expected unresolved with no hit");}
void emit(char type,const Ray& ray,Vec3 anchor,Vec3 axis,double radius,double aperture,const Result& r){
    std::cout<<type;
    const auto out=[](double x){std::cout<<','<<std::hex<<std::bit_cast<std::uint64_t>(x)<<std::dec;};
    for(double x:{ray.origin.x,ray.origin.y,ray.origin.z,ray.direction.x,ray.direction.y,ray.direction.z,ray.minimum_parameter,ray.maximum_parameter,anchor.x,anchor.y,anchor.z,axis.x,axis.y,axis.z,radius,aperture})out(x);
    std::cout<<','<<int(r.status)<<','<<int(r.reason)<<','<<r.root_count<<','<<r.considered_count<<','<<bool(r.nearest);
    for(const auto& c:r.candidates){out(c.parameter.lower());out(c.parameter.upper());}
    std::cout<<','<<int(r.candidates[0].state)<<','<<int(r.candidates[1].state);
    for(unsigned i=0;i<3;++i){out(r.nearest?r.nearest->position[i].lower():0);out(r.nearest?r.nearest->position[i].upper():0);}
    out(r.nearest?r.nearest->physical_distance.lower():0);out(r.nearest?r.nearest->physical_distance.upper():0);
    std::cout<<','<<(r.nearest?r.nearest->front_face:false)<<'\n';
}
int oracle(){
    // Fully rational inputs. Cap axes use unit Z or the exact 3-4-5 unit
    // direction, so the independent Fraction checker needs no libm reference.
    for(unsigned j=0;j<64;++j){
        const double k=1+j/16.0,x=(static_cast<int>(j%9)-4)/8.0,z=j/8.0;
        const Ray ray{{x,0,z-3*k},{0,0,k},0,20};
        const PlaneDisk disk{{0,0,z},{0,0,2},1};emit('P',ray,disk.center,disk.normal,0,disk.aperture_radius,intersect(ray,disk));
        const FullSphere sphere{{0,0,z},1};emit('S',ray,sphere.center,{},sphere.radius,0,intersect(ray,sphere));
        const SphericalCap cap{{0,0,z},{0,0,3},2,1};emit('C',ray,cap.vertex,cap.axis,cap.signed_radius,cap.aperture_radius,intersect(ray,cap));
    }
    for(double y:{0.0,0.5,1.0,1.0-1e-6,1.0+1e-6,2.0}){
        const Ray ray{{-3,y,0},{1,0,0},0,10};const FullSphere s{};emit('S',ray,s.center,{},s.radius,0,intersect(ray,s));
    }
    const SphericalCap cap{{},{0,0,1},5,3};const Ray back{{-8,0,4},{4,0,-2},0,4};emit('C',back,cap.vertex,cap.axis,5,3,intersect(back,cap));
    const SphericalCap rotated{{1,2,3},{0,3,4},5,1};const Ray rotated_ray{{1,-4,-5},{0,3,4},0,10};emit('C',rotated_ray,rotated.vertex,rotated.axis,5,1,intersect(rotated_ray,rotated));
    return 0;
}
}
int main(int argc,char** argv){try{
    if(argc==2&&std::string_view(argv[1])=="--oracle")return oracle();
    test("plane disk parameter differs from physical distance",[]{
        const auto r=intersect({{0,0,-6},{0,0,2},0,10},PlaneDisk{});const auto& h=hit(r,3);
        check(h.physical_distance.contains(6),"distance6m");vec(h.position_estimate,{0,0,0});vec(h.geometric_normal_estimate,{0,0,1});
        check(!h.front_face,"backside plane");vec(h.incident_normal_estimate,{0,0,-1});
        check(h.position[0].contains(0)&&h.position[1].contains(0)&&h.position[2].contains(0),"true hit position enclosed");
    });
    test("plane front and back are both valid with incident side normal",[]{
        const auto r=intersect({{0,0,3},{0,0,-1},0,10},PlaneDisk{});const auto& h=hit(r,3);check(h.front_face,"front plane");vec(h.incident_normal_estimate,{0,0,1});
        const auto reversed=intersect({{0,0,3},{0,0,-1},0,10},PlaneDisk{{},{0,0,-2},1});check(!hit(reversed,3).front_face,"normal reversal changes side");
    });
    test("plane translation tilted normal and direction scaling",[]{
        const PlaneDisk disk{{2,3,4},{0,3,4},2};
        const auto r0=intersect({{2,9,12},{0,-3,-4},0,10},disk);const auto& h=hit(r0,2);
        vec(h.position_estimate,{2,3,4});check(h.physical_distance.contains(10),"tilted distance10");
        const auto r=intersect({{2,9,12},{0,-6,-8},0,10},disk);hit(r,1);vec(r.nearest->position_estimate,{2,3,4});
    });
    test("parallel miss and coplanar ambiguity are not silently biased",[]{
        const auto a=intersect({{0,0,1},{1,0,0},0,10},PlaneDisk{});check(a.status==Status::miss&&a.reason==Reason::parallel,"parallel miss");
        unknown(intersect({{0,0,0},{1,0,0},0,10},PlaneDisk{}),Reason::parallel_or_coplanar);
    });
    test("circular aperture interior exterior and boundary",[]{
        hit(intersect({{0.5,0,2},{0,0,-1},0,10},PlaneDisk{}),2);
        const auto outside=intersect({{1.1,0,2},{0,0,-1},0,10},PlaneDisk{});
        check(outside.status==Status::miss&&outside.candidates[0].state==CandidateState::rejected_aperture,"outside disk");
        unknown(intersect({{1,0,2},{0,0,-1},0,10},PlaneDisk{}),Reason::aperture_boundary);
        unknown(intersect({{std::nextafter(1.0,0.0),0,2},{0,0,-1},0,10},PlaneDisk{}),Reason::aperture_boundary);
    });
    test("full sphere ordered roots and true normal bounds",[]{
        const auto r=intersect({{0,0,-3},{0,0,1},0,10},FullSphere{});const auto& h=hit(r,2);
        check(r.root_count==2&&r.considered_count==1&&r.candidates[1].parameter.contains(4),"ordered roots2,4");
        check(h.front_face&&h.geometric_normal[2].contains(-1),"sphere outward front normal");vec(h.position_estimate,{0,0,-1});
    });
    test("sphere inside exit and roots behind requested ray",[]{
        const auto r=intersect({{0,0,0},{1,0,0},0,10},FullSphere{});check(!hit(r,1).front_face,"inside exit backside");
        check(r.candidates[0].state==CandidateState::rejected_parameter,"negative root excluded");
        const auto behind=intersect({{0,0,0},{1,0,0},0,10},FullSphere{{-3,0,0},1});check(behind.status==Status::miss,"behind miss within domain");
    });
    test("sphere translation scaling and nonunit ray",[]{
        const FullSphere s{{5,-2,4},2};
        const auto r=intersect({{5,-2,-6},{0,0,4},0,10},s);const auto& h=hit(r,2);check(h.physical_distance.contains(8),"translated distance8");vec(h.position_estimate,{5,-2,2});
    });
    test("tangent and neighboring rounded configurations remain conservative",[]{
        unknown(intersect({{-2,1,0},{1,0,0},0,10},FullSphere{}),Reason::tangent_or_discriminant);
        const auto near_tangent=intersect({{-2,std::nextafter(1.0,0.0),0},{1,0,0},0,10},FullSphere{});check(near_tangent.status==Status::unresolved&&!near_tangent.nearest,"adjacent tangent ambiguity");
        const auto outside=intersect({{-2,1+1e-6,0},{1,0,0},0,10},FullSphere{});check(outside.status==Status::miss&&outside.reason==Reason::no_real_roots,"outside tangent proof");
        const auto inside=intersect({{-2,1-1e-6,0},{1,0,0},0,10},FullSphere{});check(inside.status==Status::hit,"inside tangent nonzero margin");
    });
    test("vertex centered cap rejects opposite sphere hemisphere",[]{
        const SphericalCap cap{{},{0,0,1},2,0.5};const Ray ray{{0,0,5},{0,0,-1},0,10};
        const auto full=intersect(ray,FullSphere{{0,0,2},2});hit(full,1);
        const auto r=intersect(ray,cap);const auto& h=hit(r,5);
        check(r.considered_count==2&&r.candidates[0].state==CandidateState::rejected_cap,"first hemisphere rejected");
        vec(h.position_estimate,{0,0,0});check(!h.front_face,"cap backside accepted");
    });
    test("cap skips aperture rejected near root and takes nearest valid second root",[]{
        const auto r=intersect({{-8,0,4},{4,0,-2},0,4},SphericalCap{{},{0,0,1},5,3});
        const auto& h=hit(r,2);check(r.candidates[0].parameter.contains(1)&&r.candidates[0].state==CandidateState::rejected_aperture,"near root aperture reject");vec(h.position_estimate,{0,0,0});
    });
    test("signed curvature and exact mathematical axis normalization",[]{
        const auto r=intersect({{0,0,3},{0,0,-1},0,10},SphericalCap{{},{0,0,7},-2,0.5});hit(r,3);vec(r.nearest->geometric_normal_estimate,{0,0,1});
        const auto rotated=intersect({{1,-4,-5},{0,3,4},0,10},SphericalCap{{1,2,3},{0,3,4},5,1});const auto& h=hit(rotated,2);vec(h.position_estimate,{1,2,3});check(h.physical_distance.contains(10),"axis normalized real distance");
    });
    test("self hit is retained or unresolved until caller gives explicit cutoff",[]{
        const Ray ray{{0,0,-1},{0,0,1},0,4};unknown(intersect(ray,FullSphere{}),Reason::parameter_boundary);
        auto cutoff=ray;cutoff.minimum_parameter=1e-6;const auto r=intersect(cutoff,FullSphere{});hit(r,2);check(r.candidates[0].state==CandidateState::rejected_parameter,"explicitly excluded self interval");
        const auto plane=intersect({{0,0,0},{0,0,1},0,4},PlaneDisk{});hit(plane,0);
        check(intersect({{0,0,0},{0,0,1},1e-6,4},PlaneDisk{}).status==Status::miss,"explicit plane origin cutoff");
    });
    test("near origin real hit is not lost to an implicit epsilon",[]{
        const double delta=0x1p-20;const auto r=intersect({{0,0,-1-delta},{0,0,1},0,4},FullSphere{});hit(r,delta);
        const auto skipped=intersect({{0,0,-1-delta},{0,0,1},2e-6,4},FullSphere{});hit(skipped,2+delta);
        const auto boundary=intersect({{0,0,-3},{0,0,1},2,4},FullSphere{});unknown(boundary,Reason::parameter_boundary);
    });
    test("precision and square root budgets yield explicit unresolved",[]{
        const auto precise=intersect({{0,0,-3},{0,0,1},0,10},FullSphere{},Settings{1e-30,128});unknown(precise,Reason::precision_limit);
        const auto budget=intersect({{0,0,-3},{0,0,1},0,10},FullSphere{},Settings{1e-8,1});check(budget.status==Status::unresolved&&budget.refinement_limited&&budget.reason==Reason::refinement_budget,"sqrt budget unresolved");
    });
    test("finite invalid domain and budget rejection",[]{
        const double nan=std::numeric_limits<double>::quiet_NaN(),inf=std::numeric_limits<double>::infinity();
        for(const Ray ray:std::array<Ray,6>{{{{nan,0,0},{1,0,0},0,10},{{},{0,0,0},0,10},{{},{1,0,0},-1,10},{{},{1,0,0},2,1},{{},{inf,0,0},0,10},{{},{1,0,0},0,inf}}})rejects<std::invalid_argument>([&]{intersect(ray,FullSphere{});});
        rejects<std::invalid_argument>([]{intersect(Ray{},FullSphere{{},0});});rejects<std::invalid_argument>([]{intersect(Ray{},PlaneDisk{{},{},1});});
        rejects<std::invalid_argument>([]{intersect(Ray{},SphericalCap{{},{0,0,1},1,2});});
        rejects<std::invalid_argument>([]{intersect(Ray{},FullSphere{},Settings{0,128});});rejects<std::invalid_argument>([]{intersect(Ray{},FullSphere{},Settings{1e-8,0});});
    });
    std::cout<<"OPTICAL GEOMETRY PASS "<<passed<<" groups\n";return 0;
}catch(const std::exception& e){std::cerr<<"OPTICAL GEOMETRY FAIL: "<<e.what()<<'\n';return 1;}}
