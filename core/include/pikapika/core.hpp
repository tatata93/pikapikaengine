#pragma once
#include <array>
#include <cstdint>
#include <functional>
#include <iosfwd>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace pikapika {
// SI units; right handed coordinates; +Y up; quaternion (x,y,z,w).
struct Vec3 {
    double x{}, y{}, z{};
    Vec3 operator+(Vec3 b) const;
    Vec3 operator-(Vec3 b) const;
    Vec3 operator*(double s) const;
    double dot(Vec3 b) const;
    Vec3 cross(Vec3 b) const;
    double length() const;
    Vec3 normalized() const;
};
struct Quaternion {
    double x{}, y{}, z{}, w{1};
    Quaternion normalized() const;
    Vec3 rotate(Vec3 point) const;
};
struct Transform {
    Vec3 position{};
    Quaternion rotation{};
    Vec3 scale{1,1,1};
    Vec3 apply(Vec3 point) const;
};
struct Sphere { Vec3 center{}; double radius{1}; };
struct SweepHit { double fraction{}; Vec3 position{}; Vec3 normal{}; };
// Sweeps a sphere center from start to end against a static sphere.
std::optional<SweepHit> sweep_sphere(Vec3 start, Vec3 end, double radius, Sphere target);

class FixedClock {
public:
    explicit FixedClock(double step_seconds = 1.0/120.0, unsigned max_steps = 30);
    unsigned advance(double elapsed_seconds, const std::function<void(double)>& tick);
    double alpha() const;
    double dropped_seconds() const { return dropped_; }
    std::uint64_t ticks() const { return ticks_; }
private:
    double step_, accumulator_{}, dropped_{};
    unsigned max_steps_;
    std::uint64_t ticks_{};
};

struct Entity {
    std::uint64_t id{};
    std::string type{"box"}, name;
    Transform transform{};
    double radius{1};
};
struct Scene {
    static constexpr unsigned version = 1;
    std::vector<Entity> entities;
    // Opaque, bounded comments let authoring adapters retain their own metadata.
    std::vector<std::string> annotations;
    Entity* find(std::uint64_t id);
    const Entity* find(std::uint64_t id) const;
    // Shared edit API for CLI and future GUI; validates before changing state.
    void set_position(std::uint64_t id, Vec3 meters);
    void validate() const;
    static Scene load(std::istream& input);
    void save(std::ostream& output) const;
};

struct DirectSound {
    double distance_meters{};
    double delay_seconds{};
    double pressure_gain{};
};
// Ideal point source, pressure ratio 1/r beyond reference distance.
DirectSound direct_sound(Vec3 source, Vec3 listener, double sound_speed = 343.0,
                         double reference_distance = 1.0);
std::vector<float> render_direct_impulse(const DirectSound&, unsigned sample_rate,
                                        double duration_seconds);
void write_wav(std::ostream& output, const std::vector<float>& mono, unsigned sample_rate);
}
