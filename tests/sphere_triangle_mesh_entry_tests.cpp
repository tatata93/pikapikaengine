#include "pikapika/sphere_triangle_mesh_entry.hpp"
#include "sphere_triangle_mesh_entry_fixture.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cstdint>
#include <iomanip>
#include <limits>
#include <optional>
#include <string>
#include <utility>
#include <vector>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif

namespace entry=pikapika::sphere_triangle_mesh_entry;
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using pikapika::Vec3;
using I=pikapika::interval::Interval;
using entry_fixture::require;
using entry_fixture::number;
using entry_fixture::json;

const char* status(entry::Status s){constexpr const char* n[]={"entry_window","separated","initial_penetration","not_certified","invalid_input","unsupported_environment","numerical_failure"};return n[unsigned(s)];}
const char* reason(entry::Reason s){constexpr const char* n[]={"none","settings","surface_count","surface_id","duplicate_id","input_domain","surface_budget","mesh_query_failed","initial_boundary","evaluation_budget","leaf_budget","depth_budget","sqrt_budget","parameter_resolution","nonfinite_intermediate","allocation_failure","environment","coverage_inconsistent"};return n[unsigned(s)];}
const char* outcome(entry::Outcome s){constexpr const char* n[]={"pending","initial_separated","initial_penetration","initial_uncertain","separated","split","unresolved"};return n[unsigned(s)];}
const char* leaf_state(entry::LeafState s){constexpr const char* n[]={"unqueried","certified","unresolved","current"};return n[unsigned(s)];}
template<class T,class F>void optional(const std::optional<T>& v,F writer){if(v){writer(*v);}else{std::cout<<"null";}}
void triangles_json(const std::vector<single::StaticTriangle>& v){std::cout<<'[';for(std::size_t i=0;i<v.size();++i){if(i){std::cout<<',';}entry_fixture::triangle_json(v[i]);}std::cout<<']';}
void pair_json(const std::array<double,2>& p){std::cout<<'[';number(p[0]);std::cout<<',';number(p[1]);std::cout<<']';}
void cell_json(const entry::Cell& c){std::cout<<"{\"parameter\":";pair_json(c.parameter);std::cout<<",\"depth\":"<<c.depth<<'}';}
void settings_json(const entry::Settings& s){const auto& p=s.mesh.primitive;
    std::cout<<"{\"mesh\":{\"maxSurfaces\":"<<s.mesh.max_surfaces<<",\"primitive\":{\"maxCandidates\":"<<p.max_candidates<<",\"sqrtRefinements\":"<<p.sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<p.max_total_sqrt_refinements<<",\"maximumLocalWidth\":";number(p.maximum_local_width);
    std::cout<<",\"maximumNormalWidth\":";number(p.maximum_normal_width);std::cout<<",\"minimumSineSquared\":";number(p.minimum_sine_squared);
    std::cout<<"}},\"parameterTolerance\":";number(s.parameter_tolerance);std::cout<<",\"maxEvaluations\":"<<s.max_evaluations<<",\"maxLeaves\":"<<s.max_leaves<<",\"maxDepth\":"<<s.max_depth<<",\"enclosureSqrtRefinements\":"<<s.enclosure_sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<s.max_total_sqrt_refinements<<'}';
}
void work_json(const entry::Work& w){std::cout<<"{\"meshQueries\":"<<w.mesh_queries<<",\"primitiveQueries\":"<<w.primitive_queries<<",\"candidatesExamined\":"<<w.candidates_examined<<",\"primitiveSqrtRefinements\":"<<w.primitive_sqrt_refinements<<",\"enclosureSqrtRefinements\":"<<w.enclosure_sqrt_refinements<<",\"sqrtRefinements\":"<<w.sqrt_refinements<<",\"sqrtRefinementsUpper\":"<<w.sqrt_refinements_upper<<",\"meshSqrtLimitedRows\":"<<w.mesh_sqrt_limited_rows<<",\"enclosureSqrtCalls\":"<<w.enclosure_sqrt_calls<<",\"enclosureSqrtLimitedCalls\":"<<w.enclosure_sqrt_limited_calls<<",\"workExact\":"<<(w.exact?"true":"false")<<'}';}
void audit_json(const entry::CellAudit& a){
    std::cout<<"{\"kind\":\""<<(a.kind==entry::AuditKind::initial_point?"initial_point":"cell")<<"\",\"cell\":";cell_json(a.cell);std::cout<<",\"parameter\":";number(a.parameter);std::cout<<",\"outcome\":\""<<outcome(a.outcome)<<"\",\"pathBounds\":";optional(a.path_bounds,[](const auto& v){json(v);});
    std::cout<<",\"pointBounds\":";optional(a.point_bounds,[](const auto& v){json(v);});std::cout<<",\"anchor\":";optional(a.anchor,[](auto v){json(v);});std::cout<<",\"meshQueried\":"<<(a.mesh_queried?"true":"false")<<",\"meshStatus\":";optional(a.mesh_status,[](auto v){std::cout<<unsigned(v);});std::cout<<",\"meshReason\":";optional(a.mesh_reason,[](auto v){std::cout<<unsigned(v);});
    const std::pair<const char*,const std::optional<I>*> fields[]={{"distance",&a.distance},{"displacementSquaredBound",&a.displacement_squared_bound},{"errorSquaredBound",&a.error_squared_bound},{"displacementRoot",&a.displacement_root},{"errorRoot",&a.error_root},{"clearanceCertificate",&a.clearance_certificate},{"penetrationCertificate",&a.penetration_certificate}};
    for(const auto& [key,value]:fields){std::cout<<",\""<<key<<"\":";optional(*value,[](I v){json(v);});}std::cout<<",\"work\":";work_json(a.work);std::cout<<'}';
}
void witness_json(const entry::Witness& w){std::cout<<"{\"cell\":";cell_json(w.cell);std::cout<<",\"parameter\":";number(w.parameter);std::cout<<",\"exactPathBounds\":";json(w.exact_path_bounds);std::cout<<",\"anchor\":";json(w.anchor);std::cout<<",\"errorUpper\":";number(w.error_upper);std::cout<<",\"upperGapCertificate\":";json(w.upper_gap_certificate);std::cout<<",\"auditIndex\":"<<w.audit_index<<'}';}
void result_json(const entry::Result& r){
    std::cout<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"failedIndex\":";optional(r.failed_index,[](auto v){std::cout<<v;});std::cout<<",\"snapshot\":";
    optional(r.snapshot,[](const auto& s){std::cout<<"{\"start\":";json(s.start);std::cout<<",\"end\":";json(s.end);std::cout<<",\"radius\":";number(s.radius);std::cout<<",\"triangles\":";triangles_json(s.triangles);std::cout<<",\"settings\":";settings_json(s.settings);std::cout<<'}';});
    std::cout<<",\"initial\":";optional(r.initial,[](const auto& p){std::cout<<"{\"lowerGapCertificate\":";json(p.lower_gap_certificate);std::cout<<",\"upperGapCertificate\":";json(p.upper_gap_certificate);std::cout<<",\"auditIndex\":"<<p.audit_index<<'}';});std::cout<<",\"initialSeparationProven\":"<<(r.initial_separation_proven?"true":"false");
    std::cout<<",\"certifiedLeaves\":[";for(std::size_t i=0;i<r.certified_leaves.size();++i){if(i){std::cout<<',';}const auto& l=r.certified_leaves[i];std::cout<<"{\"cell\":";cell_json(l.cell);std::cout<<",\"lowerGapCertificate\":";json(l.lower_gap_certificate);std::cout<<",\"auditIndex\":"<<l.audit_index<<'}';}
    std::cout<<"],\"safePrefix\":";optional(r.safe_prefix,[](const auto& p){pair_json(p);});std::cout<<",\"bestWitness\":";optional(r.best_witness,[](const auto& w){witness_json(w);});
    std::cout<<",\"window\":";optional(r.window,[](const auto& w){std::cout<<"{\"parameter\":";pair_json(w.parameter);std::cout<<",\"width\":";json(w.width);std::cout<<",\"witnessAuditIndex\":"<<w.witness_audit_index<<'}';});
    std::cout<<",\"candidateSurfaceIds\":[";for(std::size_t i=0;i<r.candidate_surface_ids.size();++i){if(i){std::cout<<',';}std::cout<<r.candidate_surface_ids[i];}std::cout<<"],\"partition\":[";
    for(std::size_t i=0;i<r.partition.size();++i){if(i){std::cout<<',';}const auto& p=r.partition[i];std::cout<<"{\"cell\":";cell_json(p.cell);std::cout<<",\"state\":\""<<leaf_state(p.state)<<"\",\"auditIndex\":";optional(p.audit_index,[](auto v){std::cout<<v;});std::cout<<",\"blockedReason\":\""<<reason(p.blocked_reason)<<"\"}";}
    std::cout<<"],\"frontier\":[";for(std::size_t i=0;i<r.frontier.size();++i){if(i){std::cout<<',';}cell_json(r.frontier[i]);}std::cout<<"],\"current\":";optional(r.current,[](const auto& c){cell_json(c);});
    std::cout<<",\"audits\":[";for(std::size_t i=0;i<r.audits.size();++i){if(i){std::cout<<',';}audit_json(r.audits[i]);}std::cout<<"],\"lastMesh\":";optional(r.last_mesh,[](const auto& m){entry_fixture::mesh_json(m);});std::cout<<",\"lastMeshAuditIndex\":";optional(r.last_mesh_audit_index,[](auto v){std::cout<<v;});
    std::cout<<",\"work\":";work_json(r.work);std::cout<<",\"partitionLeaves\":"<<r.partition_leaves<<",\"maximumDepth\":"<<r.maximum_depth<<'}';
}

struct Case {
    std::string name;Vec3 start{1,1,1},end{1,1,1};double radius=.25;
    std::vector<single::StaticTriangle> triangles{{37,{{{-0.,0,-0.},{4,0,0},{0,0,4}}}}};entry::Settings settings;
    entry::Status expected=entry::Status::separated;std::optional<entry::Reason> why=entry::Reason::none;
};
single::StaticTriangle flat(std::uint64_t id,double y=0){return {id,{{{0,y,0},{4,y,0},{0,y,4}}}};}
std::vector<Case> cases(){
    std::vector<Case> all;auto add=[&](Case c){all.push_back(std::move(c));};Case c;
    c.name="static-face";add(c);
    c.name="short-safe-linear";c.start={.5,1,.5};c.end={1.5,1,.5};add(c);
    c.name="parallel-near-miss";c.end={2.5,1,.5};c.radius=.5;add(c);
    c.name="backside-parallel";c.start.y=-1;c.end.y=-1;add(c);
    c=Case{};c.name="edge-near-miss";c.start={1,1,-1};c.end={3,1,-1};add(c);
    c=Case{};c.name="vertex-near-miss";c.start={-1,1,-1};c.end={-2,2,-1};add(c);
    c=Case{};c.name="sheared-triangle-safe";c.triangles={{37,{{{0,0,0},{4,0,1},{1,0,4}}}}};c.end={1.5,1,1};add(c);
    c=Case{};c.name="shared-edge-safe";c.end={3,1,1};c.triangles.push_back({11,{{{4,0,0},{4,0,4},{0,0,4}}}});add(c);
    c=Case{};c.name="strict-dominance";c.end={1.5,1,1};c.triangles.push_back(flat(99,-4));add(c);
    c.name="source-order-reversed";std::reverse(c.triangles.begin(),c.triangles.end());add(c);
    c=Case{};c.name="huge-common-offset";const double offset=0x1p38;for(auto& t:c.triangles){for(auto& v:t.vertices){v.x+=offset;v.y-=offset;v.z+=offset;}}c.start={offset+1,-offset+1,offset+1};c.end={offset+1.5,-offset+1,offset+1};add(c);
    c=Case{};c.name="uniform-small-scale";for(auto& t:c.triangles){for(auto& v:t.vertices){v.x*=.125;v.y*=.125;v.z*=.125;}}c.start={.125,.125,.125};c.end={.1875,.125,.125};c.radius*=.125;add(c);
    c=Case{};c.name="coincident-geometry-distinct-ids";c.triangles.push_back(flat(5));c.triangles.push_back(flat(99));add(c);
    c=Case{};c.name="actual-64-surfaces";c.triangles.clear();for(unsigned i=0;i<64;++i){c.triangles.push_back(flat(64-i));}add(c);
    c.name="actual-64-entry-all-conservative-ids";c.start={1,2,1};c.end={1,-4,1};c.radius=.5;c.expected=entry::Status::entry_window;add(c);
    c=Case{};c.name="actual-256-audits-128-leaves";c.end={129,1,1};c.triangles={{37,{{{0,0,0},{1024,0,0},{0,0,1024}}}}};add(c);
    c.name="255-evaluation-budget-includes-initial";c.settings.max_evaluations=255;c.expected=entry::Status::not_certified;c.why=entry::Reason::evaluation_budget;add(c);
    c.settings.max_evaluations=256;c.settings.max_leaves=127;c.name="127-leaf-budget-preserves-prefix";c.why=entry::Reason::leaf_budget;add(c);
    c.settings.max_leaves=128;c.settings.max_evaluations=128;c.name="breadth-frontier-budget";c.why=entry::Reason::evaluation_budget;add(c);
    c=Case{};c.name="analytic-entry-quarter";c.start={1,2,1};c.end={1,-4,1};c.radius=.5;c.expected=entry::Status::entry_window;add(c);
    c.name="reverse-entry-seven-twelfths";std::swap(c.start,c.end);add(c);
    c.name="symmetric-midpoint-normal-failure";c.start={1,2,1};c.end={1,-2,1};add(c);
    c.name="large-displacement-endpoints-outside";c.start={1,1000,1};c.end={1,-1000,1};add(c);
    c=Case{};c.name="multiple-entries-first-quarter";c.start={1,2,1};c.end={1,-4,1};c.radius=.5;c.triangles.push_back(flat(5,-2));c.expected=entry::Status::entry_window;add(c);
    c.name="multiple-entries-source-reversed";std::reverse(c.triangles.begin(),c.triangles.end());add(c);
    c=Case{};c.name="wide-tolerance-is-still-proof";c.start={1,2,1};c.end={1,-4,1};c.radius=.5;c.settings.parameter_tolerance=1;c.expected=entry::Status::entry_window;add(c);
    c.name="tight-tolerance-depth-budget";c.settings.parameter_tolerance=0x1p-32;c.settings.max_depth=10;c.expected=entry::Status::not_certified;c.why=entry::Reason::depth_budget;add(c);
    c=Case{};c.name="initial-strict-negative";c.start=c.end={1,.125,1};c.expected=entry::Status::initial_penetration;add(c);
    c.name="initial-backside-negative";c.start.y=c.end.y=-.125;add(c);
    c=Case{};c.name="initial-exact-boundary";c.start=c.end={1,.5,1};c.radius=.5;c.expected=entry::Status::not_certified;c.why=entry::Reason::initial_boundary;add(c);
    c.name="initial-boundary-moving-away";c.end={1,2,1};add(c);
    c=Case{};c.name="initial-zero-distance-normal-failure";c.start=c.end={1,0,1};c.expected=entry::Status::not_certified;c.why=entry::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="terminal-contact-never-negative";c.end={1,.5,1};c.radius=.5;c.settings.max_depth=4;c.expected=entry::Status::not_certified;c.why=entry::Reason::depth_budget;add(c);
    c=Case{};c.name="exact-vertex-tangency-no-negative";c.start={-.75,1,-1};c.end={-.75,-1,-1};c.radius=1.25;c.settings.max_depth=4;c.expected=entry::Status::not_certified;c.why=entry::Reason::depth_budget;add(c);
    c=Case{};c.name="primitive-normal-quality";c.settings.mesh.primitive.maximum_normal_width=1e-30;c.expected=entry::Status::not_certified;c.why=entry::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="far-degenerate-not-skipped";c.triangles.push_back({99,{{{1000,0,0},{1004,0,0},{1008,0,0}}}});c.expected=entry::Status::not_certified;c.why=entry::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="middle-degenerate-later-row-preserved";c.triangles.push_back({99,{{{0,0,0},{4,0,0},{8,0,0}}}});c.triangles.push_back(flat(5,-4));c.expected=entry::Status::not_certified;c.why=entry::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="primitive-candidate-budget";c.settings.mesh.primitive.max_candidates=3;c.expected=entry::Status::not_certified;c.why=entry::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="surface-budget-before-query";c.triangles.push_back(flat(99,-4));c.settings.mesh.max_surfaces=1;c.expected=entry::Status::not_certified;c.why=entry::Reason::surface_budget;add(c);
    c=Case{};c.name="initial-only-evaluation-budget";c.settings.max_evaluations=1;c.expected=entry::Status::not_certified;c.why=entry::Reason::evaluation_budget;add(c);
    c=Case{};c.name="leaf-budget-one";c.end={3,1,1};c.radius=.5;c.settings.max_leaves=1;c.expected=entry::Status::not_certified;c.why=entry::Reason::leaf_budget;add(c);
    c.settings.max_leaves=128;c.settings.max_depth=0;c.name="depth-budget-zero";c.why=entry::Reason::depth_budget;add(c);
    c=Case{};c.name="sqrt-reservation-before-mesh";c.settings.max_total_sqrt_refinements=511;c.expected=entry::Status::not_certified;c.why=entry::Reason::sqrt_budget;add(c);
    c.name="sqrt-reservation-before-enclosure";c.settings.max_total_sqrt_refinements=512;add(c);
    c=Case{};c.name="duplicate-source-id";c.triangles.push_back(flat(37));c.expected=entry::Status::invalid_input;c.why=entry::Reason::duplicate_id;add(c);
    c=Case{};c.name="zero-source-id";c.triangles[0].id=0;c.expected=entry::Status::invalid_input;c.why=entry::Reason::surface_id;add(c);
    c.name="unsafe-source-id";c.triangles[0].id=9007199254740992ULL;add(c);
    c=Case{};c.name="empty-source";c.triangles.clear();c.expected=entry::Status::invalid_input;c.why=entry::Reason::surface_count;add(c);
    c=Case{};c.name="65-source-rejection";c.triangles.clear();for(unsigned i=0;i<65;++i){c.triangles.push_back(flat(i+1));}c.expected=entry::Status::invalid_input;c.why=entry::Reason::surface_count;add(c);
    c=Case{};c.name="endpoint-outside-domain";c.start.x=0x1p40;c.expected=entry::Status::invalid_input;c.why=entry::Reason::input_domain;add(c);
    c=Case{};c.name="last-vertex-outside-domain";c.triangles.push_back(flat(99));c.triangles.back().vertices[2].z=std::nextafter(1e12,1e13);c.expected=entry::Status::invalid_input;c.why=entry::Reason::input_domain;add(c);
    c=Case{};c.name="zero-radius";c.radius=0;c.expected=entry::Status::invalid_input;c.why=entry::Reason::input_domain;add(c);
    c=Case{};c.name="invalid-evaluation-zero";c.settings.max_evaluations=0;c.expected=entry::Status::invalid_input;c.why=entry::Reason::settings;add(c);
    c.name="invalid-evaluation-257";c.settings.max_evaluations=257;add(c);
    c=Case{};c.name="invalid-leaf-129";c.settings.max_leaves=129;c.expected=entry::Status::invalid_input;c.why=entry::Reason::settings;add(c);
    c=Case{};c.name="invalid-depth-33";c.settings.max_depth=33;c.expected=entry::Status::invalid_input;c.why=entry::Reason::settings;add(c);
    c=Case{};c.name="invalid-enclosure-zero";c.settings.enclosure_sqrt_refinements=0;c.expected=entry::Status::invalid_input;c.why=entry::Reason::settings;add(c);
    c=Case{};c.name="invalid-tolerance-zero";c.settings.parameter_tolerance=0;c.expected=entry::Status::invalid_input;c.why=entry::Reason::settings;add(c);
    c.name="invalid-tolerance-negative";c.settings.parameter_tolerance=-1;add(c);
    c.name="invalid-tolerance-above-one";c.settings.parameter_tolerance=std::nextafter(1.,2.);add(c);
    c=Case{};c.name="invalid-primitive-setting";c.settings.mesh.primitive.minimum_sine_squared=0;c.expected=entry::Status::invalid_input;c.why=entry::Reason::settings;add(c);
    c=Case{};c.name="signed-source-zero";c.start=c.end={-0.,1,1};add(c);
    c=Case{};c.name="positive-subnormal-radius";c.radius=std::numeric_limits<double>::denorm_min();add(c);
    c=Case{};c.name="limited-sqrt-certified-far-path";c.start={1,100,1};c.end={2,100,1};c.settings.mesh.primitive.sqrt_refinements=1;c.settings.mesh.primitive.maximum_normal_width=2;c.settings.enclosure_sqrt_refinements=1;add(c);
    c=Case{};c.name="inside-rounded-anchor-no-false-witness";const double base=0x1p39;c.start={base,0,0};c.end={base+0x1p-13,0,0};c.radius=1-3*0x1p-15;c.triangles={{37,{{{base+1,-4,-4},{base+1,4,-4},{base+1,0,4}}}}};c.settings.max_depth=4;c.expected=entry::Status::not_certified;c.why.reset();add(c);
    return all;
}
Case named_case(const std::string& name){const auto all=cases();const auto i=std::find_if(all.begin(),all.end(),[&](const auto& c){return c.name==name;});require(i!=all.end(),"Named case missing");return *i;}
std::uint64_t bits(double x){return std::bit_cast<std::uint64_t>(x);}
bool same(I a,I b){return bits(a.lower())==bits(b.lower())&&bits(a.upper())==bits(b.upper());}
bool same_cell(const entry::Cell& a,const entry::Cell& b){return a.depth==b.depth&&a.parameter==b.parameter;}
std::vector<std::uint64_t> source_bits(const Case& c){
    std::vector<std::uint64_t> b;
    for(auto v:{c.start,c.end}){b.insert(b.end(),{bits(v.x),bits(v.y),bits(v.z)});}b.push_back(bits(c.radius));
    for(const auto& t:c.triangles){b.push_back(t.id);for(auto v:t.vertices){b.insert(b.end(),{bits(v.x),bits(v.y),bits(v.z)});}}
    const auto& s=c.settings;const auto& p=s.mesh.primitive;
    b.insert(b.end(),{s.mesh.max_surfaces,p.max_candidates,p.sqrt_refinements,p.max_total_sqrt_refinements,bits(p.maximum_local_width),bits(p.maximum_normal_width),bits(p.minimum_sine_squared),bits(s.parameter_tolerance),s.max_evaluations,s.max_leaves,s.max_depth,s.enclosure_sqrt_refinements,s.max_total_sqrt_refinements});return b;
}
void verify_partition(const entry::Result& r){
    require(r.partition.size()==r.partition_leaves,"Partition count mismatch");
    if(!r.partition.empty()){
        double end=0;
        for(const auto& p:r.partition){
            require(p.cell.parameter[0]==end&&p.cell.parameter[1]>end&&p.cell.parameter[1]<=1,"Closed partition gap/overlap");end=p.cell.parameter[1];
            if(p.audit_index){require(*p.audit_index<r.audits.size()&&same_cell(p.cell,r.audits[*p.audit_index].cell),"Partition audit link wrong");}
            if(p.state==entry::LeafState::certified){require(p.audit_index&&r.audits[*p.audit_index].outcome==entry::Outcome::separated,"Certified leaf lacks actual proof");}
        }
        require(end==1,"Partition silently lost tail");
    }
    double prefix=0;bool blocked=false;
    for(const auto& l:r.certified_leaves){
        require(l.audit_index<r.audits.size()&&same_cell(l.cell,r.audits[l.audit_index].cell)&&l.lower_gap_certificate.strictly_positive(),"Certified island proof link invalid");
        require(r.audits[l.audit_index].clearance_certificate.has_value(),"Certified leaf lacks clearance interval");
        require(same(l.lower_gap_certificate,*r.audits[l.audit_index].clearance_certificate),"Certified expression changed");
        if(!blocked&&l.cell.parameter[0]==prefix){prefix=l.cell.parameter[1];}else{blocked=true;}
    }
    if(r.initial_separation_proven){require(r.initial&&r.initial->lower_gap_certificate.strictly_positive()&&r.safe_prefix&&(*r.safe_prefix)[0]==0&&(*r.safe_prefix)[1]==prefix,"Later island filled earlier unknown prefix");}
    else{require(!r.safe_prefix,"No initial positive proof yet safe prefix claimed");}
    if(r.status==entry::Status::separated){require(prefix==1&&r.work.exact,"Incomplete separated cover");}
    if(r.window){
        const auto& w=*r.window;require(r.status==entry::Status::entry_window&&r.initial_separation_proven&&r.work.exact&&r.safe_prefix&&r.best_witness,"Window without all proof objects");
        require(w.parameter[0]==prefix&&w.parameter[0]<w.parameter[1]&&w.parameter[1]<=1&&w.parameter[1]==r.best_witness->parameter,"Window endpoints not certified prefix/witness");
        require(w.witness_audit_index==r.best_witness->audit_index&&w.width.lower()>0&&w.width.upper()<=r.snapshot->settings.parameter_tolerance,"Window width threshold/link wrong");
        require(w.width.contains(w.parameter[1]-w.parameter[0]),"Width misses binary64 endpoint difference");
    }else{require(r.status!=entry::Status::entry_window&&r.candidate_surface_ids.empty(),"Window/candidate flags invented");}
    if(r.best_witness){
        const auto& w=*r.best_witness;require(w.audit_index<r.audits.size()&&r.audits[w.audit_index].kind==entry::AuditKind::cell&&w.upper_gap_certificate.strictly_negative(),"Witness not strict/exact-path cell proof");
        require(r.audits[w.audit_index].penetration_certificate.has_value(),"Witness lacks actual upper certificate");
        require(same_cell(w.cell,r.audits[w.audit_index].cell)&&w.parameter==r.audits[w.audit_index].parameter&&same(w.upper_gap_certificate,*r.audits[w.audit_index].penetration_certificate),"Witness detached from audit");
    }
    if(r.initial){require(r.initial->audit_index==0&&!r.audits.empty()&&r.audits[0].kind==entry::AuditKind::initial_point&&r.audits[0].parameter==0,"Initial point proof belongs to another query");}
    if(r.status==entry::Status::initial_penetration){require(r.initial&&r.initial->upper_gap_certificate.strictly_negative()&&!r.initial_separation_proven&&!r.best_witness&&!r.window,"Initial negative confused with entry");}
    std::vector<entry::Cell> unqueried;for(const auto& p:r.partition){if(p.state==entry::LeafState::unqueried){unqueried.push_back(p.cell);}}
    require(unqueried.size()==r.frontier.size(),"Frontier not every unqueried tail cell");for(std::size_t i=0;i<unqueried.size();++i){require(same_cell(unqueried[i],r.frontier[i]),"Frontier order/source changed");}
}
void verify_work(const Case& c,const entry::Result& r){
    entry::Work total;unsigned previous_depth=0;double previous_left=-1;bool previous_cell=false;
    for(std::size_t i=0;i<r.audits.size();++i){const auto& a=r.audits[i];const auto& w=a.work;entry::Work expected;
        if(a.kind==entry::AuditKind::initial_point){require(i==0&&a.cell.parameter==std::array<double,2>{0,0}&&a.parameter==0,"Initial audit special domain changed");}
        else{
            require(a.parameter==(a.cell.parameter[0]+a.cell.parameter[1])/2,"Cell not original global midpoint");
            if(previous_cell){require(a.cell.depth>previous_depth||(a.cell.depth==previous_depth&&a.cell.parameter[0]>previous_left),"Evaluation is not breadth/left-tie order");}
            previous_depth=a.cell.depth;previous_left=a.cell.parameter[0];previous_cell=true;
        }
        if(a.mesh_queried){
            require(a.anchor.has_value(),"Mesh query missing arbitrary anchor");const auto m=mesh::query({*a.anchor,c.radius},c.triangles,c.settings.mesh);
            require(a.mesh_status==m.status&&a.mesh_reason==m.reason,"Audit status differs from actual anchor requery");
            expected.mesh_queries=1;expected.primitive_queries=m.queries;expected.candidates_examined=m.candidates_examined;expected.primitive_sqrt_refinements=m.sqrt_refinements;expected.mesh_sqrt_limited_rows=m.sqrt_limited_rows;
        }
        const std::array<std::pair<const std::optional<I>*,const std::optional<I>*>,2> roots{{{&a.displacement_root,&a.displacement_squared_bound},{&a.error_root,&a.error_squared_bound}}};
        for(const auto& [root,squared]:roots){if(*root){
            require(squared->has_value(),"Root missing squared upper input");const auto known=pikapika::interval::sqrt_enclosure(I::point((*squared)->upper()),c.settings.enclosure_sqrt_refinements);
            require(same(**root,known.value),"Returned root differs from actual independent strict call");expected.enclosure_sqrt_calls++;expected.enclosure_sqrt_refinements+=known.refinements;expected.enclosure_sqrt_limited_calls+=known.refinement_limited?1u:0u;
        }}
        expected.sqrt_refinements=expected.primitive_sqrt_refinements+expected.enclosure_sqrt_refinements;
        require(w.exact&&w.sqrt_refinements_upper==w.sqrt_refinements&&w.mesh_queries==expected.mesh_queries&&w.primitive_queries==expected.primitive_queries&&w.candidates_examined==expected.candidates_examined&&w.primitive_sqrt_refinements==expected.primitive_sqrt_refinements&&w.enclosure_sqrt_refinements==expected.enclosure_sqrt_refinements&&w.sqrt_refinements==expected.sqrt_refinements&&w.mesh_sqrt_limited_rows==expected.mesh_sqrt_limited_rows&&w.enclosure_sqrt_calls==expected.enclosure_sqrt_calls&&w.enclosure_sqrt_limited_calls==expected.enclosure_sqrt_limited_calls,"Audit delta actual work differs (not an independent math oracle)");
        total.mesh_queries+=w.mesh_queries;total.primitive_queries+=w.primitive_queries;total.candidates_examined+=w.candidates_examined;total.primitive_sqrt_refinements+=w.primitive_sqrt_refinements;total.enclosure_sqrt_refinements+=w.enclosure_sqrt_refinements;total.mesh_sqrt_limited_rows+=w.mesh_sqrt_limited_rows;total.enclosure_sqrt_calls+=w.enclosure_sqrt_calls;total.enclosure_sqrt_limited_calls+=w.enclosure_sqrt_limited_calls;
    }
    total.sqrt_refinements=total.primitive_sqrt_refinements+total.enclosure_sqrt_refinements;const auto& w=r.work;
    require(w.exact&&w.sqrt_refinements_upper==w.sqrt_refinements&&w.mesh_queries==total.mesh_queries&&w.primitive_queries==total.primitive_queries&&w.candidates_examined==total.candidates_examined&&w.primitive_sqrt_refinements==total.primitive_sqrt_refinements&&w.enclosure_sqrt_refinements==total.enclosure_sqrt_refinements&&w.sqrt_refinements==total.sqrt_refinements&&w.mesh_sqrt_limited_rows==total.mesh_sqrt_limited_rows&&w.enclosure_sqrt_calls==total.enclosure_sqrt_calls&&w.enclosure_sqrt_limited_calls==total.enclosure_sqrt_limited_calls,"Result work differs from all delta records");
    require(r.audits.size()<=256&&r.partition.size()<=128&&w.mesh_queries<=c.settings.max_evaluations&&w.sqrt_refinements_upper<=c.settings.max_total_sqrt_refinements,"Hard/configured budget exceeded");
    if(r.last_mesh){require(r.last_mesh_audit_index&&*r.last_mesh_audit_index<r.audits.size()&&r.audits[*r.last_mesh_audit_index].mesh_status==r.last_mesh->status,"Last mesh attached to unqueried/other audit");}
    else{require(!r.last_mesh_audit_index,"Last mesh ordinal without returned call");}
}
void dump(const Case& c,const entry::Result& r){std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"start\":";json(c.start);std::cout<<",\"end\":";json(c.end);std::cout<<",\"radius\":";number(c.radius);std::cout<<",\"triangles\":";triangles_json(c.triangles);std::cout<<",\"settings\":";settings_json(c.settings);std::cout<<"},\"result\":";result_json(r);std::cout<<'}';}
unsigned groups{};
template<class F>void test(const std::string& name,F f){f();++groups;std::cout<<"PASS "<<name<<'\n';}
entry::Result run(const Case& c){return entry::query(c.start,c.end,c.radius,c.triangles,c.settings);}
int main(int argc,char** argv){try{
    const auto fixture=cases();std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);
    if(argc==2&&std::string(argv[1])=="--fixtures"){
        std::cout<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-entry-fixtures\",\"fixtures\":[";
        for(std::size_t i=0;i<fixture.size();++i){if(i){std::cout<<',';}dump(fixture[i],run(fixture[i]));}std::cout<<"]}\n";return 0;
    }
    require(argc==1,"Usage: sphere_triangle_mesh_entry_tests [--fixtures]");
    for(const auto& c:fixture){test(c.name,[&]{
        const auto before=source_bits(c);const auto r=run(c);
        if(r.status!=c.expected||(c.why&&r.reason!=*c.why)){std::cerr<<"actual "<<status(r.status)<<'/'<<reason(r.reason)<<' '<<r.message<<'\n';throw std::runtime_error("Unexpected classification; original fixture retained");}
        require(source_bits(c)==before,"Source changed during query");verify_partition(r);verify_work(c,r);
    });}
    test("analytic plane entries bound quarter reverse seven-twelfths and symmetric three-eighths",[]{
        struct Known {const char* name;double numerator,denominator;};
        for(const auto& k:std::array<Known,5>{{{"analytic-entry-quarter",1,4},{"reverse-entry-seven-twelfths",7,12},{"symmetric-midpoint-normal-failure",3,8},{"large-displacement-endpoints-outside",1999,4000},{"multiple-entries-first-quarter",1,4}}}){
            const auto r=run(named_case(k.name));require(r.window&&r.window->parameter[0]*k.denominator<k.numerator&&r.window->parameter[1]*k.denominator>k.numerator,"Window misses independently analytic first entry");
        }
    });
    test("failed zero-distance ancestor is not proof but later successful children yield a witness",[]{
        const auto r=run(named_case("symmetric-midpoint-normal-failure"));require(r.audits.size()>2&&r.audits[1].mesh_status==mesh::Status::row_failure&&r.audits[1].outcome==entry::Outcome::split&&r.best_witness&&r.best_witness->audit_index>1&&r.window,"Earlier unknown stopped later witness search");
    });
    test("later certified island does not fill earlier unknown prefix",[]{
        const auto r=run(named_case("tight-tolerance-depth-budget"));require(!r.window&&r.best_witness&&r.safe_prefix&&(*r.safe_prefix)[1]<.25&&r.best_witness->parameter>.25,"Unknown narrowness was promoted to entry");
        require(std::any_of(r.certified_leaves.begin(),r.certified_leaves.end(),[&](const auto& l){return l.cell.parameter[0]>(*r.safe_prefix)[1];}),"Isolated later success was not retained");
    });
    test("window IDs are all original conservative candidates rather than last nearest",[]{
        const auto r=run(named_case("multiple-entries-first-quarter"));require(r.window&&r.candidate_surface_ids==std::vector<std::uint64_t>{5,37},"Conservative IDs were narrowed without a window proof");
        const auto many=run(named_case("actual-64-entry-all-conservative-ids"));require(many.candidate_surface_ids.size()==64&&many.candidate_surface_ids.front()==1&&many.candidate_surface_ids.back()==64,"Final candidate/source lost");
        require(many.last_mesh&&many.last_mesh->rows.size()==64&&many.last_mesh->rows.back().query&&many.last_mesh->rows.back().query->candidates.size()==7,"64th row/7th candidate truncated");
    });
    test("initial point is charged in actual256audit128leaf capacity and255limit",[]{
        const auto r=run(named_case("actual-256-audits-128-leaves"));require(r.status==entry::Status::separated&&r.audits.size()==256&&r.work.mesh_queries==256&&r.certified_leaves.size()==128&&r.certified_leaves.back().cell.parameter[1]==1,"Actual hard capacity not reached");
        const auto fail=run(named_case("255-evaluation-budget-includes-initial"));require(fail.status==entry::Status::not_certified&&fail.work.mesh_queries==255&&!fail.window&&fail.partition_leaves==128,"Initial query was free or count truncated");
    });
    test("BFS frontier can exceed old DFS33 and retains all original global cells",[]{
        const auto r=run(named_case("breadth-frontier-budget"));require(r.status==entry::Status::not_certified&&r.partition_leaves==128&&r.frontier.size()>33&&r.current&&r.safe_prefix&&(*r.safe_prefix)[1]==0,"Breadth tail clipped or later island became prefix");
    });
    test("snapshot owns source profile and all signedzero across later calls and caller mutation",[]{
        Case c=named_case("signed-source-zero");auto r=run(c);require(r.snapshot&&std::signbit(r.snapshot->start.x)&&std::signbit(r.snapshot->triangles[0].vertices[0].x),"Signed zero lost");
        c.start.x=99;c.triangles[0].id=999;c.triangles[0].vertices[0].x=3;c.settings.parameter_tolerance=.25;c.settings.mesh.primitive.maximum_local_width=1;
        const auto other=run(c);require(r.snapshot->triangles[0].id==37&&r.snapshot->settings.parameter_tolerance==1e-6&&r.snapshot->settings.mesh.primitive.maximum_local_width==1e-7&&std::signbit(r.snapshot->start.x)&&other.snapshot->triangles[0].id==999,"Snapshot borrows mutable caller/new result");
    });
    test("initial negative boundary and zero-distance failure never carry an entry window",[]{
        for(const char* name:{"initial-strict-negative","initial-exact-boundary","initial-zero-distance-normal-failure"}){const auto r=run(named_case(name));require(!r.window&&!r.best_witness&&r.candidate_surface_ids.empty(),"Initial classification became a later window");}
    });
    test("nonfinite inputs and settings reject before snapshot then recover",[]{
        for(double value:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}){
            Case c;c.end.z=value;auto r=run(c);require(r.status==entry::Status::invalid_input&&!r.snapshot&&r.audits.empty(),"Nonfinite endpoint accepted");
            c=Case{};c.triangles[0].vertices[2].x=value;r=run(c);require(r.status==entry::Status::invalid_input&&!r.snapshot&&r.failed_index==0,"Nonfinite source accepted");
            c=Case{};c.settings.parameter_tolerance=value;r=run(c);require(r.status==entry::Status::invalid_input&&r.reason==entry::Reason::settings&&!r.snapshot,"Nonfinite tolerance accepted");
        }require(run(Case{}).status==entry::Status::separated,"Finite retry failed");
    });
    test("unsupported rounding precedes bad model and preserves caller mode",[]{
        Case c;c.triangles.clear();const auto before=std::fegetround();require(std::fesetround(FE_UPWARD)==0,"Set upward");const auto r=run(c);const auto after=std::fegetround();std::fesetround(before);
        require(r.status==entry::Status::unsupported_environment&&r.reason==entry::Reason::environment&&!r.snapshot&&after==FE_UPWARD,"Environment priority/control changed");require(run(Case{}).status==entry::Status::separated,"Nearest retry failed");
    });
#if defined(_M_X64) || defined(__x86_64__)
    test("FTZ DAZ reject without changing caller flags and restore recovers",[]{
        const auto before=_mm_getcsr();_mm_setcsr(before|0x8040u);const auto r=run(Case{});const auto after=_mm_getcsr();_mm_setcsr(before);
        require(r.status==entry::Status::unsupported_environment&&!r.snapshot&&(after&0x8040u)==0x8040u,"FTZ DAZ accepted or changed");require(run(Case{}).status==entry::Status::separated,"Gradual retry failed");
    });
#endif
    std::cout<<"PASS "<<groups<<" groups; "<<fixture.size()<<" complete-input finite entry fixtures\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
