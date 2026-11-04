#include "pikapika/core.hpp"
#include "pikapika/portable.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <istream>
#include <limits>
#include <locale>
#include <ostream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <unordered_map>

#if !defined(_M_ARM64EC) && !defined(__wasm__) && !defined(__clang__) && ((defined(_MSC_VER) && defined(_M_X64)) || (defined(__GNUC__) && defined(__x86_64__) && defined(__SSE2__)))
#include <emmintrin.h>
#define PP_WORLD_FLIGHT_NATIVE_SSE2 1
#else
#define PP_WORLD_FLIGHT_NATIVE_SSE2 0
#endif
#if defined(PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE) && PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE == 1
#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error Audited World predicate core requires strict floating point.
#endif
#endif

namespace pikapika {
namespace {
bool finite(Vec3 v) { return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z); }
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
void u16(std::ostream& out, std::uint16_t x) { out.put(char(x&255)); out.put(char((x>>8)&255)); }
void u32(std::ostream& out, std::uint32_t x) { u16(out,std::uint16_t(x&65535)); u16(out,std::uint16_t(x>>16)); }
}
Vec3 Vec3::operator+(Vec3 b) const { return {x+b.x,y+b.y,z+b.z}; }
Vec3 Vec3::operator-(Vec3 b) const { return {x-b.x,y-b.y,z-b.z}; }
Vec3 Vec3::operator*(double s) const { return {x*s,y*s,z*s}; }
double Vec3::dot(Vec3 b) const { return x*b.x+y*b.y+z*b.z; }
Vec3 Vec3::cross(Vec3 b) const { return {y*b.z-z*b.y,z*b.x-x*b.z,x*b.y-y*b.x}; }
double Vec3::length() const {
    const double squared=dot(*this);
#if PP_WORLD_FLIGHT_NATIVE_SSE2
    // One binary64 hardware square root. The externally audited source profile,
    // FP environment and actual object/link instructions remain separate gates.
    const __m128d value=_mm_set_sd(squared);
    return _mm_cvtsd_f64(_mm_sqrt_sd(value,value));
#else
    return std::sqrt(squared);
#endif
}
namespace detail {
unsigned world_predicate_binding_profile() noexcept {
#if PP_WORLD_FLIGHT_NATIVE_SSE2 && defined(PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE) && PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE == 1 && defined(PIKAPIKA_WORLD_FLIGHT_BUILD_ID)
    constexpr char identity[]=PIKAPIKA_WORLD_FLIGHT_BUILD_ID;
    if(sizeof(identity)!=65) {return 0;}
    for(unsigned i=0;i<64;++i) {
        const char c=identity[i];
        if(!((c>='0'&&c<='9')||(c>='a'&&c<='f'))) {return 0;}
    }
    return 1;
#else
    return 0;
#endif
}
const char* world_predicate_binding_build_id() noexcept {
#if PP_WORLD_FLIGHT_NATIVE_SSE2 && defined(PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE) && PIKAPIKA_WORLD_FLIGHT_AUDITED_PROFILE == 1 && defined(PIKAPIKA_WORLD_FLIGHT_BUILD_ID)
    return world_predicate_binding_profile()==1?PIKAPIKA_WORLD_FLIGHT_BUILD_ID:"";
#else
    return "";
#endif
}
}
Vec3 Vec3::normalized() const { const double n=length(); return n>1e-15 ? *this*(1/n) : Vec3{}; }
Quaternion Quaternion::normalized() const {
    const double n=std::sqrt(x*x+y*y+z*z+w*w);
    require(std::isfinite(n)&&n>1e-15,"invalid quaternion");
    return {x/n,y/n,z/n,w/n};
}
Vec3 Quaternion::rotate(Vec3 p) const {
    const auto q=normalized(); const Vec3 v{q.x,q.y,q.z};
    return p+v.cross(p)*(2*q.w)+v.cross(v.cross(p))*2;
}
Vec3 Transform::apply(Vec3 p) const { return position+rotation.rotate({p.x*scale.x,p.y*scale.y,p.z*scale.z}); }
std::optional<SweepHit> sweep_sphere(Vec3 start, Vec3 end, double radius, Sphere target) {
    require(finite(start)&&finite(end)&&finite(target.center)&&std::isfinite(radius)&&radius>=0&&
            std::isfinite(target.radius)&&target.radius>=0,"invalid sphere sweep");
    const Vec3 m=start-target.center, d=end-start;
    const double combined=radius+target.radius;
    // Reject magnitudes that overflow the quadratic's discriminant calculation.
    require(finite(m)&&finite(d)&&std::isfinite(combined)&&
            m.length()<1e75&&d.length()<1e75&&combined<1e75,"sphere sweep numeric range exceeded");
    const double t=pp_sweep_fraction(m.x,m.y,m.z,d.x,d.y,d.z,combined);
    if(t<0) return std::nullopt;
    const Vec3 p=start+d*t;
    return SweepHit{t,p,(p-target.center).normalized()};
}
FixedClock::FixedClock(double step, unsigned max_steps):step_(step),max_steps_(max_steps) {
    require(std::isfinite(step)&&step>0&&max_steps>0,"invalid fixed clock configuration");
}
unsigned FixedClock::advance(double elapsed, const std::function<void(double)>& tick) {
    require(std::isfinite(elapsed)&&elapsed>=0,"invalid elapsed time");
    require(std::isfinite(accumulator_+elapsed),"fixed clock elapsed range exceeded");
    accumulator_+=elapsed;
    unsigned count=0;
    while(accumulator_+step_*1e-10>=step_&&count<max_steps_) {
        tick(step_); accumulator_=std::max(0.0,accumulator_-step_); ++count; ++ticks_;
    }
    if(accumulator_>=step_) {
        const double remainder=std::fmod(accumulator_,step_);
        const double whole=accumulator_-remainder;
        require(std::isfinite(dropped_+whole),"fixed clock dropped time range exceeded");
        dropped_+=whole; accumulator_=remainder;
    }
    return count;
}
double FixedClock::alpha() const { return accumulator_/step_; }
Entity* Scene::find(std::uint64_t id) { for(auto& e:entities) if(e.id==id) return &e; return nullptr; }
const Entity* Scene::find(std::uint64_t id) const { for(const auto& e:entities) if(e.id==id) return &e; return nullptr; }
void Mesh::validate() const {
    require(version==1,"unsupported mesh version");
    require(positions.size()>=3&&positions.size()<=65536,"mesh vertex count must be 3..65536");
    require(!triangles.empty()&&triangles.size()<=131072,"mesh triangle count must be 1..131072");
    for(const auto& p:positions) require(finite(p)&&std::abs(p.x)<=1e6&&std::abs(p.y)<=1e6&&std::abs(p.z)<=1e6,"mesh vertex numeric range exceeded");
    for(const auto& triangle:triangles) {
        const auto a=triangle[0],b=triangle[1],c=triangle[2];
        require(a<positions.size()&&b<positions.size()&&c<positions.size(),"mesh triangle index out of range");
        require(a!=b&&b!=c&&a!=c,"degenerate mesh triangle indices");
        const auto normal=(positions[b]-positions[a]).cross(positions[c]-positions[a]);
        require(normal.dot(normal)>1e-24,"degenerate mesh triangle area");
        const auto rounded=[](Vec3 p){return Vec3{double(float(p.x)),double(float(p.y)),double(float(p.z))};};
        const auto af=rounded(positions[a]),bf=rounded(positions[b]),cf=rounded(positions[c]);
        const auto float_normal=(bf-af).cross(cf-af);
        require(float_normal.dot(float_normal)>0,"mesh triangle collapses in Float32 representation");
    }
}
Mesh make_box_mesh(Vec3 size) {
    require(finite(size)&&size.x>0&&size.y>0&&size.z>0,"invalid box mesh dimensions");
    const auto h=size*0.5;
    Mesh mesh; mesh.positions={{-h.x,-h.y,-h.z},{h.x,-h.y,-h.z},{h.x,h.y,-h.z},{-h.x,h.y,-h.z},
                              {-h.x,-h.y,h.z},{h.x,-h.y,h.z},{h.x,h.y,h.z},{-h.x,h.y,h.z}};
    mesh.triangles={{0,2,1},{0,3,2},{4,5,6},{4,6,7},{0,4,7},{0,7,3},
                    {1,2,6},{1,6,5},{3,7,6},{3,6,2},{0,1,5},{0,5,4}};
    mesh.validate(); return mesh;
}
unsigned Scene::format_version() const {
    for(const auto& entity:entities) if(entity.type=="mesh") return 2;
    return 1;
}
void Scene::set_position(std::uint64_t id, Vec3 meters) {
    require(finite(meters),"nonfinite entity position");
    auto* e=find(id); require(e!=nullptr,"unknown stable entity ID"); e->transform.position=meters;
}
void Scene::set_mesh_vertex(std::uint64_t id,std::size_t index,Vec3 meters) {
    auto* entity=find(id); require(entity&&entity->type=="mesh","unknown mesh entity ID");
    require(index<entity->mesh.positions.size(),"mesh vertex index out of range");
    auto candidate=entity->mesh; candidate.positions[index]=meters; candidate.validate();
    entity->mesh=std::move(candidate);
}
void Scene::validate() const {
    require(entities.size()<=100000,"scene entity limit exceeded");
    require(annotations.size()<=100000,"scene annotation limit exceeded");
    for(const auto& comment:annotations) require(!comment.empty()&&comment.front()=='#'&&comment.size()<=4096&&
        comment.find_first_of("\r\n")==std::string::npos,"invalid scene annotation");
    std::set<std::uint64_t> ids;
    std::size_t total_vertices=0,total_triangles=0;
    for(const auto& e:entities) {
        require(e.id>0&&e.id<=9007199254740991ULL&&ids.insert(e.id).second,"invalid or duplicate stable ID");
        require(!e.type.empty()&&e.type.size()<=64&&e.name.size()<=1024,"invalid entity metadata length");
        const bool nongeometry=e.type=="camera"||e.type=="source"||e.type=="listener";
        require(e.type=="box"||e.type=="robot"||e.type=="plane"||e.type=="mesh"||nongeometry,"unsupported scene entity type");
        require(e.type.find_first_of("\r\n")==std::string::npos&&e.name.find_first_of("\r\n")==std::string::npos,"newline in entity metadata");
        require(finite(e.transform.position)&&finite(e.transform.scale),"nonfinite transform");
        const auto& s=e.transform.scale;
        require(s.x>0&&s.y>0&&s.z>0,"scale must be positive");
        const auto& q=e.transform.rotation;
        const double q2=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
        require(std::isfinite(q2)&&std::abs(q2-1)<1e-6,"quaternion must be normalized");
        require(std::isfinite(e.radius)&&e.radius>=0,"invalid collider radius");
        require(!nongeometry||e.radius==0,"nongeometry entity radius is reserved as zero");
        if(e.type=="mesh") {
            e.mesh.validate(); total_vertices+=e.mesh.positions.size(); total_triangles+=e.mesh.triangles.size();
            require(total_vertices<=262144&&total_triangles<=524288,"scene mesh geometry quota exceeded");
        } else require(e.mesh.positions.empty()&&e.mesh.triangles.empty(),"mesh data attached to nonmesh entity");
    }
}
Scene Scene::load(std::istream& input) {
    Scene scene;
    std::string line;
    const auto bounded_line=[&]() {
        line.clear(); char character{};
        while(input.get(character)) {
            if(character=='\n') return true;
            require(line.size()<4096,"scene line limit exceeded"); line.push_back(character);
        }
        return !line.empty();
    };
    unsigned input_version=0;
    const std::array<std::string,3> headers={"","units m s kg","axes right-handed y-up"};
    for(std::size_t index=0;index<headers.size();++index) {
        require(bounded_line(),"missing scene header");
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        if(index==0) {
            require(line=="pikapika-scene 1"||line=="pikapika-scene 2","unsupported scene header/version/units/axes");
            input_version=line.back()=='2'?2:1;
        } else require(line==headers[index],"unsupported scene header/version/units/axes");
    }
    std::set<std::uint64_t> mesh_blocks;
    std::unordered_map<std::uint64_t,std::size_t> entity_indices;
    std::size_t total_vertices=0,total_triangles=0;
    while(bounded_line()) {
        require(line.size()<=4096,"scene line limit exceeded");
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        if(line.empty()) continue;
        if(line[0]=='#') {
            scene.annotations.push_back(line); require(scene.annotations.size()<=100000,"scene annotation limit exceeded"); continue;
        }
        std::istringstream row(line); row.imbue(std::locale::classic());
        Entity e; std::string tag,extra; auto& t=e.transform;
        require(bool(row>>tag),"malformed scene record");
        if(tag=="mesh") {
            std::uint64_t id{};std::size_t vertex_count{},triangle_count{};
            require(input_version==2&&bool(row>>id>>vertex_count>>triangle_count)&&!(row>>extra),"malformed mesh block header/version");
            const auto location=entity_indices.find(id);
            auto* entity=location==entity_indices.end()?nullptr:&scene.entities[location->second];
            require(entity&&entity->type=="mesh"&&mesh_blocks.insert(id).second,"unknown or duplicate mesh block");
            require(vertex_count>=3&&vertex_count<=65536&&triangle_count>0&&triangle_count<=131072,"mesh block count limit exceeded");
            total_vertices+=vertex_count;total_triangles+=triangle_count;
            require(total_vertices<=262144&&total_triangles<=524288,"scene mesh geometry quota exceeded");
            for(std::size_t i=0;i<vertex_count;++i) {
                require(bounded_line(),"incomplete mesh vertex block");std::istringstream vertex(line);vertex.imbue(std::locale::classic());
                Vec3 p;require(bool(vertex>>tag>>p.x>>p.y>>p.z)&&tag=="vertex"&&!(vertex>>extra),"malformed mesh vertex");
                entity->mesh.positions.push_back(p);
            }
            for(std::size_t i=0;i<triangle_count;++i) {
                require(bounded_line(),"incomplete mesh triangle block");std::istringstream face(line);face.imbue(std::locale::classic());
                std::array<std::uint32_t,3> triangle{};
                require(bool(face>>tag>>triangle[0]>>triangle[1]>>triangle[2])&&tag=="triangle"&&!(face>>extra),"malformed mesh triangle");
                entity->mesh.triangles.push_back(triangle);
            }
            entity->mesh.validate();continue;
        }
        require(tag=="entity"&&bool(row>>e.id>>std::quoted(e.type)>>std::quoted(e.name)
            >>t.position.x>>t.position.y>>t.position.z
            >>t.rotation.x>>t.rotation.y>>t.rotation.z>>t.rotation.w
            >>t.scale.x>>t.scale.y>>t.scale.z>>e.radius),"malformed scene entity");
        require(!(row>>extra),"unknown scene record or trailing property");
        require(e.type!="mesh"||input_version==2,"mesh entity requires scene version 2");
        require(entity_indices.emplace(e.id,scene.entities.size()).second,"duplicate stable entity ID");
        scene.entities.push_back(std::move(e));
        require(scene.entities.size()<=100000,"scene entity limit exceeded");
    }
    for(const auto& entity:scene.entities) require(entity.type!="mesh"||mesh_blocks.contains(entity.id),"missing mesh geometry block");
    require(!input.bad(),"scene read failure"); scene.validate(); return scene;
}
void Scene::save(std::ostream& output) const {
    validate(); output.imbue(std::locale::classic()); output<<std::setprecision(17);
    output<<"pikapika-scene "<<format_version()<<"\nunits m s kg\naxes right-handed y-up\n";
    for(const auto& comment:annotations) output<<comment<<'\n';
    for(const auto& e:entities) {
        const auto& t=e.transform;
        output<<"entity "<<e.id<<' '<<std::quoted(e.type)<<' '<<std::quoted(e.name)<<' '
            <<t.position.x<<' '<<t.position.y<<' '<<t.position.z<<' '
            <<t.rotation.x<<' '<<t.rotation.y<<' '<<t.rotation.z<<' '<<t.rotation.w<<' '
            <<t.scale.x<<' '<<t.scale.y<<' '<<t.scale.z<<' '<<e.radius<<'\n';
        if(e.type=="mesh") {
            output<<"mesh "<<e.id<<' '<<e.mesh.positions.size()<<' '<<e.mesh.triangles.size()<<'\n';
            for(const auto& p:e.mesh.positions) output<<"vertex "<<p.x<<' '<<p.y<<' '<<p.z<<'\n';
            for(const auto& f:e.mesh.triangles) output<<"triangle "<<f[0]<<' '<<f[1]<<' '<<f[2]<<'\n';
        }
    }
    require(bool(output),"scene write failure");
}
DirectSound direct_sound(Vec3 source, Vec3 listener, double speed, double reference) {
    require(finite(source)&&finite(listener)&&std::isfinite(speed)&&speed>0&&
            std::isfinite(reference)&&reference>0,"invalid direct sound configuration");
    const double d=(listener-source).length();
    require(std::isfinite(d)&&std::isfinite(d/speed),"direct sound numeric range exceeded");
    return {d,pp_direct_delay(d,speed),pp_direct_pressure_gain(d,reference)};
}
std::vector<float> render_direct_impulse(const DirectSound& path, unsigned rate, double duration) {
    require(rate>=8000&&rate<=192000&&std::isfinite(duration)&&duration>0&&duration<=60,"invalid audio output limits");
    require(std::isfinite(path.delay_seconds)&&path.delay_seconds>=0&&std::isfinite(path.pressure_gain)&&
            path.pressure_gain>=0&&path.pressure_gain<=1,"invalid direct sound path");
    std::vector<float> pcm(static_cast<std::size_t>(std::ceil(duration*rate)),0);
    const double offset=path.delay_seconds*rate;
    // Linear fractional-sample delay for the reference impulse.
    if(offset<double(pcm.size())) {
        const auto i=static_cast<std::size_t>(offset); const double f=offset-double(i);
        pcm[i]=float(path.pressure_gain*(1-f));
        if(i+1<pcm.size()) pcm[i+1]=float(path.pressure_gain*f);
    }
    return pcm;
}
void write_wav(std::ostream& out, const std::vector<float>& mono, unsigned rate) {
    require(rate>=8000&&rate<=192000&&mono.size()<=(std::numeric_limits<std::uint32_t>::max()-36)/2,"invalid WAV size/rate");
    for(float sample:mono) require(std::isfinite(sample),"nonfinite WAV sample");
    const auto bytes=std::uint32_t(mono.size()*2);
    out.write("RIFF",4); u32(out,36+bytes); out.write("WAVEfmt ",8); u32(out,16); u16(out,1); u16(out,1);
    u32(out,rate); u32(out,rate*2); u16(out,2); u16(out,16); out.write("data",4); u32(out,bytes);
    for(float sample:mono) u16(out,std::uint16_t(std::int16_t(std::lround(std::clamp(sample,-1.f,1.f)*32767))));
    require(bool(out),"WAV write failure");
}
}
