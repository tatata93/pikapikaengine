#include "pikapika/world_static_mesh_session_source_wire.hpp"
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <iterator>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {
namespace w=pikapika::world_static_mesh_session_source_wire;
namespace s=pikapika::world_static_mesh_session;
struct Case {std::string name;std::vector<double> f;std::vector<std::uint32_t> u;bool upward{};};
void need(bool ok,const char* message) {if(!ok)throw std::runtime_error(message);}
std::uint64_t bits(double v) {return std::bit_cast<std::uint64_t>(v);}
void id(std::vector<std::uint32_t>& u,std::size_t offset,std::uint64_t value) {u[offset]=static_cast<std::uint32_t>(value);u[offset+1]=static_cast<std::uint32_t>(value>>32);}
Case base(std::string name,unsigned bodies,unsigned planes) {
    Case c{std::move(name),{-0.,-9.,0.,.25,-0.,1./120.},{bodies,planes,4,17,0}};
    for(unsigned i=0;i<bodies;++i) {
        const auto a=c.u.size();c.u.resize(a+3);id(c.u,a,1000-3*i);c.u[a+2]=i%2;
        const double j=static_cast<double>(i)/16;
        const double values[]{2+j,.5+j,11+j,12+j,13+j,21+j,22+j,-0.,31+j,32+j,33+j,34+j,
            41+j,42+j,43+j,51+j,52+j,53+j,61+j,-0.,63+j,71+j,72+j,73+j,81+j,91+j};
        c.f.insert(c.f.end(),std::begin(values),std::end(values));
    }
    for(unsigned i=0;i<planes;++i) {
        const auto a=c.u.size();c.u.resize(a+2);id(c.u,a,i+1);
        const double values[]{-0.,1.,0.,i==0?-0.:static_cast<double>(i)/8,0.5,0.25};c.f.insert(c.f.end(),std::begin(values),std::end(values));
    }
    return c;
}
std::vector<Case> cases() {
    std::vector<Case> out{base("empty",0,0),base("raw-body",1,0),base("ordered-planes-raw-body-order",2,1),base("simultaneous-maximum",8,16)};
    auto c=base("full64-body-ids-and-ticks",3,1);id(c.u,3,std::numeric_limits<std::uint64_t>::max());id(c.u,5,std::numeric_limits<std::uint64_t>::max());id(c.u,8,0);id(c.u,11,1);out.push_back(c);
    c=base("raw-model-invalid-body-and-margin",1,1);c.f[4]=-1;c.f[6]=-2;out.push_back(c);
    c=base("deferred-invalid-clock",1,0);c.f[5]=0;c.u[2]=0;out.push_back(c);
    c=base("raw-subnormal",1,0);c.f[6+18]=std::numeric_limits<double>::denorm_min();out.push_back(c);
    c=base("nonfinite-body",1,1);c.f[6]=std::bit_cast<double>(0x7ff8000000001234ULL);out.push_back(c);
    c=base("nonfinite-header",1,0);c.f[0]=-std::numeric_limits<double>::infinity();out.push_back(c);
    c=base("short-floats",1,0);c.f.pop_back();out.push_back(c);
    c=base("extra-floats",1,0);c.f.push_back(0);out.push_back(c);
    c=base("short-word-header",0,0);c.u.resize(4);out.push_back(c);
    c=base("extra-words",1,0);c.u.push_back(0);out.push_back(c);
    c=base("too-many-bodies",0,0);c.u[0]=9;out.push_back(c);
    c=base("too-many-planes",0,0);c.u[1]=17;out.push_back(c);
    c=base("static-flag",1,0);c.u[7]=2;out.push_back(c);
    c=base("zero-plane-id",0,1);id(c.u,5,0);out.push_back(c);
    c=base("wide-plane-id",0,1);id(c.u,5,9007199254740992ULL);out.push_back(c);
    c=base("full64-plane-id",0,1);id(c.u,5,std::numeric_limits<std::uint64_t>::max());out.push_back(c);
    c=base("plane-order",0,2);id(c.u,5,2);id(c.u,7,1);out.push_back(c);
    c=base("duplicate-plane",0,2);id(c.u,7,1);out.push_back(c);
    c=base("plane-normal",0,1);c.f[7]=2;out.push_back(c);
    c=base("plane-offset",0,1);c.f[9]=1000000000001.;out.push_back(c);
    c=base("plane-restitution",0,1);c.f[10]=2;out.push_back(c);
    c=base("plane-friction",0,1);c.f[11]=11;out.push_back(c);
    c=base("actual-upward-environment",1,1);c.upward=true;out.push_back(c);
    return out;
}
template<class Values> void integers(const Values& values) {std::cout<<'[';bool comma=false;for(auto v:values) {if(comma) {std::cout<<',';}comma=true;std::cout<<v;}std::cout<<']';}
void vector_bits(pikapika::Vec3 v) {integers(std::array<std::uint64_t,3>{bits(v.x),bits(v.y),bits(v.z)});}
void body_json(const pikapika::dynamics::RigidBody& b) {
    std::cout<<"{\"id\":"<<b.id<<",\"static\":"<<(b.is_static?"true":"false")<<",\"massBits\":"<<bits(b.mass)<<",\"radiusBits\":"<<bits(b.radius)<<",\"inertiaBits\":";vector_bits(b.inertia_diagonal);
    std::cout<<",\"positionBits\":";vector_bits(b.position);std::cout<<",\"orientationBits\":";integers(std::array<std::uint64_t,4>{bits(b.orientation.x),bits(b.orientation.y),bits(b.orientation.z),bits(b.orientation.w)});
    std::cout<<",\"velocityBits\":";vector_bits(b.velocity);std::cout<<",\"angularMomentumBits\":";vector_bits(b.angular_momentum);std::cout<<",\"forceBits\":";vector_bits(b.force);std::cout<<",\"torqueBits\":";vector_bits(b.torque);
    std::cout<<",\"restitutionBits\":"<<bits(b.material.restitution)<<",\"frictionBits\":"<<bits(b.material.friction)<<'}';
}
void source_json(const w::PlainSource& source) {
    std::cout<<"{\"gravityBits\":";vector_bits(source.world.gravity);std::cout<<",\"timeBits\":"<<bits(source.progress.time)<<",\"ticks\":"<<source.progress.ticks<<",\"marginBits\":"<<bits(source.guard.contact_margin)<<",\"stepBits\":"<<bits(source.clock.step_seconds)<<",\"maxAttempts\":"<<source.clock.max_attempts_per_pump<<",\"bodies\":[";
    bool comma=false;for(const auto& body:source.world.bodies()) {if(comma) {std::cout<<',';}comma=true;body_json(body);}std::cout<<"],\"planes\":[";comma=false;
    for(const auto& p:source.world.planes()) {if(comma) {std::cout<<',';}comma=true;std::cout<<"{\"id\":"<<p.id<<",\"normalBits\":";vector_bits(p.normal);std::cout<<",\"offsetBits\":"<<bits(p.offset)<<",\"restitutionBits\":"<<bits(p.material.restitution)<<",\"frictionBits\":"<<bits(p.material.friction)<<'}';}
    std::cout<<"]}";
}
void lifetime() {
    auto c=base("lifetime",2,1);auto decoded=w::decode(c.f,c.u);need(decoded.status==w::Status::ok&&decoded.source,"Decode for lifetime failed");
    const auto x=bits(decoded.source->world.bodies()[0].position.x);c.f[6+5]=-123;c.u[5]=99;
    need(bits(decoded.source->world.bodies()[0].position.x)==x&&decoded.source->world.bodies()[0].id==1000,"Decoded source aliases caller exchange");
    s::Registry registry;const auto made=registry.create(decoded.source->world,{},decoded.source->guard,decoded.source->progress,decoded.source->clock);need(made.status==s::Status::ok,"Actual owner copy failed");
    auto old=registry.read(made.token);need(old.status==s::Status::ok&&old.snapshot,"Actual owner read failed");decoded.source->world.find_body(1000)->position.x=999;decoded.source.reset();
    auto after=registry.read(made.token);need(after.snapshot&&bits(after.snapshot->world.bodies()[0].position.x)==x&&after.snapshot->world.bodies()[1].id==997,"Actual owner lost source bits/order/lifetime");
    need(registry.destroy(made.token)==s::Status::ok&&bits(old.snapshot->world.bodies()[0].position.x)==x,"Actual old read did not survive owner destruction");
    auto invalid=base("clock",1,0);invalid.f[5]=0;auto raw=w::decode(invalid.f,invalid.u);need(raw.source&&registry.create(raw.source->world,{},raw.source->guard,raw.source->progress,raw.source->clock).status==s::Status::invalid_settings,"Wire silently repaired or conflated owner clock refusal");
}
void fixtures() {
    auto all=cases();std::cout<<"{\"schema\":1,\"kind\":\"plain-session-source-wire-fixtures\",\"version\":"<<w::version<<",\"rows\":[";bool comma=false;
    for(const auto& c:all) {
        if(comma) {std::cout<<',';}
        comma=true;std::vector<std::uint64_t> fb;for(auto value:c.f)fb.push_back(bits(value));
        const auto prior=std::fegetround();need(prior==FE_TONEAREST,"Fixture begins outside nearest environment");if(c.upward)need(std::fesetround(FE_UPWARD)==0,"Cannot set actual upward environment");
        const auto observed=std::fegetround();auto result=w::decode(c.f,c.u);need(std::fesetround(prior)==0,"Cannot restore actual environment");need(observed==(c.upward?FE_UPWARD:FE_TONEAREST),"Actual environment observation differs");
        std::cout<<"{\"name\":\""<<c.name<<"\",\"floatBits\":";integers(fb);std::cout<<",\"words\":";integers(c.u);std::cout<<",\"actualEnvironment\":\""<<(observed==FE_UPWARD?"upward":"nearest")<<"\",\"status\":"<<static_cast<unsigned>(result.status)<<",\"part\":"<<static_cast<unsigned>(result.part)<<",\"index\":";
        if(result.index)std::cout<<*result.index;else std::cout<<"null";std::cout<<",\"source\":";if(result.source)source_json(*result.source);else std::cout<<"null";std::cout<<'}';
        for(std::size_t i=0;i<c.f.size();++i)need(bits(c.f[i])==fb[i],"Decoder modified source float exchange");
    }
    std::cout<<"],\"actualRows\":"<<all.size()<<"}\n";
}
}
int main(int argc,char** argv) {
    try {const std::string_view mode=argc==2?argv[1]:"--run";if(mode=="--fixtures")fixtures();else {need(mode=="--run","Unknown mode");lifetime();std::cout<<"Plain source wire caller/decoded/actual owner/old read lifetime PASS. No model step or C ABI/WASM acceptance.\n";}return 0;}
    catch(const std::exception& error) {std::cerr<<error.what()<<'\n';return 1;}
}
