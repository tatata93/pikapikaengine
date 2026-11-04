#pragma once
#include "pikapika/accelerated_sphere_box_coverage.hpp"
#include <iosfwd>
#include <optional>
#include <string>
#include <vector>
namespace sphere_box_fixture {
namespace coverage=pikapika::accelerated_sphere_box_coverage;
struct Case {
    std::string name;
    coverage::Input input{pikapika::accelerated::Sphere{{-0.,0,-0.},{-0.,0,0},{0,-0.,0},.25},pikapika::accelerated::Sphere{{4,-0.,0},{0,-0.,0},{-0.,0,-0.},.25},0.,0.,0.};
    double horizon{.0625};
    coverage::Settings settings;
    std::optional<coverage::Status> expected{coverage::Status::certified};
    std::optional<coverage::Reason> reason;
    std::optional<std::size_t> failed_input;
};
Case base_case();
std::vector<Case> cases();
void input_json(std::ostream&,const Case&);
void snapshot_json(std::ostream&,const coverage::Snapshot&);
void result_json(std::ostream&,const coverage::Result&);
void emit_fixtures(std::ostream&,const std::vector<Case>&);
}
