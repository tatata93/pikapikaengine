#include "pikapika/dynamics.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <type_traits>
#include <vector>

using pikapika::Vec3;
namespace d=pikapika::dynamics;
static_assert(std::is_copy_constructible_v<d::World>);
static_assert(std::is_copy_assignable_v<d::World>);

void need(bool condition,const char* text) {
    if(!condition) {throw std::runtime_error(text);}
}
std::uint64_t bits(double x) noexcept {return std::bit_cast<std::uint64_t>(x);}
struct BodyBits {
    std::uint64_t id{};
    bool is_static{};
    std::array<std::uint64_t,26> values{};
    bool operator==(const BodyBits&) const=default;
};
struct PlaneBits {
    std::uint64_t id{};
    std::array<std::uint64_t,6> values{};
    bool operator==(const PlaneBits&) const=default;
};
struct Snapshot {
    std::array<std::uint64_t,3> gravity{};
    std::vector<BodyBits> bodies;
    std::vector<PlaneBits> planes;
    bool operator==(const Snapshot&) const=default;
};
Snapshot snapshot(const d::World& w) {
    Snapshot out;out.gravity={bits(w.gravity.x),bits(w.gravity.y),bits(w.gravity.z)};
    for(const auto& b:w.bodies()) {
        const std::array<double,26> values{b.mass,b.radius,
            b.inertia_diagonal.x,b.inertia_diagonal.y,b.inertia_diagonal.z,
            b.position.x,b.position.y,b.position.z,
            b.orientation.x,b.orientation.y,b.orientation.z,b.orientation.w,
            b.velocity.x,b.velocity.y,b.velocity.z,
            b.angular_momentum.x,b.angular_momentum.y,b.angular_momentum.z,
            b.force.x,b.force.y,b.force.z,b.torque.x,b.torque.y,b.torque.z,
            b.material.restitution,b.material.friction};
        BodyBits row;row.id=b.id;row.is_static=b.is_static;
        for(std::size_t i=0;i<values.size();++i) {row.values[i]=bits(values[i]);}
        out.bodies.push_back(row);
    }
    for(const auto& p:w.planes()) {
        out.planes.push_back({p.id,{bits(p.normal.x),bits(p.normal.y),bits(p.normal.z),
                                  bits(p.offset),bits(p.material.restitution),bits(p.material.friction)}});
    }
    return out;
}
struct Addresses {
    std::vector<const d::RigidBody*> bodies;
    std::vector<const d::Plane*> planes;
    bool operator==(const Addresses&) const=default;
};
Addresses addresses(const d::World& w) {
    Addresses out;
    for(const auto& b:w.bodies()) {out.bodies.push_back(&b);}
    for(const auto& p:w.planes()) {out.planes.push_back(&p);}
    return out;
}
void independent_addresses(const Addresses& first,const Addresses& second) {
    need(first.bodies.size()==second.bodies.size()&&first.planes.size()==second.planes.size(),"Copy address count changed");
    for(std::size_t i=0;i<first.bodies.size();++i) {need(first.bodies[i]!=second.bodies[i],"Body copy aliases source address");}
    for(std::size_t i=0;i<first.planes.size();++i) {need(first.planes[i]!=second.planes[i],"Plane copy aliases source address");}
}
void hex_json(std::ostream& out,std::uint64_t value) {
    out<<'"'<<std::hex<<std::setfill('0')<<std::setw(16)<<value<<std::dec<<'"';
}
template<std::size_t N> void array_json(std::ostream& out,const std::array<std::uint64_t,N>& values) {
    out<<'[';
    for(std::size_t i=0;i<N;++i) {if(i) {out<<',';}hex_json(out,values[i]);}
    out<<']';
}
void snapshot_json(std::ostream& out,const Snapshot& s) {
    out<<"{\"gravityBits\":";array_json(out,s.gravity);out<<",\"bodies\":[";
    for(std::size_t i=0;i<s.bodies.size();++i) {
        if(i) {out<<',';}
        const auto& b=s.bodies[i];out<<"{\"ordinal\":"<<i<<",\"id\":"<<b.id<<",\"isStatic\":"<<(b.is_static?"true":"false")<<",\"doubleBits\":";
        array_json(out,b.values);out<<'}';
    }
    out<<"],\"planes\":[";
    for(std::size_t i=0;i<s.planes.size();++i) {
        if(i) {out<<',';}
        out<<"{\"ordinal\":"<<i<<",\"id\":"<<s.planes[i].id<<",\"doubleBits\":";
        array_json(out,s.planes[i].values);out<<'}';
    }
    out<<"]}";
}
std::size_t negative_zeros(const Snapshot& s) {
    std::size_t count=0;
    const auto add=[&](auto values) {for(auto value:values) {if(value==0x8000000000000000ULL) {++count;}}};
    add(s.gravity);
    for(const auto& b:s.bodies) {add(b.values);}
    for(const auto& p:s.planes) {add(p.values);}
    return count;
}
int main() {
    try {
        d::World world;world.gravity={-0.0,-1.25,0.0};
        d::RigidBody first;first.id=101;first.mass=2;first.radius=.5;first.inertia_diagonal={1,2,3};
        first.position={-0.0,2,0.0};first.velocity={.5,-0.0,-.25};first.angular_momentum={-.125,.25,-0.0};
        first.orientation={-0.0,0.0,-0.0,1};first.force={3,-0.0,4};first.torque={-0.0,.25,-.5};first.material={-0.0,.625};
        d::RigidBody second=first;second.id=202;second.mass=3;second.radius=.25;second.inertia_diagonal={2,2,2};
        second.position={4,3,-0.0};second.velocity={-0.0,.25,.5};second.force={-0.0,5,-6};second.torque={.125,-0.0,.25};
        d::RigidBody fixed=first;fixed.id=303;fixed.is_static=true;fixed.position={8,-0.0,1};
        fixed.velocity={-0.0,0,-0.0};fixed.angular_momentum={0,-0.0,0};
        // Deliberately unsorted insertion: capture the actual public API order.
        world.add_body(fixed);world.add_body(first);world.add_body(second);
        world.add_plane({505,{-0.0,1.0+0x1p-30,0.0},-0.0,{-0.0,.75}});
        world.add_plane({404,{0.0,-1.0,-0.0},-8.0,{.125,-0.0}});
        const auto before=snapshot(world);const auto locations=addresses(world);
        need(before.bodies.size()==3&&before.bodies[0].id==101&&before.bodies[1].id==202&&before.bodies[2].id==303,"Unexpected actual body order");
        need(before.planes[0].id==404&&before.planes[1].id==505,"Unexpected actual plane order");
        d::World copy(world);const auto copied=snapshot(copy);
        need(copied==before,"Copy constructor changed original fields/order/bits");
        independent_addresses(locations,addresses(copy));
        d::World assigned;assigned.add_body(d::make_sphere(999,.25,1,{0,8,0}));assigned=world;
        const auto assignment=snapshot(assigned);
        need(assignment==before,"Copy assignment changed original fields/order/bits");
        independent_addresses(locations,addresses(assigned));independent_addresses(addresses(copy),addresses(assigned));
        for(std::size_t i=0;i<world.bodies().size();++i) {
            need(world.find_body(world.bodies()[i].id)==locations.bodies[i],"Source find_body does not match ordinal/address");
        }
        copy.find_body(101)->force={11,-0.0,-13};copy.find_body(101)->torque={-0.0,17,19};
        const auto changed=snapshot(copy);
        need(changed!=before&&snapshot(world)==before&&addresses(world)==locations,"Copy load mutation changed original");
        const double raw_nan=std::bit_cast<double>(0x7ff8000000001234ULL);
        d::RigidBody bad=first;bad.id=606;bad.force.x=raw_nan;
        bool add_rejected=false;
        try {world.add_body(bad);}catch(const std::runtime_error&) {add_rejected=true;}
        need(add_rejected&&snapshot(world)==before&&addresses(world)==locations,"Invalid add_body accepted or changed original");
        // Legal mutable field access can create an INVALID physics state; it is
        // not accepted through add_body/validate and is never propagated here.
        d::World invalid(world);invalid.find_body(101)->force.x=raw_nan;
        invalid.find_body(202)->force.y=0x1p100;
        const auto invalid_before=snapshot(invalid);const auto invalid_locations=addresses(invalid);
        std::size_t validate_rejected=0;
        for(const auto id:{101ULL,202ULL}) {
            try {invalid.find_body(id)->validate();}catch(const std::runtime_error&) {++validate_rejected;}
        }
        need(validate_rejected==2,"Invalid raw forces were not rejected by validate");
        d::World invalid_copy(invalid);const auto invalid_copied=snapshot(invalid_copy);
        need(invalid_before==invalid_copied,"Copy repaired/dropped an invalid raw force or NaN payload");
        independent_addresses(invalid_locations,addresses(invalid_copy));
        invalid_copy.find_body(101)->force={0.0,-0.0,0.0};
        need(snapshot(invalid)==invalid_before&&addresses(invalid)==invalid_locations,"Invalid copy edit leaked into source");
        const auto after=snapshot(world);
        need(after==before&&addresses(world)==locations,"Source valid World changed during copy probe");
        need(negative_zeros(before)>0,"Signed-zero source not exercised");
        std::ostringstream out;out.imbue(std::locale::classic());
        out<<"{\"schema\":1,\"kind\":\"world-copy-preparation\",\"status\":\"PASS\",\"compilerMSVC\":"<<_MSC_VER
           <<",\"scope\":\"Finite copy preparation only; no transaction, flight query, propagation, GNU or full artifact acceptance.\","
           <<"\"bodyDoubleFields\":[\"mass\",\"radius\",\"inertia.x\",\"inertia.y\",\"inertia.z\",\"position.x\",\"position.y\",\"position.z\",\"orientation.x\",\"orientation.y\",\"orientation.z\",\"orientation.w\",\"velocity.x\",\"velocity.y\",\"velocity.z\",\"angularMomentum.x\",\"angularMomentum.y\",\"angularMomentum.z\",\"force.x\",\"force.y\",\"force.z\",\"torque.x\",\"torque.y\",\"torque.z\",\"restitution\",\"friction\"],"
           <<"\"planeDoubleFields\":[\"normal.x\",\"normal.y\",\"normal.z\",\"offset\",\"restitution\",\"friction\"],"
           <<"\"before\":";snapshot_json(out,before);
        out<<",\"copyBeforeEdit\":";snapshot_json(out,copied);
        out<<",\"copyAfterLoadEdit\":";snapshot_json(out,changed);
        out<<",\"assignment\":";snapshot_json(out,assignment);
        out<<",\"after\":";snapshot_json(out,after);
        out<<",\"invalidBefore\":";snapshot_json(out,invalid_before);
        out<<",\"invalidCopy\":";snapshot_json(out,invalid_copied);
        out<<",\"observations\":{\"copyConstructed\":true,\"copyAssigned\":true,\"originalAllBitsUnchanged\":true,\"originalAllAddressesStable\":true,\"copyBodyAddressesDistinct\":true,\"copyPlaneAddressesDistinct\":true,\"findBodyMatchesOrdinal\":true,\"copyLoadEditIsolated\":true,\"invalidAddRejected\":true,\"invalidRawMutableAccessPossible\":true,\"invalidRawValidateRejected\":"<<validate_rejected
           <<",\"invalidRawCopyBitsPreserved\":true,\"negativeZeroValuesInOriginal\":"<<negative_zeros(before)
           <<",\"flightQueryCalls\":0,\"propagationCalls\":0}}\n";
        const auto text=out.str();need(text.size()<=262144,"Probe JSON budget exceeded");
        std::cout<<text;return std::cout?0:1;
    }catch(const std::exception& error) {
        std::cerr<<error.what()<<'\n';return 1;
    }
}
