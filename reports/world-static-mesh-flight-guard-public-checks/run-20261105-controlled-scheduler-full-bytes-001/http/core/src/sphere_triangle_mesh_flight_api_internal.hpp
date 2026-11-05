// Included once by simulation_api.cpp, after the legacy pure packet helpers.
// Private same-TU implementation: no old global record is used as scratch.
namespace {
namespace flight_held=pikapika::sphere_triangle_mesh_held_load;
namespace flight_guard=pikapika::sphere_triangle_mesh_free_flight_guard;
using FlightPacket=std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>;
using FlightInterval=pikapika::interval::Interval;
struct FlightRecord {
    uint32_t mode{};
    std::array<double,PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_GUARD_INPUT_COUNT> input{};
    std::vector<sphere_tri::StaticTriangle> source;
    std::optional<flight_held::Result> held;
    std::optional<flight_guard::Result> guard;
};
std::array<std::optional<SphereTriangleMeshStage>,2> flight_stages;
std::array<std::optional<FlightRecord>,2> flight_records;
void flight_mode(uint32_t mode) {require(mode<=1,PP_SIM_INVALID_ARGUMENT,"Unknown flight mode");}
bool flight_same(double a,double b) {return std::bit_cast<uint64_t>(a)==std::bit_cast<uint64_t>(b);}
bool flight_same_interval(const FlightInterval& a,const FlightInterval& b) {return flight_same(a.lower(),b.lower())&&flight_same(a.upper(),b.upper());}
Vec3 flight_vector(const FlightPacket& a,std::size_t o) {return {a[o],a[o+1],a[o+2]};}
void flight_interval(FlightPacket& a,std::size_t o,const FlightInterval& value) {a[o]=value.lower();a[o+1]=value.upper();}
void flight_settings_packet(FlightPacket& a,std::size_t o,const flight_held::Settings& s) {
    const auto& p=s.mesh.primitive;a[o]=double(s.mesh.max_surfaces);a[o+1]=p.max_candidates;a[o+2]=p.sqrt_refinements;a[o+3]=p.max_total_sqrt_refinements;
    a[o+4]=p.maximum_local_width;a[o+5]=p.maximum_normal_width;a[o+6]=p.minimum_sine_squared;a[o+7]=s.time_tolerance;
    a[o+8]=double(s.max_evaluations);a[o+9]=double(s.max_leaves);a[o+10]=s.max_depth;a[o+11]=s.enclosure_sqrt_refinements;a[o+12]=double(s.max_total_sqrt_refinements);
}
std::size_t flight_uint(double value) {
    const auto magnitude=std::bit_cast<uint64_t>(value)&0x7fffffffffffffffULL;
    require(magnitude==0||(magnitude>>52)>=1023,PP_SIM_INVALID_ARGUMENT,"Flight integer setting has a fractional magnitude");
    return query_integer(value,0,4294967295ULL);
}
flight_held::Settings flight_settings(const FlightPacket& a,std::size_t o) {
    flight_held::Settings s;
    s.mesh={flight_uint(a[o]),{unsigned(flight_uint(a[o+1])),unsigned(flight_uint(a[o+2])),unsigned(flight_uint(a[o+3])),a[o+4],a[o+5],a[o+6]}};
    s.time_tolerance=a[o+7];s.max_evaluations=flight_uint(a[o+8]);s.max_leaves=flight_uint(a[o+9]);s.max_depth=unsigned(flight_uint(a[o+10]));
    s.enclosure_sqrt_refinements=unsigned(flight_uint(a[o+11]));s.max_total_sqrt_refinements=flight_uint(a[o+12]);return s;
}
void flight_body_packet(FlightPacket& a,const dyn::RigidBody& b) {
    a[0]=double(b.id);a[1]=b.is_static?1:0;a[2]=b.mass;a[3]=b.radius;put_vector(a,4,b.inertia_diagonal);put_vector(a,7,b.position);
    a[10]=b.orientation.x;a[11]=b.orientation.y;a[12]=b.orientation.z;a[13]=b.orientation.w;put_vector(a,14,b.velocity);put_vector(a,17,b.angular_momentum);
    put_vector(a,20,b.force);put_vector(a,23,b.torque);a[26]=b.material.restitution;a[27]=b.material.friction;
}
dyn::RigidBody flight_body_input(const FlightPacket& a) {
    dyn::RigidBody b;b.id=id_from(a[0]);const auto flag=std::bit_cast<uint64_t>(a[1]);
    require(flag==0||flag==0x8000000000000000ULL||flag==0x3ff0000000000000ULL,PP_SIM_INVALID_ARGUMENT,"Flight static flag must be 0 or 1");b.is_static=flag==0x3ff0000000000000ULL;
    b.mass=a[2];b.radius=a[3];b.inertia_diagonal=flight_vector(a,4);b.position=flight_vector(a,7);b.orientation={a[10],a[11],a[12],a[13]};
    b.velocity=flight_vector(a,14);b.angular_momentum=flight_vector(a,17);b.force=flight_vector(a,20);b.torque=flight_vector(a,23);b.material={a[26],a[27]};return b;
}
FlightPacket flight_held_input_packet(const flight_held::HeldSphere& x,double horizon,const flight_held::Settings& settings) {
    FlightPacket a{};a[0]=double(x.id);put_vector(a,1,x.position);put_vector(a,4,x.velocity);a[7]=x.mass;put_vector(a,8,x.force);put_vector(a,11,x.gravity);a[14]=x.radius;a[15]=horizon;flight_settings_packet(a,16,settings);return a;
}
flight_held::HeldSphere flight_held_input(const FlightPacket& a) {return {id_from(a[0]),flight_vector(a,1),flight_vector(a,4),a[7],flight_vector(a,8),flight_vector(a,11),a[14]};}
const flight_held::Result* flight_held_result(const FlightRecord& record) {
    if(record.held) {return &*record.held;}
    return record.guard&&record.guard->inflated?&*record.guard->inflated:nullptr;
}
const sphere_mesh::Result* flight_mesh(const FlightRecord& record) {const auto* r=flight_held_result(record);return r&&r->last_mesh?&*r->last_mesh:nullptr;}
void flight_work(FlightPacket& a,std::size_t o,const flight_held::Work& w) {
    a[o]=double(w.mesh_queries);a[o+1]=double(w.primitive_queries);a[o+2]=double(w.candidates_examined);a[o+3]=double(w.primitive_sqrt_refinements);a[o+4]=double(w.enclosure_sqrt_refinements);
    a[o+5]=double(w.sqrt_refinements);a[o+6]=double(w.sqrt_refinements_upper);a[o+7]=double(w.mesh_sqrt_limited_rows);a[o+8]=double(w.enclosure_sqrt_calls);a[o+9]=double(w.enclosure_sqrt_limited_calls);a[o+10]=w.exact?1:0;
}
FlightPacket flight_summary(const FlightRecord& record) {
    FlightPacket a{};a[0]=record.mode;a[3]=double(record.source.size());const auto* h=flight_held_result(record);a[15]=h?1:0;
    if(record.held) {const auto& r=*record.held;a[1]=unsigned(r.status);a[2]=unsigned(r.reason);a[4]=r.snapshot?1:0;a[5]=r.failed_index?1:0;if(r.failed_index){a[6]=double(*r.failed_index);}a[7]=r.world_body?1:0;}
    if(record.guard) {const auto& r=*record.guard;a[1]=unsigned(r.status);a[2]=unsigned(r.reason);a[4]=r.snapshot?1:0;a[5]=r.failed_index?1:0;if(r.failed_index){a[6]=double(*r.failed_index);}
        a[7]=r.world_body?1:0;a[8]=r.tube?1:0;a[9]=r.flight_failure?1:0;if(r.flight_failure){a[10]=unsigned(*r.flight_failure);}a[11]=r.candidate_evaluated?1:0;a[12]=r.endpoint?1:0;a[13]=r.inflated?1:0;a[14]=r.candidate?1:0;}
    return a;
}
FlightPacket flight_held_header(const flight_held::Result& r,std::size_t n) {
    FlightPacket a{};a[0]=unsigned(r.status);a[1]=unsigned(r.reason);a[2]=double(n);a[3]=r.snapshot?1:0;a[4]=r.failed_index?1:0;if(r.failed_index){a[5]=double(*r.failed_index);}
    a[6]=r.world_body?1:0;a[7]=r.acceleration?1:0;a[8]=r.whole_path_bounds?1:0;a[9]=r.whole_velocity_bounds?1:0;a[10]=r.initial?1:0;a[11]=r.initial_separation_proven?1:0;
    a[12]=double(r.certified_leaves.size());a[13]=double(r.partition.size());a[14]=double(r.frontier.size());a[15]=double(r.audits.size());a[16]=r.safe_prefix?1:0;if(r.safe_prefix){a[17]=(*r.safe_prefix)[0];a[18]=(*r.safe_prefix)[1];}
    a[19]=r.best_witness?1:0;a[20]=r.window?1:0;a[21]=double(r.candidate_surface_ids.size());a[22]=r.current?1:0;a[23]=r.last_mesh?1:0;a[24]=r.last_mesh_audit_index?1:0;if(r.last_mesh_audit_index){a[25]=double(*r.last_mesh_audit_index);}
    a[26]=double(r.partition_leaves);a[27]=r.maximum_depth;flight_work(a,28,r.work);return a;
}
FlightPacket flight_audit_packet(const flight_held::CellAudit& r,std::size_t index) {
    FlightPacket a{};a[0]=double(index);a[1]=unsigned(r.kind);a[2]=r.cell.time_bounds[0];a[3]=r.cell.time_bounds[1];a[4]=r.cell.depth;a[5]=r.time;a[6]=unsigned(r.outcome);
    a[7]=r.path_bounds?1:0;if(r.path_bounds){put_bounds(a,8,*r.path_bounds);}a[14]=r.point_bounds?1:0;if(r.point_bounds){put_bounds(a,15,*r.point_bounds);}a[21]=r.anchor?1:0;if(r.anchor){put_vector(a,22,*r.anchor);}
    a[25]=r.mesh_queried?1:0;a[26]=r.mesh_status?1:0;if(r.mesh_status){a[27]=unsigned(*r.mesh_status);}a[28]=r.mesh_reason?1:0;if(r.mesh_reason){a[29]=unsigned(*r.mesh_reason);}
    const auto optional_interval=[&](std::size_t flag,const auto& v){a[flag]=v?1:0;if(v){flight_interval(a,flag+1,*v);}};
    optional_interval(30,r.distance);optional_interval(33,r.displacement_squared_bound);optional_interval(36,r.error_squared_bound);optional_interval(39,r.displacement_root);optional_interval(42,r.error_root);optional_interval(45,r.clearance_certificate);optional_interval(48,r.penetration_certificate);flight_work(a,51,r.work);return a;
}
FlightPacket flight_leaf_packet(const flight_held::CertifiedLeaf& r) {FlightPacket a{};a[0]=r.cell.time_bounds[0];a[1]=r.cell.time_bounds[1];a[2]=r.cell.depth;flight_interval(a,3,r.lower_gap_certificate);a[5]=double(r.audit_index);return a;}
FlightPacket flight_partition_packet(const flight_held::PartitionLeaf& r,std::size_t index) {FlightPacket a{};a[0]=double(index);a[1]=r.cell.time_bounds[0];a[2]=r.cell.time_bounds[1];a[3]=r.cell.depth;a[4]=unsigned(r.state);a[5]=r.audit_index?1:0;if(r.audit_index){a[6]=double(*r.audit_index);}a[7]=unsigned(r.blocked_reason);return a;}
FlightPacket flight_cell_packet(const flight_held::Cell& r,std::size_t index) {FlightPacket a{};a[0]=double(index);a[1]=r.time_bounds[0];a[2]=r.time_bounds[1];a[3]=r.depth;return a;}
FlightPacket flight_initial_packet(const flight_held::InitialProof& r) {FlightPacket a{};flight_interval(a,1,r.lower_gap_certificate);flight_interval(a,3,r.upper_gap_certificate);a[5]=double(r.audit_index);return a;}
FlightPacket flight_witness_packet(const flight_held::Witness& r) {FlightPacket a{};a[1]=r.cell.time_bounds[0];a[2]=r.cell.time_bounds[1];a[3]=r.cell.depth;a[4]=r.time;put_bounds(a,5,r.exact_path_bounds);put_vector(a,11,r.anchor);a[14]=r.error_upper;flight_interval(a,15,r.upper_gap_certificate);a[17]=double(r.audit_index);return a;}
FlightPacket flight_window_packet(const flight_held::EntryWindow& r) {FlightPacket a{};a[1]=r.time_bounds[0];a[2]=r.time_bounds[1];flight_interval(a,3,r.time_width);put_bounds(a,5,r.path_bounds);flight_interval(a,11,r.l1_diameter_bound);a[13]=double(r.witness_audit_index);return a;}
FlightPacket flight_tube_packet(const flight_guard::Tube& r) {FlightPacket a{};put_vector(a,0,r.nominal_acceleration);put_bounds(a,3,r.exact_acceleration);put_bounds(a,9,r.acceleration_difference);a[15]=r.position_error;a[16]=r.roundoff;a[17]=r.guard_radius;return a;}
FlightPacket flight_endpoint_packet(const flight_guard::EndpointAudit& r) {FlightPacket a{};put_bounds(a,0,r.nominal_position);put_bounds(a,6,r.nominal_allowed);put_bounds(a,12,r.exact_position);put_bounds(a,18,r.exact_allowed);put_bounds(a,24,r.exact_difference);flight_interval(a,30,r.l1_error_bound);a[32]=r.nominal_contained?1:0;a[33]=r.exact_contained?1:0;a[34]=r.l1_within_tube?1:0;return a;}
}

namespace {
void validate_flight_held(const FlightRecord& record,const flight_held::Result& r,const flight_held::HeldSphere& input,double horizon,const flight_held::Settings& s) {
    using State=flight_held::LeafState;using Outcome=flight_held::Outcome;
    const auto n=record.source.size();
    const auto same=[](double a,double b){return std::bit_cast<uint64_t>(a)==std::bit_cast<uint64_t>(b);};
    const auto same_vector=[&](Vec3 a,Vec3 b){return same(a.x,b.x)&&same(a.y,b.y)&&same(a.z,b.z);};
    const auto same_interval=[&](const auto& a,const auto& b){return same(a.lower(),b.lower())&&same(a.upper(),b.upper());};
    const auto same_cell=[&](const flight_held::Cell& a,const flight_held::Cell& b){return a.depth==b.depth&&same(a.time_bounds[0],b.time_bounds[0])&&same(a.time_bounds[1],b.time_bounds[1]);};
    const auto initial_cell=[](const flight_held::Cell& c){return c.time_bounds[0]==0&&c.time_bounds[1]==0&&c.depth==0;};
    const auto regular_cell=[horizon](const flight_held::Cell& c){return std::isfinite(c.time_bounds[0])&&std::isfinite(c.time_bounds[1])&&c.time_bounds[0]>=0&&c.time_bounds[0]<c.time_bounds[1]&&c.time_bounds[1]<=horizon&&c.depth<=32;};
    require(n<=64&&unsigned(r.status)<=unsigned(flight_held::Status::numerical_failure)&&unsigned(r.reason)<=unsigned(flight_held::Reason::derived_domain),PP_SIM_CORE_REJECTED,"Invalid flight held enum/source capacity");
    require((!r.failed_index||*r.failed_index<n)&&r.audits.size()<=256&&r.certified_leaves.size()<=128&&r.partition.size()<=128&&r.frontier.size()<=128&&r.partition_leaves==r.partition.size()&&r.maximum_depth<=32,PP_SIM_CORE_REJECTED,"Invalid flight held diagnostic counts");
    const bool resolved=r.status==flight_held::Status::entry_window||r.status==flight_held::Status::separated||r.status==flight_held::Status::initial_penetration;
    require(resolved?r.reason==flight_held::Reason::none:r.reason!=flight_held::Reason::none,PP_SIM_CORE_REJECTED,"Invalid flight held status/reason");
    require(r.window.has_value()==(r.status==flight_held::Status::entry_window)&&r.last_mesh.has_value()==r.last_mesh_audit_index.has_value(),PP_SIM_CORE_REJECTED,"Invalid flight held completion flags");
    require(!r.world_body,PP_SIM_CORE_REJECTED,"Raw/nested held result unexpectedly contains a World body");
    if(r.snapshot) {
        const auto& x=*r.snapshot;
        const auto actual=flight_held_input_packet(x.input,x.horizon,x.settings),expected=flight_held_input_packet(input,horizon,s);
        for(unsigned i=0;i<32;++i) {require(flight_same(actual[i],expected[i]),PP_SIM_CORE_REJECTED,"Held snapshot changed input/settings bits");}
        require(x.triangles.size()==n,PP_SIM_CORE_REJECTED,"Held snapshot changed source count");
        for(std::size_t i=0;i<n;++i) {require(same_source(x.triangles[i],record.source[i]),PP_SIM_CORE_REJECTED,"Held snapshot changed source bits");}
        require(r.audits.size()<=s.max_evaluations&&r.work.mesh_queries<=s.max_evaluations&&r.partition.size()<=s.max_leaves&&r.maximum_depth<=s.max_depth&&r.work.sqrt_refinements_upper<=s.max_total_sqrt_refinements,PP_SIM_CORE_REJECTED,"Held exceeds profile");
    }else {
        require(r.audits.empty()&&r.partition.empty()&&r.certified_leaves.empty()&&r.frontier.empty()&&!r.initial&&!r.initial_separation_proven&&!r.safe_prefix&&!r.best_witness&&!r.current&&!r.last_mesh&&!r.acceleration&&!r.whole_path_bounds&&!r.whole_velocity_bounds,PP_SIM_CORE_REJECTED,"Held diagnostics without snapshot");
    }
    require((!r.whole_path_bounds||r.acceleration)&&(!r.whole_velocity_bounds||r.whole_path_bounds)&&(!r.initial||r.whole_velocity_bounds),PP_SIM_CORE_REJECTED,"Held derived diagnostics out of execution order");
    if(r.acceleration) {
        const double g[3]{input.gravity.x,input.gravity.y,input.gravity.z},f[3]{input.force.x,input.force.y,input.force.z};
        for(unsigned k=0;k<3;++k) {const auto exact=FlightInterval::point(g[k])+FlightInterval::point(f[k])/FlightInterval::point(input.mass);require(flight_same_interval((*r.acceleration)[k],exact),PP_SIM_CORE_REJECTED,"Held acceleration changed exact F/m construction");}
    }
    for(const auto* bounds:{&r.acceleration,&r.whole_path_bounds,&r.whole_velocity_bounds}) {if(*bounds) {FlightPacket a{};put_bounds(a,1,**bounds);finite_output(a,8);}}
    const auto work_valid=[](const flight_held::Work& w){
        require(w.mesh_queries<=256&&w.primitive_queries<=16384&&w.candidates_examined<=114688&&w.primitive_sqrt_refinements<=8388608&&w.enclosure_sqrt_refinements<=262144&&w.sqrt_refinements<=8650752&&w.sqrt_refinements==w.primitive_sqrt_refinements+w.enclosure_sqrt_refinements&&w.sqrt_refinements<=w.sqrt_refinements_upper&&w.sqrt_refinements_upper<=16777216&&
            (!w.exact||w.sqrt_refinements_upper==w.sqrt_refinements)&&w.mesh_sqrt_limited_rows<=w.primitive_queries&&w.enclosure_sqrt_calls<=512&&w.enclosure_sqrt_limited_calls<=w.enclosure_sqrt_calls,PP_SIM_CORE_REJECTED,"Invalid flight held work accounting");
    };
    work_valid(r.work);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> sums{};bool exact=true;unsigned maximum_depth=0;std::optional<std::size_t> best;
    unsigned previous_depth=0;double previous_left=0;bool previous_cell=false;
    for(std::size_t i=0;i<r.audits.size();++i){const auto& a=r.audits[i];const bool initial=a.kind==flight_held::AuditKind::initial_point;
        require(unsigned(a.kind)<=unsigned(flight_held::AuditKind::cell)&&unsigned(a.outcome)<=unsigned(Outcome::unresolved)&&((i==0)==initial),PP_SIM_CORE_REJECTED,"Invalid flight held audit kind/order/outcome");
        require(initial?(initial_cell(a.cell)&&same(a.time,0)):(regular_cell(a.cell)&&same(a.time,std::midpoint(a.cell.time_bounds[0],a.cell.time_bounds[1]))),PP_SIM_CORE_REJECTED,"Invalid flight held audit parameter/cell");
        maximum_depth=std::max(maximum_depth,a.cell.depth);
        if(!initial) {
            require(!previous_cell||a.cell.depth>previous_depth||(a.cell.depth==previous_depth&&a.cell.time_bounds[0]>previous_left),PP_SIM_CORE_REJECTED,"Held audit order is not breadth-first/left-tied");
            previous_cell=true;previous_depth=a.cell.depth;previous_left=a.cell.time_bounds[0];
        }
        require(a.mesh_status.has_value()==a.mesh_reason.has_value()&&(!a.mesh_status||a.mesh_queried)&&(!a.mesh_status||unsigned(*a.mesh_status)<=unsigned(sphere_mesh::Status::unsupported_environment))&&(!a.mesh_reason||unsigned(*a.mesh_reason)<=unsigned(sphere_mesh::Reason::environment)),PP_SIM_CORE_REJECTED,"Invalid flight held audit mesh flags");
        work_valid(a.work);require(a.work.mesh_queries==(a.mesh_queried?1u:0u)&&a.work.primitive_queries<=n&&a.work.candidates_examined<=n*7&&a.work.primitive_sqrt_refinements<=n*512&&a.work.enclosure_sqrt_calls<=2&&a.work.enclosure_sqrt_refinements<=1024,PP_SIM_CORE_REJECTED,"Invalid flight held audit work bounds");
        require((!a.point_bounds||a.path_bounds)&&(!a.anchor||a.point_bounds)&&(!a.mesh_queried||a.anchor)&&(!a.distance||(a.mesh_status&&*a.mesh_status==sphere_mesh::Status::completed&&a.distance->strictly_positive())),PP_SIM_CORE_REJECTED,"Held audit optional execution order changed");
        require((!a.displacement_squared_bound||a.distance)&&(!a.error_squared_bound||a.displacement_squared_bound)&&(!a.displacement_root||a.error_squared_bound)&&(!a.error_root||a.displacement_root)&&(!a.clearance_certificate||a.error_root)&&(!a.penetration_certificate||a.clearance_certificate),PP_SIM_CORE_REJECTED,"Held proof execution order changed");
        for(const auto* squared:{&a.displacement_squared_bound,&a.error_squared_bound}) {if(*squared){require((**squared).upper()>=0,PP_SIM_CORE_REJECTED,"Invalid held squared bound");}}
        for(const auto* root:{&a.displacement_root,&a.error_root}) {if(*root){require((**root).lower()>=0,PP_SIM_CORE_REJECTED,"Invalid held nonnegative root");}}
        const std::size_t returned_roots=(a.displacement_root?1u:0u)+(a.error_root?1u:0u);
        if(!a.work.exact) {
            require(i+1==r.audits.size()&&!resolved,PP_SIM_CORE_REJECTED,"Held continued or succeeded after unknown work");
            if(a.work.enclosure_sqrt_calls==0) {require(a.mesh_queried&&!a.distance&&!a.displacement_root&&!a.error_root&&a.work.sqrt_refinements_upper==n*512,PP_SIM_CORE_REJECTED,"Unknown mesh block lost its full reservation");}
            else {require(a.mesh_status&&*a.mesh_status==sphere_mesh::Status::completed&&a.work.enclosure_sqrt_calls==returned_roots+1&&a.work.sqrt_refinements_upper==a.work.sqrt_refinements+512,PP_SIM_CORE_REJECTED,"Unknown enclosure block lost its reservation");}
        }else {require(a.work.enclosure_sqrt_calls==returned_roots,PP_SIM_CORE_REJECTED,"Held exact root call/return counts differ");}
        if(a.outcome==Outcome::separated) {require(a.clearance_certificate&&a.penetration_certificate&&a.clearance_certificate->strictly_positive(),PP_SIM_CORE_REJECTED,"Held separated audit lacks proof");}
        if(a.outcome==Outcome::split) {
            const bool proof=a.clearance_certificate&&a.penetration_certificate;
            require(a.work.exact&&(proof||(a.mesh_status&&*a.mesh_status==sphere_mesh::Status::row_failure))&&a.cell.depth<s.max_depth,PP_SIM_CORE_REJECTED,"Held split lacks an exact returned result");
        }
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> w{};flight_work(w,0,a.work);
        for(unsigned k=0;k<10;++k){sums[k]+=w[k];}
        exact=exact&&a.work.exact;
        if(!initial&&a.penetration_certificate&&a.penetration_certificate->strictly_negative()&&(!best||a.time<r.audits[*best].time)){best=i;}
        finite_output(flight_audit_packet(a,i),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_AUDIT_COUNT);
    }
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> totals{};flight_work(totals,0,r.work);
    for(unsigned k=0;k<10;++k){require(totals[k]==sums[k],PP_SIM_CORE_REJECTED,"Flight held audit delta/global counters differ");}
    require(r.work.exact==exact,PP_SIM_CORE_REJECTED,"Flight held audit/global exact flags differ");
    if(r.initial){const auto& p=*r.initial;require(p.audit_index==0&&!r.audits.empty(),PP_SIM_CORE_REJECTED,"Invalid flight held initial proof ordinal");const auto& a=r.audits[0];
        require(a.kind==flight_held::AuditKind::initial_point&&a.clearance_certificate&&a.penetration_certificate&&same_interval(p.lower_gap_certificate,*a.clearance_certificate)&&same_interval(p.upper_gap_certificate,*a.penetration_certificate)&&r.initial_separation_proven==p.lower_gap_certificate.strictly_positive(),PP_SIM_CORE_REJECTED,"Flight held initial proof changed audit certificates");
        finite_output(flight_initial_packet(p),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_INITIAL_COUNT);
    }else{require(!r.initial_separation_proven,PP_SIM_CORE_REJECTED,"Flight held initial flag lacks proof");}
    if(r.status==flight_held::Status::initial_penetration){require(r.initial&&r.initial->upper_gap_certificate.strictly_negative()&&!r.initial_separation_proven&&!r.safe_prefix&&!r.best_witness,PP_SIM_CORE_REJECTED,"Invalid flight held initial penetration");}
    require(r.best_witness.has_value()==best.has_value(),PP_SIM_CORE_REJECTED,"Flight held best-witness presence differs from audits");
    if(r.best_witness){const auto& w=*r.best_witness;require(best&&w.audit_index==*best,PP_SIM_CORE_REJECTED,"Flight held best witness is not earliest proven point");const auto& a=r.audits[*best];
        require(r.initial_separation_proven&&same_cell(w.cell,a.cell)&&same(w.time,a.time)&&a.point_bounds&&a.anchor&&same_vector(w.anchor,*a.anchor)&&a.error_root&&same(w.error_upper,a.error_root->upper())&&a.penetration_certificate&&same_interval(w.upper_gap_certificate,*a.penetration_certificate)&&w.upper_gap_certificate.strictly_negative(),PP_SIM_CORE_REJECTED,"Flight held negative witness changed audit link");
        for(unsigned k=0;k<3;++k){require(same_interval(w.exact_path_bounds[k],(*a.point_bounds)[k]),PP_SIM_CORE_REJECTED,"Flight held witness changed exact-path bounds");}
        finite_output(flight_witness_packet(w),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_WITNESS_COUNT);
    }
    double end=0,safe=0;std::size_t frontier=0,certified=0,current_count=0;bool prefix=true;
    for(std::size_t i=0;i<r.partition.size();++i){const auto& l=r.partition[i];
        require(regular_cell(l.cell)&&same(l.cell.time_bounds[0],end)&&unsigned(l.state)<=unsigned(State::current)&&unsigned(l.blocked_reason)<=unsigned(flight_held::Reason::derived_domain)&&(!l.audit_index||*l.audit_index<r.audits.size()),PP_SIM_CORE_REJECTED,"Invalid flight held full partition/enum/link");end=l.cell.time_bounds[1];
        if(l.audit_index){require(same_cell(l.cell,r.audits[*l.audit_index].cell),PP_SIM_CORE_REJECTED,"Flight held partition audit belongs to another cell");}
        if(l.state==State::unqueried){require(!l.audit_index&&l.blocked_reason==flight_held::Reason::none&&frontier<r.frontier.size()&&same_cell(l.cell,r.frontier[frontier]),PP_SIM_CORE_REJECTED,"Flight held unqueried/frontier changed");++frontier;}
        if(l.state==State::certified){require(l.audit_index&&l.blocked_reason==flight_held::Reason::none&&certified<r.certified_leaves.size(),PP_SIM_CORE_REJECTED,"Flight held certified partition lacks proof leaf");const auto& proof=r.certified_leaves[certified++];const auto& a=r.audits[*l.audit_index];
            require(proof.audit_index==*l.audit_index&&same_cell(proof.cell,l.cell)&&a.outcome==Outcome::separated&&a.clearance_certificate&&same_interval(proof.lower_gap_certificate,*a.clearance_certificate)&&proof.lower_gap_certificate.strictly_positive(),PP_SIM_CORE_REJECTED,"Flight held certified island changed audit proof");if(prefix){safe=l.cell.time_bounds[1];}
        }else{prefix=false;}
        if(l.state==State::unresolved){require(l.audit_index&&r.audits[*l.audit_index].outcome==Outcome::unresolved,PP_SIM_CORE_REJECTED,"Flight held unresolved partition lacks real audit");}
        if(l.state==State::current){require(r.current&&same_cell(l.cell,*r.current),PP_SIM_CORE_REJECTED,"Flight held stopped partition lacks current");++current_count;}
        finite_output(flight_partition_packet(l,i),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_PARTITION_COUNT);
    }
    require((r.partition.empty()||end==horizon)&&frontier==r.frontier.size()&&certified==r.certified_leaves.size()&&current_count<=1,PP_SIM_CORE_REJECTED,"Incomplete flight held partition/frontier/island mapping");
    require(r.safe_prefix.has_value()==r.initial_separation_proven&&(!r.safe_prefix||(same((*r.safe_prefix)[0],0)&&same((*r.safe_prefix)[1],safe))),PP_SIM_CORE_REJECTED,"Flight held safe prefix is not continuous certified cover");
    for(const auto& l:r.certified_leaves){finite_output(flight_leaf_packet(l),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_LEAF_COUNT);}
    for(std::size_t i=0;i<r.frontier.size();++i){finite_output(flight_cell_packet(r.frontier[i],i),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_CELL_COUNT);}
    if(r.current){require(regular_cell(*r.current)||initial_cell(*r.current),PP_SIM_CORE_REJECTED,"Invalid flight held stopped current cell");maximum_depth=std::max(maximum_depth,r.current->depth);
        require(initial_cell(*r.current)?current_count==0:current_count==1,PP_SIM_CORE_REJECTED,"Flight held current/partition membership mismatch");finite_output(flight_cell_packet(*r.current,0),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_CELL_COUNT);
    }else{require(current_count==0,PP_SIM_CORE_REJECTED,"Flight held partition has missing current");}
    require(maximum_depth==r.maximum_depth,PP_SIM_CORE_REJECTED,"Flight held maximum popped depth differs");
    if(r.status==flight_held::Status::separated){require(r.initial_separation_proven&&r.work.exact&&r.safe_prefix&&safe==horizon&&!r.best_witness&&!r.current&&r.frontier.empty()&&certified==r.partition.size(),PP_SIM_CORE_REJECTED,"Incomplete successful flight held separation cover");}
    if(r.window){const auto& w=*r.window;require(r.snapshot&&r.initial_separation_proven&&r.work.exact&&r.safe_prefix&&r.best_witness&&same(w.time_bounds[0],safe)&&same(w.time_bounds[1],r.best_witness->time)&&w.time_bounds[0]<w.time_bounds[1]&&w.witness_audit_index==r.best_witness->audit_index&&w.time_width.upper()<=s.time_tolerance,PP_SIM_CORE_REJECTED,"Invalid flight held window proof conditions");
        const auto width=pikapika::interval::Interval::point(w.time_bounds[1])-pikapika::interval::Interval::point(w.time_bounds[0]);require(same_interval(w.time_width,width),PP_SIM_CORE_REJECTED,"Flight held window width changed original subtraction enclosure");
        auto diameter=FlightInterval::point(0);for(const auto& component:w.path_bounds){diameter=diameter+(FlightInterval::point(component.upper())-FlightInterval::point(component.lower()));}
        require(flight_same_interval(diameter,w.l1_diameter_bound),PP_SIM_CORE_REJECTED,"Held window L1 diagnostic changed box widths");
        std::vector<uint64_t> ids;ids.reserve(n);for(const auto& t:record.source){ids.push_back(t.id);}std::sort(ids.begin(),ids.end());require(ids==r.candidate_surface_ids,PP_SIM_CORE_REJECTED,"Flight held conservative all-source IDs changed");finite_output(flight_window_packet(w),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_WINDOW_COUNT);
    }else{require(r.candidate_surface_ids.empty(),PP_SIM_CORE_REJECTED,"Flight held IDs without accepted window");}
    if(r.last_mesh){require(*r.last_mesh_audit_index<r.audits.size(),PP_SIM_CORE_REJECTED,"Invalid flight held last-mesh ordinal");const auto& a=r.audits[*r.last_mesh_audit_index];const auto& m=*r.last_mesh;
        require(a.mesh_queried&&a.mesh_status&&a.mesh_reason&&*a.mesh_status==m.status&&*a.mesh_reason==m.reason&&a.work.primitive_queries==m.queries&&a.work.candidates_examined==m.candidates_examined&&a.work.primitive_sqrt_refinements==m.sqrt_refinements&&a.work.mesh_sqrt_limited_rows==m.sqrt_limited_rows,PP_SIM_CORE_REJECTED,"Flight held last-mesh link/counters changed");validate_sphere_triangle_mesh(record.source,m,s.mesh.primitive);
    }
    for(std::size_t i=0;i<n;++i){finite_output(sphere_triangle_mesh_source_packet(record.source,r.last_mesh?&*r.last_mesh:nullptr,i),PP_SIM_SPHERE_TRIANGLE_MESH_SOURCE_COUNT);}
    finite_output(flight_held_header(r,n),PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_HELD_HEADER_COUNT);
}
}

namespace {
FlightPacket flight_original(const FlightRecord& record) {FlightPacket a{};std::copy(record.input.begin(),record.input.end(),a.begin());return a;}
FlightPacket flight_guard_snapshot(const flight_guard::Snapshot& s) {FlightPacket a{};flight_body_packet(a,s.body);put_vector(a,28,s.gravity);a[31]=s.horizon;flight_settings_packet(a,32,s.settings.held_load);a[45]=s.settings.max_angular_increment;return a;}
FlightPacket flight_record_packet(const FlightRecord& record,uint32_t kind,uint32_t index,uint32_t& count) {
    FlightPacket a{};const auto* h=flight_held_result(record);count=0;
    const auto scalar_index=[&]{require(index==0,PP_SIM_INVALID_ARGUMENT,"Flight optional record requires ordinal zero");};
    switch(kind) {
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_INPUT:
        scalar_index();a=flight_original(record);count=record.mode==0?32u:48u;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_SOURCE:
        require(index<record.source.size(),PP_SIM_INVALID_ARGUMENT,"Missing flight source ordinal");a=sphere_triangle_mesh_source_packet(record.source,flight_mesh(record),index);count=14;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_SNAPSHOT:
        scalar_index();
        if(record.mode==0) {require(record.held&&record.held->snapshot,PP_SIM_INVALID_ARGUMENT,"No held Native snapshot");const auto& x=*record.held->snapshot;a=flight_held_input_packet(x.input,x.horizon,x.settings);count=32;}
        else {require(record.guard&&record.guard->snapshot,PP_SIM_INVALID_ARGUMENT,"No guard Native snapshot");a=flight_guard_snapshot(*record.guard->snapshot);count=48;}break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_HELD_HEADER:
        scalar_index();require(h!=nullptr,PP_SIM_INVALID_ARGUMENT,"No executed held result");a=flight_held_header(*h,record.source.size());count=48;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_HELD_INPUT:
        scalar_index();require(h&&h->snapshot,PP_SIM_INVALID_ARGUMENT,"No held input snapshot");a=flight_held_input_packet(h->snapshot->input,h->snapshot->horizon,h->snapshot->settings);count=32;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_WORLD_BODY:
        scalar_index();require(record.guard&&record.guard->world_body,PP_SIM_INVALID_ARGUMENT,"No captured guard body");flight_body_packet(a,record.guard->world_body->body);put_vector(a,28,record.guard->world_body->gravity);count=32;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_TUBE:
        scalar_index();require(record.guard&&record.guard->tube,PP_SIM_INVALID_ARGUMENT,"No guard tube");a=flight_tube_packet(*record.guard->tube);count=24;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_ENDPOINT:
        scalar_index();require(record.guard&&record.guard->endpoint,PP_SIM_INVALID_ARGUMENT,"No guard endpoint audit");a=flight_endpoint_packet(*record.guard->endpoint);count=40;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_BODY_CANDIDATE:
        scalar_index();require(record.guard&&record.guard->candidate,PP_SIM_INVALID_ARGUMENT,"No completed guard candidate");flight_body_packet(a,*record.guard->candidate);count=32;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_ACCELERATION:
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_WHOLE_PATH:
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_WHOLE_VELOCITY: {
        scalar_index();require(h!=nullptr,PP_SIM_INVALID_ARGUMENT,"No executed held bounds");const auto& bounds=kind==9?h->acceleration:kind==10?h->whole_path_bounds:h->whole_velocity_bounds;
        require(bounds.has_value(),PP_SIM_INVALID_ARGUMENT,"Absent held bounds");put_bounds(a,1,*bounds);count=8;break;}
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_AUDIT:
        require(h&&index<h->audits.size(),PP_SIM_INVALID_ARGUMENT,"Missing held audit ordinal");a=flight_audit_packet(h->audits[index],index);count=64;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_LEAF:
        require(h&&index<h->certified_leaves.size(),PP_SIM_INVALID_ARGUMENT,"Missing held island ordinal");a=flight_leaf_packet(h->certified_leaves[index]);count=6;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_PARTITION:
        require(h&&index<h->partition.size(),PP_SIM_INVALID_ARGUMENT,"Missing held partition ordinal");a=flight_partition_packet(h->partition[index],index);count=8;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_FRONTIER:
        require(h&&index<h->frontier.size(),PP_SIM_INVALID_ARGUMENT,"Missing held frontier ordinal");a=flight_cell_packet(h->frontier[index],index);count=4;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_CURRENT:
        scalar_index();require(h&&h->current,PP_SIM_INVALID_ARGUMENT,"No held stopped current");a=flight_cell_packet(*h->current,0);count=4;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_INITIAL:
        scalar_index();require(h&&h->initial,PP_SIM_INVALID_ARGUMENT,"No held initial proof");a=flight_initial_packet(*h->initial);count=6;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_WITNESS:
        scalar_index();require(h&&h->best_witness,PP_SIM_INVALID_ARGUMENT,"No held negative witness");a=flight_witness_packet(*h->best_witness);count=18;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_WINDOW:
        scalar_index();require(h&&h->window,PP_SIM_INVALID_ARGUMENT,"No held window");a=flight_window_packet(*h->window);count=14;break;
    case PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_SURFACE_ID:
        require(h&&index<h->candidate_surface_ids.size(),PP_SIM_INVALID_ARGUMENT,"Missing conservative flight ID ordinal");a[0]=index;a[1]=double(h->candidate_surface_ids[index]);count=2;break;
    default:throw Failure{PP_SIM_INVALID_ARGUMENT,"Unknown flight record kind"};
    }
    return a;
}
void flight_check_source(const std::vector<sphere_tri::StaticTriangle>& actual,const FlightRecord& record) {
    require(actual.size()==record.source.size(),PP_SIM_CORE_REJECTED,"Flight snapshot source size changed");
    for(std::size_t i=0;i<actual.size();++i) {require(same_source(actual[i],record.source[i]),PP_SIM_CORE_REJECTED,"Flight snapshot source bits changed");}
}
void flight_check_packets_equal(const FlightPacket& a,const FlightPacket& b,unsigned count) {
    for(unsigned i=0;i<count;++i) {require(flight_same(a[i],b[i]),PP_SIM_CORE_REJECTED,"Flight normalized snapshot bits changed");}
}
void flight_validate_guard(const FlightRecord& record,const FlightPacket& input,const flight_guard::Settings& settings) {
    const auto& r=*record.guard;const auto body=flight_body_input(input);const auto gravity=flight_vector(input,28);const double horizon=input[31];
    require(unsigned(r.status)<=unsigned(flight_guard::Status::numerical_failure)&&unsigned(r.reason)<=unsigned(flight_guard::Reason::coverage_inconsistent)&&(!r.failed_index||*r.failed_index<record.source.size()),PP_SIM_CORE_REJECTED,"Invalid guard model enum/index");
    const bool success=r.status==flight_guard::Status::certified_separated;
    require((success?r.reason==flight_guard::Reason::none:r.reason!=flight_guard::Reason::none)&&r.candidate.has_value()==success,PP_SIM_CORE_REJECTED,"Invalid guard completion flags");
    if(r.world_body) {
        FlightPacket a{},b{};flight_body_packet(a,r.world_body->body);put_vector(a,28,r.world_body->gravity);flight_body_packet(b,body);put_vector(b,28,gravity);flight_check_packets_equal(a,b,32);
        // Invalid captured body is an owned FAILURE diagnostic, not a candidate.
        finite_output(a,32);
    }else {require(r.status==flight_guard::Status::unsupported_environment||r.reason==flight_guard::Reason::allocation_failure,PP_SIM_CORE_REJECTED,"Missing captured guard body");}
    if(r.snapshot) {
        FlightPacket expected{};flight_body_packet(expected,body);put_vector(expected,28,gravity);expected[31]=horizon;flight_settings_packet(expected,32,settings.held_load);expected[45]=settings.max_angular_increment;
        flight_check_packets_equal(flight_guard_snapshot(*r.snapshot),expected,48);flight_check_source(r.snapshot->triangles,record);
    }else {require(!r.tube&&!r.flight_failure&&!r.candidate_evaluated&&!r.endpoint&&!r.inflated&&!r.candidate,PP_SIM_CORE_REJECTED,"Guard execution without original snapshot");}
    if(r.flight_failure) {require(unsigned(*r.flight_failure)>0&&unsigned(*r.flight_failure)<=unsigned(dyn::CcdFailure::numerical_failure)&&!r.tube&&!r.candidate_evaluated&&!r.endpoint&&!r.inflated,PP_SIM_CORE_REJECTED,"Guard bridge failure with later execution");}
    require((!r.candidate_evaluated||r.tube)&&(!r.endpoint||r.candidate_evaluated)&&(!r.inflated||r.endpoint),PP_SIM_CORE_REJECTED,"Guard diagnostics violate execution order");
    if(r.tube) {
        const auto& t=*r.tube;finite_output(flight_tube_packet(t),24);
        require(t.position_error>=0&&t.roundoff>=0&&t.position_error>=t.roundoff&&t.guard_radius>0,PP_SIM_CORE_REJECTED,"Invalid guard tube bounds");
        const double g[3]{gravity.x,gravity.y,gravity.z},f[3]{body.force.x,body.force.y,body.force.z},nominal[3]{t.nominal_acceleration.x,t.nominal_acceleration.y,t.nominal_acceleration.z};
        for(unsigned k=0;k<3;++k) {
            const auto exact=FlightInterval::point(g[k])+FlightInterval::point(f[k])/FlightInterval::point(body.mass);
            require(flight_same_interval(exact,t.exact_acceleration[k])&&flight_same_interval(exact-FlightInterval::point(nominal[k]),t.acceleration_difference[k]),PP_SIM_CORE_REJECTED,"Guard exact/nominal coefficient diagnostic changed");
        }
        require(t.guard_radius==(FlightInterval::point(body.radius)+FlightInterval::point(t.position_error)).upper(),PP_SIM_CORE_REJECTED,"Guard inflated radius lost outward sum");
        if(r.endpoint) {require(t.guard_radius<=1e9,PP_SIM_CORE_REJECTED,"Guard continued outside inflated radius domain");}
    }
    if(r.endpoint) {
        const auto& e=*r.endpoint;finite_output(flight_endpoint_packet(e),40);
        require(r.tube&&e.l1_error_bound.upper()>=0&&e.l1_within_tube==(e.l1_error_bound.upper()<=r.tube->position_error),PP_SIM_CORE_REJECTED,"Guard endpoint L1 flag changed");
        auto l1=FlightInterval::point(0);
        for(unsigned k=0;k<3;++k) {
            const auto& t=*r.tube;const FlightInterval rn(-t.roundoff,t.roundoff),total(-t.position_error,t.position_error);
            require(flight_same_interval(e.nominal_position[k]+rn,e.nominal_allowed[k])&&flight_same_interval(e.exact_position[k]+total,e.exact_allowed[k]),PP_SIM_CORE_REJECTED,"Guard endpoint expansion changed");
            const auto& d=e.exact_difference[k];const auto absolute=d.lower()>=0?d:d.upper()<=0?-d:FlightInterval(0,std::max(-d.lower(),d.upper()));l1=l1+absolute;
        }
        require(flight_same_interval(l1,e.l1_error_bound),PP_SIM_CORE_REJECTED,"Guard endpoint L1 audit changed");
        if(r.inflated) {require(e.nominal_contained&&e.exact_contained&&e.l1_within_tube,PP_SIM_CORE_REJECTED,"Guard queried geometry after endpoint rejection");}
    }
    if(r.inflated) {
        require(r.tube&&r.endpoint,PP_SIM_CORE_REJECTED,"Inflated query without tube/endpoint");
        const flight_held::HeldSphere expected{body.id,body.position,body.velocity,body.mass,body.force,gravity,r.tube->guard_radius};
        validate_flight_held(record,*r.inflated,expected,horizon,settings.held_load);
        require(success==(r.inflated->status==flight_held::Status::separated&&r.inflated->work.exact),PP_SIM_CORE_REJECTED,"Guard promoted non-separated inflated result");
    }else {require(!success,PP_SIM_CORE_REJECTED,"Guard success without geometry proof");}
    if(r.candidate) {
        const auto& c=*r.candidate;c.validate();FlightPacket a{},b{};flight_body_packet(a,c);flight_body_packet(b,body);finite_output(a,32);
        for(unsigned k=0;k<28;++k) {if(k<7||k>=20) {require(flight_same(a[k],b[k]),PP_SIM_CORE_REJECTED,"Guard candidate changed held/static body fields");}}
        const auto& e=*r.endpoint;const double pos[3]{c.position.x,c.position.y,c.position.z};
        for(unsigned k=0;k<3;++k) {require(e.nominal_allowed[k].contains(pos[k])&&e.exact_allowed[k].contains(pos[k])&&flight_same_interval(FlightInterval::point(pos[k])-e.exact_position[k],e.exact_difference[k]),PP_SIM_CORE_REJECTED,"Guard actual candidate is outside its endpoint tube");}
    }
}
void validate_flight_record(const FlightRecord& record,const flight_held::Settings& held_settings,const flight_guard::Settings& guard_settings) {
    require(record.mode<=1&&record.source.size()<=64&&record.held.has_value()==(record.mode==0)&&record.guard.has_value()==(record.mode==1),PP_SIM_CORE_REJECTED,"Invalid flight snapshot ownership");
    const auto input=flight_original(record);
    if(record.held) {validate_flight_held(record,*record.held,flight_held_input(input),input[15],held_settings);}
    if(record.guard) {flight_validate_guard(record,input,guard_settings);}
    finite_output(flight_summary(record),24);
    // Check every publishable packet, including diagnostic-only invalid bodies.
    for(uint32_t kind=0;kind<=20;++kind) {
        const auto* h=flight_held_result(record);std::size_t count=0;
        switch(kind) {
        case 0:count=1;break;case 1:count=record.source.size();break;
        case 2:count=(record.held&&record.held->snapshot)||(record.guard&&record.guard->snapshot)?1u:0u;break;
        case 3:count=h?1u:0u;break;case 4:count=h&&h->snapshot?1u:0u;break;
        case 5:count=record.guard&&record.guard->world_body?1u:0u;break;case 6:count=record.guard&&record.guard->tube?1u:0u;break;
        case 7:count=record.guard&&record.guard->endpoint?1u:0u;break;case 8:count=record.guard&&record.guard->candidate?1u:0u;break;
        case 9:count=h&&h->acceleration?1u:0u;break;case 10:count=h&&h->whole_path_bounds?1u:0u;break;case 11:count=h&&h->whole_velocity_bounds?1u:0u;break;
        case 12:count=h?h->audits.size():0;break;case 13:count=h?h->certified_leaves.size():0;break;case 14:count=h?h->partition.size():0;break;case 15:count=h?h->frontier.size():0;break;
        case 16:count=h&&h->current?1u:0u;break;case 17:count=h&&h->initial?1u:0u;break;case 18:count=h&&h->best_witness?1u:0u;break;case 19:count=h&&h->window?1u:0u;break;case 20:count=h?h->candidate_surface_ids.size():0;break;
        }
        for(std::size_t index=0;index<count;++index) {uint32_t length{};const auto a=flight_record_packet(record,kind,uint32_t(index),length);finite_output(a,length);}
    }
}
}

extern "C" {
int32_t pp_sim_sphere_triangle_mesh_flight_begin(uint32_t mode,uint32_t triangle_count) {
    return guarded([&] {
        flight_mode(mode);require(triangle_count<=64,PP_SIM_INVALID_ARGUMENT,"Flight staging exceeds 64 surfaces");
        SphereTriangleMeshStage candidate;candidate.expected=triangle_count;candidate.source.reserve(triangle_count);
        static_assert(std::is_nothrow_move_assignable_v<std::optional<SphereTriangleMeshStage>>);
        flight_stages[mode]=std::move(candidate);
    });
}
int32_t pp_sim_sphere_triangle_mesh_flight_append(uint32_t mode,uint32_t count) {
    return guarded([&] {
        flight_mode(mode);require(flight_stages[mode].has_value(),PP_SIM_INVALID_ARGUMENT,"Flight append requires begin");
        require(count>=10&&count<=60&&count%10==0,PP_SIM_INVALID_ARGUMENT,"Flight append needs 1..6 whole surfaces");
        const auto& old=*flight_stages[mode];const std::size_t additional=count/10;
        require(old.source.size()<=old.expected&&additional<=old.expected-old.source.size(),PP_SIM_INVALID_ARGUMENT,"Flight append exceeds declared source count");
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite flight source exchange");
        std::array<sphere_tri::StaticTriangle,6> chunk{};
        for(std::size_t i=0;i<additional;++i) {chunk[i].id=id_from(input_f64[i*10]);for(unsigned k=0;k<3;++k){chunk[i].vertices[k]=vector_at(i*10+1+3*k);}}
        auto candidate=old;candidate.source.reserve(candidate.expected);candidate.source.insert(candidate.source.end(),chunk.begin(),chunk.begin()+additional);
        flight_stages[mode]=std::move(candidate);
    });
}
int32_t pp_sim_sphere_triangle_mesh_flight_query(uint32_t mode,uint32_t count) {
    return guarded([&] {
        flight_mode(mode);count_is(count,mode==0?32u:48u);
        require(flight_stages[mode]&&flight_stages[mode]->source.size()==flight_stages[mode]->expected,PP_SIM_INVALID_ARGUMENT,"Flight query needs complete staging");
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite flight query exchange");
        const unsigned reserved=mode==0?29u:46u;
        for(unsigned i=reserved;i<count;++i) {require(std::bit_cast<uint64_t>(input_f64[i])==0,PP_SIM_INVALID_ARGUMENT,"Flight reserved slots must be positive zero");}
        FlightPacket input{};std::copy_n(input_f64.begin(),count,input.begin());
        const auto settings=flight_settings(input,mode==0?16u:32u);
        flight_guard::Settings guard_settings;guard_settings.held_load=settings;if(mode==1){guard_settings.max_angular_increment=input[45];}
        // Decode host-representability only. Physics validation belongs to core.
        std::optional<flight_held::HeldSphere> held_input;std::optional<dyn::RigidBody> body;
        if(mode==0) {held_input=flight_held_input(input);}else{body=flight_body_input(input);}
        FlightRecord candidate;candidate.mode=mode;std::copy_n(input.begin(),count,candidate.input.begin());candidate.source=flight_stages[mode]->source;
        if(mode==0) {candidate.held=flight_held::query(*held_input,candidate.source,input[15],settings);}
        else {candidate.guard=flight_guard::query(*body,flight_vector(input,28),candidate.source,input[31],guard_settings);}
        validate_flight_record(candidate,settings,guard_settings);const auto summary=flight_summary(candidate);
        static_assert(std::is_nothrow_move_assignable_v<std::optional<FlightRecord>>);
        flight_records[mode]=std::move(candidate);publish(summary,PP_SIM_SPHERE_TRIANGLE_MESH_FLIGHT_OUTPUT_COUNT);
    });
}
int32_t pp_sim_sphere_triangle_mesh_flight_record(uint32_t mode,uint32_t kind,uint32_t index) {
    return guarded([&] {
        flight_mode(mode);require(flight_records[mode].has_value(),PP_SIM_INVALID_ARGUMENT,"No flight committed record");
        uint32_t count{};const auto a=flight_record_packet(*flight_records[mode],kind,index,count);finite_output(a,count);publish(a,count);
    });
}
int32_t pp_sim_sphere_triangle_mesh_flight_last_mesh(uint32_t mode,uint32_t part,uint32_t index) {
    return guarded([&] {
        flight_mode(mode);require(flight_records[mode].has_value(),PP_SIM_INVALID_ARGUMENT,"No flight committed record");const auto& record=*flight_records[mode];const auto* mesh=flight_mesh(record);
        require(mesh!=nullptr,PP_SIM_INVALID_ARGUMENT,"No flight last mesh");FlightPacket a{};uint32_t count{};
        if(part==0) {require(index==0,PP_SIM_INVALID_ARGUMENT,"Flight mesh summary requires ordinal zero");a=sphere_triangle_mesh_packet(record.source,*mesh);count=24;}
        else if(part==1) {require(index<mesh->rows.size()&&mesh->rows[index].query,PP_SIM_INVALID_ARGUMENT,"No examined flight mesh row");const auto& row=mesh->rows[index];a=sphere_triangle_packet(*row.query,row.triangle.id);count=58;}
        else {throw Failure{PP_SIM_INVALID_ARGUMENT,"Unknown flight last-mesh part"};}
        finite_output(a,count);publish(a,count);
    });
}
int32_t pp_sim_sphere_triangle_mesh_flight_candidate(uint32_t mode,uint32_t row,uint32_t ordinal) {
    return guarded([&] {
        flight_mode(mode);require(flight_records[mode].has_value(),PP_SIM_INVALID_ARGUMENT,"No flight committed record");const auto* mesh=flight_mesh(*flight_records[mode]);
        require(mesh&&row<mesh->rows.size()&&mesh->rows[row].query&&ordinal<mesh->rows[row].query->candidates.size(),PP_SIM_INVALID_ARGUMENT,"No flight primitive candidate");
        const auto a=sphere_triangle_candidate_packet(mesh->rows[row].query->candidates[ordinal]);finite_output(a,13);publish(a,13);
    });
}
}
