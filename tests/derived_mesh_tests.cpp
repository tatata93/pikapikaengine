#include "pikapika/derived_mesh.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <chrono>
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

namespace dm=pikapika::derived_mesh;
using pikapika::Vec3;
using I=pikapika::interval::Interval;
struct Case {
    std::string name;
    std::vector<Vec3> positions{{0,0,0},{1,0,0},{0,1,0}};
    std::vector<dm::Triangle> triangles{{0,1,2}};
    dm::Settings settings;
    dm::Status status=dm::Status::completed;
    dm::Reason reason=dm::Reason::none;
};
void require(bool b,const char* message){if(!b)throw std::runtime_error(message);}
std::uint32_t bits(float x){return std::bit_cast<std::uint32_t>(x);}
std::uint64_t bits(double x){return std::bit_cast<std::uint64_t>(x);}
std::vector<Case> cases(){
    std::vector<Case> out;auto add=[&](Case c){out.push_back(std::move(c));};Case c;
    c.name="xy-unit";add(c);
    c.name="rational-345";c.positions={{0,0,0},{1,0,0},{0,4,-3}};add(c);
    c.name="reverse-winding";c.triangles={{0,2,1}};add(c);
    c=Case{};c.name="rigid-180-x";c.positions[2]={0,-1,0};add(c);
    c.name="affine-shear";c.positions={{1,-2,3},{3,-2,3},{2,2,4}};add(c);
    c=Case{};c.name="signed-zero";c.positions[0]={-0.0,0,-0.0};add(c);
    c.name="subnormal-component";c.positions[0].z=std::numeric_limits<double>::denorm_min();add(c);
    c=Case{};c.name="float32-subnormal-component";c.positions[0].z=0x1p-149;add(c);
    c=Case{};c.name="tie-even-low";c.positions[1].x=1+0x1p-24;add(c);
    c.name="tie-even-high";c.positions[1].x=1+3*0x1p-24;add(c);
    c.name="tie-next-up";c.positions[1].x=std::nextafter(1+0x1p-24,2.0);add(c);
    c=Case{};c.name="two-face-square";c.positions.push_back({1,1,0});c.triangles={{0,1,3},{0,3,2}};add(c);
    c=Case{};c.name="large-offset-collapse";c.positions={{999999,999999,0},{999999.001,999999,0},{999999,999999.001,0}};c.status=dm::Status::degenerate;c.reason=dm::Reason::zero_cross;add(c);
    c=Case{};c.name="lbs-half-turn-collapse";c.positions={{0,0,0},{0,0,0},{0,0,0}};c.status=dm::Status::degenerate;c.reason=dm::Reason::zero_cross;add(c);
    c=Case{};c.name="exact-axis-collinear";c.positions[2]={2,0,0};c.status=dm::Status::degenerate;c.reason=dm::Reason::zero_cross;add(c);
    c=Case{};c.name="area-below-floor";c.positions[2].y=1e-13;c.status=dm::Status::quality_rejected;c.reason=dm::Reason::below_area_floor;add(c);
    c.name="floor-nearest-below";c.positions[2].y=double(float(1e-12));add(c);
    c=Case{};c.name="floor-next-above";c.positions[2].y=double(std::nextafter(float(1e-12),std::numeric_limits<float>::infinity()));add(c);
    c=Case{};c.name="collinear-uncertain";c.positions={{0,0,0},{1e6,1e6,0},{999999,999999,0}};c.status=dm::Status::quality_unresolved;c.reason=dm::Reason::cross_uncertain;add(c);
    c=Case{};c.name="area-threshold-uncertain";
    const float z=std::nextafter(float(1e-12/(8*std::sqrt(2.0))),0.0f);
    c.positions={{0,0,0},{8,8,0},{8,8,double(z)}};c.status=dm::Status::quality_unresolved;c.reason=dm::Reason::area_uncertain;add(c);
    c=Case{};c.name="sqrt-budget-unresolved";c.positions[2]={0,4,-3};c.settings.sqrt_refinements=1;c.status=dm::Status::quality_unresolved;c.reason=dm::Reason::normal_uncertain;add(c);
    c=Case{};c.name="sqrt-budget-maximum";c.settings.sqrt_refinements=256;add(c);
    c=Case{};c.name="coordinate-boundary";c.positions={{1e6,0,0},{999999,0,0},{1e6,1,0}};add(c);
    c=Case{};c.name="coordinate-overflow";c.positions[0].x=std::nextafter(1e6,std::numeric_limits<double>::infinity());c.status=dm::Status::invalid_input;c.reason=dm::Reason::position_domain;add(c);
    c=Case{};c.name="finite-unrenderable-deformation";c.positions[0].x=1e300;c.status=dm::Status::invalid_input;c.reason=dm::Reason::position_domain;add(c);
    c=Case{};c.name="index-outside";c.triangles[0][2]=3;c.status=dm::Status::invalid_input;c.reason=dm::Reason::index_range;add(c);
    c=Case{};c.name="duplicate-index";c.triangles[0][2]=1;c.status=dm::Status::invalid_input;c.reason=dm::Reason::duplicate_index;add(c);
    c=Case{};c.name="second-invalid-preflight";c.triangles.push_back({0,1,3});c.status=dm::Status::invalid_input;c.reason=dm::Reason::index_range;add(c);
    c=Case{};c.name="second-degenerate-no-buffer";c.positions.push_back({0,0,0});c.triangles.push_back({0,1,3});c.status=dm::Status::degenerate;c.reason=dm::Reason::zero_cross;add(c);
    c=Case{};c.name="no-vertices";c.positions.clear();c.status=dm::Status::invalid_input;c.reason=dm::Reason::vertex_count;add(c);
    c=Case{};c.name="no-faces";c.triangles.clear();c.status=dm::Status::invalid_input;c.reason=dm::Reason::triangle_count;add(c);
    c=Case{};c.name="vertex-budget";c.positions.push_back({1,1,0});c.settings.max_vertices=3;c.status=dm::Status::budget_exceeded;c.reason=dm::Reason::vertex_budget;add(c);
    c=Case{};c.name="face-budget";c.triangles.push_back({0,2,1});c.settings.max_triangles=1;c.status=dm::Status::budget_exceeded;c.reason=dm::Reason::triangle_budget;add(c);
    c=Case{};c.name="bad-vertex-setting-low";c.settings.max_vertices=2;c.status=dm::Status::invalid_input;c.reason=dm::Reason::settings;add(c);
    c.name="bad-vertex-setting-high";c.settings.max_vertices=65537;add(c);
    c=Case{};c.name="bad-triangle-setting-low";c.settings.max_triangles=0;c.status=dm::Status::invalid_input;c.reason=dm::Reason::settings;add(c);
    c.name="bad-triangle-setting-high";c.settings.max_triangles=131073;add(c);
    c=Case{};c.name="bad-sqrt-setting-low";c.settings.sqrt_refinements=0;c.status=dm::Status::invalid_input;c.reason=dm::Reason::settings;add(c);
    c.name="bad-sqrt-setting-high";c.settings.sqrt_refinements=257;add(c);
    c=Case{};c.name="hard-budget-settings";c.settings={65536,131072,128};add(c);
    return out;
}
void vector_bits(const auto&values){std::cout<<'[';bool first=true;for(float x:values){if(!first)std::cout<<',';first=false;std::cout<<bits(x);}std::cout<<']';}
void interval_json(const I&value){std::cout<<'['<<value.lower()<<','<<value.upper()<<']';}
void bounds_json(const dm::Bounds3&values){std::cout<<'[';for(unsigned i=0;i<3;++i){if(i)std::cout<<',';interval_json(values[i]);}std::cout<<']';}
void dump(const Case&c,const dm::Result&r){
    std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"positions\":[";
    for(std::size_t i=0;i<c.positions.size();++i){if(i)std::cout<<',';auto p=c.positions[i];std::cout<<'['<<p.x<<','<<p.y<<','<<p.z<<']';}
    std::cout<<"],\"triangles\":[";for(std::size_t i=0;i<c.triangles.size();++i){if(i)std::cout<<',';auto t=c.triangles[i];std::cout<<'['<<t[0]<<','<<t[1]<<','<<t[2]<<']';}
    std::cout<<"],\"settings\":["<<c.settings.max_vertices<<','<<c.settings.max_triangles<<','<<c.settings.sqrt_refinements<<"]},\"result\":{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"failedVertex\":";
    if(r.failed_vertex)std::cout<<*r.failed_vertex;else std::cout<<"null";
    std::cout<<",\"failedFace\":";if(r.failed_face)std::cout<<*r.failed_face;else std::cout<<"null";
    std::cout<<",\"positionsBits\":";if(r.geometry){std::cout<<'[';bool first=true;for(const auto&p:r.geometry->positions){if(!first)std::cout<<',';first=false;vector_bits(p);}std::cout<<']';}else std::cout<<"null";
    std::cout<<",\"triangles\":";if(r.geometry){std::cout<<'[';bool first=true;for(auto t:r.geometry->triangles){if(!first)std::cout<<',';first=false;std::cout<<'['<<t[0]<<','<<t[1]<<','<<t[2]<<']';}std::cout<<']';}else std::cout<<"null";
    std::cout<<",\"interleavedBits\":";if(r.geometry)vector_bits(r.geometry->interleaved);else std::cout<<"null";
    std::cout<<",\"minimumBits\":";if(r.geometry)vector_bits(r.geometry->minimum);else std::cout<<"null";
    std::cout<<",\"maximumBits\":";if(r.geometry)vector_bits(r.geometry->maximum);else std::cout<<"null";
    std::cout<<",\"audits\":[";
    for(std::size_t i=0;i<r.audits.size();++i){if(i)std::cout<<',';const auto&a=r.audits[i];std::cout<<"{\"face\":"<<a.face<<",\"cross\":";bounds_json(a.cross);std::cout<<",\"squaredCross\":";interval_json(a.squared_cross);
        std::cout<<",\"normalized\":";if(a.normalized)bounds_json(*a.normalized);else std::cout<<"null";
        std::cout<<",\"normalBits\":";if(a.normal)vector_bits(*a.normal);else std::cout<<"null";
        std::cout<<",\"normalError\":";if(a.normal_error){const auto&e=*a.normal_error;std::cout<<'['<<e[0]<<','<<e[1]<<','<<e[2]<<']';}else std::cout<<"null";
        std::cout<<",\"sqrtRefinements\":"<<a.sqrt_refinements<<",\"sqrtRefinementLimited\":"<<(a.sqrt_refinement_limited?"true":"false")<<'}';}
    std::cout<<"],\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtLimitedFaces\":"<<r.sqrt_limited_faces<<"}}";
}
void audit(const Case&c,const dm::Result&r){
    if(r.status!=c.status||r.reason!=c.reason){std::cerr<<"case "<<c.name<<" actual "<<unsigned(r.status)<<'/'<<unsigned(r.reason)<<" expected "<<unsigned(c.status)<<'/'<<unsigned(c.reason)<<'\n';throw std::runtime_error("Case classification mismatch");}
    require(r.geometry.has_value()==(r.status==dm::Status::completed),"Failure exposed geometry");
    std::uint64_t total=0;unsigned limited=0;for(const auto&a:r.audits){total+=a.sqrt_refinements;if(a.sqrt_refinement_limited)++limited;}
    require(total==r.sqrt_refinements&&limited==r.sqrt_limited_faces,"Counter accounting mismatch");
    if(!r.geometry)return;
    require(r.geometry->triangles==c.triangles,"Triangle order changed");
    require(r.geometry->positions.size()==c.positions.size()&&r.geometry->interleaved.size()==18*c.triangles.size(),"Buffer size mismatch");
    require(r.audits.size()==c.triangles.size(),"Missing success audit");
    for(std::size_t f=0;f<c.triangles.size();++f){const auto&a=r.audits[f];require(a.face==f&&a.normal&&a.normalized&&a.normal_error,"Missing normal proof");
        require(a.squared_cross.lower()>dm::minimum_cross_squared,"Area not certified");
        require(std::any_of(a.cross.begin(),a.cross.end(),[](const I&x){return x.strictly_positive()||x.strictly_negative();}),"Nonzero cross not certified");
        for(unsigned axis=0;axis<3;++axis){require(std::isfinite((*a.normal)[axis])&&(*a.normal_error)[axis]<=dm::maximum_normal_component_error,"Normal not certified");
            for(unsigned corner=0;corner<3;++corner){auto index=c.triangles[f][corner];const auto&p=c.positions[index];const double original[]={p.x,p.y,p.z};
                require(bits(r.geometry->interleaved[f*18+corner*6+axis])==bits(static_cast<float>(original[axis])),"Expanded position mismatch");
                require(bits(r.geometry->interleaved[f*18+corner*6+axis+3])==bits((*a.normal)[axis]),"Flat normal mismatch");}}}
}
int main(int argc,char**argv){
    try {const auto all=cases();const bool fixtures=argc==2&&std::string(argv[1])=="--fixtures";
        if(argc>1&&!fixtures)throw std::runtime_error("Usage: derived-mesh-tests [--fixtures]");
        std::cout<<std::setprecision(17);if(fixtures)std::cout<<"{\"schema\":1,\"fixtures\":[";
        unsigned count=0;for(const auto&c:all){const auto before=c.positions;const auto faces=c.triangles;const auto r=dm::prepare(c.positions,c.triangles,c.settings);audit(c,r);
            require(c.triangles==faces,"Input triangles changed");for(std::size_t i=0;i<before.size();++i){require(bits(before[i].x)==bits(c.positions[i].x)&&bits(before[i].y)==bits(c.positions[i].y)&&bits(before[i].z)==bits(c.positions[i].z),"Input bits changed");}
            if(fixtures){if(count)std::cout<<',';dump(c,r);}++count;}
        if(fixtures){std::cout<<"]}\n";return 0;}
        auto c=Case{};auto result=dm::prepare(c.positions,c.triangles);require((*result.audits[0].normal)==dm::Float3{0,0,1},"XY analytic normal");++count;
        c.positions[2]={0,4,-3};result=dm::prepare(c.positions,c.triangles);require((*result.audits[0].normal)==dm::Float3{0,float(3.0/5),float(4.0/5)},"345 analytic normal");++count;
        // Stored outputs own all arrays, not views into future author edits.
        c.positions[1].x=9;c.triangles[0]={2,1,0};require(result.geometry->positions[1][0]==1&&result.geometry->triangles[0][0]==0,"Output snapshot aliases source");++count;
        c=Case{};c.settings.sqrt_refinements=24;result=dm::prepare(c.positions,c.triangles,c.settings);
        require(result.status==dm::Status::completed&&result.sqrt_limited_faces==1&&result.audits[0].sqrt_refinement_limited,"Limited but certified normal was rejected");++count;
        c=Case{};c.positions[0].x=std::numeric_limits<double>::quiet_NaN();require(dm::prepare(c.positions,c.triangles).status==dm::Status::invalid_input,"NaN accepted");++count;
        c.positions[0].x=std::numeric_limits<double>::infinity();require(dm::prepare(c.positions,c.triangles).status==dm::Status::invalid_input,"Infinity accepted");++count;
        c=Case{};c.positions.resize(65536);c.settings={65536,131072,128};require(dm::prepare(c.positions,c.triangles,c.settings).status==dm::Status::completed,"Hard vertex boundary failed");++count;
        c.positions.push_back({});require(dm::prepare(c.positions,c.triangles,c.settings).status==dm::Status::budget_exceeded,"Hard vertex overflow accepted");++count;
        c=Case{};c.triangles.resize(131073,{0,1,2});c.settings.max_triangles=131072;require(dm::prepare(c.positions,c.triangles,c.settings).status==dm::Status::budget_exceeded,"Hard face overflow accepted");++count;
        {
            Case capacity;capacity.positions.resize(65536);capacity.triangles.resize(131072,{0,1,2});capacity.settings={65536,131072,128};
            const auto original_positions=capacity.positions;const auto original_faces=capacity.triangles;
            const auto start=std::chrono::steady_clock::now();
            const auto full=dm::prepare(capacity.positions,capacity.triangles,capacity.settings);
            const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
            require(full.status==dm::Status::completed&&full.geometry,"Simultaneous hard capacity failed");
            require(full.geometry->positions.size()==65536&&full.geometry->triangles==original_faces&&
                full.geometry->interleaved.size()==131072*18&&full.audits.size()==131072,"Hard capacity output truncated");
            require(full.audits.back().face==131071&&full.audits.back().normal.has_value(),"Last hard capacity face not processed");
            require(capacity.triangles==original_faces,"Hard capacity changed input indices");
            for(std::size_t i=0;i<original_positions.size();++i){const auto&a=original_positions[i];const auto&b=capacity.positions[i];
                require(bits(a.x)==bits(b.x)&&bits(a.y)==bits(b.y)&&bits(a.z)==bits(b.z),"Hard capacity changed input position bits");}
            std::cout<<"observed hard capacity prepare seconds: "<<elapsed<<" (65536 vertices, 131072 faces; not a general performance guarantee)\n";++count;
        }
        // A local-valid millimetre triangle can still collapse after a world
        // Float32 translation; this kernel explicitly makes no world guarantee.
        c=Case{};c.positions[1].x=.001;c.positions[2].y=.001;result=dm::prepare(c.positions,c.triangles);require(result.status==dm::Status::completed,"Local small triangle failed");
        volatile float offset=1e6f;volatile float world0=offset+result.geometry->positions[0][0];volatile float world1=offset+result.geometry->positions[1][0];require(world0==world1,"World collapse scope example failed");++count;
        const int saved=std::fegetround();require(std::fesetround(FE_DOWNWARD)==0,"Cannot set test rounding mode");c=Case{};auto unsupported=dm::prepare(c.positions,c.triangles);const int retained=std::fegetround();std::fesetround(saved);
        require(unsupported.status==dm::Status::unsupported_environment&&!unsupported.geometry&&retained==FE_DOWNWARD,"Rounding environment not rejected/preserved");++count;
#if defined(_M_X64) || defined(__x86_64__)
        const auto control=_mm_getcsr();_mm_setcsr(control|0x8040u);unsupported=dm::prepare(c.positions,c.triangles);const auto retained_control=_mm_getcsr();_mm_setcsr(control);
        require(unsupported.status==dm::Status::unsupported_environment&&!unsupported.geometry&&retained_control==(control|0x8040u),"FTZ/DAZ environment not rejected/preserved");++count;
#endif
        require(dm::prepare(c.positions,c.triangles).status==dm::Status::completed,"Failure prevented later reuse");++count;
        std::cout<<"derived mesh: "<<count<<" groups passed ("<<all.size()<<" fixtures)\n";return 0;
    }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
