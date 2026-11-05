#pragma once
#include "pikapika/diagnostic_wire.hpp"
#include "pikapika/world_static_mesh_flight_controlled_tick.hpp"
#include "pikapika/world_static_mesh_flight_scheduler.hpp"

namespace pikapika::report_values_wire {
// Leaf values for a future complete Report schema. These functions write ONE
// value into an already active Writer; caller checks the returned Status and
// finishes the enclosing document. They do not validate physical domains,
// allocate, normalize, query a World, or execute numerical model functions.
// Input and reachable vectors must remain alive and immutable through callbacks.
using Status=diagnostic_wire::Status;
using Writer=diagnostic_wire::Writer;
Status write(Writer&,const Vec3&) noexcept;
Status write(Writer&,const Quaternion&) noexcept;
Status write(Writer&,const dynamics::Material&) noexcept;
Status write(Writer&,const dynamics::RigidBody&) noexcept;
Status write(Writer&,const dynamics::Plane&) noexcept;
Status write(Writer&,const sphere_triangle::StaticTriangle&) noexcept;
Status write(Writer&,const world_static_mesh_flight::StaticMeshSource&) noexcept;
Status write(Writer&,const world_static_mesh_flight_controlled_tick::BodyLoad&) noexcept;
Status write(Writer&,const world_static_mesh_flight_controlled_tick::TickLoadPacket&) noexcept;
Status write(Writer&,const world_static_mesh_flight_advance::Progress&) noexcept;
Status write(Writer&,const world_static_mesh_flight_scheduler::Settings&) noexcept;
Status write(Writer&,const world_static_mesh_flight_scheduler::Snapshot&) noexcept;
Status write(Writer&,const sphere_triangle::Settings&) noexcept;
Status write(Writer&,const sphere_triangle_mesh::Settings&) noexcept;
Status write(Writer&,const sphere_triangle_mesh_held_load::Settings&) noexcept;
Status write(Writer&,const sphere_triangle_mesh_free_flight_guard::Settings&) noexcept;
Status write(Writer&,const accelerated_pair_coverage::Settings&) noexcept;
Status write(Writer&,const accelerated_plane_box_coverage::Settings&) noexcept;
Status write(Writer&,const accelerated_sphere_box_coverage::Settings&) noexcept;
Status write(Writer&,const world_static_mesh_flight::Settings&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::Limits&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::GuardSettings&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::Counter&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::HeldLedger&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::Retained&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::WorkGrant&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::Reservation&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::Grant&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::MessageOmission&) noexcept;
Status write(Writer&,const world_static_mesh_flight_guard::Work&) noexcept;
Status write(Writer&,const interval::Interval&) noexcept;
Status write(Writer&,const interval::SqrtResult&) noexcept;
Status write(Writer&,const sphere_triangle::CandidateAudit&) noexcept;
Status write(Writer&,const sphere_triangle::Geometry&) noexcept;
Status write(Writer&,const sphere_triangle::Result&) noexcept;
Status write(Writer&,const sphere_triangle_mesh::Row&) noexcept;
Status write(Writer&,const sphere_triangle_mesh::Nearest&) noexcept;
}
