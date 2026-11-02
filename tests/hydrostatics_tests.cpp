#include "pikapika/hydrostatics.hpp"
#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <limits>
#include <map>
#include <stdexcept>

using namespace pikapika;
namespace hydro=pikapika::hydrostatics;
namespace dyn=pikapika::dynamics;
namespace {
unsigned passed{};
void check(bool ok,const char* detail) {if(!ok)throw std::runtime_error(detail);}
void near(double a,double b,double tolerance=1e-8) {if(std::abs(a-b)>tolerance)throw std::runtime_error("hydrostatic tolerance: actual="+std::to_string(a)+" expected="+std::to_string(b)+" tolerance="+std::to_string(tolerance));}
void vector_near(Vec3 a,Vec3 b,double tolerance=1e-8) {near(a.x,b.x,tolerance);near(a.y,b.y,tolerance);near(a.z,b.z,tolerance);}
void rejects(const std::function<void()>& call) {bool rejected=false;try{call();}catch(const std::exception&){rejected=true;}check(rejected,"expected hydrostatics input rejection");}
void test(const char* name,const std::function<void()>& call) {call();++passed;std::cout<<"PASS "<<name<<'\n';}
const hydro::Fluid water{1000,10,0};
Quaternion yaw(double angle) {return {0,std::sin(angle/2),0,std::cos(angle/2)};}
Quaternion roll(double angle) {return {0,0,std::sin(angle/2),std::cos(angle/2)};}
Mesh subdivide(const Mesh& mesh) {
    Mesh next;next.positions=mesh.positions;std::map<std::pair<std::uint32_t,std::uint32_t>,std::uint32_t> mids;
    const auto midpoint=[&](std::uint32_t a,std::uint32_t b) {
        const auto key=std::minmax(a,b);const std::pair<std::uint32_t,std::uint32_t> pair{key.first,key.second};
        auto found=mids.find(pair);if(found!=mids.end())return found->second;
        const auto index=std::uint32_t(next.positions.size());next.positions.push_back((mesh.positions[a]+mesh.positions[b])*0.5);mids[pair]=index;return index;
    };
    for(const auto& f:mesh.triangles){const auto a=f[0],b=f[1],c=f[2],ab=midpoint(a,b),bc=midpoint(b,c),ca=midpoint(c,a);next.triangles.insert(next.triangles.end(),{{a,ab,ca},{ab,b,bc},{ca,bc,c},{ab,bc,ca}});}
    next.validate();return next;
}
dyn::World floating(double y) {
    dyn::World world;world.gravity={0,-10,0};auto body=dyn::make_sphere(1,0.25,16000,{0,y,0});
    body.inertia_diagonal={16000*20./12,16000*32./12,16000*20./12};world.add_body(body);return world;
}
dyn::World ballasted(double angle) {
    dyn::World world;world.gravity={0,-10,0};auto body=dyn::make_sphere(1,0.25,32000,{0,-4,0});
    body.inertia_diagonal={24000,48000,40000};body.orientation=roll(angle);world.add_body(body);return world;
}
dyn::RigidBody heave(double dt,double duration=2) {
    auto world=floating(0.1);const hydro::Hull hull(make_box_mesh({4,2,4}));
    for(unsigned i=0;i<unsigned(std::lround(duration/dt));++i)hydro::step_isolated_buoyant_body(world,1,hull,dt,water);
    return *world.find_body(1);
}
std::array<double,2> pendulum_reference(double angle,double time) {
    const double dt=1./20000;double speed=0;
    for(unsigned i=0;i<unsigned(std::lround(time/dt));++i) {
        const double a1=speed,b1=-4*std::sin(angle),a2=speed+b1*dt/2,b2=-4*std::sin(angle+a1*dt/2);
        const double a3=speed+b2*dt/2,b3=-4*std::sin(angle+a2*dt/2),a4=speed+b3*dt,b4=-4*std::sin(angle+a3*dt);
        angle+=dt*(a1+2*a2+2*a3+a4)/6;speed+=dt*(b1+2*b2+2*b3+b4)/6;
    }
    return {angle,speed};
}
}
int main() {
    try {
        test("gauge pressure uses rho g depth and rejects nonfinite loads",[]{
            near(hydro::pressure(-3,water),0);near(hydro::pressure(2.5,water),25000);
            rejects([]{hydro::pressure(std::numeric_limits<double>::infinity());});
            rejects([]{hydro::pressure(1e308,{1e308,10,0});});
        });
        test("dry half and full cube match analytic displacement centroids and area",[]{
            const hydro::Hull hull(make_box_mesh({2,2,2}));hydro::Pose pose;pose.transform.position={0,2,0};
            const auto dry=hydro::forces(hull,water,pose);vector_near(dry.force,{});near(dry.wet_area,0);check(!dry.center_of_buoyancy,"dry has no centroid");
            const auto half=hydro::forces(hull,water);vector_near(half.force,{0,40000,0});vector_near(half.torque,{});near(half.submerged_volume,4);near(half.total_volume,8);near(half.wet_area,12);vector_near(*half.center_of_buoyancy,{0,-0.5,0});
            pose.transform.position={0,-2,0};const auto full=hydro::forces(hull,water,pose);near(full.submerged_volume,8);near(full.wet_area,24);vector_near(full.force,{0,80000,0});vector_near(*full.center_of_buoyancy,{0,-2,0});
        });
        test("waterline clipping remains analytic through vertices and complete wetting",[]{
            const hydro::Hull hull(make_box_mesh({2,2,2}));for(double level:{-2.,-1.,-0.95,-0.4,0.,0.4,0.95,1.,2.}) {
                auto fluid=water;fluid.water_level=level;const auto result=hydro::forces(hull,fluid);const double height=std::clamp(level+1,0.,2.);
                near(result.submerged_volume,4*height);vector_near(result.force,{0,40000*height,0});
                if(height>0)vector_near(*result.center_of_buoyancy,{0,-1+height/2,0});else check(!result.center_of_buoyancy,"dry centroid");
            }
        });
        test("translation scale and yaw preserve pressure geometry relationships",[]{
            const hydro::Hull cube(make_box_mesh({2,2,2}));hydro::Pose p;p.transform.position={12345,54321,-23456};auto f=water;f.water_level=p.transform.position.y;
            const auto translated=hydro::forces(cube,f,p);vector_near(translated.force,{0,40000,0});vector_near(*translated.center_of_buoyancy,{12345,54320.5,-23456});
            const hydro::Hull unit(make_box_mesh());p={};p.transform.scale={2,4,6};p.transform.rotation=yaw(0.73);
            const auto scaled=hydro::forces(unit,water,p);near(scaled.total_volume,48);near(scaled.submerged_volume,24);near(scaled.wet_area,44);vector_near(scaled.force,{0,240000,0});vector_near(*scaled.center_of_buoyancy,{0,-1,0});
        });
        test("arbitrary quaternion and ninety-degree roll preserve known volume and resultant line",[]{
            const hydro::Hull box(make_box_mesh({2,4,6}));hydro::Pose p;p.transform.rotation=roll(3.141592653589793/2);
            const auto r=hydro::forces(box,water,p);near(r.submerged_volume,24);near(r.wet_area,44);vector_near(*r.center_of_buoyancy,{0,-0.5,0});
            const double a=.37,b=.21;p.transform.rotation={std::sin(a/2)*std::cos(b/2),std::cos(a/2)*std::sin(b/2),std::sin(a/2)*std::sin(b/2),std::cos(a/2)*std::cos(b/2)};
            const hydro::Hull cube(make_box_mesh({2,2,2}));const auto tilted=hydro::forces(cube,water,p);near(tilted.submerged_volume,4);vector_near(tilted.torque,tilted.center_of_buoyancy->cross(tilted.force));
        });
        test("off-centre pressure moment matches independent r cross F",[]{
            const hydro::Hull hull(make_box_mesh({2,2,2}));hydro::Pose p;p.center_of_mass=Vec3{1,2,3};const auto r=hydro::forces(hull,water,p);vector_near(r.torque,{120000,0,-40000});
        });
        test("sloping tetrahedron matches independent volume subtraction and centroid",[]{
            Mesh m;m.positions={{0,0,0},{2,0,0},{0,2,0},{0,0,2}};m.triangles={{0,2,1},{0,1,3},{0,3,2},{1,2,3}};
            const hydro::Hull hull(m);auto fluid=water;fluid.water_level=1;const auto r=hydro::forces(hull,fluid);
            near(r.submerged_volume,7./6);vector_near(*r.center_of_buoyancy,{15./28,11./28,15./28});vector_near(r.torque,{-6250,0,6250});
        });
        test("surface retriangulation leaves exact-order pressure and moment integrals unchanged",[]{
            auto m=make_box_mesh({2,2,2});m.positions[6]={1.4,1.7,1.2};const hydro::Hull coarse(m),fine(subdivide(subdivide(m)));
            hydro::Pose p;p.transform.position={2,-0.4,-1};p.transform.rotation=yaw(.6);p.center_of_mass=Vec3{1,0,2};auto fluid=water;fluid.water_level=.23;
            const auto a=hydro::forces(coarse,fluid,p),b=hydro::forces(fine,fluid,p);vector_near(a.force,b.force);vector_near(a.torque,b.torque);near(a.wet_area,b.wet_area);near(a.submerged_volume,b.submerged_volume);vector_near(*a.center_of_buoyancy,*b.center_of_buoyancy);
        });
        test("density and gravity scale loads while displaced geometry stays fixed",[]{
            const hydro::Hull hull(make_box_mesh({2,2,2}));hydro::Pose p;p.center_of_mass=Vec3{1,2,3};const auto a=hydro::forces(hull,water,p);
            for(double scale:{.5,1.025,2.}) {auto f=water;f.density*=scale;const auto b=hydro::forces(hull,f,p);vector_near(b.force,a.force*scale);vector_near(b.torque,a.torque*scale);near(b.submerged_volume,a.submerged_volume);}
        });
        test("closed winding and per-shell volume validation reject invalid boundaries",[]{
            auto m=make_box_mesh({2,2,2});m.triangles.pop_back();rejects([&]{hydro::Hull h(m);});
            m=make_box_mesh({2,2,2});for(auto& t:m.triangles)std::swap(t[1],t[2]);rejects([&]{hydro::Hull h(m);});
            m=make_box_mesh({2,2,2});std::swap(m.triangles[0][0],m.triangles[0][1]);rejects([&]{hydro::Hull h(m);});
            m=make_box_mesh({2,2,2});m.triangles.push_back(m.triangles[0]);rejects([&]{hydro::Hull h(m);});
            Mesh flat;flat.positions={{0,0,0},{1,0,0},{1,1,0},{0,1,0}};flat.triangles={{0,1,2},{0,2,3},{0,3,1},{1,3,2}};rejects([&]{hydro::Hull h(flat);});
        });
        test("disjoint shells sum and one inverted shell cannot hide in positive total volume",[]{
            auto m=make_box_mesh({2,2,2});const auto b=m;for(auto p:b.positions)m.positions.push_back(p+Vec3{4,0,0});
            for(auto t:b.triangles){for(auto& i:t)i+=8;m.triangles.push_back(t);}const hydro::Hull hull(m);const auto r=hydro::forces(hull,water);
            check(r.shells==2,"two shells");near(r.submerged_volume,8);vector_near(*r.center_of_buoyancy,{2,-.5,0});
            for(std::size_t i=12;i<24;++i)std::swap(m.triangles[i][1],m.triangles[i][2]);rejects([&]{hydro::Hull invalid(m);});
        });
        test("invalid fluid pose scales and numeric overflow fail explicitly",[]{
            const hydro::Hull hull(make_box_mesh({2,2,2}));auto p=hydro::Pose{};p.transform.scale.y=-1;rejects([&]{hydro::forces(hull,water,p);});
            p={};p.transform.rotation.w=2;rejects([&]{hydro::forces(hull,water,p);});p={};p.center_of_mass=Vec3{0,std::numeric_limits<double>::quiet_NaN(),0};rejects([&]{hydro::forces(hull,water,p);});
            rejects([&]{hydro::forces(hull,{0,10,0});});rejects([&]{hydro::forces(hull,{1e308,1e308,0});});
        });
        test("native load helper adds world CoM torque and requires matching gravity",[]{
            const hydro::Hull hull(make_box_mesh({2,2,2}));auto world=floating(-3);const auto r=hydro::apply_buoyancy(world,1,hull,water,{1,0,0});
            vector_near(world.find_body(1)->force,r.force);vector_near(world.find_body(1)->torque,{0,0,80000});
            world.gravity={};rejects([&]{hydro::apply_buoyancy(world,1,hull,water);});
        });
        test("unrotated partial float remains in weight-buoyancy equilibrium without contacts",[]{
            const hydro::Hull hull(make_box_mesh({4,2,4}));auto world=floating(0);
            for(unsigned i=0;i<1200;++i){const auto r=hydro::step_isolated_buoyant_body(world,1,hull,1./120,water);check(r.dynamics.contacts==0,"floating reference must be contact-free");}
            vector_near(world.find_body(1)->position,{},1e-9);vector_near(world.find_body(1)->velocity,{},1e-9);vector_near(world.find_body(1)->angular_momentum,{},1e-7);
        });
        test("fully submerged offset CoM has exact restoring moment and wide partial box righting sign",[]{
            const hydro::Hull hull(make_box_mesh({4,2,4}));for(double angle:{-.15,.15}) {
                auto world=ballasted(angle);const auto r=hydro::apply_buoyancy(world,1,hull,water,{0,.5,0});near(r.torque.z,-160000*std::sin(angle),1e-7);
                auto partial=floating(0);partial.find_body(1)->orientation=roll(angle);const auto p=hydro::apply_buoyancy(partial,1,hull,water);check(p.torque.z*angle<0,"wide box restoring sign");
            }
        });
        test("original narrow box pitch is destabilising while wide reference pitch restores",[]{
            const hydro::Hull narrow(make_box_mesh({4,2,2})),wide(make_box_mesh({4,2,4}));
            for(double angle:{-.01,.01}) {
                hydro::Pose pose;pose.transform.rotation={std::sin(angle/2),0,0,std::cos(angle/2)};
                const auto a=hydro::forces(narrow,water,pose),b=hydro::forces(wide,water,pose);
                check(a.torque.x*angle>0,"narrow central CoM has negative pitch stability");
                check(b.torque.x*angle<0,"wide central CoM has positive pitch stability");
            }
        });
        test("midpoint heave coupling converges against independent harmonic trajectory",[]{
            const double frequency=std::sqrt(10.),time=2;double errors[3]{};
            for(unsigned i=0;i<3;++i) {const auto b=heave(1./(30*(1U<<i)),time);const double ey=b.position.y-.1*std::cos(frequency*time),ev=(b.velocity.y+.1*frequency*std::sin(frequency*time))/frequency;errors[i]=std::hypot(ey,ev);}
            std::cout<<"METRIC heave_error_30="<<errors[0]<<" 60="<<errors[1]<<" 120="<<errors[2]<<'\n';
            check(errors[0]/errors[1]>3.5&&errors[0]/errors[1]<4.5&&errors[1]/errors[2]>3.5&&errors[1]/errors[2]<4.5,"second-order coupled heave convergence");
        });
        test("undamped heave exposes bounded long-run energy error without hidden drag",[]{
            const hydro::Hull hull(make_box_mesh({4,2,4}));double worst[2]{};
            for(unsigned level=0;level<2;++level) {const unsigned rate=120U<<level;const double dt=1./rate;auto world=floating(.1);const double initial=800;
                for(unsigned i=0;i<rate*100;++i){hydro::step_isolated_buoyant_body(world,1,hull,dt,water);const auto& b=*world.find_body(1);const double energy=b.kinetic_energy()+.5*160000*b.position.y*b.position.y;worst[level]=std::max(worst[level],std::abs(energy-initial)/initial);}
            }
            std::cout<<"METRIC heave_100s_energy_relative_max_120="<<worst[0]<<" 240="<<worst[1]<<'\n';check(worst[0]<.001&&worst[1]<worst[0]/2,"documented heave energy error must shrink");
        });
        test("ballasted roll converges against independent scalar pendulum and accounts for torque work",[]{
            const hydro::Hull hull(make_box_mesh({4,2,4}));const auto reference=pendulum_reference(.15,2);double errors[3]{};
            for(unsigned i=0;i<3;++i){const unsigned rate=30U<<i;auto world=ballasted(.15);double work=0;
                for(unsigned tick=0;tick<rate*2;++tick){const auto before=*world.find_body(1);const auto r=hydro::step_isolated_buoyant_body(world,1,hull,1./rate,water,{0,.5,0});const auto& after=*world.find_body(1);work+=r.midpoint_load.torque.dot((before.angular_velocity()+after.angular_velocity())*.5)/rate;}
                const auto& b=*world.find_body(1);const double angle=2*std::atan2(b.orientation.z,b.orientation.w);errors[i]=std::hypot(angle-reference[0],(b.angular_velocity().z-reference[1])/2);near(b.kinetic_energy(),work,1e-6);
            }
            std::cout<<"METRIC roll_error_30="<<errors[0]<<" 60="<<errors[1]<<" 120="<<errors[2]<<'\n';check(errors[0]/errors[1]>3.5&&errors[1]/errors[2]>3.5,"second-order nonlinear restoring response");
        });
        test("isolated midpoint guard and failed load leave the original world unchanged",[]{
            const hydro::Hull hull(make_box_mesh({4,2,2}));auto world=floating(0);world.apply_force(1,{1,0,0},{});const auto before=*world.find_body(1);
            rejects([&]{hydro::step_isolated_buoyant_body(world,1,hull,-1,water);});vector_near(world.find_body(1)->force,before.force);vector_near(world.find_body(1)->position,before.position);
            world.add_plane({2});rejects([&]{hydro::step_isolated_buoyant_body(world,1,hull,.01,water);});
        });
        std::cout<<passed<<" native hydrostatics/coupling test groups passed\n";return 0;
    }catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}
}
