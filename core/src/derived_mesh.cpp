#include "pikapika/derived_mesh.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <limits>
#include <new>
#include <stdexcept>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Derived mesh certification requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#define PIKA_DERIVED_NOINLINE __declspec(noinline)
#elif defined(__clang__) || defined(__GNUC__)
#define PIKA_DERIVED_NOINLINE __attribute__((noinline))
#if defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif
#else
#define PIKA_DERIVED_NOINLINE
#endif

namespace pikapika::derived_mesh {
namespace {
using I=interval::Interval;
static_assert(sizeof(float)==4 && std::numeric_limits<float>::is_iec559 &&
    std::numeric_limits<float>::radix==2 && std::numeric_limits<float>::digits==24 &&
    std::numeric_limits<float>::min_exponent==-125 && std::numeric_limits<float>::max_exponent==128 &&
    std::numeric_limits<float>::has_denorm==std::denorm_present,
    "Derived mesh requires IEEE binary32 with subnormals.");
PIKA_DERIVED_NOINLINE float rounded(double value) {volatile float out=static_cast<float>(value);return out;}
PIKA_DERIVED_NOINLINE float float_product(float a,float b) {volatile float out=a*b;return out;}
const char* environment_issue() {
    if(const char* issue=interval::environment_issue())return issue;
    const float tiny=std::numeric_limits<float>::denorm_min();
    if(rounded(1.0+0x1p-24)!=1.0f || rounded(1.0+3*0x1p-24)!=0x1.000004p0f ||
       rounded(-1.0-0x1p-24)!=-1.0f || rounded(std::nextafter(1.0+0x1p-24,2.0))!=0x1.000002p0f)
        return "binary32 round-to-nearest ties-to-even conversion probes failed";
    if(rounded(0x1p-149)!=tiny || rounded(0x1p-150)!=0 || rounded(3*0x1p-150)!=2*tiny ||
       float_product(tiny,1)!=tiny || float_product(std::numeric_limits<float>::min(),.5f)!=0x1p-127f)
        return "binary32 gradual-underflow probes failed";
    return nullptr;
}
void fail(Result&out,Status status,Reason reason,const char* text) noexcept {
    out.status=status;out.reason=reason;out.geometry.reset();
    // Stable status/reason remain available even when diagnostic allocation fails.
    try {out.message=text;}catch(...){out.message.clear();}
}
bool zero(const I&value){return value.lower()==0 && value.upper()==0;}
I difference(double a,double b) {
    // Equal point values have exactly zero difference, including either zero sign.
    // This identity also lets coincident quantized corners certify degeneracy.
    return a==b?I::point(0):I::point(a)-I::point(b);
}
Bounds3 edge(const Float3&a,const Float3&b){return {difference(b[0],a[0]),difference(b[1],a[1]),difference(b[2],a[2])};}
Bounds3 cross(const Bounds3&a,const Bounds3&b){return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};}
bool finite(const I&value){return std::isfinite(value.lower()) && std::isfinite(value.upper());}
}

Result prepare(std::span<const Vec3> positions,std::span<const Triangle> triangles,const Settings&s) {
    Result out;
    try {
        if(const char* issue=environment_issue()){fail(out,Status::unsupported_environment,Reason::environment,issue);return out;}
        if(s.max_vertices<3 || s.max_vertices>65536 || s.max_triangles<1 || s.max_triangles>131072 || s.sqrt_refinements<1 || s.sqrt_refinements>256){
            fail(out,Status::invalid_input,Reason::settings,"Invalid derived mesh budgets");return out;}
        if(positions.size()<3){fail(out,Status::invalid_input,Reason::vertex_count,"At least three positions required");return out;}
        if(triangles.empty()){fail(out,Status::invalid_input,Reason::triangle_count,"At least one face required");return out;}
        if(positions.size()>s.max_vertices){fail(out,Status::budget_exceeded,Reason::vertex_budget,"Vertex budget exceeded");return out;}
        if(triangles.size()>s.max_triangles){fail(out,Status::budget_exceeded,Reason::triangle_budget,"Triangle budget exceeded");return out;}
        // Complete structural preflight before quantization or face processing.
        for(std::size_t i=0;i<positions.size();++i){const auto&p=positions[i];
            if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||
               std::max({std::abs(p.x),std::abs(p.y),std::abs(p.z)})>coordinate_limit){
                out.failed_vertex=i;fail(out,Status::invalid_input,Reason::position_domain,"Position outside finite +/-1e6 metre domain");return out;}}
        for(std::size_t f=0;f<triangles.size();++f){const auto&t=triangles[f];
            for(auto index:t)if(index>=positions.size()){out.failed_face=f;fail(out,Status::invalid_input,Reason::index_range,"Face index outside position array");return out;}
            if(t[0]==t[1]||t[1]==t[2]||t[0]==t[2]){out.failed_face=f;fail(out,Status::invalid_input,Reason::duplicate_index,"Face repeats a vertex index");return out;}}
        Geometry candidate;candidate.positions.reserve(positions.size());candidate.triangles.assign(triangles.begin(),triangles.end());
        candidate.interleaved.reserve(triangles.size()*18);out.audits.reserve(triangles.size());
        for(const auto&p:positions)candidate.positions.push_back({rounded(p.x),rounded(p.y),rounded(p.z)});
        candidate.minimum=candidate.maximum=candidate.positions.front();
        for(const auto&p:candidate.positions)for(unsigned i=0;i<3;++i){candidate.minimum[i]=std::min(candidate.minimum[i],p[i]);candidate.maximum[i]=std::max(candidate.maximum[i],p[i]);}
        for(std::size_t f=0;f<triangles.size();++f){out.failed_face=f;const auto&t=triangles[f];
            const auto&a=candidate.positions[t[0]],&b=candidate.positions[t[1]],&c=candidate.positions[t[2]];
            FaceAudit audit;audit.face=f;audit.cross=cross(edge(a,b),edge(a,c));
            audit.squared_cross=interval::square(audit.cross[0])+interval::square(audit.cross[1])+interval::square(audit.cross[2]);
            out.audits.push_back(std::move(audit));auto&record=out.audits.back();
            if(!finite(record.squared_cross)){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Nonfinite cross enclosure");return out;}
            if(std::all_of(record.cross.begin(),record.cross.end(),zero)){
                fail(out,Status::degenerate,Reason::zero_cross,"Quantized face has provably zero cross product");return out;}
            if(record.squared_cross.upper()<=minimum_cross_squared){
                fail(out,Status::quality_rejected,Reason::below_area_floor,"Quantized face cross squared is below the fixed area quality floor");return out;}
            if(std::none_of(record.cross.begin(),record.cross.end(),[](const I&x){return x.strictly_positive()||x.strictly_negative();})){
                fail(out,Status::quality_unresolved,Reason::cross_uncertain,"Nonzero cross component could not be certified");return out;}
            if(record.squared_cross.lower()<=minimum_cross_squared){
                fail(out,Status::quality_unresolved,Reason::area_uncertain,"Cross squared enclosure straddles area quality floor");return out;}
            const auto norm=interval::sqrt_enclosure(record.squared_cross,s.sqrt_refinements);
            record.sqrt_refinements=norm.refinements;record.sqrt_refinement_limited=norm.refinement_limited;
            out.sqrt_refinements+=norm.refinements;if(norm.refinement_limited)++out.sqrt_limited_faces;
            if(!finite(norm.value)||!norm.value.strictly_positive()){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Invalid normal length enclosure");return out;}
            record.normalized=Bounds3{record.cross[0]/norm.value,record.cross[1]/norm.value,record.cross[2]/norm.value};
            const double ux=double(b[0])-double(a[0]),uy=double(b[1])-double(a[1]),uz=double(b[2])-double(a[2]);
            const double vx=double(c[0])-double(a[0]),vy=double(c[1])-double(a[1]),vz=double(c[2])-double(a[2]);
            const std::array<double,3> n{uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx};
            const double length=std::hypot(n[0],n[1],n[2]);
            if(!std::isfinite(length)||length<=0){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Point normal candidate could not be formed");return out;}
            record.normal=Float3{rounded(n[0]/length),rounded(n[1]/length),rounded(n[2]/length)};
            record.normal_error=std::array<double,3>{};
            for(unsigned i=0;i<3;++i){
                const auto delta=I::point((*record.normal)[i])-(*record.normalized)[i];
                (*record.normal_error)[i]=std::max(std::abs(delta.lower()),std::abs(delta.upper()));}
            for(double error:*record.normal_error)if(!std::isfinite(error)||error>maximum_normal_component_error){
                fail(out,Status::quality_unresolved,Reason::normal_uncertain,"Float32 normal accuracy could not be certified");return out;}
            for(const auto index:t){const auto&p=candidate.positions[index];candidate.interleaved.insert(candidate.interleaved.end(),p.begin(),p.end());candidate.interleaved.insert(candidate.interleaved.end(),record.normal->begin(),record.normal->end());}
        }
        out.failed_face.reset();out.geometry=std::move(candidate);out.status=Status::completed;out.reason=Reason::none;return out;
    }catch(const std::bad_alloc&){fail(out,Status::budget_exceeded,Reason::allocation_failure,"Derived mesh allocation failed");}
    catch(const std::exception&){fail(out,Status::numerical_failure,Reason::nonfinite_intermediate,"Derived mesh certification operation failed");}
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
