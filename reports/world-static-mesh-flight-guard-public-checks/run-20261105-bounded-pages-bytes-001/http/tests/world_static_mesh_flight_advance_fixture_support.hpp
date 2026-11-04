#pragma once
// Test-only transaction evidence. No public engine API or profile is enabled here.
#include "pikapika/world_static_mesh_flight_advance.hpp"
#include "world_static_mesh_flight_guard_test_support.hpp"
#include <iosfwd>
#include <string_view>

namespace world_advance_fixture {
namespace advance=pikapika::world_static_mesh_flight_advance;
inline constexpr double initial_time=.125;
inline constexpr std::uint64_t initial_ticks=17;

// All AdvanceReport fields, including the ACTUAL returned owned guard. The
// established guard writer retains every numerical field and its explicit
// non-normative child-message omission accounting. No replacement query occurs.
void report_json(std::ostream& output,const advance::AdvanceReport& report);
// Shared test-only strict UTF-8/JSON helpers; no query or result synthesis.
void string_json(std::ostream& output,std::string_view value);
void validate_document(std::string_view document);

// Each existing guard input is copied into an independent live transaction.
// Exactly one advance per case; no expected-result synthesis or guard re-query.
// Complete document buffering precedes output. Serialization/capture errors throw
// and the standalone main exits nonzero, without emitting a partial JSON document.
void emit_fixtures(std::ostream& output);
}
