#include "pikapika/motion.hpp"
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
using namespace pikapika;namespace mo=motion;
namespace {
void require(bool ok,const char*message){if(!ok)throw std::runtime_error(message);}
bool near(double a,double b,double tolerance=2e-12){return std::abs(a-b)<=tolerance*std::max({1.0,std::abs(a),std::abs(b)});}
Transform trs(Vec3 position={},Quaternion rotation={},Vec3 scale={1,1,1}){return {position,rotation,scale};}
struct OwnedTrack {std::uint64_t id{};mo::Interpolation interpolation{mo::Interpolation::linear};std::vector<mo::Key> keys;};
struct Case {
    std::string name;std::vector<mo::Bone> bones{{10,0,{}}};std::vector<OwnedTrack> tracks;double duration{2},time{1};mo::Playback mode{mo::Playback::clamp};mo::Settings settings;
    mo::Result run()const{std::vector<mo::Track> views;for(const auto&t:tracks)views.push_back({t.id,t.interpolation,t.keys});return mo::sample({bones,{duration,views}},time,mode,settings);}
};
Case linear(std::string name,double time=1){Case c;c.name=name;c.time=time;c.tracks={{10,mo::Interpolation::linear,{{0,trs({}, {0,0,0,4})},{2,trs({4,2,-2},{0,0,3,4},{3,2,1})}}}};return c;}
Case chain(std::string name){Case c;c.name=name;c.bones={{30,20,trs({1,0,0})},{10,0,trs({}, {0,0,1,1})},{20,10,trs({2,0,0},{0,0,-1,1})}};return c;}
std::vector<Case> cases(){
    std::vector<Case> cs;Case c;c.name="rest";c.bones[0].rest=trs({3,4,5});cs.push_back(c);
    cs.push_back(chain("two-link"));c=chain("permuted-tree");std::reverse(c.bones.begin(),c.bones.end());cs.push_back(c);
    c=Case{};c.name="shear";c.bones={{11,10,trs({1,0,0},{0,0,1,2},{.5,3,1})},{10,0,trs({}, {},{2,1,1})}};cs.push_back(c);
    for(const auto&v:std::vector<std::pair<std::string,double>>{{"linear-start",0},{"linear-quarter",.5},{"linear-mid",1},{"linear-terminal",2},{"clamp-after",100}})cs.push_back(linear(v.first,v.second));
    c=linear("loop-duration",2);c.mode=mo::Playback::loop;cs.push_back(c);c.name="loop-multiple";c.time=6;cs.push_back(c);c.name="loop-offset";c.time=2.5;cs.push_back(c);c.name="loop-huge-clock";c.time=1e300;cs.push_back(c);
    c=linear("hold-before",0);c.tracks[0].keys[0].time=.25;c.tracks[0].keys[1].time=1.75;cs.push_back(c);c.name="hold-after";c.time=2;cs.push_back(c);c.name="exact-first-key";c.time=.25;cs.push_back(c);
    c=linear("single-key",0);c.tracks[0].keys={{1,trs({7,8,9},{1,0,0,0},{2,3,4})}};cs.push_back(c);
    c=linear("step-before",.999);c.tracks[0].interpolation=mo::Interpolation::step;c.tracks[0].keys.insert(c.tracks[0].keys.begin()+1,{1,trs({2,3,4},{0,1,0,0},{2,2,2})});cs.push_back(c);c.name="step-boundary";c.time=1;cs.push_back(c);c.name="step-after";c.time=1.5;cs.push_back(c);
    c=Case{};c.name="antipodal-mid";c.duration=1;c.time=.5;c.tracks={{10,mo::Interpolation::linear,{{0,trs({}, {0,0,1,2})},{1,trs({}, {0,0,-2,-4})}}}};cs.push_back(c);c.name="antipodal-terminal";c.time=1;cs.push_back(c);
    c=Case{};c.name="huge-quaternion";c.bones[0].rest.rotation={1e300,-1e300,1e300,-1e300};cs.push_back(c);
    c=Case{};c.name="subnormal-quaternion";const double tiny=std::numeric_limits<double>::denorm_min();c.bones[0].rest.rotation={tiny,tiny,tiny,tiny};cs.push_back(c);
    c=linear("subnormal-duration",tiny);c.duration=2*tiny;c.tracks[0].keys[1].time=c.duration;cs.push_back(c);
    c=chain("missing-track-rest");c.tracks=linear("unused").tracks;cs.push_back(c);
    c=Case{};c.name="maximum-id";c.bones[0].id=9007199254740991ULL;cs.push_back(c);
    c=Case{};c.name="duplicate-id";c.bones.push_back(c.bones[0]);cs.push_back(c);
    c=Case{};c.name="zero-id";c.bones[0].id=0;cs.push_back(c);
    c=Case{};c.name="unsafe-id";c.bones[0].id=9007199254740992ULL;cs.push_back(c);
    c=chain("missing-parent");c.bones[0].parent_id=99;cs.push_back(c);
    c=chain("multiple-roots");c.bones[0].parent_id=0;cs.push_back(c);
    c=Case{};c.name="disconnected-cycle";c.bones.push_back({20,30,{}});c.bones.push_back({30,20,{}});cs.push_back(c);
    c=chain("self-cycle");c.bones[0].parent_id=30;cs.push_back(c);
    c=linear("unknown-track");c.tracks[0].id=99;cs.push_back(c);
    c=linear("duplicate-track");c.tracks.push_back(c.tracks[0]);cs.push_back(c);
    c=linear("empty-track");c.tracks[0].keys.clear();cs.push_back(c);
    c=linear("duplicate-time");c.tracks[0].keys[1].time=0;cs.push_back(c);
    c=linear("descending-time");std::reverse(c.tracks[0].keys.begin(),c.tracks[0].keys.end());cs.push_back(c);
    c=linear("outside-time");c.tracks[0].keys[1].time=3;cs.push_back(c);
    c=linear("zero-quaternion");c.tracks[0].keys[1].pose.rotation={0,0,0,0};cs.push_back(c);
    c=Case{};c.name="negative-scale";c.bones[0].rest.scale.x=-1;cs.push_back(c);
    c=Case{};c.name="zero-scale";c.bones[0].rest.scale.x=0;cs.push_back(c);
    c=Case{};c.name="outside-position";c.bones[0].rest.position.x=1000001;cs.push_back(c);
    c=Case{};c.name="outside-quaternion";c.bones[0].rest.rotation.w=1e301;cs.push_back(c);
    c=Case{};c.name="zero-duration";c.duration=0;cs.push_back(c);
    c=Case{};c.name="negative-sample";c.time=-1;cs.push_back(c);
    c=Case{};c.name="invalid-mode";c.mode=static_cast<mo::Playback>(9);cs.push_back(c);
    c=linear("invalid-interpolation");c.tracks[0].interpolation=static_cast<mo::Interpolation>(9);cs.push_back(c);
    c=Case{};c.name="invalid-budget";c.settings.max_bones=0;cs.push_back(c);
    c=chain("bone-budget");c.settings.max_bones=2;cs.push_back(c);
    c=linear("track-budget");c.bones.push_back({20,10,{}});c.tracks.push_back({20,mo::Interpolation::step,{{0,{}}}});c.settings.max_tracks=1;cs.push_back(c);
    c=linear("key-budget");c.settings.max_keys=1;cs.push_back(c);
    c=Case{};c.name="empty-tree";c.bones.clear();cs.push_back(c);
    c=Case{};c.name="world-overflow";c.bones.clear();for(unsigned j=0;j<54;++j)c.bones.push_back({j+1,j,trs({1,0,0},{},{1e6,1e6,1e6})});cs.push_back(c);
    c=Case{};c.name="branching-order";c.bones={{40,20,trs({1,0,0})},{30,10,trs({0,3,0})},{10,0,trs({1,2,3})},{20,10,trs({2,0,0})}};cs.push_back(c);
    return cs;
}
void vec(Vec3 v){std::cout<<'['<<v.x<<','<<v.y<<','<<v.z<<']';}
void trs_json(const Transform&t){std::cout<<"{\"position\":";vec(t.position);std::cout<<",\"rotation\":["<<t.rotation.x<<','<<t.rotation.y<<','<<t.rotation.z<<','<<t.rotation.w<<"],\"scale\":";vec(t.scale);std::cout<<'}';}
void matrix(const mo::Mat4&m){std::cout<<'[';for(unsigned j=0;j<16;++j){if(j)std::cout<<',';std::cout<<m[j];}std::cout<<']';}
void json(const std::vector<Case>&cs){std::cout<<std::setprecision(17)<<"{\"schema\":1,\"fixtures\":[";
    for(unsigned j=0;j<cs.size();++j){if(j)std::cout<<',';const auto&c=cs[j];const auto r=c.run();std::cout<<"{\"name\":\""<<c.name<<"\",\"input\":{\"bones\":[";for(unsigned k=0;k<c.bones.size();++k){if(k)std::cout<<',';const auto&b=c.bones[k];std::cout<<"{\"id\":"<<b.id<<",\"parentId\":"<<b.parent_id<<",\"rest\":";trs_json(b.rest);std::cout<<'}';}std::cout<<"],\"tracks\":[";
        for(unsigned k=0;k<c.tracks.size();++k){if(k)std::cout<<',';const auto&t=c.tracks[k];std::cout<<"{\"boneId\":"<<t.id<<",\"interpolation\":"<<int(t.interpolation)<<",\"keys\":[";for(unsigned z=0;z<t.keys.size();++z){if(z)std::cout<<',';std::cout<<"{\"time\":"<<t.keys[z].time<<",\"pose\":";trs_json(t.keys[z].pose);std::cout<<'}';}std::cout<<"]}";}
        std::cout<<"],\"duration\":"<<c.duration<<",\"time\":"<<c.time<<",\"mode\":"<<int(c.mode)<<",\"settings\":["<<c.settings.max_bones<<','<<c.settings.max_tracks<<','<<c.settings.max_keys<<"]},\"result\":{\"status\":"<<int(r.status)<<",\"pose\":";
        if(r.pose){const auto&p=*r.pose;std::cout<<"{\"requestedTime\":"<<p.requested_time<<",\"sampledTime\":"<<p.sampled_time<<",\"evaluationOrder\":[";for(unsigned k=0;k<p.evaluation_order.size();++k){if(k)std::cout<<',';std::cout<<p.evaluation_order[k];}std::cout<<"],\"bones\":[";for(unsigned k=0;k<p.bones.size();++k){if(k)std::cout<<',';const auto&b=p.bones[k];std::cout<<"{\"id\":"<<b.id<<",\"parentId\":"<<b.parent_id<<",\"local\":";trs_json(b.local);std::cout<<",\"localMatrix\":";matrix(b.local_matrix);std::cout<<",\"worldMatrix\":";matrix(b.world_matrix);std::cout<<'}';}std::cout<<"]}";}else std::cout<<"null";std::cout<<"}}";
    }std::cout<<"]}\n";
}
void oracle(){std::cout<<"id,time,world0,world1,world2,world3,world4,world5,world6,world7,world8,world9,world10,world11,world12,world13,world14,world15\n"<<std::hexfloat;
    for(unsigned j=0;j<128;++j){auto c=linear("oracle",double(j)/64);c.bones.push_back({20,10,trs({1,2,0},{0,0,1,2},{2,.5,1})});const auto r=c.run();require(r.pose.has_value(),"Motion oracle failed");std::cout<<j<<','<<c.time;for(double x:r.pose->bones[1].world_matrix)std::cout<<','<<x;std::cout<<'\n';}
}
bool known_good(const std::string&n){return n=="rest"||n=="two-link"||n=="permuted-tree"||n=="shear"||n.starts_with("linear-")||n.starts_with("clamp-")||n.starts_with("loop-")||n.starts_with("hold-")||n=="exact-first-key"||n=="single-key"||n.starts_with("step-")||n.starts_with("antipodal-")||n=="huge-quaternion"||n=="subnormal-quaternion"||n=="subnormal-duration"||n=="missing-track-rest"||n=="maximum-id"||n=="branching-order";}
}
int main(int argc,char**argv){try{const auto cs=cases();if(argc==2&&std::string(argv[1])=="--fixtures"){json(cs);return 0;}if(argc==2&&std::string(argv[1])=="--oracle"){oracle();return 0;}unsigned passed=0;
    for(const auto&c:cs){const auto r=c.run();const auto expected=c.name=="world-overflow"?mo::Status::numerical_failure:c.name=="bone-budget"||c.name=="track-budget"||c.name=="key-budget"?mo::Status::budget_exceeded:known_good(c.name)?mo::Status::completed:mo::Status::invalid_input;
        if(r.status!=expected)std::cerr<<c.name<<": "<<int(r.status)<<' '<<r.message<<'\n';require(r.status==expected,"Motion classification mismatch");require(r.pose.has_value()==(expected==mo::Status::completed),"Failed motion has partial pose");
        if(r.pose){require(r.pose->bones.size()==c.bones.size(),"Bone count changed");for(unsigned j=0;j<c.bones.size();++j)require(r.pose->bones[j].id==c.bones[j].id&&r.pose->bones[j].parent_id==c.bones[j].parent_id,"Stable ID/order changed");
            if(c.name=="two-link"){const auto&m=r.pose->bones[0].world_matrix;require(near(m[12],1)&&near(m[13],2),"Two-link FK wrong");}
            if(c.name=="shear"){const auto&m=r.pose->bones[0].world_matrix;const double d=m[0]*m[4]+m[1]*m[5]+m[2]*m[6];require(near(d,-54.0/25),"Parent scale shear was lost");}
            if(c.name=="linear-mid")require(r.pose->bones[0].local.position.x==2&&r.pose->bones[0].local.scale.y==1.5,"TRS interpolation wrong");
            if(c.name=="loop-duration"||c.name=="loop-multiple")require(r.pose->sampled_time==0,"Loop endpoint did not wrap");
            if(c.name=="linear-terminal"||c.name=="clamp-after")require(r.pose->bones[0].local.rotation.z==.6&&r.pose->bones[0].local.rotation.w==.8,"Exact normalized key endpoint not selected");
        }++passed;
    }
    auto c=linear("fps");c.mode=mo::Playback::loop;for(unsigned frame=0;frame<=90;++frame){c.time=double(frame)/30;const auto baseline=c.run();for(unsigned fps:{60u,120u}){c.time=double(frame*(fps/30))/fps;const auto other=c.run();for(unsigned k=0;k<16;++k)require(std::bit_cast<std::uint64_t>(baseline.pose->bones[0].world_matrix[k])==std::bit_cast<std::uint64_t>(other.pose->bones[0].world_matrix[k]),"Absolute 30/60/120 sampling differs");}}++passed;
    auto boundary=Case{};boundary.name="limits";boundary.bones.clear();for(unsigned j=0;j<128;++j)boundary.bones.push_back({j+1,j,{}});require(boundary.run().status==mo::Status::completed,"128 bones rejected");++passed;
    for(unsigned j=0;j<128;++j){OwnedTrack track;track.id=j+1;for(unsigned k=0;k<32;++k)track.keys.push_back({double(k)/16,{}});boundary.tracks.push_back(track);}require(boundary.run().status==mo::Status::completed,"128 tracks / 4096 total keys rejected");++passed;
    auto keys=linear("limits");keys.duration=1;keys.time=.5;keys.tracks[0].keys.clear();for(unsigned j=0;j<4096;++j)keys.tracks[0].keys.push_back({double(j)/4095,trs({double(j),0,0})});require(keys.run().status==mo::Status::completed,"4096 keys rejected");keys.tracks[0].keys.push_back({1,{}});require(keys.run().status==mo::Status::budget_exceeded,"4097 keys accepted");++passed;
    auto nan=linear("nan");nan.tracks[0].keys[1].pose.rotation.w=std::numeric_limits<double>::infinity();require(nan.run().status==mo::Status::invalid_input,"Nonfinite quaternion accepted");nan=linear("nan");nan.time=std::numeric_limits<double>::quiet_NaN();require(nan.run().status==mo::Status::invalid_input,"NaN sample accepted");++passed;
    require(linear("reuse").run().status==mo::Status::completed,"Failure contaminated later sampling");++passed;
    std::cout<<"motion: "<<passed<<" groups PASS\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL: "<<e.what()<<'\n';return 1;}}
