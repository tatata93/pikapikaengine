// Original finite compatibility corpus using existing public World APIs only.
#include "pikapika/dynamics.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
using namespace pikapika;
using namespace pikapika::dynamics;
void require(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void number(double value){require(std::isfinite(value),"Nonfinite legacy proof field");if(value==0&&std::signbit(value)){std::cout<<"-0";}else{std::cout<<value;}}
void boolean(bool value){std::cout<<(value?"true":"false");}
void string(const std::string& value){std::cout<<'"';for(unsigned char c:value){switch(c){case '"':std::cout<<"\\\"";break;case '\\':std::cout<<"\\\\";break;case '\n':std::cout<<"\\n";break;case '\r':std::cout<<"\\r";break;case '\t':std::cout<<"\\t";break;default:if(c<32){std::cout<<"\\u00"<<"0123456789abcdef"[c>>4]<<"0123456789abcdef"[c&15];}else{std::cout<<char(c);}break;}}std::cout<<'"';}
void vec(Vec3 v){std::cout<<'[';number(v.x);std::cout<<',';number(v.y);std::cout<<',';number(v.z);std::cout<<']';}
void material(const Material& m){std::cout<<"{\"restitution\":";number(m.restitution);std::cout<<",\"friction\":";number(m.friction);std::cout<<'}';}
void body(const RigidBody& b){
    std::cout<<"{\"id\":"<<b.id<<",\"isStatic\":";boolean(b.is_static);std::cout<<",\"mass\":";number(b.mass);std::cout<<",\"radius\":";number(b.radius);std::cout<<",\"inertiaDiagonal\":";vec(b.inertia_diagonal);
    std::cout<<",\"position\":";vec(b.position);std::cout<<",\"velocity\":";vec(b.velocity);std::cout<<",\"angularMomentum\":";vec(b.angular_momentum);
    std::cout<<",\"orientation\":[";number(b.orientation.x);std::cout<<',';number(b.orientation.y);std::cout<<',';number(b.orientation.z);std::cout<<',';number(b.orientation.w);
    std::cout<<"],\"force\":";vec(b.force);std::cout<<",\"torque\":";vec(b.torque);std::cout<<",\"material\":";material(b.material);std::cout<<'}';
}
void world(const World& w){
    std::cout<<"{\"gravity\":";vec(w.gravity);std::cout<<",\"bodies\":[";
    for(std::size_t i=0;i<w.bodies().size();++i){if(i){std::cout<<',';}body(w.bodies()[i]);}
    std::cout<<"],\"planes\":[";for(std::size_t i=0;i<w.planes().size();++i){if(i){std::cout<<',';}const auto& p=w.planes()[i];std::cout<<"{\"id\":"<<p.id<<",\"normal\":";vec(p.normal);std::cout<<",\"offset\":";number(p.offset);std::cout<<",\"material\":";material(p.material);std::cout<<'}';}std::cout<<"]}";
}
std::string snapshot(const World& w){std::ostringstream out;auto* before=std::cout.rdbuf(out.rdbuf());try{world(w);}catch(...){std::cout.rdbuf(before);throw;}std::cout.rdbuf(before);return out.str();}
void settings(const CcdSettings& s){
    std::cout<<"{\"timeTolerance\":";number(s.time_tolerance);std::cout<<",\"spatialTolerance\":";number(s.spatial_tolerance);std::cout<<",\"minimumImpactSpeed\":";number(s.minimum_impact_speed);
    std::cout<<",\"closingResidualTolerance\":";number(s.closing_residual_tolerance);std::cout<<",\"relativeEnergyTolerance\":";number(s.relative_energy_tolerance);
    std::cout<<",\"maxEventBatches\":"<<s.max_event_batches<<",\"maxFreeSegments\":"<<s.max_free_segments<<",\"maxPairQueries\":"<<s.max_pair_queries<<",\"maxRootEvaluations\":"<<s.max_root_evaluations<<",\"queryEvaluations\":"<<s.query_evaluations<<",\"queryFrontier\":"<<s.query_frontier<<",\"queryDepth\":"<<s.query_depth;
    const auto& p=s.solver;std::cout<<",\"solver\":{\"velocityIterations\":"<<p.velocity_iterations<<",\"maxContacts\":"<<p.max_contacts<<",\"contactMargin\":";number(p.contact_margin);std::cout<<",\"penetrationSlop\":";number(p.penetration_slop);std::cout<<",\"positionCorrection\":";number(p.position_correction);std::cout<<",\"maxPositionCorrection\":";number(p.max_position_correction);std::cout<<",\"restitutionVelocityThreshold\":";number(p.restitution_velocity_threshold);std::cout<<",\"maxAngularIncrement\":";number(p.max_angular_increment);std::cout<<"}}";
}
void stats(const StepStats& s){std::cout<<"{\"contacts\":"<<s.contacts<<",\"velocityIterations\":"<<s.velocity_iterations<<",\"maxPenetration\":";number(s.max_penetration);std::cout<<",\"normalImpulseSum\":";number(s.normal_impulse_sum);std::cout<<",\"frictionImpulseSum\":";number(s.friction_impulse_sum);std::cout<<",\"maxClosingResidual\":";number(s.max_closing_residual);std::cout<<'}';}
void report(const CcdReport& r){
    std::cout<<"{\"success\":";boolean(r.success);std::cout<<",\"failure\":"<<unsigned(r.failure)<<",\"message\":";string(r.message);std::cout<<",\"advancedDt\":";number(r.advanced_dt);std::cout<<",\"candidateTime\":";number(r.candidate_time);
    std::cout<<",\"firstId\":"<<r.first_id<<",\"secondId\":"<<r.second_id<<",\"pairQueries\":"<<r.pair_queries<<",\"rootEvaluations\":"<<r.root_evaluations<<",\"freeSegments\":"<<r.free_segments<<",\"maximumPropagationError\":";number(r.maximum_propagation_error);std::cout<<",\"accumulatedPositionRoundoff\":";number(r.accumulated_position_roundoff);std::cout<<",\"timeRoundoff\":";number(r.time_roundoff);std::cout<<",\"impactStats\":";stats(r.impact_stats);
    std::cout<<",\"events\":[";for(std::size_t i=0;i<r.events.size();++i){if(i){std::cout<<',';}const auto& e=r.events[i];std::cout<<"{\"respondedAt\":";number(e.responded_at);std::cout<<",\"entryLower\":";number(e.entry_lower);std::cout<<",\"entryUpper\":";number(e.entry_upper);std::cout<<",\"maximumGap\":";number(e.maximum_gap);std::cout<<",\"propagationError\":";number(e.propagation_error);std::cout<<",\"firstId\":"<<e.first_id<<",\"secondId\":"<<e.second_id<<",\"contacts\":"<<e.contacts<<'}';}std::cout<<"]}";
}
RigidBody ball(std::uint64_t id,Vec3 p,Vec3 v={},double mass=1){auto b=make_sphere(id,.5,mass,p);b.velocity=v;b.material={1,0};return b;}
Plane wall(std::uint64_t id,Vec3 normal,double offset){return {id,normal,offset,{1,0}};}
World corridor(){World w;w.gravity={0,-9.8,0};w.add_plane(wall(100,{1,0,0},-1.5));w.add_plane(wall(101,{-1,0,0},-1.5));auto b=ball(1,{}, {100,0,0});b.force={0,4,0};w.add_body(b);return w;}
struct Case{std::string name;World input;double duration{.03};CcdSettings profile;bool success{true};};
std::vector<Case> cases(){
    std::vector<Case> out;auto add=[&](Case c){out.push_back(std::move(c));};Case c;
    c.name="held-gravity-force-torque-no-contact";c.input.gravity={.1,-9.8,.3};auto b=ball(1,{2,30,4},{1,2,3},2);b.inertia_diagonal={2,3,4};b.angular_momentum={.2,.3,.4};b.force={6,-4,2};b.torque={.7,.8,-.5};c.input.add_body(b);add(c);
    c=Case{};c.name="fast-plane";c.duration=.001;c.input.gravity={0,-10,0};c.input.add_plane(wall(100,{0,1,0},0));c.input.add_body(ball(1,{0,2,0},{0,-10000,0}));add(c);
    c=Case{};c.name="moving-equal-pair";c.input.gravity={0,-10,0};c.input.add_body(ball(1,{-2,0,0},{100,0,0}));c.input.add_body(ball(2,{2,0,0},{-100,0,0}));add(c);
    c=Case{};c.name="accelerated-unequal-pair";c.duration=.1;c.input.gravity={0,-9.8,0};b=ball(1,{-2,0,0},{},1);b.force={400,0,0};c.input.add_body(b);b=ball(2,{2,0,0},{},2);b.force={-800,0,0};c.input.add_body(b);add(c);
    c=Case{};c.name="unequal-mass-restitution";c.input.gravity={};c.input.add_body(ball(1,{-3,0,0},{100,0,0},1));c.input.add_body(ball(2,{0,0,0},{},3));add(c);
    c=Case{};c.name="three-events-held-force";c.input=corridor();c.duration=.06;add(c);
    c.name="three-events-coarse-space";c.profile.spatial_tolerance=1e-4;add(c);c.name="three-events-fine-space";c.profile.spatial_tolerance=1e-8;add(c);
    c=Case{};c.name="three-body-sequential";c.duration=.06;c.input.gravity={0,-10,0};c.input.add_body(ball(1,{-3,0,0},{100,0,0}));c.input.add_body(ball(2,{}));c.input.add_body(ball(3,{3,0,0}));add(c);
    c=Case{};c.name="simultaneous-three-body";c.input.gravity={};c.input.add_body(ball(1,{-3,0,0},{100,0,0}));c.input.add_body(ball(2,{}));c.input.add_body(ball(3,{3,0,0},{-100,0,0}));c.profile.solver.velocity_iterations=64;add(c);
    c=Case{};c.name="torque-and-static-loads";c.input=corridor();c.duration=.06;b=ball(2,{0,100,100});b.inertia_diagonal={2,3,4};b.angular_momentum={0,0,1.2};b.torque={0,0,8};c.input.add_body(b);b=make_sphere(3,.5,1,{100,100,100},true);b.force={2,3,4};b.torque={5,6,7};c.input.add_body(b);add(c);
    c=Case{};c.name="oblique-friction";c.duration=.025;c.input.gravity={0,-10,0};c.input.add_plane({100,{0,1,0},0,{.7,.5}});b=ball(1,{0,2,0},{20,-100,0});b.material={.7,.5};c.input.add_body(b);add(c);
    c=Case{};c.name="oriented-plane";c.input.gravity={};c.input.add_plane(wall(100,{.6,.8,0},0));c.input.add_body(ball(1,{1.2,1.6,0},{-60,-80,0}));add(c);
    c=Case{};c.name="initial-boundary-rollback";c.duration=.01;c.input.add_plane(wall(100,{0,1,0},0));b=ball(1,{0,.5,0},{0,2,0});b.force={1,2,3};c.input.add_body(b);c.success=false;add(c);
    c.name="initial-overlap-rollback";c.input.find_body(1)->position.y=.49;add(c);
    c=Case{};c.name="event-budget-rollback";c.input=corridor();c.duration=.06;c.profile.max_event_batches=1;c.success=false;add(c);
    c=Case{};c.name="invalid-duration-rollback";c.input=corridor();c.duration=0;c.success=false;add(c);
    c=Case{};c.name="rotation-limit-rollback";c.input.gravity={};b=ball(1,{0,20,0});b.angular_momentum={0,0,1000};b.force={1,2,3};b.torque={3,2,1};c.input.add_body(b);c.success=false;add(c);
    c=Case{};c.name="support-required-rollback";c.duration=.1;c.input.gravity={0,-10,0};c.input.add_plane({100,{0,1,0},0,{0,0}});b=ball(1,{0,.6,0},{0,-2,0});b.material={0,0};b.force={1,0,0};c.input.add_body(b);c.success=false;add(c);
    c=Case{};c.name="signed-zero-free-flight";c.input.gravity={-0.,0,-0.};b=ball(7,{-0.,2,-0.},{-0.,0,-0.});b.force={-0.,0,-0.};b.torque={0,-0.,0};c.input.add_body(b);add(c);
    return out;
}
}
int main(){try{
    const auto corpus=cases();std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema\":1,\"kind\":\"free-flight-legacy-world-fixtures\",\"fixtures\":[";
    std::size_t successes=0,failures=0,multiple=0;
    for(std::size_t i=0;i<corpus.size();++i){const auto& c=corpus[i];auto w=c.input;const auto before=snapshot(w);const auto* storage=w.bodies().data();const auto* plane_storage=w.planes().data();std::vector<const RigidBody*> pointers;for(const auto& b:w.bodies()){pointers.push_back(w.find_body(b.id));}
        const auto r=w.step_continuous(c.duration,c.profile);require(r.success==c.success,"Legacy probe nonvacuity expectation failed");bool stable=w.bodies().data()==storage&&w.planes().data()==plane_storage;for(std::size_t j=0;j<pointers.size();++j){stable=stable&&w.find_body(c.input.bodies()[j].id)==pointers[j];}require(stable,"Legacy World pointer stability failed");
        const bool unchanged=before==snapshot(w);if(!r.success){require(unchanged&&r.advanced_dt==0,"Legacy failure did not rollback all fields");++failures;}else{++successes;}if(r.events.size()>1){++multiple;}
        if(i){std::cout<<',';}std::cout<<"{\"name\":";string(c.name);std::cout<<",\"input\":{\"duration\":";number(c.duration);std::cout<<",\"settings\":";settings(c.profile);std::cout<<",\"world\":"<<before<<"},\"report\":";report(r);std::cout<<",\"after\":";world(w);std::cout<<",\"pointerStable\":";boolean(stable);std::cout<<",\"worldUnchanged\":";boolean(unchanged);std::cout<<",\"rollbackVerified\":";boolean(!r.success&&unchanged&&r.advanced_dt==0);std::cout<<'}';
    }
    require(corpus.size()>=12&&successes>=6&&failures>=4&&multiple>=2,"Legacy corpus became vacuous");std::cout<<"],\"counts\":{\"fixtures\":"<<corpus.size()<<",\"successes\":"<<successes<<",\"failures\":"<<failures<<",\"multipleEventCases\":"<<multiple<<"}}\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL legacy probe: "<<e.what()<<'\n';return 1;}}
