#pragma once
#include "pikapika/dynamics.hpp"
#include "pikapika/sphere_triangle.hpp"
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::world_static_mesh_flight {
// Native preparation ONLY. No propagation, collision query, certification,
// candidate, World advance or force/torque consumption occurs in this API.
inline constexpr std::size_t hard_max_bodies=8,hard_max_planes=16;
inline constexpr std::size_t hard_max_meshes=4,hard_max_faces=64,hard_max_pairs=256;
struct StaticMeshSource {
    std::uint64_t id{},revision{}; // Both 1..2^53-1; revision is caller-declared.
    std::vector<sphere_triangle::StaticTriangle> triangles; // Static WORLD metres.
};
struct Settings {
    std::size_t max_bodies=hard_max_bodies,max_planes=hard_max_planes;
    std::size_t max_meshes=hard_max_meshes,max_total_faces=hard_max_faces;
    std::size_t max_pairs=hard_max_pairs;
};
enum class Status : unsigned {ready,invalid_input,budget_exceeded,unsupported_environment,numerical_failure};
enum class Reason : unsigned {
    none,settings,body_count,plane_count,mesh_count,total_face_count,
    body_budget,plane_budget,mesh_budget,face_budget,pair_budget,
    horizon,gravity,collider_id,duplicate_collider_id,body_invalid,plane_invalid,
    mesh_revision,mesh_face_count,face_id,duplicate_face_id,vertex_domain,
    allocation_failure,accounting_inconsistent,environment,unexpected_exception
};
enum class ObjectKind : unsigned {settings,world,body,plane,mesh,face};
struct FailureLocation {
    ObjectKind kind=ObjectKind::world;
    // Body/plane/mesh: ORIGINAL source ordinal. Face: mesh ordinal plus face_index.
    // Settings/world have neither index. Duplicates point to the second occurrence.
    std::optional<std::size_t> index,face_index;
};
enum class CaptureState : unsigned {none,partial,complete};
struct Snapshot {
    Vec3 gravity{};
    double horizon{}; // Original binary64 seconds, never a normalized parameter.
    Settings settings;
    std::vector<dynamics::RigidBody> bodies; // ALL original fields and order/bits.
    std::vector<dynamics::Plane> planes; // Raw n/offset/material/order/bits.
    std::vector<StaticMeshSource> meshes;
};
enum class ColliderKind : unsigned {body,plane,mesh};
struct ColliderRef {
    ColliderKind kind=ColliderKind::body;
    std::uint64_t id{};
    std::size_t ordinal{}; // Original vector ordinal in the owned Snapshot.
    std::uint64_t revision{}; // Mesh revision; ZERO for body/plane.
};
enum class PairKind : unsigned {body_mesh,body_plane,body_body};
struct Pair {
    PairKind kind=PairKind::body_mesh;
    // Body first for body_mesh/body_plane; ascending body IDs for body_body.
    ColliderRef first,second;
};
struct StaticOnlyCounts {
    std::size_t body_body{},body_plane{},body_mesh{};
    std::size_t plane_plane{},plane_mesh{},mesh_mesh{},total{};
};
struct Inventory {
    std::size_t dynamic_bodies{},static_bodies{},total_faces{},colliders{},all_pairs{};
    StaticOnlyCounts excluded;
    // ALL dynamic-motion-required pairs. Order: (min ID,max ID,PairKind),
    // independent of source order; refs keep original typed ordinals.
    std::vector<Pair> pairs;
};
struct Result {
    Status status=Status::invalid_input;
    Reason reason=Reason::none;
    std::optional<FailureLocation> failure;
    CaptureState capture=CaptureState::none;
    // Bounded counts are checked before capture. A complete captured snapshot
    // can be INVALID: it is original diagnostic data, not a prepared inventory.
    // On allocation failure a partial snapshot may retain copied vector prefixes.
    std::optional<Snapshot> snapshot;
    std::optional<Inventory> inventory; // Present IFF ready; never a truncated list.
    std::string message;
};

// Environment FIRST. Count hard limits 8/16/1..4/total faces<=64 precede owned
// capture; each mesh then requires 1..64 faces. Whole captured input is validated
// before inventory creation. H finite (0,.1], |gravity|<=1e9 component-wise.
// Body validation is existing RigidBody::validate; plane uses existing World
// near-unit-normal/material/offset domain WITHOUT renormalizing its raw values.
// All collider IDs unique across bodies/planes/meshes. Face IDs are unique only
// WITHIN each mesh; ID/revision/face ID domain is 1..2^53-1. |vertices|<=1e12.
// Degenerate/ill-conditioned triangles can be READY: geometry is NOT queried.
// Profile counts are 1..hard cap (max_planes may be 0); exceeding a smaller
// profile is budget_exceeded, never truncated ready. All static-only six kinds
// are counted/excluded; ready is not static-static non-overlap certification.
// The caller must prevent concurrent mutation during this synchronous capture.
// Source/World/loads/pointers/order/clock remain unchanged; results own all data.
// No allocator/stack/16MiB hard-byte guarantee or certification is claimed.
Result prepare(const dynamics::World& world,std::span<const StaticMeshSource> meshes,
               double horizon_seconds,const Settings& settings={}) noexcept;
}
