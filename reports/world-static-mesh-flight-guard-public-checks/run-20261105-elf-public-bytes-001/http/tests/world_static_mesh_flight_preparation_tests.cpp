#include "world_static_mesh_flight_preparation_support.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <type_traits>
#include <utility>

namespace {
namespace f=preparation_fixture;
namespace p=f::preparation;
namespace d=f::dynamics;
void require(bool condition,const std::string& message){if(!condition){throw std::runtime_error(message);}}
std::string input_text(const f::Case& c){std::ostringstream o;f::input_json(o,c);return o.str();}
std::string snapshot_text(const p::Snapshot& s){std::ostringstream o;f::snapshot_json(o,s);return o.str();}
std::string result_text(const p::Result& r){std::ostringstream o;f::result_json(o,r);return o.str();}
using Key=std::tuple<std::uint64_t,std::uint64_t,unsigned>;
Key key(const p::Pair& x){return {std::min(x.first.id,x.second.id),std::max(x.first.id,x.second.id),unsigned(x.kind)};}
struct Object {p::ColliderRef ref;bool dynamic;};
bool ref_equal(const p::ColliderRef& a,const p::ColliderRef& b){return a.kind==b.kind&&a.id==b.id&&a.ordinal==b.ordinal&&a.revision==b.revision;}
void inventory_oracle(const p::Snapshot& s,const p::Inventory& inventory){
    // Independent unordered all-collider combinations, not the implementation's
    // dynamic-body x each collection traversal or closed-form pair generation.
    std::vector<Object> objects;std::size_t dynamics=0,statics=0,faces=0;
    for(std::size_t i=0;i<s.bodies.size();++i){const auto& b=s.bodies[i];objects.push_back({{p::ColliderKind::body,b.id,i,0},!b.is_static});if(b.is_static){++statics;}else{++dynamics;}}
    for(std::size_t i=0;i<s.planes.size();++i){objects.push_back({{p::ColliderKind::plane,s.planes[i].id,i,0},false});}
    for(std::size_t i=0;i<s.meshes.size();++i){objects.push_back({{p::ColliderKind::mesh,s.meshes[i].id,i,s.meshes[i].revision},false});faces+=s.meshes[i].triangles.size();}
    std::vector<p::Pair> needed;std::array<std::size_t,6> excluded{};std::size_t all=0;
    for(std::size_t i=0;i<objects.size();++i){for(std::size_t j=i+1;j<objects.size();++j){++all;auto a=objects[i],b=objects[j];if(a.ref.kind>b.ref.kind){std::swap(a,b);}if(a.dynamic||b.dynamic){
        require(a.ref.kind==p::ColliderKind::body,"Required pair must include a body");p::Pair pair;pair.first=a.ref;pair.second=b.ref;
        if(b.ref.kind==p::ColliderKind::body){pair.kind=p::PairKind::body_body;if(pair.first.id>pair.second.id){std::swap(pair.first,pair.second);}}
        else{pair.kind=b.ref.kind==p::ColliderKind::plane?p::PairKind::body_plane:p::PairKind::body_mesh;}needed.push_back(pair);
    }else{const auto ak=a.ref.kind,bk=b.ref.kind;const std::size_t category=ak==p::ColliderKind::body?(bk==p::ColliderKind::body?0:bk==p::ColliderKind::plane?1:2):ak==p::ColliderKind::plane?(bk==p::ColliderKind::plane?3:4):5;++excluded[category];}}}
    std::sort(needed.begin(),needed.end(),[](const auto& a,const auto& b){return key(a)<key(b);});
    require(inventory.dynamic_bodies==dynamics&&inventory.static_bodies==statics,"Body classification count");
    require(inventory.total_faces==faces&&inventory.colliders==objects.size()&&inventory.all_pairs==all,"Original collider/face/all-pair counts");
    const auto& e=inventory.excluded;const std::array<std::size_t,6> actual{e.body_body,e.body_plane,e.body_mesh,e.plane_plane,e.plane_mesh,e.mesh_mesh};require(actual==excluded,"All six static-only pair categories");
    std::size_t total=0;for(auto count:excluded){total+=count;}require(e.total==total&&needed.size()+total==all,"Required plus excluded closes whole collider matrix");
    require(inventory.pairs.size()==needed.size(),"No required pair truncated or invented");std::set<Key> unique;
    for(std::size_t i=0;i<needed.size();++i){const auto& a=inventory.pairs[i];const auto& b=needed[i];require(a.kind==b.kind&&ref_equal(a.first,b.first)&&ref_equal(a.second,b.second),"Sorted typed key/original ordinal/revision mismatch");require(unique.insert(key(a)).second,"Duplicate required key");}
}
void check_case(const f::Case& c){
    const auto before=input_text(c);std::vector<const d::RigidBody*> pointers;for(const auto& b:c.world.bodies()){pointers.push_back(&b);}const auto result=p::prepare(c.world,c.meshes,c.horizon,c.settings);
    require(result.status==c.expected,c.name+": status");require(result.reason==c.reason,c.name+": reason");
    require(input_text(c)==before,c.name+": full World/source/settings bits or loads changed");for(std::size_t i=0;i<pointers.size();++i){require(pointers[i]==&c.world.bodies()[i],c.name+": body pointer moved");}
    if(result.capture==p::CaptureState::complete){require(result.snapshot.has_value(),c.name+": complete snapshot missing");require(snapshot_text(*result.snapshot)==before,c.name+": snapshot not exact full original input");}
    else{require(result.capture==p::CaptureState::none&&!result.snapshot,c.name+": unexplained partial capture without injected allocation fault");}
    const bool hard=c.reason==p::Reason::body_count||c.reason==p::Reason::plane_count||c.reason==p::Reason::mesh_count||c.reason==p::Reason::total_face_count;
    require(result.capture==(hard?p::CaptureState::none:p::CaptureState::complete),c.name+": hard preflight/capture boundary");
    if(c.failure){require(result.failure.has_value(),c.name+": failure location missing");require(result.failure->kind==c.failure->kind&&result.failure->index==c.failure->index&&result.failure->face_index==c.failure->face_index,c.name+": typed first failure location");}
    if(result.status==p::Status::ready){require(!result.failure&&result.inventory&&result.snapshot,c.name+": ready publication");inventory_oracle(*result.snapshot,*result.inventory);}
    else{require(!result.inventory&&result.failure,c.name+": invalid/budget result must not publish partial inventory");}
}
template<class T>concept HasCandidate=requires(T v){v.candidate;};
template<class T>concept HasTube=requires(T v){v.tube;};
template<class T>concept HasWork=requires(T v){v.work;};
static_assert(!HasCandidate<p::Result>&&!HasTube<p::Result>&&!HasWork<p::Result>);
static_assert(std::is_nothrow_move_constructible_v<p::Result>);

void ownership(){
    auto c=f::base_case();auto first=p::prepare(c.world,c.meshes,c.horizon,c.settings);auto second=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(first.snapshot&&second.snapshot&&first.inventory&&second.inventory,"Ownership ready");const auto frozen=result_text(first),other=result_text(second);
    require(first.snapshot->bodies.data()!=second.snapshot->bodies.data()&&first.snapshot->planes.data()!=c.world.planes().data(),"Independent body/plane arrays");
    require(first.snapshot->meshes.data()!=c.meshes.data()&&first.snapshot->meshes[0].triangles.data()!=c.meshes[0].triangles.data(),"Independent nested source vectors");
    require(first.inventory->pairs.data()!=second.inventory->pairs.data(),"Independent pair arrays");
    c.world.find_body(101)->force={9,8,7};c.world.gravity={7,8,9};c.meshes[0].revision=91;c.meshes[0].triangles[0].vertices[0].x=89;c.settings.max_pairs=1;c.horizon=.1;
    require(result_text(first)==frozen&&result_text(second)==other,"Caller mutation changed old result");
    first.snapshot->bodies[0].mass=17;first.snapshot->planes[0].normal.x=19;first.snapshot->meshes[0].triangles[0].vertices[0].y=23;first.inventory->pairs[0].first.id=29;require(result_text(second)==other,"Returned DTO mutation changed another result");
    auto after_destruction=[] {auto local=f::base_case();return p::prepare(local.world,local.meshes,local.horizon,local.settings);}();require(result_text(after_destruction)==other,"Result depends on destroyed input");
    auto invalid=f::base_case();invalid.world.find_body(101)->mass=0;auto diagnostic=p::prepare(invalid.world,invalid.meshes,invalid.horizon,invalid.settings);const auto original=result_text(diagnostic);invalid.world.find_body(101)->mass=1;invalid.meshes.clear();require(result_text(diagnostic)==original&&diagnostic.snapshot&&!diagnostic.inventory,"Invalid full snapshot also independently owned");
}
void source_permutations(){
    auto c=f::base_case();auto b=d::make_sphere(37,.25,1);c.world.add_body(b);c.world.add_plane({71,{1,0,0},0,{}});auto source=c.meshes.front();source.id=23;source.revision=13;c.meshes.push_back(source);auto first=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(first.inventory&&first.snapshot,"Permutation first ready");
    // Mutating legal nonconst underlying objects through their public const
    // accessor tests revalidation/order preservation, without private access.
    std::swap(*c.world.find_body(37),*c.world.find_body(101));auto& planes=const_cast<std::vector<d::Plane>&>(c.world.planes());std::reverse(planes.begin(),planes.end());std::reverse(c.meshes.begin(),c.meshes.end());
    auto second=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(second.inventory&&second.snapshot,"Permutation second ready");inventory_oracle(*first.snapshot,*first.inventory);inventory_oracle(*second.snapshot,*second.inventory);require(first.inventory->pairs.size()==second.inventory->pairs.size(),"Permutation pair count");bool changed=false;
    for(std::size_t i=0;i<first.inventory->pairs.size();++i){const auto& x=first.inventory->pairs[i];const auto& y=second.inventory->pairs[i];require(key(x)==key(y),"Source permutation changed stable keys");changed=changed||x.first.ordinal!=y.first.ordinal||x.second.ordinal!=y.second.ordinal;}require(changed,"Permutation actually changes original ordinal links");
}
void full_capacity(const std::vector<f::Case>& corpus){
    const auto found=std::find_if(corpus.begin(),corpus.end(),[](const auto& c){return c.name=="full-8-16-4-64-capacity";});require(found!=corpus.end(),"Capacity source exists");auto result=p::prepare(found->world,found->meshes,found->horizon,found->settings);require(result.inventory&&result.snapshot,"Capacity ready");const auto& v=*result.inventory;require(v.pairs.size()==188&&v.excluded.total==190&&v.all_pairs==378,"Exact 188+190=378 nonvacuous capacity");require(v.excluded.plane_plane==120&&v.excluded.plane_mesh==64&&v.excluded.mesh_mesh==6,"All static collider combinations counted");require(result.snapshot->meshes.back().triangles.back().id==26,"Last of all 64 faces retained");require(v.pairs.back().second.id==304,"Last sorted required mesh key retained");
    auto low=*found;low.settings.max_pairs=187;const auto failed=p::prepare(low.world,low.meshes,low.horizon,low.settings);require(failed.status==p::Status::budget_exceeded&&failed.reason==p::Reason::pair_budget&&!failed.inventory&&failed.snapshot&&failed.capture==p::CaptureState::complete,"188 pairs cannot publish truncated 187-slot inventory");
}
void nonfinite_native_only(){
    const double nan=std::numeric_limits<double>::quiet_NaN(),inf=std::numeric_limits<double>::infinity();
    auto c=f::base_case();c.horizon=nan;auto r=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(r.reason==p::Reason::horizon&&r.snapshot&&!r.inventory&&std::isnan(r.snapshot->horizon),"NaN H captured but not serialized");
    c=f::base_case();c.world.gravity.x=inf;r=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(r.reason==p::Reason::gravity&&r.snapshot&&!r.inventory&&std::isinf(r.snapshot->gravity.x),"Infinite gravity rejected with original capture");
    c=f::base_case();c.world.find_body(101)->force.y=nan;r=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(r.reason==p::Reason::body_invalid&&r.snapshot&&!r.inventory,"Nonfinite body rejected");
    c=f::base_case();const_cast<d::Plane&>(c.world.planes().front()).normal.x=nan;r=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(r.reason==p::Reason::plane_invalid&&r.snapshot&&!r.inventory,"Nonfinite raw plane rejected");
    c=f::base_case();c.meshes[0].triangles[0].vertices[0].z=inf;r=p::prepare(c.world,c.meshes,c.horizon,c.settings);require(r.reason==p::Reason::vertex_domain&&r.failure&&r.failure->face_index==0&&!r.inventory,"Nonfinite last-stage source rejected");
}
void environment_first(){
    auto c=f::base_case();c.settings.max_pairs=0;c.meshes.clear();const int original=std::fegetround();require(original==FE_TONEAREST,"Initial RN-even test environment");
    require(std::fesetround(FE_UPWARD)==0,"Can set unsupported rounding mode");const auto rejected=p::prepare(c.world,c.meshes,c.horizon,c.settings);const int after=std::fegetround();const int restored=std::fesetround(original);
    require(restored==0&&after==FE_UPWARD,"Preparation must not change caller FP control");require(rejected.status==p::Status::unsupported_environment&&rejected.reason==p::Reason::environment&&rejected.capture==p::CaptureState::none&&!rejected.snapshot&&!rejected.inventory,"Environment precedes counts/settings/capture");
    c=f::base_case();require(p::prepare(c.world,c.meshes,c.horizon,c.settings).status==p::Status::ready,"Recovery after unsupported environment");
}
void storage_observation(const std::vector<f::Case>& corpus){
    const auto found=std::find_if(corpus.begin(),corpus.end(),[](const auto& c){return c.name=="full-8-16-4-64-capacity";});require(found!=corpus.end(),"Storage source");const auto r=p::prepare(found->world,found->meshes,found->horizon,found->settings);require(r.snapshot&&r.inventory,"Storage ready");const auto& s=*r.snapshot;
    std::cout<<"{\"schema\":1,\"kind\":\"world-static-mesh-flight-preparation-storage\",\"scope\":\"sizeof and observed vector capacities only; excludes allocator overhead, temporary buffers, stack, RSS and heap guarantees\",\"sizes\":{\"result\":"<<sizeof(p::Result)<<",\"snapshot\":"<<sizeof(p::Snapshot)<<",\"inventory\":"<<sizeof(p::Inventory)<<",\"body\":"<<sizeof(d::RigidBody)<<",\"plane\":"<<sizeof(d::Plane)<<",\"mesh\":"<<sizeof(p::StaticMeshSource)<<",\"triangle\":"<<sizeof(pikapika::sphere_triangle::StaticTriangle)<<",\"pair\":"<<sizeof(p::Pair)<<",\"colliderRef\":"<<sizeof(p::ColliderRef)<<"},\"capacities\":{\"bodies\":"<<s.bodies.capacity()<<",\"planes\":"<<s.planes.capacity()<<",\"meshes\":"<<s.meshes.capacity()<<",\"pairs\":"<<r.inventory->pairs.capacity()<<",\"triangles\":[";for(std::size_t i=0;i<s.meshes.size();++i){if(i){std::cout<<',';}std::cout<<s.meshes[i].triangles.capacity();}std::cout<<"]}}\n";
}
}
int main(int argc,char** argv){
    try{const auto corpus=f::cases();if(argc==2&&std::string(argv[1])=="--fixtures"){f::emit_fixtures(std::cout,corpus);return 0;}if(argc==2&&std::string(argv[1])=="--storage"){storage_observation(corpus);return 0;}require(argc==1,"Usage: tests [--fixtures|--storage]");std::set<std::string> names;for(const auto& c:corpus){require(names.insert(c.name).second,"Duplicate fixture name");check_case(c);}
        ownership();source_permutations();full_capacity(corpus);nonfinite_native_only();environment_first();
        std::cout<<"World static mesh preparation: "<<corpus.size()+5<<" groups PASS; "<<corpus.size()<<" finite fixtures. All-pair ownership/preflight only; no numeric guard, propagation, candidate or World advance.\n";return 0;
    }catch(const std::exception& error){std::cerr<<"World static mesh preparation FAIL: "<<error.what()<<'\n';return 1;}
}
