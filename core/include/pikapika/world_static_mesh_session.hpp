#pragma once
#include "pikapika/world_static_mesh_flight_controlled_scheduler.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <span>
#include <vector>

namespace pikapika::world_static_mesh_session {
// Isolated Native ownership prototype. No SDK, persistent packet queue, thread
// atomicity or cross-registry capability. Calls to one Registry are exclusive.
namespace flight=world_static_mesh_flight_controlled_scheduler;
inline constexpr std::size_t hard_max_sessions=4;
inline constexpr std::uint64_t maximum_generation=(std::uint64_t{1}<<53)-1;
struct RegistrySettings {std::uint64_t generation_limit=maximum_generation;};
struct Token {std::uint32_t slot{};std::uint64_t generation{};bool operator==(const Token&) const = default;};
enum class Status : unsigned {ok,busy,slot_range,not_alive,stale_generation,foreign_session,no_free_slot,
    generation_exhausted,source_counts,invalid_settings,allocation_failure,unexpected_exception};
struct Created {Status status=Status::unexpected_exception;Token token;};
struct Snapshot {
    Token token;
    dynamics::World world;
    std::vector<flight::StaticMeshSource> meshes;
    flight::GuardSettings guard;
    flight::Progress progress;
    flight::Snapshot scheduler;
    Snapshot(Token,const dynamics::World&,std::span<const flight::StaticMeshSource>,
             const flight::GuardSettings&,flight::Progress,flight::Snapshot);
};
struct Read {Status status=Status::unexpected_exception;std::optional<Snapshot> snapshot;};
struct Pump {
    Status status=Status::unexpected_exception; // Owner gate, separate from model status.
    Token token;
    std::size_t scheduler_calls{};
    std::optional<flight::PumpReport> report; // Actual delegated call only.
};
struct Request {
    Token owner; // The packet envelope's origin, independent of the target handle.
    double elapsed{};
    std::span<const flight::TickLoadPacket> packets;
};
class Registry {
public:
    explicit Registry(RegistrySettings settings={});
    ~Registry() noexcept;
    Registry(const Registry&)=delete;
    Registry& operator=(const Registry&)=delete;
    Registry(Registry&&)=delete;
    Registry& operator=(Registry&&)=delete;
    Created create(const dynamics::World&,std::span<const flight::StaticMeshSource>,
                   const flight::GuardSettings&,flight::Progress,flight::Settings={}) noexcept;
    Created reset(Token,const dynamics::World&,std::span<const flight::StaticMeshSource>,
                  const flight::GuardSettings&,flight::Progress,flight::Settings={}) noexcept;
    Status destroy(Token) noexcept;
    Read read(Token) noexcept; // Owned value copy, no mutable owner reference.
    Pump pump(Token target,const Request&) noexcept;
private:
    struct Session;
    struct Slot {std::uint64_t generation{};std::unique_ptr<Session> active;};
    RegistrySettings settings_;
    std::array<Slot,hard_max_sessions> slots_;
    bool busy_{};
    Status validate(Token) const noexcept;
};
}
