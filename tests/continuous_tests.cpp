#include "pikapika/continuous.hpp"
#include <algorithm>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>

using pikapika::Vec3;
using namespace pikapika::continuous;
namespace {
unsigned passed=0,analytic_cases=0;
double maximum_time_error=0,maximum_normal_error=0,maximum_residual=0;
Vec3 add(Vec3 a,Vec3 b) { return {a.x+b.x,a.y+b.y,a.z+b.z}; }
Vec3 sub(Vec3 a,Vec3 b) { return {a.x-b.x,a.y-b.y,a.z-b.z}; }
Vec3 mul(Vec3 a,double s) { return {a.x*s,a.y*s,a.z*s}; }
double length(Vec3 a) { return std::hypot(a.x,a.y,a.z); }
void check(bool ok,const char* message) { if(!ok)throw std::runtime_error(message); }
bool near(double a,double b,double tolerance=1e-12) { return std::abs(a-b)<=tolerance; }
void vector_near(Vec3 a,Vec3 b,double tolerance=1e-12) { check(length(sub(a,b))<=tolerance,"normal/vector tolerance"); }
void finite_result(const ToiResult& r) {
    check(std::isfinite(r.initial_gap)&&std::isfinite(r.initial_normal_speed)&&std::isfinite(r.normal_speed),"successful scalar output must be finite");
    check(std::isfinite(r.normal.x)&&std::isfinite(r.normal.y)&&std::isfinite(r.normal.z),"successful normal must be finite");
    check(!r.time||std::isfinite(*r.time),"successful time must be finite");
    if(r.normal_valid)check(near(length(r.normal),1,5e-15),"valid normal must have unit length");
}
void rejects(const std::function<void()>& body) { bool threw=false;try{body();}catch(const std::exception&){threw=true;}check(threw,"invalid input must throw"); }
void test(const char* name,const std::function<void()>& body) { body();++passed;std::cout<<"PASS "<<name<<'\n'; }
void known(const ToiResult& result,double time,Vec3 normal,double tolerance=1e-12) {
    finite_result(result);
    check(result.time.has_value(),"expected event time");
    const double time_error=std::abs(*result.time-time),normal_error=length(sub(result.normal,normal));
    maximum_time_error=std::max(maximum_time_error,time_error);
    maximum_normal_error=std::max(maximum_normal_error,normal_error);++analytic_cases;
    check(time_error<=tolerance,"known contact time");check(result.normal_valid,"known contact normal must exist");
    check(normal_error<=tolerance,"known contact normal");
}
void residual(const MovingSphere& a,const MovingSphere& b,const ToiResult& result,double tolerance=2e-12) {
    check(result.time.has_value(),"residual needs a hit");
    const Vec3 r=sub(b.center,a.center),v=sub(b.velocity,a.velocity);
    const Vec3 contact{std::fma(v.x,*result.time,r.x),std::fma(v.y,*result.time,r.y),std::fma(v.z,*result.time,r.z)};
    const double error=std::abs(length(contact)-(a.radius+b.radius))/(a.radius+b.radius);
    maximum_residual=std::max(maximum_residual,error);check(error<=tolerance,"contact surface residual");
}
}
int main() {
    try {
        test("sphere-plane analytic vertical entry and SI normal speed",[]{
            auto r=sphere_plane({{0,10,0},{0,-3,0},1},{},4);
            known(r,3,{0,1,0});check(r.kind==ContactKind::impact,"plane impact");
            check(r.initial_motion==Motion::approaching&&near(r.initial_gap,9)&&near(r.normal_speed,-3),"plane initial quantities");
        });
        test("translating inclined plane uses relative normal velocity",[]{
            const Vec3 n{0.6,0.8,0};
            MovingSphere sphere{mul(n,12),add(mul(n,-4),{0,0,17}),2};
            MovingPlane plane{n,3,mul(n,-1)};
            auto r=sphere_plane(sphere,plane,3);known(r,7./3,n);
            plane.normal=mul(n,1+5e-13);plane.offset=3*(1+5e-13);
            known(sphere_plane(sphere,plane,3),7./3,n);
        });
        test("two moving spheres head-on unequal velocities",[]{
            MovingSphere a{{-5,0,0},{3,0,0},1},b{{5,0,0},{-1,0,0},1};
            auto r=sphere_sphere(a,b,3);known(r,2,{1,0,0});residual(a,b,r);
            check(r.kind==ContactKind::impact&&near(r.initial_gap,8)&&near(r.normal_speed,-4),"relative speed");
        });
        test("oblique 3D entry has actual contact normal",[]{
            MovingSphere a{{0,0,0},{0,0,0},2},b{{-10,1.8,2.4},{2,0,0},3};
            auto r=sphere_sphere(a,b,4);known(r,3,{-0.8,0.36,0.48});residual(a,b,r);
            check(near(r.normal_speed,-1.6),"oblique normal closing speed");
        });
        test("fast crossing is detected despite separated endpoints",[]{
            MovingSphere a{{-100,0,0},{20000,0,0},1},b{{0,0,0},{0,0,0},1};
            auto r=sphere_sphere(a,b,0.01);known(r,0.0049,{1,0,0});residual(a,b,r,2e-14);
            check(length(sub(add(a.center,mul(a.velocity,0.01)),b.center))>a.radius+b.radius,"endpoint remains separated");
            known(sphere_plane({{0,100,0},{0,-1e9,0},0.25},{},1e-6),99.75/1e9,{0,1,0});
        });
        test("tangent and clearly missed trajectories remain distinct",[]{
            MovingSphere a{{0,0,0},{},0.5},b{{-3,1,0},{1,0,0},0.5};
            auto r=sphere_sphere(a,b,4);known(r,3,{0,1,0});
            check(r.kind==ContactKind::grazing&&r.roundoff_sensitive,"exact tangent boundary");
            b.center.y=1.001;r=sphere_sphere(a,b,4);check(r.kind==ContactKind::none&&!r.time,"clear miss");
            b.center.y=std::nextafter(1.,2.);r=sphere_sphere(a,b,4);
            check(r.kind==ContactKind::uncertain&&r.roundoff_sensitive&&r.time,"near-miss is explicitly uncertain");
        });
        test("initial sphere overlap reports approach separation and missing coincident normal",[]{
            MovingSphere a{{0,0,0},{},1},b{{1,0,0},{-1,0,0},1};
            auto r=sphere_sphere(a,b,0);known(r,0,{1,0,0});
            check(r.kind==ContactKind::initial_overlap&&r.initial_motion==Motion::approaching&&r.at_horizon,"initial approach");
            b.velocity={1,0,0};r=sphere_sphere(a,b,1);check(r.kind==ContactKind::initial_overlap&&r.initial_motion==Motion::separating,"overlap remains overlap when separating");
            b.velocity={};r=sphere_sphere(a,b,1);check(r.initial_motion==Motion::stationary,"stationary overlap");
            b.center={};b.velocity={0,1,0};r=sphere_sphere(a,b,1);
            check(r.kind==ContactKind::initial_overlap&&!r.normal_valid&&r.initial_motion==Motion::separating,"coincident centres right derivative");vector_near(r.normal,{});
        });
        test("initial touching and solid plane half-space semantics",[]{
            auto r=sphere_plane({{0,1,0},{1,0,0},1},{},0);
            check(r.kind==ContactKind::initial_touch&&r.initial_motion==Motion::tangential&&r.at_horizon,"touching tangent plane");
            r=sphere_plane({{0,-20,0},{0,3,0},1},{},1);
            check(r.kind==ContactKind::initial_overlap&&r.initial_motion==Motion::separating&&*r.time==0,"plane solid is negative halfspace");
            r=sphere_sphere({{},{},1},{{2,0,0},{1,0,0},1},1);
            check(r.kind==ContactKind::initial_touch&&r.initial_motion==Motion::separating&&*r.time==0,"initial sphere touch takes priority over exit");
        });
        test("horizon is closed with explicit roundoff boundary",[]{
            MovingSphere a{{},{},1},b{{6,0,0},{-2,0,0},1};
            auto r=sphere_sphere(a,b,2);known(r,2,{1,0,0});check(r.at_horizon,"sphere horizon included");
            check(sphere_sphere(a,b,1.99).kind==ContactKind::none,"sphere after horizon");
            check(sphere_sphere(a,b,2.01).kind==ContactKind::impact,"sphere before horizon");
            r=sphere_sphere(a,b,std::nextafter(2.,0.));check(r.kind==ContactKind::uncertain&&r.at_horizon,"ulp outside is not definite impact");
            r=sphere_plane({{0,5,0},{0,-2,0},1},{},2);known(r,2,{0,1,0});check(r.at_horizon,"plane horizon included");
            check(sphere_plane({{0,5,0},{0,-2,0},1},{},1.99).kind==ContactKind::none,"plane after horizon");
        });
        test("zero horizon stationary separating and tangential misses",[]{
            MovingSphere a{{},{},1},b{{6,0,0},{-2,0,0},1};
            check(sphere_sphere(a,b,0).kind==ContactKind::none,"zero horizon future event absent");
            b.velocity={};check(sphere_sphere(a,b,100).kind==ContactKind::none,"stationary separated");
            b.velocity={1,0,0};check(sphere_sphere(a,b,100).kind==ContactKind::none,"separating separated");
            b.velocity={0,1,0};check(sphere_sphere(a,b,100).kind==ContactKind::none,"tangential separated");
            check(sphere_plane({{0,3,0},{2,0,0},1},{},100).kind==ContactKind::none,"parallel plane motion");
        });
        test("spatial and temporal scaling preserve analytic answer",[]{
            for(double scale:{1e-9,1e-6,1.,1e6,1e9}) {
                MovingSphere a{{},{},2*scale},b{{-10*scale,1.8*scale,2.4*scale},{2*scale,0,0},3*scale};
                auto r=sphere_sphere(a,b,4);known(r,3,{-0.8,0.36,0.48},4e-12);residual(a,b,r);
                known(sphere_plane({{0,10*scale,0},{0,-3*scale,0},scale},{},4),3,{0,1,0},4e-12);
            }
            for(double rate:{1e-5,1.,1e6}) {
                auto r=sphere_sphere({{},{},1},{{6,0,0},{-2*rate,0,0},1},3/rate);
                check(r.time&&near(*r.time*rate,2,1e-12),"time unit scaling");
            }
        });
        test("common translation and Galilean boosts preserve relative result",[]{
            const Vec3 shift{1000,-2000,500},boost{50,-80,13};
            MovingSphere a{{0,0,0},{1,2,3},2},b{{-10,1.8,2.4},{3,2,3},3};
            auto original=sphere_sphere(a,b,4);
            a.center=add(a.center,shift);b.center=add(b.center,shift);a.velocity=add(a.velocity,boost);b.velocity=add(b.velocity,boost);
            auto changed=sphere_sphere(a,b,4);check(changed.kind==original.kind,"boost kind");
            check(near(*changed.time,*original.time,2e-13),"Galilean time");vector_near(changed.normal,original.normal,2e-13);
            MovingPlane plane{{0.6,0.8,0},3,{1,2,3}};MovingSphere sphere{{12,16,0},{-2,-2,4},2};
            original=sphere_plane(sphere,plane,10);sphere.center=add(sphere.center,shift);sphere.velocity=add(sphere.velocity,boost);
            plane.offset+=0.6*shift.x+0.8*shift.y;plane.velocity=add(plane.velocity,boost);
            changed=sphere_plane(sphere,plane,10);check(near(*changed.time,*original.time,3e-13),"plane Galilean/translation time");vector_near(changed.normal,original.normal);
        });
        test("sphere argument exchange reverses normal and preserves time",[]{
            MovingSphere a{{2,1,-3},{1,2,3},2},b{{-8,2.8,-0.6},{3,2,3},3};
            auto ab=sphere_sphere(a,b,4),ba=sphere_sphere(b,a,4);
            check(ab.kind==ba.kind&&ab.time&&ba.time&&near(*ab.time,*ba.time),"exchange time/status");
            vector_near(ab.normal,mul(ba.normal,-1));check(ab.initial_motion==ba.initial_motion&&near(ab.normal_speed,ba.normal_speed),"exchange speed");
        });
        test("stable entry root retains near-start and distant head-on hits",[]{
            MovingSphere a{{},{},0.5},b{{1+1e-10,0,0},{-1,0,0},0.5};
            const double expected=b.center.x-1;auto r=sphere_sphere(a,b,1);
            check(r.time&&std::abs(*r.time-expected)<=expected*1e-12,"small root relative accuracy");residual(a,b,r);
            b.center={1e9,0,0};b.velocity={-1e9,0,0};known(sphere_sphere(a,b,2),1-1e-9,{1,0,0},3e-15);
            // No squaring of the absolute 1e12 coordinate or subtraction of b^2-ac.
            a.center={-1e12,0,0};b.center={1e12,0,0};a.velocity={1e12,0,0};b.velocity={-1e12,0,0};
            known(sphere_sphere(a,b,2),1-5e-13,{1,0,0},3e-15);
        });
        test("subnormal input normalization avoids reciprocal overflow",[]{
            MovingSphere a{{},{},1e-310},b{{6e-310,0,0},{-2e-310,0,0},1e-310};
            auto r=sphere_sphere(a,b,3);check(r.kind==ContactKind::impact&&r.time&&std::isfinite(*r.time),"subnormal finite hit");
            check(near(*r.time,2,1e-12)&&r.normal_valid,"subnormal scaled analytic time");vector_near(r.normal,{1,0,0});
            const double tiny=1e-320,smallest=std::numeric_limits<double>::denorm_min();
            for(Vec3 position:{Vec3{tiny,0,0},Vec3{tiny,tiny,tiny},Vec3{smallest,smallest,smallest},Vec3{2*tiny,0,0}}) {
                r=sphere_sphere({{},{},tiny},{position,{},tiny},0);finite_result(r);
                check(r.kind==ContactKind::initial_overlap||r.kind==ContactKind::initial_touch,"subnormal initial event");
            }
            const double normal_min=std::numeric_limits<double>::min();
            MovingSphere c{{},{normal_min,0,0},tiny},d{{6*tiny,0,0},{std::nextafter(normal_min,0.),0,0},tiny};
            r=sphere_sphere(c,d,1e5);finite_result(r);
            check(r.kind==ContactKind::impact&&r.roundoff_sensitive&&r.time,"subnormal relative velocity after cancellation");
            vector_near(r.normal,{1,0,0});
        });
        test("independent chord family checks contact surface and correct entry branch",[]{
            for(double radius:{0.25,1.,5.,100.})for(double yratio:{0.,0.2,0.6})for(double zratio:{0.,0.3,0.5})for(double speed:{0.1,1.,77.}) {
                const double y=radius*yratio,z=radius*zratio,chord=std::sqrt(radius*radius-y*y-z*z),start=10*radius;
                MovingSphere a{{},{},radius*0.4},b{{-start,y,z},{speed,0,0},radius*0.6};
                const double expected=(start-chord)/speed;auto r=sphere_sphere(a,b,expected*1.1);
                known(r,expected,{-chord/radius,y/radius,z/radius},3e-11);residual(a,b,r,3e-14);
                check(r.normal_speed<0&&r.kind==ContactKind::impact,"must use entry branch");
            }
        });
        test("invalid and overflow-prone input rejected before arithmetic",[]{
            const double inf=std::numeric_limits<double>::infinity(),nan=std::numeric_limits<double>::quiet_NaN();
            MovingSphere good;
            for(double bad:{inf,-inf,nan,1e308,-1e308,1e12+1}) {
                rejects([&]{auto s=good;s.center.x=bad;(void)sphere_sphere(s,good,1);});
                rejects([&]{auto s=good;s.velocity.y=bad;(void)sphere_plane(s,{},1);});
                rejects([&]{auto p=MovingPlane{};p.offset=bad;(void)sphere_plane(good,p,1);});
            }
            for(double bad:{0.,-1.,inf,nan})rejects([&]{auto s=good;s.radius=bad;(void)sphere_sphere(s,good,1);});
            for(double bad:{-1.,1e6+1,inf,nan})rejects([&]{(void)sphere_sphere(good,good,bad);});
            for(Vec3 bad:{Vec3{},Vec3{0,2,0},Vec3{nan,1,0}})rejects([&]{MovingPlane p;p.normal=bad;(void)sphere_plane(good,p,1);});
            rejects([&]{(void)sphere_sphere({{},{},1e-200},{{1,0,0},{-1,0,0},1e-200},2);});
            rejects([&]{(void)sphere_plane({{0,2e-320,0},{0,-1e12,0},1e-320},{},1);});
            // Query functions are stateless; an invalid query does not poison later use.
            known(sphere_plane({{0,10,0},{0,-3,0},1},{},4),3,{0,1,0});
        });
        std::cout<<std::setprecision(17)<<"RESULT groups="<<passed<<" analytic_cases="<<analytic_cases
                 <<" max_time_abs_error_s="<<maximum_time_error<<" max_normal_error="<<maximum_normal_error
                 <<" max_surface_relative_residual="<<maximum_residual<<'\n';
        return 0;
    } catch(const std::exception& e) {std::cerr<<"FAIL after "<<passed<<" groups: "<<e.what()<<'\n';return 1;}
}
