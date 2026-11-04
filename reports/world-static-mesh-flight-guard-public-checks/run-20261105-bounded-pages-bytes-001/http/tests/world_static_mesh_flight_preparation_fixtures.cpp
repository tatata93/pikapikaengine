#include "world_static_mesh_flight_preparation_support.hpp"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <ostream>
#include <stdexcept>
#include <utility>

namespace preparation_fixture {
namespace p=preparation;
namespace {
void number(std::ostream& o,double x){if(!std::isfinite(x)){throw std::runtime_error("Nonfinite fixture number");}if(x==0&&std::signbit(x)){o<<"-0";}else{o<<std::setprecision(std::numeric_limits<double>::max_digits10)<<x;}}
void vec(std::ostream& o,pikapika::Vec3 v){o<<'[';number(o,v.x);o<<',';number(o,v.y);o<<',';number(o,v.z);o<<']';}
void material(std::ostream& o,dynamics::Material v){o<<"{\"restitution\":";number(o,v.restitution);o<<",\"friction\":";number(o,v.friction);o<<'}';}
void body(std::ostream& o,const dynamics::RigidBody& b){
    o<<"{\"id\":"<<b.id<<",\"isStatic\":"<<(b.is_static?"true":"false")<<",\"mass\":";number(o,b.mass);o<<",\"inertiaDiagonal\":";vec(o,b.inertia_diagonal);o<<",\"radius\":";number(o,b.radius);
    o<<",\"position\":";vec(o,b.position);o<<",\"velocity\":";vec(o,b.velocity);o<<",\"angularMomentum\":";vec(o,b.angular_momentum);o<<",\"orientation\":[";number(o,b.orientation.x);o<<',';number(o,b.orientation.y);o<<',';number(o,b.orientation.z);o<<',';number(o,b.orientation.w);o<<']';
    o<<",\"force\":";vec(o,b.force);o<<",\"torque\":";vec(o,b.torque);o<<",\"material\":";material(o,b.material);o<<'}';
}
void plane(std::ostream& o,const dynamics::Plane& v){o<<"{\"id\":"<<v.id<<",\"normal\":";vec(o,v.normal);o<<",\"offset\":";number(o,v.offset);o<<",\"material\":";material(o,v.material);o<<'}';}
void mesh(std::ostream& o,const p::StaticMeshSource& m){o<<"{\"id\":"<<m.id<<",\"revision\":"<<m.revision<<",\"triangles\":[";for(std::size_t i=0;i<m.triangles.size();++i){if(i){o<<',';}const auto& t=m.triangles[i];o<<"{\"id\":"<<t.id<<",\"vertices\":[";for(std::size_t j=0;j<3;++j){if(j){o<<',';}vec(o,t.vertices[j]);}o<<"]}";}o<<"]}";}
template<class T,class Writer>void array(std::ostream& o,const std::vector<T>& v,Writer writer){o<<'[';for(std::size_t i=0;i<v.size();++i){if(i){o<<',';}writer(o,v[i]);}o<<']';}
void settings(std::ostream& o,const p::Settings& s){o<<"{\"maxBodies\":"<<s.max_bodies<<",\"maxPlanes\":"<<s.max_planes<<",\"maxMeshes\":"<<s.max_meshes<<",\"maxTotalFaces\":"<<s.max_total_faces<<",\"maxPairs\":"<<s.max_pairs<<'}';}
void full_input(std::ostream& o,const std::vector<dynamics::RigidBody>& b,const std::vector<dynamics::Plane>& planes,pikapika::Vec3 gravity,const std::vector<p::StaticMeshSource>& meshes,double h,const p::Settings& s){o<<"{\"bodies\":";array(o,b,body);o<<",\"planes\":";array(o,planes,plane);o<<",\"gravity\":";vec(o,gravity);o<<",\"meshes\":";array(o,meshes,mesh);o<<",\"horizon\":";number(o,h);o<<",\"settings\":";settings(o,s);o<<'}';}
template<class T>void optional_index(std::ostream& o,const std::optional<T>& v){if(v){o<<*v;}else{o<<"null";}}
const char* status(p::Status v){constexpr const char* n[]={"ready","invalid_input","budget_exceeded","unsupported_environment","numerical_failure"};return n[unsigned(v)];}
const char* reason(p::Reason v){constexpr const char* n[]={"none","settings","body_count","plane_count","mesh_count","total_face_count","body_budget","plane_budget","mesh_budget","face_budget","pair_budget","horizon","gravity","collider_id","duplicate_collider_id","body_invalid","plane_invalid","mesh_revision","mesh_face_count","face_id","duplicate_face_id","vertex_domain","allocation_failure","accounting_inconsistent","environment","unexpected_exception"};return n[unsigned(v)];}
const char* object_kind(p::ObjectKind v){constexpr const char* n[]={"settings","world","body","plane","mesh","face"};return n[unsigned(v)];}
const char* collider_kind(p::ColliderKind v){constexpr const char* n[]={"body","plane","mesh"};return n[unsigned(v)];}
const char* pair_kind(p::PairKind v){constexpr const char* n[]={"body_mesh","body_plane","body_body"};return n[unsigned(v)];}
void ref(std::ostream& o,const p::ColliderRef& r){o<<"{\"kind\":\""<<collider_kind(r.kind)<<"\",\"id\":"<<r.id<<",\"ordinal\":"<<r.ordinal<<",\"revision\":"<<r.revision<<'}';}
void pair(std::ostream& o,const p::Pair& v){o<<"{\"kind\":\""<<pair_kind(v.kind)<<"\",\"first\":";ref(o,v.first);o<<",\"second\":";ref(o,v.second);o<<'}';}
void inventory(std::ostream& o,const p::Inventory& v){const auto& e=v.excluded;o<<"{\"dynamicBodies\":"<<v.dynamic_bodies<<",\"staticBodies\":"<<v.static_bodies<<",\"totalFaces\":"<<v.total_faces<<",\"colliders\":"<<v.colliders<<",\"allPairs\":"<<v.all_pairs<<",\"excluded\":{\"bodyBody\":"<<e.body_body<<",\"bodyPlane\":"<<e.body_plane<<",\"bodyMesh\":"<<e.body_mesh<<",\"planePlane\":"<<e.plane_plane<<",\"planeMesh\":"<<e.plane_mesh<<",\"meshMesh\":"<<e.mesh_mesh<<",\"total\":"<<e.total<<"},\"pairs\":";array(o,v.pairs,pair);o<<'}';}
dynamics::RigidBody sphere(std::uint64_t id,bool fixed=false){auto b=dynamics::make_sphere(id,.25,2,{1,2,3},fixed);b.inertia_diagonal={2,3,4};return b;}
p::StaticMeshSource source(std::uint64_t id=301,std::size_t n=1){p::StaticMeshSource m;m.id=id;m.revision=7;for(std::size_t i=0;i<n;++i){m.triangles.push_back({static_cast<std::uint64_t>(11+i),{{{-0.,0,-0.},{4,0,0},{0,0,4}}}});}return m;}
void bad(Case& c,p::Reason reason_value,p::ObjectKind kind,std::optional<std::size_t> index={},std::optional<std::size_t> face_index={}){c.expected=p::Status::invalid_input;c.reason=reason_value;c.failure=p::FailureLocation{kind,index,face_index};}
void budget(Case& c,p::Reason reason_value){c.expected=p::Status::budget_exceeded;c.reason=reason_value;switch(reason_value){case p::Reason::body_budget:c.failure=p::FailureLocation{p::ObjectKind::body,c.settings.max_bodies,{}};break;case p::Reason::plane_budget:c.failure=p::FailureLocation{p::ObjectKind::plane,c.settings.max_planes,{}};break;case p::Reason::mesh_budget:c.failure=p::FailureLocation{p::ObjectKind::mesh,c.settings.max_meshes,{}};break;case p::Reason::face_budget:c.failure=p::FailureLocation{p::ObjectKind::mesh,0,{}};break;default:c.failure=p::FailureLocation{p::ObjectKind::settings,{},{}};break;}}
}
Case base_case(){Case c;c.name="single-dynamic";c.world.gravity={-0.,-9.80665,0};c.world.add_body(sphere(101));c.world.add_plane({201,{0,1,-0.},-0.,{.25,.75}});c.meshes.push_back(source());return c;}
std::vector<Case> cases(){
    std::vector<Case> out;auto add=[&](Case c){out.push_back(std::move(c));};Case c=base_case();add(c);
    c=base_case();c.name="full-body-and-raw-plane-bits";{auto& b=*c.world.find_body(101);b.mass=3;b.inertia_diagonal={2,3,4};b.radius=.375;b.position={-0.,0x1p39,-0.};b.velocity={-0.,.5,-.25};b.angular_momentum={.125,-.25,.5};b.orientation={-0.,-0.,1,-0.};b.force={-0.,2,-3};b.torque={4,-0.,6};b.material={-0.,.625};auto& pl=const_cast<dynamics::Plane&>(c.world.planes().front());pl.normal={-0.,std::nextafter(1.,2.),-0.};pl.offset=-0.;pl.material={-0.,.125};}add(c);
    c=base_case();c.name="mixed-static-dynamic-complete-pairs";c.world.add_body(sphere(17,true));c.world.add_body(sphere(401));c.world.add_plane({23,{0,1,0},1,{}});c.meshes.push_back(source(19,2));add(c);
    c=base_case();c.name="static-force-torque-are-original-data";{auto& b=*c.world.find_body(101);b.is_static=true;b.force={3,-0.,7};b.torque={-0.,5,9};}add(c);
    c=base_case();c.name="static-subnormal-original-velocity";{auto& b=*c.world.find_body(101);b.is_static=true;b.velocity={std::numeric_limits<double>::denorm_min(),-0.,0};b.angular_momentum={-0.,0,std::numeric_limits<double>::denorm_min()};}add(c);
    c=base_case();c.name="empty-world-vacuous";c.world=dynamics::World{};c.world.gravity={-0.,0,-0.};add(c);
    c=base_case();c.name="planes-only-vacuous";c.world=dynamics::World{};c.world.add_plane({201,{0,1,0},0,{}});c.world.add_plane({202,{1,0,0},0,{}});add(c);
    c=base_case();c.name="no-planes-profile-zero";c.world=dynamics::World{};c.world.add_body(sphere(101));c.settings.max_planes=0;add(c);
    c=base_case();c.name="minimum-positive-horizon";c.horizon=std::numeric_limits<double>::denorm_min();add(c);
    c=base_case();c.name="maximum-horizon";c.horizon=.1;add(c);
    c=base_case();c.name="maximum-safe-identifiers";c.meshes.front().id=9007199254740991ULL;c.meshes.front().revision=9007199254740991ULL;c.meshes.front().triangles.front().id=9007199254740991ULL;add(c);
    c=base_case();c.name="face-id-equals-collider-id";c.meshes.front().triangles.front().id=101;add(c);
    c=base_case();c.name="face-id-reused-across-meshes";c.meshes.push_back(source(302));add(c);
    c=base_case();c.name="same-revision-distinct-geometry";c.meshes.push_back(source(302));c.meshes.back().triangles.front().vertices[1].x=8;add(c);
    c=base_case();c.name="fully-degenerate-face-structurally-ready";for(auto& v:c.meshes.front().triangles.front().vertices){v={-0.,1,-0.};}add(c);
    c=base_case();c.name="tiny-collinear-face-structurally-ready";c.meshes.front().triangles.front().vertices={pikapika::Vec3{},pikapika::Vec3{std::numeric_limits<double>::denorm_min(),0,0},pikapika::Vec3{2*std::numeric_limits<double>::denorm_min(),0,0}};add(c);
    c=base_case();c.name="maximum-vertex-domain";c.meshes.front().triangles.front().vertices[2]={1e12,-1e12,-0.};add(c);
    c=base_case();c.name="maximum-gravity-domain";c.world.gravity={1e9,-1e9,-0.};add(c);
    c=base_case();c.name="nonuniform-original-mesh-face-order";c.meshes={source(503,3),source(7,2),source(401)};std::reverse(c.meshes.front().triangles.begin(),c.meshes.front().triangles.end());add(c);
    c=base_case();c.name="body-order-mutated-after-world-sort";c.world.add_body(sphere(102));std::swap(*c.world.find_body(101),*c.world.find_body(102));add(c);
    c=base_case();c.name="full-8-16-4-64-capacity";c.world=dynamics::World{};for(std::uint64_t i=0;i<8;++i){c.world.add_body(sphere(101+i));}for(std::uint64_t i=0;i<16;++i){c.world.add_plane({201+i,{0,1,0},double(i),{}});}c.meshes.clear();for(std::uint64_t i=0;i<4;++i){c.meshes.push_back(source(301+i,16));}add(c);
    c.name="full-all-static-378-excluded";for(const auto& b:c.world.bodies()){c.world.find_body(b.id)->is_static=true;}add(c);
    c.name="full-mixed-3-static-5-dynamic";for(std::size_t i=3;i<c.world.bodies().size();++i){c.world.find_body(c.world.bodies()[i].id)->is_static=false;}add(c);
    c=base_case();c.name="pair-profile-exact";c.settings.max_pairs=2;add(c);
    c=base_case();c.name="pair-profile-too-small";c.settings.max_pairs=1;budget(c,p::Reason::pair_budget);add(c);
    c=base_case();c.name="body-profile-too-small";c.world.add_body(sphere(102));c.settings.max_bodies=1;budget(c,p::Reason::body_budget);add(c);
    c=base_case();c.name="plane-profile-too-small";c.settings.max_planes=0;budget(c,p::Reason::plane_budget);add(c);
    c=base_case();c.name="mesh-profile-too-small";c.meshes.push_back(source(302));c.settings.max_meshes=1;budget(c,p::Reason::mesh_budget);add(c);
    c=base_case();c.name="face-profile-too-small";c.meshes.front()=source(301,2);c.settings.max_total_faces=1;budget(c,p::Reason::face_budget);add(c);
    for(unsigned field=0;field<5;++field){for(unsigned side=0;side<2;++side){c=base_case();c.name="invalid-profile-"+std::to_string(field)+(side?"-high":"-zero");std::size_t* target=nullptr;std::size_t cap=0;switch(field){case 0:target=&c.settings.max_bodies;cap=8;break;case 1:target=&c.settings.max_planes;cap=16;break;case 2:target=&c.settings.max_meshes;cap=4;break;case 3:target=&c.settings.max_total_faces;cap=64;break;default:target=&c.settings.max_pairs;cap=256;break;}if(field==1&&!side){continue;}*target=side?cap+1:0;bad(c,p::Reason::settings,p::ObjectKind::settings);add(c);}}
    for(unsigned which=0;which<3;++which){c=base_case();c.name="invalid-horizon-"+std::to_string(which);c.horizon=which==0?-0.:which==1?-.01:std::nextafter(.1,1.);bad(c,p::Reason::horizon,p::ObjectKind::world);add(c);}
    c=base_case();c.name="invalid-gravity-domain";c.world.gravity.z=std::nextafter(1e9,2e9);bad(c,p::Reason::gravity,p::ObjectKind::world);add(c);
    c=base_case();c.name="nine-bodies-hard-rejection";for(std::uint64_t i=102;i<110;++i){c.world.add_body(sphere(i));}bad(c,p::Reason::body_count,p::ObjectKind::body,8);add(c);
    c=base_case();c.name="seventeen-planes-hard-rejection";for(std::uint64_t i=202;i<218;++i){c.world.add_plane({i,{0,1,0},0,{}});}bad(c,p::Reason::plane_count,p::ObjectKind::plane,16);add(c);
    c=base_case();c.name="no-mesh-hard-rejection";c.meshes.clear();bad(c,p::Reason::mesh_count,p::ObjectKind::mesh);add(c);
    c=base_case();c.name="five-meshes-hard-rejection";for(std::uint64_t i=302;i<306;++i){c.meshes.push_back(source(i));}bad(c,p::Reason::mesh_count,p::ObjectKind::mesh,4);add(c);
    c=base_case();c.name="sixty-five-faces-hard-rejection";c.meshes.front()=source(301,65);bad(c,p::Reason::total_face_count,p::ObjectKind::mesh,0);add(c);
    for(unsigned which=0;which<12;++which){c=base_case();c.name="invalid-mutable-body-"+std::to_string(which);auto& b=*c.world.find_body(101);switch(which){case 0:b.mass=0;break;case 1:b.inertia_diagonal.x=0;break;case 2:b.inertia_diagonal={1,1,3};break;case 3:b.radius=0;break;case 4:b.position.x=std::nextafter(1e12,2e12);break;case 5:b.velocity.y=std::nextafter(1e9,2e9);break;case 6:b.angular_momentum.z=std::nextafter(1e24,2e24);break;case 7:b.force.x=std::nextafter(1e24,2e24);break;case 8:b.torque.y=std::nextafter(1e24,2e24);break;case 9:b.orientation.w=2;break;case 10:b.material.friction=11;break;default:b.is_static=true;b.velocity.x=1;break;}bad(c,p::Reason::body_invalid,p::ObjectKind::body,0);add(c);}
    c=base_case();c.name="invalid-body-id-zero";c.world.find_body(101)->id=0;bad(c,p::Reason::collider_id,p::ObjectKind::body,0);add(c);
    c=base_case();c.name="invalid-body-id-over-safe";c.world.find_body(101)->id=9007199254740992ULL;bad(c,p::Reason::collider_id,p::ObjectKind::body,0);add(c);
    c=base_case();c.name="duplicate-mutable-body-id";c.world.add_body(sphere(102));c.world.find_body(102)->id=101;bad(c,p::Reason::duplicate_collider_id,p::ObjectKind::body,1);add(c);
    c=base_case();c.name="duplicate-body-plane-id";c.world.find_body(101)->id=201;bad(c,p::Reason::duplicate_collider_id,p::ObjectKind::plane,0);add(c);
    for(unsigned which=0;which<5;++which){c=base_case();c.name="invalid-captured-plane-"+std::to_string(which);auto& pl=const_cast<dynamics::Plane&>(c.world.planes().front());switch(which){case 0:pl.normal={0,0,0};break;case 1:pl.normal.y=2;break;case 2:pl.offset=std::nextafter(1e12,2e12);break;case 3:pl.material.restitution=2;break;default:pl.material.friction=-1;break;}bad(c,p::Reason::plane_invalid,p::ObjectKind::plane,0);add(c);}
    c=base_case();c.name="invalid-plane-id-zero";const_cast<dynamics::Plane&>(c.world.planes().front()).id=0;bad(c,p::Reason::collider_id,p::ObjectKind::plane,0);add(c);
    c=base_case();c.name="duplicate-captured-plane-id";c.world.add_plane({202,{0,1,0},0,{}});const_cast<dynamics::Plane&>(c.world.planes().back()).id=201;bad(c,p::Reason::duplicate_collider_id,p::ObjectKind::plane,1);add(c);
    c=base_case();c.name="invalid-mesh-id-zero";c.meshes.front().id=0;bad(c,p::Reason::collider_id,p::ObjectKind::mesh,0);add(c);
    c=base_case();c.name="duplicate-mesh-body-id";c.meshes.front().id=101;bad(c,p::Reason::duplicate_collider_id,p::ObjectKind::mesh,0);add(c);
    c=base_case();c.name="duplicate-mesh-plane-id";c.meshes.front().id=201;bad(c,p::Reason::duplicate_collider_id,p::ObjectKind::mesh,0);add(c);
    c=base_case();c.name="duplicate-mesh-id";c.meshes.push_back(source(301));bad(c,p::Reason::duplicate_collider_id,p::ObjectKind::mesh,1);add(c);
    for(unsigned which=0;which<2;++which){c=base_case();c.name="invalid-revision-"+std::to_string(which);c.meshes.front().revision=which?9007199254740992ULL:0;bad(c,p::Reason::mesh_revision,p::ObjectKind::mesh,0);add(c);}
    c=base_case();c.name="empty-mesh-face-list";c.meshes.front().triangles.clear();bad(c,p::Reason::mesh_face_count,p::ObjectKind::mesh,0);add(c);
    for(unsigned which=0;which<2;++which){c=base_case();c.name="invalid-face-id-"+std::to_string(which);c.meshes.front().triangles.front().id=which?9007199254740992ULL:0;bad(c,p::Reason::face_id,p::ObjectKind::face,0,0);add(c);}
    c=base_case();c.name="duplicate-face-id-within-mesh";c.meshes.front()=source(301,2);c.meshes.front().triangles.back().id=c.meshes.front().triangles.front().id;bad(c,p::Reason::duplicate_face_id,p::ObjectKind::face,0,1);add(c);
    c=base_case();c.name="invalid-last-mesh-last-face-vertex";c.meshes.push_back(source(302,2));c.meshes.back().triangles.back().vertices[2].z=std::nextafter(1e12,2e12);bad(c,p::Reason::vertex_domain,p::ObjectKind::face,1,1);add(c);
    c.name="invalid-source-precedes-smaller-profile";c.settings.max_meshes=1;add(c);
    c=base_case();c.name="invalid-body-precedes-smaller-profile";c.world.add_body(sphere(102));c.world.find_body(102)->mass=0;c.settings.max_bodies=1;bad(c,p::Reason::body_invalid,p::ObjectKind::body,1);add(c);
    c=base_case();c.name="hard-count-precedes-invalid-settings";c.meshes.clear();c.settings.max_pairs=0;bad(c,p::Reason::mesh_count,p::ObjectKind::mesh);add(c);
    return out;
}
void input_json(std::ostream& o,const Case& c){full_input(o,c.world.bodies(),c.world.planes(),c.world.gravity,c.meshes,c.horizon,c.settings);}
void snapshot_json(std::ostream& o,const p::Snapshot& s){full_input(o,s.bodies,s.planes,s.gravity,s.meshes,s.horizon,s.settings);}
void result_json(std::ostream& o,const p::Result& r){o<<"{\"status\":\""<<status(r.status)<<"\",\"reason\":\""<<reason(r.reason)<<"\",\"failure\":";if(r.failure){o<<"{\"kind\":\""<<object_kind(r.failure->kind)<<"\",\"index\":";optional_index(o,r.failure->index);o<<",\"faceIndex\":";optional_index(o,r.failure->face_index);o<<'}';}else{o<<"null";}constexpr const char* captures[]={"none","partial","complete"};o<<",\"capture\":\""<<captures[unsigned(r.capture)]<<"\",\"snapshot\":";if(r.snapshot){snapshot_json(o,*r.snapshot);}else{o<<"null";}o<<",\"inventory\":";if(r.inventory){inventory(o,*r.inventory);}else{o<<"null";}o<<'}';}
void emit_fixtures(std::ostream& o,const std::vector<Case>& corpus){o<<"{\"schema\":1,\"kind\":\"world-static-mesh-flight-preparation-fixtures\",\"fixtures\":[";for(std::size_t i=0;i<corpus.size();++i){if(i){o<<',';}const auto& c=corpus[i];o<<"{\"name\":\""<<c.name<<"\",\"input\":";input_json(o,c);o<<",\"result\":";result_json(o,p::prepare(c.world,c.meshes,c.horizon,c.settings));o<<'}';}o<<"]}\n";}
}
