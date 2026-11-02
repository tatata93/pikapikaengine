#include "pikapika/dynamics.hpp"
#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <stdexcept>

using namespace pikapika;
using namespace pikapika::dynamics;
namespace {
unsigned passed=0;
void check(bool ok,const char* detail) { if(!ok)throw std::runtime_error(detail); }
bool near(double a,double b,double tolerance=1e-9) { return std::abs(a-b)<=tolerance; }
void vector_near(Vec3 a,Vec3 b,double tolerance=1e-9) { check((a-b).length()<=tolerance,"vector tolerance"); }
void rejects(const std::function<void()>& operation) { bool rejected=false;try{operation();}catch(const std::exception&){rejected=true;}check(rejected,"expected invalid-input rejection"); }
void test(const char* name,const std::function<void()>& body) { body();++passed;std::cout<<"PASS "<<name<<'\n'; }
Vec3 linear_momentum(const World& world) { Vec3 p;for(const auto& b:world.bodies())if(!b.is_static)p=p+b.velocity*b.mass;return p; }
Vec3 total_angular_momentum(const World& world) { Vec3 l;for(const auto& b:world.bodies())if(!b.is_static)l=l+b.angular_momentum+b.position.cross(b.velocity*b.mass);return l; }
double kinetic(const World& world) {double value=0;for(const auto& b:world.bodies())value+=b.kinetic_energy();return value;}
RigidBody free_rotation(double dt,double duration=4) {
    World world;world.gravity={};auto body=make_sphere(1,1,1);body.inertia_diagonal={2,3,4};body.angular_momentum={1.1,2.2,3.3};world.add_body(body);
    const int steps=int(std::lround(duration/dt));for(int i=0;i<steps;++i)world.step(dt);return *world.find_body(1);
}
double orientation_error(Quaternion q,Quaternion reference) {
    const auto x=q.rotate({1,0,0})-reference.rotate({1,0,0}),y=q.rotate({0,1,0})-reference.rotate({0,1,0}),z=q.rotate({0,0,1})-reference.rotate({0,0,1});
    return std::sqrt(x.dot(x)+y.dot(y)+z.dot(z));
}
}
int main() {
    try {
        test("free fall matches constant-acceleration analytic trajectory",[]{
            World w;w.add_body(make_sphere(1,0.2,2,{0,100,0}));for(unsigned i=0;i<240;++i)w.step(1./120);
            const auto& b=*w.find_body(1);check(near(b.position.y,100-0.5*9.80665*4,1e-10),"analytic height");check(near(b.velocity.y,-9.80665*2,1e-11),"analytic velocity");
        });
        test("force torque and off-centre impulses use SI mass and principal inertia",[]{
            World w;w.gravity={};auto b=make_sphere(1,1,2);b.inertia_diagonal={2,3,4};w.add_body(b);
            w.apply_force(1,{6,0,0},{0,0,0});w.apply_torque(1,{0,0,8});w.step(0.1);
            const auto& result=*w.find_body(1);check(near(result.velocity.x,0.3)&&near(result.position.x,0.015),"F/m translation");
            check(near(result.angular_momentum.z,0.8)&&near(result.angular_velocity().z,0.2),"torque/inertia acceleration");
            vector_near(result.orientation.rotate({1,0,0}),{std::cos(0.01),std::sin(0.01),0},1e-12);
            vector_near(result.force,{});vector_near(result.torque,{});
            w.apply_impulse(1,{2,0,0},result.position+Vec3{0,1,0});
            check(near(w.find_body(1)->velocity.x,1.3)&&near(w.find_body(1)->angular_momentum.z,-1.2),"point impulse spin");
            World force;force.gravity={};force.add_body(make_sphere(2,1,2));force.apply_force(2,{3,0,0},{0,2,0});force.step(0.1);
            check(near(force.find_body(2)->angular_momentum.z,-0.6),"off-centre force torque");
        });
        test("elastic unequal-mass sphere collision conserves momentum and energy",[]{
            World w;w.gravity={};auto a=make_sphere(1,1,2,{-1,0,0}),b=make_sphere(2,1,3,{1,0,0});
            a.velocity={3,0,0};b.velocity={-1,0,0};a.material={1,0};b.material={1,0};w.add_body(a);w.add_body(b);
            const auto p=linear_momentum(w);const double e=kinetic(w);SolverSettings settings;settings.position_correction=0;
            const auto stats=w.step(0.01,settings);check(stats.contacts==1,"one collision");
            // 1D two-body elastic formula, independently evaluated for m1=2,m2=3,u1=3,u2=-1.
            check(near(w.find_body(1)->velocity.x,-1.8)&&near(w.find_body(2)->velocity.x,2.2),"analytic elastic velocities");
            vector_near(linear_momentum(w),p);check(near(kinetic(w),e,1e-10),"elastic kinetic energy");
        });
        test("restitution ratio and inelastic dissipation match isolated analytic collision",[]{
            World w;w.gravity={};auto a=make_sphere(1,1,1,{-1,0,0}),b=make_sphere(2,1,1,{1,0,0});
            a.velocity={2,0,0};b.velocity={-2,0,0};a.material={0.5,0};b.material={0.5,0};w.add_body(a);w.add_body(b);
            const double before=kinetic(w);w.step(0.01);check(near(w.find_body(2)->velocity.x-w.find_body(1)->velocity.x,2),"relative separation e times approach");
            check(near(kinetic(w),before*0.25),"centre-of-mass kinetic energy ratio e squared");
        });
        test("static sphere collision and plane bounce preserve prescribed static state",[]{
            World w;w.gravity={};auto a=make_sphere(1,1,1,{-1,0,0}),fixed=make_sphere(2,1,1,{1,0,0},true);
            a.velocity={2,0,0};a.material={1,0};fixed.material={1,0};w.add_body(a);w.add_body(fixed);w.step(0.01);
            check(near(w.find_body(1)->velocity.x,-2),"static sphere bounce");vector_near(w.find_body(2)->position,{1,0,0});
            World p;p.gravity={};auto ball=make_sphere(3,1,1,{0,1,0});ball.velocity={0,-3,0};ball.material={0.5,0};p.add_body(ball);p.add_plane({4,{0,1,0},0,{0.5,0}});p.step(0.01);
            check(near(p.find_body(3)->velocity.y,1.5),"plane restitution");
        });
        test("resting sphere receives analytic weight support without kinetic energy",[]{
            World w;w.add_body(make_sphere(1,1,2,{0,1,0}));w.add_plane({2});double impulse=0;
            for(unsigned i=0;i<1200;++i) {const auto stats=w.step(1./120);impulse+=stats.normal_impulse_sum;check(kinetic(w)<1e-18,"resting contact must not inject speed");}
            check(near(impulse,2*9.80665*10,1e-8),"integrated support impulse = m g t");
            check(std::abs(w.find_body(1)->position.y-1)<0.0002,"bounded penetration at rest");
        });
        test("sphere-plane friction transfers translation into rotation without energy creation",[]{
            World w;w.gravity={};auto ball=make_sphere(1,1,1,{0,1,0});ball.velocity={5,-2,0};ball.material={0,0.8};w.add_body(ball);w.add_plane({2,{0,1,0},0,{0,0.8}});
            const double before=kinetic(w);const auto stats=w.step(0.01);const auto& body=*w.find_body(1);
            check(body.velocity.x<5&&body.velocity.x>0&&body.angular_momentum.z<0,"friction spin and slowdown");
            check(stats.friction_impulse_sum<=0.8*stats.normal_impulse_sum+1e-12,"Coulomb bound");
            check(kinetic(w)<=before+1e-10,"no kinetic energy creation");
            vector_near(body.velocity+body.angular_velocity().cross({0,-1,0}),{},1e-9);
        });
        test("uniform sphere rolling down incline matches analytic five-sevenths acceleration",[]{
            const double angle=0.3;const Vec3 normal{std::sin(angle),std::cos(angle),0},downhill{std::cos(angle),-std::sin(angle),0};
            World w;w.add_body(make_sphere(1,1,2,normal));w.add_plane({2,normal,0,{0,0.6}});
            for(unsigned i=0;i<120;++i)w.step(1./120);
            const auto& body=*w.find_body(1);const double expected=5./7*9.80665*std::sin(angle);
            check(near(body.velocity.dot(downhill),expected,1e-9),"rolling acceleration = 5/7 g sin(theta)");
            vector_near(body.velocity+body.angular_velocity().cross(normal*(-1)),{},1e-9);
        });
        test("anisotropic sphere-plane tangent disk dissipates energy across fixed cases",[]{
            for(double mu:{0.,0.1,0.7,2.})for(double yaw:{0.,0.4,1.,2.}) {
                World w;w.gravity={};auto body=make_sphere(1,1,2,{0,1,0});body.inertia_diagonal={2,3,4};
                body.orientation={0,std::sin(yaw/2),0,std::cos(yaw/2)};body.velocity={3,-2,-1.5};body.angular_momentum={1.2,-0.4,2.1};body.material={0,mu};
                w.add_body(body);w.add_plane({2,{0,1,0},0,{0,mu}});const double before=kinetic(w);const auto stats=w.step(0.001);
                check(kinetic(w)<=before+1e-10,"anisotropic disk kinetic energy");
                check(stats.friction_impulse_sum<=mu*stats.normal_impulse_sum+1e-10,"anisotropic disk Coulomb bound");
            }
        });
        test("anisotropic tangent effective mass obeys friction energy and angular momentum",[]{
            World w;w.gravity={};auto a=make_sphere(1,1,2,{-1,0,0}),b=make_sphere(2,1,3,{1,0,0});
            a.inertia_diagonal={2,3,4};b.inertia_diagonal={4,5,6};a.velocity={2,3,2};b.velocity={-1,-2,0.2};a.material={0,0.9};b.material={0,0.9};
            w.add_body(a);w.add_body(b);const auto linear=linear_momentum(w),angular=total_angular_momentum(w);const double before=kinetic(w);
            SolverSettings s;s.position_correction=0;const auto stats=w.step(0.001,s);check(stats.contacts==1,"anisotropic pair contact");
            vector_near(linear_momentum(w),linear,1e-10);vector_near(total_angular_momentum(w),angular,1e-9);
            check(kinetic(w)<=before+1e-9,"anisotropic friction does not increase pair energy");
        });
        test("torque-free anisotropic body conserves world L and retains gyroscopic motion",[]{
            const auto body=free_rotation(1./240,8);vector_near(body.angular_momentum,{1.1,2.2,3.3},0);
            const Vec3 initial_omega{1.1/2,2.2/3,3.3/4};check((body.angular_velocity()-initial_omega).length()>0.1,"omega must evolve at fixed L for anisotropic body");
            const double energy0=0.5*initial_omega.dot({1.1,2.2,3.3});check(std::abs(body.kinetic_energy()-energy0)/energy0<2e-5,"bounded free-rotation energy error");
        });
        test("spherical principal-axis rotation matches exact trigonometric solution",[]{
            World w;w.gravity={};auto body=make_sphere(1,1,1);body.angular_momentum={0,0,0.8};w.add_body(body);
            for(unsigned i=0;i<100;++i)w.step(0.01);
            vector_near(w.find_body(1)->orientation.rotate({1,0,0}),{std::cos(2.),std::sin(2.),0},1e-12);
        });
        test("anisotropic angular acceleration agrees with Euler body-frame equation",[]{
            World w;w.gravity={};auto body=make_sphere(1,1,1);body.inertia_diagonal={2,3,4};body.angular_momentum={1.1,2.2,3.3};w.add_body(body);
            const auto omega=body.angular_velocity(),cross=omega.cross(body.angular_momentum);
            const Vec3 expected{-cross.x/2,-cross.y/3,-cross.z/4};const double dt=1e-5;w.step(dt);
            const auto& result=*w.find_body(1);const Quaternion inverse{-result.orientation.x,-result.orientation.y,-result.orientation.z,result.orientation.w};
            const auto derivative=(inverse.rotate(result.angular_velocity())-omega)*(1/dt);vector_near(derivative,expected,2e-6);
        });
        test("orientation midpoint exhibits second-order timestep convergence",[]{
            const auto reference=free_rotation(1./15360);const auto coarse=free_rotation(1./30),fine=free_rotation(1./60),finer=free_rotation(1./120);
            const double ec=orientation_error(coarse.orientation,reference.orientation),ef=orientation_error(fine.orientation,reference.orientation),eff=orientation_error(finer.orientation,reference.orientation);
            std::cout<<"METRIC orientation_error_dt_1_30="<<ec<<" dt_1_60="<<ef<<" dt_1_120="<<eff<<'\n';
            check(ec/ef>3.5&&ec/ef<4.5&&ef/eff>3.5&&ef/eff<4.5,"second-order error reduction");
        });
        test("bounded contact iterations solve a small resting stack",[]{
            World w;for(unsigned i=0;i<3;++i)w.add_body(make_sphere(i+1,1,1,{0,1.+2*i,0}));w.add_plane({4});SolverSettings s;s.velocity_iterations=64;
            for(unsigned i=0;i<480;++i)w.step(1./240,s);
            for(const auto& b:w.bodies())check(std::abs(b.velocity.y)<1e-5,"stack residual velocity");
        });
        test("failed budgets invalid loads IDs and excessive rotation abort transactionally",[]{
            World w;w.gravity={};w.add_body(make_sphere(1,1,1));w.add_body(make_sphere(2,1,1,{0.5,0,0}));w.add_plane({3});
            w.apply_force(1,{1,0,0},{});
            SolverSettings s;s.max_contacts=1;const auto previous=*w.find_body(1);rejects([&]{w.step(0.01,s);});vector_near(w.find_body(1)->position,previous.position);
            vector_near(w.find_body(1)->force,previous.force);
            rejects([&]{w.add_plane({1});});rejects([&]{w.apply_force(99,{},{});});rejects([&]{w.step(-1);});
            auto body=make_sphere(9,1,1);body.inertia_diagonal={1,1,3};rejects([&]{body.validate();});
            World spin;spin.gravity={};body=make_sphere(9,1,1);body.angular_momentum={0,0,100};spin.add_body(body);
            rejects([&]{spin.step(0.01);});vector_near(spin.find_body(9)->position,{});
        });
        std::cout<<passed<<" dynamics test groups passed\n";return 0;
    } catch(const std::exception& error) {std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}
