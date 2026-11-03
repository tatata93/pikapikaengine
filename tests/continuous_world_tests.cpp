#include "pikapika/dynamics.hpp"
#include <bit>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace pikapika;
using namespace pikapika::dynamics;
namespace {
unsigned passed=0;
void check(bool b,const std::string& message) {if(!b)throw std::runtime_error(message);}
void near(double a,double b,double tol=1e-10) {check(std::abs(a-b)<=tol,"analytical tolerance: "+std::to_string(a)+" != "+std::to_string(b));}
void vec(Vec3 a,Vec3 b,double tol=1e-10) {near(a.x,b.x,tol);near(a.y,b.y,tol);near(a.z,b.z,tol);}
void out_vec(std::ostream& out,Vec3 v) {out<<'['<<v.x<<','<<v.y<<','<<v.z<<']';}
void out_input(std::ostream& out,const World& w) {
    out<<"{\"gravity\":";out_vec(out,w.gravity);out<<",\"bodies\":[";bool comma=false;
    for(const auto& b:w.bodies()) {
        if(comma)out<<',';comma=true;
        out<<"{\"id\":"<<b.id<<",\"isStatic\":"<<(b.is_static?"true":"false")<<",\"mass\":"<<b.mass<<",\"radius\":"<<b.radius
            <<",\"inertiaDiagonal\":";out_vec(out,b.inertia_diagonal);out<<",\"position\":";out_vec(out,b.position);
        out<<",\"velocity\":";out_vec(out,b.velocity);out<<",\"angularMomentum\":";out_vec(out,b.angular_momentum);
        out<<",\"orientation\":["<<b.orientation.x<<','<<b.orientation.y<<','<<b.orientation.z<<','<<b.orientation.w<<"],\"force\":";out_vec(out,b.force);
        out<<",\"torque\":";out_vec(out,b.torque);out<<",\"material\":{\"restitution\":"<<b.material.restitution<<",\"friction\":"<<b.material.friction<<"}}";
    }
    out<<"],\"planes\":[";comma=false;for(const auto& p:w.planes()) {
        if(comma)out<<',';comma=true;out<<"{\"id\":"<<p.id<<",\"normal\":";out_vec(out,p.normal);
        out<<",\"offset\":"<<p.offset<<",\"material\":{\"restitution\":"<<p.material.restitution<<",\"friction\":"<<p.material.friction<<"}}";
    }
    out<<"]}";
}
std::string snapshot(const World& w) {
    std::ostringstream out;out<<std::setprecision(17);
    for(const auto& b:w.bodies()) {
        out<<b.id<<','<<b.is_static<<','<<b.mass<<','<<b.radius<<',';out_vec(out,b.position);out_vec(out,b.velocity);
        out_vec(out,b.angular_momentum);out_vec(out,b.force);out_vec(out,b.torque);out_vec(out,b.inertia_diagonal);
        out<<b.orientation.x<<','<<b.orientation.y<<','<<b.orientation.z<<','<<b.orientation.w<<','<<b.material.restitution<<','<<b.material.friction<<';';
    }
    return out.str();
}
void ok(const CcdReport& r) {check(r.success,"W1 failed: "+r.message+" ("+std::to_string(static_cast<int>(r.failure))+")");}
void rejects(World& w,double dt,const CcdSettings& s,CcdFailure expected) {
    const auto before=snapshot(w);const auto* ptr=w.bodies().empty()?nullptr:&w.bodies().front();
    const auto r=w.step_continuous(dt,s);check(!r.success,"expected transactional failure");
    check(r.failure==expected,"unexpected failure code "+std::to_string(static_cast<int>(r.failure))+": "+r.message);
    check(r.advanced_dt==0&&snapshot(w)==before,"failed tick changed body state or loads");
    check(w.bodies().empty()||ptr==&w.bodies().front(),"failed tick replaced body storage");
}
void test(const char* name,const std::function<void()>& fn) {fn();++passed;std::cout<<"PASS "<<name<<'\n';}
RigidBody ball(std::uint64_t id,Vec3 p,Vec3 v={},double mass=1) {
    auto b=make_sphere(id,0.5,mass,p);b.velocity=v;b.material={1,0};return b;
}
Plane wall(std::uint64_t id,Vec3 n,double d) {return {id,n,d,{1,0}};}
World corridor() {
    World w;w.gravity={0,-9.8,0};w.add_plane(wall(100,{1,0,0},-1.5));w.add_plane(wall(101,{-1,0,0},-1.5));
    auto b=ball(1,{}, {100,0,0});b.force={0,4,0};w.add_body(b);return w;
}
void analytic_bracket(const CcdReport& r,std::size_t i,double expected,double tolerance=2e-12) {
    check(i<r.events.size(),"missing event");const auto& e=r.events[i];
    check(e.entry_lower<=expected+tolerance&&e.entry_upper>=expected-tolerance,"independent root outside entry bracket");
    check(e.responded_at<=expected+tolerance&&expected-e.responded_at<=1e-7,"early response time guard");
    check(e.maximum_gap<=1e-6&&e.maximum_gap>0,"spatial guard");
}
void fixtures() {
    auto w=corridor();const auto initial=w;const auto report=w.step_continuous(0.06);ok(report);
    std::cout<<std::setprecision(17)<<"{\"version\":1,\"model\":\"held-load early-response W1\",\"dt\":0.06,\"input\":";
    out_input(std::cout,initial);std::cout<<",\"settings\":{\"timeTolerance\":1e-7,\"spatialTolerance\":1e-6,\"profile\":\"CcdSettings defaults W1\"},\"success\":true,\"events\":[";
    bool comma=false;for(const auto& e:report.events) {
        if(comma)std::cout<<',';comma=true;
        std::cout<<"{\"respondedAt\":"<<e.responded_at<<",\"entryLower\":"<<e.entry_lower<<",\"entryUpper\":"<<e.entry_upper
            <<",\"maximumGap\":"<<e.maximum_gap<<",\"propagationError\":"<<e.propagation_error<<",\"contacts\":"<<e.contacts<<'}';
    }
    std::cout<<"],\"bodies\":[";comma=false;for(const auto& b:w.bodies()) {
        if(comma)std::cout<<',';comma=true;std::cout<<"{\"id\":"<<b.id<<",\"position\":";out_vec(std::cout,b.position);
        std::cout<<",\"velocity\":";out_vec(std::cout,b.velocity);std::cout<<",\"angularMomentum\":";out_vec(std::cout,b.angular_momentum);
        std::cout<<",\"orientation\":["<<b.orientation.x<<','<<b.orientation.y<<','<<b.orientation.z<<','<<b.orientation.w<<"],\"force\":";out_vec(std::cout,b.force);
        std::cout<<",\"torque\":";out_vec(std::cout,b.torque);std::cout<<'}';
    }
    std::cout<<"],\"queries\":"<<report.pair_queries<<",\"evaluations\":"<<report.root_evaluations<<",\"freeSegments\":"<<report.free_segments
        <<",\"maximumPropagationError\":"<<report.maximum_propagation_error<<",\"accumulatedPositionRoundoff\":"<<report.accumulated_position_roundoff
        <<",\"timeRoundoff\":"<<report.time_roundoff<<",\"refinement\":[";
    comma=false;for(double space:{1e-4,1e-6,1e-8}) {
        auto case_world=corridor();CcdSettings s;s.spatial_tolerance=space;const auto r=case_world.step_continuous(.06,s);ok(r);
        if(comma)std::cout<<',';comma=true;std::cout<<"{\"spaceTolerance\":"<<space<<",\"finalPositionX\":"<<case_world.find_body(1)->position.x
            <<",\"absoluteError\":"<<std::abs(case_world.find_body(1)->position.x)<<",\"eventCount\":"<<r.events.size()<<'}';
    }
    auto rejected=corridor();const auto before=snapshot(rejected);CcdSettings s;s.max_event_batches=1;
    const auto failed=rejected.step_continuous(.06,s);
    std::cout<<"],\"rollback\":{\"failure\":"<<static_cast<int>(failed.failure)<<",\"advancedDt\":"<<failed.advanced_dt
        <<",\"candidateTime\":"<<failed.candidate_time<<",\"stateUnchanged\":"<<(before==snapshot(rejected)?"true":"false")<<"}}\n";
}
void tests() {
    test("no-contact held gravity/force/torque matches legacy step byte for byte",[] {
        World a;a.gravity={0.1,-9.8,0.3};auto b=ball(1,{2,30,4},{1,2,3},2);b.inertia_diagonal={2,3,4};
        b.angular_momentum={0.2,0.3,0.4};b.force={6,-4,2};b.torque={0.7,0.8,-0.5};a.add_body(b);
        auto old=a;old.step(0.03);const auto* ptr=a.find_body(1);const auto r=a.step_continuous(0.03);ok(r);
        check(snapshot(a)==snapshot(old),"no-contact legacy numeric drift");check(ptr==a.find_body(1),"successful commit replaced body storage");
        check(r.events.empty()&&r.free_segments==1&&r.advanced_dt==0.03,"no-contact report");
        vec(a.find_body(1)->position,{2.031395,30.05469,4.090585});
    });
    test("high-speed plane crossing cannot tunnel",[] {
        World w;w.gravity={0,-10,0};w.add_plane(wall(100,{0,1,0},0));w.add_body(ball(1,{0,2,0},{0,-10000,0}));
        const auto r=w.step_continuous(0.001);ok(r);check(r.events.size()==1,"one plane event");
        const double root=3/(10000+std::sqrt(100000000+30));analytic_bracket(r,0,root,1e-11);
        const double impact_v=-10000-10*root,tail=0.001-root;
        near(w.find_body(1)->velocity.y,-impact_v-10*tail,1e-5);
        near(w.find_body(1)->position.y,0.5-impact_v*tail-5*tail*tail,3e-6);
    });
    test("two moving spheres retain gravity and exchange equal-mass velocity",[] {
        World w;w.gravity={0,-10,0};w.add_body(ball(1,{-2,0,0},{100,0,0}));w.add_body(ball(2,{2,0,0},{-100,0,0}));
        const auto r=w.step_continuous(0.03);ok(r);check(r.events.size()==1,"pair event");analytic_bracket(r,0,0.015);
        vec(w.find_body(1)->position,{-2,-0.0045,0},3e-6);vec(w.find_body(2)->position,{2,-0.0045,0},3e-6);
        vec(w.find_body(1)->velocity,{-100,-0.3,0},1e-9);vec(w.find_body(2)->velocity,{100,-0.3,0},1e-9);
    });
    test("different force over mass produces accelerated pair collision",[] {
        World w;w.gravity={0,-9.8,0};auto a=ball(1,{-2,0,0},{},1);a.force={400,0,0};w.add_body(a);
        auto b=ball(2,{2,0,0},{},2);b.force={-800,0,0};w.add_body(b);
        const auto r=w.step_continuous(0.1);ok(r);check(r.events.size()==1,"accelerated pair event");
        const double t=std::sqrt(3./400),tail=.1-t;analytic_bracket(r,0,t);
        const double u=400*t,v=-400*t,va=(-u+4*v)/3.,vb=(2*u+v)/3.;
        near(w.find_body(1)->velocity.x,va+400*tail,1e-5);near(w.find_body(2)->velocity.x,vb-400*tail,1e-5);
        near(w.find_body(1)->position.y,-.049,1e-12);near(w.find_body(2)->position.y,-.049,1e-12);
        check(w.find_body(1)->force.length()==0&&w.find_body(2)->force.length()==0,"loads not consumed once");
    });
    test("unequal mass momentum and restitution",[] {
        World w;w.gravity={};w.add_body(ball(1,{-3,0,0},{100,0,0},1));w.add_body(ball(2,{0,0,0},{},3));
        const auto r=w.step_continuous(.03);ok(r);analytic_bracket(r,0,.02);
        vec(w.find_body(1)->velocity,{-50,0,0});vec(w.find_body(2)->velocity,{50,0,0});
        near(w.find_body(1)->position.x,-1.5,3e-6);near(w.find_body(2)->position.x,.5,3e-6);
        near(w.find_body(1)->velocity.x+3*w.find_body(2)->velocity.x,100);
    });
    test("curved relative trajectory solves a genuine quartic first entry",[] {
        World w;w.gravity={0,-10,0};auto b=ball(1,{-2,0,0},{24,0,0});b.force={0,490,0};w.add_body(b);
        b=ball(2,{});b.is_static=true;w.add_body(b);const auto r=w.step_continuous(.055);ok(r);
        // F(t)=(-2+24t)^2+(240t^2)^2-1. F(.05)=0 and F'(.05)=-9.6.
        // F''>0, so this negative derivative proves this is the first entry.
        analytic_bracket(r,0,.05,1e-12);check(r.events.size()==1,"quartic event count");
        vec(w.find_body(1)->velocity,{16.32,32.16,0},5e-4);
        vec(w.find_body(1)->position,{-.7184,.7548,0},5e-6);
    });
    test("three impacts in one tick preserve remaining time and held gravity/force",[] {
        auto w=corridor();const auto r=w.step_continuous(.06);ok(r);check(r.events.size()==3,"three wall impacts");
        near(w.find_body(1)->position.x,0,8e-6);near(w.find_body(1)->velocity.x,-100,1e-9);
        near(w.find_body(1)->position.y,-.5*5.8*.06*.06,1e-12);near(w.find_body(1)->velocity.y,-5.8*.06,1e-12);
        check(r.free_segments==4,"remaining segment was dropped");check(r.time_roundoff<1e-15,"time composition roundoff");
    });
    test("spatial guard refinement reduces independently known multi-impact position error",[] {
        auto coarse=corridor(),medium=corridor(),fine=corridor();CcdSettings s;s.spatial_tolerance=1e-4;
        ok(coarse.step_continuous(.06,s));s.spatial_tolerance=1e-6;ok(medium.step_continuous(.06,s));
        s.spatial_tolerance=1e-8;ok(fine.step_continuous(.06,s));
        const double a=std::abs(coarse.find_body(1)->position.x),b=std::abs(medium.find_body(1)->position.x),c=std::abs(fine.find_body(1)->position.x);
        check(b<a/4&&c<b/4,"early response does not converge as guard is refined");
        check(c<1e-8,"refined multi-impact final error");
    });
    test("three-body sequential impact propagates all bodies at each event",[] {
        World w;w.gravity={0,-10,0};w.add_body(ball(1,{-3,0,0},{100,0,0}));w.add_body(ball(2,{}));w.add_body(ball(3,{3,0,0}));
        const auto r=w.step_continuous(.06);ok(r);check(r.events.size()==2,"two chain events");
        near(w.find_body(1)->position.x,-1,3e-6);near(w.find_body(2)->position.x,2,3e-6);near(w.find_body(3)->position.x,5,3e-6);
        for(const auto& b:w.bodies()){near(b.position.y,-.018,1e-12);near(b.velocity.y,-.6,1e-12);}
    });
    test("simultaneous three-body batch is solved together",[] {
        World w;w.gravity={};w.add_body(ball(1,{-3,0,0},{100,0,0}));w.add_body(ball(2,{}));w.add_body(ball(3,{3,0,0},{-100,0,0}));
        CcdSettings s;s.solver.velocity_iterations=64;const auto r=w.step_continuous(.03,s);ok(r);
        check(r.events.size()==1&&r.events[0].contacts==2,"simultaneous contacts not batched");
        near(w.find_body(1)->velocity.x,-100,1e-9);near(w.find_body(2)->velocity.x,0,1e-9);near(w.find_body(3)->velocity.x,100,1e-9);
    });
    test("torque and static loads survive all intervals then consume once",[] {
        auto w=corridor();auto b=ball(2,{0,100,100});b.inertia_diagonal={2,3,4};b.angular_momentum={0,0,1.2};b.torque={0,0,8};w.add_body(b);
        b=make_sphere(3,.5,1,{100,100,100},true);b.force={2,3,4};b.torque={5,6,7};w.add_body(b);
        const auto r=w.step_continuous(.06);ok(r);const auto* rotating=w.find_body(2);
        near(rotating->angular_momentum.z,1.2+8*.06,1e-12);const double angle=.3*.06+.06*.06;
        vec(rotating->orientation.rotate({1,0,0}),{std::cos(angle),std::sin(angle),0},1e-12);
        check(rotating->torque.length()==0&&w.find_body(3)->force.length()==0&&w.find_body(3)->torque.length()==0,"load consumption");
        vec(w.find_body(3)->position,{100,100,100});
    });
    test("oblique frictional impact audits kinetic energy and angular impulse",[] {
        World w;w.gravity={0,-10,0};w.add_plane({100,{0,1,0},0,{.7,.5}});auto b=ball(1,{0,2,0},{20,-100,0});b.material={.7,.5};w.add_body(b);
        const auto r=w.step_continuous(.025);ok(r);check(r.impact_stats.friction_impulse_sum>0,"no friction impulse");
        check(std::abs(w.find_body(1)->angular_momentum.z)>0,"friction failed to transfer torque");
        check(w.find_body(1)->kinetic_energy()<5200,"friction/restitution created energy");
    });
    test("static sphere and arbitrarily oriented plane use actual geometry",[] {
        World w;w.gravity={0,-10,0};auto a=ball(1,{-2,0,0},{100,0,0});w.add_body(a);
        auto fixed=ball(2,{});fixed.is_static=true;w.add_body(fixed);
        const auto r=w.step_continuous(.02);ok(r);check(r.events.size()==1,"static sphere event");
        near(w.find_body(1)->velocity.x,-100,1e-3);vec(w.find_body(2)->position,{});
        World plane;plane.gravity={};const Vec3 n{.6,.8,0};plane.add_plane(wall(100,n,0));
        plane.add_body(ball(1,n*2,n*(-100)));const auto rr=plane.step_continuous(.03);ok(rr);analytic_bracket(rr,0,.015,1e-12);
        vec(plane.find_body(1)->velocity,n*100,1e-10);vec(plane.find_body(1)->position,n*2,3e-6);
    });
    test("pair translation and common velocity preserve impact response",[] {
        World base;base.gravity={0,-10,0};base.add_body(ball(1,{-2,0,0},{100,0,0}));base.add_body(ball(2,{2,0,0},{-100,0,0}));
        World moved;moved.gravity=base.gravity;const Vec3 shift{1000,-30,500},boost{3,4,5};
        for(auto b:base.bodies()){b.position=b.position+shift;b.velocity=b.velocity+boost;moved.add_body(b);}
        ok(base.step_continuous(.03));const auto r=moved.step_continuous(.03);ok(r);check(r.events.size()==1,"translated event");
        for(std::uint64_t id:{1,2}) {
            vec(moved.find_body(id)->position,base.find_body(id)->position+shift+boost*.03,5e-6);
            vec(moved.find_body(id)->velocity,base.find_body(id)->velocity+boost,1e-9);
        }
    });
    test("initial boundary and overlap fail without touching state",[] {
        World w;w.add_plane(wall(100,{0,1,0},0));auto b=ball(1,{0,.5,0},{0,2,0});b.force={1,2,3};w.add_body(b);
        rejects(w,.01,{},CcdFailure::initial_contact);w.find_body(1)->position.y=.49;rejects(w,.01,{},CcdFailure::initial_contact);
    });
    test("inelastic gravity contact explicitly requests W2 support",[] {
        World w;w.gravity={0,-10,0};w.add_plane({100,{0,1,0},0,{0,0}});auto b=ball(1,{0,.6,0},{0,-2,0});b.material={0,0};b.force={1,0,0};w.add_body(b);
        rejects(w,.1,{},CcdFailure::sustained_contact_required);
    });
    test("root and pair query budgets roll back and permit reuse",[] {
        auto w=corridor();CcdSettings s;s.max_root_evaluations=1;rejects(w,.06,s,CcdFailure::root_budget);
        s={};s.max_pair_queries=1;rejects(w,.06,s,CcdFailure::query_budget);
        const auto r=w.step_continuous(.06);ok(r);check(r.events.size()==3,"world unusable after rejected tick");
    });
    test("event/segment/contact budgets restore state and held loads",[] {
        auto w=corridor();CcdSettings s;s.max_event_batches=1;rejects(w,.06,s,CcdFailure::event_budget);
        s={};s.max_free_segments=1;rejects(w,.06,s,CcdFailure::segment_budget);
        World pair;pair.gravity={};pair.add_body(ball(1,{-3,0,0},{100,0,0}));pair.add_body(ball(2,{}));pair.add_body(ball(3,{3,0,0},{-100,0,0}));
        s={};s.solver.max_contacts=1;rejects(pair,.03,s,CcdFailure::solver_failure);
    });
    test("horizon-only contact and tangent are unresolved, never no hit",[] {
        World w;w.gravity={};w.add_plane(wall(100,{0,1,0},0));w.add_body(ball(1,{0,1.5,0},{0,-10,0}));
        rejects(w,.1,{},CcdFailure::query_unresolved);
        World tangent;tangent.gravity={};tangent.add_body(ball(1,{-2,1,0},{40,0,0}));tangent.add_body(ball(2,{}, {},1));tangent.find_body(2)->is_static=true;
        rejects(tangent,.1,{},CcdFailure::query_unresolved);
    });
    test("large-coordinate roundoff guard and invalid settings reject atomically",[] {
        World w;w.gravity={};w.add_body(ball(1,{1e12,0,0}));rejects(w,.01,{},CcdFailure::geometric_guard);
        auto normal=corridor();CcdSettings s;s.solver.position_correction=.1;rejects(normal,.06,s,CcdFailure::invalid_input);
        s={};s.spatial_tolerance=1e-2;rejects(normal,.06,s,CcdFailure::invalid_input);
        rejects(normal,0,{},CcdFailure::invalid_input);
        normal.find_body(1)->id=100;rejects(normal,.06,{},CcdFailure::invalid_input);
    });
    test("angular propagation and solver residual failures also roll back",[] {
        World rotating;rotating.gravity={};auto b=ball(1,{});b.angular_momentum={0,0,100};b.torque={0,0,1};rotating.add_body(b);
        rejects(rotating,.1,{},CcdFailure::propagation_failure);
        World batch;batch.gravity={};batch.add_body(ball(1,{-3,0,0},{100,0,0}));batch.add_body(ball(2,{}));batch.add_body(ball(3,{3,0,0},{-100,0,0}));
        CcdSettings s;s.solver.velocity_iterations=1;rejects(batch,.03,s,CcdFailure::solver_failure);
        rotating.find_body(1)->angular_momentum={};ok(rotating.step_continuous(.001));
    });
}
}
int main(int argc,char** argv) {
    try {if(argc>1&&std::string(argv[1])=="--fixtures")fixtures();else{tests();std::cout<<passed<<" continuous-world test groups passed\n";}return 0;}
    catch(const std::exception& e){std::cerr<<"FAIL after "<<passed<<" groups: "<<e.what()<<'\n';return 1;}
}
