#pragma once
#include "pikapika/motion.hpp"
#include <iosfwd>

namespace pikapika::motion_io {
struct TrackSource {
    std::uint64_t bone_id{};
    motion::Interpolation interpolation{motion::Interpolation::linear};
    std::vector<motion::Key> keys;
};
// Owned editable source; spans exist only during a sampling call.
struct Source {
    std::string name;
    std::vector<motion::Bone> bones;
    std::vector<std::string> bone_names;
    std::string clip_name;
    double duration{1};
    std::vector<TrackSource> tracks;
    void validate() const;
    motion::Result sample(double seconds,motion::Playback mode=motion::Playback::clamp) const;
    void save(std::ostream&) const;
    static Source load(std::istream&);
};
}
