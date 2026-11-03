#include "pikapika/motion.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <stdexcept>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Motion reference requires strict floating point without contraction.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::motion {
namespace {
constexpr std::uint64_t maximum_id=9007199254740991ULL;
void valid_id(std::uint64_t id,bool parent=false){if(id>maximum_id||(!parent&&id==0))throw std::invalid_argument("Motion ID outside exact numeric domain");}
bool finite(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);}
Quaternion normalized(Quaternion q){
    if(!std::isfinite(q.x)||!std::isfinite(q.y)||!std::isfinite(q.z)||!std::isfinite(q.w))throw std::invalid_argument("Motion quaternion requires finite components");
    const double m=std::max({std::abs(q.x),std::abs(q.y),std::abs(q.z),std::abs(q.w)});
    if(m==0||m>1e300)throw std::invalid_argument("Motion quaternion max component outside (0,1e300]");
    const double x=q.x/m,y=q.y/m,z=q.z/m,w=q.w/m;
    const double n=std::sqrt(x*x+y*y+z*z+w*w);
    if(!std::isfinite(n)||n==0)throw std::domain_error("Motion quaternion normalization failed");
    return {x/n,y/n,z/n,w/n};
}
Transform prepare(const Transform&t){
    if(!finite(t.position)||std::max({std::abs(t.position.x),std::abs(t.position.y),std::abs(t.position.z)})>1e6)throw std::invalid_argument("Motion translation outside finite +/-1e6 metres");
    if(!finite(t.scale)||std::min({t.scale.x,t.scale.y,t.scale.z})<1e-6||std::max({t.scale.x,t.scale.y,t.scale.z})>1e6)throw std::invalid_argument("Motion positive scale outside [1e-6,1e6]");
    return {t.position,normalized(t.rotation),t.scale};
}
Mat4 compose(const Transform&t){
    const auto&q=t.rotation;const double xx=q.x*q.x,yy=q.y*q.y,zz=q.z*q.z,xy=q.x*q.y,xz=q.x*q.z,yz=q.y*q.z,wx=q.w*q.x,wy=q.w*q.y,wz=q.w*q.z;
    return {(1-2*(yy+zz))*t.scale.x,2*(xy+wz)*t.scale.x,2*(xz-wy)*t.scale.x,0,
            2*(xy-wz)*t.scale.y,(1-2*(xx+zz))*t.scale.y,2*(yz+wx)*t.scale.y,0,
            2*(xz+wy)*t.scale.z,2*(yz-wx)*t.scale.z,(1-2*(xx+yy))*t.scale.z,0,
            t.position.x,t.position.y,t.position.z,1};
}
Mat4 multiply(const Mat4&a,const Mat4&b){
    Mat4 out{};
    for(unsigned c=0;c<4;++c)for(unsigned r=0;r<4;++r)for(unsigned k=0;k<4;++k)out[c*4+r]+=a[k*4+r]*b[c*4+k];
    return out;
}
void world_valid(const Mat4&m){for(double v:m)if(!std::isfinite(v))throw std::domain_error("Motion world matrix overflow/nonfinite result");}
double lerp(double a,double b,double alpha){return (1-alpha)*a+alpha*b;}
Vec3 lerp(Vec3 a,Vec3 b,double alpha){return {lerp(a.x,b.x,alpha),lerp(a.y,b.y,alpha),lerp(a.z,b.z,alpha)};}
Transform interpolate(const Transform&a,const Transform&b,double alpha){
    const auto&x=a.rotation;const auto&y=b.rotation;
    const double sign=x.x*y.x+x.y*y.y+x.z*y.z+x.w*y.w<0?-1:1;
    const Quaternion mixed{lerp(x.x,sign*y.x,alpha),lerp(x.y,sign*y.y,alpha),lerp(x.z,sign*y.z,alpha),lerp(x.w,sign*y.w,alpha)};
    return {lerp(a.position,b.position,alpha),normalized(mixed),lerp(a.scale,b.scale,alpha)};
}
struct PreparedTrack {std::size_t bone{};Interpolation interpolation{};std::vector<Key> keys;};
Transform at(const PreparedTrack&t,double seconds){
    if(seconds<=t.keys.front().time)return t.keys.front().pose;
    if(seconds>=t.keys.back().time)return t.keys.back().pose;
    const auto upper=std::upper_bound(t.keys.begin(),t.keys.end(),seconds,[](double time,const Key&key){return time<key.time;});
    const auto&left=*(upper-1);
    if(left.time==seconds||t.interpolation==Interpolation::step)return left.pose;
    const double alpha=(seconds-left.time)/(upper->time-left.time);
    if(!std::isfinite(alpha)||alpha<0||alpha>1)throw std::domain_error("Motion interpolation fraction failed");
    return interpolate(left.pose,upper->pose,alpha);
}
}

Result sample(const Input&input,double seconds,Playback mode,const Settings&settings){
    Result out;bool checked=false;
    try{
        if(settings.max_bones<1||settings.max_bones>128||settings.max_tracks<1||settings.max_tracks>128||settings.max_keys<1||settings.max_keys>4096)throw std::invalid_argument("Invalid motion count budgets");
        if(!std::isfinite(seconds)||seconds<0)throw std::invalid_argument("Motion sample time must be finite nonnegative seconds");
        if(mode!=Playback::clamp&&mode!=Playback::loop)throw std::invalid_argument("Invalid motion playback mode");
        if(!std::isfinite(input.clip.duration)||input.clip.duration<=0||input.clip.duration>1e9)throw std::invalid_argument("Motion clip duration outside (0,1e9] seconds");
        if(input.bones.empty())throw std::invalid_argument("Motion requires a nonempty single-root tree");
        if(input.bones.size()>settings.max_bones||input.clip.tracks.size()>settings.max_tracks){out.status=Status::budget_exceeded;out.message="Motion bone/track count exceeds admitted budget";return out;}
        std::size_t total_keys=0;
        for(const auto&t:input.clip.tracks){if(t.keys.size()>settings.max_keys-total_keys){out.status=Status::budget_exceeded;out.message="Motion total key count exceeds budget";return out;}total_keys+=t.keys.size();}
        const std::size_t n=input.bones.size();std::map<std::uint64_t,std::size_t> indices;
        std::vector<Transform> local;local.reserve(n);unsigned roots=0;
        for(std::size_t j=0;j<n;++j){const auto&b=input.bones[j];valid_id(b.id);valid_id(b.parent_id,true);if(!indices.emplace(b.id,j).second)throw std::invalid_argument("Duplicate motion bone ID");if(b.parent_id==0)++roots;local.push_back(prepare(b.rest));}
        if(roots!=1)throw std::invalid_argument("Motion requires exactly one root");
        std::vector<std::size_t> parents(n,n);
        for(std::size_t j=0;j<n;++j)if(input.bones[j].parent_id){const auto i=indices.find(input.bones[j].parent_id);if(i==indices.end())throw std::invalid_argument("Missing motion parent ID");parents[j]=i->second;}
        // Bounded deterministic topological traversal. Lowest ready stable ID
        // breaks ties; neither computation nor diagnostics depend on map order.
        std::vector<std::size_t> order;order.reserve(n);std::vector<bool> done(n,false);
        while(order.size()<n){std::size_t next=n;
            for(std::size_t j=0;j<n;++j)if(!done[j]&&(parents[j]==n||done[parents[j]])&&(next==n||input.bones[j].id<input.bones[next].id))next=j;
            if(next==n)throw std::invalid_argument("Cyclic motion bone parent graph");done[next]=true;order.push_back(next);
        }
        std::vector<bool> tracked(n,false);std::vector<PreparedTrack> tracks;tracks.reserve(input.clip.tracks.size());
        for(const auto&t:input.clip.tracks){
            valid_id(t.bone_id);const auto i=indices.find(t.bone_id);if(i==indices.end())throw std::invalid_argument("Motion track targets unknown bone");
            if(tracked[i->second])throw std::invalid_argument("Duplicate motion track target");tracked[i->second]=true;
            if(t.interpolation!=Interpolation::linear&&t.interpolation!=Interpolation::step)throw std::invalid_argument("Invalid motion interpolation mode");
            if(t.keys.empty())throw std::invalid_argument("Motion track must have at least one key");
            PreparedTrack prepared{i->second,t.interpolation,{}};prepared.keys.reserve(t.keys.size());double previous=-1;
            for(const auto&key:t.keys){if(!std::isfinite(key.time)||key.time<0||key.time>input.clip.duration||key.time<=previous)throw std::invalid_argument("Motion key times must strictly increase within clip duration");previous=key.time;prepared.keys.push_back({key.time,prepare(key.pose)});}
            tracks.push_back(std::move(prepared));
        }
        checked=true;
        const double time=mode==Playback::clamp?std::min(seconds,input.clip.duration):std::fmod(seconds,input.clip.duration);
        if(!std::isfinite(time)||time<0||time>input.clip.duration||(mode==Playback::loop&&time>=input.clip.duration))throw std::domain_error("Motion loop/clamp time computation failed");
        for(const auto&t:tracks)local[t.bone]=at(t,time);
        Pose candidate;candidate.requested_time=seconds;candidate.sampled_time=time;candidate.bones.resize(n);candidate.evaluation_order.reserve(n);
        for(const auto j:order){auto&bone=candidate.bones[j];bone.id=input.bones[j].id;bone.parent_id=input.bones[j].parent_id;bone.local=local[j];bone.local_matrix=compose(local[j]);world_valid(bone.local_matrix);
            bone.world_matrix=parents[j]==n?bone.local_matrix:multiply(candidate.bones[parents[j]].world_matrix,bone.local_matrix);world_valid(bone.world_matrix);candidate.evaluation_order.push_back(bone.id);
        }
        out.pose=std::move(candidate);out.status=Status::completed;return out;
    }catch(const std::invalid_argument&e){out.status=checked?Status::numerical_failure:Status::invalid_input;out.message=e.what();}
    catch(const std::exception&e){out.status=Status::numerical_failure;out.message=e.what();}
    out.pose.reset();return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
