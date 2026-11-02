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
double Vec3::length() const { return std::sqrt(dot(*this)); }
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
void Scene::set_position(std::uint64_t id, Vec3 meters) {
    require(finite(meters),"nonfinite entity position");
    auto* e=find(id); require(e!=nullptr,"unknown stable entity ID"); e->transform.position=meters;
}
void Scene::validate() const {
    require(entities.size()<=100000,"scene entity limit exceeded");
    require(annotations.size()<=100000,"scene annotation limit exceeded");
    for(const auto& comment:annotations) require(!comment.empty()&&comment.front()=='#'&&comment.size()<=4096&&
        comment.find_first_of("\r\n")==std::string::npos,"invalid scene annotation");
    std::set<std::uint64_t> ids;
    for(const auto& e:entities) {
        require(e.id>0&&e.id<=9007199254740991ULL&&ids.insert(e.id).second,"invalid or duplicate stable ID");
        require(!e.type.empty()&&e.type.size()<=64&&e.name.size()<=1024,"invalid entity metadata length");
        const bool nongeometry=e.type=="camera"||e.type=="source"||e.type=="listener";
        require(e.type=="box"||e.type=="robot"||e.type=="plane"||nongeometry,"unsupported scene entity type");
        require(e.type.find_first_of("\r\n")==std::string::npos&&e.name.find_first_of("\r\n")==std::string::npos,"newline in entity metadata");
        require(finite(e.transform.position)&&finite(e.transform.scale),"nonfinite transform");
        const auto& s=e.transform.scale;
        require(s.x>0&&s.y>0&&s.z>0,"scale must be positive");
        const auto& q=e.transform.rotation;
        const double q2=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
        require(std::isfinite(q2)&&std::abs(q2-1)<1e-6,"quaternion must be normalized");
        require(std::isfinite(e.radius)&&e.radius>=0,"invalid collider radius");
        require(!nongeometry||e.radius==0,"nongeometry entity radius is reserved as zero");
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
    const std::array<std::string,3> headers={"pikapika-scene 1","units m s kg","axes right-handed y-up"};
    for(const auto& expected:headers) {
        require(bounded_line(),"missing scene header");
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        require(line==expected,"unsupported scene header/version/units/axes");
    }
    while(bounded_line()) {
        require(line.size()<=4096,"scene line limit exceeded");
        if(!line.empty()&&line.back()=='\r') line.pop_back();
        if(line.empty()) continue;
        if(line[0]=='#') {
            scene.annotations.push_back(line); require(scene.annotations.size()<=100000,"scene annotation limit exceeded"); continue;
        }
        std::istringstream row(line); row.imbue(std::locale::classic());
        Entity e; std::string tag,extra; auto& t=e.transform;
        require(bool(row>>tag>>e.id>>std::quoted(e.type)>>std::quoted(e.name)
            >>t.position.x>>t.position.y>>t.position.z
            >>t.rotation.x>>t.rotation.y>>t.rotation.z>>t.rotation.w
            >>t.scale.x>>t.scale.y>>t.scale.z>>e.radius),"malformed scene entity");
        require(tag=="entity"&&!(row>>extra),"unknown scene record or trailing property");
        scene.entities.push_back(std::move(e));
        require(scene.entities.size()<=100000,"scene entity limit exceeded");
    }
    require(!input.bad(),"scene read failure"); scene.validate(); return scene;
}
void Scene::save(std::ostream& output) const {
    validate(); output.imbue(std::locale::classic()); output<<std::setprecision(17);
    output<<"pikapika-scene 1\nunits m s kg\naxes right-handed y-up\n";
    for(const auto& comment:annotations) output<<comment<<'\n';
    for(const auto& e:entities) {
        const auto& t=e.transform;
        output<<"entity "<<e.id<<' '<<std::quoted(e.type)<<' '<<std::quoted(e.name)<<' '
            <<t.position.x<<' '<<t.position.y<<' '<<t.position.z<<' '
            <<t.rotation.x<<' '<<t.rotation.y<<' '<<t.rotation.z<<' '<<t.rotation.w<<' '
            <<t.scale.x<<' '<<t.scale.y<<' '<<t.scale.z<<' '<<e.radius<<'\n';
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
