#include "pikapika/motion_io.hpp"
#include <charconv>
#include <cmath>
#include <iomanip>
#include <istream>
#include <limits>
#include <locale>
#include <ostream>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <utility>

namespace pikapika::motion_io {
namespace {
void require(bool ok,const char* text){if(!ok)throw std::invalid_argument(text);}
void name_valid(const std::string& s){
    require(s.size()<=256,"Motion name exceeds UTF-8 byte budget");
    for(std::size_t i=0;i<s.size();){
        const unsigned a=static_cast<unsigned char>(s[i++]);
        if(a<128){require(a>=32&&a!=127,"Motion name contains control character");continue;}
        unsigned count=0,value=0,minimum=0;
        if(a>=0xc2&&a<=0xdf){count=1;value=a&31;minimum=0x80;}
        else if(a>=0xe0&&a<=0xef){count=2;value=a&15;minimum=0x800;}
        else if(a>=0xf0&&a<=0xf4){count=3;value=a&7;minimum=0x10000;}
        else throw std::invalid_argument("Invalid UTF-8 motion name");
        require(i+count<=s.size(),"Truncated UTF-8 motion name");
        while(count--){const unsigned b=static_cast<unsigned char>(s[i++]);require((b&0xc0)==0x80,"Invalid UTF-8 continuation");value=(value<<6)|(b&63);}
        require(value>=minimum&&value<=0x10ffff&&!(value>=0xd800&&value<=0xdfff),"Invalid UTF-8 scalar");
    }
}
std::vector<motion::Track> views(const Source& source){
    std::vector<motion::Track> tracks;tracks.reserve(source.tracks.size());
    for(const auto& t:source.tracks)tracks.push_back({t.bone_id,t.interpolation,t.keys});return tracks;
}
struct Reader {
    std::istringstream in;
    explicit Reader(std::string text):in(std::move(text)){in.imbue(std::locale::classic());}
    std::string token(){std::string t;require(bool(in>>t),"Truncated portable motion");return t;}
    void expect(std::string_view text){require(token()==text,"Unexpected portable motion token");}
    double number(){const auto t=token();const auto start=t.data()+(t.front()=='+'?1:0);double v{};const auto result=std::from_chars(start,t.data()+t.size(),v,std::chars_format::general);require(result.ec==std::errc{}&&result.ptr==t.data()+t.size()&&std::isfinite(v),"Invalid finite portable decimal");return v==0?0:v;}
    unsigned count(unsigned max){const double v=number();require(v>=0&&v<=max&&std::floor(v)==v,"Portable count exceeds budget");return unsigned(v);}
    std::uint64_t id(bool root=false){const double v=number();require(v>=(root?0:1)&&v<=9007199254740991.&&std::floor(v)==v,"Invalid portable motion ID");return std::uint64_t(v);}
    std::string name(){in>>std::ws;require(in.get()=='"',"Portable motion name must be quoted");std::string s;char c{};bool closed=false;while(in.get(c)){if(c=='"'){closed=true;break;}if(c=='\\'){require(bool(in.get(c))&&(c=='"'||c=='\\'),"Invalid portable name escape");}s.push_back(c);require(s.size()<=256,"Portable motion name exceeds byte budget");}require(closed,"Truncated quoted motion name");name_valid(s);return s;}
    Transform pose(){Transform p;p.position={number(),number(),number()};p.rotation={number(),number(),number(),number()};p.scale={number(),number(),number()};return p;}
};
void put_pose(std::ostream& out,const Transform& p){const double v[]{p.position.x,p.position.y,p.position.z,p.rotation.x,p.rotation.y,p.rotation.z,p.rotation.w,p.scale.x,p.scale.y,p.scale.z};for(unsigned j=0;j<10;++j){if(j)out<<' ';out<<(v[j]==0?0:v[j]);}}
}
void Source::validate() const {
    require(!bones.empty()&&bones.size()<=128&&tracks.size()<=128,"Motion source count exceeds budget");std::size_t keys=0;for(const auto& t:tracks){require(!t.keys.empty()&&t.keys.size()<=4096-keys,"Motion source key budget exceeded");keys+=t.keys.size();}
    name_valid(name);name_valid(clip_name);require(bone_names.size()==bones.size(),"Bone name count mismatch");for(const auto& n:bone_names)name_valid(n);
    const auto track_views=views(*this);const auto result=motion::sample({bones,{duration,track_views}},0);
    if(result.status==motion::Status::invalid_input||result.status==motion::Status::budget_exceeded)throw std::invalid_argument(result.message);
    // Per-node-valid sources whose FK overflows may still be edited/saved.
    // Their actual sample returns numerical_failure without a partial pose.
}
motion::Result Source::sample(double seconds,motion::Playback mode) const {
    validate();const auto track_views=views(*this);return motion::sample({bones,{duration,track_views}},seconds,mode);
}
void Source::save(std::ostream& destination) const {
    validate();std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(std::numeric_limits<double>::max_digits10);
    out<<"pikapika_motion 1\nname "<<std::quoted(name)<<"\nbones "<<bones.size()<<'\n';
    for(std::size_t i=0;i<bones.size();++i){const auto& b=bones[i];out<<"bone "<<b.id<<' '<<b.parent_id<<' '<<std::quoted(bone_names[i])<<' ';put_pose(out,b.rest);out<<'\n';}
    out<<"clip "<<std::quoted(clip_name)<<' '<<duration<<' '<<tracks.size()<<'\n';
    for(const auto& t:tracks){out<<"track "<<t.bone_id<<' '<<(t.interpolation==motion::Interpolation::linear?"linear":"step")<<' '<<t.keys.size()<<'\n';for(const auto& k:t.keys){out<<"key "<<(k.time==0?0:k.time)<<' ';put_pose(out,k.pose);out<<'\n';}}
    out<<"end\n";destination<<out.str();if(!destination)throw std::runtime_error("Cannot write portable motion");
}
Source Source::load(std::istream& input){
    constexpr std::size_t limit=4*1024*1024;std::string text;text.reserve(4096);char c{};
    while(input.get(c)){require(text.size()<limit,"Portable motion exceeds text budget");text.push_back(c);}if(!input.eof())throw std::runtime_error("Cannot read portable motion");
    Reader r(std::move(text));r.expect("pikapika_motion");require(r.number()==1,"Unsupported portable motion version");r.expect("name");Source source;source.name=r.name();r.expect("bones");const auto count=r.count(128);source.bones.reserve(count);source.bone_names.reserve(count);
    for(unsigned j=0;j<count;++j){r.expect("bone");const auto id=r.id(),parent=r.id(true);source.bone_names.push_back(r.name());source.bones.push_back({id,parent,r.pose()});}
    r.expect("clip");source.clip_name=r.name();source.duration=r.number();const auto nt=r.count(128);unsigned total=0;source.tracks.reserve(nt);
    for(unsigned j=0;j<nt;++j){r.expect("track");TrackSource track;track.bone_id=r.id();const auto mode=r.token();require(mode=="linear"||mode=="step","Invalid motion interpolation");track.interpolation=mode=="linear"?motion::Interpolation::linear:motion::Interpolation::step;const auto nk=r.count(4096);require(nk<=4096-total,"Portable total key budget exceeded");total+=nk;track.keys.reserve(nk);for(unsigned k=0;k<nk;++k){r.expect("key");track.keys.push_back({r.number(),r.pose()});}source.tracks.push_back(std::move(track));}
    r.expect("end");r.in>>std::ws;require(r.in.eof(),"Trailing portable motion data");source.validate();return source;
}
}
