#include "pikapika/report_values_wire.hpp"
#include <string_view>
#include <type_traits>

namespace pikapika::report_values_wire {
namespace {
static_assert(sizeof(std::size_t)<=sizeof(std::uint64_t));
static_assert(std::is_same_v<unsigned,std::uint32_t>);
static_assert(sizeof(std::underlying_type_t<world_static_mesh_flight_controlled_tick::LoadMode>)==4);
Status scalar(Writer& w,const double& v) noexcept {return w.f64(v);}
Status scalar(Writer& w,bool v) noexcept {return w.boolean(v);}
Status scalar(Writer& w,std::uint64_t v) noexcept {return w.u64(v);}
Status scalar(Writer& w,std::uint32_t v) noexcept {return w.u32(v);}
template<class T> Status scalar(Writer& w,const T& v) noexcept {return write(w,v);}
class Record {
    Writer& writer_;
    Status status_;
    bool key(std::string_view name) noexcept {
        if(status_!=Status::ok) return false;
        status_=writer_.key(std::as_bytes(std::span(name.data(),name.size())));
        return status_==Status::ok;
    }
public:
    explicit Record(Writer& w) noexcept:writer_(w),status_(w.object()) {}
    template<class T> void field(std::string_view name,const T& value) noexcept {
        if(key(name)) status_=scalar(writer_,value);
    }
    void count(std::string_view name,std::size_t value) noexcept {
        field(name,static_cast<std::uint64_t>(value));
    }
    void enumeration(std::string_view name,std::uint32_t value) noexcept {
        if(key(name)) status_=writer_.enumeration(value);
    }
    template<class T> void array(std::string_view name,std::span<const T> values) noexcept {
        if(!key(name)) return;
        status_=writer_.array();
        for(const auto& value:values) {
            if(status_!=Status::ok) return;
            status_=scalar(writer_,value);
        }
        if(status_==Status::ok) status_=writer_.end();
    }
    Status end() noexcept {
        // Preserve transient reentrant status; Writer::status() intentionally
        // remains ok during a refused nested call from its own sink.
        if(status_==Status::ok) status_=writer_.end();
        return status_;
    }
};
}
Status write(Writer& w,const Vec3& v) noexcept {
    Record r(w);r.field("x",v.x);r.field("y",v.y);r.field("z",v.z);return r.end();
}
Status write(Writer& w,const Quaternion& v) noexcept {
    Record r(w);r.field("x",v.x);r.field("y",v.y);r.field("z",v.z);r.field("w",v.w);return r.end();
}
Status write(Writer& w,const dynamics::Material& v) noexcept {
    Record r(w);r.field("restitution",v.restitution);r.field("friction",v.friction);return r.end();
}
Status write(Writer& w,const dynamics::RigidBody& v) noexcept {
    Record r(w);r.field("id",v.id);r.field("is_static",v.is_static);r.field("mass",v.mass);
    r.field("inertia_diagonal",v.inertia_diagonal);r.field("radius",v.radius);r.field("position",v.position);
    r.field("velocity",v.velocity);r.field("angular_momentum",v.angular_momentum);r.field("orientation",v.orientation);
    r.field("force",v.force);r.field("torque",v.torque);r.field("material",v.material);return r.end();
}
Status write(Writer& w,const dynamics::Plane& v) noexcept {
    Record r(w);r.field("id",v.id);r.field("normal",v.normal);r.field("offset",v.offset);r.field("material",v.material);return r.end();
}
Status write(Writer& w,const sphere_triangle::StaticTriangle& v) noexcept {
    Record r(w);r.field("id",v.id);r.array("vertices",std::span<const Vec3>(v.vertices));return r.end();
}
Status write(Writer& w,const world_static_mesh_flight::StaticMeshSource& v) noexcept {
    Record r(w);r.field("id",v.id);r.field("revision",v.revision);
    r.array("triangles",std::span<const sphere_triangle::StaticTriangle>(v.triangles));return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_controlled_tick::BodyLoad& v) noexcept {
    Record r(w);r.field("body_id",v.body_id);r.field("force_newtons",v.force_newtons);
    r.field("torque_newton_meters",v.torque_newton_meters);return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_controlled_tick::TickLoadPacket& v) noexcept {
    Record r(w);r.enumeration("mode",static_cast<std::uint32_t>(v.mode));r.field("expected_tick",v.expected_tick);
    r.array("loads",std::span<const world_static_mesh_flight_controlled_tick::BodyLoad>(v.loads));return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_advance::Progress& v) noexcept {
    Record r(w);r.field("time",v.time);r.field("ticks",v.ticks);return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_scheduler::Settings& v) noexcept {
    Record r(w);r.field("step_seconds",v.step_seconds);r.count("max_attempts_per_pump",v.max_attempts_per_pump);return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_scheduler::Snapshot& v) noexcept {
    Record r(w);r.field("settings",v.settings);r.field("backlog",v.backlog);r.field("sequence",v.sequence);r.field("busy",v.busy);return r.end();
}
Status write(Writer& w,const sphere_triangle::Settings& v) noexcept {
    Record r(w);r.field("max_candidates",v.max_candidates);r.field("sqrt_refinements",v.sqrt_refinements);
    r.field("max_total_sqrt_refinements",v.max_total_sqrt_refinements);r.field("maximum_local_width",v.maximum_local_width);
    r.field("maximum_normal_width",v.maximum_normal_width);r.field("minimum_sine_squared",v.minimum_sine_squared);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh::Settings& v) noexcept {
    Record r(w);r.count("max_surfaces",v.max_surfaces);r.field("primitive",v.primitive);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::Settings& v) noexcept {
    Record r(w);r.field("mesh",v.mesh);r.field("time_tolerance",v.time_tolerance);r.count("max_evaluations",v.max_evaluations);
    r.count("max_leaves",v.max_leaves);r.field("max_depth",v.max_depth);r.field("enclosure_sqrt_refinements",v.enclosure_sqrt_refinements);
    r.count("max_total_sqrt_refinements",v.max_total_sqrt_refinements);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_free_flight_guard::Settings& v) noexcept {
    Record r(w);r.field("held_load",v.held_load);r.field("max_angular_increment",v.max_angular_increment);return r.end();
}
Status write(Writer& w,const accelerated_pair_coverage::Settings& v) noexcept {
    Record r(w);r.field("time_tolerance",v.time_tolerance);r.count("max_evaluations",v.max_evaluations);r.count("max_leaves",v.max_leaves);r.field("max_depth",v.max_depth);return r.end();
}
Status write(Writer& w,const accelerated_plane_box_coverage::Settings& v) noexcept {
    Record r(w);r.field("time_tolerance",v.time_tolerance);r.count("max_evaluations",v.max_evaluations);r.count("max_leaves",v.max_leaves);r.field("max_depth",v.max_depth);return r.end();
}
Status write(Writer& w,const accelerated_sphere_box_coverage::Settings& v) noexcept {
    Record r(w);r.field("time_tolerance",v.time_tolerance);r.count("max_evaluations",v.max_evaluations);r.count("max_leaves",v.max_leaves);
    r.field("max_depth",v.max_depth);r.field("sqrt_refinements",v.sqrt_refinements);return r.end();
}
Status write(Writer& w,const world_static_mesh_flight::Settings& v) noexcept {
    Record r(w);r.count("max_bodies",v.max_bodies);r.count("max_planes",v.max_planes);r.count("max_meshes",v.max_meshes);
    r.count("max_total_faces",v.max_total_faces);r.count("max_pairs",v.max_pairs);return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::Limits& v) noexcept {
    Record r(w);r.count("body_records",v.body_records);r.count("pair_records",v.pair_records);
    r.count("held_audits",v.held_audits);r.count("held_certified_leaves",v.held_certified_leaves);r.count("held_partition",v.held_partition);r.count("held_frontier",v.held_frontier);
    r.count("primitive_audits",v.primitive_audits);r.count("primitive_partition",v.primitive_partition);r.count("primitive_frontier",v.primitive_frontier);
    r.count("last_mesh_rows",v.last_mesh_rows);r.count("primitive_candidates",v.primitive_candidates);r.count("retained_faces",v.retained_faces);
    r.count("mesh_queries",v.mesh_queries);r.count("primitive_queries",v.primitive_queries);r.count("candidates_examined",v.candidates_examined);
    r.count("sqrt_refinements",v.sqrt_refinements);r.count("plane_metric_values",v.plane_metric_values);r.count("box_values",v.box_values);
    r.count("propagations",v.propagations);r.count("logical_payload_bytes",v.logical_payload_bytes);return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::GuardSettings& v) noexcept {
    Record r(w);r.field("preparation",v.preparation);r.field("mesh",v.mesh);r.field("plane_metric",v.plane_metric);r.field("plane_box",v.plane_box);
    r.field("sphere_box",v.sphere_box);r.field("contact_margin",v.contact_margin);r.field("limits",v.limits);return r.end();
}
}
