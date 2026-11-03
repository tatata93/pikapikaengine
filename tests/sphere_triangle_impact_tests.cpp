#include "pikapika/sphere_triangle.hpp"
#include "pikapika/dynamics.hpp"
#include "../core/src/dynamics_internal.hpp"
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

namespace st=pikapika::sphere_triangle;
namespace dyn=pikapika::dynamics;
using pikapika::Vec3;
using pikapika::Quaternion;
namespace {
unsigned passed{};
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void near(double a,double b,double tolerance=2e-11){require(std::abs(a-b)<=tolerance,"analytic scalar tolerance");}
void near(Vec3 a,Vec3 b,double tolerance=2e-11){near(a.x,b.x,tolerance);near(a.y,b.y,tolerance);near(a.z,b.z,tolerance);}
void exact(double a,double b){require(std::bit_cast<std::uint64_t>(a)==std::bit_cast<std::uint64_t>(b),"exact scalar invariant");}
void exact(Vec3 a,Vec3 b){exact(a.x,b.x);exact(a.y,b.y);exact(a.z,b.z);}
void exact(Quaternion a,Quaternion b){exact(a.x,b.x);exact(a.y,b.y);exact(a.z,b.z);exact(a.w,b.w);}
void test(const char* name,const std::function<void()>& operation){operation();++passed;std::cout<<"PASS "<<name<<'\n';}
st::StaticTriangle triangle(){return {73101,{{{0,0,0},{4,0,0},{0,0,4}}}};}
dyn::SolverSettings solver(){dyn::SolverSettings s;s.position_correction=0;s.restitution_velocity_threshold=0;s.contact_margin=0;return s;}
void contains(const st::Bounds3& bounds,Vec3 value){require(bounds[0].contains(value.x)&&bounds[1].contains(value.y)&&bounds[2].contains(value.z),"known reference inside geometric enclosure");}
void known(const st::Result& result,Vec3 point,Vec3 normal,double distance){
    require(result.status==st::Status::completed&&result.geometry.has_value(),"known query completed");
    const auto& geometry=*result.geometry;require(geometry.surface_id==73101&&geometry.surviving_features!=0,"surface identity");
    contains(geometry.closest,point);contains(geometry.normal,normal);contains(geometry.sphere_point,point);
    require(geometry.distance.contains(distance)&&geometry.squared_distance.contains(distance*distance)&&geometry.gap.contains(0),"known distance and contact");
}
void pose_and_loads(const dyn::RigidBody& after,const dyn::RigidBody& before){
    require(after.id==before.id&&after.is_static==before.is_static,"body identity unchanged");
    exact(after.position,before.position);exact(after.orientation,before.orientation);exact(after.force,before.force);exact(after.torque,before.torque);
    exact(after.mass,before.mass);exact(after.radius,before.radius);exact(after.inertia_diagonal,before.inertia_diagonal);
    exact(after.material.restitution,before.material.restitution);exact(after.material.friction,before.material.friction);
}
std::string snapshot(const dyn::World& world){
    std::ostringstream out;out<<std::hex;
    const auto scalar=[&](double value){out<<std::bit_cast<std::uint64_t>(value)<<',';};
    const auto vector=[&](Vec3 value){scalar(value.x);scalar(value.y);scalar(value.z);};
    vector(world.gravity);
    for(const auto& b:world.bodies()){
        out<<b.id<<','<<b.is_static<<',';scalar(b.mass);scalar(b.radius);vector(b.inertia_diagonal);vector(b.position);vector(b.velocity);vector(b.angular_momentum);
        scalar(b.orientation.x);scalar(b.orientation.y);scalar(b.orientation.z);scalar(b.orientation.w);vector(b.force);vector(b.torque);scalar(b.material.restitution);scalar(b.material.friction);
    }
    for(const auto& p:world.planes()){out<<p.id<<',';vector(p.normal);scalar(p.offset);scalar(p.material.restitution);scalar(p.material.friction);}
    return out.str();
}
dyn::RigidBody body(double radius,double mass,Vec3 center){
    auto result=dyn::make_sphere(73001,radius,mass,center);result.force={3,5,7};result.torque={.2,.3,.4};return result;
}
struct AnalyticContact {Vec3 center,point,normal;double distance;};
const std::array<AnalyticContact,4> analytic{{
    {{1,2,1},{1,0,1},{0,1,0},2},
    {{1,-2,1},{1,0,1},{0,-1,0},2},
    {{2,3,-4},{2,0,0},{0,.6,-.8},5},
    {{-3,4,0},{0,0,0},{-.6,.8,0},5}
}};
void normal_case(const AnalyticContact& c,double restitution,double mass,double speed){
    dyn::World source;auto b=body(c.distance,mass,c.center);b.velocity=c.normal*(-speed);b.material={restitution,0};source.add_body(b);
    const auto original=snapshot(source);const auto* pointer=source.find_body(b.id);
    const auto result=st::query_sphere_triangle({b.position,b.radius},triangle());known(result,c.point,c.normal,c.distance);
    // Only this independently known analytic point/normal enters the existing
    // point solver. Never take the midpoint of an arbitrary returned interval.
    std::vector<dyn::RigidBody> candidates=source.bodies();
    const double before=candidates[0].kinetic_energy();
    const dyn::detail::ImpactContact contact{dyn::detail::absent_body,0,c.point,c.normal,{restitution,0},b.material};
    const auto stats=dyn::detail::solve_selected_impacts(candidates,{contact},solver());
    near(candidates[0].velocity,c.normal*(restitution*speed));near(candidates[0].angular_momentum,{});
    near(candidates[0].kinetic_energy()-before,-.5*mass*(1-restitution*restitution)*speed*speed);
    near(stats.normal_impulse_sum,mass*(1+restitution)*speed);near(stats.friction_impulse_sum,0);near(stats.max_closing_residual,0);
    require(stats.contacts==1,"one selected analytic contact");pose_and_loads(candidates[0],b);
    require(snapshot(source)==original&&source.find_body(b.id)==pointer,"original World and body pointer unchanged");
}
void tests(){
    for(unsigned i=0;i<analytic.size();++i)test(("known face/back/edge/vertex normal restitution family "+std::to_string(i)).c_str(),[i]{
        for(double e:{0.,.25,.5,1.})for(double mass:{1.,3.})for(double speed:{2.,4.})normal_case(analytic[i],e,mass,speed);
    });
    test("face friction matches independent uniform-sphere effective mass and torque",[]{
        dyn::World source;auto b=body(1,2,{1,1,1});b.velocity={4,-2,0};b.material={.5,.6};source.add_body(b);const auto original=snapshot(source);
        const Vec3 point{1,0,1},normal{0,1,0};known(st::query_sphere_triangle({b.position,b.radius},triangle()),point,normal,1);
        auto candidates=source.bodies();const auto stats=dyn::detail::solve_selected_impacts(candidates,{{dyn::detail::absent_body,0,point,normal,b.material,b.material}},solver());
        near(candidates[0].velocity,{20./7,1,0});near(candidates[0].angular_momentum,{0,0,-16./7});
        near(stats.normal_impulse_sum,6);near(stats.friction_impulse_sum,16./7);
        const Vec3 impulse=(candidates[0].velocity-b.velocity)*b.mass;
        near(candidates[0].angular_momentum-b.angular_momentum,(point-b.position).cross(impulse));
        near(candidates[0].velocity+candidates[0].angular_velocity().cross(point-b.position),{0,1,0});
        require(candidates[0].kinetic_energy()<=b.kinetic_energy(),"no friction energy creation");pose_and_loads(candidates[0],b);require(snapshot(source)==original,"source unchanged");
    });
    test("sliding friction reaches the Coulomb limit and preserves instantaneous pose",[]{
        auto b=body(1,2,{1,1,1});b.velocity={4,-2,0};b.material={.5,.05};
        const Vec3 point{1,0,1},normal{0,1,0};known(st::query_sphere_triangle({b.position,b.radius},triangle()),point,normal,1);
        std::vector<dyn::RigidBody> candidates{b};const auto stats=dyn::detail::solve_selected_impacts(candidates,{{dyn::detail::absent_body,0,point,normal,b.material,b.material}},solver());
        near(stats.normal_impulse_sum,6);near(stats.friction_impulse_sum,.3);near(candidates[0].velocity,{3.85,1,0});near(candidates[0].angular_momentum,{0,0,-.3});
        require(candidates[0].kinetic_energy()<=b.kinetic_energy(),"sliding energy");pose_and_loads(candidates[0],b);
    });
    test("analytic face contacts equal existing plane solver for anisotropic inertia",[]{
        const Vec3 point{1,0,1},normal{0,1,0};
        for(double mu:{0.,.05,.6,2.})for(double angle:{0.,.4,1.,2.}){
            auto b=body(1,2,{1,1,1});b.inertia_diagonal={2,3,4};b.orientation={0,std::sin(angle/2),0,std::cos(angle/2)};
            b.velocity={3,-2,-1.5};b.angular_momentum={1.2,-.4,2.1};b.material={.5,mu};
            known(st::query_sphere_triangle({b.position,b.radius},triangle()),point,normal,1);
            std::vector<dyn::RigidBody> selected{b},plane{b};
            const auto a=dyn::detail::solve_selected_impacts(selected,{{dyn::detail::absent_body,0,point,normal,b.material,b.material}},solver());
            const auto p=dyn::detail::solve_contacts_at_current_state(plane,{{73101,normal,0,b.material}},solver());
            exact(selected[0].velocity,plane[0].velocity);exact(selected[0].angular_momentum,plane[0].angular_momentum);
            exact(a.normal_impulse_sum,p.normal_impulse_sum);exact(a.friction_impulse_sum,p.friction_impulse_sum);
            const Vec3 impulse=(selected[0].velocity-b.velocity)*b.mass;
            near(selected[0].angular_momentum-b.angular_momentum,(point-b.position).cross(impulse));
            pose_and_loads(selected[0],b);require(selected[0].kinetic_energy()<=b.kinetic_energy()+1e-10,"anisotropic friction energy");
        }
    });
    test("finite triangle outside region remains separated despite infinite plane proximity",[]{
        dyn::World source;auto b=body(.25,2,{8,.1,8});b.velocity={0,-2,0};source.add_body(b);const auto original=snapshot(source);
        const auto result=st::query_sphere_triangle({b.position,b.radius},triangle());
        require(result.status==st::Status::completed&&result.geometry->relation==st::Relation::separated,"outside finite triangle is separated");
        require(snapshot(source)==original,"query has no World side effects");
    });
    test("failed query never supplies geometry or consumes original loads and permits reuse",[]{
        dyn::World source;auto b=body(1,2,{1,1,1});source.add_body(b);const auto original=snapshot(source);
        st::Settings small;small.max_candidates=1;const auto budget=st::query_sphere_triangle({b.position,b.radius},triangle(),small);
        require(budget.status==st::Status::budget_exceeded&&!budget.geometry,"candidate budget has no accepted geometry");
        const auto zero=st::query_sphere_triangle({{1,0,1},1},triangle());require(zero.status!=st::Status::completed&&!zero.geometry,"undefined normal is not fabricated");
        require(snapshot(source)==original,"failed query preserves World");known(st::query_sphere_triangle({b.position,b.radius},triangle()),{1,0,1},{0,1,0},1);
    });
    test("selected solver preflight budget failure leaves candidate and original state intact",[]{
        dyn::World source;auto b=body(1,2,{1,1,1});source.add_body(b);const auto original=snapshot(source);auto candidate=source.bodies();
        const dyn::detail::ImpactContact c{dyn::detail::absent_body,0,{1,0,1},{0,1,0},b.material,b.material};auto s=solver();s.max_contacts=1;
        bool rejected=false;try{dyn::detail::solve_selected_impacts(candidate,{c,c},s);}catch(const std::exception&){rejected=true;}
        require(rejected&&snapshot(source)==original,"selected budget rejected before original mutation");
        pose_and_loads(candidate[0],b);exact(candidate[0].velocity,b.velocity);exact(candidate[0].angular_momentum,b.angular_momentum);
    });
    std::cout<<passed<<" sphere triangle analytic impact groups passed\n";
}
}
int main(){try{tests();return 0;}catch(const std::exception& error){std::cerr<<"FAIL "<<error.what()<<'\n';return 1;}}
