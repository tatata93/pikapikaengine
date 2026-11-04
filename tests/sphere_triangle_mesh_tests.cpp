#include "pikapika/sphere_triangle_mesh.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using pikapika::Sphere;
using pikapika::Vec3;
using I=pikapika::interval::Interval;
struct Case {
    std::string name;
    Sphere sphere{{1,1,1},.5};
    std::vector<single::StaticTriangle> triangles{{37,{{{0,0,0},{4,0,0},{0,0,4}}}}};
    mesh::Settings settings;
    mesh::Status status=mesh::Status::completed;
    mesh::Reason reason=mesh::Reason::none;
};
single::StaticTriangle flat(std::uint64_t id,double y){return {id,{{{0,y,0},{4,y,0},{0,y,4}}}};}
std::vector<Case> cases(){
    std::vector<Case> a;auto add=[&](Case c){a.push_back(std::move(c));};Case c;
    c.name="singleton-face";add(c);
    c.name="singleton-edge-ab";c.sphere={{2,3,-4},5};add(c);
    c.name="singleton-edge-bc";c.sphere={{3,2,3},.5};add(c);
    c.name="singleton-edge-ca";c.sphere={{-1,2,2},.5};add(c);
    c.name="singleton-vertex-a";c.sphere={{-3,4,0},5};add(c);
    c.name="singleton-vertex-b";c.sphere={{5,2,-1},.5};add(c);
    c.name="singleton-vertex-c";c.sphere={{-1,2,5},.5};add(c);
    c.name="singleton-back";c.sphere={{1,-1,1},.5};add(c);
    c=Case{};c.name="strict-dominance";c.triangles.push_back(flat(99,-4));add(c);
    c.name="strict-dominance-source-reversed";std::reverse(c.triangles.begin(),c.triangles.end());add(c);
    c=Case{};c.name="shared-coplanar-edge";c.sphere.center={2,1,2};c.triangles.push_back({11,{{{4,0,0},{4,0,4},{0,0,4}}}});add(c);
    c=Case{};c.name="shared-vertex";c.sphere.center={0,1,0};c.triangles.push_back({11,{{{0,0,0},{-4,0,0},{0,0,-4}}}});add(c);
    c=Case{};c.name="different-closest-left-right";c.sphere={{0,0,0},.25};c.triangles={{99,{{{-1,-2,-2},{-1,2,-2},{-1,0,2}}}},{7,{{{1,-2,-2},{1,2,-2},{1,0,2}}}}};add(c);
    c.name="different-closest-left-right-reversed";std::reverse(c.triangles.begin(),c.triangles.end());add(c);
    c=Case{};c.name="equal-geometry-distinct-ids";c.triangles.push_back(flat(5,0));c.triangles.push_back(flat(100,0));add(c);
    c=Case{};c.name="uncertain-order-not-dropped";c.triangles.push_back(flat(5,-std::numeric_limits<double>::denorm_min()));add(c);
    c=Case{};c.name="huge-common-offset";c.triangles.push_back(flat(99,-4));const double offset=0x1p40;
    for(auto&t:c.triangles)for(auto&v:t.vertices){v.x+=offset;v.y-=offset;v.z+=offset;}c.sphere.center={offset+1,-offset+1,offset+1};add(c);
    c=Case{};c.name="middle-degenerate-later-row-still-examined";c.triangles.push_back({99,{{{0,0,0},{4,0,0},{8,0,0}}}});c.triangles.push_back(flat(5,-4));c.status=mesh::Status::row_failure;c.reason=mesh::Reason::row_failed;add(c);
    c=Case{};c.name="middle-undefined-normal";c.triangles.push_back(flat(99,1));c.triangles.push_back(flat(5,-4));c.status=mesh::Status::row_failure;c.reason=mesh::Reason::row_failed;add(c);
    c=Case{};c.name="middle-thin-surface";c.triangles.push_back({99,{{{0,0,0},{4,0,0},{4,0,0x1p-30}}}});c.triangles.push_back(flat(5,-4));c.status=mesh::Status::row_failure;c.reason=mesh::Reason::row_failed;add(c);
    c=Case{};c.name="all-primitive-candidate-budgets";c.triangles.push_back(flat(99,-4));c.settings.primitive.max_candidates=3;c.status=mesh::Status::row_failure;c.reason=mesh::Reason::row_failed;add(c);
    c=Case{};c.name="all-primitive-normal-width-failures";c.triangles.push_back(flat(99,-4));c.settings.primitive.maximum_normal_width=1e-30;c.status=mesh::Status::row_failure;c.reason=mesh::Reason::row_failed;add(c);
    c=Case{};c.name="limited-sqrt-completed-rows";c.sphere={{2,3,-4},.5};c.triangles.push_back(flat(99,-1));c.settings.primitive.sqrt_refinements=1;c.settings.primitive.maximum_normal_width=2;add(c);
    c=Case{};c.name="surface-budget";c.triangles.push_back(flat(99,-4));c.settings.max_surfaces=1;c.status=mesh::Status::budget_exceeded;c.reason=mesh::Reason::surface_budget;add(c);
    c=Case{};c.name="actual-64-surfaces-all-tied";c.triangles.clear();for(unsigned i=0;i<64;++i)c.triangles.push_back(flat(64-i,0));add(c);
    c.name="65-surfaces-invalid";c.triangles.push_back(flat(1000,0));c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::surface_count;add(c);
    c=Case{};c.name="empty-source";c.triangles.clear();c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::surface_count;add(c);
    c=Case{};c.name="duplicate-second-id";c.triangles.push_back(flat(37,-4));c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::duplicate_id;add(c);
    c=Case{};c.name="second-zero-id";c.triangles.push_back(flat(0,-4));c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::surface_id;add(c);
    c=Case{};c.name="second-unsafe-id";c.triangles.push_back(flat(9007199254740992ULL,-4));c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::surface_id;add(c);
    c=Case{};c.name="maximum-stable-id";c.triangles[0].id=9007199254740991ULL;add(c);
    c=Case{};c.name="last-source-coordinate-outside-domain";c.triangles.push_back(flat(99,-4));c.triangles[1].vertices[2].x=std::nextafter(single::coordinate_limit,std::numeric_limits<double>::infinity());c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::input_domain;add(c);
    c=Case{};c.name="invalid-sphere-radius";c.sphere.radius=0;c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::input_domain;add(c);
    c=Case{};c.name="invalid-sphere-coordinate";c.sphere.center.x=1e151;c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::input_domain;add(c);
    c=Case{};c.name="invalid-surface-setting-zero";c.settings.max_surfaces=0;c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::settings;add(c);
    c.name="invalid-surface-setting-65";c.settings.max_surfaces=65;add(c);
    c=Case{};c.name="invalid-primitive-candidate-setting";c.settings.primitive.max_candidates=0;c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::settings;add(c);
    c=Case{};c.name="invalid-primitive-sine-setting";c.settings.primitive.minimum_sine_squared=0;c.status=mesh::Status::invalid_input;c.reason=mesh::Reason::settings;add(c);
    c=Case{};c.name="ordinary-row-numerical-failure";c.triangles.push_back({99,{{{0,0,0},{1e150,0,0},{0,0,1e150}}}});c.triangles.push_back(flat(5,-4));c.status=mesh::Status::row_failure;c.reason=mesh::Reason::row_failed;add(c);
    c=Case{};c.name="signed-source-zero";c.triangles[0].vertices[0]={-0.,0,-0.};c.sphere.center.z=-0.;add(c);
    c=Case{};c.name="small-uniform-scale";const auto scale=[](Vec3 v){return Vec3{v.x*1e-50,v.y*1e-50,v.z*1e-50};};for(auto&t:c.triangles)for(auto&v:t.vertices)v=scale(v);c.sphere.center=scale(c.sphere.center);c.sphere.radius*=1e-50;add(c);
    std::array<unsigned,3> order{0,1,2};unsigned index=0;
    do{c=Case{};c.name="stable-id-row-order-"+std::to_string(index++);const std::array<single::StaticTriangle,3> source{flat(37,0),flat(99,-4),flat(5,0)};c.triangles.clear();for(auto j:order)c.triangles.push_back(source[j]);add(c);}while(std::next_permutation(order.begin(),order.end()));
    c=Case{};c.name="all-six-windings-retained";const auto v=c.triangles.front().vertices;c.triangles.clear();order={0,1,2};index=0;
    do{c.triangles.push_back({10+index++,{{v[order[0]],v[order[1]],v[order[2]]}}});}while(std::next_permutation(order.begin(),order.end()));add(c);
    return a;
}
void require(bool b,const char* text){if(!b)throw std::runtime_error(text);}
unsigned groups{};
template<class F>void test(const std::string& name,F f){f();++groups;std::cout<<"PASS "<<name<<'\n';}
std::uint64_t bits(double x){return std::bit_cast<std::uint64_t>(x);}
std::vector<std::uint64_t> source_bits(Sphere sphere,const std::vector<single::StaticTriangle>& t){std::vector<std::uint64_t> b{bits(sphere.center.x),bits(sphere.center.y),bits(sphere.center.z),bits(sphere.radius)};for(const auto&s:t){b.push_back(s.id);for(auto v:s.vertices){b.push_back(bits(v.x));b.push_back(bits(v.y));b.push_back(bits(v.z));}}return b;}
void push(std::vector<std::uint64_t>&b,I x){b.push_back(bits(x.lower()));b.push_back(bits(x.upper()));}
void push(std::vector<std::uint64_t>&b,const single::Bounds3&v){for(auto x:v)push(b,x);}
std::vector<std::uint64_t> query_bits(const single::Result&r){
    std::vector<std::uint64_t> b{unsigned(r.status),unsigned(r.reason),r.geometry?1u:0u,r.candidates_examined,r.sqrt_refinements,r.sqrt_refinement_limited?1u:0u,r.squared_cross?1u:0u,r.sine_squared?1u:0u};
    if(r.squared_cross)push(b,*r.squared_cross);if(r.sine_squared)push(b,*r.sine_squared);
    for(const auto& c:r.candidates){b.push_back(unsigned(c.feature));b.push_back(unsigned(c.disposition));b.push_back(c.kkt_count);push(b,c.barycentric);push(b,c.kkt[0]);push(b,c.kkt[1]);}
    if(r.geometry){const auto&g=*r.geometry;b.push_back(g.surface_id);b.push_back(g.surviving_features);b.push_back(unsigned(g.relation));push(b,g.barycentric);push(b,g.closest_local);push(b,g.closest);push(b,g.delta);push(b,g.normal);push(b,g.sphere_point);push(b,g.squared_distance);push(b,g.distance);push(b,g.gap);}return b;
}
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
void dump(const Case&c,const mesh::Result&r){
    const auto&s=c.settings.primitive;std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"sphere\":{\"center\":";json(c.sphere.center);std::cout<<",\"radius\":";number(c.sphere.radius);std::cout<<"},\"triangles\":[";
    for(std::size_t i=0;i<c.triangles.size();++i){if(i)std::cout<<',';triangle_json(c.triangles[i]);}
    std::cout<<"],\"settings\":{\"maxSurfaces\":"<<c.settings.max_surfaces<<",\"primitive\":{\"maxCandidates\":"<<s.max_candidates<<",\"sqrtRefinements\":"<<s.sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<s.max_total_sqrt_refinements<<",\"maximumLocalWidth\":";number(s.maximum_local_width);std::cout<<",\"maximumNormalWidth\":";number(s.maximum_normal_width);std::cout<<",\"minimumSineSquared\":";number(s.minimum_sine_squared);std::cout<<"}}},\"result\":{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"failedIndex\":";
    if(r.failed_index)std::cout<<*r.failed_index;else std::cout<<"null";std::cout<<",\"firstFailedRow\":";if(r.first_failed_row)std::cout<<*r.first_failed_row;else std::cout<<"null";
    std::cout<<",\"rows\":[";for(std::size_t i=0;i<r.rows.size();++i){if(i)std::cout<<',';const auto&row=r.rows[i];std::cout<<"{\"triangle\":";triangle_json(row.triangle);std::cout<<",\"query\":";if(row.query)single_json(*row.query);else std::cout<<"null";std::cout<<'}';}
    std::cout<<"],\"nearest\":";if(r.nearest){std::cout<<"{\"squaredDistance\":";json(r.nearest->squared_distance);std::cout<<",\"distance\":";json(r.nearest->distance);std::cout<<",\"gap\":";json(r.nearest->gap);std::cout<<",\"possibleSurfaceIds\":[";for(std::size_t i=0;i<r.nearest->possible_surface_ids.size();++i){if(i)std::cout<<',';std::cout<<r.nearest->possible_surface_ids[i];}std::cout<<"]}";}else std::cout<<"null";
    std::cout<<",\"queries\":"<<r.queries<<",\"candidatesExamined\":"<<r.candidates_examined<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtLimitedRows\":"<<r.sqrt_limited_rows<<",\"failedRows\":"<<r.failed_rows<<"}}";
}
int main(int argc,char**argv){try{
    const auto fixture=cases();if(argc==2&&std::string(argv[1])=="--fixtures"){
        std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema\":1,\"kind\":\"sphere-triangle-mesh-fixtures\",\"fixtures\":[";
        for(std::size_t i=0;i<fixture.size();++i){if(i)std::cout<<',';const auto&c=fixture[i];dump(c,mesh::query(c.sphere,c.triangles,c.settings));}std::cout<<"]}\n";return 0;}
    require(argc==1,"Usage: sphere_triangle_mesh_tests [--fixtures]");
    for(const auto&c:fixture)test(c.name,[&]{const auto original=source_bits(c.sphere,c.triangles);const auto r=mesh::query(c.sphere,c.triangles,c.settings);
        if(r.status!=c.status||r.reason!=c.reason){std::cerr<<"actual="<<unsigned(r.status)<<" reason="<<unsigned(r.reason)<<" "<<r.message<<'\n';throw std::runtime_error("Unexpected finite-set result");}
        require(source_bits(c.sphere,c.triangles)==original,"Source input bits changed");require(r.nearest.has_value()==(r.status==mesh::Status::completed),"Partial nearest on failure");
        if(r.status==mesh::Status::completed||r.status==mesh::Status::row_failure){require(r.rows.size()==c.triangles.size()&&r.queries==c.triangles.size(),"Rows silently skipped");std::size_t candidates=0,roots=0,limited=0,failed=0;
            for(std::size_t i=0;i<r.rows.size();++i){const auto&row=r.rows[i];require(row.query.has_value(),"Ordinary row incorrectly unexamined");require(source_bits(c.sphere,{row.triangle})==source_bits(c.sphere,{c.triangles[i]}),"Owned source copy changed ID/order/-0");const auto direct=single::query_sphere_triangle(c.sphere,c.triangles[i],c.settings.primitive);require(query_bits(*row.query)==query_bits(direct),"Row differs from unchanged single-kernel bits");candidates+=row.query->candidates_examined;roots+=row.query->sqrt_refinements;limited+=row.query->sqrt_refinement_limited?1:0;failed+=row.query->status!=single::Status::completed?1:0;}
            require(candidates==r.candidates_examined&&roots==r.sqrt_refinements&&limited==r.sqrt_limited_rows&&failed==r.failed_rows,"Actual work sums differ");require(candidates<=448&&roots<=32768,"Hard work bounds exceeded");
        }else require(r.rows.empty()&&r.queries==0,"Preflight performed queries or published copied prefix");
    });
    test("singleton aggregate endpoints retain all source query bits",[]{Case c;const auto r=mesh::query(c.sphere,c.triangles);const auto&g=*r.rows[0].query->geometry;const auto&n=*r.nearest;require(bits(n.squared_distance.lower())==bits(g.squared_distance.lower())&&bits(n.squared_distance.upper())==bits(g.squared_distance.upper())&&bits(n.distance.lower())==bits(g.distance.lower())&&bits(n.distance.upper())==bits(g.distance.upper())&&bits(n.gap.lower())==bits(g.gap.lower())&&bits(n.gap.upper())==bits(g.gap.upper()),"Singleton endpoints changed");require(n.possible_surface_ids==std::vector<std::uint64_t>{37},"Singleton ID");});
    test("coplanar edge vertex and separated closest ties keep every ID without merged normal",[]{
        for(const auto&c:cases())if(c.name=="shared-coplanar-edge"||c.name=="shared-vertex"||c.name=="different-closest-left-right"){
            const auto r=mesh::query(c.sphere,c.triangles);require(r.nearest&&r.nearest->possible_surface_ids.size()==2,"True tie lost");require(r.nearest->squared_distance.contains(1)&&r.nearest->distance.contains(1),"Independent tied distance");
            if(c.name=="different-closest-left-right"){require(r.rows[0].query->geometry->closest[0].contains(-1)&&r.rows[1].query->geometry->closest[0].contains(1),"Separate closest points lost");require(r.rows[0].query->geometry->normal[0].contains(1)&&r.rows[1].query->geometry->normal[0].contains(-1),"Separate opposing normals lost");}
        }
    });
    test("strict dominance excludes only proven larger lower bounds and uncertain order survives",[]{Case c;c.triangles.push_back(flat(99,-4));auto r=mesh::query(c.sphere,c.triangles);require(r.nearest->possible_surface_ids==std::vector<std::uint64_t>{37},"Dominated surface retained as unique or removed winner");c.triangles[1]=flat(5,-std::numeric_limits<double>::denorm_min());r=mesh::query(c.sphere,c.triangles);require(r.nearest->possible_surface_ids==std::vector<std::uint64_t>({5,37}),"Unresolved near-tie rounded to one ID");});
    test("all six row permutations preserve aggregate bits and stable ID mapping",[]{
        Case c;const std::array<single::StaticTriangle,3> source{flat(37,0),flat(99,-4),flat(5,0)};std::array<unsigned,3> order{0,1,2};std::optional<std::vector<std::uint64_t>> expected;
        do{c.triangles.clear();for(auto j:order)c.triangles.push_back(source[j]);const auto r=mesh::query(c.sphere,c.triangles);std::vector<std::uint64_t> value;push(value,r.nearest->squared_distance);push(value,r.nearest->distance);push(value,r.nearest->gap);value.insert(value.end(),r.nearest->possible_surface_ids.begin(),r.nearest->possible_surface_ids.end());if(expected)require(value==*expected,"Source order changed aggregate");else expected=value;for(std::size_t i=0;i<3;++i)require(r.rows[i].triangle.id==source[order[i]].id,"Rows were silently sorted");}while(std::next_permutation(order.begin(),order.end()));
    });
    test("ordinary failed middle row does not stop later diagnostics or return a partial nearest",[]{Case c;c.triangles.push_back({99,{{{0,0,0},{4,0,0},{8,0,0}}}});c.triangles.push_back(flat(5,-4));const auto r=mesh::query(c.sphere,c.triangles);require(r.status==mesh::Status::row_failure&&!r.nearest&&r.first_failed_row==1&&r.failed_rows==1&&r.queries==3,"Failure aggregate contract");require(r.rows[0].query->geometry&&r.rows[1].query->status==single::Status::degenerate&&r.rows[2].query->geometry,"Full row evidence lost");});
    test("structural last-row errors preflight the whole input and valid retry recovers",[]{Case c;c.triangles.push_back(flat(0,-4));auto r=mesh::query(c.sphere,c.triangles);require(r.status==mesh::Status::invalid_input&&r.failed_index==1&&r.rows.empty()&&r.queries==0,"First good row queried before last invalid ID");c.triangles[1].id=99;r=mesh::query(c.sphere,c.triangles);require(r.status==mesh::Status::completed&&r.queries==2,"Valid retry");});
    test("owned source snapshots and old query results survive caller edits and later queries",[]{Case c;c.triangles[0].vertices[0].x=-0.;auto r=mesh::query(c.sphere,c.triangles);const auto saved=query_bits(*r.rows[0].query);c.triangles[0].id=999;c.triangles[0].vertices[0].x=123;c.sphere.radius=7;require(r.rows[0].triangle.id==37&&std::signbit(r.rows[0].triangle.vertices[0].x),"Snapshot aliases source");const auto later=mesh::query(c.sphere,c.triangles);require(query_bits(*r.rows[0].query)==saved,"Later query overwrote old snapshot");require(later.rows[0].triangle.id==999,"New source not used");});
    test("actual 64 sources produce every owned row query and nearest ID without truncation",[]{Case c;c.triangles.clear();for(unsigned i=0;i<64;++i)c.triangles.push_back(flat(64-i,0));const auto original=source_bits(c.sphere,c.triangles);auto r=mesh::query(c.sphere,c.triangles);require(r.status==mesh::Status::completed&&r.rows.size()==64&&r.queries==64&&r.candidates_examined==448&&r.nearest->possible_surface_ids.size()==64,"Maximum capacity truncated");require(r.rows.back().triangle.id==1&&r.rows.back().query&&r.nearest->possible_surface_ids.front()==1&&r.nearest->possible_surface_ids.back()==64,"Maximum last row/IDs lost");require(source_bits(c.sphere,c.triangles)==original,"Capacity test changed source");});
    test("all nonfinite inputs and settings reject before copying or running any row",[]{Case c;const double nan=std::numeric_limits<double>::quiet_NaN(),inf=std::numeric_limits<double>::infinity();
        for(double bad:{nan,inf,-inf}){auto q=c;q.triangles[0].vertices[2].z=bad;auto r=mesh::query(q.sphere,q.triangles);require(r.status==mesh::Status::invalid_input&&r.rows.empty()&&r.queries==0,"Nonfinite triangle");q=c;q.sphere.radius=bad;r=mesh::query(q.sphere,q.triangles);require(r.status==mesh::Status::invalid_input&&r.rows.empty(),"Nonfinite sphere");q=c;q.settings.primitive.maximum_local_width=bad;r=mesh::query(q.sphere,q.triangles,q.settings);require(r.status==mesh::Status::invalid_input&&r.rows.empty(),"Nonfinite profile");}
    });
    test("rounding rejection precedes invalid input and does not change control mode",[]{Case c;c.triangles.clear();const auto old=std::fegetround();require(std::fesetround(FE_UPWARD)==0,"Set rounding test");const auto r=mesh::query(c.sphere,c.triangles);const auto after=std::fegetround();std::fesetround(old);require(r.status==mesh::Status::unsupported_environment&&r.reason==mesh::Reason::environment&&r.rows.empty()&&after==FE_UPWARD,"Environment precedence/control mutation");c=Case{};require(mesh::query(c.sphere,c.triangles).nearest.has_value(),"Environment retry");});
#if defined(_M_X64) || defined(__x86_64__)
    test("FTZ DAZ rejects with no rows and leaves caller mode for caller to restore",[]{Case c;const auto old=_mm_getcsr();_mm_setcsr(old|0x8040u);const auto r=mesh::query(c.sphere,c.triangles);const auto after=_mm_getcsr();_mm_setcsr(old);require(r.status==mesh::Status::unsupported_environment&&r.rows.empty()&&(after&0x8040u)==0x8040u,"FTZ DAZ contract");require(mesh::query(c.sphere,c.triangles).nearest.has_value(),"Gradual underflow retry");});
#endif
    std::cout<<"PASS "<<groups<<" groups; "<<fixture.size()<<" complete-input finite mesh fixtures\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL after "<<groups<<" groups: "<<e.what()<<'\n';return 1;}}
