#pragma once
#include "pikapika/accelerated_pair_coverage.hpp"
#include <iosfwd>
#include <optional>
#include <string>
#include <vector>
namespace coverage_fixture {
namespace coverage=pikapika::accelerated_pair_coverage;
namespace accelerated=pikapika::accelerated;
struct Case {
    std::string name;
    coverage::Input input=coverage::SpherePair{};
    double horizon{.0625};
    coverage::Settings settings;
    std::optional<coverage::Status> expected{coverage::Status::certified};
    std::optional<coverage::Reason> reason;
    std::optional<std::size_t> failed_input;
};
Case sphere_case();
Case plane_case();
coverage::Result query(const Case&);
std::vector<Case> cases();
void input_json(std::ostream&,const Case&);
void snapshot_json(std::ostream&,const coverage::Snapshot&);
void result_json(std::ostream&,const coverage::Result&);
void emit_fixtures(std::ostream&,const std::vector<Case>&);
}
