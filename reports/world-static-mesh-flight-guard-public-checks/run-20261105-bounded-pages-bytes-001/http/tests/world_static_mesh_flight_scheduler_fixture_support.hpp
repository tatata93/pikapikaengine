#pragma once
// Test-only full scheduler serialization; no production API or profile enable.
#include "pikapika/world_static_mesh_flight_scheduler.hpp"
#include <cstddef>
#include <iosfwd>

namespace world_scheduler_fixture {
inline constexpr std::size_t maximum_document_bytes=64*1024*1024;
// Each stored AdvanceReport is the ACTUAL pump-returned value. No requery or
// fabricated intermediate external World/pointer observation is performed.
void report_json(std::ostream&,const pikapika::world_static_mesh_flight_scheduler::PumpReport&);
void emit_fixtures(std::ostream&);
}
