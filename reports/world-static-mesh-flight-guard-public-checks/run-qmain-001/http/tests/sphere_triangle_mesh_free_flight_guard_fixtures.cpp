#include "sphere_triangle_mesh_free_flight_guard_test_support.hpp"
#include <algorithm>
#include <iomanip>
#include <limits>
#include <utility>

namespace free_fixture {
using I=pikapika::interval::Interval;
using entry_fixture::number;
using entry_fixture::json;
namespace held=pikapika::sphere_triangle_mesh_held_load;
const char* status(guard::Status s){constexpr const char* names[]={"certified_separated","not_certified","invalid_input","unsupported_environment","numerical_failure"};return names[unsigned(s)];}
const char* reason(guard::Reason s){constexpr const char* names[]={"none","settings","body_not_found","body_invalid","unsupported_body","input_domain","surface_count","surface_id","duplicate_id","surface_budget","flight_tube_failure","derived_domain","inflated_radius_domain","propagation_failure","candidate_invalid","endpoint_tube_failure","held_load_not_separated","environment","allocation_failure","nonfinite_intermediate","coverage_inconsistent"};return names[unsigned(s)];}
template<class T,class F>void optional(const std::optional<T>& value,F writer){if(value){writer(*value);}else{std::cout<<"null";}}
void settings_json(const guard::Settings& s){std::cout<<"{\"heldLoad\":";held_fixture::settings_json(s.held_load);std::cout<<",\"maxAngularIncrement\":";number(s.max_angular_increment);std::cout<<'}';}
void triangles_json(const std::vector<single::StaticTriangle>& v){std::cout<<'[';for(std::size_t i=0;i<v.size();++i){if(i){std::cout<<',';}entry_fixture::triangle_json(v[i]);}std::cout<<']';}
void result_json(const guard::Result& r){
    std::cout<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"failedIndex\":";optional(r.failed_index,[](auto v){std::cout<<v;});
    std::cout<<",\"worldBody\":";optional(r.world_body,[](const auto& w){std::cout<<"{\"body\":";held_fixture::body_json(w.body);std::cout<<",\"gravity\":";json(w.gravity);std::cout<<'}';});
    std::cout<<",\"snapshot\":";optional(r.snapshot,[](const auto& s){std::cout<<"{\"body\":";held_fixture::body_json(s.body);std::cout<<",\"gravity\":";json(s.gravity);std::cout<<",\"horizon\":";number(s.horizon);std::cout<<",\"triangles\":";triangles_json(s.triangles);std::cout<<",\"settings\":";settings_json(s.settings);std::cout<<'}';});
    std::cout<<",\"tube\":";optional(r.tube,[](const auto& t){std::cout<<"{\"nominalAcceleration\":";json(t.nominal_acceleration);std::cout<<",\"exactAcceleration\":";json(t.exact_acceleration);std::cout<<",\"accelerationDifference\":";json(t.acceleration_difference);std::cout<<",\"positionError\":";number(t.position_error);std::cout<<",\"roundoff\":";number(t.roundoff);std::cout<<",\"guardRadius\":";number(t.guard_radius);std::cout<<'}';});
    std::cout<<",\"flightFailure\":";optional(r.flight_failure,[](auto f){std::cout<<unsigned(f);});std::cout<<",\"candidateEvaluated\":"<<(r.candidate_evaluated?"true":"false");
    std::cout<<",\"endpoint\":";optional(r.endpoint,[](const auto& e){std::cout<<"{\"nominalPosition\":";json(e.nominal_position);std::cout<<",\"nominalAllowed\":";json(e.nominal_allowed);std::cout<<",\"exactPosition\":";json(e.exact_position);std::cout<<",\"exactAllowed\":";json(e.exact_allowed);std::cout<<",\"exactDifference\":";json(e.exact_difference);std::cout<<",\"l1ErrorBound\":";json(e.l1_error_bound);std::cout<<",\"nominalContained\":"<<(e.nominal_contained?"true":"false")<<",\"exactContained\":"<<(e.exact_contained?"true":"false")<<",\"l1WithinTube\":"<<(e.l1_within_tube?"true":"false")<<'}';});
    std::cout<<",\"inflated\":";optional(r.inflated,[](const auto& h){held_fixture::result_json(h);});std::cout<<",\"candidate\":";optional(r.candidate,[](const auto& b){held_fixture::body_json(b);});std::cout<<'}';
}
void input_json(const Case& c){std::cout<<"{\"body\":";held_fixture::body_json(c.body);std::cout<<",\"gravity\":";json(c.gravity);std::cout<<",\"horizon\":";number(c.horizon);std::cout<<",\"triangles\":";triangles_json(c.triangles);std::cout<<",\"settings\":";settings_json(c.settings);std::cout<<'}';}
std::vector<Case> cases(){
    // Reuse original INPUT VALUES only; every row executes the NEW guard and
    // owns full rotational data. Previous held-load results are never imported.
    std::vector<Case> out;
    for(const auto& source:held_fixture::cases()){
        Case c;c.name="held-input-"+source.name;c.body.id=source.sphere.id;c.body.position=source.sphere.position;c.body.velocity=source.sphere.velocity;c.body.mass=source.sphere.mass;c.body.force=source.sphere.force;c.body.radius=source.sphere.radius;c.gravity=source.sphere.gravity;c.horizon=source.horizon;c.triangles=source.triangles;c.settings.held_load=source.settings;
        c.expected=source.expected==held::Status::separated?guard::Status::certified_separated:source.expected==held::Status::invalid_input?guard::Status::invalid_input:guard::Status::not_certified;out.push_back(std::move(c));
    }
    auto add=[&](Case c){out.push_back(std::move(c));};Case c;
    c.name="safe-face-held-rotation";c.body.velocity={8,0,0};c.body.force={0,2,0};c.body.torque={.1,-.2,.3};c.body.angular_momentum={.2,.3,.1};c.body.orientation={0,0,1,0};c.body.inertia_diagonal={2,3,4};c.body.material={.4,.7};c.gravity={0,-1,0};add(c);
    c=Case{};c.name="safe-edge";c.body.position={1,1,-1};c.body.velocity={8,0,0};add(c);
    c=Case{};c.name="safe-vertex";c.body.position={-1,1,-1};c.body.velocity={-8,0,0};add(c);
    c=Case{};c.name="safe-cancelled-nominal-acceleration";c.body.mass=3;c.body.force={0,-1,0};c.gravity={0,1./3,0};add(c);
    c=Case{};c.name="subnormal-force-and-velocity";c.body.force.y=std::numeric_limits<double>::denorm_min();c.body.velocity.x=std::numeric_limits<double>::denorm_min();add(c);
    c=Case{};c.name="smallest-subnormal-duration";c.horizon=std::numeric_limits<double>::denorm_min();c.expected=guard::Status::not_certified;add(c);
    c=Case{};c.name="two-subnormal-duration";c.horizon=2*std::numeric_limits<double>::denorm_min();add(c);
    c=Case{};c.name="non-dyadic-global-seconds";c.horizon=.03;c.body.velocity={4,0,0};c.body.force={0,7,0};c.gravity={0,-1,0};add(c);
    for(int direction:{-1,0,1}){
        c=Case{};c.name=direction<0?"binade-before":direction>0?"binade-after":"binade-at";const double offset=direction<0?std::nextafter(0x1p39,0.):direction>0?std::nextafter(0x1p39,1e12):0x1p39;
        c.body.position.x=offset+1;for(auto& t:c.triangles){for(auto& v:t.vertices){v.x+=offset;}}add(c);
    }
    c=Case{};c.name="inflated-entry-is-not-original-entry";const double offset=0x1p39;c.body.position={offset+1,1.25+0x1p-20,1};c.body.radius=1;c.body.velocity={0,-16,0};c.body.force={0,512,0};for(auto& t:c.triangles){for(auto& v:t.vertices){v.x+=offset;}}c.expected=guard::Status::not_certified;c.reason=guard::Reason::held_load_not_separated;add(c);
    c=Case{};c.name="inflated-radius-over-domain";c.body.radius=1e9;c.expected=guard::Status::not_certified;c.reason=guard::Reason::inflated_radius_domain;add(c);
    c=Case{};c.name="rotation-increment-failure";c.body.angular_momentum={0,0,1000};c.body.torque={1,2,3};c.expected=guard::Status::not_certified;c.reason=guard::Reason::propagation_failure;add(c);
    c=Case{};c.name="candidate-final-validation-failure";c.body.inertia_diagonal={1e18,1e18,1e18};c.body.angular_momentum={1e24,0,0};c.body.torque={1e24,0,0};c.horizon=1e-7;c.expected=guard::Status::not_certified;c.reason=guard::Reason::candidate_invalid;add(c);
    c=Case{};c.name="static-body-unsupported";c.body.is_static=true;c.body.force={3,2,1};c.body.torque={4,5,6};c.expected=guard::Status::not_certified;c.reason=guard::Reason::unsupported_body;add(c);
    c=Case{};c.name="invalid-body-inertia";c.body.inertia_diagonal.x=0;c.expected=guard::Status::invalid_input;c.reason=guard::Reason::body_invalid;add(c);
    c=Case{};c.name="invalid-body-quaternion";c.body.orientation.w=2;c.expected=guard::Status::invalid_input;c.reason=guard::Reason::body_invalid;add(c);
    c=Case{};c.name="invalid-body-material";c.body.material.friction=11;c.expected=guard::Status::invalid_input;c.reason=guard::Reason::body_invalid;add(c);
    c=Case{};c.name="invalid-angular-increment-zero";c.settings.max_angular_increment=0;c.expected=guard::Status::invalid_input;c.reason=guard::Reason::settings;add(c);
    c.name="invalid-angular-increment-over-pi";c.settings.max_angular_increment=4;add(c);
    return out;
}
Case named_case(const std::string& name){const auto corpus=cases();const auto found=std::find_if(corpus.begin(),corpus.end(),[&](const auto& c){return c.name==name;});require(found!=corpus.end(),"Named free-flight input missing");return *found;}
std::vector<Case> binade_cases(){
    std::vector<Case> result;
    for(int direction:{-1,0,1}){
        Case c;c.name=direction<0?"center-binade-before":direction>0?"center-binade-after":"center-binade-at";
        const double center=direction<0?std::nextafter(0x1p39,0.):direction>0?std::nextafter(0x1p39,1e12):0x1p39;
        c.body.position.x=center;
        for(auto& t:c.triangles){for(auto& vertex:t.vertices){vertex.x+=center-1;}}
        result.push_back(std::move(c));
    }
    return result;
}
std::vector<Case> supplemental_cases(){
    auto result=binade_cases();auto c=named_case("inflated-entry-is-not-original-entry");
    c.name="coarse-inflated-window-not-original-entry";
    // Explicit additional profile; the original100 default-tolerance inputs and
    // their unresolved-window outcome remain unchanged in the canonical corpus.
    c.settings.held_load.time_tolerance=.1;result.push_back(std::move(c));return result;
}
void emit_fixtures(const std::vector<Case>& corpus){
    std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-free-flight-guard-fixtures\",\"fixtures\":[";
    for(std::size_t i=0;i<corpus.size();++i){if(i){std::cout<<',';}const auto& c=corpus[i];std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":";input_json(c);std::cout<<",\"result\":";result_json(guard::query(c.body,c.gravity,c.triangles,c.horizon,c.settings));std::cout<<'}';}std::cout<<"]}\n";
}
}
