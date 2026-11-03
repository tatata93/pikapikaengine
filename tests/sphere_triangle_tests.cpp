#include "pikapika/sphere_triangle.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>
#if defined(_M_X64) || defined(__x86_64__)
#include <xmmintrin.h>
#endif

namespace st=pikapika::sphere_triangle;
using pikapika::Vec3;
using pikapika::Sphere;
using I=pikapika::interval::Interval;
struct Case {
    std::string name;
    Sphere sphere{{1,1,1},.5};
    st::StaticTriangle triangle{37,{{{0,0,0},{4,0,0},{0,0,4}}}};
    st::Settings settings;
    st::Status expected=st::Status::completed;
    st::Reason reason=st::Reason::none;
};
void require(bool x,const char* message){if(!x)throw std::runtime_error(message);}
std::uint64_t bits(double x){return std::bit_cast<std::uint64_t>(x);}
void contains(const st::Bounds3& bounds,Vec3 x){require(bounds[0].contains(x.x)&&bounds[1].contains(x.y)&&bounds[2].contains(x.z),"Independent reference outside bounds");}
unsigned passed{};
template<class F>void test(const std::string& name,F f){f();++passed;std::cout<<"PASS "<<name<<'\n';}
std::vector<Case> cases(){
    std::vector<Case> all;auto add=[&](Case c){all.push_back(std::move(c));};Case c;
    c.name="face-separated";add(c);
    c.name="face-penetrating";c.sphere.radius=2;add(c);
    c.name="face-boundary";c.sphere.radius=1;add(c);
    c.name="face-radius-next-below";c.sphere.radius=std::nextafter(1.,0.);add(c);
    c.name="face-radius-next-above";c.sphere.radius=std::nextafter(1.,2.);add(c);
    c=Case{};c.name="edge-345";c.sphere={{2,3,-4},5};add(c);
    c.name="vertex-345";c.sphere={{-3,4,0},5};add(c);
    c.name="opposite-edge";c.sphere={{3,2,3},.25};add(c);
    c.name="outside-infinite-plane";c.sphere={{3,.125,3},.25};add(c);
    c=Case{};c.name="backside";c.sphere.center.y=-1;add(c);
    c=Case{};c.name="feature-face-edge-boundary";c.sphere.center={2,1,0};add(c);
    c.name="feature-edge-vertex-boundary";c.sphere.center={0,1,0};add(c);
    c.name="face-bc-boundary";c.sphere.center={2,1,2};add(c);
    c=Case{};c.name="centre-on-face";c.sphere.center.y=0;c.expected=st::Status::quality_unresolved;c.reason=st::Reason::distance_uncertain;add(c);
    c.name="centre-on-vertex";c.sphere.center={0,0,0};c.reason=st::Reason::distance_uncertain;add(c);
    c=Case{};c.name="zero-edge";c.triangle.vertices[1]=c.triangle.vertices[0];c.expected=st::Status::degenerate;c.reason=st::Reason::zero_cross;add(c);
    c.name="axis-collinear";c.triangle.vertices={{{0,0,0},{1,0,0},{2,0,0}}};add(c);
    c=Case{};c.name="collinear-cancellation";c.triangle.vertices={{{0,0,0},{1e6,1e6,0},{999999,999999,0}}};c.expected=st::Status::quality_unresolved;c.reason=st::Reason::cross_uncertain;add(c);
    c=Case{};c.name="near-collinear";c.triangle.vertices[2]={4,0,1e-7};c.expected=st::Status::ill_conditioned;c.reason=st::Reason::conditioning_rejected;add(c);
    c=Case{};c.name="conditioning-threshold";c.settings.minimum_sine_squared=1;c.expected=st::Status::quality_unresolved;c.reason=st::Reason::conditioning_uncertain;add(c);
    c=Case{};c.name="candidate-budget";c.settings.max_candidates=6;c.expected=st::Status::budget_exceeded;c.reason=st::Reason::candidate_budget;add(c);
    c=Case{};c.name="sqrt-width-budget";c.sphere.center={2,3,-4};c.settings.sqrt_refinements=1;c.expected=st::Status::quality_unresolved;c.reason=st::Reason::normal_width;add(c);
    c=Case{};c.name="sqrt-total-budget";c.sphere.center={2,3,-4};c.settings.max_total_sqrt_refinements=1;c.expected=st::Status::budget_exceeded;c.reason=st::Reason::sqrt_budget;add(c);
    c=Case{};c.name="strict-local-width";c.settings.maximum_local_width=1e-30;c.expected=st::Status::quality_unresolved;c.reason=st::Reason::local_width;add(c);
    c=Case{};c.name="strict-normal-width";c.settings.maximum_normal_width=1e-30;c.expected=st::Status::quality_unresolved;c.reason=st::Reason::normal_width;add(c);
    c=Case{};c.name="sqrt-maximum";c.settings.sqrt_refinements=256;add(c);
    c=Case{};c.name="huge-common-offset";for(auto&v:c.triangle.vertices){v.x+=0x1p40;v.y-=0x1p40;v.z+=0x1p40;}c.sphere.center={0x1p40+1,-0x1p40+1,0x1p40+1};add(c);
    const auto scale=[](Vec3 v,double factor){return Vec3{v.x*factor,v.y*factor,v.z*factor};};
    c=Case{};c.name="small-uniform-scale";for(auto&v:c.triangle.vertices)v=scale(v,1e-50);c.sphere.center=scale(c.sphere.center,1e-50);c.sphere.radius*=1e-50;add(c);
    c=Case{};c.name="underflow-area-unresolved";for(auto&v:c.triangle.vertices)v=scale(v,1e-100);c.sphere.center=scale(c.sphere.center,1e-100);c.sphere.radius*=1e-100;c.expected=st::Status::quality_unresolved;c.reason=st::Reason::cross_uncertain;add(c);
    c=Case{};c.name="finite-intermediate-overflow";c.triangle.vertices={{{0,0,0},{1e150,0,0},{0,0,1e150}}};c.expected=st::Status::numerical_failure;c.reason=st::Reason::nonfinite_intermediate;add(c);
    c=Case{};c.name="coordinate-outside-domain";c.sphere.center.x=std::nextafter(st::coordinate_limit,std::numeric_limits<double>::infinity());c.expected=st::Status::invalid_input;c.reason=st::Reason::input_domain;add(c);
    c=Case{};c.name="zero-radius";c.sphere.radius=0;c.expected=st::Status::invalid_input;c.reason=st::Reason::input_domain;add(c);
    c.name="negative-radius";c.sphere.radius=-1;add(c);
    c=Case{};c.name="zero-id";c.triangle.id=0;c.expected=st::Status::invalid_input;c.reason=st::Reason::surface_id;add(c);
    c.name="unsafe-id";c.triangle.id=9007199254740992ULL;add(c);
    c=Case{};c.name="maximum-id";c.triangle.id=9007199254740991ULL;add(c);
    c=Case{};c.name="bad-candidate-setting";c.settings.max_candidates=0;c.expected=st::Status::invalid_input;c.reason=st::Reason::settings;add(c);
    c=Case{};c.name="bad-sqrt-setting";c.settings.sqrt_refinements=257;c.expected=st::Status::invalid_input;c.reason=st::Reason::settings;add(c);
    c=Case{};c.name="bad-total-setting";c.settings.max_total_sqrt_refinements=1025;c.expected=st::Status::invalid_input;c.reason=st::Reason::settings;add(c);
    c=Case{};c.name="bad-local-setting";c.settings.maximum_local_width=0;c.expected=st::Status::invalid_input;c.reason=st::Reason::settings;add(c);
    c=Case{};c.name="bad-normal-setting";c.settings.maximum_normal_width=3;c.expected=st::Status::invalid_input;c.reason=st::Reason::settings;add(c);
    c=Case{};c.name="bad-conditioning-setting";c.settings.minimum_sine_squared=0;c.expected=st::Status::invalid_input;c.reason=st::Reason::settings;add(c);
    c=Case{};c.name="signed-zero";c.triangle.vertices[0]={-0.,0,-0.};add(c);
    std::array<unsigned,3> permutation{0,1,2};unsigned pi=0;
    do{c=Case{};c.name="vertex-permutation-"+std::to_string(pi++);const auto vertices=c.triangle.vertices;for(unsigned j=0;j<3;++j)c.triangle.vertices[j]=vertices[permutation[j]];add(c);}while(std::next_permutation(permutation.begin(),permutation.end()));
    for(unsigned i=0;i<64;++i){
        c=Case{};std::ostringstream name;name<<"dyadic-affine-"<<std::setw(2)<<std::setfill('0')<<i;c.name=name.str();
        const double s=(int(i%3)-1)*.5,t=(i%2?-.25:.25),u=(i%4<2?.25:-.25);
        const Vec3 translation{double(int(i%5)-2)*16,double(int(i%7)-3)*8,double(int(i%9)-4)*4};
        const auto transform=[&](Vec3 p){return Vec3{p.x+s*p.y+translation.x,p.y+t*p.z+translation.y,p.z+u*p.x+translation.z};};
        for(auto& vertex:c.triangle.vertices)vertex=transform(vertex);
        const double x=double(int(i%4)*2-1),z=double(int((i/4)%4)*2-1),y=(i%2?-1:1)*(.5+double(i%3)*.25);
        c.sphere.center=transform({x,y,z});c.sphere.radius=.25+double(i%4)*.125;c.triangle.id=1000+i;add(c);
    }
    return all;
}
void json(I x){std::cout<<'['<<x.lower()<<','<<x.upper()<<']';}
void json(const st::Bounds3& x){std::cout<<'[';for(unsigned k=0;k<3;++k){if(k)std::cout<<',';json(x[k]);}std::cout<<']';}
void json(Vec3 p){std::cout<<'['<<p.x<<','<<p.y<<','<<p.z<<']';}
void dump(const Case& c,const st::Result& r){
    std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"sphere\":{\"center\":";json(c.sphere.center);std::cout<<",\"radius\":"<<c.sphere.radius<<"},\"triangle\":{\"id\":"<<c.triangle.id<<",\"vertices\":[";
    for(unsigned k=0;k<3;++k){if(k)std::cout<<',';json(c.triangle.vertices[k]);}
    const auto&s=c.settings;std::cout<<"]},\"settings\":{\"maxCandidates\":"<<s.max_candidates<<",\"sqrtRefinements\":"<<s.sqrt_refinements<<",\"maxTotalSqrtRefinements\":"<<s.max_total_sqrt_refinements<<",\"maximumLocalWidth\":"<<s.maximum_local_width<<",\"maximumNormalWidth\":"<<s.maximum_normal_width<<",\"minimumSineSquared\":"<<s.minimum_sine_squared<<"}},\"result\":{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"geometry\":";
    if(r.geometry){const auto&g=*r.geometry;std::cout<<"{\"surfaceId\":"<<g.surface_id<<",\"survivingFeatures\":"<<g.surviving_features<<",\"barycentric\":";json(g.barycentric);std::cout<<",\"closestLocal\":";json(g.closest_local);std::cout<<",\"closest\":";json(g.closest);std::cout<<",\"delta\":";json(g.delta);std::cout<<",\"normal\":";json(g.normal);std::cout<<",\"spherePoint\":";json(g.sphere_point);std::cout<<",\"squaredDistance\":";json(g.squared_distance);std::cout<<",\"distance\":";json(g.distance);std::cout<<",\"gap\":";json(g.gap);std::cout<<",\"relation\":"<<unsigned(g.relation)<<'}';}else std::cout<<"null";
    std::cout<<",\"squaredCross\":";if(r.squared_cross)json(*r.squared_cross);else std::cout<<"null";std::cout<<",\"sineSquared\":";if(r.sine_squared)json(*r.sine_squared);else std::cout<<"null";
    std::cout<<",\"candidates\":[";for(std::size_t i=0;i<r.candidates.size();++i){if(i)std::cout<<',';const auto&a=r.candidates[i];std::cout<<"{\"feature\":"<<unsigned(a.feature)<<",\"disposition\":"<<unsigned(a.disposition)<<",\"barycentric\":";json(a.barycentric);std::cout<<",\"kkt\":[";json(a.kkt[0]);std::cout<<',';json(a.kkt[1]);std::cout<<"],\"kktCount\":"<<a.kkt_count<<'}';}
    std::cout<<"],\"candidatesExamined\":"<<r.candidates_examined<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtRefinementLimited\":"<<(r.sqrt_refinement_limited?"true":"false")<<"}}";
}
int main(int argc,char**argv){try{
    const auto fixtures=cases();if(argc==2&&std::string(argv[1])=="--fixtures"){
        std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"schema\":1,\"kind\":\"sphere-triangle-fixtures\",\"fixtures\":[";
        for(std::size_t i=0;i<fixtures.size();++i){if(i)std::cout<<',';const auto&c=fixtures[i];dump(c,st::query_sphere_triangle(c.sphere,c.triangle,c.settings));}std::cout<<"]}\n";return 0;}
    require(argc==1,"Usage: sphere_triangle_tests [--fixtures]");
    for(const auto&c:fixtures)test(c.name,[&]{const auto r=st::query_sphere_triangle(c.sphere,c.triangle,c.settings);
        if(r.status!=c.expected||r.reason!=c.reason){std::cerr<<"actual status="<<unsigned(r.status)<<" reason="<<unsigned(r.reason)<<" message="<<r.message<<'\n';throw std::runtime_error("Unexpected model result");}
        require(r.geometry.has_value()==(r.status==st::Status::completed),"Geometry failure atomicity");if(r.geometry){require(r.candidates_examined==7&&r.candidates.size()==7,"All candidates required");require(r.geometry->surface_id==c.triangle.id,"Stable surface ID");for(const auto& n:r.geometry->normal)require(std::isfinite(n.lower())&&std::isfinite(n.upper())&&n.lower()>=-1&&n.upper()<=1,"Finite unit component bounds");}});
    test("face edge vertex rational references and source immutability",[]{Case c;const auto original=c;auto r=st::query_sphere_triangle(c.sphere,c.triangle);require(r.geometry.has_value(),"Face success");contains(r.geometry->closest,{1,0,1});contains(r.geometry->normal,{0,1,0});require(r.geometry->squared_distance.contains(1)&&r.geometry->gap.contains(.5),"Face distance and gap");
        c.sphere={{2,3,-4},5};r=st::query_sphere_triangle(c.sphere,c.triangle);contains(r.geometry->closest,{2,0,0});contains(r.geometry->normal,{0,.6,-.8});require(r.geometry->distance.contains(5),"Edge exact distance");
        c.sphere={{-3,4,0},5};r=st::query_sphere_triangle(c.sphere,c.triangle);contains(r.geometry->closest,{0,0,0});contains(r.geometry->normal,{-.6,.8,0});require(r.geometry->squared_distance.contains(25),"Vertex exact squared distance");require(bits(c.triangle.vertices[1].x)==bits(original.triangle.vertices[1].x)&&c.triangle.id==original.triangle.id,"Input remains immutable");});
    test("feature tie is not normal nonuniqueness",[]{Case c;c.sphere.center={0,1,0};const auto r=st::query_sphere_triangle(c.sphere,c.triangle);require(r.geometry.has_value(),"Boundary normal success");require(std::popcount(r.geometry->surviving_features)>1,"Multiple retained features");contains(r.geometry->normal,{0,1,0});});
    test("near plane outside triangle remains separated",[]{Case c;c.sphere={{3,.125,3},.25};const auto r=st::query_sphere_triangle(c.sphere,c.triangle);require(r.geometry&&r.geometry->relation==st::Relation::separated&&r.geometry->distance.lower()>1,"No infinite-plane fallback");contains(r.geometry->closest,{2,0,2});});
    test("normal changes side but not winding",[]{Case c;auto front=st::query_sphere_triangle(c.sphere,c.triangle);std::swap(c.triangle.vertices[1],c.triangle.vertices[2]);auto reverse=st::query_sphere_triangle(c.sphere,c.triangle);contains(reverse.geometry->normal,{0,1,0});c.sphere.center.y=-1;auto back=st::query_sphere_triangle(c.sphere,c.triangle);contains(back.geometry->normal,{0,-1,0});require(front.geometry->gap.contains(.5)&&back.geometry->gap.contains(.5),"Two sided model");});
    test("rigid rational rotation and translation covariance",[]{Case c;const auto transform=[](Vec3 p){return Vec3{p.z+8,-p.y-16,p.x+32};};c.sphere.center=transform(c.sphere.center);for(auto&v:c.triangle.vertices)v=transform(v);auto r=st::query_sphere_triangle(c.sphere,c.triangle);require(r.geometry.has_value(),"Rotated geometry");contains(r.geometry->closest,{9,-16,33});contains(r.geometry->normal,{0,-1,0});require(r.geometry->distance.contains(1),"Rigid distance");});
    test("large common translation retains precise local delta",[]{Case c;const double offset=0x1p40;for(auto& v:c.triangle.vertices){v.x+=offset;v.y-=offset;v.z+=offset;}c.sphere.center={offset+1,-offset+1,offset+1};const auto r=st::query_sphere_triangle(c.sphere,c.triangle);require(r.geometry.has_value(),"Large-offset success");contains(r.geometry->delta,{0,1,0});contains(r.geometry->closest_local,{1,0,1});require(r.geometry->closest[0].upper()-r.geometry->closest[0].lower()>c.settings.maximum_local_width,"World width is disclosed not clamped to local budget");require(r.geometry->distance.contains(1),"No world q resubtraction");});
    test("candidate budget preserves diagnostic prefix and retry",[]{Case c;c.settings.max_candidates=1;auto bad=st::query_sphere_triangle(c.sphere,c.triangle,c.settings);require(!bad.geometry&&bad.candidates_examined==1&&bad.candidates.size()==1,"Candidate prefix only");auto good=st::query_sphere_triangle(c.sphere,c.triangle);require(good.geometry.has_value(),"Reuse after failure");});
    test("all invalid finite setting boundaries and nonfinite inputs fail closed",[]{Case c;std::vector<st::Settings> settings(10);settings[0].max_candidates=8;settings[1].sqrt_refinements=0;settings[2].max_total_sqrt_refinements=0;settings[3].maximum_local_width=-1;settings[4].maximum_local_width=std::numeric_limits<double>::infinity();settings[5].maximum_normal_width=0;settings[6].maximum_normal_width=std::numeric_limits<double>::quiet_NaN();settings[7].minimum_sine_squared=-1;settings[8].minimum_sine_squared=2;settings[9].minimum_sine_squared=std::numeric_limits<double>::quiet_NaN();for(const auto&s:settings){const auto r=st::query_sphere_triangle(c.sphere,c.triangle,s);require(r.status==st::Status::invalid_input&&!r.geometry,"Bad settings");}
        c.sphere.center.x=std::numeric_limits<double>::quiet_NaN();auto r=st::query_sphere_triangle(c.sphere,c.triangle);require(r.status==st::Status::invalid_input&&!r.geometry,"NaN input");c=Case{};c.triangle.vertices[2].z=std::numeric_limits<double>::infinity();r=st::query_sphere_triangle(c.sphere,c.triangle);require(r.status==st::Status::invalid_input&&!r.geometry,"Infinity input");});
    test("returned snapshots own values across later queries",[]{Case c;auto a=st::query_sphere_triangle(c.sphere,c.triangle);const auto before=bits(a.geometry->closest[0].lower());c.sphere.center={20,4,-20};auto b=st::query_sphere_triangle(c.sphere,c.triangle);require(b.geometry&&bits(a.geometry->closest[0].lower())==before,"Owned output");a.candidates.clear();require(b.candidates.size()==7,"Independent candidate snapshots");});
    test("normal width gate includes inward rounded subtraction boundary",[]{Case c;c.sphere.center={0,1,0};const auto first=st::query_sphere_triangle(c.sphere,c.triangle);require(first.geometry.has_value(),"Boundary reference geometry");
        double scalar_width=0;for(const auto& n:first.geometry->normal)scalar_width=std::max(scalar_width,n.upper()-n.lower());
        bool outward_exceeds=false;for(const auto& n:first.geometry->normal){const auto width=I::point(n.upper())-I::point(n.lower());outward_exceeds=outward_exceeds||width.upper()>scalar_width;}
        require(outward_exceeds,"Corpus exercises a width rounded inward or at its outward guard");c.settings.maximum_normal_width=scalar_width;const auto result=st::query_sphere_triangle(c.sphere,c.triangle,c.settings);
        require(result.status==st::Status::quality_unresolved&&result.reason==st::Reason::normal_width&&!result.geometry,"Outward width gate must reject scalar RN boundary");});
    test("limited sqrt may complete only within an explicit wider normal profile",[]{Case c;c.sphere.center={2,3,-4};c.settings.sqrt_refinements=1;c.settings.maximum_normal_width=2;const auto r=st::query_sphere_triangle(c.sphere,c.triangle,c.settings);
        require(r.geometry&&r.sqrt_refinement_limited,"Limited enclosure remains valid");contains(r.geometry->normal,{0,.6,-.8});require(r.geometry->distance.contains(5),"Known distance in limited enclosure");});
    test("rounding mode fails without changing caller state",[]{Case c;const int old=std::fegetround();require(std::fesetround(FE_UPWARD)==0,"Set test rounding");const auto r=st::query_sphere_triangle(c.sphere,c.triangle);const int after=std::fegetround();std::fesetround(old);require(r.status==st::Status::unsupported_environment&&!r.geometry&&after==FE_UPWARD,"Environment preserved");require(st::query_sphere_triangle(c.sphere,c.triangle).geometry.has_value(),"Environment restored by test only");});
#if defined(_M_X64) || defined(__x86_64__)
    test("FTZ DAZ failure preserves caller control and recovers",[]{Case c;const auto saved=_mm_getcsr();_mm_setcsr(saved|0x8040u);const auto r=st::query_sphere_triangle(c.sphere,c.triangle);const auto after=_mm_getcsr();_mm_setcsr(saved);require(r.status==st::Status::unsupported_environment&&!r.geometry&&(after&0x8040u)==0x8040u,"No environment mutation");require(st::query_sphere_triangle(c.sphere,c.triangle).geometry.has_value(),"Retry after environment correction");});
#endif
    std::cout<<"PASS "<<passed<<" groups; "<<fixtures.size()<<" finite complete-input fixtures\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL after "<<passed<<" groups: "<<e.what()<<'\n';return 1;}}
