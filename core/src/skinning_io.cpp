#include "pikapika/skinning_io.hpp"
#include <algorithm>
#include <bit>
#include <charconv>
#include <cmath>
#include <iomanip>
#include <istream>
#include <limits>
#include <locale>
#include <map>
#include <ostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string_view>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Skin binding IO requires signed-zero-preserving strict floating point.
#endif

namespace pikapika::skinning_io {
namespace {
constexpr std::size_t text_limit=8*1024*1024,motion_limit=4*1024*1024;
constexpr std::uint64_t maximum_id=9007199254740991ULL;
void require(bool ok,const char* s){if(!ok)throw std::invalid_argument(s);}
std::size_t unicode_units(std::string_view s,bool controls){
    std::size_t units=0;
    for(std::size_t i=0;i<s.size();){unsigned a=static_cast<unsigned char>(s[i++]);
        if(a<128){require(!controls||(a>=32&&a!=127),"Skin text contains control character");++units;continue;}
        unsigned count{},value{},minimum{};
        if(a>=0xc2&&a<=0xdf){count=1;value=a&31;minimum=0x80;}
        else if(a>=0xe0&&a<=0xef){count=2;value=a&15;minimum=0x800;}
        else if(a>=0xf0&&a<=0xf4){count=3;value=a&7;minimum=0x10000;}
        else throw std::invalid_argument("Invalid skin UTF-8 lead byte");
        require(i+count<=s.size(),"Truncated skin UTF-8");
        while(count--){const unsigned b=static_cast<unsigned char>(s[i++]);require((b&0xc0)==0x80,"Invalid skin UTF-8 continuation");value=(value<<6)|(b&63);}
        require(value>=minimum&&value<=0x10ffff&&!(value>=0xd800&&value<=0xdfff),"Invalid skin Unicode scalar");units+=value>0xffff?2:1;
    }return units;
}
void name_valid(const std::string&s){require(s.size()<=256,"Skin name exceeds256 UTF-8 bytes");unicode_units(s,true);}
void id_valid(std::uint64_t id){require(id>=1&&id<=maximum_id,"Skin ID outside exact integer domain");}
std::uint64_t native_id(std::string_view s){require(!s.empty()&&s.front()>='1'&&s.front()<='9'&&s.size()<=16,"Skin nativeId must be canonical decimal");std::uint64_t out=0;for(char c:s){require(c>='0'&&c<='9',"Skin nativeId must be canonical decimal");const unsigned digit=unsigned(c-'0');require(out<=(maximum_id-digit)/10,"Skin nativeId outside exact integer domain");out=out*10+digit;}return out;}
bool equal(Vec3 a,Vec3 b){return a.x==b.x&&a.y==b.y&&a.z==b.z;}
bool equal(Transform a,Transform b){return equal(a.position,b.position)&&equal(a.scale,b.scale)&&a.rotation.x==b.rotation.x&&a.rotation.y==b.rotation.y&&a.rotation.z==b.rotation.z&&a.rotation.w==b.rotation.w;}
void matrix_valid(const skinning::Mat4&m){for(double x:m)require(std::isfinite(x)&&std::abs(x)<=1e150,"Skin affine element outside finite +/-1e150 domain");require(m[3]==0&&m[7]==0&&m[11]==0&&m[15]==1,"Skin matrix final row must be0,0,0,1");}
void structure(const Source&s,bool joints_required){
    name_valid(s.name);require(!s.target.object_id.empty()&&s.target.object_id.size()<=384&&unicode_units(s.target.object_id,true)<=96,"Skin objectId exceeds Unicode domain");native_id(s.target.native_id);
    require(s.mesh.positions.size()>=3&&s.mesh.positions.size()<=2048&&s.mesh.triangles.size()>=1&&s.mesh.triangles.size()<=131072,"Skin owned mesh count limit");s.mesh.validate();
    require(s.influences.size()==s.mesh.positions.size(),"Skin influence vertex count mismatch");s.motion.validate();require(s.rest_bones.size()>=1&&s.rest_bones.size()<=128&&s.rest_bones.size()==s.motion.bones.size(),"Skin rest snapshot count mismatch");
    std::map<std::uint64_t,const motion::Bone*> rest;for(const auto&b:s.rest_bones){id_valid(b.id);require(rest.emplace(b.id,&b).second,"Duplicate skin rest snapshot ID");}
    for(const auto&b:s.motion.bones){const auto i=rest.find(b.id);require(i!=rest.end()&&i->second->parent_id==b.parent_id&&equal(i->second->rest,b.rest),"Motion local rest/parent differs from binding snapshot");}
    std::size_t total=0;for(const auto&v:s.influences){require(v.size()>=1&&v.size()<=4&&v.size()<=8192-total,"Skin influence count limit");total+=v.size();std::set<std::uint64_t> seen;bool positive=false;for(const auto&i:v){id_valid(i.bone_id);require(rest.contains(i.bone_id)&&seen.insert(i.bone_id).second,"Unknown or duplicate skin influence ID");require(std::isfinite(i.weight)&&i.weight>=0,"Invalid skin author weight");positive=positive||i.weight>0;}require(positive,"Skin author weights all zero");}
    if(joints_required){require(s.joints.size()==rest.size(),"Skin joint set/count mismatch");std::set<std::uint64_t> seen;for(const auto&j:s.joints){id_valid(j.bone_id);require(rest.contains(j.bone_id)&&seen.insert(j.bone_id).second,"Unknown or duplicate skin joint ID");matrix_valid(j.rest_world);matrix_valid(j.inverse_bind);}}
    require(s.fingerprint.size()==16&&std::all_of(s.fingerprint.begin(),s.fingerprint.end(),[](char c){return(c>='0'&&c<='9')||(c>='a'&&c<='f');}),"Skin fingerprint requires16 lowercase hex digits");require(s.fingerprint==mesh_fingerprint(s.mesh),"Skin fingerprint differs from owned ordered geometry");
}
motion::Result rest_pose(const Source&s){const std::array<motion::Track,0> tracks{};return motion::sample({s.motion.bones,{s.motion.duration,tracks}},0,motion::Playback::clamp);}
void put_number(std::ostream&out,double x){if(x==0&&std::signbit(x))out<<"-0";else out<<x;}
void put_pose(std::ostream&out,const Transform&t){const double values[]{t.position.x,t.position.y,t.position.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale.x,t.scale.y,t.scale.z};for(double x:values){out<<' ';put_number(out,x);}}
struct Line {
    std::string_view value;std::size_t offset{};
    void space(){while(offset<value.size()&&(value[offset]==' '||value[offset]=='\t'||value[offset]=='\r'))++offset;}
    std::string_view token(){space();const auto start=offset;while(offset<value.size()&&value[offset]!=' '&&value[offset]!='\t'&&value[offset]!='\r')++offset;require(offset>start,"Truncated skin portable line");return value.substr(start,offset-start);}
    void expect(std::string_view t){require(token()==t,"Unexpected skin portable record");}
    void done(){space();require(offset==value.size(),"Trailing skin portable field");}
    double number(){const auto t=token();const auto start=t.data()+(t.front()=='+'?1:0);double x{};const auto r=std::from_chars(start,t.data()+t.size(),x,std::chars_format::general);require(r.ec==std::errc{}&&r.ptr==t.data()+t.size()&&std::isfinite(x),"Invalid finite skin decimal");if(x==0){bool nonzero=false;for(char c:t){if(c=='e'||c=='E')break;if(c>='1'&&c<='9')nonzero=true;}require(!nonzero,"Skin nonzero decimal underflows to zero");}return x;}
    std::size_t count(std::size_t max){const double x=number();require(x>=0&&x<=double(max)&&std::floor(x)==x,"Skin portable count outside budget");return std::size_t(x);}
    std::uint64_t id(bool parent=false){const double x=number();require(x>=(parent?0:1)&&x<=double(maximum_id)&&std::floor(x)==x,"Invalid skin numeric ID");return std::uint64_t(x);}
    std::string quoted(){space();require(offset<value.size()&&value[offset++]=='"',"Skin string must be quoted");std::string out;bool closed=false;while(offset<value.size()){char c=value[offset++];if(c=='"'){closed=true;break;}if(c=='\\'){require(offset<value.size(),"Truncated skin quote escape");c=value[offset++];require(c=='"'||c=='\\',"Unknown skin quote escape");}out.push_back(c);require(out.size()<=384,"Skin quoted string byte budget");}require(closed,"Unclosed skin string");require(offset==value.size()||value[offset]==' '||value[offset]=='\t'||value[offset]=='\r',"Skin quoted strings require a delimiter");return out;}
    Transform pose(){Transform t;t.position={number(),number(),number()};t.rotation={number(),number(),number(),number()};t.scale={number(),number(),number()};return t;}
};
struct Reader {
    std::string text;std::size_t offset{};
    Line line(){require(offset<text.size(),"Truncated skin source");const auto start=offset;const auto end=text.find('\n',start);const auto stop=end==std::string::npos?text.size():end;require(stop-start<=4096,"Skin outer line exceeds4096 bytes");offset=end==std::string::npos?stop:stop+1;auto v=std::string_view(text).substr(start,stop-start);if(!v.empty()&&v.back()=='\r')v.remove_suffix(1);return {v};}
};
}

std::string mesh_fingerprint(const Mesh&mesh){
    static_assert(sizeof(double)==8&&std::numeric_limits<double>::is_iec559);
    mesh.validate();std::uint64_t hash=0xcbf29ce484222325ULL;const auto byte=[&](unsigned b){hash^=std::uint8_t(b);hash*=0x100000001b3ULL;};
    for(unsigned char c:std::string_view("pikapika_mesh_fingerprint 1\n"))byte(c);
    const auto u32=[&](std::uint32_t n){for(unsigned j=0;j<4;++j)byte(unsigned(n>>(8*j)));};u32(mesh.version);u32(std::uint32_t(mesh.positions.size()));u32(std::uint32_t(mesh.triangles.size()));
    for(const auto&p:mesh.positions)for(double x:{p.x,p.y,p.z}){const auto bits=std::bit_cast<std::uint64_t>(x==0?0.:x);for(unsigned j=0;j<8;++j)byte(unsigned(bits>>(8*j)));}
    for(const auto&t:mesh.triangles){
        for(auto n:t)u32(n);
    }
    std::ostringstream out;out.imbue(std::locale::classic());out<<std::hex<<std::nouppercase<<std::setfill('0')<<std::setw(16)<<hash;return out.str();
}
void Source::validate()const{structure(*this,true);}
skinning::DeformResult Source::sample(double seconds,pikapika::motion::Playback mode)const{
    validate();const auto rest=rest_pose(*this);require(rest.pose.has_value(),"Skin rest FK failed; no deformation");std::map<std::uint64_t,const skinning::Mat4*> matrices;for(const auto&b:rest.pose->bones)matrices.emplace(b.id,&b.world_matrix);
    for(const auto&j:joints){
        require(*matrices.at(j.bone_id)==j.rest_world,"Skin stored restWorld differs from C++ rest FK");
    }
    const auto sampled=motion.sample(seconds,mode);require(sampled.pose.has_value(),"Skin current motion FK failed; no deformation");
    std::vector<skinning::BoneMatrix> pose;pose.reserve(sampled.pose->bones.size());for(const auto&b:sampled.pose->bones)pose.push_back({b.id,b.world_matrix});std::vector<skinning::Vertex> vertices;vertices.reserve(mesh.positions.size());for(std::size_t j=0;j<mesh.positions.size();++j)vertices.push_back({mesh.positions[j],influences[j]});return skinning::deform(vertices,joints,pose);
}
void Source::match(const Scene&scene)const{
    validate();scene.validate();const auto*entity=scene.find(native_id(target.native_id));require(entity&&entity->type=="mesh","Skin numeric target not found or not mesh");const auto&m=entity->mesh;require(mesh_fingerprint(m)==fingerprint&&m.version==mesh.version&&m.positions.size()==mesh.positions.size()&&m.triangles==mesh.triangles,"Skin context ordered geometry differs");for(std::size_t j=0;j<m.positions.size();++j)require(equal(m.positions[j],mesh.positions[j]),"Skin context vertex differs");
}
void Source::set_weight(std::size_t vertex,std::uint64_t bone_id,double value){validate();require(vertex<influences.size(),"Skin vertex index outside source");Source candidate=*this;auto&v=candidate.influences[vertex];const auto i=std::find_if(v.begin(),v.end(),[&](const auto&w){return w.bone_id==bone_id;});require(i!=v.end(),"Skin weight edit requires an existing influence");i->weight=value;candidate.validate();*this=std::move(candidate);}
Source create(std::string name,Target target,Mesh mesh,motion_io::Source motion,std::vector<std::vector<skinning::Influence>> influences){
    require(mesh.positions.size()>=3&&mesh.positions.size()<=2048&&mesh.triangles.size()>=1&&mesh.triangles.size()<=131072&&motion.bones.size()>=1&&motion.bones.size()<=128,"Skin creation count limit");
    Source s;s.name=std::move(name);s.target=std::move(target);s.mesh=std::move(mesh);s.motion=std::move(motion);s.influences=std::move(influences);s.rest_bones=s.motion.bones;s.fingerprint=mesh_fingerprint(s.mesh);structure(s,false);const auto rest=rest_pose(s);require(rest.pose.has_value(),"Cannot bind failed rest FK");std::vector<skinning::BoneMatrix> matrices;for(const auto&b:rest.pose->bones)matrices.push_back({b.id,b.world_matrix});auto binding=skinning::bind(matrices);require(binding.joints.has_value(),"Cannot construct inverse binding");s.joints=std::move(*binding.joints);s.validate();return s;
}
Source example(){
    Mesh mesh;mesh.positions={{0,-.2,0},{1,-.2,0},{2,-.2,0},{0,.2,0},{1,.2,0},{2,.2,0}};mesh.triangles={{0,1,4},{0,4,3},{1,2,5},{1,5,4}};
    motion_io::Source motion;motion.name="Original arm motion";motion.bones={{19,7,{{1,0,0},{},{1,1,1}}},{7,0,{}}};motion.bone_names={"Child","Root"};motion.clip_name="Bend";motion.duration=2;motion_io::TrackSource t;t.bone_id=19;for(unsigned j=0;j<3;++j)t.keys.push_back({double(j),{{1,0,0},j==1?Quaternion{0,0,1,1}:Quaternion{},{1,1,1}}});motion.tracks.push_back(t);
    std::vector<std::vector<skinning::Influence>> weights;for(unsigned j=0;j<6;++j)weights.push_back(j%3==0?std::vector<skinning::Influence>{{7,1}}:j%3==1?std::vector<skinning::Influence>{{19,1},{7,1}}:std::vector<skinning::Influence>{{19,1}});return create("Original arm binding",{"arm-mesh","42"},std::move(mesh),std::move(motion),std::move(weights));
}
void Source::save(std::ostream&destination)const{
    validate();std::ostringstream motion_text;motion.save(motion_text);const auto block=motion_text.str();require(!block.empty()&&block.size()<=motion_limit&&block.back()=='\n',"Skin embedded motion byte budget/termination");std::ostringstream out;out.imbue(std::locale::classic());out<<std::setprecision(std::numeric_limits<double>::max_digits10);
    out<<"pikapika_skin 1\nname "<<std::quoted(name)<<"\nobject "<<std::quoted(target.object_id)<<' '<<std::quoted(target.native_id)<<"\nspace mesh-local-is-skeleton\nfingerprint "<<fingerprint<<"\nmesh "<<mesh.positions.size()<<' '<<mesh.triangles.size()<<'\n';
    for(const auto&p:mesh.positions){out<<"vertex ";put_number(out,p.x);out<<' ';put_number(out,p.y);out<<' ';put_number(out,p.z);out<<'\n';}for(const auto&t:mesh.triangles)out<<"triangle "<<t[0]<<' '<<t[1]<<' '<<t[2]<<'\n';
    out<<"influences "<<influences.size()<<'\n';for(const auto&v:influences){out<<"weights "<<v.size();for(const auto&w:v){out<<' '<<w.bone_id<<' ';put_number(out,w.weight);}out<<'\n';}
    out<<"joints "<<joints.size()<<'\n';for(const auto&j:joints){out<<"joint "<<j.bone_id;for(const auto&m:{j.rest_world,j.inverse_bind})for(double x:m){out<<' ';put_number(out,x);}out<<'\n';}
    out<<"rest_bones "<<rest_bones.size()<<'\n';for(const auto&b:rest_bones){out<<"rest_bone "<<b.id<<' '<<b.parent_id;put_pose(out,b.rest);out<<'\n';}out<<"motion_bytes "<<block.size()<<'\n'<<block<<"end_skin\n";const auto text=out.str();require(text.size()<=text_limit,"Skin serialized text exceeds8MiB");destination.write(text.data(),std::streamsize(text.size()));if(!destination)throw std::runtime_error("Cannot write skin source");
}
Source Source::load(std::istream&input){
    Reader r;char c{};while(input.get(c)){require(r.text.size()<text_limit,"Skin text exceeds8MiB");r.text.push_back(c);}if(!input.eof())throw std::runtime_error("Cannot read skin source");unicode_units(r.text,false);Source s;
    {auto l=r.line();l.expect("pikapika_skin");require(l.number()==1,"Unsupported skin version");l.done();}{auto l=r.line();l.expect("name");s.name=l.quoted();l.done();}{auto l=r.line();l.expect("object");s.target={l.quoted(),l.quoted()};l.done();}{auto l=r.line();l.expect("space");l.expect("mesh-local-is-skeleton");l.done();}{auto l=r.line();l.expect("fingerprint");s.fingerprint=std::string(l.token());l.done();}
    std::size_t nv{},nt{};{auto l=r.line();l.expect("mesh");nv=l.count(2048);nt=l.count(131072);require(nv>=3&&nt>=1,"Skin mesh count minimum");l.done();}s.mesh.positions.reserve(nv);s.mesh.triangles.reserve(nt);for(std::size_t j=0;j<nv;++j){auto l=r.line();l.expect("vertex");s.mesh.positions.push_back({l.number(),l.number(),l.number()});l.done();}for(std::size_t j=0;j<nt;++j){auto l=r.line();l.expect("triangle");std::array<std::uint32_t,3> t{};for(auto&i:t)i=std::uint32_t(l.count(nv-1));s.mesh.triangles.push_back(t);l.done();}
    {auto l=r.line();l.expect("influences");require(l.count(2048)==nv,"Skin influence vertex count mismatch");l.done();}s.influences.reserve(nv);std::size_t total=0;for(std::size_t j=0;j<nv;++j){auto l=r.line();l.expect("weights");const auto size=l.count(4);require(size>=1&&size<=8192-total,"Skin influence total limit");total+=size;std::vector<skinning::Influence> v;for(std::size_t k=0;k<size;++k)v.push_back({l.id(),l.number()});l.done();s.influences.push_back(std::move(v));}
    std::size_t nj{},nb{};{auto l=r.line();l.expect("joints");nj=l.count(128);require(nj>=1,"Skin joint count minimum");l.done();}s.joints.reserve(nj);for(std::size_t j=0;j<nj;++j){auto l=r.line();l.expect("joint");skinning::JointBind b;b.bone_id=l.id();for(auto*m:{&b.rest_world,&b.inverse_bind})for(double&x:*m)x=l.number();l.done();s.joints.push_back(b);}
    {auto l=r.line();l.expect("rest_bones");nb=l.count(128);require(nb>=1,"Skin rest count minimum");l.done();}s.rest_bones.reserve(nb);for(std::size_t j=0;j<nb;++j){auto l=r.line();l.expect("rest_bone");const auto id=l.id(),parent=l.id(true);s.rest_bones.push_back({id,parent,l.pose()});l.done();}
    std::size_t bytes{};{auto l=r.line();l.expect("motion_bytes");bytes=l.count(motion_limit);require(bytes>=1,"Skin motion block empty");l.done();}require(bytes<=r.text.size()-r.offset,"Truncated skin motion block");const auto block=r.text.substr(r.offset,bytes);require(block.back()=='\n',"Skin motion block requires finalLF");r.offset+=bytes;std::istringstream motion_input(block);s.motion=motion_io::Source::load(motion_input);{auto l=r.line();l.expect("end_skin");l.done();}require(r.offset==r.text.size(),"Trailing skin source data");s.validate();return s;
}
}
