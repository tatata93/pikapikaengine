#include "sphere_triangle_mesh_held_load_test_support.hpp"
#include <algorithm>
#include <iomanip>
#include <limits>
#include <utility>

namespace held_fixture {
using I=pikapika::interval::Interval;
using entry_fixture::json;
using entry_fixture::number;
const char* status(held::Status s){constexpr const char* names[]={"entry_window","separated","initial_penetration","not_certified","invalid_input","unsupported_environment","numerical_failure"};return names[unsigned(s)];}
const char* reason(held::Reason s){constexpr const char* names[]={"none","settings","surface_count","surface_id","duplicate_id","input_domain","surface_budget","mesh_query_failed","initial_boundary","evaluation_budget","leaf_budget","depth_budget","sqrt_budget","time_resolution","nonfinite_intermediate","allocation_failure","environment","coverage_inconsistent","body_not_found","body_invalid","unsupported_body","derived_domain"};return names[unsigned(s)];}
const char* outcome(held::Outcome s){constexpr const char* names[]={"pending","initial_separated","initial_penetration","initial_uncertain","separated","split","unresolved"};return names[unsigned(s)];}
const char* leaf_state(held::LeafState s){constexpr const char* names[]={"unqueried","certified","unresolved","current"};return names[unsigned(s)];}
template<class T,class F>void optional(const std::optional<T>& value,F writer){if(value){writer(*value);}else{std::cout<<"null";}}
void pair_json(const std::array<double,2>& value){std::cout<<'[';number(value[0]);std::cout<<',';number(value[1]);std::cout<<']';}
void triangles_json(const std::vector<single::StaticTriangle>& source){std::cout<<'[';for(std::size_t i=0;i<source.size();++i){if(i){std::cout<<',';}entry_fixture::triangle_json(source[i]);}std::cout<<']';}
void sphere_json(const held::HeldSphere& b){std::cout<<"{\"id\":"<<b.id<<",\"position\":";json(b.position);std::cout<<",\"velocity\":";json(b.velocity);std::cout<<",\"mass\":";number(b.mass);std::cout<<",\"force\":";json(b.force);std::cout<<",\"gravity\":";json(b.gravity);std::cout<<",\"radius\":";number(b.radius);std::cout<<'}';}
void body_json(const pikapika::dynamics::RigidBody& b){
    std::cout<<"{\"id\":"<<b.id<<",\"isStatic\":"<<(b.is_static?"true":"false")<<",\"mass\":";number(b.mass);std::cout<<",\"inertiaDiagonal\":";json(b.inertia_diagonal);std::cout<<",\"radius\":";number(b.radius);
    for(const auto& [name,v]:std::initializer_list<std::pair<const char*,Vec3>>{{"position",b.position},{"velocity",b.velocity},{"angularMomentum",b.angular_momentum},{"force",b.force},{"torque",b.torque}}){std::cout<<",\""<<name<<"\":";json(v);}
    std::cout<<",\"orientation\":[";number(b.orientation.x);std::cout<<',';number(b.orientation.y);std::cout<<',';number(b.orientation.z);std::cout<<',';number(b.orientation.w);std::cout<<"],\"material\":{\"restitution\":";number(b.material.restitution);std::cout<<",\"friction\":";number(b.material.friction);std::cout<<"}}";
}
void settings_json(const held::Settings& s){const auto& p=s.mesh.primitive;
    std::cout<<"{\"mesh\":{\"maxSurfaces\":"<<s.mesh.max_surfaces<<",\"primitive\":{\"maxCandidates\":"<<p.max_candidates<<",\"sqrtRefinements\":"<<p.sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<p.max_total_sqrt_refinements<<",\"maximumLocalWidth\":";number(p.maximum_local_width);
    std::cout<<",\"maximumNormalWidth\":";number(p.maximum_normal_width);std::cout<<",\"minimumSineSquared\":";number(p.minimum_sine_squared);std::cout<<"}},\"timeTolerance\":";number(s.time_tolerance);
    std::cout<<",\"maxEvaluations\":"<<s.max_evaluations<<",\"maxLeaves\":"<<s.max_leaves<<",\"maxDepth\":"<<s.max_depth<<",\"enclosureSqrtRefinements\":"<<s.enclosure_sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<s.max_total_sqrt_refinements<<'}';
}
void cell_json(const held::Cell& c){std::cout<<"{\"timeBounds\":";pair_json(c.time_bounds);std::cout<<",\"depth\":"<<c.depth<<'}';}
void work_json(const held::Work& w){std::cout<<"{\"meshQueries\":"<<w.mesh_queries<<",\"primitiveQueries\":"<<w.primitive_queries<<",\"candidatesExamined\":"<<w.candidates_examined<<",\"primitiveSqrtRefinements\":"<<w.primitive_sqrt_refinements<<",\"enclosureSqrtRefinements\":"<<w.enclosure_sqrt_refinements<<",\"sqrtRefinements\":"<<w.sqrt_refinements<<",\"sqrtRefinementsUpper\":"<<w.sqrt_refinements_upper<<",\"meshSqrtLimitedRows\":"<<w.mesh_sqrt_limited_rows<<",\"enclosureSqrtCalls\":"<<w.enclosure_sqrt_calls<<",\"enclosureSqrtLimitedCalls\":"<<w.enclosure_sqrt_limited_calls<<",\"workExact\":"<<(w.exact?"true":"false")<<'}';}
void audit_json(const held::CellAudit& a){
    std::cout<<"{\"kind\":\""<<(a.kind==held::AuditKind::initial_point?"initial_point":"cell")<<"\",\"cell\":";cell_json(a.cell);std::cout<<",\"time\":";number(a.time);std::cout<<",\"outcome\":\""<<outcome(a.outcome)<<"\",\"pathBounds\":";optional(a.path_bounds,[](const auto& v){json(v);});
    std::cout<<",\"pointBounds\":";optional(a.point_bounds,[](const auto& v){json(v);});std::cout<<",\"anchor\":";optional(a.anchor,[](auto v){json(v);});std::cout<<",\"meshQueried\":"<<(a.mesh_queried?"true":"false")<<",\"meshStatus\":";optional(a.mesh_status,[](auto v){std::cout<<unsigned(v);});std::cout<<",\"meshReason\":";optional(a.mesh_reason,[](auto v){std::cout<<unsigned(v);});
    const std::pair<const char*,const std::optional<I>*> fields[]={{"distance",&a.distance},{"displacementSquaredBound",&a.displacement_squared_bound},{"errorSquaredBound",&a.error_squared_bound},{"displacementRoot",&a.displacement_root},{"errorRoot",&a.error_root},{"clearanceCertificate",&a.clearance_certificate},{"penetrationCertificate",&a.penetration_certificate}};
    for(const auto& [name,value]:fields){std::cout<<",\""<<name<<"\":";optional(*value,[](I v){json(v);});}std::cout<<",\"work\":";work_json(a.work);std::cout<<'}';
}
void result_json(const held::Result& r){
    std::cout<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"failedIndex\":";optional(r.failed_index,[](auto v){std::cout<<v;});std::cout<<",\"snapshot\":";
    optional(r.snapshot,[](const auto& s){std::cout<<"{\"input\":";sphere_json(s.input);std::cout<<",\"horizon\":";number(s.horizon);std::cout<<",\"triangles\":";triangles_json(s.triangles);std::cout<<",\"settings\":";settings_json(s.settings);std::cout<<'}';});
    std::cout<<",\"worldBody\":";optional(r.world_body,[](const auto& b){std::cout<<"{\"body\":";body_json(b.body);std::cout<<",\"gravity\":";json(b.gravity);std::cout<<'}';});
    std::cout<<",\"acceleration\":";optional(r.acceleration,[](const auto& b){json(b);});std::cout<<",\"wholePathBounds\":";optional(r.whole_path_bounds,[](const auto& b){json(b);});std::cout<<",\"wholeVelocityBounds\":";optional(r.whole_velocity_bounds,[](const auto& b){json(b);});
    std::cout<<",\"initial\":";optional(r.initial,[](const auto& p){std::cout<<"{\"lowerGapCertificate\":";json(p.lower_gap_certificate);std::cout<<",\"upperGapCertificate\":";json(p.upper_gap_certificate);std::cout<<",\"auditIndex\":"<<p.audit_index<<'}';});std::cout<<",\"initialSeparationProven\":"<<(r.initial_separation_proven?"true":"false");
    std::cout<<",\"certifiedLeaves\":[";for(std::size_t i=0;i<r.certified_leaves.size();++i){if(i){std::cout<<',';}const auto& l=r.certified_leaves[i];std::cout<<"{\"cell\":";cell_json(l.cell);std::cout<<",\"lowerGapCertificate\":";json(l.lower_gap_certificate);std::cout<<",\"auditIndex\":"<<l.audit_index<<'}';}
    std::cout<<"],\"safePrefix\":";optional(r.safe_prefix,[](const auto& p){pair_json(p);});std::cout<<",\"bestWitness\":";
    optional(r.best_witness,[](const auto& w){std::cout<<"{\"cell\":";cell_json(w.cell);std::cout<<",\"time\":";number(w.time);std::cout<<",\"exactPathBounds\":";json(w.exact_path_bounds);std::cout<<",\"anchor\":";json(w.anchor);std::cout<<",\"errorUpper\":";number(w.error_upper);std::cout<<",\"upperGapCertificate\":";json(w.upper_gap_certificate);std::cout<<",\"auditIndex\":"<<w.audit_index<<'}';});
    std::cout<<",\"window\":";optional(r.window,[](const auto& w){std::cout<<"{\"timeBounds\":";pair_json(w.time_bounds);std::cout<<",\"timeWidth\":";json(w.time_width);std::cout<<",\"pathBounds\":";json(w.path_bounds);std::cout<<",\"l1DiameterBound\":";json(w.l1_diameter_bound);std::cout<<",\"witnessAuditIndex\":"<<w.witness_audit_index<<'}';});
    std::cout<<",\"candidateSurfaceIds\":[";for(std::size_t i=0;i<r.candidate_surface_ids.size();++i){if(i){std::cout<<',';}std::cout<<r.candidate_surface_ids[i];}std::cout<<"],\"partition\":[";
    for(std::size_t i=0;i<r.partition.size();++i){if(i){std::cout<<',';}const auto& p=r.partition[i];std::cout<<"{\"cell\":";cell_json(p.cell);std::cout<<",\"state\":\""<<leaf_state(p.state)<<"\",\"auditIndex\":";optional(p.audit_index,[](auto v){std::cout<<v;});std::cout<<",\"blockedReason\":\""<<reason(p.blocked_reason)<<"\"}";}
    std::cout<<"],\"frontier\":[";for(std::size_t i=0;i<r.frontier.size();++i){if(i){std::cout<<',';}cell_json(r.frontier[i]);}std::cout<<"],\"current\":";optional(r.current,[](const auto& c){cell_json(c);});std::cout<<",\"audits\":[";
    for(std::size_t i=0;i<r.audits.size();++i){if(i){std::cout<<',';}audit_json(r.audits[i]);}std::cout<<"],\"lastMesh\":";optional(r.last_mesh,[](const auto& m){entry_fixture::mesh_json(m);});std::cout<<",\"lastMeshAuditIndex\":";optional(r.last_mesh_audit_index,[](auto v){std::cout<<v;});
    std::cout<<",\"work\":";work_json(r.work);std::cout<<",\"partitionLeaves\":"<<r.partition_leaves<<",\"maximumDepth\":"<<r.maximum_depth<<'}';
}
void input_json(const Case& c){std::cout<<"{\"sphere\":";sphere_json(c.sphere);std::cout<<",\"horizon\":";number(c.horizon);std::cout<<",\"triangles\":";triangles_json(c.triangles);std::cout<<",\"settings\":";settings_json(c.settings);std::cout<<'}';}
single::StaticTriangle flat(std::uint64_t id,double y){return {id,{{{0,y,0},{4,y,0},{0,y,4}}}};}
std::vector<Case> cases(){
    std::vector<Case> all;auto add=[&](Case c){all.push_back(std::move(c));};Case c;
    c.name="static-face";add(c);
    c.name="short-safe-linear";c.sphere.velocity={8,0,0};add(c);
    c=Case{};c.name="analytic-chord-false-safe";c.sphere.velocity={0,-64,0};c.sphere.force={0,2048,0};c.expected=held::Status::entry_window;add(c);
    c.name="analytic-chord-false-safe-force-gravity";c.sphere.mass=2;c.sphere.force={0,2048,0};c.sphere.gravity={0,1024,0};add(c);
    c=Case{};c.name="analytic-chord-false-collision";c.sphere.position={-2,.125,1};c.sphere.velocity={128,64,0};c.sphere.force={0,-2048,0};add(c);
    c=Case{};c.name="analytic-edge-quartic";c.sphere.position={1,.75,-.25};c.sphere.velocity={0,-48,0};c.sphere.force={0,1536,0};c.sphere.radius=5./16;c.expected=held::Status::entry_window;add(c);
    c=Case{};c.name="analytic-vertex-quartic";c.sphere.position={-3./16,3,-.25};c.sphere.velocity={0,-192,0};c.sphere.force={0,6144,0};c.sphere.radius=13./16;c.expected=held::Status::entry_window;add(c);
    c=Case{};c.name="analytic-tangent-no-negative";c.sphere.position={1,.5,1};c.sphere.velocity={0,-16,0};c.sphere.force={0,512,0};c.expected=held::Status::not_certified;c.why.reset();add(c);
    c=Case{};c.name="analytic-irrational-minimum-safe";c.sphere.position={-1,-.5,-1};c.sphere.velocity={16,0,0};c.sphere.force={0,512,0};c.sphere.radius=1;add(c);
    c.name="analytic-irrational-minimum-entry";c.sphere.radius=17./16;c.expected=held::Status::entry_window;add(c);
    c=Case{};c.name="force-mass-cancellation-not-point";c.sphere.position={0,0x1p-64,0};c.sphere.force={0,-1,0};c.sphere.mass=3;c.sphere.gravity={0,1./3,0};c.sphere.radius=0x1p-65;c.expected=held::Status::not_certified;c.why.reset();add(c);
    c=Case{};c.name="seconds-rescale-half";c.sphere.velocity={0,-128,0};c.sphere.force={0,8192,0};c.horizon=.03125;c.expected=held::Status::entry_window;add(c);
    c.name="seconds-rescale-quarter";c.sphere.velocity={0,-256,0};c.sphere.force={0,32768,0};c.horizon=.015625;add(c);
    c=Case{};c.name="linear-entry-quarter";c.sphere.position={1,2,1};c.sphere.velocity={0,-96,0};c.sphere.radius=.5;c.expected=held::Status::entry_window;add(c);
    c.name="linear-reverse-entry";c.sphere.position={1,-4,1};c.sphere.velocity={0,96,0};add(c);
    c.name="multiple-entries-source-order";c.sphere.position={1,2,1};c.sphere.velocity={0,-96,0};c.triangles.push_back(flat(5,-2));add(c);
    c.name="multiple-entries-source-reversed";std::reverse(c.triangles.begin(),c.triangles.end());add(c);
    c=Case{};c.name="actual-64-entry-all-conservative-ids";c.sphere.position={1,2,1};c.sphere.velocity={0,-96,0};c.sphere.radius=.5;c.triangles.clear();for(unsigned i=0;i<64;++i){c.triangles.push_back(flat(64-i));}c.expected=held::Status::entry_window;add(c);
    c=Case{};c.name="actual-256-audits-128-leaves";c.sphere.velocity={2048,0,0};c.triangles={{37,{{{0,0,0},{1024,0,0},{0,0,1024}}}}};add(c);
    c.name="255-evaluation-budget-includes-initial";c.settings.max_evaluations=255;c.expected=held::Status::not_certified;c.why=held::Reason::evaluation_budget;add(c);
    c.settings.max_evaluations=256;c.settings.max_leaves=127;c.name="127-leaf-budget-preserves-prefix";c.why=held::Reason::leaf_budget;add(c);
    c.settings.max_leaves=128;c.settings.max_evaluations=128;c.name="breadth-frontier-budget";c.why=held::Reason::evaluation_budget;add(c);
    c=Case{};c.name="wide-time-tolerance";c.sphere.position={1,2,1};c.sphere.velocity={0,-96,0};c.sphere.radius=.5;c.settings.time_tolerance=.1;c.expected=held::Status::entry_window;add(c);
    c.name="tight-time-tolerance-depth-budget";c.settings.time_tolerance=0x1p-40;c.settings.max_depth=10;c.expected=held::Status::not_certified;c.why=held::Reason::depth_budget;add(c);
    c=Case{};c.name="initial-strict-negative";c.sphere.position.y=.125;c.expected=held::Status::initial_penetration;add(c);
    c.name="initial-backside-negative";c.sphere.position.y=-.125;add(c);
    c=Case{};c.name="initial-boundary";c.sphere.position.y=.25;c.expected=held::Status::not_certified;c.why=held::Reason::initial_boundary;add(c);
    c.name="initial-boundary-moving-away";c.sphere.velocity.y=32;add(c);
    c=Case{};c.name="initial-zero-distance-normal-failure";c.sphere.position.y=0;c.expected=held::Status::not_certified;c.why=held::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="terminal-contact-no-negative";c.sphere.velocity.y=-12;c.settings.max_depth=4;c.expected=held::Status::not_certified;c.why=held::Reason::depth_budget;add(c);
    c=Case{};c.name="far-degenerate-not-skipped";c.triangles.push_back({99,{{{1000,0,0},{1004,0,0},{1008,0,0}}}});c.expected=held::Status::not_certified;c.why=held::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="middle-degenerate-later-row-preserved";c.triangles.push_back({99,{{{0,0,0},{4,0,0},{8,0,0}}}});c.triangles.push_back(flat(5,-4));c.expected=held::Status::not_certified;c.why=held::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="primitive-normal-quality";c.settings.mesh.primitive.maximum_normal_width=1e-30;c.expected=held::Status::not_certified;c.why=held::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="primitive-candidate-budget";c.settings.mesh.primitive.max_candidates=3;c.expected=held::Status::not_certified;c.why=held::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="surface-budget-before-query";c.triangles.push_back(flat(99,-4));c.settings.mesh.max_surfaces=1;c.expected=held::Status::not_certified;c.why=held::Reason::surface_budget;add(c);
    c=Case{};c.name="initial-only-evaluation-budget";c.settings.max_evaluations=1;c.expected=held::Status::not_certified;c.why=held::Reason::evaluation_budget;add(c);
    c=Case{};c.name="leaf-budget-one";c.sphere.velocity.x=32;c.settings.max_leaves=1;c.expected=held::Status::not_certified;c.why=held::Reason::leaf_budget;add(c);
    c.settings.max_leaves=128;c.settings.max_depth=0;c.name="depth-budget-zero";c.why=held::Reason::depth_budget;add(c);
    c=Case{};c.name="sqrt-reservation-before-mesh";c.settings.max_total_sqrt_refinements=511;c.expected=held::Status::not_certified;c.why=held::Reason::sqrt_budget;add(c);
    c.name="sqrt-reservation-before-enclosure";c.settings.max_total_sqrt_refinements=512;add(c);
    c=Case{};c.name="huge-common-offset";const double offset=0x1p38;for(auto& t:c.triangles){for(auto& v:t.vertices){v.x+=offset;v.y-=offset;v.z+=offset;}}c.sphere.position={offset+1,-offset+1,offset+1};c.sphere.velocity={8,0,0};add(c);
    c=Case{};c.name="signed-source-zero";c.sphere.position.x=-0.;c.sphere.velocity={-0.,0,-0.};c.sphere.force={-0.,0,-0.};c.sphere.gravity={0,-0.,0};add(c);
    c=Case{};c.name="limited-sqrt-certified-far";c.sphere.position={1,100,1};c.sphere.velocity={16,0,0};c.settings.mesh.primitive.sqrt_refinements=1;c.settings.mesh.primitive.maximum_normal_width=2;c.settings.enclosure_sqrt_refinements=1;add(c);
    c=Case{};c.name="derived-acceleration-domain";c.sphere.mass=1e-12;c.sphere.force.y=1e24;c.expected=held::Status::not_certified;c.why=held::Reason::derived_domain;add(c);
    c=Case{};c.name="derived-velocity-domain";c.sphere.velocity.y=1e9;c.sphere.force.y=1024;c.expected=held::Status::not_certified;c.why=held::Reason::derived_domain;add(c);
    c=Case{};c.name="derived-position-domain";c.sphere.position.x=1e12;c.sphere.velocity.x=1e9;c.expected=held::Status::not_certified;c.why=held::Reason::derived_domain;add(c);
    c=Case{};c.name="duplicate-source-id";c.triangles.push_back(flat(37));c.expected=held::Status::invalid_input;c.why=held::Reason::duplicate_id;add(c);
    c=Case{};c.name="zero-source-id";c.triangles[0].id=0;c.expected=held::Status::invalid_input;c.why=held::Reason::surface_id;add(c);
    c.name="unsafe-source-id";c.triangles[0].id=9007199254740992ULL;add(c);
    c=Case{};c.name="empty-source";c.triangles.clear();c.expected=held::Status::invalid_input;c.why=held::Reason::surface_count;add(c);
    c=Case{};c.name="65-source-rejection";c.triangles.clear();for(unsigned i=0;i<65;++i){c.triangles.push_back(flat(i+1));}c.expected=held::Status::invalid_input;c.why=held::Reason::surface_count;add(c);
    c=Case{};c.name="zero-body-id";c.sphere.id=0;c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);
    c.name="unsafe-body-id";c.sphere.id=9007199254740992ULL;add(c);
    for(const auto& item:std::initializer_list<std::pair<const char*,double>>{{"mass-zero",0},{"mass-below-domain",1e-13},{"mass-above-domain",1e19}}){c=Case{};c.name=item.first;c.sphere.mass=item.second;c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);}
    for(const auto& item:std::initializer_list<std::pair<const char*,double>>{{"horizon-zero",0},{"horizon-negative",-.0625},{"horizon-above-domain",std::nextafter(.1,1.)}}){c=Case{};c.name=item.first;c.horizon=item.second;c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);}
    c=Case{};c.name="position-outside-domain";c.sphere.position.x=0x1p40;c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);
    c=Case{};c.name="velocity-outside-domain";c.sphere.velocity.z=std::nextafter(1e9,1e10);c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);
    c=Case{};c.name="force-outside-domain";c.sphere.force.x=std::nextafter(1e24,1e25);c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);
    c=Case{};c.name="gravity-outside-domain";c.sphere.gravity.x=std::nextafter(1e9,1e10);c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);
    c=Case{};c.name="zero-radius";c.sphere.radius=0;c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);
    c=Case{};c.name="last-source-outside-domain";c.triangles.push_back(flat(99));c.triangles.back().vertices[2].z=std::nextafter(1e12,1e13);c.expected=held::Status::invalid_input;c.why=held::Reason::input_domain;add(c);
    c=Case{};c.name="invalid-evaluation-zero";c.settings.max_evaluations=0;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);
    c.name="invalid-evaluation-257";c.settings.max_evaluations=257;add(c);
    c=Case{};c.name="invalid-leaf-zero";c.settings.max_leaves=0;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);
    c.name="invalid-leaf-129";c.settings.max_leaves=129;add(c);
    c=Case{};c.name="invalid-depth-33";c.settings.max_depth=33;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);
    c=Case{};c.name="invalid-enclosure-zero";c.settings.enclosure_sqrt_refinements=0;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);
    c.name="invalid-enclosure-257";c.settings.enclosure_sqrt_refinements=257;add(c);
    c=Case{};c.name="invalid-total-sqrt-zero";c.settings.max_total_sqrt_refinements=0;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);
    c.name="invalid-total-sqrt-16777217";c.settings.max_total_sqrt_refinements=16777217;add(c);
    for(const auto& item:std::initializer_list<std::pair<const char*,double>>{{"invalid-time-tolerance-zero",0},{"invalid-time-tolerance-negative",-1},{"invalid-time-tolerance-above-domain",std::nextafter(.1,1.)}}){c=Case{};c.name=item.first;c.settings.time_tolerance=item.second;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);}
    c=Case{};c.name="invalid-primitive-setting";c.settings.mesh.primitive.minimum_sine_squared=0;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);
    c=Case{};c.name="invalid-mesh-setting";c.settings.mesh.max_surfaces=0;c.expected=held::Status::invalid_input;c.why=held::Reason::settings;add(c);
    return all;
}
Case named_case(const std::string& name){const auto corpus=cases();const auto found=std::find_if(corpus.begin(),corpus.end(),[&](const auto& c){return c.name==name;});require(found!=corpus.end(),"Named held-load input missing");return *found;}
void emit_fixtures(const std::vector<Case>& corpus){
    std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-held-load-fixtures\",\"fixtures\":[";
    for(std::size_t i=0;i<corpus.size();++i){if(i){std::cout<<',';}const auto& c=corpus[i];std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":";input_json(c);std::cout<<",\"result\":";result_json(held::query(c.sphere,c.triangles,c.horizon,c.settings));std::cout<<'}';}
    std::cout<<"]}\n";
}
}
