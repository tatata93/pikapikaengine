#pragma once
#include "pikapika/motion.hpp"

namespace pikapika::skinning {
using Mat4=motion::Mat4;
struct BoneMatrix { std::uint64_t bone_id{};Mat4 matrix{}; };
struct JointBind { std::uint64_t bone_id{};Mat4 rest_world{},inverse_bind{}; };
struct Influence { std::uint64_t bone_id{};double weight{}; };
struct Vertex { Vec3 position{};std::span<const Influence> influences; };
struct Settings {
    unsigned max_bones{128}; // 1..128, rest/bind/pose counts
    unsigned max_vertices{65536}; // 1..65536, zero actual vertices is valid
    unsigned max_influences{262144}; // 1..262144, TOTAL across vertices
    double maximum_condition{1e10}; // [1,1e12], 3x3 linear infinity-norm estimate
    double maximum_inverse_residual{1e-10}; // [1e-15,1e-3], definition below
};
enum class Status { completed,invalid_input,budget_exceeded,ill_conditioned,numerical_failure };
struct InverseDiagnostic {
    std::uint64_t bone_id{};
    std::optional<double> linear_condition,inverse_residual;
    bool pivot_failure{};
};
struct BindResult {
    Status status{Status::invalid_input};
    std::optional<std::vector<JointBind>> joints; // completed only, original rest order
    std::vector<InverseDiagnostic> diagnostics; // failure prefix is diagnostic only
    std::string message;
};
struct DeformResult {
    Status status{Status::invalid_input};
    std::optional<std::vector<Vec3>> positions; // completed only, original vertex order
    std::vector<InverseDiagnostic> inverse_diagnostics;
    std::vector<double> weight_residuals; // |sum(normalized weights)-1|; diagnostic prefix
    std::string message;
};
// Pure rest inverse construction. IDs 1..2^53-1, nonempty unique bone list.
// All matrices column-major affine, exact last row [0,0,0,1], finite |entry|<=1e150.
// Uses scaled 3x3 elimination; condition and BOTH inverse-product residuals are
// point-binary64 acceptance metrics, not rigorous condition/error enclosures.
// Residual=max infinity norm of R*I-Id and I*R-Id. Translation columns use a
// declared 1 metre reference, so the numeric threshold also audits metre error.
BindResult bind(std::span<const BoneMatrix> rest,const Settings& settings={});
// mesh local == skeleton space: p'=sum w_j * G_j * inverseBind_j * p.
// Bind/pose stable-ID sets must match; their input orders may differ. Every
// vertex has 1..4 UNIQUE known IDs and finite nonnegative author weights, with
// at least one positive. Source position finite within +/-1e6 metres.
// Working weights are sorted by stable ID, divided by their maximum then sum;
// original vertices/weights/matrices are untouched. Positive weight ->0 during
// either normalization stage is numerical_failure, not a discarded influence.
// Normalized sum residual must be <=32*binary64 epsilon. Explicit imported
// inverse binds are re-audited against their rest_world matrices and condition.
// Output positions need only be finite binary64, not within source +/-1e6 or
// representable as Float32. No partial positions on any failure. Allocation
// failure may escape if recording diagnostics itself cannot allocate.
// Position-only LBS: no normals/tangents, triangle validity, inversion/volume
// guarantee, skinning GPU, scene-world transform, bind-shape map or glTF import.
DeformResult deform(std::span<const Vertex> vertices,std::span<const JointBind> joints,
                    std::span<const BoneMatrix> pose,const Settings& settings={});
}
