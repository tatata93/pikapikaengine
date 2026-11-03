#include "pikapika/skinning.hpp"
#include "pikapika/motion.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace sk=pikapika::skinning;
namespace mo=pikapika::motion;
using pikapika::Vec3;
using M=sk::Mat4;
M identity(){return {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};}
M affine(double x=1,double y=1,double z=1,Vec3 t={}){auto m=identity();m[0]=x;m[5]=y;m[10]=z;m[12]=t.x;m[13]=t.y;m[14]=t.z;return m;}
void require(bool b,const std::string&s){if(!b)throw std::runtime_error(s);}
void near(double a,double b,double scale=1){require(std::abs(a-b)<=256*std::numeric_limits<double>::epsilon()*std::max({scale,std::abs(a),std::abs(b)}),"Numerical reference mismatch");}
void point(Vec3 a,Vec3 b){near(a.x,b.x);near(a.y,b.y);near(a.z,b.z);}
struct OwnedVertex {Vec3 position;std::vector<sk::Influence> influences;};
struct Case {
    std::string name;bool is_bind{};std::vector<sk::BoneMatrix> rest,pose;
    std::vector<sk::JointBind> joints;std::vector<OwnedVertex> vertices;
    sk::Settings settings;sk::Status expected=sk::Status::completed;
    std::optional<std::vector<Vec3>> expected_positions;
};
std::vector<sk::Vertex> views(const Case&c){std::vector<sk::Vertex> out;for(const auto&v:c.vertices)out.push_back({v.position,v.influences});return out;}
Case basic(std::string name){Case c;c.name=std::move(name);c.rest={{7,identity()}};c.pose=c.rest;c.joints={{7,identity(),identity()}};c.vertices={{{1,2,3},{{7,1}}}};c.expected_positions=std::vector<Vec3>{{1,2,3}};return c;}
Case bound(std::string name,M m){auto c=basic(std::move(name));c.is_bind=true;c.rest={{7,m}};c.pose.clear();c.joints.clear();c.vertices.clear();c.expected_positions.reset();return c;}
void second(Case&c){c.rest.push_back({19,identity()});c.pose.push_back({19,affine(1,1,1,{4,0,0})});c.joints.push_back({19,identity(),identity()});c.vertices[0].influences={{7,1},{19,3}};c.expected_positions=std::vector<Vec3>{{4,2,3}};}
std::vector<Case> cases(){std::vector<Case> out;auto add=[&](Case c){out.push_back(std::move(c));};
    add(bound("bind-identity",identity()));
    auto m=affine(2,4,.5,{1,-2,3});m[4]=.5;m[9]=.25;add(bound("bind-affine-shear",m));
    add(bound("bind-tiny-uniform",affine(1e-150,1e-150,1e-150)));
    add(bound("bind-huge-uniform",affine(1e150,1e150,1e150)));
    auto c=bound("bind-inverse-translation-domain",affine(1e-150,1e-150,1e-150,{1e150,0,0}));c.expected=sk::Status::numerical_failure;add(c);
    c=bound("bind-singular",affine(1,0,1));c.expected=sk::Status::ill_conditioned;add(c);
    c=bound("bind-condition-failure",affine(1,1,1e-11));c.expected=sk::Status::ill_conditioned;add(c);
    c=bound("bind-condition-boundary",affine(1,1,1e-10));add(c);
    c=bound("bind-condition-setting-one",identity());c.settings.maximum_condition=1;add(c);
    c=bound("bind-condition-setting-max",identity());c.settings.maximum_condition=1e12;add(c);
    c=bound("bind-residual-setting-min",identity());c.settings.maximum_inverse_residual=1e-15;add(c);
    c=bound("bind-residual-setting-max",identity());c.settings.maximum_inverse_residual=1e-3;add(c);
    c=bound("bind-empty",identity());c.rest.clear();c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-zero-id",identity());c.rest[0].bone_id=0;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-unsafe-id",identity());c.rest[0].bone_id=9007199254740992ULL;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-largest-id",identity());c.rest[0].bone_id=9007199254740991ULL;add(c);
    c=bound("bind-duplicate-id",identity());c.rest.push_back(c.rest[0]);c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-nonaffine",identity());c.rest[0].matrix[3]=1e-30;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-matrix-domain",identity());c.rest[0].matrix[12]=1e151;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-budget",identity());c.rest.push_back({19,identity()});c.settings.max_bones=1;c.expected=sk::Status::budget_exceeded;add(c);
    c=bound("bind-invalid-budget",identity());c.settings.max_bones=0;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-invalid-condition",identity());c.settings.maximum_condition=.5;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-invalid-residual",identity());c.settings.maximum_inverse_residual=1e-16;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-invalid-vertex-budget",identity());c.settings.max_vertices=65537;c.expected=sk::Status::invalid_input;add(c);
    c=bound("bind-invalid-influence-budget",identity());c.settings.max_influences=262145;c.expected=sk::Status::invalid_input;add(c);
    add(basic("deform-identity"));
    c=basic("deform-translation");c.pose[0].matrix=affine(1,1,1,{4,-1,2});c.expected_positions=std::vector<Vec3>{{5,1,5}};add(c);
    c=basic("deform-two-weighted");second(c);add(c);
    c=basic("deform-pose-order");second(c);std::reverse(c.pose.begin(),c.pose.end());add(c);
    c=basic("deform-influence-order");second(c);std::reverse(c.vertices[0].influences.begin(),c.vertices[0].influences.end());add(c);
    c=basic("deform-weight-scaled");second(c);for(auto&i:c.vertices[0].influences)i.weight*=1e200;add(c);
    c=basic("deform-max-weights");second(c);for(auto&i:c.vertices[0].influences)i.weight=std::numeric_limits<double>::max();c.expected_positions=std::vector<Vec3>{{3,2,3}};add(c);
    c=basic("deform-subnormal-single-weight");c.vertices[0].influences[0].weight=std::numeric_limits<double>::denorm_min();add(c);
    c=basic("deform-scaling-underflow");second(c);c.vertices[0].influences[0].weight=std::numeric_limits<double>::denorm_min();c.vertices[0].influences[1].weight=std::numeric_limits<double>::max();c.expected=sk::Status::numerical_failure;add(c);
    c=basic("deform-normalizing-underflow");second(c);c.vertices[0].influences={{7,std::numeric_limits<double>::denorm_min()},{19,1}};c.joints.push_back({29,identity(),identity()});c.pose.push_back({29,identity()});c.vertices[0].influences.push_back({29,1});c.expected=sk::Status::numerical_failure;add(c);
    c=basic("deform-zero-weight-known");second(c);c.vertices[0].influences[1].weight=0;c.expected_positions=std::vector<Vec3>{{1,2,3}};add(c);
    c=basic("deform-all-zero");c.vertices[0].influences[0].weight=0;c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-negative-weight");c.vertices[0].influences[0].weight=-1;c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-unknown-zero-weight");c.vertices[0].influences.push_back({19,0});c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-duplicate-weight");c.vertices[0].influences.push_back({7,0});c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-no-influences");c.vertices[0].influences.clear();c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-too-many-influences");for(unsigned j=0;j<4;++j)c.vertices[0].influences.push_back({19+j,1});c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-four-influences");for(unsigned j=1;j<4;++j){c.joints.push_back({7+j,identity(),identity()});c.pose.push_back({7+j,affine(1,1,1,{double(j),0,0})});c.vertices[0].influences.push_back({7+j,1});}c.expected_positions=std::vector<Vec3>{{2.5,2,3}};add(c);
    c=basic("deform-nonuniform-shear");c.pose[0].matrix=affine(2,3,.5);c.pose[0].matrix[4]=.5;c.pose[0].matrix[9]=.25;c.expected_positions=std::vector<Vec3>{{3,6.75,1.5}};add(c);
    c=basic("deform-explicit-inverse");c.joints[0]={7,affine(2,4,.5,{1,-2,3}),affine(.5,.25,2,{-.5,.5,-6})};c.pose[0].matrix=c.joints[0].rest_world;add(c);
    c=basic("deform-invalid-inverse-residual");c.joints[0].inverse_bind[12]=1e-4;c.expected=sk::Status::ill_conditioned;add(c);
    c=basic("deform-residual-exact-boundary");c.settings.maximum_inverse_residual=1e-3;c.joints[0].inverse_bind[12]=1e-3;c.expected_positions=std::vector<Vec3>{{1.001,2,3}};add(c);
    c=basic("deform-residual-above-boundary");c.settings.maximum_inverse_residual=1e-3;c.joints[0].inverse_bind[12]=std::nextafter(1e-3,1.0);c.expected=sk::Status::ill_conditioned;add(c);
    c=basic("deform-inverse-nonaffine");c.joints[0].inverse_bind[15]=.9;c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-missing-pose");c.pose.clear();c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-extra-pose");c.pose.push_back({19,identity()});c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-duplicate-pose");c.pose.push_back(c.pose[0]);c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-duplicate-bind");c.joints.push_back(c.joints[0]);c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-source-domain");c.vertices[0].position.x=1e6+1;c.expected=sk::Status::invalid_input;add(c);
    c=basic("deform-output-outside-mesh-domain");c.pose[0].matrix[12]=1e100;c.expected_positions=std::vector<Vec3>{{1e100,2,3}};add(c);
    c=basic("deform-singular-pose-allowed");c.pose[0].matrix=affine(0,1,-1);c.expected_positions=std::vector<Vec3>{{0,2,-3}};add(c);
    c=basic("deform-empty-vertices");c.vertices.clear();c.expected_positions=std::vector<Vec3>{};add(c);
    c=basic("deform-vertex-budget");c.vertices.push_back(c.vertices[0]);c.settings.max_vertices=1;c.expected=sk::Status::budget_exceeded;add(c);
    c=basic("deform-influence-budget");second(c);c.settings.max_influences=1;c.expected=sk::Status::budget_exceeded;add(c);
    c=basic("deform-palette-domain-finite");c.joints[0]={7,affine(1e-150,1e-150,1e-150),affine(1e150,1e150,1e150)};c.pose[0].matrix=affine(1e150,1e150,1e150);c.expected_positions=std::vector<Vec3>{{1e300,2e300,3e300}};add(c);
    c=basic("deform-large-finite-product");c.joints[0]={7,affine(1e-150,1e-150,1e-150),affine(1e150,1e150,1e150)};c.pose[0].matrix=affine(1e150,1e150,1e150);c.vertices[0].position={1e6,1e6,1e6};c.expected_positions=std::vector<Vec3>{{1e306,1e306,1e306}};add(c);
    c=basic("deform-bind-order");second(c);std::reverse(c.joints.begin(),c.joints.end());add(c);
    c=basic("deform-shear-rest-identity");m=affine(2,4,.5,{1,-2,3});m[4]=.5;m[9]=.25;c.joints=*sk::bind(std::array<sk::BoneMatrix,1>{{{7,m}}}).joints;c.pose[0].matrix=m;add(c);
    c=bound("bind-dependent-pivot",identity());c.rest[0].matrix[4]=1;c.rest[0].matrix[1]=1;c.rest[0].matrix[5]=std::nextafter(1.0,2.0);c.expected=sk::Status::ill_conditioned;add(c);
    c=basic("deform-cancellation-limit");second(c);c.vertices[0].position={1,0,0};c.vertices[0].influences={{7,1},{19,1}};c.pose[0].matrix[12]=9007199254740992.0;c.pose[1].matrix[12]=-9007199254740992.0;c.expected_positions=std::vector<Vec3>{{1,0,0}};add(c);
    return out;
}
void number(double x){if(!std::isfinite(x))throw std::runtime_error("Nonfinite JSON result");std::cout<<std::setprecision(17)<<x;}
template<class A>void numbers(const A&a){std::cout<<'[';bool first=true;for(double x:a){if(!first)std::cout<<',';first=false;number(x);}std::cout<<']';}
void vec(Vec3 v){numbers(std::array<double,3>{v.x,v.y,v.z});}
void matrices(const std::vector<sk::BoneMatrix>&v){std::cout<<'[';for(std::size_t j=0;j<v.size();++j){if(j)std::cout<<',';std::cout<<"{\"id\":"<<v[j].bone_id<<",\"matrix\":";numbers(v[j].matrix);std::cout<<'}';}std::cout<<']';}
void joints(const std::vector<sk::JointBind>&v){std::cout<<'[';for(std::size_t j=0;j<v.size();++j){if(j)std::cout<<',';const auto&b=v[j];std::cout<<"{\"id\":"<<b.bone_id<<",\"restWorld\":";numbers(b.rest_world);std::cout<<",\"inverseBind\":";numbers(b.inverse_bind);std::cout<<'}';}std::cout<<']';}
void diagnostics(const std::vector<sk::InverseDiagnostic>&v){std::cout<<'[';for(std::size_t j=0;j<v.size();++j){if(j)std::cout<<',';const auto&d=v[j];std::cout<<"{\"id\":"<<d.bone_id<<",\"condition\":";if(d.linear_condition)number(*d.linear_condition);else std::cout<<"null";std::cout<<",\"residual\":";if(d.inverse_residual)number(*d.inverse_residual);else std::cout<<"null";std::cout<<",\"pivotFailure\":"<<(d.pivot_failure?"true":"false")<<'}';}std::cout<<']';}
void fixtures(){std::cout<<"{\"schema\":1,\"fixtures\":[";bool first=true;for(const auto&c:cases()){if(!first)std::cout<<',';first=false;std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"operation\":\""<<(c.is_bind?"bind":"deform")<<"\",\"rest\":";matrices(c.rest);std::cout<<",\"joints\":";joints(c.joints);std::cout<<",\"pose\":";matrices(c.pose);std::cout<<",\"vertices\":[";
        for(std::size_t j=0;j<c.vertices.size();++j){if(j)std::cout<<',';const auto&v=c.vertices[j];std::cout<<"{\"position\":";vec(v.position);std::cout<<",\"influences\":[";for(std::size_t k=0;k<v.influences.size();++k){if(k)std::cout<<',';std::cout<<"{\"id\":"<<v.influences[k].bone_id<<",\"weight\":";number(v.influences[k].weight);std::cout<<'}';}std::cout<<"]}";}std::cout<<"],\"settings\":["<<c.settings.max_bones<<','<<c.settings.max_vertices<<','<<c.settings.max_influences<<',';number(c.settings.maximum_condition);std::cout<<',';number(c.settings.maximum_inverse_residual);std::cout<<"]},\"result\":{";
        if(c.is_bind){const auto r=sk::bind(c.rest,c.settings);std::cout<<"\"status\":"<<int(r.status)<<",\"joints\":";if(r.joints)joints(*r.joints);else std::cout<<"null";std::cout<<",\"positions\":null,\"diagnostics\":";diagnostics(r.diagnostics);std::cout<<",\"weightResiduals\":[]";}
        else{const auto v=views(c);const auto r=sk::deform(v,c.joints,c.pose,c.settings);std::cout<<"\"status\":"<<int(r.status)<<",\"joints\":null,\"positions\":";if(r.positions){std::cout<<'[';for(std::size_t j=0;j<r.positions->size();++j){if(j)std::cout<<',';vec((*r.positions)[j]);}std::cout<<']';}else std::cout<<"null";std::cout<<",\"diagnostics\":";diagnostics(r.inverse_diagnostics);std::cout<<",\"weightResiduals\":";numbers(r.weight_residuals);}std::cout<<"}}";
    }std::cout<<"]}\n";}
void hex(double x){std::cout<<std::hexfloat<<x<<std::defaultfloat;}
void oracle(){std::cout<<"id";for(const auto prefix:{"r0","r1","g0","g1"})for(unsigned j=0;j<16;++j)std::cout<<','<<prefix<<'_'<<j;std::cout<<",px,py,pz,w0,w1";for(const auto prefix:{"i0","i1"})for(unsigned j=0;j<16;++j)std::cout<<','<<prefix<<'_'<<j;std::cout<<",x,y,z\n";
    for(unsigned j=0;j<128;++j){auto r0=affine(2,1,.5,{1,-2,3});r0[4]=.5;r0[9]=.25;auto r1=affine(1,2,1,{-3,1,2});r1[8]=.5;auto g0=affine(1,2,.5,{double(j)/64,2,-1});g0[4]=.25;auto g1=identity();g1[0]=0;g1[1]=2;g1[4]=-1;g1[5]=0;g1[12]=-double(j)/32;g1[13]=1;g1[14]=.5;
        const std::array<sk::BoneMatrix,2> rest{{{7,r0},{19,r1}}},pose{{{19,g1},{7,g0}}};const auto b=sk::bind(rest);require(b.status==sk::Status::completed,"Oracle bind");const Vec3 p{double(int(j%17)-8)/8,double(int(j%13)-6)/4,double(int(j%11)-5)/8};const double w0=1+j%7,w1=1+j%11;const std::array<sk::Influence,2> w{{{19,w1},{7,w0}}};const std::array<sk::Vertex,1> v{{{p,w}}};const auto d=sk::deform(v,*b.joints,pose);require(d.status==sk::Status::completed,"Oracle deform");std::cout<<j;
        for(const auto&m:{r0,r1,g0,g1})for(double x:m){std::cout<<',';hex(x);}for(double x:{p.x,p.y,p.z,w0,w1}){std::cout<<',';hex(x);}for(const auto&joint:*b.joints)for(double x:joint.inverse_bind){std::cout<<',';hex(x);}const auto q=d.positions->front();for(double x:{q.x,q.y,q.z}){std::cout<<',';hex(x);}std::cout<<'\n';}
}
int main(int argc,char**argv){try{if(argc==2&&std::string(argv[1])=="--fixtures"){fixtures();return 0;}if(argc==2&&std::string(argv[1])=="--oracle"){oracle();return 0;}require(argc==1,"Unknown command");unsigned count=0;
    for(const auto&c:cases()){if(c.is_bind){const auto r=sk::bind(c.rest,c.settings);require(r.status==c.expected,c.name+": bind status "+std::to_string(int(r.status)));require(bool(r.joints)==(r.status==sk::Status::completed),c.name+": atomic joints");}
        else{const auto v=views(c);const auto r=sk::deform(v,c.joints,c.pose,c.settings);require(r.status==c.expected,c.name+": deform status "+std::to_string(int(r.status)));require(bool(r.positions)==(r.status==sk::Status::completed),c.name+": atomic positions");if(r.positions&&c.expected_positions){require(r.positions->size()==c.expected_positions->size(),"Position size");for(std::size_t j=0;j<r.positions->size();++j)point((*r.positions)[j],(*c.expected_positions)[j]);}}++count;}
    // Inputs remain author values; failed calls have no retained state.
    auto c=basic("pure");second(c);const auto v=views(c);const auto source=c.vertices[0].influences;auto r=sk::deform(v,c.joints,c.pose);require(r.status==sk::Status::completed,"Pure call");for(std::size_t j=0;j<source.size();++j)require(source[j].bone_id==c.vertices[0].influences[j].bone_id&&source[j].weight==c.vertices[0].influences[j].weight,"Author mutation");c.settings.maximum_condition=0;require(sk::deform(v,c.joints,c.pose,c.settings).status==sk::Status::invalid_input,"Failure call");require(sk::deform(v,c.joints,c.pose).status==sk::Status::completed,"Reuse");++count;
    // Preflight NaN/infinity, represented directly rather than invalid JSON.
    for(double bad:{std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()}){c=basic("nonfinite");c.pose[0].matrix[0]=bad;require(sk::deform(views(c),c.joints,c.pose).status==sk::Status::invalid_input,"Nonfinite matrix");c=basic("nonfinite");c.vertices[0].influences[0].weight=bad;require(sk::deform(views(c),c.joints,c.pose).status==sk::Status::invalid_input,"Nonfinite weight");c=basic("nonfinite");c.vertices[0].position.x=bad;require(sk::deform(views(c),c.joints,c.pose).status==sk::Status::invalid_input,"Nonfinite vertex");}++count;
    // Actual motion pose: nonuniform parent scale and child rotation retain shear.
    std::array<mo::Bone,2> bones{{{19,7,{{1,0,0},{0,0,0,1},{1,1,1}}},{7,0,{{},{0,0,0,1},{2,1,1}}}}};std::array<mo::Key,1> keys{{{0,{{1,0,0},{0,0,1,1},{1,1,1}}}}};std::array<mo::Track,1> tracks{{{19,mo::Interpolation::linear,keys}}};const mo::Input input{bones,{1,tracks}};const auto pose=mo::sample(input,0,mo::Playback::clamp);require(pose.pose.has_value(),"Motion pose");std::array<mo::Track,0> no_tracks{};const auto rest=mo::sample({bones,{1,no_tracks}},0,mo::Playback::clamp);require(rest.pose.has_value(),"Motion rest");std::vector<sk::BoneMatrix> rm,gm;for(const auto&b:rest.pose->bones)rm.push_back({b.id,b.world_matrix});for(const auto&b:pose.pose->bones)gm.push_back({b.id,b.world_matrix});const auto binding=sk::bind(rm);require(binding.joints.has_value(),"Motion binding");const std::array<sk::Influence,1> w{{{19,1}}};const std::array<sk::Vertex,1> vertex{{{{4,0,0},w}}};const auto deformed=sk::deform(vertex,*binding.joints,gm);require(deformed.positions.has_value(),"Motion deform");point(deformed.positions->front(),{2,1,0});++count;
    std::cout<<"PASS "<<count<<" skinning test groups\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
