#include "pikapika/motion_io.hpp"
#include <algorithm>
#include <charconv>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>

namespace {
using namespace pikapika;
double number(const char* text){const std::string s(text);double value{};const char* begin=s.data()+(s.starts_with('+')?1:0);const auto r=std::from_chars(begin,s.data()+s.size(),value,std::chars_format::general);if(r.ec!=std::errc{}||r.ptr!=s.data()+s.size()||!std::isfinite(value))throw std::invalid_argument("Expected finite decimal argument");return value;}
std::uint64_t id(const char* text){const double v=number(text);if(v<1||v>9007199254740991.||std::floor(v)!=v)throw std::invalid_argument("Expected exact bone ID");return std::uint64_t(v);}
motion_io::Source load(const char* path){std::ifstream in(path,std::ios::binary);if(!in)throw std::runtime_error("Cannot open motion source");return motion_io::Source::load(in);}
void save(const motion_io::Source& source,const char* path){std::ostringstream buffer;source.save(buffer);std::ofstream out(path,std::ios::binary);if(!out)throw std::runtime_error("Cannot open motion output");out<<buffer.str();if(!out)throw std::runtime_error("Cannot write motion output");}
motion_io::Source example(){
    motion_io::Source s;s.name="Original two-link arm";s.clip_name="Reach";s.duration=2;
    s.bones={{1,0,{{0,0,0},{},{1,1,1}}},{2,1,{{0,1,0},{},{1,1,1}}},{3,2,{{1,0,0},{},{1,1,1}}},{4,3,{{1,0,0},{},{1,1,1}}}};s.bone_names={"Root","Upper","Forearm","Tip"};
    for(const auto bone:{2ULL,3ULL}){motion_io::TrackSource t;t.bone_id=bone;const Vec3 position=bone==2?Vec3{0,1,0}:Vec3{1,0,0};for(unsigned j=0;j<3;++j)t.keys.push_back({double(j),{position,j==1?Quaternion{0,0,bone==2?1.:-1.,1}:Quaternion{},{1,1,1}}});s.tracks.push_back(std::move(t));}return s;
}
void json(const motion::Result& result,double requested,double duration){
    const char* statuses[]{"completed","invalid_input","budget_exceeded","numerical_failure"};std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10)<<"{\"status\":\""<<statuses[int(result.status)]<<"\",\"requestedTime\":"<<requested<<",\"sampledTime\":";
    if(result.pose)std::cout<<result.pose->sampled_time;else std::cout<<"null";std::cout<<",\"duration\":"<<duration<<",\"bones\":[";
    if(result.pose)for(std::size_t j=0;j<result.pose->bones.size();++j){const auto& b=result.pose->bones[j];if(j)std::cout<<',';std::cout<<"{\"id\":"<<b.id<<",\"parentId\":"<<b.parent_id<<",\"local\":[";const auto& p=b.local;const double local[]{p.position.x,p.position.y,p.position.z,p.rotation.x,p.rotation.y,p.rotation.z,p.rotation.w,p.scale.x,p.scale.y,p.scale.z};for(unsigned k=0;k<10;++k){if(k)std::cout<<',';std::cout<<local[k];}std::cout<<"],\"localMatrix\":[";for(unsigned k=0;k<16;++k){if(k)std::cout<<',';std::cout<<b.local_matrix[k];}std::cout<<"],\"worldMatrix\":[";for(unsigned k=0;k<16;++k){if(k)std::cout<<',';std::cout<<b.world_matrix[k];}std::cout<<"]}";}
    std::cout<<"],\"evaluationOrder\":[";if(result.pose)for(std::size_t j=0;j<result.pose->evaluation_order.size();++j){if(j)std::cout<<',';std::cout<<result.pose->evaluation_order[j];}std::cout<<"]}\n";
}
}
int main(int argc,char** argv){try{
    const std::string command=argc>1?argv[1]:"help";
    if(command=="help"){std::cout<<"pikapika-motion init output.motion\npikapika-motion sample input.motion seconds [clamp|loop]\npikapika-motion roundtrip input.motion output.motion\npikapika-motion key input.motion boneID time px py pz qx qy qz qw sx sy sz output.motion\npikapika-motion remove-key input.motion boneID time output.motion\n";return 0;}
    if(command=="init"&&argc==3){save(example(),argv[2]);return 0;}
    if(command=="sample"&&(argc==4||argc==5)){auto source=load(argv[2]);const double time=number(argv[3]);const std::string mode=argc==5?argv[4]:"clamp";if(mode!="clamp"&&mode!="loop")throw std::invalid_argument("Playback requires clamp or loop");json(source.sample(time,mode=="loop"?motion::Playback::loop:motion::Playback::clamp),time,source.duration);return 0;}
    if(command=="roundtrip"&&argc==4){save(load(argv[2]),argv[3]);return 0;}
    if(command=="key"&&argc==16){auto source=load(argv[2]);const auto target=id(argv[3]);const double time=number(argv[4]);if(std::none_of(source.bones.begin(),source.bones.end(),[&](const auto& b){return b.id==target;}))throw std::invalid_argument("Unknown key bone");
        const motion::Key key{time,{{number(argv[5]),number(argv[6]),number(argv[7])},{number(argv[8]),number(argv[9]),number(argv[10]),number(argv[11])},{number(argv[12]),number(argv[13]),number(argv[14])}}};
        auto found=std::find_if(source.tracks.begin(),source.tracks.end(),[&](const auto& t){return t.bone_id==target;});if(found==source.tracks.end()){source.tracks.push_back({target,motion::Interpolation::linear,{}});found=source.tracks.end()-1;}
        auto old=std::find_if(found->keys.begin(),found->keys.end(),[&](const auto& k){return k.time==time;});if(old==found->keys.end())found->keys.push_back(key);else *old=key;std::sort(found->keys.begin(),found->keys.end(),[](const auto& a,const auto& b){return a.time<b.time;});save(source,argv[15]);return 0;}
    if(command=="remove-key"&&argc==6){auto source=load(argv[2]);const auto target=id(argv[3]);const double time=number(argv[4]);auto track=std::find_if(source.tracks.begin(),source.tracks.end(),[&](const auto& t){return t.bone_id==target;});if(track==source.tracks.end())throw std::invalid_argument("No such key track");auto key=std::find_if(track->keys.begin(),track->keys.end(),[&](const auto& k){return k.time==time;});if(key==track->keys.end())throw std::invalid_argument("No such key");track->keys.erase(key);if(track->keys.empty())source.tracks.erase(track);save(source,argv[5]);return 0;}
    throw std::invalid_argument("Invalid motion command; run help");
}catch(const std::exception& e){std::cerr<<"ERROR "<<e.what()<<'\n';return 1;}}
