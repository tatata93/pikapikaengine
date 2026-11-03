#pragma once
#include "pikapika/motion_io.hpp"
#include "pikapika/skinning.hpp"
#include <iosfwd>

namespace pikapika::skinning_io {
struct Target {std::string object_id,native_id;};
struct Source {
    std::string name;
    Target target;
    std::string fingerprint;
    Mesh mesh;
    std::vector<std::vector<skinning::Influence>> influences;
    std::vector<skinning::JointBind> joints;
    std::vector<motion::Bone> rest_bones;
    motion_io::Source motion;
    // Structure, exact local-rest snapshot and mesh fingerprint only. Singular
    // inverse/rest matrices and normalization underflow remain editable values.
    void validate() const;
    // Rest FK must exactly match stored world matrices (+/-0 equal), then
    // current FK -> existing positions-only LBS. Pose/mismatch failures throw;
    // skinning model failures remain DeformResult without partial positions.
    skinning::DeformResult sample(double seconds,motion::Playback mode=motion::Playback::clamp) const;
    // Numeric native ID + complete ordered mesh comparison. Browser object_id
    // is a declaration only; object transform/material is independent.
    void match(const Scene&) const;
    void set_weight(std::size_t vertex,std::uint64_t bone_id,double value);
    void save(std::ostream&) const;
    static Source load(std::istream&);
};
// Noncryptographic FNV1a64 canonical ordered geometry bytes, not identity proof.
std::string mesh_fingerprint(const Mesh&);
// Initial binding requires successful rest FK/inverse construction. Other Source
// values can be preserved structurally even when later evaluation fails.
Source create(std::string name,Target target,Mesh mesh,motion_io::Source motion,
              std::vector<std::vector<skinning::Influence>> influences);
Source example();
}
