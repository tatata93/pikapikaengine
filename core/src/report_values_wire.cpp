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
    template<class T> void optional(std::string_view name,const std::optional<T>& value) noexcept {
        if(!key(name)) return;
        status_=value ? writer_.present() : writer_.absent();
        if(value && status_==Status::ok) {
            status_=scalar(writer_,*value);
            if(status_==Status::ok) status_=writer_.end();
        }
    }
    void optional_count(std::string_view name,const std::optional<std::size_t>& value) noexcept {
        if(!key(name)) return;
        status_=value ? writer_.present() : writer_.absent();
        if(value && status_==Status::ok) {
            status_=writer_.u64(static_cast<std::uint64_t>(*value));
            if(status_==Status::ok) status_=writer_.end();
        }
    }
    template<class T,std::size_t N> void optional_array(std::string_view name,const std::optional<std::array<T,N>>& value) noexcept {
        if(!key(name)) return;
        status_=value ? writer_.present() : writer_.absent();
        if(value && status_==Status::ok) {
            status_=writer_.array();
            for(const auto& element:*value) {
                if(status_!=Status::ok) return;
                status_=scalar(writer_,element);
            }
            if(status_==Status::ok) status_=writer_.end();
            if(status_==Status::ok) status_=writer_.end();
        }
    }
    template<class E> void optional_enumeration(std::string_view name,const std::optional<E>& value) noexcept {
        static_assert(std::is_enum_v<E> && sizeof(std::underlying_type_t<E>)==4 && std::is_unsigned_v<std::underlying_type_t<E>>);
        if(!key(name)) return;
        status_=value ? writer_.present() : writer_.absent();
        if(value && status_==Status::ok) {
            status_=writer_.enumeration(static_cast<std::uint32_t>(*value));
            if(status_==Status::ok) status_=writer_.end();
        }
    }
    template<class E> void optional_signed_enumeration(std::string_view name,const std::optional<E>& value) noexcept {
        static_assert(std::is_enum_v<E> && std::is_same_v<std::underlying_type_t<E>,std::int32_t>);
        if(!key(name)) return;
        status_=value ? writer_.present() : writer_.absent();
        if(value && status_==Status::ok) {
            // Defined integer conversion modulo2^32; no object-byte aliasing.
            status_=writer_.enumeration(static_cast<std::uint32_t>(static_cast<std::int32_t>(*value)));
            if(status_==Status::ok) status_=writer_.end();
        }
    }
    template<std::size_t N> void fixed_bytes(std::string_view name,const std::array<char,N>& value) noexcept {
        if(key(name)) status_=writer_.bytes(std::as_bytes(std::span<const char>(value)));
    }
    void bytes(std::string_view name,const std::string& value) noexcept {
        if(key(name)) status_=writer_.bytes(std::as_bytes(std::span(value.data(),value.size())));
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
Status write(Writer& w,const world_static_mesh_flight_guard::Counter& v) noexcept {
    Record r(w);
    r.count("known",v.known);
    r.count("upper",v.upper);
    r.field("exact",v.exact);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::HeldLedger& v) noexcept {
    Record r(w);
    r.field("mesh_queries",v.mesh_queries);
    r.field("primitive_queries",v.primitive_queries);
    r.field("candidates_examined",v.candidates_examined);
    r.field("primitive_sqrt_refinements",v.primitive_sqrt_refinements);
    r.field("enclosure_sqrt_refinements",v.enclosure_sqrt_refinements);
    r.field("sqrt_refinements",v.sqrt_refinements);
    r.field("mesh_sqrt_limited_rows",v.mesh_sqrt_limited_rows);
    r.field("enclosure_sqrt_calls",v.enclosure_sqrt_calls);
    r.field("enclosure_sqrt_limited_calls",v.enclosure_sqrt_limited_calls);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::Retained& v) noexcept {
    Record r(w);
    r.count("body_records",v.body_records);
    r.count("pair_records",v.pair_records);
    r.count("held_audits",v.held_audits);
    r.count("held_certified_leaves",v.held_certified_leaves);
    r.count("held_partition",v.held_partition);
    r.count("held_frontier",v.held_frontier);
    r.count("primitive_audits",v.primitive_audits);
    r.count("primitive_partition",v.primitive_partition);
    r.count("primitive_frontier",v.primitive_frontier);
    r.count("last_mesh_rows",v.last_mesh_rows);
    r.count("primitive_candidates",v.primitive_candidates);
    r.count("retained_faces",v.retained_faces);
    r.count("logical_payload_bytes",v.logical_payload_bytes);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::WorkGrant& v) noexcept {
    Record r(w);
    r.count("mesh_queries",v.mesh_queries);
    r.count("primitive_queries",v.primitive_queries);
    r.count("candidates_examined",v.candidates_examined);
    r.count("sqrt_refinements",v.sqrt_refinements);
    r.count("propagations",v.propagations);
    r.count("plane_metric_values",v.plane_metric_values);
    r.count("box_values",v.box_values);
    r.count("plane_norm_loop_iterations_upper",v.plane_norm_loop_iterations_upper);
    r.count("bridge_calls_upper",v.bridge_calls_upper);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::Reservation& v) noexcept {
    Record r(w);
    r.field("retained",v.retained);
    r.field("granted",v.granted);
    r.field("charged",v.charged);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::Grant& v) noexcept {
    Record r(w);
    r.field("retained",v.retained);
    r.field("work",v.work);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::MessageOmission& v) noexcept {
    Record r(w);
    r.count("fields",v.fields);
    r.count("nonempty_fields",v.nonempty_fields);
    r.count("bytes",v.bytes);
    r.field("omitted",v.omitted);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::Work& v) noexcept {
    Record r(w);
    r.count("child_calls_attempted",v.child_calls_attempted);
    r.count("child_calls_returned",v.child_calls_returned);
    r.count("mesh_calls_attempted",v.mesh_calls_attempted);
    r.count("mesh_calls_returned",v.mesh_calls_returned);
    r.count("plane_metric_calls_attempted",v.plane_metric_calls_attempted);
    r.count("plane_metric_calls_returned",v.plane_metric_calls_returned);
    r.count("plane_box_calls_attempted",v.plane_box_calls_attempted);
    r.count("plane_box_calls_returned",v.plane_box_calls_returned);
    r.count("sphere_box_calls_attempted",v.sphere_box_calls_attempted);
    r.count("sphere_box_calls_returned",v.sphere_box_calls_returned);
    r.field("held",v.held);
    r.field("propagation_attempts",v.propagation_attempts);
    r.field("plane_metric_values",v.plane_metric_values);
    r.field("box_values",v.box_values);
    r.count("bridge_calls_upper",v.bridge_calls_upper);
    r.count("plane_norm_calls_upper",v.plane_norm_calls_upper);
    r.count("plane_norm_loop_iterations_upper",v.plane_norm_loop_iterations_upper);
    r.count("sphere_root_results_returned",v.sphere_root_results_returned);
    r.count("sphere_root_limited_returns",v.sphere_root_limited_returns);
    r.field("sphere_sqrt_refinements",v.sphere_sqrt_refinements);
    r.field("sqrt_refinements",v.sqrt_refinements);
    r.field("exact",v.exact);
    return r.end();
}
Status write(Writer& w,const interval::Interval& v) noexcept {
    Record r(w);r.field("lower",v.lower());r.field("upper",v.upper());return r.end();
}
Status write(Writer& w,const interval::SqrtResult& v) noexcept {
    Record r(w);r.field("value",v.value);r.field("refinements",v.refinements);
    r.field("refinement_limited",v.refinement_limited);return r.end();
}
Status write(Writer& w,const sphere_triangle::CandidateAudit& v) noexcept {
    Record r(w);r.enumeration("feature",static_cast<std::uint32_t>(v.feature));
    r.enumeration("disposition",static_cast<std::uint32_t>(v.disposition));
    r.array("barycentric",std::span<const interval::Interval>(v.barycentric));
    r.array("kkt",std::span<const interval::Interval>(v.kkt));r.field("kkt_count",v.kkt_count);return r.end();
}
Status write(Writer& w,const sphere_triangle::Geometry& v) noexcept {
    Record r(w);r.field("surface_id",v.surface_id);r.field("surviving_features",v.surviving_features);
    r.array("barycentric",std::span<const interval::Interval>(v.barycentric));
    r.array("closest_local",std::span<const interval::Interval>(v.closest_local));
    r.array("closest",std::span<const interval::Interval>(v.closest));
    r.array("delta",std::span<const interval::Interval>(v.delta));
    r.array("normal",std::span<const interval::Interval>(v.normal));
    r.array("sphere_point",std::span<const interval::Interval>(v.sphere_point));
    r.field("squared_distance",v.squared_distance);r.field("distance",v.distance);r.field("gap",v.gap);
    r.enumeration("relation",static_cast<std::uint32_t>(v.relation));return r.end();
}
Status write(Writer& w,const sphere_triangle::Result& v) noexcept {
    Record r(w);r.enumeration("status",static_cast<std::uint32_t>(v.status));
    r.enumeration("reason",static_cast<std::uint32_t>(v.reason));
    r.optional("geometry",v.geometry);r.optional("squared_cross",v.squared_cross);r.optional("sine_squared",v.sine_squared);
    r.array("candidates",std::span<const sphere_triangle::CandidateAudit>(v.candidates));
    r.field("candidates_examined",v.candidates_examined);r.field("sqrt_refinements",v.sqrt_refinements);
    r.field("sqrt_refinement_limited",v.sqrt_refinement_limited);r.bytes("message",v.message);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh::Row& v) noexcept {
    Record r(w);r.field("triangle",v.triangle);r.optional("query",v.query);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh::Nearest& v) noexcept {
    Record r(w);r.field("squared_distance",v.squared_distance);r.field("distance",v.distance);r.field("gap",v.gap);
    r.array("possible_surface_ids",std::span<const std::uint64_t>(v.possible_surface_ids));return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh::Result& v) noexcept {
    Record r(w);r.enumeration("status",static_cast<std::uint32_t>(v.status));
    r.enumeration("reason",static_cast<std::uint32_t>(v.reason));
    r.optional_count("failed_index",v.failed_index);r.optional_count("first_failed_row",v.first_failed_row);
    r.array("rows",std::span<const sphere_triangle_mesh::Row>(v.rows));r.optional("nearest",v.nearest);
    r.count("queries",v.queries);r.count("candidates_examined",v.candidates_examined);r.count("sqrt_refinements",v.sqrt_refinements);
    r.count("sqrt_limited_rows",v.sqrt_limited_rows);r.count("failed_rows",v.failed_rows);r.bytes("message",v.message);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::HeldSphere& v) noexcept {
    Record r(w);r.field("id",v.id);r.field("position",v.position);r.field("velocity",v.velocity);r.field("mass",v.mass);
    r.field("force",v.force);r.field("gravity",v.gravity);r.field("radius",v.radius);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::Cell& v) noexcept {
    Record r(w);r.array("time_bounds",std::span<const double>(v.time_bounds));r.field("depth",v.depth);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::WorldBodySnapshot& v) noexcept {
    Record r(w);r.field("body",v.body);r.field("gravity",v.gravity);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::Snapshot& v) noexcept {
    Record r(w);r.field("input",v.input);r.field("horizon",v.horizon);
    r.array("triangles",std::span<const sphere_triangle::StaticTriangle>(v.triangles));r.field("settings",v.settings);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::Work& v) noexcept {
    Record r(w);
    r.count("mesh_queries",v.mesh_queries);
    r.count("primitive_queries",v.primitive_queries);
    r.count("candidates_examined",v.candidates_examined);
    r.count("primitive_sqrt_refinements",v.primitive_sqrt_refinements);
    r.count("enclosure_sqrt_refinements",v.enclosure_sqrt_refinements);
    r.count("sqrt_refinements",v.sqrt_refinements);
    r.count("sqrt_refinements_upper",v.sqrt_refinements_upper);
    r.count("mesh_sqrt_limited_rows",v.mesh_sqrt_limited_rows);
    r.count("enclosure_sqrt_calls",v.enclosure_sqrt_calls);
    r.count("enclosure_sqrt_limited_calls",v.enclosure_sqrt_limited_calls);
    r.field("exact",v.exact);return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::InitialProof& v) noexcept {
    Record r(w);
    r.field("lower_gap_certificate",v.lower_gap_certificate);
    r.field("upper_gap_certificate",v.upper_gap_certificate);
    r.count("audit_index",v.audit_index);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::CertifiedLeaf& v) noexcept {
    Record r(w);
    r.field("cell",v.cell);
    r.field("lower_gap_certificate",v.lower_gap_certificate);
    r.count("audit_index",v.audit_index);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::Witness& v) noexcept {
    Record r(w);
    r.field("cell",v.cell);
    r.field("time",v.time);
    r.array("exact_path_bounds",std::span<const interval::Interval>(v.exact_path_bounds));
    r.field("anchor",v.anchor);
    r.field("error_upper",v.error_upper);
    r.field("upper_gap_certificate",v.upper_gap_certificate);
    r.count("audit_index",v.audit_index);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::EntryWindow& v) noexcept {
    Record r(w);
    r.array("time_bounds",std::span<const double>(v.time_bounds));
    r.field("time_width",v.time_width);
    r.array("path_bounds",std::span<const interval::Interval>(v.path_bounds));
    r.field("l1_diameter_bound",v.l1_diameter_bound);
    r.count("witness_audit_index",v.witness_audit_index);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::CellAudit& v) noexcept {
    Record r(w);
    r.enumeration("kind",static_cast<std::uint32_t>(v.kind));
    r.field("cell",v.cell);
    r.field("time",v.time);
    r.enumeration("outcome",static_cast<std::uint32_t>(v.outcome));
    r.optional_array("path_bounds",v.path_bounds);
    r.optional_array("point_bounds",v.point_bounds);
    r.optional("anchor",v.anchor);
    r.field("mesh_queried",v.mesh_queried);
    r.optional_enumeration("mesh_status",v.mesh_status);
    r.optional_enumeration("mesh_reason",v.mesh_reason);
    r.optional("distance",v.distance);
    r.optional("displacement_squared_bound",v.displacement_squared_bound);
    r.optional("error_squared_bound",v.error_squared_bound);
    r.optional("displacement_root",v.displacement_root);
    r.optional("error_root",v.error_root);
    r.optional("clearance_certificate",v.clearance_certificate);
    r.optional("penetration_certificate",v.penetration_certificate);
    r.field("work",v.work);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::PartitionLeaf& v) noexcept {
    Record r(w);
    r.field("cell",v.cell);
    r.enumeration("state",static_cast<std::uint32_t>(v.state));
    r.optional_count("audit_index",v.audit_index);
    r.enumeration("blocked_reason",static_cast<std::uint32_t>(v.blocked_reason));
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_held_load::Result& v) noexcept {
    Record r(w);
    r.enumeration("status",static_cast<std::uint32_t>(v.status));
    r.enumeration("reason",static_cast<std::uint32_t>(v.reason));
    r.optional_count("failed_index",v.failed_index);
    r.optional("snapshot",v.snapshot);
    r.optional("world_body",v.world_body);
    r.optional_array("acceleration",v.acceleration);
    r.optional_array("whole_path_bounds",v.whole_path_bounds);
    r.optional_array("whole_velocity_bounds",v.whole_velocity_bounds);
    r.optional("initial",v.initial);
    r.field("initial_separation_proven",v.initial_separation_proven);
    r.array("certified_leaves",std::span<const sphere_triangle_mesh_held_load::CertifiedLeaf>(v.certified_leaves));
    r.optional_array("safe_prefix",v.safe_prefix);
    r.optional("best_witness",v.best_witness);
    r.optional("window",v.window);
    r.array("candidate_surface_ids",std::span<const std::uint64_t>(v.candidate_surface_ids));
    r.array("partition",std::span<const sphere_triangle_mesh_held_load::PartitionLeaf>(v.partition));
    r.array("frontier",std::span<const sphere_triangle_mesh_held_load::Cell>(v.frontier));
    r.optional("current",v.current);
    r.array("audits",std::span<const sphere_triangle_mesh_held_load::CellAudit>(v.audits));
    r.optional("last_mesh",v.last_mesh);
    r.optional_count("last_mesh_audit_index",v.last_mesh_audit_index);
    r.field("work",v.work);
    r.count("partition_leaves",v.partition_leaves);
    r.field("maximum_depth",v.maximum_depth);
    r.bytes("message",v.message);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_free_flight_guard::Snapshot& v) noexcept {
    Record r(w);
    r.field("body",v.body);
    r.field("gravity",v.gravity);
    r.field("horizon",v.horizon);
    r.array("triangles",std::span<const sphere_triangle::StaticTriangle>(v.triangles));
    r.field("settings",v.settings);
    return r.end();
}

Status write(Writer& w,const sphere_triangle_mesh_free_flight_guard::Tube& v) noexcept {
    Record r(w);
    r.field("nominal_acceleration",v.nominal_acceleration);
    r.array("exact_acceleration",std::span<const interval::Interval>(v.exact_acceleration));
    r.array("acceleration_difference",std::span<const interval::Interval>(v.acceleration_difference));
    r.field("position_error",v.position_error);
    r.field("roundoff",v.roundoff);
    r.field("guard_radius",v.guard_radius);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_free_flight_guard::EndpointAudit& v) noexcept {
    Record r(w);
    r.array("nominal_position",std::span<const interval::Interval>(v.nominal_position));
    r.array("nominal_allowed",std::span<const interval::Interval>(v.nominal_allowed));
    r.array("exact_position",std::span<const interval::Interval>(v.exact_position));
    r.array("exact_allowed",std::span<const interval::Interval>(v.exact_allowed));
    r.array("exact_difference",std::span<const interval::Interval>(v.exact_difference));
    r.field("l1_error_bound",v.l1_error_bound);
    r.field("nominal_contained",v.nominal_contained);
    r.field("exact_contained",v.exact_contained);
    r.field("l1_within_tube",v.l1_within_tube);
    return r.end();
}
Status write(Writer& w,const sphere_triangle_mesh_free_flight_guard::Result& v) noexcept {
    Record r(w);
    r.enumeration("status",static_cast<std::uint32_t>(v.status));
    r.enumeration("reason",static_cast<std::uint32_t>(v.reason));
    r.optional_count("failed_index",v.failed_index);
    r.optional("world_body",v.world_body);
    r.optional("snapshot",v.snapshot);
    r.optional("tube",v.tube);
    r.optional_signed_enumeration("flight_failure",v.flight_failure);
    r.field("candidate_evaluated",v.candidate_evaluated);
    r.optional("endpoint",v.endpoint);
    r.optional("inflated",v.inflated);
    r.optional("candidate",v.candidate);
    r.bytes("message",v.message);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight_guard::BindingInfo& v) noexcept {
    Record r(w);
    r.enumeration("mode",static_cast<std::uint32_t>(v.mode));
    r.enumeration("state",static_cast<std::uint32_t>(v.state));
    r.field("checked",v.checked);
    r.field("profile",v.profile);
    r.fixed_bytes("build_id",v.build_id);
    return r.end();
}

Status write(Writer& w,const world_static_mesh_flight_guard::BodyRecord& v) noexcept {
    Record r(w);
    r.count("body_ordinal",v.body_ordinal);
    r.field("is_static",v.is_static);
    r.enumeration("state",static_cast<std::uint32_t>(v.state));
    r.optional_count("seed_pair_ordinal",v.seed_pair_ordinal);
    return r.end();
}
Status write(Writer& w,const world_static_mesh_flight::FailureLocation& v) noexcept {
    Record r(w);
    r.enumeration("kind",static_cast<std::uint32_t>(v.kind));
    r.optional_count("index",v.index);
    r.optional_count("face_index",v.face_index);
    return r.end();
}

Status write(Writer& w,const world_static_mesh_flight_guard::Failure& v) noexcept {
    Record r(w);
    r.optional("preparation",v.preparation);
    r.optional_count("body_ordinal",v.body_ordinal);
    r.optional_count("pair_ordinal",v.pair_ordinal);
    return r.end();
}
Status write(Writer& w,const accelerated::Sphere& v) noexcept {
    Record r(w);
    r.field("center",v.center);
    r.field("velocity",v.velocity);
    r.field("acceleration",v.acceleration);
    r.field("radius",v.radius);
    return r.end();
}

Status write(Writer& w,const accelerated::StaticPlane& v) noexcept {
    Record r(w);
    r.field("normal",v.normal);
    r.field("offset",v.offset);
    return r.end();
}
Status write(Writer& w,const accelerated_pair_coverage::SpherePair& v) noexcept {
    Record r(w);
    r.field("first",v.first);
    r.field("second",v.second);
    return r.end();
}

Status write(Writer& w,const accelerated_pair_coverage::SpherePlane& v) noexcept {
    Record r(w);
    r.field("sphere",v.sphere);
    r.field("plane",v.plane);
    return r.end();
}
Status write(Writer& w,const accelerated_pair_coverage::Input& v) noexcept {
    if(const auto* pair=std::get_if<accelerated_pair_coverage::SpherePair>(&v)) {
        if(const auto s=w.variant(0);s!=Status::ok) return s;
        if(const auto s=write(w,*pair);s!=Status::ok) return s;
        return w.end();
    }
    if(const auto* plane=std::get_if<accelerated_pair_coverage::SpherePlane>(&v)) {
        if(const auto s=w.variant(1);s!=Status::ok) return s;
        if(const auto s=write(w,*plane);s!=Status::ok) return s;
        return w.end();
    }
    return w.reject_invalid_value();
}

Status write(Writer& w,const accelerated_pair_coverage::Snapshot& v) noexcept {
    Record r(w);
    r.field("input",v.input);
    r.field("horizon",v.horizon);
    r.field("settings",v.settings);
    return r.end();
}

Status write(Writer& w,const accelerated_pair_coverage::Cell& v) noexcept {
    Record r(w);
    r.array("time_bounds",std::span<const double>(v.time_bounds));
    r.field("depth",v.depth);
    r.optional_count("parent_audit",v.parent_audit);
    return r.end();
}
Status write(Writer& w,const accelerated_pair_coverage::Work& v) noexcept {
    Record r(w);
    r.count("value_calls_attempted",v.value_calls_attempted);
    r.count("value_calls_returned",v.value_calls_returned);
    r.count("plane_norm_calls_upper",v.plane_norm_calls_upper);
    r.count("plane_norm_loop_iterations_upper",v.plane_norm_loop_iterations_upper);
    return r.end();
}

Status write(Writer& w,const accelerated_pair_coverage::Audit& v) noexcept {
    Record r(w);
    r.field("cell",v.cell);
    r.field("call_attempted",v.call_attempted);
    r.optional("value",v.value);
    r.enumeration("outcome",static_cast<std::uint32_t>(v.outcome));
    r.enumeration("blocked_reason",static_cast<std::uint32_t>(v.blocked_reason));
    r.optional("split_time",v.split_time);
    return r.end();
}
Status write(Writer& w,const accelerated_pair_coverage::PartitionLeaf& v) noexcept {
    Record r(w);
    r.field("cell",v.cell);
    r.enumeration("state",static_cast<std::uint32_t>(v.state));
    r.optional_count("audit_index",v.audit_index);
    r.enumeration("blocked_reason",static_cast<std::uint32_t>(v.blocked_reason));
    return r.end();
}

Status write(Writer& w,const accelerated_pair_coverage::Result& v) noexcept {
    Record r(w);
    r.enumeration("status",static_cast<std::uint32_t>(v.status));
    r.enumeration("reason",static_cast<std::uint32_t>(v.reason));
    r.optional("snapshot",v.snapshot);
    r.field("snapshot_validated",v.snapshot_validated);
    r.optional_count("failed_input",v.failed_input);
    r.field("partition_complete",v.partition_complete);
    r.array("audits",std::span<const accelerated_pair_coverage::Audit>(v.audits));
    r.array("partition",std::span<const accelerated_pair_coverage::PartitionLeaf>(v.partition));
    r.array("frontier",std::span<const accelerated_pair_coverage::Cell>(v.frontier));
    r.optional("current",v.current);
    r.field("work",v.work);
    r.bytes("message",v.message);
    return r.end();
}

Status write(Writer& w,const accelerated_plane_box_coverage::Input& v) noexcept {
    Record r(w);
    r.field("sphere",v.sphere);
    r.field("plane",v.plane);
    r.field("position_error",v.position_error);
    r.field("contact_margin",v.contact_margin);
    return r.end();
}

Status write(Writer& w,const accelerated_plane_box_coverage::Snapshot& v) noexcept {
    Record r(w);
    r.field("input",v.input);
    r.field("horizon",v.horizon);
    r.field("settings",v.settings);
    return r.end();
}

Status write(Writer& w,const accelerated_plane_box_coverage::Evaluation& v) noexcept {
    Record r(w);
    r.array("tube_coordinates",std::span<const interval::Interval>(v.tube_coordinates));
    r.field("distance",v.distance);
    r.field("threshold",v.threshold);
    r.field("gap",v.gap);
    return r.end();
}

Status write(Writer& w,const accelerated_plane_box_coverage::Cell& v) noexcept {
    Record r(w);
    r.array("time_bounds",std::span<const double>(v.time_bounds));
    r.field("depth",v.depth);
    r.optional_count("parent_audit",v.parent_audit);
    return r.end();
}
Status write(Writer& w,const accelerated_plane_box_coverage::Work& v) noexcept {
    Record r(w);
    r.count("value_calls_attempted",v.value_calls_attempted);
    r.count("value_calls_returned",v.value_calls_returned);
    return r.end();
}

Status write(Writer& w,const accelerated_plane_box_coverage::Audit& v) noexcept {
    Record r(w);
    r.field("cell",v.cell);
    r.field("call_attempted",v.call_attempted);
    r.optional("evaluation",v.evaluation);
    r.enumeration("outcome",static_cast<std::uint32_t>(v.outcome));
    r.enumeration("blocked_reason",static_cast<std::uint32_t>(v.blocked_reason));
    r.optional("split_time",v.split_time);
    return r.end();
}
Status write(Writer& w,const accelerated_plane_box_coverage::PartitionLeaf& v) noexcept {
    Record r(w);
    r.field("cell",v.cell);
    r.enumeration("state",static_cast<std::uint32_t>(v.state));
    r.optional_count("audit_index",v.audit_index);
    r.enumeration("blocked_reason",static_cast<std::uint32_t>(v.blocked_reason));
    return r.end();
}

}
