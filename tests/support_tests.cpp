#include "pikapika/support.hpp"
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace pikapika;
using namespace pikapika::dynamics;
namespace {
unsigned passed=0;
void check(bool b,const std::string& message){if(!b)throw std::runtime_error(message);}
void near(double a,double b,double tolerance=2e-8){check(std::abs(a-b)<=tolerance,"analytical mismatch "+std::to_string(a)+" != "+std::to_string(b));}
void vec(Vec3 a,Vec3 b,double t=2e-8){near(a.x,b.x,t);near(a.y,b.y,t);near(a.z,b.z,t);}
void outvec(std::ostream& out,Vec3 v){out<<'['<<v.x<<','<<v.y<<','<<v.z<<']';}
void out2(std::ostream& out,std::array<double,2> v){out<<'['<<v[0]<<','<<v[1]<<']';}
void outbody(std::ostream& out,const RigidBody& b){
    out<<"{\"id\":"<<b.id<<",\"isStatic\":"<<(b.is_static?"true":"false")<<",\"mass\":"<<b.mass<<",\"radius\":"<<b.radius<<",\"inertia\":";outvec(out,b.inertia_diagonal);
    out<<",\"position\":";outvec(out,b.position);out<<",\"velocity\":";outvec(out,b.velocity);out<<",\"orientation\":["<<b.orientation.x<<','<<b.orientation.y<<','<<b.orientation.z<<','<<b.orientation.w<<"],\"angularMomentum\":";outvec(out,b.angular_momentum);
    out<<",\"force\":";outvec(out,b.force);out<<",\"torque\":";outvec(out,b.torque);out<<",\"material\":{\"restitution\":"<<b.material.restitution<<",\"friction\":"<<b.material.friction<<"}}";
}
void outworld(std::ostream& out,const World& w){
    out<<"{\"gravity\":";outvec(out,w.gravity);out<<",\"bodies\":[";bool comma=false;for(const auto& b:w.bodies()){if(comma)out<<',';comma=true;outbody(out,b);}out<<"],\"planes\":[";comma=false;
    for(const auto& p:w.planes()){if(comma)out<<',';comma=true;out<<"{\"id\":"<<p.id<<",\"normal\":";outvec(out,p.normal);out<<",\"offset\":"<<p.offset<<",\"material\":{\"restitution\":"<<p.material.restitution<<",\"friction\":"<<p.material.friction<<"}}";}out<<"]}";
}
std::string snapshot(const World& w){std::ostringstream out;out<<std::setprecision(17);outworld(out,w);return out.str();}
void outsettings(std::ostream& out,const support::Settings& s){
    out<<"{\"gapTolerance\":"<<s.gap_tolerance<<",\"velocityIntervalTolerance\":"<<s.velocity_interval_tolerance<<",\"accelerationTolerance\":"<<s.acceleration_tolerance
        <<",\"complementarityTolerance\":"<<s.complementarity_tolerance<<",\"projectedForceTolerance\":"<<s.projected_force_tolerance<<",\"minimumScaledPivot\":"<<s.minimum_scaled_pivot
        <<",\"maximumForce\":"<<s.maximum_force<<",\"maxIterations\":"<<s.max_iterations<<",\"maxContacts\":"<<s.max_contacts<<",\"maxPairQueries\":"<<s.max_pair_queries<<'}';
}
void outresult(std::ostream& out,const support::Result& r){
    out<<"{\"success\":"<<(r.success?"true":"false")<<",\"failure\":"<<static_cast<int>(r.failure)<<",\"firstId\":"<<r.first_id<<",\"secondId\":"<<r.second_id
        <<",\"message\":"<<std::quoted(r.message)
        <<",\"pairQueries\":"<<r.pair_queries<<",\"separatedPairs\":"<<r.separated_pairs<<",\"restingConstraints\":"<<r.resting_constraints<<",\"separatingConstraints\":"<<r.separating_constraints
        <<",\"iterations\":"<<r.iterations<<",\"maximumGeometryOffset\":"<<r.maximum_geometry_offset<<",\"maximumVelocityIntervalWidth\":"<<r.maximum_velocity_interval_width
        <<",\"minimumScaledPivot\":"<<r.minimum_scaled_pivot<<",\"residuals\":{\"negativeForce\":"<<r.residuals.negative_force<<",\"negativeAcceleration\":"<<r.residuals.negative_acceleration
        <<",\"complementarity\":"<<r.residuals.complementarity<<",\"projectedForce\":"<<r.residuals.projected_force<<",\"maximumAccelerationIntervalWidth\":"<<r.residuals.maximum_acceleration_interval_width<<"},\"constraints\":[";
    bool comma=false;for(const auto& c:r.constraints){if(comma)out<<',';comma=true;out<<"{\"firstId\":"<<c.first_id<<",\"secondId\":"<<c.second_id<<",\"phase\":"<<static_cast<int>(c.phase)<<",\"normal\":";outvec(out,c.normal);
        out<<",\"normalLower\":";outvec(out,c.normal_lower);out<<",\"normalUpper\":";outvec(out,c.normal_upper);out<<",\"gap\":";out2(out,c.gap);out<<",\"normalVelocity\":";out2(out,c.normal_velocity);
        out<<",\"curvature\":";out2(out,c.curvature);out<<",\"guardedGeometry\":"<<(c.guarded_geometry?"true":"false")<<",\"freeNormalAcceleration\":"<<c.free_normal_acceleration
            <<",\"lambda\":"<<c.lambda<<",\"normalAcceleration\":"<<c.normal_acceleration<<",\"accelerationBounds\":";out2(out,c.acceleration_bounds);out<<'}';}
    out<<"],\"bodies\":[";comma=false;for(const auto& b:r.bodies){if(comma)out<<',';comma=true;out<<"{\"id\":"<<b.id<<",\"force\":";outvec(out,b.force);out<<",\"forceLower\":";outvec(out,b.force_lower);
        out<<",\"forceUpper\":";outvec(out,b.force_upper);out<<",\"normalTorque\":";outvec(out,b.normal_torque);out<<",\"acceleration\":";outvec(out,b.acceleration);out<<",\"accelerationLower\":";outvec(out,b.acceleration_lower);
        out<<",\"accelerationUpper\":";outvec(out,b.acceleration_upper);out<<'}';}out<<"]}";
}
support::Result query(const World& w,const support::Settings& s={}){
    const auto before=snapshot(w);const auto* pointer=w.bodies().empty()?nullptr:&w.bodies().front();const auto r=support::solve(w,s);
    check(snapshot(w)==before,"read-only query changed geometry, velocities, loads, materials, gravity or IDs");check(w.bodies().empty()||pointer==&w.bodies().front(),"query replaced World body storage");return r;
}
void ok(const support::Result& r,const support::Settings& s={}){check(r.success,"support failed: "+r.message+" ("+std::to_string(static_cast<int>(r.failure))+")");
    check(r.residuals.negative_force==0&&r.residuals.negative_acceleration<=s.acceleration_tolerance&&r.residuals.complementarity<=s.complementarity_tolerance&&r.residuals.projected_force<=s.projected_force_tolerance,"success violated complementarity tolerances");}
void fails(const World& w,support::Failure f,const support::Settings& s={}){const auto r=query(w,s);check(!r.success&&r.failure==f,"wrong support failure "+std::to_string(static_cast<int>(r.failure))+": "+r.message);}
void test(const char* name,const std::function<void()>& fn){fn();++passed;std::cout<<"PASS "<<name<<'\n';}
World ground(){World w;w.gravity={0,-10,0};w.add_plane({100});w.add_body(make_sphere(1,.5,1,{0,.5,0}));return w;}
World stack(){World w;w.gravity={0,-10,0};w.add_plane({100});for(unsigned i=0;i<3;++i){auto b=make_sphere(i+1,.5,i+1,{0,.5+i,0});b.force={0,i==0?5.:i==1?-4.:7.,0};b.torque={1,2,3};w.add_body(b);}return w;}
World curve(double speed){World w;w.gravity={0,-10,0};auto b=make_sphere(1,.5,1,{0,1,0});b.velocity={speed,0,0};w.add_body(b);w.add_body(make_sphere(2,.5,1,{},true));return w;}
World slope(){World w;w.gravity={0,-10,0};w.add_plane({100,{.6,.8,0},-.5});w.add_body(make_sphere(1,.5,1));return w;}
void fixture(const char* name,const World& w,const support::Settings& s={}){std::cout<<"{\"name\":\""<<name<<"\",\"input\":{\"world\":";outworld(std::cout,w);std::cout<<",\"settings\":";outsettings(std::cout,s);std::cout<<"},\"result\":";const auto r=query(w,s);outresult(std::cout,r);std::cout<<",\"worldUnchanged\":true}";}
void fixtures(){
    std::cout<<std::setprecision(17)<<"{\"version\":1,\"model\":\"normal-only acceleration support, no integration\",\"fixtures\":[";
    auto w=ground();fixture("planeWeight",w);std::cout<<',';w.find_body(1)->velocity={3,0,0};w.find_body(1)->angular_momentum={0,0,-.6};fixture("rollingNoFalseCentripetal",w);std::cout<<',';
    fixture("unequalLoadedStack",stack());std::cout<<',';fixture("slopeNormalOnly",slope());std::cout<<',';fixture("curvatureSupported",curve(2));std::cout<<',';fixture("curvatureDetach",curve(4));std::cout<<',';
    w=ground();w.find_body(1)->force={0,12,0};fixture("outwardForceDetach",w);std::cout<<',';w=ground();w.find_body(1)->velocity={0,1,0};fixture("separatingNotRestLcp",w);std::cout<<',';
    w=ground();w.find_body(1)->velocity={0,-1e-20,0};fixture("tinyClosingIsImpact",w);std::cout<<',';w=ground();w.add_plane({101});fixture("redundantRejected",w);std::cout<<',';
    support::Settings s;s.max_iterations=1;fixture("iterationBudgetRejected",stack(),s);std::cout<<',';w=ground();w.find_body(1)->position.y+=1e-9;fixture("explicitGuardedGeometry",w);std::cout<<"]}\n";
}
void tests(){
    test("nonorthogonal two-plane support resolves positive coupling and inactive boundary",[]{
        World w;w.gravity={0,-10,0};w.add_plane({100,{0,1,0},-.5});w.add_plane({101,{.6,.8,0},-.5});
        auto b=make_sphere(1,.5,1);b.force={-6,0,0};w.add_body(b);
        const auto coupled=query(w);ok(coupled);check(coupled.constraints.size()==2,"two oblique constraints");
        near(coupled.constraints[0].lambda,2);near(coupled.constraints[1].lambda,10);vec(coupled.bodies[0].acceleration,{});
        w.find_body(1)->force={-6,9,0};const auto released=query(w);ok(released);
        near(released.constraints[0].lambda,0);near(released.constraints[1].lambda,4.4);vec(released.bodies[0].acceleration,{-3.36,2.52});
    });
    test("independent unequal-mass pair with curvature and held force has rational reaction",[]{
        World w;w.gravity={0,-10,0};w.add_body(make_sphere(1,.5,2));
        auto b=make_sphere(2,.5,3,{0,1,0});b.velocity={3,0,0};b.force={0,-54,0};w.add_body(b);
        const auto r=query(w);ok(r);near(r.constraints[0].lambda,10.8);near(r.constraints[0].curvature[0],9);
        vec(r.bodies[0].acceleration,{0,-15.4,0});vec(r.bodies[1].acceleration,{0,-24.4,0});
    });
    test("single sphere support equals mg and is entirely read-only",[]{auto w=ground();const auto r=query(w);ok(r);check(r.constraints.size()==1&&r.resting_constraints==1,"missing support constraint");near(r.constraints[0].lambda,10);vec(r.bodies[0].force,{0,10,0});vec(r.bodies[0].acceleration,{});vec(r.bodies[0].normal_torque,{});});
    test("rolling and spinning sphere-plane support never subtracts r omega squared",[]{auto w=ground();w.find_body(1)->velocity={3,0,0};w.find_body(1)->angular_momentum={0,0,-.6};w.find_body(1)->torque={100,200,300};const auto r=query(w);ok(r);near(r.constraints[0].lambda,10);near(r.constraints[0].curvature[1],0);vec(r.bodies[0].normal_torque,{});w.find_body(1)->angular_momentum={10,20,30};const auto spun=query(w);ok(spun);near(spun.constraints[0].lambda,10);});
    test("unequal-mass three-body loaded stack matches independent cumulative weight",[]{const auto r=query(stack());ok(r);check(r.constraints.size()==3,"stack contacts");near(r.constraints[0].lambda,52);near(r.constraints[1].lambda,47);near(r.constraints[2].lambda,23);for(const auto& b:r.bodies)vec(b.acceleration,{});check(r.iterations>1,"stack not actually coupled");});
    test("unanchored touching spheres fall together with zero internal normal force",[]{World w;w.gravity={0,-10,0};w.add_body(make_sphere(1,.5,1));w.add_body(make_sphere(2,.5,2,{0,1,0}));const auto r=query(w);ok(r);near(r.constraints[0].lambda,0);for(const auto& b:r.bodies)vec(b.acceleration,{0,-10,0});});
    test("inclined plane supplies normal reaction and leaves tangential acceleration",[]{const auto r=query(slope());ok(r);near(r.constraints[0].lambda,8);vec(r.bodies[0].force,{4.8,6.4,0});vec(r.bodies[0].acceleration,{4.8,-3.6,0});check(r.constraints[0].guarded_geometry,"approximate boundary model not disclosed");});
    test("independent oblique constraints solve a symmetric wedge",[]{World w;w.gravity={0,-10,0};const double n=std::sqrt(.5);w.add_plane({100,{n,n,0},-.5});w.add_plane({101,{-n,n,0},-.5});w.add_body(make_sphere(1,.5,1));const auto r=query(w);ok(r);near(r.constraints[0].lambda,10/std::sqrt(2.));near(r.constraints[1].lambda,10/std::sqrt(2.));vec(r.bodies[0].force,{0,10,0});vec(r.bodies[0].acceleration,{});});
    test("outward acceleration detaches with lambda zero",[]{auto w=ground();w.find_body(1)->force={0,12,0};const auto r=query(w);ok(r);near(r.constraints[0].lambda,0);near(r.constraints[0].normal_acceleration,2);vec(r.bodies[0].acceleration,{0,2,0});});
    test("mass and radius scales retain SI reaction without an artificial compliance",[]{for(double mass:{1e-3,1.,1e3})for(double radius:{.005,.5,5.}){World w;w.gravity={0,-10,0};w.add_plane({100});w.add_body(make_sphere(1,radius,mass,{0,radius,0}));const auto r=query(w);ok(r);near(r.constraints[0].lambda,10*mass,1e-7);vec(r.bodies[0].acceleration,{});}World tiny;tiny.gravity={std::numeric_limits<double>::denorm_min(),0,0};tiny.add_body(make_sphere(1,.5,1));const auto t=query(tiny);ok(t);check(t.bodies[0].acceleration.x==tiny.gravity.x,"subnormal interval midpoint silently vanished");});
    test("sphere-pair tangent curvature reduces support and permits detachment",[]{auto r=query(curve(2));ok(r);near(r.constraints[0].lambda,6);near(r.constraints[0].curvature[0],4);near(r.constraints[0].normal_acceleration,0);vec(r.bodies[0].acceleration,{0,-4,0});vec(r.bodies[1].acceleration,{});vec(r.bodies[1].force,{0,-6,0});r=query(curve(4));ok(r);near(r.constraints[0].lambda,0);near(r.constraints[0].normal_acceleration,6);});
    test("moving unequal-mass pair uses relative acceleration and curvature",[]{World w;w.gravity={0,-10,0};w.add_body(make_sphere(1,.5,1));auto b=make_sphere(2,.5,2,{0,1,0});b.velocity={2,0,0};b.force={0,-20,0};w.add_body(b);const auto r=query(w);ok(r);near(r.constraints[0].lambda,4);vec(r.bodies[0].force,{0,-4,0});vec(r.bodies[1].force,{0,4,0});vec(r.bodies[0].acceleration,{0,-14,0});vec(r.bodies[1].acceleration,{0,-18,0});});
    test("provably separating velocity has lambda zero outside the rest LCP",[]{auto w=ground();w.find_body(1)->velocity={0,1,0};const auto r=query(w);ok(r);check(r.separating_constraints==1&&r.resting_constraints==0,"separating contact misclassified");near(r.constraints[0].lambda,0);near(r.constraints[0].normal_acceleration,-10);});
    test("even tiny closing velocity requires an impact; cancellation uncertainty fails",[]{auto w=ground();w.find_body(1)->velocity={0,-1e-20,0};fails(w,support::Failure::impact_required);w=slope();w.find_body(1)->velocity={.8,-.6,0};fails(w,support::Failure::velocity_uncertain);w.find_body(1)->velocity={};ok(query(w));});
    test("contact band is explicit and never projects or erases deep penetration",[]{auto w=ground();w.find_body(1)->position.y+=1e-9;const auto r=query(w);ok(r);check(r.maximum_geometry_offset>0&&r.constraints[0].gap[0]>0,"near-gap approximation not exposed");near(r.constraints[0].lambda,10);w.find_body(1)->position.y=.5+2e-8;const auto separated=query(w);ok(separated);check(separated.constraints.empty()&&separated.separated_pairs==1,"far gap was supported");vec(separated.bodies[0].acceleration,{0,-10,0});w.find_body(1)->position.y=.5-2e-8;fails(w,support::Failure::geometry_incompatible);});
    test("static-static and coincident geometry are explicit failures",[]{auto w=ground();w.find_body(1)->is_static=true;fails(w,support::Failure::static_constraint);World pair;pair.add_body(make_sphere(1,.5,1));pair.add_body(make_sphere(2,.5,1));fails(pair,support::Failure::geometry_uncertain);});
    test("singular duplicate and near-parallel normals reject without regularization",[]{auto w=ground();w.add_plane({101});fails(w,support::Failure::ill_conditioned);World near_parallel;near_parallel.gravity={0,-10,0};near_parallel.add_plane({100,{0,1,0},-.5});near_parallel.add_plane({101,{1e-7,std::sqrt(1-1e-14),0},-.5});near_parallel.add_body(make_sphere(1,.5,1));fails(near_parallel,support::Failure::ill_conditioned);});
    test("iteration/contact/pair budgets fail with residuals and allow reuse",[]{auto w=stack();support::Settings s;s.max_iterations=1;const auto r=query(w,s);check(!r.success&&r.failure==support::Failure::iteration_budget,"iteration budget");check(r.residuals.negative_acceleration>0||r.residuals.complementarity>0,"failure residuals silently zero");s={};s.max_contacts=1;fails(w,support::Failure::contact_budget,s);s={};s.max_pair_queries=1;fails(w,support::Failure::pair_budget,s);ok(query(w));});
    test("unattainable numerical residuals fail instead of nominal convergence",[]{auto w=ground();support::Settings s;s.acceleration_tolerance=1e-30;s.complementarity_tolerance=1e-30;s.projected_force_tolerance=1e-30;fails(w,support::Failure::numerical_uncertainty,s);ok(query(w));});
    test("reaction is translation invariant and independent of stable ID ordering",[]{auto w=stack();const auto r=query(w);ok(r);World shifted;shifted.gravity=w.gravity;shifted.add_plane({100,{0,1,0},20});for(auto b:w.bodies()){b.position=b.position+Vec3{100,20,300};b.id=4-b.id;shifted.add_body(b);}const auto s=query(shifted);ok(s);for(const auto& b:s.bodies){const auto original=4-b.id;const auto& before=r.bodies[original-1];vec(b.force,before.force);vec(b.acceleration,{});}});
    test("settings and mutated body input reject read-only then recover",[]{auto w=ground();support::Settings s;s.max_iterations=0;fails(w,support::Failure::invalid_input,s);s={};s.gap_tolerance=1;fails(w,support::Failure::invalid_input,s);w.find_body(1)->mass=0;fails(w,support::Failure::invalid_input);w.find_body(1)->mass=1;w.find_body(1)->force={0,1e24,0};fails(w,support::Failure::invalid_input);w.find_body(1)->force={};ok(query(w));});
}
}
int main(int argc,char** argv){try{if(argc>1&&std::string(argv[1])=="--fixtures")fixtures();else{tests();std::cout<<passed<<" support test groups passed\n";}return 0;}catch(const std::exception& e){std::cerr<<"FAIL after "<<passed<<" groups: "<<e.what()<<'\n';return 1;}}
