#include "pikapika/skinning.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Skinning reference requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::skinning {
namespace {
constexpr double matrix_limit=1e150;
constexpr std::uint64_t maximum_id=9007199254740991ULL;
struct IllConditioned {};
void finite_result(double x){if(!std::isfinite(x))throw std::domain_error("Nonfinite skinning intermediate");}
void valid_id(std::uint64_t id){if(id==0||id>maximum_id)throw std::invalid_argument("Skin bone ID outside exact numeric domain");}
void matrix_valid(const Mat4&m){
    for(double x:m)if(!std::isfinite(x)||std::abs(x)>matrix_limit)throw std::invalid_argument("Skin affine matrix outside finite +/-1e150 domain");
    if(m[3]!=0||m[7]!=0||m[11]!=0||m[15]!=1)throw std::invalid_argument("Skin matrix requires exact affine last row");
}
void position_valid(Vec3 p){if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.z)||std::max({std::abs(p.x),std::abs(p.y),std::abs(p.z)})>1e6)throw std::invalid_argument("Skin source position outside finite +/-1e6 metres");}
void settings_valid(const Settings&s){if(s.max_bones<1||s.max_bones>128||s.max_vertices<1||s.max_vertices>65536||s.max_influences<1||s.max_influences>262144||!std::isfinite(s.maximum_condition)||s.maximum_condition<1||s.maximum_condition>1e12||!std::isfinite(s.maximum_inverse_residual)||s.maximum_inverse_residual<1e-15||s.maximum_inverse_residual>1e-3)throw std::invalid_argument("Invalid skinning count/quality budgets");}
Mat4 identity(){return {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};}
Mat4 multiply(const Mat4&a,const Mat4&b){Mat4 out{};for(unsigned c=0;c<4;++c)for(unsigned r=0;r<4;++r)for(unsigned k=0;k<4;++k){const double term=a[k*4+r]*b[c*4+k];finite_result(term);out[c*4+r]+=term;finite_result(out[c*4+r]);}return out;}
double linear_norm(const Mat4&m){double out=0;for(unsigned r=0;r<3;++r){double row=0;for(unsigned c=0;c<3;++c)row+=std::abs(m[c*4+r]);finite_result(row);out=std::max(out,row);}return out;}
double inverse_residual(const Mat4&a,const Mat4&b){
    double out=0;
    for(const auto& product:{multiply(a,b),multiply(b,a)})for(unsigned r=0;r<4;++r){double row=0;for(unsigned c=0;c<4;++c)row+=std::abs(product[c*4+r]-(r==c?1:0));finite_result(row);out=std::max(out,row);}return out;
}
void quality(const Mat4&rest,const Mat4&inverse,const Settings&s,InverseDiagnostic&d){
    const double condition=linear_norm(rest)*linear_norm(inverse);finite_result(condition);d.linear_condition=condition;
    const double residual=inverse_residual(rest,inverse);d.inverse_residual=residual;
    if(condition>s.maximum_condition||residual>s.maximum_inverse_residual)throw IllConditioned{};
}
Mat4 invert(const Mat4&m,InverseDiagnostic&diagnostic){
    double scale=0;for(unsigned c=0;c<3;++c)for(unsigned r=0;r<3;++r)scale=std::max(scale,std::abs(m[c*4+r]));
    if(scale==0){diagnostic.pivot_failure=true;throw IllConditioned{};}
    std::array<std::array<double,6>,3> a{};std::array<double,3> row_scale{};
    for(unsigned r=0;r<3;++r){for(unsigned c=0;c<3;++c){a[r][c]=m[c*4+r]/scale;row_scale[r]=std::max(row_scale[r],std::abs(a[r][c]));}a[r][r+3]=1;
        if(row_scale[r]==0){diagnostic.pivot_failure=true;throw IllConditioned{};}}
    for(unsigned c=0;c<3;++c){unsigned pivot=c;double best=-1;
        for(unsigned r=c;r<3;++r){const double score=std::abs(a[r][c])/row_scale[r];if(score>best){best=score;pivot=r;}}
        if(best<=64*std::numeric_limits<double>::epsilon()||a[pivot][c]==0){diagnostic.pivot_failure=true;throw IllConditioned{};}
        if(pivot!=c){std::swap(a[pivot],a[c]);std::swap(row_scale[pivot],row_scale[c]);}
        const double p=a[c][c];for(unsigned k=0;k<6;++k){a[c][k]/=p;finite_result(a[c][k]);}
        for(unsigned r=0;r<3;++r)if(r!=c){const double factor=a[r][c];for(unsigned k=0;k<6;++k){const double term=factor*a[c][k];finite_result(term);a[r][k]-=term;finite_result(a[r][k]);}}
    }
    Mat4 inverse=identity();for(unsigned r=0;r<3;++r)for(unsigned c=0;c<3;++c){inverse[c*4+r]=a[r][c+3]/scale;finite_result(inverse[c*4+r]);}
    for(unsigned r=0;r<3;++r){double value=0;for(unsigned c=0;c<3;++c){const double term=inverse[c*4+r]*m[12+c];finite_result(term);value-=term;finite_result(value);}inverse[12+r]=value;}
    for(double value:inverse)if(!std::isfinite(value)||std::abs(value)>matrix_limit)throw std::domain_error("Constructed inverse bind exceeds supported matrix domain");
    return inverse;
}
using IdMap=std::map<std::uint64_t,std::size_t>;
IdMap rest_valid(std::span<const BoneMatrix>rest){
    if(rest.empty())throw std::invalid_argument("Skin binding requires nonempty bone matrices");
    IdMap map;for(std::size_t j=0;j<rest.size();++j){valid_id(rest[j].bone_id);matrix_valid(rest[j].matrix);if(!map.emplace(rest[j].bone_id,j).second)throw std::invalid_argument("Duplicate skin bone ID");}return map;
}
struct Weight {std::uint64_t id{};std::size_t joint{};double weight{};};
struct WorkingVertex {Vec3 position{};std::array<Weight,4> weights;unsigned count{};};
std::vector<WorkingVertex> vertex_valid(std::span<const Vertex>vertices,const IdMap&joints){
    std::vector<WorkingVertex> working;working.reserve(vertices.size());
    for(const auto&v:vertices){position_valid(v.position);if(v.influences.empty()||v.influences.size()>4)throw std::invalid_argument("Skin vertex requires 1..4 influences");
        WorkingVertex w;w.position=v.position;w.count=unsigned(v.influences.size());double maximum=0;
        for(unsigned j=0;j<w.count;++j){const auto&i=v.influences[j];valid_id(i.bone_id);const auto found=joints.find(i.bone_id);if(found==joints.end())throw std::invalid_argument("Skin influence targets unknown bone ID");
            if(!std::isfinite(i.weight)||i.weight<0)throw std::invalid_argument("Skin author weights must be finite nonnegative");maximum=std::max(maximum,i.weight);w.weights[j]={i.bone_id,found->second,i.weight};}
        if(maximum==0)throw std::invalid_argument("Skin vertex author weights are all zero");
        // Only 1..4 entries are populated. Bound every insertion by the physical
        // array extent, avoiding generic introsort's larger-range code paths.
        for(unsigned i=1;i<4;++i){
            if(i>=w.count)break;
            const Weight value=w.weights[i];unsigned slot=i;
            while(slot>0&&value.id<w.weights[slot-1].id){w.weights[slot]=w.weights[slot-1];--slot;}
            w.weights[slot]=value;
        }
        for(unsigned j=1;j<w.count;++j)if(w.weights[j-1].id==w.weights[j].id)throw std::invalid_argument("Duplicate bone influence on skin vertex");
        working.push_back(w);
    }return working;
}
void normalize(WorkingVertex&v,DeformResult&out){
    double maximum=0;for(unsigned j=0;j<v.count;++j)maximum=std::max(maximum,v.weights[j].weight);
    double sum=0;for(unsigned j=0;j<v.count;++j){const double author=v.weights[j].weight,ratio=author/maximum;if(author>0&&ratio==0)throw std::domain_error("Positive skin weight underflows during max scaling");v.weights[j].weight=ratio;sum+=ratio;finite_result(sum);}
    if(!(sum>0))throw std::domain_error("Skin normalized weight denominator failed");
    double normalized_sum=0;for(unsigned j=0;j<v.count;++j){const double ratio=v.weights[j].weight,value=ratio/sum;if(ratio>0&&value==0)throw std::domain_error("Positive skin weight underflows during normalization");v.weights[j].weight=value;normalized_sum+=value;finite_result(normalized_sum);}
    const double residual=std::abs(normalized_sum-1);out.weight_residuals.push_back(residual);
    if(residual>32*std::numeric_limits<double>::epsilon())throw std::domain_error("Skin normalized weight sum residual exceeds acceptance");
}
Vec3 transform(const Mat4&m,Vec3 p){
    std::array<double,3> out{};const std::array<double,4> v{p.x,p.y,p.z,1};
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c){const double term=m[c*4+r]*v[c];finite_result(term);out[r]+=term;finite_result(out[r]);}return {out[0],out[1],out[2]};
}
}

BindResult bind(std::span<const BoneMatrix>rest,const Settings&settings){
    BindResult out;bool checked=false;
    try{
        settings_valid(settings);if(rest.size()>settings.max_bones){out.status=Status::budget_exceeded;out.message="Skin rest bone count exceeds budget";return out;}
        rest_valid(rest);checked=true;std::vector<JointBind> candidate;candidate.reserve(rest.size());out.diagnostics.reserve(rest.size());
        for(const auto&bone:rest){out.diagnostics.push_back({bone.bone_id,{},{},false});auto&d=out.diagnostics.back();const auto inverse=invert(bone.matrix,d);quality(bone.matrix,inverse,settings,d);candidate.push_back({bone.bone_id,bone.matrix,inverse});}
        out.joints=std::move(candidate);out.status=Status::completed;return out;
    }catch(const IllConditioned&){out.status=Status::ill_conditioned;out.message="Singular/scaled-pivot or inverse condition/residual acceptance failed";}
    catch(const std::invalid_argument&e){out.status=checked?Status::numerical_failure:Status::invalid_input;out.message=e.what();}
    catch(const std::exception&e){out.status=Status::numerical_failure;out.message=e.what();}
    out.joints.reset();return out;
}

DeformResult deform(std::span<const Vertex>vertices,std::span<const JointBind>joints,std::span<const BoneMatrix>pose,const Settings&settings){
    DeformResult out;bool checked=false;
    try{
        settings_valid(settings);if(joints.size()>settings.max_bones||pose.size()>settings.max_bones||vertices.size()>settings.max_vertices){out.status=Status::budget_exceeded;out.message="Skin bone/vertex count exceeds budget";return out;}
        std::size_t influences=0;for(const auto&v:vertices){if(v.influences.size()>settings.max_influences-influences){out.status=Status::budget_exceeded;out.message="Skin total influence count exceeds budget";return out;}influences+=v.influences.size();}
        if(joints.empty())throw std::invalid_argument("Skin binding is empty");
        IdMap ids;for(std::size_t j=0;j<joints.size();++j){const auto&b=joints[j];valid_id(b.bone_id);matrix_valid(b.rest_world);matrix_valid(b.inverse_bind);if(!ids.emplace(b.bone_id,j).second)throw std::invalid_argument("Duplicate inverse-bind bone ID");}
        const auto poses=rest_valid(pose);if(poses.size()!=ids.size())throw std::invalid_argument("Skin pose and inverse-bind ID sets differ");
        for(const auto&[id,index]:ids){(void)index;if(!poses.contains(id))throw std::invalid_argument("Skin pose is missing a bound bone ID");}
        auto working=vertex_valid(vertices,ids);checked=true;out.inverse_diagnostics.reserve(joints.size());out.weight_residuals.reserve(vertices.size());
        for(const auto&b:joints){out.inverse_diagnostics.push_back({b.bone_id,{},{},false});quality(b.rest_world,b.inverse_bind,settings,out.inverse_diagnostics.back());}
        for(auto&v:working)normalize(v,out);
        std::vector<Mat4> palette;palette.reserve(joints.size());for(const auto&b:joints)palette.push_back(multiply(pose[poses.at(b.bone_id)].matrix,b.inverse_bind));
        std::vector<Vec3> candidate;candidate.reserve(vertices.size());
        for(const auto&v:working){Mat4 blended=identity();for(unsigned c=0;c<4;++c)for(unsigned r=0;r<3;++r){double value=0;for(unsigned j=0;j<v.count;++j){const auto&w=v.weights[j];const double term=w.weight*palette[w.joint][c*4+r];finite_result(term);value+=term;finite_result(value);}blended[c*4+r]=value;}
            candidate.push_back(transform(blended,v.position));}
        out.positions=std::move(candidate);out.status=Status::completed;return out;
    }catch(const IllConditioned&){out.status=Status::ill_conditioned;out.message="Explicit inverse-bind condition/residual acceptance failed";}
    catch(const std::invalid_argument&e){out.status=checked?Status::numerical_failure:Status::invalid_input;out.message=e.what();}
    catch(const std::exception&e){out.status=Status::numerical_failure;out.message=e.what();}
    out.positions.reset();return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
