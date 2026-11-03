#include "pikapika/dynamics.hpp"
#include "../core/src/dynamics_internal.hpp"
#include <bit>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace pikapika;
using namespace pikapika::dynamics;
namespace {
void vector_out(std::ostream& out,Vec3 v) {out<<v.x<<','<<v.y<<','<<v.z;}
void body_out(std::ostream& out,const RigidBody& b) {
    out<<'['<<b.id<<','<<(b.is_static?1:0)<<','<<b.mass<<','<<b.radius<<',';vector_out(out,b.inertia_diagonal);
    out<<',';vector_out(out,b.position);out<<','<<b.orientation.x<<','<<b.orientation.y<<','<<b.orientation.z<<','<<b.orientation.w;
    out<<',';vector_out(out,b.velocity);out<<',';vector_out(out,b.angular_momentum);out<<',';vector_out(out,b.force);
    out<<',';vector_out(out,b.torque);out<<','<<b.material.restitution<<','<<b.material.friction<<']';
}
void state_out(std::ostream& out,const World& world,const StepStats& stats={}) {
    out<<"{\"bodies\":[";bool comma=false;
    for(const auto& b:world.bodies()){if(comma)out<<',';comma=true;body_out(out,b);}
    out<<"],\"stats\":["<<stats.contacts<<','<<stats.velocity_iterations<<','<<stats.max_penetration<<','
       <<stats.normal_impulse_sum<<','<<stats.friction_impulse_sum<<','<<stats.max_closing_residual<<"]}";
}
void fixture(const char* name,World world,unsigned ticks,double dt,const SolverSettings& settings={},bool reapply=false) {
    std::cout<<"{\"name\":\""<<name<<"\",\"dt\":"<<dt<<",\"ticks\":"<<ticks<<",\"states\":[";state_out(std::cout,world);
    for(unsigned i=0;i<ticks;++i) {
        if(reapply)for(const auto& b:world.bodies())if(!b.is_static) {
            world.apply_force(b.id,{0.4,-0.3,0.2},b.position+Vec3{0.1,0.2,0.3});
            world.apply_torque(b.id,{0.01,-0.02,0.03});
        }
        const auto stats=world.step(dt,settings);std::cout<<',';state_out(std::cout,world,stats);
    }
    std::cout<<"]}";
}
void fixtures() {
    std::cout<<std::setprecision(17)<<"{\"fixtureVersion\":1,\"cases\":[";
    World free;free.gravity={0.1,-9.8,0.3};auto b=make_sphere(1,1,2,{10,100,20});b.inertia_diagonal={2,3,4};
    b.velocity={2,3,4};b.angular_momentum={0.2,0.3,0.4};b.force={6,-4,2};b.torque={0.7,0.8,-0.5};free.add_body(b);
    fixture("loadedFree",free,16,1./120,{},true);std::cout<<',';
    World plane;plane.add_plane({100,{0,1,0},0,{0.5,0.6}});b=make_sphere(1,1,2,{0,1,0});b.velocity={4,-3,0.7};
    b.inertia_diagonal={0.7,0.9,1.1};b.angular_momentum={0.1,0.2,0.3};b.material={0.5,0.6};plane.add_body(b);
    fixture("obliqueFrictionPlane",plane,24,1./240);std::cout<<',';
    World pair;pair.gravity={};b=make_sphere(1,1,1,{-0.95,0,0});b.velocity={3,0.2,0};b.material={0.8,0.5};pair.add_body(b);
    b=make_sphere(2,1,2,{0.95,0,0});b.velocity={-1,-0.3,0};b.material={0.8,0.5};pair.add_body(b);
    fixture("unequalPairProjection",pair,12,1./120);std::cout<<',';
    SolverSettings no_projection;no_projection.position_correction=0;
    fixture("unequalPairNoProjection",pair,12,1./120,no_projection);std::cout<<',';
    World stack;stack.add_plane({100});for(unsigned i=0;i<3;++i)stack.add_body(make_sphere(i+1,1,1,{0,1.+2*i,0}));
    SolverSettings stack_settings;stack_settings.velocity_iterations=64;fixture("restingStack",stack,48,1./240,stack_settings);std::cout<<',';
    World static_loads;static_loads.gravity={};b=make_sphere(1,1,3,{100,100,100},true);b.force={5,6,7};b.torque={8,9,10};static_loads.add_body(b);
    b=make_sphere(2,1,2);b.force={1,2,3};b.torque={0,0,0.5};static_loads.add_body(b);fixture("staticAndDynamicLoadConsumption",static_loads,4,0.02);std::cout<<',';
    World rotation;rotation.gravity={};b=make_sphere(1,1,1);b.inertia_diagonal={2,3,4};b.angular_momentum={1.1,2.2,3.3};rotation.add_body(b);
    fixture("anisotropicGyroscopicRotation",rotation,240,1./120);std::cout<<',';
    World mixed;mixed.add_plane({100});
    for(unsigned i=0;i<8;++i){b=make_sphere(i+1,0.5,1+0.25*(i%3),{double(i%4)*0.95,0.5+0.9*(i/4),0});
        b.inertia_diagonal={0.1,0.14,0.18};b.velocity={0.1*double(int(i%3)-1),-0.1,0.05};b.angular_momentum={0.001,0.002,0.003};mixed.add_body(b);}
    fixture("multipleContactsAndHeldLoads",mixed,48,1./120,{},true);std::cout<<"]}\n";
}

#ifndef PP_DYNAMICS_BASELINE_ONLY
unsigned passed=0;
void check(bool condition,const char* message) {if(!condition)throw std::runtime_error(message);}
bool near(double a,double b,double tolerance=1e-12) {return std::abs(a-b)<=tolerance;}
void vector_near(Vec3 a,Vec3 b,double tolerance=1e-12) {check((a-b).length()<=tolerance,"vector tolerance");}
void exact(double a,double b) {check(std::bit_cast<std::uint64_t>(a)==std::bit_cast<std::uint64_t>(b),"bitwise scalar invariant");}
void exact(Vec3 a,Vec3 b) {exact(a.x,b.x);exact(a.y,b.y);exact(a.z,b.z);}
void exact(Quaternion a,Quaternion b) {exact(a.x,b.x);exact(a.y,b.y);exact(a.z,b.z);exact(a.w,b.w);}
std::string snapshot(const World& world) {std::ostringstream out;out<<std::setprecision(17);state_out(out,world);return out.str();}
void rejects(const std::function<void()>& operation) {bool threw=false;try{operation();}catch(const std::exception&){threw=true;}check(threw,"expected failure");}
void test(const char* name,const std::function<void()>& operation) {operation();++passed;std::cout<<"PASS "<<name<<'\n';}
RigidBody loaded() {
    auto b=make_sphere(1,1,2,{1,2,3});b.inertia_diagonal={2,3,4};b.velocity={2,3,4};
    b.angular_momentum={0,0,1.2};b.force={6,4,-2};b.torque={0,0,8};return b;
}
void analytical_loaded(const RigidBody& b,double t) {
    const Vec3 acceleration{3,-8,-1};vector_near(b.position,Vec3{1,2,3}+Vec3{2,3,4}*t+acceleration*(0.5*t*t));
    vector_near(b.velocity,Vec3{2,3,4}+acceleration*t);vector_near(b.angular_momentum,{0,0,1.2+8*t});
    const double angle=0.3*t+t*t;vector_near(b.orientation.rotate({1,0,0}),{std::cos(angle),std::sin(angle),0});
}
void tests() {
    test("free propagation keeps held loads and matches force torque analytic solution",[]{
        auto b=loaded();const auto original=b;detail::propagate_free(b,{0,-10,0},0.05,0.5);analytical_loaded(b,0.05);
        exact(b.force,original.force);exact(b.torque,original.torque);check(b.id==original.id,"body identity");
    });
    test("two free intervals reuse held loads without consuming or duplicating them",[]{
        auto split=loaded(),whole=split;detail::propagate_free(split,{0,-10,0},0.02,0.5);analytical_loaded(split,0.02);
        detail::propagate_free(split,{0,-10,0},0.03,0.5);analytical_loaded(split,0.05);
        detail::propagate_free(whole,{0,-10,0},0.05,0.5);
        vector_near(split.position,whole.position);vector_near(split.velocity,whole.velocity);
        vector_near(split.orientation.rotate({1,0,0}),whole.orientation.rotate({1,0,0}));
        exact(split.force,Vec3{6,4,-2});exact(split.torque,Vec3{0,0,8});
    });
    test("static free candidate preserves loads but successful public tick consumes them",[]{
        auto b=make_sphere(1,1,2,{0,0.5,0},true);b.force={1,2,3};b.torque={4,5,6};const auto before=b;
        detail::propagate_free(b,{0,-10,0},0.05,0.5);exact(b.position,before.position);exact(b.orientation,before.orientation);
        exact(b.velocity,before.velocity);exact(b.angular_momentum,before.angular_momentum);exact(b.force,before.force);exact(b.torque,before.torque);
        World w;w.add_body(b);w.step(0.05);exact(w.find_body(1)->force,{});exact(w.find_body(1)->torque,{});exact(w.find_body(1)->position,before.position);
    });
    test("free propagation does not detect or correct penetration",[]{
        auto b=make_sphere(1,1,2,{0,0.1,0});b.velocity={0,-2,0};detail::propagate_free(b,{0,-10,0},0.05,0.5);
        check(near(b.position.y,-0.0125)&&near(b.velocity.y,-2.5),"unconstrained free trajectory below potential floor");
    });
    test("fixed-time frictional impact changes velocity and L but not pose or loads",[]{
        auto b=make_sphere(1,1,2,{0,1,0});b.velocity={4,-2,0};b.material={0.5,0.6};b.force={3,5,7};b.torque={0.2,0.3,0.4};const auto before=b;
        std::vector<RigidBody> candidates{b};SolverSettings settings;settings.position_correction=0;
        const auto stats=detail::solve_contacts_at_current_state(candidates,{{100,{0,1,0},0,{0.5,0.6}}},settings);
        const auto& after=candidates[0];exact(after.position,before.position);exact(after.orientation,before.orientation);
        exact(after.force,before.force);exact(after.torque,before.torque);
        vector_near(after.velocity,{20./7,1,0});vector_near(after.angular_momentum,{0,0,-16./7});
        check(stats.contacts==1&&near(stats.normal_impulse_sum,6)&&near(stats.friction_impulse_sum,16./7),"analytic effective mass and impulse");
    });
    test("fixed-time unequal-mass elastic sphere impact preserves poses and loads",[]{
        auto a=make_sphere(1,1,1,{-1,0,0}),b=make_sphere(2,1,2,{1,0,0});a.velocity={3,0,0};b.velocity={-1,0,0};
        a.material={1,0};b.material={1,0};a.force={1,2,3};b.torque={0.1,0.2,0.3};const auto before_a=a,before_b=b;
        std::vector<RigidBody> candidates{a,b};SolverSettings settings;settings.position_correction=0;
        const auto stats=detail::solve_contacts_at_current_state(candidates,{},settings);
        vector_near(candidates[0].velocity,{-7./3,0,0});vector_near(candidates[1].velocity,{5./3,0,0});
        exact(candidates[0].position,before_a.position);exact(candidates[1].position,before_b.position);
        exact(candidates[0].orientation,before_a.orientation);exact(candidates[1].orientation,before_b.orientation);
        exact(candidates[0].force,before_a.force);exact(candidates[1].torque,before_b.torque);check(stats.contacts==1,"sphere contact count");
    });
    test("fixed-time solve retains optional legacy geometric projection",[]{
        auto b=make_sphere(1,1,2,{0,0.5,0});b.force={3,5,7};b.torque={0.2,0.3,0.4};const auto before=b;
        std::vector<RigidBody> candidates{b};const auto stats=detail::solve_contacts_at_current_state(candidates,{{100}},{});
        check(near(candidates[0].position.y,0.7)&&near(stats.max_penetration,0.5),"legacy capped projection");
        exact(candidates[0].velocity,before.velocity);exact(candidates[0].orientation,before.orientation);
        exact(candidates[0].force,before.force);exact(candidates[0].torque,before.torque);
    });
    test("public tick contact-budget failure preserves every body and held load",[]{
        World w;auto a=loaded();a.position={0,0.5,0};w.add_body(a);auto b=make_sphere(2,1,2,{0,1.5,0});b.force={7,8,9};w.add_body(b);
        b=make_sphere(3,1,2,{50,50,50},true);b.force={1,2,3};b.torque={4,5,6};w.add_body(b);w.add_plane({100});
        const auto before=snapshot(w);SolverSettings settings;settings.max_contacts=1;
        rejects([&]{w.step(0.01,settings);});check(snapshot(w)==before,"whole public candidate rollback");
        settings.max_contacts=8;w.step(0.01,settings);for(const auto& body:w.bodies()){exact(body.force,{});exact(body.torque,{});}
    });
    test("public tick rotation failure preserves original loads and permits reuse",[]{
        World w;auto b=loaded();b.angular_momentum={0,0,100};w.add_body(b);const auto before=snapshot(w);
        rejects([&]{w.step(0.1);});check(snapshot(w)==before,"rotation failure rollback");
        w.step(0.001);exact(w.find_body(1)->force,{});exact(w.find_body(1)->torque,{});
    });
    test("public load is consumed once while subsequent tick retains gravity",[]{
        World w;w.gravity={0,-10,0};auto b=make_sphere(1,1,2,{0,100,0});b.force={6,0,0};w.add_body(b);
        w.step(0.05);w.step(0.05);vector_near(w.find_body(1)->position,{0.01125,99.95,0});vector_near(w.find_body(1)->velocity,{0.15,-1,0});
    });
    std::cout<<passed<<" dynamics internal test groups passed\n";
}
#endif
}
int main(int argc,char** argv) {
    try {
        if(argc==2&&std::string(argv[1])=="--fixtures"){fixtures();return 0;}
#ifndef PP_DYNAMICS_BASELINE_ONLY
        if(argc!=1)throw std::runtime_error("usage: dynamics_internal_tests [--fixtures]");tests();return 0;
#else
        throw std::runtime_error("baseline build only supports --fixtures");
#endif
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}
