#pragma once
#include "pikapika/core.hpp"
#include <array>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <vector>

namespace pikapika::motion {
using Mat4=std::array<double,16>; // column-major; column vectors, translation 12..14
struct Bone {
    std::uint64_t id{},parent_id{}; // exact numeric IDs 1..2^53-1, parent 0 = root
    Transform rest;
};
struct Key { double time{};Transform pose; };
enum class Interpolation { linear,step };
struct Track {
    std::uint64_t bone_id{};
    Interpolation interpolation{Interpolation::linear};
    std::span<const Key> keys;
};
struct Clip { double duration{1};std::span<const Track> tracks; };
struct Input { std::span<const Bone> bones;Clip clip; };
enum class Playback { clamp,loop };
struct Settings {
    unsigned max_bones{128}; // 1..128
    unsigned max_tracks{128}; // 1..128
    unsigned max_keys{4096}; // 1..4096, total across tracks
};
struct BonePose {
    std::uint64_t id{},parent_id{};
    Transform local;
    Mat4 local_matrix{},world_matrix{};
};
struct Pose {
    double requested_time{},sampled_time{}; // seconds, no accumulated frame clock
    std::vector<BonePose> bones; // original bone input order, IDs unchanged
    std::vector<std::uint64_t> evaluation_order; // parent first, stable-ID tie order
};
enum class Status { completed,invalid_input,budget_exceeded,numerical_failure };
struct Result {
    Status status{Status::invalid_input};
    std::optional<Pose> pose; // complete only; no partial candidate on failure
    std::string message;
};
// Pure absolute-seconds sampling plus FK for a nonempty SINGLE-root tree.
// Arbitrary bone order; missing/duplicate/cyclic IDs and duplicate/unknown tracks
// fail. Missing track = rest, nonempty track, times [0,duration] strictly rising.
// Duration finite in (0,1e9], sample seconds finite >=0. Clamp holds duration;
// loop uses finite fmod(time,duration), exact duration ->0. Huge clocks do not
// retain sub-frame information absent from their input binary64 value.
// Translation components finite within +/-1e6 m; POSITIVE scale [1e-6,1e6].
// Quaternion [x,y,z,w] nonzero, finite, max abs <=1e300; scaled normalization
// avoids norm overflow, including subnormal nonzero input orientations.
// Step holds the preceding key; linear uses T/S lerp and shortest-path NLERP,
// not constant-angular-speed SLERP. Exact key times select normalized key pose;
// outside a track's keys holds its first/last key. No epsilon snapping.
// World = parentWorld * T*R*S, no world TRS decomposition: shear is retained.
// Preflights every source before sampling; nonfinite world is numerical failure.
// No events, IK, limits, dynamic control, blending, skinning or geometry binding.
// Point binary64 evaluation, NOT interval/exact-real containment. Inputs/external
// state unchanged on every failure; allocation failure may escape diagnostics.
Result sample(const Input&,double seconds,Playback mode=Playback::clamp,
              const Settings& settings={});
inline Result sample(std::span<const Bone> bones,const Clip& clip,double seconds,
                     Playback mode=Playback::clamp,const Settings& settings={}) {
    return sample(Input{bones,clip},seconds,mode,settings);
}
}
