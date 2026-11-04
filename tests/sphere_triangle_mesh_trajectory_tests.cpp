#include "pikapika/sphere_triangle_mesh_trajectory.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif
namespace guard=pikapika::sphere_triangle_mesh_trajectory;
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using pikapika::Vec3;
using I=pikapika::interval::Interval;
void require(bool b,const char* message){if(!b)throw std::runtime_error(message);}
void number(double x){require(std::isfinite(x),"Nonfinite fixture output");if(x==0&&std::signbit(x))std::cout<<"-0";else std::cout<<x;}
void json(I x){std::cout<<'[';number(x.lower());std::cout<<',';number(x.upper());std::cout<<']';}
void json(const single::Bounds3&v){std::cout<<'[';for(unsigned i=0;i<3;++i){if(i)std::cout<<',';json(v[i]);}std::cout<<']';}
void json(Vec3 v){std::cout<<'[';number(v.x);std::cout<<',';number(v.y);std::cout<<',';number(v.z);std::cout<<']';}
void triangle_json(const single::StaticTriangle&t){std::cout<<"{\"id\":"<<t.id<<",\"vertices\":[";for(unsigned i=0;i<3;++i){if(i)std::cout<<',';json(t.vertices[i]);}std::cout<<"]}";}
void single_json(const single::Result&r){
    std::cout<<"{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"geometry\":";
    if(r.geometry){const auto&g=*r.geometry;std::cout<<"{\"surfaceId\":"<<g.surface_id<<",\"survivingFeatures\":"<<g.surviving_features<<",\"barycentric\":";json(g.barycentric);std::cout<<",\"closestLocal\":";json(g.closest_local);std::cout<<",\"closest\":";json(g.closest);std::cout<<",\"delta\":";json(g.delta);std::cout<<",\"normal\":";json(g.normal);std::cout<<",\"spherePoint\":";json(g.sphere_point);std::cout<<",\"squaredDistance\":";json(g.squared_distance);std::cout<<",\"distance\":";json(g.distance);std::cout<<",\"gap\":";json(g.gap);std::cout<<",\"relation\":"<<unsigned(g.relation)<<'}';}else std::cout<<"null";
    std::cout<<",\"squaredCross\":";if(r.squared_cross)json(*r.squared_cross);else std::cout<<"null";std::cout<<",\"sineSquared\":";if(r.sine_squared)json(*r.sine_squared);else std::cout<<"null";
    std::cout<<",\"candidates\":[";for(std::size_t i=0;i<r.candidates.size();++i){if(i)std::cout<<',';const auto&c=r.candidates[i];std::cout<<"{\"feature\":"<<unsigned(c.feature)<<",\"disposition\":"<<unsigned(c.disposition)<<",\"barycentric\":";json(c.barycentric);std::cout<<",\"kkt\":[";json(c.kkt[0]);std::cout<<',';json(c.kkt[1]);std::cout<<"],\"kktCount\":"<<c.kkt_count<<'}';}
    std::cout<<"],\"candidatesExamined\":"<<r.candidates_examined<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtRefinementLimited\":"<<(r.sqrt_refinement_limited?"true":"false")<<'}';
}
void mesh_json(const mesh::Result& r){
    std::cout<<"{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"failedIndex\":";if(r.failed_index)std::cout<<*r.failed_index;else std::cout<<"null";
    std::cout<<",\"firstFailedRow\":";if(r.first_failed_row)std::cout<<*r.first_failed_row;else std::cout<<"null";
    std::cout<<",\"rows\":[";for(std::size_t j=0;j<r.rows.size();++j){if(j)std::cout<<',';std::cout<<"{\"triangle\":";triangle_json(r.rows[j].triangle);std::cout<<",\"query\":";if(r.rows[j].query)single_json(*r.rows[j].query);else std::cout<<"null";std::cout<<'}';}
    std::cout<<"],\"nearest\":";if(r.nearest){const auto& n=*r.nearest;std::cout<<"{\"squaredDistance\":";json(n.squared_distance);std::cout<<",\"distance\":";json(n.distance);std::cout<<",\"gap\":";json(n.gap);std::cout<<",\"possibleSurfaceIds\":[";for(std::size_t j=0;j<n.possible_surface_ids.size();++j){if(j)std::cout<<',';std::cout<<n.possible_surface_ids[j];}std::cout<<"]}";}else std::cout<<"null";
    std::cout<<",\"queries\":"<<r.queries<<",\"candidatesExamined\":"<<r.candidates_examined<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtLimitedRows\":"<<r.sqrt_limited_rows<<",\"failedRows\":"<<r.failed_rows<<'}';
}
const char* status(guard::Status s){constexpr const char* names[]={"separated","penetration_witness","not_certified","invalid_input","unsupported_environment","numerical_failure"};return names[unsigned(s)];}
const char* reason(guard::Reason s){constexpr const char* names[]={"none","settings","surface_count","surface_id","duplicate_id","input_domain","surface_budget","mesh_query_failed","evaluation_budget","leaf_budget","depth_budget","sqrt_budget","parameter_resolution","nonfinite_intermediate","allocation_failure","environment","coverage_inconsistent"};return names[unsigned(s)];}
const char* outcome(guard::Outcome s){constexpr const char* names[]={"pending","separated","split","penetration_witness","not_certified"};return names[unsigned(s)];}
void settings_json(const guard::Settings& s){const auto& p=s.mesh.primitive;
    std::cout<<"{\"mesh\":{\"maxSurfaces\":"<<s.mesh.max_surfaces<<",\"primitive\":{\"maxCandidates\":"<<p.max_candidates<<",\"sqrtRefinements\":"<<p.sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<p.max_total_sqrt_refinements<<",\"maximumLocalWidth\":";number(p.maximum_local_width);std::cout<<",\"maximumNormalWidth\":";number(p.maximum_normal_width);std::cout<<",\"minimumSineSquared\":";number(p.minimum_sine_squared);
    std::cout<<"}},\"maxEvaluations\":"<<s.max_evaluations<<",\"maxLeaves\":"<<s.max_leaves<<",\"maxDepth\":"<<s.max_depth<<",\"enclosureSqrtRefinements\":"<<s.enclosure_sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<s.max_total_sqrt_refinements<<'}';
}
void work_json(const guard::Work& w){std::cout<<"{\"meshQueries\":"<<w.mesh_queries<<",\"primitiveQueries\":"<<w.primitive_queries<<",\"candidatesExamined\":"<<w.candidates_examined<<",\"primitiveSqrtRefinements\":"<<w.primitive_sqrt_refinements<<",\"enclosureSqrtRefinements\":"<<w.enclosure_sqrt_refinements<<",\"sqrtRefinements\":"<<w.sqrt_refinements<<",\"sqrtRefinementsUpper\":"<<w.sqrt_refinements_upper<<",\"meshSqrtLimitedRows\":"<<w.mesh_sqrt_limited_rows<<",\"enclosureSqrtCalls\":"<<w.enclosure_sqrt_calls<<",\"enclosureSqrtLimitedCalls\":"<<w.enclosure_sqrt_limited_calls<<",\"workExact\":"<<(w.exact?"true":"false")<<'}';}
void cell_json(const guard::Cell& c){std::cout<<"{\"parameter\":[";number(c.parameter[0]);std::cout<<',';number(c.parameter[1]);std::cout<<"],\"depth\":"<<c.depth<<'}';}
template<class T,class F>void optional(const std::optional<T>& value,F writer){if(value)writer(*value);else std::cout<<"null";}
void audit_json(const guard::CellAudit& a){
    std::cout<<"{\"cell\":";cell_json(a.cell);std::cout<<",\"midpoint\":";number(a.midpoint);std::cout<<",\"outcome\":\""<<outcome(a.outcome)<<"\",\"pathBounds\":";optional(a.path_bounds,[](const auto& v){json(v);});std::cout<<",\"pointBounds\":";optional(a.point_bounds,[](const auto& v){json(v);});std::cout<<",\"anchor\":";optional(a.anchor,[](const auto& v){json(v);});
    std::cout<<",\"meshQueried\":"<<(a.mesh_queried?"true":"false")<<",\"meshStatus\":";optional(a.mesh_status,[](auto v){std::cout<<unsigned(v);});std::cout<<",\"meshReason\":";optional(a.mesh_reason,[](auto v){std::cout<<unsigned(v);});
    const std::pair<const char*,const std::optional<I>*> fields[]={{"distance",&a.distance},{"displacementSquaredBound",&a.displacement_squared_bound},{"errorSquaredBound",&a.error_squared_bound},{"displacementRoot",&a.displacement_root},{"errorRoot",&a.error_root},{"clearanceCertificate",&a.clearance_certificate},{"penetrationCertificate",&a.penetration_certificate}};
    for(const auto& [key,value]:fields){std::cout<<",\""<<key<<"\":";optional(*value,[](I v){json(v);});}std::cout<<",\"work\":";work_json(a.work);std::cout<<'}';
}
void triangles_json(const std::vector<single::StaticTriangle>& t){std::cout<<'[';for(std::size_t j=0;j<t.size();++j){if(j)std::cout<<',';triangle_json(t[j]);}std::cout<<']';}
void result_json(const guard::Result& r){
    std::cout<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"failedIndex\":";optional(r.failed_index,[](auto v){std::cout<<v;});std::cout<<",\"snapshot\":";
    optional(r.snapshot,[](const auto& s){std::cout<<"{\"start\":";json(s.start);std::cout<<",\"end\":";json(s.end);std::cout<<",\"radius\":";number(s.radius);std::cout<<",\"triangles\":";triangles_json(s.triangles);std::cout<<",\"settings\":";settings_json(s.settings);std::cout<<'}';});
    std::cout<<",\"certifiedLeaves\":[";for(std::size_t j=0;j<r.certified_leaves.size();++j){if(j)std::cout<<',';const auto& l=r.certified_leaves[j];std::cout<<"{\"cell\":";cell_json(l.cell);std::cout<<",\"lowerGapCertificate\":";json(l.lower_gap_certificate);std::cout<<",\"auditIndex\":"<<l.audit_index<<'}';}
    std::cout<<"],\"safePrefix\":";optional(r.safe_prefix,[](const auto& p){std::cout<<'[';number(p[0]);std::cout<<',';number(p[1]);std::cout<<']';});std::cout<<",\"witness\":";
    optional(r.witness,[](const auto& w){std::cout<<"{\"cell\":";cell_json(w.cell);std::cout<<",\"parameter\":";number(w.parameter);std::cout<<",\"exactPathBounds\":";json(w.exact_path_bounds);std::cout<<",\"anchor\":";json(w.anchor);std::cout<<",\"errorUpper\":";number(w.error_upper);std::cout<<",\"upperGapCertificate\":";json(w.upper_gap_certificate);std::cout<<",\"auditIndex\":"<<w.audit_index<<'}';});
    std::cout<<",\"current\":";optional(r.current,[](const auto& c){cell_json(c);});std::cout<<",\"frontier\":[";for(std::size_t j=0;j<r.frontier.size();++j){if(j)std::cout<<',';cell_json(r.frontier[j]);}
    std::cout<<"],\"audits\":[";for(std::size_t j=0;j<r.audits.size();++j){if(j)std::cout<<',';audit_json(r.audits[j]);}
    std::cout<<"],\"lastMesh\":";optional(r.last_mesh,[](const auto& m){mesh_json(m);});std::cout<<",\"lastMeshAuditIndex\":";optional(r.last_mesh_audit_index,[](auto v){std::cout<<v;});std::cout<<",\"work\":";work_json(r.work);std::cout<<",\"partitionLeaves\":"<<r.partition_leaves<<",\"maximumDepth\":"<<r.maximum_depth<<'}';
}
struct Case {
    std::string name;Vec3 start{1,1,1},end{1,1,1};double radius=.25;
    std::vector<single::StaticTriangle> triangles{{37,{{{-0.,0,-0.},{4,0,0},{0,0,4}}}}};
    guard::Settings settings;
    guard::Status expected=guard::Status::separated;guard::Reason why=guard::Reason::none;
};
single::StaticTriangle flat(std::uint64_t id,double y=0){return {id,{{{0,y,0},{4,y,0},{0,y,4}}}};}
std::vector<Case> cases(){
    std::vector<Case> all;auto add=[&](Case c){all.push_back(std::move(c));};Case c;
    c.name="static-face";add(c);
    c.name="short-safe-linear";c.start={.5,1,.5};c.end={1.5,1,.5};add(c);
    c.name="parallel-near-miss";c.end={2.5,1,.5};c.radius=.5;add(c);
    c.name="reverse-parallel-near-miss";std::swap(c.start,c.end);add(c);
    c=Case{};c.name="edge-near-miss";c.start={1,1,-1};c.end={3,1,-1};c.radius=.5;add(c);
    c=Case{};c.name="vertex-near-miss";c.start={-1,1,-1};c.end={-2,2,-1};add(c);
    c=Case{};c.name="backside-parallel";c.start={.5,-1,.5};c.end={2.5,-1,.5};add(c);
    c=Case{};c.name="shared-edge-path";c.start={1,1,1};c.end={3,1,1};c.triangles.push_back({11,{{{4,0,0},{4,0,4},{0,0,4}}}});add(c);
    c=Case{};c.name="shared-vertex-static";c.start=c.end={0,1,0};c.triangles.push_back({11,{{{0,0,0},{-4,0,0},{0,0,-4}}}});add(c);
    c=Case{};c.name="different-closest-two-surfaces";c.start={0,0,0};c.end={0,.25,0};c.triangles={{99,{{{-1,-2,-2},{-1,2,-2},{-1,0,2}}}},{7,{{{1,-2,-2},{1,2,-2},{1,0,2}}}}};add(c);
    c=Case{};c.name="strict-dominance";c.start={.5,1,.5};c.end={2.5,1,.5};c.triangles.push_back(flat(99,-4));add(c);
    c.name="source-order-reversed";std::reverse(c.triangles.begin(),c.triangles.end());add(c);
    c=Case{};c.name="huge-common-offset-in-domain";c.start={.5,1,.5};c.end={2.5,1,.5};const double offset=0x1p38;for(auto& t:c.triangles)for(auto& v:t.vertices){v.x+=offset;v.y-=offset;v.z+=offset;}c.start={offset+.5,-offset+1,offset+.5};c.end={offset+2.5,-offset+1,offset+.5};add(c);
    c=Case{};c.name="translated-dyadic";c.start={.5,1,.5};c.end={2.5,1,.5};for(auto& t:c.triangles)for(auto& v:t.vertices){v.x+=10000.25;v.y-=.125;v.z+=17.5;}c.start={10000.75,.875,18};c.end={10002.75,.875,18};add(c);
    c=Case{};c.name="uniform-small-scale";for(auto& t:c.triangles)for(auto& v:t.vertices){v.x*=.125;v.y*=.125;v.z*=.125;}c.start={.0625,.125,.0625};c.end={.3125,.125,.0625};c.radius*=.125;add(c);
    c=Case{};c.name="coincident-geometry-distinct-ids";c.triangles.push_back(flat(5));c.triangles.push_back(flat(99));c.end={1.5,1,1};add(c);
    c=Case{};c.name="actual-64-surfaces";c.triangles.clear();for(unsigned i=0;i<64;++i)c.triangles.push_back(flat(64-i));add(c);
    c=Case{};c.name="actual-128-leaf-partition";c.start={1,1,1};c.end={129,1,1};c.triangles={{37,{{{0,0,0},{1024,0,0},{0,0,1024}}}}};add(c);
    c.name="127-leaf-budget-preserves-prefix";c.settings.max_leaves=127;c.expected=guard::Status::not_certified;c.why=guard::Reason::leaf_budget;add(c);
    c=Case{};c.name="endpoints-outside-interior-penetration";c.start={1,2,1};c.end={1,-4,1};c.radius=1.5;c.expected=guard::Status::penetration_witness;add(c);
    c.name="reverse-interior-penetration";std::swap(c.start,c.end);add(c);
    c=Case{};c.name="static-strict-penetration";c.start=c.end={1,.125,1};c.expected=guard::Status::penetration_witness;add(c);
    c=Case{};c.name="edge-strict-penetration";c.start=c.end={2,.125,-.125};c.expected=guard::Status::penetration_witness;add(c);
    c=Case{};c.name="anchor-on-face-normal-unresolved";c.start=c.end={1,0,1};c.expected=guard::Status::not_certified;c.why=guard::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="exact-contact-not-separation";c.start=c.end={1,.5,1};c.radius=.5;c.settings.max_depth=2;c.expected=guard::Status::not_certified;c.why=guard::Reason::depth_budget;add(c);
    c.name="initial-contact";c.end={1,1,1};add(c);
    c.name="terminal-contact-with-prefix";std::swap(c.start,c.end);add(c);
    c=Case{};c.name="unresolved-positive-subulp-margin";c.start=c.end={1,.5+0x1p-50,1};c.radius=.5;c.settings.max_depth=2;c.expected=guard::Status::not_certified;c.why=guard::Reason::depth_budget;add(c);
    c=Case{};c.name="evaluation-budget";c.start={.5,1,.5};c.end={2.5,1,.5};c.radius=.5;c.settings.max_evaluations=1;c.expected=guard::Status::not_certified;c.why=guard::Reason::evaluation_budget;add(c);
    c.settings.max_evaluations=256;c.settings.max_leaves=1;c.name="leaf-budget";c.why=guard::Reason::leaf_budget;add(c);
    c.settings.max_leaves=128;c.settings.max_depth=0;c.name="depth-zero-budget";c.why=guard::Reason::depth_budget;add(c);
    c=Case{};c.name="sqrt-reservation-before-mesh";c.settings.max_total_sqrt_refinements=511;c.expected=guard::Status::not_certified;c.why=guard::Reason::sqrt_budget;add(c);
    c.name="sqrt-reservation-before-displacement";c.settings.max_total_sqrt_refinements=512;c.start={1,1,-1};c.end={3,1,-1};add(c);
    c.name="sqrt-reservation-before-error";c.start={.5,1,.5};c.end={2.5,1,2.5};add(c);
    c=Case{};c.name="primitive-candidate-budget";c.settings.mesh.primitive.max_candidates=3;c.expected=guard::Status::not_certified;c.why=guard::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="primitive-normal-width";c.settings.mesh.primitive.maximum_normal_width=1e-30;c.expected=guard::Status::not_certified;c.why=guard::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="remote-degenerate-not-skipped";c.triangles.push_back({99,{{{1000,0,0},{1004,0,0},{1008,0,0}}}});c.expected=guard::Status::not_certified;c.why=guard::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="middle-degenerate-later-row-preserved";c.triangles.push_back({99,{{{0,0,0},{4,0,0},{8,0,0}}}});c.triangles.push_back(flat(5,-4));c.expected=guard::Status::not_certified;c.why=guard::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="thin-surface-quality";c.triangles[0].vertices={{{0,0,0},{4,0,0},{4,0,0x1p-30}}};c.expected=guard::Status::not_certified;c.why=guard::Reason::mesh_query_failed;add(c);
    c=Case{};c.name="surface-budget-before-query";c.triangles.push_back(flat(99,-4));c.settings.mesh.max_surfaces=1;c.expected=guard::Status::not_certified;c.why=guard::Reason::surface_budget;add(c);
    c=Case{};c.name="duplicate-source-id";c.triangles.push_back(flat(37));c.expected=guard::Status::invalid_input;c.why=guard::Reason::duplicate_id;add(c);
    c=Case{};c.name="zero-source-id";c.triangles[0].id=0;c.expected=guard::Status::invalid_input;c.why=guard::Reason::surface_id;add(c);
    c.name="unsafe-source-id";c.triangles[0].id=9007199254740992ULL;add(c);
    c=Case{};c.name="empty-source";c.triangles.clear();c.expected=guard::Status::invalid_input;c.why=guard::Reason::surface_count;add(c);
    c=Case{};c.name="65-source-rejection";c.triangles.clear();for(unsigned i=0;i<65;++i)c.triangles.push_back(flat(i+1));c.expected=guard::Status::invalid_input;c.why=guard::Reason::surface_count;add(c);
    c=Case{};c.name="endpoint-domain-2pow40";c.start.x=0x1p40;c.expected=guard::Status::invalid_input;c.why=guard::Reason::input_domain;add(c);
    c=Case{};c.name="last-vertex-outside-domain";c.triangles.push_back(flat(99));c.triangles.back().vertices[2].z=std::nextafter(1e12,1e13);c.expected=guard::Status::invalid_input;c.why=guard::Reason::input_domain;add(c);
    c=Case{};c.name="zero-radius";c.radius=0;c.expected=guard::Status::invalid_input;c.why=guard::Reason::input_domain;add(c);
    c=Case{};c.name="invalid-evaluation-setting";c.settings.max_evaluations=0;c.expected=guard::Status::invalid_input;c.why=guard::Reason::settings;add(c);
    c=Case{};c.name="invalid-leaf-setting";c.settings.max_leaves=129;c.expected=guard::Status::invalid_input;c.why=guard::Reason::settings;add(c);
    c=Case{};c.name="invalid-depth-setting";c.settings.max_depth=33;c.expected=guard::Status::invalid_input;c.why=guard::Reason::settings;add(c);
    c=Case{};c.name="invalid-enclosure-sqrt-setting";c.settings.enclosure_sqrt_refinements=0;c.expected=guard::Status::invalid_input;c.why=guard::Reason::settings;add(c);
    c=Case{};c.name="invalid-primitive-setting";c.settings.mesh.primitive.minimum_sine_squared=0;c.expected=guard::Status::invalid_input;c.why=guard::Reason::settings;add(c);
    c=Case{};c.name="signed-source-zero";c.start=c.end={-0.,1,1};add(c);
    c=Case{};c.name="limited-sqrt-certified-far-path";c.start={1,100,1};c.end={2,100,1};c.settings.mesh.primitive.sqrt_refinements=1;c.settings.mesh.primitive.maximum_normal_width=2;c.settings.enclosure_sqrt_refinements=1;add(c);
    c=Case{};c.name="positive-subnormal-radius";c.radius=std::numeric_limits<double>::denorm_min();add(c);
    c=Case{};c.name="sheared-triangle-safe-path";c.triangles={{37,{{{0,0,0},{4,0,1},{1,0,4}}}}};c.start={1,1,1};c.end={1.5,1,1};add(c);
    c=Case{};c.name="face-to-edge-bc-path";c.start={1,2,1};c.end={4,2,4};add(c);
    c=Case{};c.name="edge-ab-to-vertex-b-path";c.start={2,2,-1};c.end={6,2,-1};add(c);
    c=Case{};c.name="edge-ca-to-vertex-c-path";c.start={-1,2,2};c.end={-1,2,6};add(c);
    c=Case{};c.name="lost-low-term-anchor-is-not-path";const double base=0x1p39,h=0x1p-13;c.start={base,0,0};c.end={base+h,0,0};c.radius=1+0x1p-15;c.triangles={{37,{{{base-1,-4,-4},{base-1,4,-4},{base-1,0,4}}}}};c.settings.max_depth=4;c.expected=guard::Status::not_certified;c.why=guard::Reason::depth_budget;add(c);
    // The observed interval midpoint anchor is base+h, not an assumed RN(base+h/2).
    // This second analytic source makes THAT actual anchor inside while the
    // exact path midpoint is outside. Preserve the first source as a distinct case.
    c.name="inside-rounded-anchor-no-false-witness";c.radius=1-3*0x1p-15;c.triangles={{37,{{{base+1,-4,-4},{base+1,4,-4},{base+1,0,4}}}}};add(c);
    return all;
}
Case named_case(const std::string& name){const auto all=cases();const auto found=std::find_if(all.begin(),all.end(),[&](const auto& c){return c.name==name;});require(found!=all.end(),"Named fixture missing");return *found;}
void dump(const Case& c,const guard::Result& r){std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"start\":";json(c.start);std::cout<<",\"end\":";json(c.end);std::cout<<",\"radius\":";number(c.radius);std::cout<<",\"triangles\":";triangles_json(c.triangles);std::cout<<",\"settings\":";settings_json(c.settings);std::cout<<"},\"result\":";result_json(r);std::cout<<'}';}
unsigned groups{};
template<class F>void test(const std::string& name,F f){f();++groups;std::cout<<"PASS "<<name<<'\n';}
std::uint64_t bits(double x){return std::bit_cast<std::uint64_t>(x);}
bool same(I a,I b){return bits(a.lower())==bits(b.lower())&&bits(a.upper())==bits(b.upper());}
std::vector<std::uint64_t> input_bits(const Case& c){std::vector<std::uint64_t> b;for(Vec3 v:{c.start,c.end}){b.push_back(bits(v.x));b.push_back(bits(v.y));b.push_back(bits(v.z));}b.push_back(bits(c.radius));for(const auto& t:c.triangles){b.push_back(t.id);for(auto v:t.vertices){b.push_back(bits(v.x));b.push_back(bits(v.y));b.push_back(bits(v.z));}}const auto& s=c.settings;const auto& p=s.mesh.primitive;b.insert(b.end(),{s.mesh.max_surfaces,p.max_candidates,p.sqrt_refinements,p.max_total_sqrt_refinements,bits(p.maximum_local_width),bits(p.maximum_normal_width),bits(p.minimum_sine_squared),s.max_evaluations,s.max_leaves,s.max_depth,s.enclosure_sqrt_refinements,s.max_total_sqrt_refinements});return b;}
void verify_partition(const guard::Result& r){if(!r.snapshot)return;std::vector<guard::Cell> cells;for(const auto& l:r.certified_leaves){require(l.lower_gap_certificate.strictly_positive(),"Nonpositive certified leaf");cells.push_back(l.cell);}if(r.current)cells.push_back(*r.current);cells.insert(cells.end(),r.frontier.begin(),r.frontier.end());std::sort(cells.begin(),cells.end(),[](const auto& a,const auto& b){return a.parameter[0]<b.parameter[0];});require(cells.size()==r.partition_leaves,"Partition count mismatch");double previous=0;for(const auto& c:cells){require(c.parameter[0]==previous&&c.parameter[1]>previous,"Closed partition gap/overlap");previous=c.parameter[1];}require(previous==1,"Partition does not cover one");double prefix=0;for(const auto& l:r.certified_leaves){require(l.cell.parameter[0]==prefix,"Noncontiguous safe prefix");prefix=l.cell.parameter[1];}require(r.safe_prefix.has_value()==!r.certified_leaves.empty(),"Fake safe prefix start");if(r.safe_prefix)require((*r.safe_prefix)[0]==0&&(*r.safe_prefix)[1]==prefix,"Safe prefix skips unknown cell");}
void verify_work(const Case& c,const guard::Result& r){guard::Work total;
    for(const auto& a:r.audits){const auto& w=a.work;guard::Work expected;
        if(a.mesh_queried){require(a.anchor.has_value(),"Queried audit missing anchor");const auto m=mesh::query({*a.anchor,c.radius},c.triangles,c.settings.mesh);require(a.mesh_status==m.status&&a.mesh_reason==m.reason,"Audit status differs from independent actual requery");expected.mesh_queries=1;expected.primitive_queries=m.queries;expected.candidates_examined=m.candidates_examined;expected.primitive_sqrt_refinements=m.sqrt_refinements;expected.mesh_sqrt_limited_rows=m.sqrt_limited_rows;}
        for(const auto& pair:std::array<std::pair<const std::optional<I>*,const std::optional<I>*>,2>{{{&a.displacement_root,&a.displacement_squared_bound},{&a.error_root,&a.error_squared_bound}}})if(*pair.first){require(pair.second->has_value(),"Root lacks squared input");const auto root=pikapika::interval::sqrt_enclosure(I::point((*pair.second)->upper()),c.settings.enclosure_sqrt_refinements);require(same(**pair.first,root.value),"Root differs from direct strict enclosure call");++expected.enclosure_sqrt_calls;expected.enclosure_sqrt_refinements+=root.refinements;expected.enclosure_sqrt_limited_calls+=root.refinement_limited?1u:0u;}
        expected.sqrt_refinements=expected.primitive_sqrt_refinements+expected.enclosure_sqrt_refinements;require(w.exact,"Fixed finite corpus unexpectedly has hidden work");require(w.mesh_queries==expected.mesh_queries&&w.primitive_queries==expected.primitive_queries&&w.candidates_examined==expected.candidates_examined&&w.primitive_sqrt_refinements==expected.primitive_sqrt_refinements&&w.enclosure_sqrt_refinements==expected.enclosure_sqrt_refinements&&w.mesh_sqrt_limited_rows==expected.mesh_sqrt_limited_rows&&w.enclosure_sqrt_calls==expected.enclosure_sqrt_calls&&w.enclosure_sqrt_limited_calls==expected.enclosure_sqrt_limited_calls&&w.sqrt_refinements==expected.sqrt_refinements&&w.sqrt_refinements_upper==w.sqrt_refinements,"Cell delta counters differ from actual mesh/root replay");
        total.mesh_queries+=w.mesh_queries;total.primitive_queries+=w.primitive_queries;total.candidates_examined+=w.candidates_examined;total.primitive_sqrt_refinements+=w.primitive_sqrt_refinements;total.enclosure_sqrt_refinements+=w.enclosure_sqrt_refinements;total.mesh_sqrt_limited_rows+=w.mesh_sqrt_limited_rows;total.enclosure_sqrt_calls+=w.enclosure_sqrt_calls;total.enclosure_sqrt_limited_calls+=w.enclosure_sqrt_limited_calls;
    }
    total.sqrt_refinements=total.primitive_sqrt_refinements+total.enclosure_sqrt_refinements;const auto& w=r.work;
    require(w.exact&&w.mesh_queries==total.mesh_queries&&w.primitive_queries==total.primitive_queries&&w.candidates_examined==total.candidates_examined&&w.primitive_sqrt_refinements==total.primitive_sqrt_refinements&&w.enclosure_sqrt_refinements==total.enclosure_sqrt_refinements&&w.sqrt_refinements==total.sqrt_refinements&&w.sqrt_refinements_upper==w.sqrt_refinements&&w.mesh_sqrt_limited_rows==total.mesh_sqrt_limited_rows&&w.enclosure_sqrt_calls==total.enclosure_sqrt_calls&&w.enclosure_sqrt_limited_calls==total.enclosure_sqrt_limited_calls,"Global counters do not equal independently replayed per-cell work");
    require(w.mesh_queries<=std::min<std::size_t>(c.settings.max_evaluations,255)&&w.sqrt_refinements_upper<=c.settings.max_total_sqrt_refinements,"Configured work budget exceeded");
    if(r.last_mesh){require(r.last_mesh_audit_index&&*r.last_mesh_audit_index<r.audits.size(),"Missing last returned query link");require(r.audits[*r.last_mesh_audit_index].mesh_queried&&r.audits[*r.last_mesh_audit_index].mesh_status==r.last_mesh->status,"Old mesh substituted for unexamined cell");}else require(!r.last_mesh_audit_index,"Fake last query ordinal");
}
int main(int argc,char** argv){try{
    const auto fixture=cases();if(argc==2&&std::string(argv[1])=="--fixtures"){std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-trajectory-fixtures\",\"fixtures\":[";for(std::size_t j=0;j<fixture.size();++j){if(j)std::cout<<',';const auto& c=fixture[j];dump(c,guard::audit(c.start,c.end,c.radius,c.triangles,c.settings));}std::cout<<"]}\n";return 0;}
    require(argc==1,"Usage: sphere_triangle_mesh_trajectory_tests [--fixtures]");
    for(const auto& c:fixture)test(c.name,[&]{const auto before=input_bits(c);const auto r=guard::audit(c.start,c.end,c.radius,c.triangles,c.settings);if(r.status!=c.expected||r.reason!=c.why){std::cerr<<"actual "<<status(r.status)<<'/'<<reason(r.reason)<<" "<<r.message<<'\n';throw std::runtime_error("Unexpected path classification");}require(input_bits(c)==before,"Input changed during audit");require(r.witness.has_value()==(r.status==guard::Status::penetration_witness),"Witness status/payload mismatch");if(r.witness)require(r.witness->upper_gap_certificate.strictly_negative(),"False strict witness");if(r.status==guard::Status::separated)require(r.safe_prefix&&(*r.safe_prefix)[1]==1&&!r.current&&r.frontier.empty(),"Partial trajectory accepted");verify_partition(r);verify_work(c,r);});
    test("actual128 full partition all255meshcalls and finalleaf are owned and unchanged",[]{auto c=named_case("actual-128-leaf-partition");const auto before=input_bits(c);const auto r=guard::audit(c.start,c.end,c.radius,c.triangles,c.settings);require(r.status==guard::Status::separated&&r.partition_leaves==128&&r.certified_leaves.size()==128&&r.audits.size()==255&&r.work.mesh_queries==255,"Actual leaf capacity not exercised");require(r.certified_leaves.back().cell.parameter[1]==1&&r.certified_leaves.back().audit_index==254,"Final leaf truncated");require(input_bits(c)==before,"Capacity source modified");});
    test("127leaf failure preserves strict left prefix but never silently discards remaining interval",[]{const auto c=named_case("127-leaf-budget-preserves-prefix");const auto r=guard::audit(c.start,c.end,c.radius,c.triangles,c.settings);require(r.status==guard::Status::not_certified&&r.reason==guard::Reason::leaf_budget&&r.partition_leaves==127&&r.safe_prefix&&(*r.safe_prefix)[1]>0&&(*r.safe_prefix)[1]<1&&r.current,"Limited partition claimed whole success or lost real prefix");verify_partition(r);});
    test("real rounded anchor inside does not prove false exact-midpoint penetration",[]{const auto c=named_case("inside-rounded-anchor-no-false-witness");const auto r=guard::audit(c.start,c.end,c.radius,c.triangles,c.settings);require(!r.witness&&!r.audits.empty(),"False midpoint witness");const auto& a=r.audits.front();require(a.midpoint==.5&&a.anchor&&a.anchor->x==c.end.x&&a.distance&&a.distance->upper()<c.radius&&a.error_root&&a.error_root->upper()>=0x1p-14&&a.penetration_certificate&&a.penetration_certificate->upper()>0,"Lost-low-term E guard not exercised");});
    test("snapshot owns endpoints sources signedzero and complete mutable caller profile",[]{Case c;auto r=guard::audit(c.start,c.end,c.radius,c.triangles,c.settings);require(r.snapshot&&std::signbit(r.snapshot->triangles[0].vertices[0].x),"Source signedzero snapshot missing");const auto old=r.snapshot->settings.mesh.primitive.maximum_local_width;c.settings.mesh.primitive.maximum_local_width=1;c.start.x=99;c.triangles[0].id=999;c.triangles[0].vertices[0].x=3;require(r.snapshot->start.x==1&&r.snapshot->triangles[0].id==37&&std::signbit(r.snapshot->triangles[0].vertices[0].x)&&r.snapshot->settings.mesh.primitive.maximum_local_width==old,"Snapshot aliases caller input/settings");const auto other=guard::audit(c.start,c.end,c.radius,c.triangles,c.settings);require(r.last_mesh&&r.last_mesh->rows[0].triangle.id==37&&other.snapshot->triangles[0].id==999,"Later call modified earlier result");});
    test("all nonfinite inputs settings and valid retry retain no fake snapshot proof",[]{Case c;for(double value:{std::numeric_limits<double>::quiet_NaN(),std::numeric_limits<double>::infinity(),-std::numeric_limits<double>::infinity()}){auto q=c;q.end.z=value;auto r=guard::audit(q.start,q.end,q.radius,q.triangles,q.settings);require(r.status==guard::Status::invalid_input&&!r.snapshot&&r.audits.empty(),"Nonfinite endpoint");q=c;q.triangles[0].vertices[2].x=value;r=guard::audit(q.start,q.end,q.radius,q.triangles,q.settings);require(r.status==guard::Status::invalid_input&&r.failed_index==0&&!r.snapshot,"Nonfinite source");q=c;q.settings.mesh.primitive.maximum_local_width=value;r=guard::audit(q.start,q.end,q.radius,q.triangles,q.settings);require(r.status==guard::Status::invalid_input&&r.reason==guard::Reason::settings&&!r.snapshot,"Nonfinite profile");}require(guard::audit(c.start,c.end,c.radius,c.triangles).status==guard::Status::separated,"Valid retry failed");});
    test("unsupported environment precedes invalid input without default Interval construction or mode change",[]{Case c;c.triangles.clear();const auto mode=std::fegetround();require(std::fesetround(FE_UPWARD)==0,"Set rounding");const auto r=guard::audit(c.start,c.end,c.radius,c.triangles);const auto after=std::fegetround();std::fesetround(mode);require(r.status==guard::Status::unsupported_environment&&r.reason==guard::Reason::environment&&!r.snapshot&&r.audits.empty()&&after==FE_UPWARD,"Environment priority/mutation");c=Case{};require(guard::audit(c.start,c.end,c.radius,c.triangles).status==guard::Status::separated,"Environment restore retry");});
#if defined(_M_X64) || defined(__x86_64__)
    test("FTZ DAZ rejection preserves caller control and recovers after caller restore",[]{Case c;const auto mode=_mm_getcsr();_mm_setcsr(mode|0x8040u);const auto r=guard::audit(c.start,c.end,c.radius,c.triangles);const auto after=_mm_getcsr();_mm_setcsr(mode);require(r.status==guard::Status::unsupported_environment&&!r.snapshot&&(after&0x8040u)==0x8040u,"FTZ DAZ mutated or silently accepted");require(guard::audit(c.start,c.end,c.radius,c.triangles).status==guard::Status::separated,"Gradual restore retry");});
#endif
    std::cout<<"PASS "<<groups<<" groups; "<<fixture.size()<<" complete-input finite trajectory fixtures\n";return 0;
}catch(const std::exception& e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
