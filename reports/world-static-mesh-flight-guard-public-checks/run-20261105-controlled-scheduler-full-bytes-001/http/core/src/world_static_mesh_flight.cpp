#include "pikapika/world_static_mesh_flight.hpp"
#include <algorithm>
#include <array>
#include <cmath>
#include <limits>
#include <new>
#include <stdexcept>
#include <type_traits>
#include <utility>

#if defined(__FAST_MATH__) || (defined(__FINITE_MATH_ONLY__) && __FINITE_MATH_ONLY__ > 0) || defined(_M_FP_FAST) || defined(_M_FP_CONTRACT)
#error World static mesh preparation requires strict floating point validation.
#endif
#if defined(_MSC_VER)
#pragma float_control(precise,on,push)
#pragma fenv_access(on)
#pragma fp_contract(off)
#elif defined(__clang__)
#pragma STDC FP_CONTRACT OFF
#endif

namespace pikapika::world_static_mesh_flight {
namespace {
constexpr std::uint64_t maximum_id=9007199254740991ULL;
struct Stop {
    Status status;
    Reason reason;
    FailureLocation location;
    const char* message;
};
FailureLocation location(ObjectKind kind,std::optional<std::size_t> index={},
                         std::optional<std::size_t> face={}) noexcept {
    return {kind,index,face};
}
void need(bool condition,Status status,Reason reason,FailureLocation where,const char* message) {
    if(!condition) {throw Stop{status,reason,where,message};}
}
void fail(Result& result,Status status,Reason reason,FailureLocation where,const char* message) noexcept {
    result.status=status;result.reason=reason;result.failure=where;result.inventory.reset();
    try {result.message=message;}catch(...) {result.message.clear();}
}
bool id_valid(std::uint64_t id) noexcept {return id>0&&id<=maximum_id;}
bool bounded(Vec3 value,double limit) noexcept {
    return std::isfinite(value.x)&&std::isfinite(value.y)&&std::isfinite(value.z)&&
        std::abs(value.x)<=limit&&std::abs(value.y)<=limit&&std::abs(value.z)<=limit;
}
bool material_valid(const dynamics::Material& material) noexcept {
    return std::isfinite(material.restitution)&&material.restitution>=0&&material.restitution<=1&&
        std::isfinite(material.friction)&&material.friction>=0&&material.friction<=10;
}
bool plane_valid(const dynamics::Plane& plane) noexcept {
    if(!std::isfinite(plane.normal.x)||!std::isfinite(plane.normal.y)||!std::isfinite(plane.normal.z)||
       !std::isfinite(plane.offset)||std::abs(plane.offset)>1e12||!material_valid(plane.material)) {return false;}
    // Existing World admission convention, NOT normalization or a geometry proof.
    const double squared=plane.normal.dot(plane.normal);
    return std::isfinite(squared)&&std::abs(squared-1)<1e-8;
}
bool profile_valid(const Settings& settings) noexcept {
    return settings.max_bodies>=1&&settings.max_bodies<=hard_max_bodies&&
        settings.max_planes<=hard_max_planes&&settings.max_meshes>=1&&settings.max_meshes<=hard_max_meshes&&
        settings.max_total_faces>=1&&settings.max_total_faces<=hard_max_faces&&
        settings.max_pairs>=1&&settings.max_pairs<=hard_max_pairs;
}
std::size_t sum(std::size_t a,std::size_t b) {
    need(b<=std::numeric_limits<std::size_t>::max()-a,Status::numerical_failure,
         Reason::accounting_inconsistent,location(ObjectKind::world),"Preparation count addition overflow");
    return a+b;
}
std::size_t product(std::size_t a,std::size_t b) {
    need(a==0||b<=std::numeric_limits<std::size_t>::max()/a,Status::numerical_failure,
         Reason::accounting_inconsistent,location(ObjectKind::world),"Preparation count multiplication overflow");
    return a*b;
}
std::size_t choose_two(std::size_t count) {return count<2?0:product(count,count-1)/2;}
ColliderRef body_ref(const Snapshot& snapshot,std::size_t index) noexcept {
    return {ColliderKind::body,snapshot.bodies[index].id,index,0};
}
ColliderRef plane_ref(const Snapshot& snapshot,std::size_t index) noexcept {
    return {ColliderKind::plane,snapshot.planes[index].id,index,0};
}
ColliderRef mesh_ref(const Snapshot& snapshot,std::size_t index) noexcept {
    return {ColliderKind::mesh,snapshot.meshes[index].id,index,snapshot.meshes[index].revision};
}
bool pair_less(const Pair& a,const Pair& b) noexcept {
    const auto a_low=std::min(a.first.id,a.second.id),b_low=std::min(b.first.id,b.second.id);
    if(a_low!=b_low) {return a_low<b_low;}
    const auto a_high=std::max(a.first.id,a.second.id),b_high=std::max(b.first.id,b.second.id);
    if(a_high!=b_high) {return a_high<b_high;}
    return static_cast<unsigned>(a.kind)<static_cast<unsigned>(b.kind);
}
}

Result prepare(const dynamics::World& world,std::span<const StaticMeshSource> sources,
               double horizon,const Settings& settings) noexcept {
    Result out;
    try {
        if(const char* issue=interval::environment_issue()) {
            fail(out,Status::unsupported_environment,Reason::environment,location(ObjectKind::world),issue);
            return out;
        }
        const auto& bodies=world.bodies();const auto& planes=world.planes();
        // Only these bounded-count inspections precede the owned capture.
        need(bodies.size()<=hard_max_bodies,Status::invalid_input,Reason::body_count,
             location(ObjectKind::body,hard_max_bodies),"World preparation body hard limit exceeded");
        need(planes.size()<=hard_max_planes,Status::invalid_input,Reason::plane_count,
             location(ObjectKind::plane,hard_max_planes),"World preparation plane hard limit exceeded");
        need(!sources.empty()&&sources.size()<=hard_max_meshes,Status::invalid_input,Reason::mesh_count,
             location(ObjectKind::mesh,sources.empty()?std::optional<std::size_t>{}:hard_max_meshes),"World preparation requires 1..4 static meshes");
        std::size_t total_faces=0;
        for(std::size_t i=0;i<sources.size();++i) {
            need(sources[i].triangles.size()<=hard_max_faces-total_faces,Status::invalid_input,Reason::total_face_count,
                 location(ObjectKind::mesh,i),"World preparation total face hard limit exceeded");
            total_faces+=sources[i].triangles.size();
        }

        out.snapshot.emplace();out.capture=CaptureState::partial;auto& snapshot=*out.snapshot;
        snapshot.gravity=world.gravity;snapshot.horizon=horizon;snapshot.settings=settings;
        out.failure=location(ObjectKind::body);snapshot.bodies.assign(bodies.begin(),bodies.end());
        out.failure=location(ObjectKind::plane);snapshot.planes.assign(planes.begin(),planes.end());
        out.failure=location(ObjectKind::mesh);snapshot.meshes.reserve(sources.size());
        for(std::size_t i=0;i<sources.size();++i) {
            out.failure=location(ObjectKind::mesh,i);
            StaticMeshSource copy;copy.id=sources[i].id;copy.revision=sources[i].revision;
            copy.triangles.assign(sources[i].triangles.begin(),sources[i].triangles.end());
            snapshot.meshes.push_back(std::move(copy));
        }
        out.capture=CaptureState::complete;out.failure.reset();
        // From this point every data read is from the isolated owned snapshot.
        const auto& s=snapshot.settings;
        need(profile_valid(s),Status::invalid_input,Reason::settings,location(ObjectKind::settings),"Invalid world preparation count profile");
        need(std::isfinite(snapshot.horizon)&&snapshot.horizon>0&&snapshot.horizon<=.1,Status::invalid_input,
             Reason::horizon,location(ObjectKind::world),"Preparation horizon must be in (0,.1] seconds");
        need(bounded(snapshot.gravity,1e9),Status::invalid_input,Reason::gravity,
             location(ObjectKind::world),"Preparation gravity outside finite domain");

        std::array<std::uint64_t,hard_max_bodies+hard_max_planes+hard_max_meshes> seen{};
        std::size_t seen_count=0;
        const auto collider=[&](std::uint64_t id,FailureLocation where) {
            need(id_valid(id),Status::invalid_input,Reason::collider_id,where,"Invalid preparation collider ID");
            for(std::size_t i=0;i<seen_count;++i) {
                need(seen[i]!=id,Status::invalid_input,Reason::duplicate_collider_id,where,"Duplicate preparation collider ID");
            }
            need(seen_count<seen.size(),Status::numerical_failure,Reason::accounting_inconsistent,
                 location(ObjectKind::world),"Preparation collider count inconsistent");
            seen[seen_count++]=id;
        };
        std::size_t dynamic_count=0,static_count=0;
        for(std::size_t i=0;i<snapshot.bodies.size();++i) {
            const auto& body=snapshot.bodies[i];const auto where=location(ObjectKind::body,i);collider(body.id,where);
            try {body.validate();}
            catch(const std::bad_alloc&) {throw;}
            catch(const std::exception&) {throw Stop{Status::invalid_input,Reason::body_invalid,where,"Invalid captured preparation body"};}
            if(body.is_static) {++static_count;}else {++dynamic_count;}
        }
        for(std::size_t i=0;i<snapshot.planes.size();++i) {
            const auto& plane=snapshot.planes[i];const auto where=location(ObjectKind::plane,i);collider(plane.id,where);
            need(plane_valid(plane),Status::invalid_input,Reason::plane_invalid,where,"Invalid captured raw preparation plane");
        }
        std::size_t captured_faces=0;
        for(std::size_t i=0;i<snapshot.meshes.size();++i) {
            const auto& mesh=snapshot.meshes[i];const auto where=location(ObjectKind::mesh,i);collider(mesh.id,where);
            need(id_valid(mesh.revision),Status::invalid_input,Reason::mesh_revision,where,"Invalid caller-declared mesh revision");
            need(!mesh.triangles.empty()&&mesh.triangles.size()<=hard_max_faces,Status::invalid_input,
                 Reason::mesh_face_count,where,"Each preparation mesh requires 1..64 faces");
            captured_faces=sum(captured_faces,mesh.triangles.size());
            for(std::size_t j=0;j<mesh.triangles.size();++j) {
                const auto& triangle=mesh.triangles[j];const auto face=location(ObjectKind::face,i,j);
                need(id_valid(triangle.id),Status::invalid_input,Reason::face_id,face,"Invalid mesh-local face ID");
                for(std::size_t previous=0;previous<j;++previous) {
                    need(mesh.triangles[previous].id!=triangle.id,Status::invalid_input,Reason::duplicate_face_id,face,"Duplicate face ID within preparation mesh");
                }
                for(const auto& vertex:triangle.vertices) {
                    need(bounded(vertex,1e12),Status::invalid_input,Reason::vertex_domain,face,"Preparation vertex outside finite world domain");
                }
            }
        }
        need(captured_faces==total_faces,Status::numerical_failure,Reason::accounting_inconsistent,
             location(ObjectKind::world),"Preparation captured face count inconsistent");
        need(snapshot.bodies.size()<=s.max_bodies,Status::budget_exceeded,Reason::body_budget,
             location(ObjectKind::body,s.max_bodies),"Preparation body profile exceeded");
        need(snapshot.planes.size()<=s.max_planes,Status::budget_exceeded,Reason::plane_budget,
             location(ObjectKind::plane,s.max_planes),"Preparation plane profile exceeded");
        need(snapshot.meshes.size()<=s.max_meshes,Status::budget_exceeded,Reason::mesh_budget,
             location(ObjectKind::mesh,s.max_meshes),"Preparation mesh profile exceeded");
        std::size_t cumulative=0;
        for(std::size_t i=0;i<snapshot.meshes.size();++i) {
            cumulative=sum(cumulative,snapshot.meshes[i].triangles.size());
            need(cumulative<=s.max_total_faces,Status::budget_exceeded,Reason::face_budget,
                 location(ObjectKind::mesh,i),"Preparation total face profile exceeded");
        }

        Inventory inventory;inventory.dynamic_bodies=dynamic_count;inventory.static_bodies=static_count;
        inventory.total_faces=captured_faces;inventory.colliders=seen_count;inventory.all_pairs=choose_two(seen_count);
        auto& excluded=inventory.excluded;const auto B=snapshot.bodies.size(),P=snapshot.planes.size(),M=snapshot.meshes.size();
        excluded.body_body=choose_two(static_count);excluded.body_plane=product(static_count,P);
        excluded.body_mesh=product(static_count,M);excluded.plane_plane=choose_two(P);
        excluded.plane_mesh=product(P,M);excluded.mesh_mesh=choose_two(M);
        excluded.total=sum(sum(sum(excluded.body_body,excluded.body_plane),sum(excluded.body_mesh,excluded.plane_plane)),sum(excluded.plane_mesh,excluded.mesh_mesh));
        const auto body_pairs=choose_two(B)-choose_two(static_count);
        const auto required=sum(sum(product(dynamic_count,M),product(dynamic_count,P)),body_pairs);
        need(sum(required,excluded.total)==inventory.all_pairs,Status::numerical_failure,Reason::accounting_inconsistent,
             location(ObjectKind::world),"Preparation required/excluded pair accounting inconsistent");
        need(required<=s.max_pairs,Status::budget_exceeded,Reason::pair_budget,
             location(ObjectKind::settings),"Preparation pair profile exceeded; no partial inventory");
        out.failure=location(ObjectKind::world);inventory.pairs.reserve(required);
        for(std::size_t i=0;i<B;++i) {
            if(!snapshot.bodies[i].is_static) {
                for(std::size_t j=0;j<M;++j) {inventory.pairs.push_back({PairKind::body_mesh,body_ref(snapshot,i),mesh_ref(snapshot,j)});}
                for(std::size_t j=0;j<P;++j) {inventory.pairs.push_back({PairKind::body_plane,body_ref(snapshot,i),plane_ref(snapshot,j)});}
            }
            for(std::size_t j=i+1;j<B;++j) {
                if(snapshot.bodies[i].is_static&&snapshot.bodies[j].is_static) {continue;}
                auto first=body_ref(snapshot,i),second=body_ref(snapshot,j);
                if(first.id>second.id) {std::swap(first,second);}
                inventory.pairs.push_back({PairKind::body_body,first,second});
            }
        }
        need(inventory.pairs.size()==required,Status::numerical_failure,Reason::accounting_inconsistent,
             location(ObjectKind::world),"Preparation inventory did not enumerate all required pairs");
        std::sort(inventory.pairs.begin(),inventory.pairs.end(),pair_less);
        static_assert(std::is_nothrow_move_assignable_v<std::optional<Inventory>>);
        out.inventory=std::move(inventory);out.failure.reset();out.status=Status::ready;out.reason=Reason::none;
    }catch(const Stop& error) {fail(out,error.status,error.reason,error.location,error.message);}
    catch(const std::bad_alloc&) {fail(out,Status::numerical_failure,Reason::allocation_failure,
                                     out.failure.value_or(location(ObjectKind::world)),"Preparation diagnostic allocation failed");}
    catch(const std::exception& error) {fail(out,Status::numerical_failure,Reason::unexpected_exception,
                                           out.failure.value_or(location(ObjectKind::world)),error.what());}
    catch(...) {fail(out,Status::numerical_failure,Reason::unexpected_exception,
                    out.failure.value_or(location(ObjectKind::world)),"Unknown preparation exception");}
    static_assert(std::is_nothrow_move_constructible_v<Result>);
    return out;
}
}
#if defined(_MSC_VER)
#pragma float_control(pop)
#endif
