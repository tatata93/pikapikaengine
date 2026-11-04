#include "pikapika/simulation_api.h"
#include "pikapika/hydrostatics.hpp"
#include "pikapika/continuous.hpp"
#include "pikapika/accelerated.hpp"
#include "pikapika/optics.hpp"
#include "pikapika/optical_geometry.hpp"
#include "pikapika/polarization.hpp"
#include "pikapika/dispersion.hpp"
#include "pikapika/optical_bounds.hpp"
#include "pikapika/support.hpp"
#include "pikapika/optical_route.hpp"
#include "pikapika/optical_selection.hpp"
#include "pikapika/optical_spot.hpp"
#include "pikapika/polarized_route.hpp"
#include "pikapika/polarized_packet.hpp"
#include "pikapika/motion.hpp"
#include "pikapika/skinning.hpp"
#include "pikapika/derived_mesh.hpp"
#include "pikapika/sphere_triangle.hpp"
#include "pikapika/sphere_triangle_mesh.hpp"
#include "pikapika/supported_world.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <exception>
#include <memory>
#include <new>
#include <optional>
#include <type_traits>
#include <utility>

namespace {
using pikapika::Vec3;
namespace dyn=pikapika::dynamics;
namespace hydro=pikapika::hydrostatics;
namespace continuous=pikapika::continuous;
namespace accel=pikapika::accelerated;
namespace optics=pikapika::optics;
namespace geometry=pikapika::optical_geometry;
namespace polarization=pikapika::optics::polarization;
namespace dispersion=pikapika::optics::dispersion;
namespace optical_bounds=pikapika::optical_bounds;
namespace support=pikapika::support;
namespace route=pikapika::optical_route;
namespace selection=pikapika::optical_selection;
namespace spot=pikapika::optical_spot;
namespace polarized_route=pikapika::polarized_route;
namespace packet=pikapika::polarized_packet;
namespace motion=pikapika::motion;
namespace skin=pikapika::skinning;
namespace derived=pikapika::derived_mesh;
namespace sphere_tri=pikapika::sphere_triangle;
namespace sphere_mesh=pikapika::sphere_triangle_mesh;
namespace supported=pikapika::supported;
struct Failure {int32_t code;const char* message;};
void require(bool value,int32_t code,const char* message){if(!value)throw Failure{code,message};}
std::array<double,PP_SIM_INPUT_F64_CAPACITY> input_f64{};
std::array<uint32_t,PP_SIM_INPUT_U32_CAPACITY> input_u32{};
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> output{};
uint32_t output_count{};
std::optional<route::Result> route_record;
std::optional<selection::Result> selection_record;
std::optional<spot::Result> spot_record;
std::optional<polarized_route::Result> polarized_route_record;
std::optional<packet::Result> packet_record;
std::optional<motion::Result> motion_record;
std::optional<skin::BindResult> skin_bind_record;
std::optional<skin::DeformResult> skin_deform_record;
std::optional<derived::Result> derived_record;
struct SphereTriangleRecord {uint64_t surface_id{};sphere_tri::Result result;};
std::optional<SphereTriangleRecord> sphere_triangle_record;
struct SphereTriangleMeshStage {uint32_t expected{};std::vector<sphere_tri::StaticTriangle> source;};
struct SphereTriangleMeshRecord {std::vector<sphere_tri::StaticTriangle> source;sphere_mesh::Result result;};
std::optional<SphereTriangleMeshStage> sphere_triangle_mesh_stage;
std::optional<SphereTriangleMeshRecord> sphere_triangle_mesh_record;
double packet_wavelength{};
int32_t status{};
std::array<char,PP_SIM_ERROR_CAPACITY> error{};
constexpr uint32_t hull_tag=0x80000000U,max_generation=0x7fffffU;
struct WorldState {dyn::World world;double time{};uint64_t ticks{};std::optional<dyn::CcdReport> last_ccd;std::optional<support::Result> last_support;std::optional<supported::Report> last_supported;};
template<class T> struct Slot {uint32_t generation{1};bool retired{};std::unique_ptr<T> object;};
std::array<Slot<WorldState>,PP_SIM_MAX_WORLDS> worlds;
std::array<Slot<hydro::Hull>,PP_SIM_MAX_HULLS> hulls;
std::size_t total_vertices{},total_triangles{};
void diagnostic(int32_t code,const char* message) noexcept {
    status=code;std::snprintf(error.data(),error.size(),"%s",message?message:"unknown simulation error");
}
template<class Function> int32_t guarded(Function operation) noexcept {
    try {operation();status=PP_SIM_OK;error[0]='\0';return PP_SIM_OK;}
    catch(const Failure& failure){diagnostic(failure.code,failure.message);}
    catch(const std::bad_alloc&){diagnostic(PP_SIM_ALLOCATION_FAILED,"simulation allocation failed; resource state retained");}
    catch(const std::exception& exception){diagnostic(PP_SIM_CORE_REJECTED,exception.what());}
    catch(...){diagnostic(PP_SIM_INTERNAL_ERROR,"unknown exception caught at simulation C boundary");}
    return status;
}
template<class T,std::size_t N> Slot<T>& lookup(std::array<Slot<T>,N>& slots,pp_sim_handle handle,uint32_t tag) {
    const uint32_t encoded_slot=handle&255U,generation=(handle&~hull_tag)>>8;
    require((handle&hull_tag)==tag&&encoded_slot>0&&encoded_slot<=N,PP_SIM_INVALID_HANDLE,"invalid simulation handle type or slot");
    auto& slot=slots[encoded_slot-1];
    require(slot.object&&generation==slot.generation,PP_SIM_INVALID_HANDLE,"stale or destroyed simulation handle");return slot;
}
template<class T,std::size_t N> std::size_t free_slot(const std::array<Slot<T>,N>& slots) {
    for(std::size_t i=0;i<N;++i)if(!slots[i].object&&!slots[i].retired)return i;
    throw Failure{PP_SIM_BUDGET_EXCEEDED,"simulation handle budget exhausted"};
}
template<class T> void retire(Slot<T>& slot) noexcept {
    slot.object.reset();if(slot.generation==max_generation)slot.retired=true;else ++slot.generation;
}
template<class T> pp_sim_handle encode(const Slot<T>& slot,std::size_t index,uint32_t tag) {
    return tag|(slot.generation<<8)|uint32_t(index+1);
}
bool finite(Vec3 v){return std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z);}
Vec3 vector_at(std::size_t offset){return {input_f64[offset],input_f64[offset+1],input_f64[offset+2]};}
uint64_t id_from(double id) {
    require(std::isfinite(id)&&id>=1&&id<=9007199254740991.&&std::floor(id)==id,PP_SIM_INVALID_ARGUMENT,"body/plane ID must be an exact integer in 1..2^53-1");return uint64_t(id);
}
void count_is(uint32_t count,uint32_t expected){require(count==expected,PP_SIM_INVALID_ARGUMENT,"simulation input value count mismatch");}
dyn::RigidBody body_input(uint32_t count) {
    count_is(count,PP_SIM_BODY_INPUT_COUNT);dyn::RigidBody b;b.id=id_from(input_f64[0]);
    require(input_f64[1]==0||input_f64[1]==1,PP_SIM_INVALID_ARGUMENT,"static flag must be exactly 0 or 1");b.is_static=input_f64[1]==1;
    b.mass=input_f64[2];b.radius=input_f64[3];b.inertia_diagonal=vector_at(4);b.position=vector_at(7);
    b.orientation={input_f64[10],input_f64[11],input_f64[12],input_f64[13]};b.velocity=vector_at(14);b.angular_momentum=vector_at(17);
    b.force=vector_at(20);b.torque=vector_at(23);b.material={input_f64[26],input_f64[27]};b.validate();return b;
}
void put_vector(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& values,std::size_t offset,Vec3 v){values[offset]=v.x;values[offset+1]=v.y;values[offset+2]=v.z;}
void publish(const std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& values,uint32_t count) noexcept {std::copy_n(values.begin(),count,output.begin());output_count=count;}
void put_hydro(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& values,const hydro::Result& result) {
    put_vector(values,0,result.force);put_vector(values,3,result.torque);values[6]=result.wet_area;values[7]=result.submerged_volume;
    values[8]=result.total_volume;values[9]=double(result.shells);values[10]=result.center_of_buoyancy?1:0;
    if(result.center_of_buoyancy)put_vector(values,11,*result.center_of_buoyancy);
}
void publish_toi(const continuous::ToiResult& result) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};
    switch(result.kind) {
    case continuous::ContactKind::none:values[0]=PP_SIM_TOI_NONE;break;
    case continuous::ContactKind::initial_overlap:values[0]=PP_SIM_TOI_INITIAL_OVERLAP;break;
    case continuous::ContactKind::initial_touch:values[0]=PP_SIM_TOI_INITIAL_TOUCH;break;
    case continuous::ContactKind::impact:values[0]=PP_SIM_TOI_IMPACT;break;
    case continuous::ContactKind::grazing:values[0]=PP_SIM_TOI_GRAZING;break;
    case continuous::ContactKind::uncertain:values[0]=PP_SIM_TOI_UNCERTAIN;break;
    }
    switch(result.initial_motion) {
    case continuous::Motion::stationary:values[1]=PP_SIM_TOI_STATIONARY;break;
    case continuous::Motion::approaching:values[1]=PP_SIM_TOI_APPROACHING;break;
    case continuous::Motion::separating:values[1]=PP_SIM_TOI_SEPARATING;break;
    case continuous::Motion::tangential:values[1]=PP_SIM_TOI_TANGENTIAL;break;
    }
    values[2]=result.time?1:0;values[3]=result.time.value_or(0);
    put_vector(values,4,result.normal);values[7]=result.normal_valid?1:0;
    values[8]=result.at_horizon?1:0;values[9]=result.roundoff_sensitive?1:0;
    values[10]=result.initial_gap;values[11]=result.initial_normal_speed;values[12]=result.normal_speed;
    require(std::all_of(values.begin(),values.begin()+PP_SIM_TOI_OUTPUT_COUNT,[](double value){return std::isfinite(value);}),
        PP_SIM_CORE_REJECTED,"nonfinite continuous query output; prior output retained");
    publish(values,PP_SIM_TOI_OUTPUT_COUNT);
}
std::size_t query_integer(double value,std::size_t minimum,std::size_t maximum) {
    require(std::isfinite(value)&&value>=double(minimum)&&value<=double(maximum)&&std::floor(value)==value,
        PP_SIM_INVALID_ARGUMENT,"query integer setting outside ABI budget");
    return std::size_t(value);
}
accel::Sphere accelerated_sphere(std::size_t offset) {
    return {vector_at(offset),vector_at(offset+3),vector_at(offset+6),input_f64[offset+9]};
}
accel::Settings accelerated_settings(std::size_t offset) {
    accel::Settings s;s.time_tolerance=input_f64[offset];
    s.max_evaluations=query_integer(input_f64[offset+1],1,PP_SIM_MAX_QUERY_EVALUATIONS);
    s.max_frontier=query_integer(input_f64[offset+2],1,PP_SIM_MAX_QUERY_FRONTIER);
    s.max_depth=unsigned(query_integer(input_f64[offset+3],0,128));return s;
}
void publish_accelerated(const accel::Result& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};
    switch(r.kind){case accel::Kind::none:values[0]=PP_SIM_ACCEL_NONE;break;
        case accel::Kind::entry_bracket:values[0]=PP_SIM_ACCEL_ENTRY_BRACKET;break;
        case accel::Kind::unresolved:values[0]=PP_SIM_ACCEL_UNRESOLVED;break;}
    switch(r.reason){case accel::Reason::none:values[1]=PP_SIM_ACCEL_REASON_NONE;break;
        case accel::Reason::initial_overlap:values[1]=PP_SIM_ACCEL_INITIAL_OVERLAP;break;
        case accel::Reason::initial_boundary:values[1]=PP_SIM_ACCEL_INITIAL_BOUNDARY;break;
        case accel::Reason::evaluation_budget:values[1]=PP_SIM_ACCEL_EVALUATION_BUDGET;break;
        case accel::Reason::frontier_budget:values[1]=PP_SIM_ACCEL_FRONTIER_BUDGET;break;
        case accel::Reason::depth_limit:values[1]=PP_SIM_ACCEL_DEPTH_LIMIT;break;
        case accel::Reason::time_resolution:values[1]=PP_SIM_ACCEL_TIME_RESOLUTION;break;
        case accel::Reason::numerical_uncertainty:values[1]=PP_SIM_ACCEL_NUMERICAL_UNCERTAINTY;break;}
    values[2]=r.initial_separation_proven?1:0;values[3]=r.safe_until;
    const auto interval_at=[&](std::size_t offset,const std::optional<pikapika::interval::Interval>& v){
        values[offset]=v?1:0;if(v){values[offset+1]=v->lower();values[offset+2]=v->upper();}
    };
    interval_at(4,r.value_at_safe);interval_at(7,r.initial_value);interval_at(10,r.bracket);
    values[13]=r.negative_witness?1:0;values[14]=r.negative_witness.value_or(0);interval_at(15,r.negative_value);
    values[18]=double(r.evaluations);values[19]=double(r.excluded_intervals);values[20]=r.depth_reached;
    require(std::all_of(values.begin(),values.begin()+PP_SIM_ACCEL_OUTPUT_COUNT,[](double x){return std::isfinite(x);}),
        PP_SIM_CORE_REJECTED,"nonfinite accelerated proof output; prior output retained");
    publish(values,PP_SIM_ACCEL_OUTPUT_COUNT);
}
void publish_optics(const optics::InterfaceResult& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
    switch(r.kind){case optics::InterfaceKind::transmission:a[0]=PP_SIM_OPTICS_TRANSMISSION;break;
        case optics::InterfaceKind::total_internal_reflection:a[0]=PP_SIM_OPTICS_TIR;break;
        case optics::InterfaceKind::uncertain:a[0]=PP_SIM_OPTICS_UNCERTAIN;break;}
    switch(r.uncertainty){case optics::Uncertainty::none:a[1]=PP_SIM_OPTICS_RESOLVED;break;
        case optics::Uncertainty::incident_side:a[1]=PP_SIM_OPTICS_INCIDENT_SIDE;break;
        case optics::Uncertainty::critical_angle:a[1]=PP_SIM_OPTICS_CRITICAL_ANGLE;break;
        case optics::Uncertainty::numerical_output:a[1]=PP_SIM_OPTICS_NUMERICAL_OUTPUT;break;}
    put_vector(a,2,r.incident_unit);put_vector(a,5,r.normal_unit);put_vector(a,8,r.reflected);
    a[11]=r.transmitted?1:0;if(r.transmitted)put_vector(a,12,*r.transmitted);
    a[15]=r.power?1:0;if(r.power){const auto& p=*r.power;a[16]=p.reflectance_s;a[17]=p.transmittance_s;
        a[18]=p.reflectance_p;a[19]=p.transmittance_p;a[20]=p.reflectance_unpolarized;a[21]=p.transmittance_unpolarized;}
    a[22]=r.cosine_incident;a[23]=r.cosine_transmitted?1:0;a[24]=r.cosine_transmitted.value_or(0);
    a[25]=r.vacuum_wavelength_m;a[26]=r.discriminant.lower();a[27]=r.discriminant.upper();
    a[28]=r.incident_dot.lower();a[29]=r.incident_dot.upper();a[30]=r.exact_grazing?1:0;
    require(std::all_of(a.begin(),a.begin()+PP_SIM_OPTICS_OUTPUT_COUNT,[](double x){return std::isfinite(x);}),
        PP_SIM_CORE_REJECTED,"nonfinite optical output; prior output retained");
    publish(a,PP_SIM_OPTICS_OUTPUT_COUNT);
}
std::unique_ptr<hydro::Hull> hull_input(uint32_t vertices,uint32_t triangles,std::size_t old_vertices=0,std::size_t old_triangles=0) {
    require(vertices>=3&&vertices<=PP_SIM_MAX_HULL_VERTICES&&triangles>=1&&triangles<=PP_SIM_MAX_HULL_TRIANGLES,
        PP_SIM_BUDGET_EXCEEDED,"hull count outside C ABI mesh budget");
    require(total_vertices-old_vertices+vertices<=PP_SIM_MAX_TOTAL_VERTICES&&total_triangles-old_triangles+triangles<=PP_SIM_MAX_TOTAL_TRIANGLES,
        PP_SIM_BUDGET_EXCEEDED,"total simulation hull geometry budget exceeded");
    pikapika::Mesh mesh;mesh.positions.reserve(vertices);mesh.triangles.reserve(triangles);
    for(uint32_t i=0;i<vertices;++i)mesh.positions.push_back(vector_at(std::size_t(i)*3));
    for(uint32_t i=0;i<triangles;++i)mesh.triangles.push_back({input_u32[i*3],input_u32[i*3+1],input_u32[i*3+2]});
    return std::make_unique<hydro::Hull>(std::move(mesh));
}
dyn::SolverSettings settings(){dyn::SolverSettings result;result.max_contacts=PP_SIM_MAX_CONTACTS;return result;}
void step_valid(const WorldState& state,double dt,uint32_t steps) {
    require(std::isfinite(dt)&&dt>0&&dt<=.1&&steps>0&&steps<=PP_SIM_MAX_STEPS,PP_SIM_INVALID_ARGUMENT,"dt must be in (0,0.1], steps in 1..32");
    require(state.time+dt*steps<=1e9&&state.ticks<=9007199254740991ULL-steps,PP_SIM_BUDGET_EXCEEDED,"simulation elapsed time/tick budget exceeded");
}
void accumulate(dyn::StepStats& total,const dyn::StepStats& one) {
    total.contacts=std::max(total.contacts,one.contacts);total.velocity_iterations=std::max(total.velocity_iterations,one.velocity_iterations);
    total.max_penetration=std::max(total.max_penetration,one.max_penetration);total.normal_impulse_sum+=one.normal_impulse_sum;
    total.friction_impulse_sum+=one.friction_impulse_sum;total.max_closing_residual=std::max(total.max_closing_residual,one.max_closing_residual);
}
void put_step(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& values,const dyn::StepStats& stats,const WorldState& state) {
    values[14]=double(stats.contacts);values[15]=stats.velocity_iterations;values[16]=stats.max_penetration;values[17]=stats.normal_impulse_sum;
    values[18]=stats.friction_impulse_sum;values[19]=stats.max_closing_residual;values[20]=state.time;values[21]=double(state.ticks);
}
void finite_output(const std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& values,uint32_t count) {
    require(std::all_of(values.begin(),values.begin()+count,[](double x){return std::isfinite(x);}),
        PP_SIM_CORE_REJECTED,"nonfinite reference output; state and prior output retained");
}
void put_bounds(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& a,std::size_t offset,const geometry::Bounds3& bounds) {
    for(std::size_t i=0;i<3;++i){a[offset+i*2]=bounds[i].lower();a[offset+i*2+1]=bounds[i].upper();}
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> derived_audit_packet(const derived::FaceAudit& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=double(r.face);put_bounds(a,1,r.cross);
    a[7]=r.squared_cross.lower();a[8]=r.squared_cross.upper();a[9]=r.normalized?1:0;
    if(r.normalized){put_bounds(a,10,*r.normalized);}a[16]=r.normal?1:0;
    if(r.normal){for(unsigned i=0;i<3;++i)a[17+i]=(*r.normal)[i];}a[20]=r.normal_error?1:0;
    if(r.normal_error)std::copy(r.normal_error->begin(),r.normal_error->end(),a.begin()+21);
    a[24]=r.sqrt_refinements;a[25]=r.sqrt_refinement_limited?1:0;return a;
}
void validate_derived(const derived::Result&r,std::size_t vertices,std::size_t faces,const derived::Settings&s) {
    require(unsigned(r.status)<=unsigned(derived::Status::unsupported_environment)&&unsigned(r.reason)<=unsigned(derived::Reason::environment),PP_SIM_CORE_REJECTED,"Invalid derived model enum");
    require(r.geometry.has_value()==(r.status==derived::Status::completed)&&
        (r.status!=derived::Status::completed||r.reason==derived::Reason::none),PP_SIM_CORE_REJECTED,"Invalid derived geometry completion flag");
    require((!r.failed_vertex||*r.failed_vertex<vertices)&&(!r.failed_face||*r.failed_face<faces)&&r.audits.size()<=faces,
        PP_SIM_CORE_REJECTED,"Invalid derived diagnostic range");
    std::uint64_t refinements=0;unsigned limited=0;
    for(std::size_t i=0;i<r.audits.size();++i){const auto&a=r.audits[i];
        require(a.face==i&&a.sqrt_refinements<=std::uint64_t(s.sqrt_refinements)*2,PP_SIM_CORE_REJECTED,"Invalid derived audit ordinal/budget");
        const auto packet=derived_audit_packet(a);finite_output(packet,PP_SIM_DERIVED_AUDIT_COUNT);
        if(a.normal_error)for(double e:*a.normal_error)require(e>=0,PP_SIM_CORE_REJECTED,"Negative derived normal error");
        refinements+=a.sqrt_refinements;if(a.sqrt_refinement_limited)++limited;
    }
    require(refinements==r.sqrt_refinements&&limited==r.sqrt_limited_faces,PP_SIM_CORE_REJECTED,"Invalid derived counter totals");
    if(!r.geometry)return;
    const auto&g=*r.geometry;
    require(!r.failed_vertex&&!r.failed_face&&g.positions.size()==vertices&&g.triangles.size()==faces&&g.interleaved.size()==faces*18&&r.audits.size()==faces,
        PP_SIM_CORE_REJECTED,"Invalid completed derived buffer counts");
    for(unsigned axis=0;axis<3;++axis)require(std::isfinite(g.minimum[axis])&&std::isfinite(g.maximum[axis])&&g.minimum[axis]<=g.maximum[axis],PP_SIM_CORE_REJECTED,"Invalid derived bounds");
    for(const auto&p:g.positions)for(unsigned axis=0;axis<3;++axis)require(std::isfinite(p[axis])&&p[axis]>=g.minimum[axis]&&p[axis]<=g.maximum[axis],PP_SIM_CORE_REJECTED,"Invalid quantized derived position");
    for(const auto&t:g.triangles)require(t[0]<vertices&&t[1]<vertices&&t[2]<vertices&&t[0]!=t[1]&&t[1]!=t[2]&&t[0]!=t[2],PP_SIM_CORE_REJECTED,"Invalid completed derived triangle");
    require(std::all_of(g.interleaved.begin(),g.interleaved.end(),[](float x){return std::isfinite(x);}),PP_SIM_CORE_REJECTED,"Nonfinite derived buffer");
    for(const auto&a:r.audits){require(a.normalized&&a.normal&&a.normal_error&&a.squared_cross.lower()>derived::minimum_cross_squared,
        PP_SIM_CORE_REJECTED,"Incomplete derived normal certificate");
        require(std::any_of(a.cross.begin(),a.cross.end(),[](const auto&x){return x.strictly_positive()||x.strictly_negative();}),PP_SIM_CORE_REJECTED,"Uncertified derived cross");
        for(double e:*a.normal_error)require(e<=derived::maximum_normal_component_error,PP_SIM_CORE_REJECTED,"Uncertified derived normal error");}
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> sphere_triangle_candidate_packet(const sphere_tri::CandidateAudit& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=unsigned(r.feature);a[1]=unsigned(r.disposition);a[2]=r.kkt_count;
    put_bounds(a,3,r.barycentric);
    // Count0/1 means unused residuals, not permission to replace their source bits.
    for(unsigned j=0;j<2;++j){a[9+2*j]=r.kkt[j].lower();a[10+2*j]=r.kkt[j].upper();}return a;
}
void validate_sphere_triangle(const sphere_tri::Result& r,uint64_t id,const sphere_tri::Settings& s) {
    require(unsigned(r.status)<=unsigned(sphere_tri::Status::unsupported_environment)&&unsigned(r.reason)<=unsigned(sphere_tri::Reason::environment),PP_SIM_CORE_REJECTED,"Invalid sphere triangle model enum");
    const bool complete=r.status==sphere_tri::Status::completed;
    require(r.geometry.has_value()==complete&&(complete?(r.reason==sphere_tri::Reason::none):(r.reason!=sphere_tri::Reason::none)),PP_SIM_CORE_REJECTED,"Invalid sphere triangle completion flag");
    require(r.candidates_examined<=PP_SIM_SPHERE_TRIANGLE_MAX_CANDIDATES&&r.candidates.size()<=r.candidates_examined&&
        r.candidates_examined-r.candidates.size()<=1&&r.sqrt_refinements<=512,PP_SIM_CORE_REJECTED,"Invalid sphere triangle work prefix");
    uint32_t retained{};
    for(std::size_t j=0;j<r.candidates.size();++j){const auto& c=r.candidates[j];
        require(unsigned(c.feature)==j&&unsigned(c.disposition)<=unsigned(sphere_tri::Disposition::kkt_violated)&&c.kkt_count==(j==0?0u:j<=3?1u:2u),PP_SIM_CORE_REJECTED,"Invalid sphere triangle candidate ordinal");
        finite_output(sphere_triangle_candidate_packet(c),PP_SIM_SPHERE_TRIANGLE_CANDIDATE_COUNT);
        if(c.disposition==sphere_tri::Disposition::retained)retained|=uint32_t(1)<<j;
    }
    if(r.squared_cross)require(r.squared_cross->lower()>=0,PP_SIM_CORE_REJECTED,"Invalid triangle cross square");
    if(r.sine_squared)require(r.sine_squared->lower()>=0&&r.sine_squared->upper()<=1,PP_SIM_CORE_REJECTED,"Invalid triangle sine square");
    if(!r.geometry)return;
    const auto& g=*r.geometry;
    require(g.surface_id==id&&g.surviving_features==retained&&retained>0&&retained<128&&r.candidates.size()==7&&r.candidates_examined==7&&
        r.squared_cross&&r.sine_squared&&r.sqrt_refinements<=s.max_total_sqrt_refinements,PP_SIM_CORE_REJECTED,"Invalid completed sphere triangle geometry");
    require(unsigned(g.relation)<=unsigned(sphere_tri::Relation::boundary_unresolved)&&g.squared_distance.strictly_positive()&&g.distance.strictly_positive(),PP_SIM_CORE_REJECTED,"Invalid sphere triangle distance/relation");
    for(unsigned k=0;k<3;++k)require(g.barycentric[k].lower()>=0&&g.barycentric[k].upper()<=1&&g.normal[k].lower()>=-1&&g.normal[k].upper()<=1,PP_SIM_CORE_REJECTED,"Invalid sphere triangle barycentric/normal bounds");
    const auto relation=g.gap.strictly_positive()?sphere_tri::Relation::separated:g.gap.strictly_negative()?sphere_tri::Relation::penetrating:
        g.gap.lower()==0&&g.gap.upper()==0?sphere_tri::Relation::touching:sphere_tri::Relation::boundary_unresolved;
    require(g.relation==relation,PP_SIM_CORE_REJECTED,"Inconsistent sphere triangle gap relation");
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> sphere_triangle_packet(const sphere_tri::Result& r,uint64_t id) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=unsigned(r.status);a[1]=unsigned(r.reason);a[2]=r.geometry?1:0;a[3]=double(id);
    a[6]=double(r.candidates.size());a[7]=r.candidates_examined;a[8]=r.sqrt_refinements;a[9]=r.sqrt_refinement_limited?1:0;
    a[10]=r.squared_cross?1:0;if(r.squared_cross){a[11]=r.squared_cross->lower();a[12]=r.squared_cross->upper();}
    a[13]=r.sine_squared?1:0;if(r.sine_squared){a[14]=r.sine_squared->lower();a[15]=r.sine_squared->upper();}
    if(r.geometry){const auto&g=*r.geometry;a[4]=g.surviving_features;a[5]=unsigned(g.relation);put_bounds(a,16,g.barycentric);put_bounds(a,22,g.closest_local);put_bounds(a,28,g.closest);
        put_bounds(a,34,g.delta);put_bounds(a,40,g.normal);put_bounds(a,46,g.sphere_point);a[52]=g.squared_distance.lower();a[53]=g.squared_distance.upper();
        a[54]=g.distance.lower();a[55]=g.distance.upper();a[56]=g.gap.lower();a[57]=g.gap.upper();}return a;
}
bool same_source(const sphere_tri::StaticTriangle& a,const sphere_tri::StaticTriangle& b) {
    if(a.id!=b.id)return false;
    const auto same=[](double x,double y){return std::bit_cast<uint64_t>(x)==std::bit_cast<uint64_t>(y);};
    for(unsigned j=0;j<3;++j)if(!same(a.vertices[j].x,b.vertices[j].x)||!same(a.vertices[j].y,b.vertices[j].y)||!same(a.vertices[j].z,b.vertices[j].z))return false;
    return true;
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> sphere_triangle_mesh_packet(const SphereTriangleMeshRecord& record) {
    const auto& r=record.result;std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
    a[0]=unsigned(r.status);a[1]=unsigned(r.reason);a[2]=r.nearest?1:0;a[3]=double(record.source.size());a[4]=double(r.rows.size());
    a[5]=r.failed_index?1:0;if(r.failed_index)a[6]=double(*r.failed_index);
    a[7]=r.first_failed_row?1:0;if(r.first_failed_row)a[8]=double(*r.first_failed_row);
    a[9]=double(r.queries);a[10]=double(r.candidates_examined);a[11]=double(r.sqrt_refinements);a[12]=double(r.sqrt_limited_rows);a[13]=double(r.failed_rows);
    if(r.nearest){const auto& n=*r.nearest;a[14]=double(n.possible_surface_ids.size());a[15]=n.squared_distance.lower();a[16]=n.squared_distance.upper();a[17]=n.distance.lower();a[18]=n.distance.upper();a[19]=n.gap.lower();a[20]=n.gap.upper();}
    return a;
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> sphere_triangle_mesh_source_packet(const SphereTriangleMeshRecord& record,std::size_t index) {
    const auto& t=record.source[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=double(index);a[1]=double(t.id);
    for(unsigned j=0;j<3;++j)put_vector(a,2+3*j,t.vertices[j]);
    a[11]=index<record.result.rows.size()?1:0;a[12]=index<record.result.rows.size()&&record.result.rows[index].query?1:0;
    if(record.result.nearest)a[13]=std::binary_search(record.result.nearest->possible_surface_ids.begin(),record.result.nearest->possible_surface_ids.end(),t.id)?1:0;
    return a;
}
void validate_sphere_triangle_mesh(const SphereTriangleMeshRecord& record,const sphere_tri::Settings& s) {
    using I=pikapika::interval::Interval;
    const auto& r=record.result;const auto n=record.source.size();
    require(n<=PP_SIM_SPHERE_TRIANGLE_MESH_MAX_SURFACES&&unsigned(r.status)<=unsigned(sphere_mesh::Status::unsupported_environment)&&unsigned(r.reason)<=unsigned(sphere_mesh::Reason::environment),PP_SIM_CORE_REJECTED,"Invalid triangle mesh model enum/source capacity");
    const bool complete=r.status==sphere_mesh::Status::completed;
    require(r.nearest.has_value()==complete&&(complete?r.reason==sphere_mesh::Reason::none:r.reason!=sphere_mesh::Reason::none),PP_SIM_CORE_REJECTED,"Invalid triangle mesh completion");
    require(r.rows.size()<=n&&(!r.failed_index||*r.failed_index<n),PP_SIM_CORE_REJECTED,"Invalid triangle mesh source diagnostic index");
    std::size_t queries=0,candidates=0,roots=0,limited=0,failed=0;std::optional<std::size_t> first;
    for(std::size_t j=0;j<r.rows.size();++j){const auto& row=r.rows[j];require(same_source(row.triangle,record.source[j]),PP_SIM_CORE_REJECTED,"Triangle mesh owned row changed source bits/order");
        if(!row.query)continue;
        const auto& q=*row.query;++queries;
        validate_sphere_triangle(q,row.triangle.id,s);finite_output(sphere_triangle_packet(q,row.triangle.id),PP_SIM_SPHERE_TRIANGLE_OUTPUT_COUNT);
        candidates+=q.candidates_examined;roots+=q.sqrt_refinements;limited+=q.sqrt_refinement_limited?1u:0u;
        if(q.status!=sphere_tri::Status::completed){++failed;if(!first)first=j;}
    }
    require(r.queries==queries&&r.candidates_examined==candidates&&r.sqrt_refinements==roots&&r.sqrt_limited_rows==limited&&r.failed_rows==failed&&r.first_failed_row==first&&queries<=64&&candidates<=448&&roots<=32768,PP_SIM_CORE_REJECTED,"Inconsistent triangle mesh actual work/prefix");
    if(r.status==sphere_mesh::Status::invalid_input||r.status==sphere_mesh::Status::budget_exceeded||r.status==sphere_mesh::Status::unsupported_environment)
        require(r.rows.empty()&&queries==0,PP_SIM_CORE_REJECTED,"Triangle mesh preflight published rows");
    if(r.status==sphere_mesh::Status::row_failure)require(failed>0&&r.rows.size()==n&&queries==n,PP_SIM_CORE_REJECTED,"Triangle mesh row failure skipped diagnostics");
    if(complete){require(n>0&&r.rows.size()==n&&queries==n&&failed==0&&!r.failed_index,PP_SIM_CORE_REJECTED,"Incomplete successful triangle mesh rows");
        auto ds=r.rows[0].query->geometry->squared_distance,d=r.rows[0].query->geometry->distance,gap=r.rows[0].query->geometry->gap;
        for(const auto& row:r.rows){const auto& g=*row.query->geometry;ds=I(std::min(ds.lower(),g.squared_distance.lower()),std::min(ds.upper(),g.squared_distance.upper()));d=I(std::min(d.lower(),g.distance.lower()),std::min(d.upper(),g.distance.upper()));gap=I(std::min(gap.lower(),g.gap.lower()),std::min(gap.upper(),g.gap.upper()));}
        const auto equal=[](I a,I b){return std::bit_cast<uint64_t>(a.lower())==std::bit_cast<uint64_t>(b.lower())&&std::bit_cast<uint64_t>(a.upper())==std::bit_cast<uint64_t>(b.upper());};
        require(equal(r.nearest->squared_distance,ds)&&equal(r.nearest->distance,d)&&equal(r.nearest->gap,gap),PP_SIM_CORE_REJECTED,"Triangle mesh aggregate endpoints differ");
        std::vector<uint64_t> ids;ids.reserve(n);for(const auto& row:r.rows)if(row.query->geometry->squared_distance.lower()<=ds.upper())ids.push_back(row.triangle.id);std::sort(ids.begin(),ids.end());
        require(!ids.empty()&&ids==r.nearest->possible_surface_ids,PP_SIM_CORE_REJECTED,"Triangle mesh possible winners lost/duplicated");
    }
    for(std::size_t j=0;j<n;++j)finite_output(sphere_triangle_mesh_source_packet(record,j),PP_SIM_SPHERE_TRIANGLE_MESH_SOURCE_COUNT);
    finite_output(sphere_triangle_mesh_packet(record),PP_SIM_SPHERE_TRIANGLE_MESH_OUTPUT_COUNT);
}
optical_bounds::Bounds3 bounds_at(std::size_t offset) {
    using I=pikapika::interval::Interval;
    return {I(input_f64[offset],input_f64[offset+1]),I(input_f64[offset+2],input_f64[offset+3]),I(input_f64[offset+4],input_f64[offset+5])};
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> bounded_geometry_packet(const optical_bounds::Result& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
    a[0]=int(r.status);a[1]=int(r.reason);a[2]=r.nearest?1:0;a[3]=r.root_count;
    a[4]=r.considered_count;a[5]=r.sqrt_refinements;a[6]=r.refinement_limited?1:0;
    a[7]=r.discriminant?1:0;if(r.discriminant){a[8]=r.discriminant->lower();a[9]=r.discriminant->upper();}
    for(std::size_t i=0;i<2;++i){const auto& c=r.candidates[i];const auto o=10+i*4;
        a[o]=c.parameter.lower();a[o+1]=c.parameter.upper();a[o+2]=int(c.state);a[o+3]=int(c.reason);}
    if(r.nearest){const auto& h=*r.nearest;a[18]=h.parameter.lower();a[19]=h.parameter.upper();
        a[20]=h.physical_distance.lower();a[21]=h.physical_distance.upper();put_bounds(a,22,h.position);
        put_bounds(a,28,h.geometric_normal);put_bounds(a,34,h.incident_normal);a[40]=h.front_face?1:0;}
    return a;
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> route_segment_packet(const route::Segment& s) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
    a[0]=int(s.branch);a[1]=s.geometry.nearest?1:0;a[2]=int(s.geometry.status);a[3]=int(s.geometry.reason);a[4]=s.interface?1:0;
    if(s.interface){a[5]=int(s.interface->kind);a[6]=int(s.interface->reason);}a[7]=s.outgoing?1:0;a[8]=s.factor?1:0;a[9]=s.accumulated?1:0;
    put_bounds(a,10,s.incoming.origin);put_bounds(a,16,s.incoming.direction);a[22]=s.incoming.minimum_parameter;a[23]=s.incoming.maximum_parameter;
    a[24]=s.incident_index.lower();a[25]=s.incident_index.upper();a[26]=s.other_index.lower();a[27]=s.other_index.upper();
    if(s.geometry.nearest){const auto& h=*s.geometry.nearest;put_bounds(a,28,h.position);a[34]=h.parameter.lower();a[35]=h.parameter.upper();
        a[36]=h.physical_distance.lower();a[37]=h.physical_distance.upper();put_bounds(a,38,h.incident_normal);a[62]=h.front_face?1:0;}
    if(s.outgoing)put_bounds(a,44,s.outgoing->direction);if(s.factor){a[50]=s.factor->lower();a[51]=s.factor->upper();}
    if(s.accumulated){const auto& t=*s.accumulated;a[52]=t.distance.lower();a[53]=t.distance.upper();a[54]=t.optical_path_length.lower();a[55]=t.optical_path_length.upper();a[56]=t.throughput.lower();a[57]=t.throughput.upper();}
    a[58]=s.geometry.sqrt_refinements;a[59]=s.geometry.refinement_limited?1:0;if(s.interface){a[58]+=s.interface->sqrt_refinements;a[59]=a[59]||s.interface->refinement_limited;}
    a[60]=s.geometry.considered_count;a[61]=s.geometry.root_count;return a;
}
void put_interval(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& a,std::size_t o,pikapika::interval::Interval x){a[o]=x.lower();a[o+1]=x.upper();}
void put_complex(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& a,std::size_t o,const polarized_route::ComplexBounds& c){put_interval(a,o,c.real);put_interval(a,o+2,c.imag);}
void put_coherency(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& a,std::size_t o,const polarized_route::Coherency& c){
    for(unsigned j=0;j<3;++j)put_interval(a,o+2*j,c.diagonal[j]);
    for(unsigned j=0;j<3;++j)put_complex(a,o+6+4*j,c.upper[j]);
}

std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> polarized_route_packet(const polarized_route::Result& r,double wavelength){
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=int(r.status);a[1]=int(r.power_failure);a[2]=r.geometry?1:0;
        if(r.geometry){const auto& g=*r.geometry;a[3]=int(g.status);a[4]=g.completed_steps;a[5]=g.failed_step;a[6]=double(g.segments.size());a[55]=g.completion?1:0;
            if(g.completion){put_bounds(a,18,g.completion->ray.origin);put_bounds(a,24,g.completion->ray.direction);put_interval(a,30,g.completion->index);a[52]=g.completion->ray.minimum_parameter;a[53]=g.completion->ray.maximum_parameter;put_interval(a,56,g.completion->totals.distance);put_interval(a,58,g.completion->totals.optical_path_length);put_interval(a,60,g.completion->totals.throughput);}}
        a[7]=r.initial_frame?1:0;a[8]=r.initial_state?1:0;a[9]=double(r.segments.size());a[10]=r.completed_power_steps;a[11]=r.failed_power_step;
        a[12]=r.geometry_queries;a[13]=r.interface_queries;a[14]=r.geometry_sqrt_refinements;a[15]=r.power_sqrt_refinements;a[16]=r.refinement_limited?1:0;a[17]=r.completion?1:0;
        if(r.completion){const auto& c=*r.completion;put_bounds(a,18,c.ray.origin);put_bounds(a,24,c.ray.direction);put_interval(a,30,c.index);put_interval(a,32,c.state.power);put_coherency(a,34,c.state.coherency);a[52]=c.ray.minimum_parameter;a[53]=c.ray.maximum_parameter;}
        a[54]=wavelength;return a;
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> polarized_initial_packet(const polarized_route::Result& r){
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=r.initial_frame?1:0;a[1]=r.initial_state?1:0;
        if(r.initial_frame){put_bounds(a,2,r.initial_frame->direction);put_bounds(a,8,r.initial_frame->first);put_bounds(a,14,r.initial_frame->second);}
        if(r.initial_state){put_interval(a,20,r.initial_state->power);put_coherency(a,22,r.initial_state->coherency);}
        return a;
}
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> polarized_power_packet(const polarized_route::Segment& p){
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
            a[0]=p.ordinal;a[1]=int(p.branch);a[2]=p.s?1:0;a[3]=p.p?1:0;a[4]=p.exact_normal?1:0;a[5]=p.homogeneous?1:0;a[6]=p.outgoing?1:0;
            if(p.s)put_complex(a,7,*p.s);if(p.p)put_complex(a,11,*p.p);if(p.outgoing){put_interval(a,15,p.outgoing->power);put_coherency(a,17,p.outgoing->coherency);}
            return a;
}
void publish_bounded_geometry(const optical_bounds::Result& r) {
    const auto a=bounded_geometry_packet(r);
    finite_output(a,PP_SIM_BOUNDED_GEOMETRY_OUTPUT_COUNT);publish(a,PP_SIM_BOUNDED_GEOMETRY_OUTPUT_COUNT);
}
void publish_bounded_interface(const optical_bounds::InterfaceResult& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
    a[0]=int(r.kind);a[1]=int(r.reason);a[2]=r.sqrt_refinements;a[3]=r.refinement_limited?1:0;a[4]=r.exact_grazing?1:0;a[5]=r.vacuum_wavelength_m;
    const std::optional<optical_bounds::Bounds3>* vectors[]{&r.incident_unit,&r.normal_unit,&r.reflected,&r.transmitted};
    for(unsigned j=0;j<4;++j){a[6+j]=*vectors[j]?1:0;if(*vectors[j])put_bounds(a,14+6*j,**vectors[j]);}
    a[10]=r.power?1:0;a[11]=r.cosine_incident?1:0;a[12]=r.cosine_transmitted?1:0;a[13]=r.discriminant?1:0;
    if(r.power){const auto& p=*r.power;const pikapika::interval::Interval power[]{p.reflectance_s,p.transmittance_s,p.reflectance_p,p.transmittance_p,p.reflectance_unpolarized,p.transmittance_unpolarized};
        for(unsigned j=0;j<6;++j){a[38+2*j]=power[j].lower();a[39+2*j]=power[j].upper();}}
    if(r.cosine_incident){a[50]=r.cosine_incident->lower();a[51]=r.cosine_incident->upper();}
    if(r.cosine_transmitted){a[52]=r.cosine_transmitted->lower();a[53]=r.cosine_transmitted->upper();}
    if(r.discriminant){a[54]=r.discriminant->lower();a[55]=r.discriminant->upper();}
    a[56]=r.incident_dot.lower();a[57]=r.incident_dot.upper();
    finite_output(a,PP_SIM_BOUNDED_INTERFACE_OUTPUT_COUNT);publish(a,PP_SIM_BOUNDED_INTERFACE_OUTPUT_COUNT);
}
void publish_geometry(const geometry::Result& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
    a[0]=int(r.status);a[1]=int(r.reason);a[2]=r.nearest?1:0;a[3]=r.root_count;
    a[4]=r.considered_count;a[5]=r.sqrt_refinements;a[6]=r.refinement_limited?1:0;
    a[7]=r.discriminant?1:0;if(r.discriminant){a[8]=r.discriminant->lower();a[9]=r.discriminant->upper();}
    for(std::size_t i=0;i<2;++i){const auto& c=r.candidates[i];const auto o=10+i*4;
        a[o]=c.parameter.lower();a[o+1]=c.parameter.upper();a[o+2]=int(c.state);a[o+3]=int(c.reason);}
    if(r.nearest){const auto& h=*r.nearest;a[18]=h.parameter.lower();a[19]=h.parameter.upper();
        a[20]=h.physical_distance.lower();a[21]=h.physical_distance.upper();
        put_bounds(a,22,h.position);put_bounds(a,28,h.geometric_normal);put_bounds(a,34,h.incident_normal);
        a[40]=h.parameter_estimate;a[41]=h.physical_distance_estimate;put_vector(a,42,h.position_estimate);
        put_vector(a,45,h.geometric_normal_estimate);put_vector(a,48,h.incident_normal_estimate);a[51]=h.front_face?1:0;}
    finite_output(a,PP_SIM_GEOMETRY_OUTPUT_COUNT);publish(a,PP_SIM_GEOMETRY_OUTPUT_COUNT);
}
void put_frame(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& a,std::size_t offset,const polarization::Frame& f) {
    put_vector(a,offset,f.direction);put_vector(a,offset+3,f.first);put_vector(a,offset+6,f.second);
}
void put_branch(std::array<double,PP_SIM_OUTPUT_F64_CAPACITY>& a,std::size_t offset,const polarization::Branch& b) {
    put_frame(a,offset,b.frame);a[offset+9]=b.power.i;a[offset+10]=b.power.q;a[offset+11]=b.power.u;a[offset+12]=b.power.v;
    a[offset+13]=b.amplitude_s.real();a[offset+14]=b.amplitude_s.imag();a[offset+15]=b.amplitude_p.real();a[offset+16]=b.amplitude_p.imag();
}
void publish_polarization(const polarization::Split& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=int(r.failure);a[1]=int(r.interface.kind);a[2]=int(r.interface.uncertainty);
    a[3]=r.reflected?1:0;a[4]=r.transmitted?1:0;put_frame(a,5,r.input_frame);
    if(r.reflected)put_branch(a,14,*r.reflected);if(r.transmitted)put_branch(a,31,*r.transmitted);
    a[48]=r.interface.discriminant.lower();a[49]=r.interface.discriminant.upper();a[50]=r.interface.incident_dot.lower();a[51]=r.interface.incident_dot.upper();
    a[52]=r.interface.cosine_incident;a[53]=r.interface.cosine_transmitted?1:0;a[54]=r.interface.cosine_transmitted.value_or(0);
    a[55]=r.interface.exact_grazing?1:0;a[56]=r.interface.vacuum_wavelength_m;
    finite_output(a,PP_SIM_POLARIZATION_OUTPUT_COUNT);publish(a,PP_SIM_POLARIZATION_OUTPUT_COUNT);
}
dyn::CcdSettings ccd_settings() {
    dyn::CcdSettings s;s.time_tolerance=input_f64[0];s.spatial_tolerance=input_f64[1];s.minimum_impact_speed=input_f64[2];
    s.closing_residual_tolerance=input_f64[3];s.relative_energy_tolerance=input_f64[4];
    s.max_event_batches=unsigned(query_integer(input_f64[5],1,32));s.max_free_segments=unsigned(query_integer(input_f64[6],1,65));
    s.max_pair_queries=query_integer(input_f64[7],1,100000);s.max_root_evaluations=query_integer(input_f64[8],1,1000000);
    s.query_evaluations=query_integer(input_f64[9],1,PP_SIM_MAX_QUERY_EVALUATIONS);s.query_frontier=query_integer(input_f64[10],1,PP_SIM_MAX_QUERY_FRONTIER);
    s.query_depth=unsigned(query_integer(input_f64[11],0,128));s.solver.velocity_iterations=unsigned(query_integer(input_f64[12],1,128));
    s.solver.max_contacts=query_integer(input_f64[13],1,PP_SIM_MAX_CONTACTS);s.solver.restitution_velocity_threshold=input_f64[14];s.solver.max_angular_increment=input_f64[15];return s;
}
supported::Settings supported_settings(){
    require(std::all_of(input_f64.begin(),input_f64.begin()+PP_SIM_SUPPORTED_SETTINGS_COUNT,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"W2 settings must be finite");
    require(input_f64[32]==0,PP_SIM_INVALID_ARGUMENT,"W2 reserved setting must be zero");
    supported::Settings s;s.maximum_substep=input_f64[0];s.minimum_substep=input_f64[1];s.spatial_tolerance=input_f64[2];s.contact_band=input_f64[3];s.velocity_tolerance=input_f64[4];
    s.position_error_tolerance=input_f64[5];s.velocity_error_tolerance=input_f64[6];s.orientation_error_tolerance=input_f64[7];s.relative_impact_energy_tolerance=input_f64[8];
    s.max_attempts=unsigned(query_integer(input_f64[9],1,32768));s.max_segments=unsigned(query_integer(input_f64[10],1,8192));s.max_events=unsigned(query_integer(input_f64[11],1,1024));
    s.max_pair_queries=query_integer(input_f64[12],1,16000000);s.max_guard_evaluations=query_integer(input_f64[13],1,64000000);
    s.constraint.max_newton_iterations=unsigned(query_integer(input_f64[14],1,64));s.constraint.max_linear_solves=unsigned(query_integer(input_f64[15],1,256));
    s.constraint.max_line_search_steps=unsigned(query_integer(input_f64[16],1,32));s.constraint.max_contacts=query_integer(input_f64[17],1,128);s.impulse.max_contacts=s.constraint.max_contacts;
    s.constraint.minimum_scaled_pivot=input_f64[18];s.constraint.position_tolerance=input_f64[19];s.constraint.velocity_tolerance=input_f64[20];s.constraint.maximum_normal_rotation=input_f64[21];
    s.constraint.maximum_angular_increment=input_f64[22];s.guard.max_depth=unsigned(query_integer(input_f64[23],0,52));s.guard.max_evaluations=query_integer(input_f64[24],1,4000000);
    s.impulse.velocity_iterations=unsigned(query_integer(input_f64[25],1,128));s.guard.max_pair_queries=query_integer(input_f64[26],1,1000000);
    s.constraint.maximum_impulse=input_f64[27];s.constraint.initial_gap_tolerance=input_f64[28];s.constraint.initial_velocity_tolerance=input_f64[29];
    s.constraint.position_equation_tolerance=input_f64[30];s.constraint.velocity_equation_tolerance=input_f64[31];return s;
}
}
extern "C" {
uint32_t pp_sim_api_version(void){return PP_SIM_API_VERSION;}
double* pp_sim_input_f64_ptr(void){return input_f64.data();}
uint32_t* pp_sim_input_u32_ptr(void){return input_u32.data();}
const double* pp_sim_output_f64_ptr(void){return output.data();}
uint32_t pp_sim_input_f64_capacity(void){return PP_SIM_INPUT_F64_CAPACITY;}
uint32_t pp_sim_input_u32_capacity(void){return PP_SIM_INPUT_U32_CAPACITY;}
uint32_t pp_sim_output_f64_capacity(void){return PP_SIM_OUTPUT_F64_CAPACITY;}
uint32_t pp_sim_output_count(void){return output_count;}
int32_t pp_sim_last_status(void){return status;}
const char* pp_sim_error_ptr(void){return error.data();}
uint32_t pp_sim_error_length(void){return uint32_t(std::strlen(error.data()));}
int32_t pp_sim_reset(void){return guarded([]{for(auto& slot:worlds)if(slot.object)retire(slot);for(auto& slot:hulls)if(slot.object)retire(slot);route_record.reset();selection_record.reset();spot_record.reset();polarized_route_record.reset();packet_record.reset();motion_record.reset();skin_bind_record.reset();skin_deform_record.reset();derived_record.reset();sphere_triangle_record.reset();sphere_triangle_mesh_stage.reset();sphere_triangle_mesh_record.reset();packet_wavelength=0;total_vertices=0;total_triangles=0;output_count=0;});}
int32_t pp_sim_sphere_sphere_toi(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_TOI_INPUT_COUNT);
        publish_toi(continuous::sphere_sphere({vector_at(0),vector_at(3),input_f64[6]},
            {vector_at(7),vector_at(10),input_f64[13]},input_f64[14]));});
}
int32_t pp_sim_sphere_plane_toi(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_TOI_INPUT_COUNT);
        publish_toi(continuous::sphere_plane({vector_at(0),vector_at(3),input_f64[6]},
            {vector_at(7),input_f64[10],vector_at(11)},input_f64[14]));});
}
int32_t pp_sim_accelerated_spheres(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_ACCEL_PAIR_INPUT_COUNT);
        const auto s=accelerated_settings(21);
        publish_accelerated(accel::sphere_sphere(accelerated_sphere(0),accelerated_sphere(10),input_f64[20],s));});
}
int32_t pp_sim_accelerated_plane(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_ACCEL_PLANE_INPUT_COUNT);
        const auto s=accelerated_settings(15);
        publish_accelerated(accel::sphere_plane(accelerated_sphere(0),{vector_at(10),input_f64[13]},input_f64[14],s));});
}
int32_t pp_sim_dielectric_interface(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_OPTICS_INPUT_COUNT);
        publish_optics(optics::dielectric_interface({vector_at(0),vector_at(3),input_f64[6],input_f64[7],input_f64[8]}));});
}
int32_t pp_sim_optical_geometry(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_GEOMETRY_INPUT_COUNT);const auto shape=query_integer(input_f64[0],0,2);
        const geometry::Ray ray{vector_at(1),vector_at(4),input_f64[7],input_f64[8]};
        const geometry::Settings s{input_f64[17],unsigned(query_integer(input_f64[18],1,256))};
        if(shape==0){require(input_f64[15]==0,PP_SIM_INVALID_ARGUMENT,"Disk radius slot is reserved zero");
            publish_geometry(geometry::intersect(ray,geometry::PlaneDisk{vector_at(9),vector_at(12),input_f64[16]},s));}
        else if(shape==1){require(input_f64[12]==0&&input_f64[13]==0&&input_f64[14]==0&&input_f64[16]==0,
            PP_SIM_INVALID_ARGUMENT,"Full sphere axis/aperture slots are reserved zero");
            publish_geometry(geometry::intersect(ray,geometry::FullSphere{vector_at(9),input_f64[15]},s));}
        else publish_geometry(geometry::intersect(ray,geometry::SphericalCap{vector_at(9),vector_at(12),input_f64[15],input_f64[16]},s));});
}
int32_t pp_sim_bounded_geometry(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_BOUNDED_GEOMETRY_INPUT_COUNT);const auto shape=query_integer(input_f64[0],0,2);
        const optical_bounds::BoundedRay ray{bounds_at(1),bounds_at(7),input_f64[13],input_f64[14]};
        const optical_bounds::Settings settings{input_f64[23],unsigned(query_integer(input_f64[24],1,256))};
        if(shape==0){require(input_f64[21]==0,PP_SIM_INVALID_ARGUMENT,"Bounded disk radius slot is reserved zero");
            publish_bounded_geometry(optical_bounds::intersect(ray,geometry::PlaneDisk{vector_at(15),vector_at(18),input_f64[22]},settings));}
        else if(shape==1){require(input_f64[18]==0&&input_f64[19]==0&&input_f64[20]==0&&input_f64[22]==0,PP_SIM_INVALID_ARGUMENT,"Bounded sphere axis/aperture slots are reserved zero");
            publish_bounded_geometry(optical_bounds::intersect(ray,geometry::FullSphere{vector_at(15),input_f64[21]},settings));}
        else publish_bounded_geometry(optical_bounds::intersect(ray,geometry::SphericalCap{vector_at(15),vector_at(18),input_f64[21],input_f64[22]},settings));
    });
}
int32_t pp_sim_bounded_interface(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_BOUNDED_INTERFACE_INPUT_COUNT);
        using I=pikapika::interval::Interval;
        const optical_bounds::IndexBoundsInterfaceInput input{bounds_at(0),bounds_at(6),I(input_f64[12],input_f64[13]),I(input_f64[14],input_f64[15]),input_f64[16]};
        const optical_bounds::Settings settings{input_f64[17],unsigned(query_integer(input_f64[18],1,256))};
        publish_bounded_interface(optical_bounds::dielectric_interface_bounds(input,settings));
    });
}
int32_t pp_sim_optical_route(uint32_t count) {
    return guarded([&]{require(count>=PP_SIM_ROUTE_HEADER_COUNT,PP_SIM_INVALID_ARGUMENT,"Missing optical route header");
        const auto size=query_integer(input_f64[20],0,64);count_is(count,PP_SIM_ROUTE_HEADER_COUNT+uint32_t(size)*PP_SIM_ROUTE_STEP_INPUT_COUNT);
        using I=pikapika::interval::Interval;
        std::vector<route::Step> steps;steps.reserve(size);
        for(std::size_t j=0;j<size;++j){const auto o=PP_SIM_ROUTE_HEADER_COUNT+j*PP_SIM_ROUTE_STEP_INPUT_COUNT;
            const auto shape=query_integer(input_f64[o],0,2),branch=query_integer(input_f64[o+9],0,1);route::Step step;
            if(shape==0){require(input_f64[o+7]==0,PP_SIM_INVALID_ARGUMENT,"Route disk radius is reserved zero");step.surface=geometry::PlaneDisk{vector_at(o+1),vector_at(o+4),input_f64[o+8]};}
            else if(shape==1){require(input_f64[o+4]==0&&input_f64[o+5]==0&&input_f64[o+6]==0&&input_f64[o+8]==0,PP_SIM_INVALID_ARGUMENT,"Route sphere axis/aperture are reserved zero");step.surface=geometry::FullSphere{vector_at(o+1),input_f64[o+7]};}
            else step.surface=geometry::SphericalCap{vector_at(o+1),vector_at(o+4),input_f64[o+7],input_f64[o+8]};
            step.branch=branch==0?route::Branch::reflected:route::Branch::transmitted;step.next_index=I(input_f64[o+10],input_f64[o+11]);
            step.minimum_parameter=input_f64[o+12];step.maximum_parameter=input_f64[o+13];steps.push_back(std::move(step));
        }
        const route::Input source{{bounds_at(0),bounds_at(6),input_f64[12],input_f64[13]},I(input_f64[14],input_f64[15]),input_f64[16],steps};
        const route::Settings settings{{input_f64[18],unsigned(query_integer(input_f64[19],1,256))},unsigned(query_integer(input_f64[17],1,64))};
        auto result=route::trace_route(source,settings);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=int(result.status);a[1]=result.completed_steps;a[2]=result.failed_step;a[3]=double(result.segments.size());a[4]=result.completion?1:0;a[5]=double(result.segments.size());
        for(const auto& segment:result.segments){a[6]+=segment.geometry.sqrt_refinements;a[7]=a[7]||segment.geometry.refinement_limited;
            if(segment.interface){a[6]+=segment.interface->sqrt_refinements;a[7]=a[7]||segment.interface->refinement_limited;}}
        if(result.completion){const auto& c=*result.completion;put_bounds(a,8,c.ray.origin);put_bounds(a,14,c.ray.direction);
            a[20]=c.index.lower();a[21]=c.index.upper();a[22]=c.totals.distance.lower();a[23]=c.totals.distance.upper();
            a[24]=c.totals.optical_path_length.lower();a[25]=c.totals.optical_path_length.upper();a[26]=c.totals.throughput.lower();a[27]=c.totals.throughput.upper();
            a[28]=c.ray.minimum_parameter;a[29]=c.ray.maximum_parameter;}
        a[30]=source.vacuum_wavelength_m;finite_output(a,PP_SIM_ROUTE_OUTPUT_COUNT);route_record=std::move(result);publish(a,PP_SIM_ROUTE_OUTPUT_COUNT);
    });
}
int32_t pp_sim_optical_route_segment(uint32_t index) {
    return guarded([&]{require(route_record&&index<route_record->segments.size(),PP_SIM_INVALID_ARGUMENT,"No such segment in last optical route attempt");
        const auto a=route_segment_packet(route_record->segments[index]);finite_output(a,PP_SIM_ROUTE_SEGMENT_COUNT);publish(a,PP_SIM_ROUTE_SEGMENT_COUNT);
    });
}
int32_t pp_sim_polarized_route(uint32_t count) {
    return guarded([&]{require(count>=PP_SIM_POLARIZED_ROUTE_HEADER_COUNT,PP_SIM_INVALID_ARGUMENT,"Missing polarized route header");
        const auto size=query_integer(input_f64[20],0,64);count_is(count,PP_SIM_POLARIZED_ROUTE_HEADER_COUNT+uint32_t(size)*PP_SIM_ROUTE_STEP_INPUT_COUNT);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite polarized route exchange");
        require(input_f64[30]==0,PP_SIM_INVALID_ARGUMENT,"Polarized route reserved slot must be zero");
        using I=pikapika::interval::Interval;
        std::vector<route::Step> steps;steps.reserve(size);
        for(std::size_t j=0;j<size;++j){const auto o=PP_SIM_POLARIZED_ROUTE_HEADER_COUNT+j*PP_SIM_ROUTE_STEP_INPUT_COUNT;
            const auto shape=query_integer(input_f64[o],0,2),branch=query_integer(input_f64[o+9],0,1);route::Step step;
            if(shape==0){require(input_f64[o+7]==0,PP_SIM_INVALID_ARGUMENT,"Route disk radius is reserved zero");step.surface=geometry::PlaneDisk{vector_at(o+1),vector_at(o+4),input_f64[o+8]};}
            else if(shape==1){require(input_f64[o+4]==0&&input_f64[o+5]==0&&input_f64[o+6]==0&&input_f64[o+8]==0,PP_SIM_INVALID_ARGUMENT,"Route sphere axis/aperture are reserved zero");step.surface=geometry::FullSphere{vector_at(o+1),input_f64[o+7]};}
            else step.surface=geometry::SphericalCap{vector_at(o+1),vector_at(o+4),input_f64[o+7],input_f64[o+8]};
            step.branch=branch==0?route::Branch::reflected:route::Branch::transmitted;step.next_index=I(input_f64[o+10],input_f64[o+11]);
            step.minimum_parameter=input_f64[o+12];step.maximum_parameter=input_f64[o+13];steps.push_back(std::move(step));
        }
        const polarized_route::Input source{{{bounds_at(0),bounds_at(6),input_f64[12],input_f64[13]},I(input_f64[14],input_f64[15]),input_f64[16],steps},
            {input_f64[24],input_f64[25],input_f64[26],input_f64[27]},vector_at(21)};
        const polarized_route::Settings settings{{{input_f64[18],unsigned(query_integer(input_f64[19],1,256))},unsigned(query_integer(input_f64[17],1,64))},
            unsigned(query_integer(input_f64[28],1,256)),unsigned(query_integer(input_f64[29],1,4000000))};
        auto r=polarized_route::trace_route(source,settings);const auto a=polarized_route_packet(r,source.route.vacuum_wavelength_m);finite_output(a,PP_SIM_POLARIZED_ROUTE_OUTPUT_COUNT);polarized_route_record=std::move(r);publish(a,PP_SIM_POLARIZED_ROUTE_OUTPUT_COUNT);
    });
}
int32_t pp_sim_polarized_route_initial(void) {
    return guarded([&]{require(bool(polarized_route_record),PP_SIM_INVALID_ARGUMENT,"No polarized route snapshot");const auto& r=*polarized_route_record;
        const auto a=polarized_initial_packet(r);finite_output(a,PP_SIM_POLARIZED_ROUTE_INITIAL_COUNT);publish(a,PP_SIM_POLARIZED_ROUTE_INITIAL_COUNT);
    });
}
int32_t pp_sim_polarized_route_segment(uint32_t index,uint32_t part) {
    return guarded([&]{require(part<=1&&polarized_route_record,PP_SIM_INVALID_ARGUMENT,"No polarized route segment/part");const auto& r=*polarized_route_record;
        if(part==0){require(r.geometry&&index<r.geometry->segments.size(),PP_SIM_INVALID_ARGUMENT,"No polarized geometry segment");const auto a=route_segment_packet(r.geometry->segments[index]);finite_output(a,PP_SIM_ROUTE_SEGMENT_COUNT);publish(a,PP_SIM_ROUTE_SEGMENT_COUNT);}
        else{require(index<r.segments.size(),PP_SIM_INVALID_ARGUMENT,"No polarized power segment");const auto& p=r.segments[index];const auto a=polarized_power_packet(p);finite_output(a,PP_SIM_POLARIZED_ROUTE_SEGMENT_COUNT);publish(a,PP_SIM_POLARIZED_ROUTE_SEGMENT_COUNT);}
    });
}
int32_t pp_sim_skin_bind(uint32_t count) {
    return guarded([&]{require(count>=PP_SIM_SKIN_BIND_HEADER_COUNT&&count<=PP_SIM_INPUT_F64_CAPACITY,PP_SIM_INVALID_ARGUMENT,"Missing/oversized skin bind exchange");
        const auto n=query_integer(input_f64[0],0,PP_SIM_SKIN_MAX_BONES);count_is(count,PP_SIM_SKIN_BIND_HEADER_COUNT+uint32_t(n)*PP_SIM_SKIN_MATRIX_INPUT_COUNT);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite skin bind exchange");
        require(input_f64[6]==0&&input_f64[7]==0,PP_SIM_INVALID_ARGUMENT,"Skin bind reserved slots must be zero");
        const skin::Settings settings{unsigned(query_integer(input_f64[1],1,128)),unsigned(query_integer(input_f64[2],1,65536)),unsigned(query_integer(input_f64[3],1,262144)),input_f64[4],input_f64[5]};
        std::vector<skin::BoneMatrix> rest;rest.reserve(n);for(std::size_t j=0,o=PP_SIM_SKIN_BIND_HEADER_COUNT;j<n;++j,o+=PP_SIM_SKIN_MATRIX_INPUT_COUNT){skin::BoneMatrix b;b.bone_id=id_from(input_f64[o]);std::copy_n(input_f64.begin()+o+1,16,b.matrix.begin());rest.push_back(b);}
        auto r=skin::bind(rest,settings);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=int(r.status);a[1]=r.joints?1:0;a[2]=r.joints?double(r.joints->size()):0;a[3]=double(r.diagnostics.size());
        finite_output(a,PP_SIM_SKIN_OUTPUT_COUNT);skin_bind_record=std::move(r);publish(a,PP_SIM_SKIN_OUTPUT_COUNT);
    });
}
int32_t pp_sim_skin_bind_record(uint32_t kind,uint32_t index) {
    return guarded([&]{require(kind<=1&&skin_bind_record,PP_SIM_INVALID_ARGUMENT,"No skin bind snapshot/kind");const auto&r=*skin_bind_record;std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        if(kind==0){require(r.joints&&index<r.joints->size(),PP_SIM_INVALID_ARGUMENT,"No completed skin joint at index");const auto&j=(*r.joints)[index];a[0]=double(j.bone_id);std::copy(j.rest_world.begin(),j.rest_world.end(),a.begin()+1);std::copy(j.inverse_bind.begin(),j.inverse_bind.end(),a.begin()+17);finite_output(a,PP_SIM_SKIN_JOINT_COUNT);publish(a,PP_SIM_SKIN_JOINT_COUNT);}
        else{require(index<r.diagnostics.size(),PP_SIM_INVALID_ARGUMENT,"No skin bind diagnostic at index");const auto&d=r.diagnostics[index];a[0]=double(d.bone_id);a[1]=d.linear_condition?1:0;a[2]=d.linear_condition.value_or(0);a[3]=d.inverse_residual?1:0;a[4]=d.inverse_residual.value_or(0);a[5]=d.pivot_failure?1:0;finite_output(a,PP_SIM_SKIN_DIAGNOSTIC_COUNT);publish(a,PP_SIM_SKIN_DIAGNOSTIC_COUNT);}
    });
}
int32_t pp_sim_skin_deform(uint32_t count) {
    return guarded([&]{require(count>=PP_SIM_SKIN_DEFORM_HEADER_COUNT&&count<=PP_SIM_INPUT_F64_CAPACITY,PP_SIM_INVALID_ARGUMENT,"Missing/oversized skin deform exchange");
        const auto nj=query_integer(input_f64[0],0,PP_SIM_SKIN_MAX_BONES),np=query_integer(input_f64[1],0,PP_SIM_SKIN_MAX_BONES),nv=query_integer(input_f64[2],0,PP_SIM_SKIN_MAX_VERTICES),ni=query_integer(input_f64[3],0,PP_SIM_SKIN_MAX_INFLUENCES);
        count_is(count,PP_SIM_SKIN_DEFORM_HEADER_COUNT+uint32_t(nj)*PP_SIM_SKIN_JOINT_COUNT+uint32_t(np)*PP_SIM_SKIN_MATRIX_INPUT_COUNT+uint32_t(nv)*PP_SIM_SKIN_VERTEX_INPUT_COUNT+uint32_t(ni)*PP_SIM_SKIN_INFLUENCE_INPUT_COUNT);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite skin deform exchange");
        require(input_f64[9]==0&&input_f64[10]==0&&input_f64[11]==0,PP_SIM_INVALID_ARGUMENT,"Skin deform reserved slots must be zero");
        const skin::Settings settings{unsigned(query_integer(input_f64[4],1,128)),unsigned(query_integer(input_f64[5],1,65536)),unsigned(query_integer(input_f64[6],1,262144)),input_f64[7],input_f64[8]};
        std::vector<skin::JointBind> joints;joints.reserve(nj);std::size_t o=PP_SIM_SKIN_DEFORM_HEADER_COUNT;
        for(std::size_t j=0;j<nj;++j,o+=PP_SIM_SKIN_JOINT_COUNT){skin::JointBind b;b.bone_id=id_from(input_f64[o]);std::copy_n(input_f64.begin()+o+1,16,b.rest_world.begin());std::copy_n(input_f64.begin()+o+17,16,b.inverse_bind.begin());joints.push_back(b);}
        std::vector<skin::BoneMatrix> pose;pose.reserve(np);for(std::size_t j=0;j<np;++j,o+=PP_SIM_SKIN_MATRIX_INPUT_COUNT){skin::BoneMatrix b;b.bone_id=id_from(input_f64[o]);std::copy_n(input_f64.begin()+o+1,16,b.matrix.begin());pose.push_back(b);}
        struct VertexMeta{Vec3 position;std::size_t count;};std::vector<VertexMeta> meta;meta.reserve(nv);std::size_t consumed=0;
        for(std::size_t j=0;j<nv;++j,o+=PP_SIM_SKIN_VERTEX_INPUT_COUNT){const auto size=query_integer(input_f64[o+3],0,PP_SIM_SKIN_MAX_INFLUENCES);require(size<=ni-consumed,PP_SIM_INVALID_ARGUMENT,"Skin vertex influence counts exceed total");meta.push_back({vector_at(o),size});consumed+=size;}
        require(consumed==ni,PP_SIM_INVALID_ARGUMENT,"Skin vertex influence sum differs from total");std::vector<skin::Influence> influences;influences.reserve(ni);
        for(std::size_t j=0;j<ni;++j,o+=PP_SIM_SKIN_INFLUENCE_INPUT_COUNT)influences.push_back({id_from(input_f64[o]),input_f64[o+1]});
        require(o==count,PP_SIM_INVALID_ARGUMENT,"Skin exchange length mismatch");std::vector<skin::Vertex> vertices;vertices.reserve(nv);std::span<const skin::Influence> span(influences);consumed=0;for(const auto&m:meta){vertices.push_back({m.position,span.subspan(consumed,m.count)});consumed+=m.count;}
        auto r=skin::deform(vertices,joints,pose,settings);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=int(r.status);a[1]=r.positions?1:0;a[2]=r.positions?double(r.positions->size()):0;a[3]=double(r.inverse_diagnostics.size());a[4]=double(r.weight_residuals.size());
        finite_output(a,PP_SIM_SKIN_OUTPUT_COUNT);skin_deform_record=std::move(r);publish(a,PP_SIM_SKIN_OUTPUT_COUNT);
    });
}
int32_t pp_sim_skin_deform_record(uint32_t kind,uint32_t index) {
    return guarded([&]{require(kind<=2&&skin_deform_record,PP_SIM_INVALID_ARGUMENT,"No skin deform snapshot/kind");const auto&r=*skin_deform_record;std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};uint32_t size=0;
        if(kind==0){require(r.positions&&index<r.positions->size(),PP_SIM_INVALID_ARGUMENT,"No completed skin position at index");put_vector(a,0,(*r.positions)[index]);size=3;}
        else if(kind==1){require(index<r.inverse_diagnostics.size(),PP_SIM_INVALID_ARGUMENT,"No skin deform diagnostic at index");const auto&d=r.inverse_diagnostics[index];a[0]=double(d.bone_id);a[1]=d.linear_condition?1:0;a[2]=d.linear_condition.value_or(0);a[3]=d.inverse_residual?1:0;a[4]=d.inverse_residual.value_or(0);a[5]=d.pivot_failure?1:0;size=PP_SIM_SKIN_DIAGNOSTIC_COUNT;}
        else{require(index<r.weight_residuals.size(),PP_SIM_INVALID_ARGUMENT,"No skin weight residual at index");a[0]=r.weight_residuals[index];size=1;}finite_output(a,size);publish(a,size);
    });
}
int32_t pp_sim_derived_mesh(uint32_t f64_count,uint32_t u32_count) {
    return guarded([&]{
        require(f64_count>=PP_SIM_DERIVED_HEADER_COUNT&&f64_count<=PP_SIM_INPUT_F64_CAPACITY&&u32_count<=PP_SIM_INPUT_U32_CAPACITY,
            PP_SIM_INVALID_ARGUMENT,"Missing/oversized derived exchange");
        const auto nv=query_integer(input_f64[0],0,PP_SIM_DERIVED_MAX_VERTICES),nt=query_integer(input_f64[1],0,PP_SIM_DERIVED_MAX_TRIANGLES);
        count_is(f64_count,PP_SIM_DERIVED_HEADER_COUNT+uint32_t(nv)*3);count_is(u32_count,uint32_t(nt)*3);
        require(std::all_of(input_f64.begin(),input_f64.begin()+f64_count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite derived exchange");
        require(input_f64[5]==0&&input_f64[6]==0&&input_f64[7]==0,PP_SIM_INVALID_ARGUMENT,"Derived reserved slots must be zero");
        constexpr std::size_t maximum_u32=4294967295ULL;
        const derived::Settings settings{query_integer(input_f64[2],0,maximum_u32),query_integer(input_f64[3],0,maximum_u32),
            unsigned(query_integer(input_f64[4],0,maximum_u32))};
        std::vector<Vec3> positions;positions.reserve(nv);for(std::size_t i=0;i<nv;++i)positions.push_back(vector_at(PP_SIM_DERIVED_HEADER_COUNT+i*3));
        std::vector<derived::Triangle> triangles;triangles.reserve(nt);for(std::size_t i=0;i<nt;++i)triangles.push_back({input_u32[i*3],input_u32[i*3+1],input_u32[i*3+2]});
        auto r=derived::prepare(positions,triangles,settings);validate_derived(r,nv,nt,settings);
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=unsigned(r.status);a[1]=unsigned(r.reason);a[2]=r.geometry?1:0;
        if(r.geometry){a[3]=double(r.geometry->positions.size());a[4]=double(r.geometry->triangles.size());a[6]=double(r.geometry->interleaved.size());for(unsigned i=0;i<3;++i){a[14+i]=r.geometry->minimum[i];a[17+i]=r.geometry->maximum[i];}}
        a[5]=double(r.audits.size());a[7]=r.failed_vertex?1:0;a[8]=r.failed_vertex?double(*r.failed_vertex):0;
        a[9]=r.failed_face?1:0;a[10]=r.failed_face?double(*r.failed_face):0;a[11]=double(r.sqrt_refinements);a[12]=r.sqrt_limited_faces;
        finite_output(a,PP_SIM_DERIVED_OUTPUT_COUNT);
        static_assert(std::is_nothrow_move_assignable_v<std::optional<derived::Result>>,"Derived snapshot commit must not throw");
        derived_record=std::move(r);publish(a,PP_SIM_DERIVED_OUTPUT_COUNT);
    });
}
int32_t pp_sim_derived_mesh_record(uint32_t kind,uint32_t index) {
    return guarded([&]{require(kind<=3&&derived_record,PP_SIM_INVALID_ARGUMENT,"No derived snapshot/kind");const auto&r=*derived_record;
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};uint32_t count{};
        if(kind==3){require(index<r.audits.size(),PP_SIM_INVALID_ARGUMENT,"No derived audit at index");a=derived_audit_packet(r.audits[index]);count=PP_SIM_DERIVED_AUDIT_COUNT;}
        else{require(bool(r.geometry),PP_SIM_INVALID_ARGUMENT,"No completed derived geometry");const auto&g=*r.geometry;
            if(kind==0){require(index<g.positions.size(),PP_SIM_INVALID_ARGUMENT,"No derived vertex at index");std::copy(g.positions[index].begin(),g.positions[index].end(),a.begin());count=3;}
            else if(kind==1){require(index<g.triangles.size(),PP_SIM_INVALID_ARGUMENT,"No derived triangle at index");std::copy(g.triangles[index].begin(),g.triangles[index].end(),a.begin());count=3;}
            else{require(index<g.triangles.size(),PP_SIM_INVALID_ARGUMENT,"No derived expanded face at index");std::copy_n(g.interleaved.begin()+std::size_t(index)*18,18,a.begin());count=18;}}
        finite_output(a,count);publish(a,count);
    });
}
int32_t pp_sim_derived_mesh_records(uint32_t kind,uint32_t first,uint32_t record_count) {
    return guarded([&]{
        require(kind<=3&&derived_record,PP_SIM_INVALID_ARGUMENT,"No derived snapshot/kind");
        constexpr std::array<uint32_t,4> strides{3,3,18,PP_SIM_DERIVED_AUDIT_COUNT};
        const auto stride=strides[kind];
        require(record_count>0&&record_count<=(uint32_t(PP_SIM_OUTPUT_F64_CAPACITY)-uint32_t(PP_SIM_DERIVED_BATCH_HEADER_COUNT))/stride,
            PP_SIM_INVALID_ARGUMENT,"Invalid derived batch record count");
        const auto&r=*derived_record;
        if(kind!=3)require(bool(r.geometry),PP_SIM_INVALID_ARGUMENT,"No completed derived geometry");
        const std::size_t available=kind==3?r.audits.size():kind==0?r.geometry->positions.size():r.geometry->triangles.size();
        // Subtraction only after first<available avoids wrapping first+count.
        require(first<available&&record_count<=available-first,PP_SIM_INVALID_ARGUMENT,"Derived batch outside snapshot range");
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=kind;a[1]=first;a[2]=record_count;a[3]=stride;
        for(uint32_t j=0;j<record_count;++j){
            const std::size_t index=std::size_t(first)+j,offset=PP_SIM_DERIVED_BATCH_HEADER_COUNT+std::size_t(j)*stride;
            if(kind==3){const auto packet=derived_audit_packet(r.audits[index]);std::copy_n(packet.begin(),stride,a.begin()+offset);}
            else if(kind==0){const auto&v=r.geometry->positions[index];std::copy(v.begin(),v.end(),a.begin()+offset);}
            else if(kind==1){const auto&t=r.geometry->triangles[index];std::copy(t.begin(),t.end(),a.begin()+offset);}
            else std::copy_n(r.geometry->interleaved.begin()+index*18,18,a.begin()+offset);
        }
        const uint32_t count=PP_SIM_DERIVED_BATCH_HEADER_COUNT+record_count*stride;
        finite_output(a,count);publish(a,count);
    });
}
int32_t pp_sim_sphere_triangle(uint32_t count) {
    return guarded([&]{
        count_is(count,PP_SIM_SPHERE_TRIANGLE_INPUT_COUNT);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite sphere triangle exchange");
        require(input_f64[20]==0&&input_f64[21]==0&&input_f64[22]==0&&input_f64[23]==0,PP_SIM_INVALID_ARGUMENT,"Sphere triangle reserved slots must be zero");
        const auto id=id_from(input_f64[4]);constexpr std::size_t maximum_u32=4294967295ULL;
        const sphere_tri::Settings settings{unsigned(query_integer(input_f64[14],0,maximum_u32)),unsigned(query_integer(input_f64[15],0,maximum_u32)),
            unsigned(query_integer(input_f64[16],0,maximum_u32)),input_f64[17],input_f64[18],input_f64[19]};
        const sphere_tri::StaticTriangle triangle{id,{{vector_at(5),vector_at(8),vector_at(11)}}};
        auto r=sphere_tri::query_sphere_triangle({vector_at(0),input_f64[3]},triangle,settings);validate_sphere_triangle(r,id,settings);
        const auto a=sphere_triangle_packet(r,id);finite_output(a,PP_SIM_SPHERE_TRIANGLE_OUTPUT_COUNT);
        static_assert(std::is_nothrow_move_assignable_v<std::optional<SphereTriangleRecord>>,"Sphere triangle snapshot commit must not throw");
        SphereTriangleRecord candidate{id,std::move(r)};sphere_triangle_record=std::move(candidate);publish(a,PP_SIM_SPHERE_TRIANGLE_OUTPUT_COUNT);
    });
}
int32_t pp_sim_sphere_triangle_candidate(uint32_t index) {
    return guarded([&]{
        require(sphere_triangle_record&&index<sphere_triangle_record->result.candidates.size(),PP_SIM_INVALID_ARGUMENT,"No sphere triangle candidate at ordinal");
        const auto a=sphere_triangle_candidate_packet(sphere_triangle_record->result.candidates[index]);
        finite_output(a,PP_SIM_SPHERE_TRIANGLE_CANDIDATE_COUNT);publish(a,PP_SIM_SPHERE_TRIANGLE_CANDIDATE_COUNT);
    });
}
int32_t pp_sim_sphere_triangle_mesh_begin(uint32_t triangle_count) {
    return guarded([&]{
        require(triangle_count<=PP_SIM_SPHERE_TRIANGLE_MESH_MAX_SURFACES,PP_SIM_INVALID_ARGUMENT,"Triangle mesh staging exceeds 64 surfaces");
        SphereTriangleMeshStage candidate;candidate.expected=triangle_count;candidate.source.reserve(triangle_count);
        static_assert(std::is_nothrow_move_assignable_v<std::optional<SphereTriangleMeshStage>>,"Triangle mesh staging commit must not throw");
        sphere_triangle_mesh_stage=std::move(candidate);
    });
}
int32_t pp_sim_sphere_triangle_mesh_append(uint32_t count) {
    return guarded([&]{
        require(sphere_triangle_mesh_stage.has_value(),PP_SIM_INVALID_ARGUMENT,"Triangle mesh append requires begin");
        require(count>=PP_SIM_SPHERE_TRIANGLE_MESH_APPEND_STRIDE&&count<=PP_SIM_SPHERE_TRIANGLE_MESH_APPEND_MAX_COUNT&&count%PP_SIM_SPHERE_TRIANGLE_MESH_APPEND_STRIDE==0,PP_SIM_INVALID_ARGUMENT,"Triangle mesh chunk must contain 1..6 complete sources");
        const auto& old=*sphere_triangle_mesh_stage;const std::size_t additional=count/PP_SIM_SPHERE_TRIANGLE_MESH_APPEND_STRIDE;
        require(old.source.size()<=old.expected&&additional<=old.expected-old.source.size(),PP_SIM_INVALID_ARGUMENT,"Triangle mesh append exceeds declared count");
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite triangle mesh source exchange");
        std::array<sphere_tri::StaticTriangle,6> chunk{};
        for(std::size_t j=0;j<additional;++j){const auto o=j*PP_SIM_SPHERE_TRIANGLE_MESH_APPEND_STRIDE;chunk[j]={id_from(input_f64[o]),{{vector_at(o+1),vector_at(o+4),vector_at(o+7)}}};}
        // Parsing precedes any allocation/commit. Even a bad last ID cannot
        // append preceding valid sources from the same chunk.
        auto candidate=old;candidate.source.reserve(candidate.expected);
        candidate.source.insert(candidate.source.end(),chunk.begin(),chunk.begin()+additional);
        sphere_triangle_mesh_stage=std::move(candidate);
    });
}
int32_t pp_sim_sphere_triangle_mesh(uint32_t count) {
    return guarded([&]{
        count_is(count,PP_SIM_SPHERE_TRIANGLE_MESH_INPUT_COUNT);
        require(sphere_triangle_mesh_stage&&sphere_triangle_mesh_stage->source.size()==sphere_triangle_mesh_stage->expected,PP_SIM_INVALID_ARGUMENT,"Triangle mesh query requires complete staging");
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite triangle mesh query exchange");
        require(input_f64[11]==0&&input_f64[12]==0&&input_f64[13]==0,PP_SIM_INVALID_ARGUMENT,"Triangle mesh reserved slots must be zero");
        constexpr std::size_t maximum_u32=4294967295ULL;
        const sphere_mesh::Settings settings{query_integer(input_f64[4],0,maximum_u32),{
            unsigned(query_integer(input_f64[5],0,maximum_u32)),unsigned(query_integer(input_f64[6],0,maximum_u32)),unsigned(query_integer(input_f64[7],0,maximum_u32)),input_f64[8],input_f64[9],input_f64[10]}};
        SphereTriangleMeshRecord candidate;candidate.source=sphere_triangle_mesh_stage->source;
        candidate.result=sphere_mesh::query({vector_at(0),input_f64[3]},candidate.source,settings);
        validate_sphere_triangle_mesh(candidate,settings.primitive);const auto a=sphere_triangle_mesh_packet(candidate);
        static_assert(std::is_nothrow_move_assignable_v<std::optional<SphereTriangleMeshRecord>>,"Triangle mesh snapshot commit must not throw");
        sphere_triangle_mesh_record=std::move(candidate);publish(a,PP_SIM_SPHERE_TRIANGLE_MESH_OUTPUT_COUNT);
    });
}
int32_t pp_sim_sphere_triangle_mesh_source(uint32_t ordinal) {
    return guarded([&]{require(sphere_triangle_mesh_record&&ordinal<sphere_triangle_mesh_record->source.size(),PP_SIM_INVALID_ARGUMENT,"No triangle mesh source at ordinal");
        const auto a=sphere_triangle_mesh_source_packet(*sphere_triangle_mesh_record,ordinal);finite_output(a,PP_SIM_SPHERE_TRIANGLE_MESH_SOURCE_COUNT);publish(a,PP_SIM_SPHERE_TRIANGLE_MESH_SOURCE_COUNT);});
}
int32_t pp_sim_sphere_triangle_mesh_row(uint32_t ordinal) {
    return guarded([&]{require(sphere_triangle_mesh_record&&ordinal<sphere_triangle_mesh_record->result.rows.size()&&sphere_triangle_mesh_record->result.rows[ordinal].query,PP_SIM_INVALID_ARGUMENT,"No examined triangle mesh row at ordinal");
        const auto& row=sphere_triangle_mesh_record->result.rows[ordinal];const auto a=sphere_triangle_packet(*row.query,row.triangle.id);finite_output(a,PP_SIM_SPHERE_TRIANGLE_OUTPUT_COUNT);publish(a,PP_SIM_SPHERE_TRIANGLE_OUTPUT_COUNT);});
}
int32_t pp_sim_sphere_triangle_mesh_candidate(uint32_t row,uint32_t ordinal) {
    return guarded([&]{require(sphere_triangle_mesh_record&&row<sphere_triangle_mesh_record->result.rows.size()&&sphere_triangle_mesh_record->result.rows[row].query&&ordinal<sphere_triangle_mesh_record->result.rows[row].query->candidates.size(),PP_SIM_INVALID_ARGUMENT,"No triangle mesh candidate at ordinals");
        const auto a=sphere_triangle_candidate_packet(sphere_triangle_mesh_record->result.rows[row].query->candidates[ordinal]);finite_output(a,PP_SIM_SPHERE_TRIANGLE_CANDIDATE_COUNT);publish(a,PP_SIM_SPHERE_TRIANGLE_CANDIDATE_COUNT);});
}
int32_t pp_sim_motion(uint32_t count) {
    return guarded([&]{require(count>=PP_SIM_MOTION_HEADER_COUNT,PP_SIM_INVALID_ARGUMENT,"Missing motion header");
        const auto nb=query_integer(input_f64[0],0,128),nt=query_integer(input_f64[1],0,128),nk=query_integer(input_f64[2],0,4096);
        count_is(count,PP_SIM_MOTION_HEADER_COUNT+uint32_t(nb)*12+uint32_t(nt)*3+uint32_t(nk)*11);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite motion exchange");
        require(input_f64[9]==0,PP_SIM_INVALID_ARGUMENT,"Motion reserved slot must be zero");
        const auto mode=query_integer(input_f64[5],0,1);const motion::Settings settings{unsigned(query_integer(input_f64[6],1,128)),unsigned(query_integer(input_f64[7],1,128)),unsigned(query_integer(input_f64[8],1,4096))};
        const auto transform_at=[&](std::size_t o){return pikapika::Transform{vector_at(o),{input_f64[o+3],input_f64[o+4],input_f64[o+5],input_f64[o+6]},vector_at(o+7)};};
        std::vector<motion::Bone> bones;bones.reserve(nb);std::size_t o=PP_SIM_MOTION_HEADER_COUNT;
        for(std::size_t j=0;j<nb;++j,o+=12)bones.push_back({id_from(input_f64[o]),input_f64[o+1]==0?0:id_from(input_f64[o+1]),transform_at(o+2)});
        std::vector<std::vector<motion::Key>> keys;keys.reserve(nt);std::vector<motion::Track> tracks;tracks.reserve(nt);std::size_t consumed=0;
        for(std::size_t j=0;j<nt;++j){require(o+3<=count,PP_SIM_INVALID_ARGUMENT,"Truncated motion track");const auto id=id_from(input_f64[o]);const auto interpolation=query_integer(input_f64[o+1],0,1),size=query_integer(input_f64[o+2],0,4096);o+=3;
            require(size<=nk-consumed&&o+11*size<=count,PP_SIM_INVALID_ARGUMENT,"Motion track key count mismatch");keys.emplace_back();auto& values=keys.back();values.reserve(size);
            for(std::size_t k=0;k<size;++k,o+=11)values.push_back({input_f64[o],transform_at(o+1)});
            consumed+=size;tracks.push_back({id,interpolation==0?motion::Interpolation::linear:motion::Interpolation::step,values});}
        require(consumed==nk&&o==count,PP_SIM_INVALID_ARGUMENT,"Motion key total mismatch");
        auto r=motion::sample({bones,{input_f64[3],tracks}},input_f64[4],mode==0?motion::Playback::clamp:motion::Playback::loop,settings);
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=int(r.status);a[1]=r.pose?1:0;a[2]=r.pose?double(r.pose->bones.size()):0;a[3]=input_f64[4];a[4]=r.pose?r.pose->sampled_time:0;a[5]=input_f64[3];a[6]=double(mode);a[7]=double(nt);a[8]=double(nk);
        finite_output(a,PP_SIM_MOTION_OUTPUT_COUNT);motion_record=std::move(r);publish(a,PP_SIM_MOTION_OUTPUT_COUNT);
    });
}
int32_t pp_sim_motion_bone(uint32_t index) {
    return guarded([&]{require(motion_record&&motion_record->pose&&index<motion_record->pose->bones.size(),PP_SIM_INVALID_ARGUMENT,"No such bone in completed motion snapshot");
        const auto& pose=*motion_record->pose;const auto& b=pose.bones[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=double(b.id);a[1]=double(b.parent_id);put_vector(a,2,b.local.position);
        a[5]=b.local.rotation.x;a[6]=b.local.rotation.y;a[7]=b.local.rotation.z;a[8]=b.local.rotation.w;put_vector(a,9,b.local.scale);std::copy(b.local_matrix.begin(),b.local_matrix.end(),a.begin()+12);std::copy(b.world_matrix.begin(),b.world_matrix.end(),a.begin()+28);
        const auto order=std::find(pose.evaluation_order.begin(),pose.evaluation_order.end(),b.id);require(order!=pose.evaluation_order.end(),PP_SIM_INTERNAL_ERROR,"Motion evaluation rank missing");a[44]=double(order-pose.evaluation_order.begin());finite_output(a,PP_SIM_MOTION_BONE_COUNT);publish(a,PP_SIM_MOTION_BONE_COUNT);
    });
}
int32_t pp_sim_polarized_packet(uint32_t count) {
    return guarded([&]{require(count>=PP_SIM_PACKET_HEADER_COUNT,PP_SIM_INVALID_ARGUMENT,"Missing polarized packet header");
        const auto n=query_integer(input_f64[0],0,1024),size=query_integer(input_f64[1],0,64);
        count_is(count,PP_SIM_PACKET_HEADER_COUNT+uint32_t(size)*PP_SIM_ROUTE_STEP_INPUT_COUNT+uint32_t(n)*PP_SIM_PACKET_INPUT_COUNT);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite packet exchange");
        require(input_f64[22]==0,PP_SIM_INVALID_ARGUMENT,"Packet reserved slot must be zero");
        using I=pikapika::interval::Interval;
        std::vector<route::Step> steps;steps.reserve(size);
        for(std::size_t j=0;j<size;++j){const auto o=PP_SIM_PACKET_HEADER_COUNT+j*PP_SIM_ROUTE_STEP_INPUT_COUNT;
            const auto shape=query_integer(input_f64[o],0,2),branch=query_integer(input_f64[o+9],0,1);route::Step step;
            if(shape==0){require(input_f64[o+7]==0,PP_SIM_INVALID_ARGUMENT,"Route disk radius is reserved zero");step.surface=geometry::PlaneDisk{vector_at(o+1),vector_at(o+4),input_f64[o+8]};}
            else if(shape==1){require(input_f64[o+4]==0&&input_f64[o+5]==0&&input_f64[o+6]==0&&input_f64[o+8]==0,PP_SIM_INVALID_ARGUMENT,"Route sphere axis/aperture are reserved zero");step.surface=geometry::FullSphere{vector_at(o+1),input_f64[o+7]};}
            else step.surface=geometry::SphericalCap{vector_at(o+1),vector_at(o+4),input_f64[o+7],input_f64[o+8]};
            step.branch=branch==0?route::Branch::reflected:route::Branch::transmitted;step.next_index=I(input_f64[o+10],input_f64[o+11]);
            step.minimum_parameter=input_f64[o+12];step.maximum_parameter=input_f64[o+13];steps.push_back(std::move(step));
        }
        std::vector<packet::Packet> packets;packets.reserve(n);
        for(std::size_t j=0;j<n;++j){const auto o=PP_SIM_PACKET_HEADER_COUNT+size*PP_SIM_ROUTE_STEP_INPUT_COUNT+j*PP_SIM_PACKET_INPUT_COUNT;
            packets.push_back({{bounds_at(o),bounds_at(o+6),input_f64[o+12],input_f64[o+13]},
                {input_f64[o+14],input_f64[o+15],input_f64[o+16],input_f64[o+17]},vector_at(o+18)});}
        const packet::Input source{packets,steps,I(input_f64[2],input_f64[3]),input_f64[4],geometry::PlaneDisk{vector_at(5),vector_at(8),input_f64[11]},input_f64[12],input_f64[13]};
        const unsigned total=unsigned(query_integer(input_f64[19],1,4000000));
        const packet::Settings settings{{{{input_f64[15],unsigned(query_integer(input_f64[16],1,256))},unsigned(query_integer(input_f64[14],1,64))},unsigned(query_integer(input_f64[20],1,256)),unsigned(query_integer(input_f64[21],1,4000000))},
            unsigned(query_integer(input_f64[17],1,1024)),unsigned(query_integer(input_f64[18],1,1024)),total};
        auto r=packet::evaluate(source,settings);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=int(r.status);a[1]=double(r.records.size());a[2]=r.evaluations;a[3]=r.accepted;a[4]=r.route_misses;a[5]=r.branch_unavailable;a[6]=r.sensor_misses;a[7]=r.unknown;
        a[8]=r.geometry_queries;a[9]=r.interface_queries;a[10]=r.sensor_queries;a[11]=r.geometry_sqrt_refinements;a[12]=r.power_sqrt_refinements;a[13]=r.sensor_sqrt_refinements;a[14]=r.refinement_limited?1:0;a[15]=r.final_stats?1:0;
        if(r.final_stats){put_interval(a,16,r.final_stats->total_source_power);put_interval(a,18,r.final_stats->accepted_source_power);put_interval(a,20,r.final_stats->detected_power);}
        a[22]=source.vacuum_wavelength_m;finite_output(a,PP_SIM_PACKET_OUTPUT_COUNT);packet_record=std::move(r);packet_wavelength=source.vacuum_wavelength_m;publish(a,PP_SIM_PACKET_OUTPUT_COUNT);
    });
}
int32_t pp_sim_polarized_packet_record(uint32_t index,uint32_t part) {
    return guarded([&]{require(part<=3&&packet_record&&index<packet_record->records.size(),PP_SIM_INVALID_ARGUMENT,"No such polarized packet/part");
        const auto& record=packet_record->records[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};uint32_t count=0;
        if(part==0){a[0]=record.ordinal;a[1]=int(record.status);a[2]=record.power.i;a[3]=record.power.q;a[4]=record.power.u;a[5]=record.power.v;a[6]=record.route?1:0;a[7]=record.sensor?1:0;a[8]=record.sensor_power?1:0;
            if(record.sensor_power)put_interval(a,9,*record.sensor_power);count=PP_SIM_PACKET_RECORD_COUNT;}
        else if(part==1){require(bool(record.route),PP_SIM_INVALID_ARGUMENT,"No packet route");a=polarized_route_packet(*record.route,packet_wavelength);count=PP_SIM_POLARIZED_ROUTE_OUTPUT_COUNT;}
        else if(part==2){require(bool(record.route),PP_SIM_INVALID_ARGUMENT,"No packet initial state");a=polarized_initial_packet(*record.route);count=PP_SIM_POLARIZED_ROUTE_INITIAL_COUNT;}
        else{require(bool(record.sensor),PP_SIM_INVALID_ARGUMENT,"No packet sensor");a=bounded_geometry_packet(*record.sensor);count=PP_SIM_BOUNDED_GEOMETRY_OUTPUT_COUNT;}
        finite_output(a,count);publish(a,count);
    });
}
int32_t pp_sim_polarized_packet_segment(uint32_t packet_index,uint32_t index,uint32_t part) {
    return guarded([&]{require(part<=1&&packet_record&&packet_index<packet_record->records.size(),PP_SIM_INVALID_ARGUMENT,"No packet segment/part");
        const auto& record=packet_record->records[packet_index];require(bool(record.route),PP_SIM_INVALID_ARGUMENT,"No packet route");const auto& r=*record.route;
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};uint32_t count=0;
        if(part==0){require(r.geometry&&index<r.geometry->segments.size(),PP_SIM_INVALID_ARGUMENT,"No packet geometry segment");a=route_segment_packet(r.geometry->segments[index]);count=PP_SIM_ROUTE_SEGMENT_COUNT;}
        else{require(index<r.segments.size(),PP_SIM_INVALID_ARGUMENT,"No packet power segment");a=polarized_power_packet(r.segments[index]);count=PP_SIM_POLARIZED_ROUTE_SEGMENT_COUNT;}
        finite_output(a,count);publish(a,count);
    });
}
int32_t pp_sim_optical_launch_ray(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_LAUNCH_INPUT_COUNT);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite launch exchange");
        const auto kind=query_integer(input_f64[0],0,1);
        const spot::Source source{kind==0?spot::SourceKind::finite_point:spot::SourceKind::parallel_beam,vector_at(1)};
        const auto ray=spot::make_launch_ray(source,vector_at(4),input_f64[7],input_f64[8]);
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};put_bounds(a,0,ray.origin);put_bounds(a,6,ray.direction);
        a[12]=ray.minimum_parameter;a[13]=ray.maximum_parameter;finite_output(a,PP_SIM_LAUNCH_OUTPUT_COUNT);publish(a,PP_SIM_LAUNCH_OUTPUT_COUNT);
    });
}
int32_t pp_sim_optical_spot(uint32_t count) {
    return guarded([&]{require(count>=PP_SIM_SPOT_HEADER_COUNT,PP_SIM_INVALID_ARGUMENT,"Missing optical spot header");
        const auto n=query_integer(input_f64[0],0,1024);const auto size=query_integer(input_f64[1],0,64);
        count_is(count,PP_SIM_SPOT_HEADER_COUNT+uint32_t(size)*PP_SIM_ROUTE_STEP_INPUT_COUNT+uint32_t(n)*PP_SIM_SPOT_SAMPLE_INPUT_COUNT);
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Nonfinite spot exchange");
        require(input_f64[20]==0,PP_SIM_INVALID_ARGUMENT,"Spot reserved slot must be zero");
        using I=pikapika::interval::Interval;
        std::vector<route::Step> steps;steps.reserve(size);
        for(std::size_t j=0;j<size;++j){const auto o=PP_SIM_SPOT_HEADER_COUNT+j*PP_SIM_ROUTE_STEP_INPUT_COUNT;
            const auto shape=query_integer(input_f64[o],0,2),branch=query_integer(input_f64[o+9],0,1);route::Step step;
            if(shape==0){require(input_f64[o+7]==0,PP_SIM_INVALID_ARGUMENT,"Route disk radius is reserved zero");step.surface=geometry::PlaneDisk{vector_at(o+1),vector_at(o+4),input_f64[o+8]};}
            else if(shape==1){require(input_f64[o+4]==0&&input_f64[o+5]==0&&input_f64[o+6]==0&&input_f64[o+8]==0,PP_SIM_INVALID_ARGUMENT,"Route sphere axis/aperture are reserved zero");step.surface=geometry::FullSphere{vector_at(o+1),input_f64[o+7]};}
            else step.surface=geometry::SphericalCap{vector_at(o+1),vector_at(o+4),input_f64[o+7],input_f64[o+8]};
            step.branch=branch==0?route::Branch::reflected:route::Branch::transmitted;step.next_index=I(input_f64[o+10],input_f64[o+11]);
            step.minimum_parameter=input_f64[o+12];step.maximum_parameter=input_f64[o+13];steps.push_back(std::move(step));
        }
        std::vector<spot::Sample> samples;samples.reserve(n);
        for(std::size_t j=0;j<n;++j){const auto o=PP_SIM_SPOT_HEADER_COUNT+size*PP_SIM_ROUTE_STEP_INPUT_COUNT+j*PP_SIM_SPOT_SAMPLE_INPUT_COUNT;
            samples.push_back({{bounds_at(o),bounds_at(o+6),input_f64[o+12],input_f64[o+13]},input_f64[o+14]});}
        const spot::Input source{samples,steps,I(input_f64[2],input_f64[3]),input_f64[4],
            geometry::PlaneDisk{vector_at(5),vector_at(8),input_f64[11]},input_f64[12],input_f64[13]};
        const spot::Settings settings{{{input_f64[15],unsigned(query_integer(input_f64[16],1,256))},unsigned(query_integer(input_f64[14],1,64))},
            unsigned(query_integer(input_f64[17],1,1024)),unsigned(query_integer(input_f64[18],1,1024)),unsigned(query_integer(input_f64[19],1,4000000))};
        auto r=spot::evaluate(source,settings);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=int(r.status);a[1]=double(r.records.size());a[2]=r.evaluations;a[3]=r.accepted;a[4]=r.route_misses;a[5]=r.branch_unavailable;
        a[6]=r.sensor_misses;a[7]=r.unknown;a[8]=r.geometry_queries;a[9]=r.interface_queries;a[10]=r.sqrt_refinements;a[11]=r.refinement_limited?1:0;
        a[12]=r.final_stats?1:0;
        if(r.final_stats){const auto& f=*r.final_stats;a[14]=f.total_weight.lower();a[15]=f.total_weight.upper();a[16]=f.accepted_weight.lower();a[17]=f.accepted_weight.upper();a[13]=f.moments?1:0;
            if(f.moments){put_bounds(a,18,f.moments->centroid);a[24]=f.moments->mean_squared_radius.lower();a[25]=f.moments->mean_squared_radius.upper();put_bounds(a,26,f.moments->hull);}}
        finite_output(a,PP_SIM_SPOT_OUTPUT_COUNT);spot_record=std::move(r);publish(a,PP_SIM_SPOT_OUTPUT_COUNT);
    });
}
int32_t pp_sim_optical_spot_sample(uint32_t index,uint32_t part) {
    return guarded([&]{require(part<=1&&spot_record&&index<spot_record->records.size(),PP_SIM_INVALID_ARGUMENT,"No such spot sample/part");
        const auto& r=spot_record->records[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=r.ordinal;a[1]=r.weight;a[2]=int(r.status);
        if(part==0){a[3]=r.route?1:0;if(r.route){const auto& t=*r.route;a[4]=int(t.status);a[5]=t.completed_steps;a[6]=t.failed_step;a[7]=t.geometry_queries;a[8]=t.interface_queries;a[9]=t.sqrt_refinements;a[10]=t.refinement_limited?1:0;a[11]=t.completion?1:0;
                if(t.completion){const auto& c=*t.completion;put_bounds(a,12,c.ray.origin);put_bounds(a,18,c.ray.direction);a[24]=c.ray.minimum_parameter;a[25]=c.ray.maximum_parameter;
                    a[26]=c.index.lower();a[27]=c.index.upper();a[28]=c.totals.distance.lower();a[29]=c.totals.distance.upper();a[30]=c.totals.optical_path_length.lower();a[31]=c.totals.optical_path_length.upper();a[32]=c.totals.throughput.lower();a[33]=c.totals.throughput.upper();}}
            finite_output(a,PP_SIM_SPOT_ROUTE_OUTPUT_COUNT);publish(a,PP_SIM_SPOT_ROUTE_OUTPUT_COUNT);
        }else{a[3]=r.sensor?1:0;if(r.sensor){const auto g=bounded_geometry_packet(*r.sensor);std::copy_n(g.begin(),PP_SIM_BOUNDED_GEOMETRY_OUTPUT_COUNT,a.begin()+5);}
            finite_output(a,PP_SIM_SPOT_SENSOR_OUTPUT_COUNT);publish(a,PP_SIM_SPOT_SENSOR_OUTPUT_COUNT);}
    });
}
int32_t pp_sim_optical_selection(uint32_t count) {
    return guarded([&]{
        require(count>=PP_SIM_SELECTION_HEADER_COUNT&&count<=PP_SIM_INPUT_F64_CAPACITY,PP_SIM_INVALID_ARGUMENT,"Missing/oversize optical selection header");
        require(std::all_of(input_f64.begin(),input_f64.begin()+count,[](double x){return std::isfinite(x);}),PP_SIM_INVALID_ARGUMENT,"Optical selection exchange requires finite values");
        const auto size=query_integer(input_f64[20],0,1024);
        count_is(count,PP_SIM_SELECTION_HEADER_COUNT+uint32_t(size)*PP_SIM_SELECTION_SURFACE_INPUT_COUNT);
        const selection::Settings settings{{input_f64[14],unsigned(query_integer(input_f64[15],1,256))},
            unsigned(query_integer(input_f64[16],1,1024)),unsigned(query_integer(input_f64[17],1,4096)),
            unsigned(query_integer(input_f64[18],1,1000000)),query_integer(input_f64[19],0,1)==1};
        std::vector<selection::SurfaceRecord> surfaces;surfaces.reserve(size);
        for(std::size_t j=0;j<size;++j){const auto o=PP_SIM_SELECTION_HEADER_COUNT+j*PP_SIM_SELECTION_SURFACE_INPUT_COUNT;
            const auto id=id_from(input_f64[o]);const auto kind=query_integer(input_f64[o+1],0,2);selection::SurfaceRecord record;record.id=id;
            if(kind==0){require(input_f64[o+8]==0,PP_SIM_INVALID_ARGUMENT,"Selection disk radius is reserved zero");record.surface=geometry::PlaneDisk{vector_at(o+2),vector_at(o+5),input_f64[o+9]};}
            else if(kind==1){require(input_f64[o+5]==0&&input_f64[o+6]==0&&input_f64[o+7]==0&&input_f64[o+9]==0,PP_SIM_INVALID_ARGUMENT,"Selection sphere axis/aperture are reserved zero");record.surface=geometry::FullSphere{vector_at(o+2),input_f64[o+8]};}
            else record.surface=geometry::SphericalCap{vector_at(o+2),vector_at(o+5),input_f64[o+8],input_f64[o+9]};
            surfaces.push_back(std::move(record));
        }
        auto r=selection::find_nearest({bounds_at(0),bounds_at(6),input_f64[12],input_f64[13]},surfaces,settings);
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=int(r.status);a[1]=r.nearest?1:0;a[3]=double(r.surfaces.size());
        a[4]=r.queries;a[5]=r.prefix_queries;a[6]=r.sqrt_refinements;a[7]=r.refinement_limited?1:0;
        if(r.nearest){a[2]=double(r.nearest->id);const auto& h=r.nearest->hit;a[8]=h.parameter.lower();a[9]=h.parameter.upper();
            a[10]=h.physical_distance.lower();a[11]=h.physical_distance.upper();put_bounds(a,12,h.position);put_bounds(a,18,h.geometric_normal);put_bounds(a,24,h.incident_normal);a[30]=h.front_face?1:0;}
        finite_output(a,PP_SIM_SELECTION_OUTPUT_COUNT);selection_record=std::move(r);publish(a,PP_SIM_SELECTION_OUTPUT_COUNT);
    });
}
int32_t pp_sim_optical_selection_surface(uint32_t index,uint32_t prefix) {
    return guarded([&]{require(prefix<=1&&selection_record&&index<selection_record->surfaces.size(),PP_SIM_INVALID_ARGUMENT,"No such optical selection surface/part");
        const auto& s=selection_record->surfaces[index];const auto& part=prefix?s.prefix:s.geometry;
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};a[0]=double(s.id);a[1]=s.geometry?1:0;a[2]=s.prefix?1:0;a[3]=s.excluded_by_prefix?1:0;a[4]=part?1:0;
        if(part){const auto g=bounded_geometry_packet(*part);std::copy_n(g.begin(),PP_SIM_BOUNDED_GEOMETRY_OUTPUT_COUNT,a.begin()+5);}
        finite_output(a,PP_SIM_SELECTION_SURFACE_OUTPUT_COUNT);publish(a,PP_SIM_SELECTION_SURFACE_OUTPUT_COUNT);
    });
}
int32_t pp_sim_polarized_interface(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_POLARIZATION_INPUT_COUNT);
        publish_polarization(polarization::dielectric_split({vector_at(0),vector_at(3),input_f64[6],input_f64[7],input_f64[8]},
            vector_at(9),{input_f64[12],input_f64[13],input_f64[14],input_f64[15]}));});
}
int32_t pp_sim_dispersion(uint32_t count) {
    return guarded([&]{count_is(count,PP_SIM_DISPERSION_INPUT_COUNT);
        const auto kind=query_integer(input_f64[0],0,1),terms=query_integer(input_f64[10],0,8);
        const dispersion::Band wavelength{input_f64[1],input_f64[2]},valid_band{input_f64[3],input_f64[4]};
        const dispersion::Settings settings{input_f64[5],unsigned(query_integer(input_f64[6],1,256))};
        dispersion::Result r;
        if(kind==0){
            require(terms==0&&std::all_of(input_f64.begin()+11,input_f64.begin()+27,[](double x){return x==0;}),
                PP_SIM_INVALID_ARGUMENT,"Cauchy oscillator slots are reserved zero");
            r=dispersion::evaluate(dispersion::Cauchy{input_f64[7],input_f64[8],input_f64[9],valid_band},wavelength,settings);
        }else{
            require(input_f64[7]==0&&input_f64[8]==0&&input_f64[9]==0,PP_SIM_INVALID_ARGUMENT,"Sellmeier Cauchy slots are reserved zero");
            dispersion::Sellmeier model;model.count=unsigned(terms);model.valid_band=valid_band;
            for(unsigned j=0;j<8;++j){
                if(j<terms)model.terms[j]={input_f64[11+2*j],input_f64[12+2*j]};
                else require(input_f64[11+2*j]==0&&input_f64[12+2*j]==0,PP_SIM_INVALID_ARGUMENT,"Unused Sellmeier terms are reserved zero");
            }
            r=dispersion::evaluate(model,wavelength,settings);
        }
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};
        values[0]=double(r.status);values[1]=double(r.reason);values[2]=r.values?1:0;values[3]=r.sqrt_refinements;
        values[4]=r.squared_phase?1:0;if(r.squared_phase){values[5]=r.squared_phase->lower();values[6]=r.squared_phase->upper();}
        if(r.values){const auto& v=*r.values;values[7]=v.phase.lower();values[8]=v.phase.upper();values[9]=v.derivative.lower();values[10]=v.derivative.upper();
            values[11]=v.group.lower();values[12]=v.group.upper();values[13]=v.within_interface_domain?1:0;}
        // Nonfinite diagnostic enclosures may arise on numerical range failure;
        // success values are finite by the model contract. No NaNs are exported.
        require(std::none_of(values.begin(),values.begin()+PP_SIM_DISPERSION_OUTPUT_COUNT,[](double x){return std::isnan(x);}),PP_SIM_CORE_REJECTED,"NaN dispersion packet");
        publish(values,PP_SIM_DISPERSION_OUTPUT_COUNT);
    });
}
pp_sim_handle pp_sim_world_create(void) {
    pp_sim_handle handle=0;guarded([&]{const auto i=free_slot(worlds);auto object=std::make_unique<WorldState>();worlds[i].object=std::move(object);handle=encode(worlds[i],i,0);output_count=0;});return handle;
}
int32_t pp_sim_world_destroy(pp_sim_handle world){return guarded([&]{retire(lookup(worlds,world,0));output_count=0;});}
int32_t pp_sim_world_reset(pp_sim_handle world){return guarded([&]{auto& slot=lookup(worlds,world,0);auto candidate=std::make_unique<WorldState>();slot.object.swap(candidate);output_count=0;});}
int32_t pp_sim_world_set_gravity(pp_sim_handle world,uint32_t count) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;count_is(count,3);const auto gravity=vector_at(0);
        require(finite(gravity)&&std::abs(gravity.x)<=1e9&&std::abs(gravity.y)<=1e9&&std::abs(gravity.z)<=1e9,PP_SIM_INVALID_ARGUMENT,"invalid world gravity");state.world.gravity=gravity;output_count=0;});
}
int32_t pp_sim_world_info(pp_sim_handle world) {
    return guarded([&]{const auto& state=*lookup(worlds,world,0).object;std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};
        put_vector(values,0,state.world.gravity);values[3]=double(state.world.bodies().size());values[4]=double(state.world.planes().size());values[5]=state.time;values[6]=double(state.ticks);publish(values,PP_SIM_WORLD_INFO_COUNT);});
}
int32_t pp_sim_world_support(pp_sim_handle world,uint32_t count) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;count_is(count,PP_SIM_SUPPORT_SETTINGS_COUNT);
        support::Settings settings;settings.gap_tolerance=input_f64[0];settings.velocity_interval_tolerance=input_f64[1];
        settings.acceleration_tolerance=input_f64[2];settings.complementarity_tolerance=input_f64[3];settings.projected_force_tolerance=input_f64[4];
        settings.minimum_scaled_pivot=input_f64[5];settings.maximum_force=input_f64[6];
        settings.max_iterations=unsigned(query_integer(input_f64[7],1,100000));settings.max_contacts=query_integer(input_f64[8],1,256);
        settings.max_pair_queries=query_integer(input_f64[9],1,1000000);
        auto report=support::solve(state.world,settings);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=report.success?1:0;a[1]=int(report.failure);a[2]=double(report.pair_queries);a[3]=double(report.separated_pairs);
        a[4]=double(report.resting_constraints);a[5]=double(report.separating_constraints);a[6]=report.iterations;
        a[7]=report.maximum_geometry_offset;a[8]=report.maximum_velocity_interval_width;a[9]=report.minimum_scaled_pivot;
        const auto& e=report.residuals;a[10]=e.negative_force;a[11]=e.negative_acceleration;a[12]=e.complementarity;a[13]=e.projected_force;a[14]=e.maximum_acceleration_interval_width;
        a[15]=double(report.constraints.size());a[16]=double(report.bodies.size());a[17]=double(report.first_id);a[18]=double(report.second_id);a[19]=state.time;a[20]=double(state.ticks);
        finite_output(a,PP_SIM_SUPPORT_OUTPUT_COUNT);state.last_support=std::move(report);publish(a,PP_SIM_SUPPORT_OUTPUT_COUNT);
    });
}
int32_t pp_sim_world_support_constraint(pp_sim_handle world,uint32_t index) {
    return guarded([&]{const auto& state=*lookup(worlds,world,0).object;
        require(state.last_support&&index<state.last_support->constraints.size(),PP_SIM_INVALID_ARGUMENT,"No such constraint in last support query");
        const auto& c=state.last_support->constraints[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=double(c.first_id);a[1]=double(c.second_id);a[2]=int(c.phase);a[3]=c.guarded_geometry?1:0;
        put_vector(a,4,c.normal);put_vector(a,7,c.normal_lower);put_vector(a,10,c.normal_upper);
        for(unsigned j=0;j<2;++j){a[13+j]=c.gap[j];a[15+j]=c.normal_velocity[j];a[17+j]=c.curvature[j];a[22+j]=c.acceleration_bounds[j];}
        a[19]=c.free_normal_acceleration;a[20]=c.lambda;a[21]=c.normal_acceleration;
        finite_output(a,PP_SIM_SUPPORT_CONSTRAINT_COUNT);publish(a,PP_SIM_SUPPORT_CONSTRAINT_COUNT);
    });
}
int32_t pp_sim_world_support_body(pp_sim_handle world,uint32_t index) {
    return guarded([&]{const auto& state=*lookup(worlds,world,0).object;
        require(state.last_support&&index<state.last_support->bodies.size(),PP_SIM_INVALID_ARGUMENT,"No such body in last support query");
        const auto& b=state.last_support->bodies[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=double(b.id);put_vector(a,1,b.force);put_vector(a,4,b.normal_torque);put_vector(a,7,b.force_lower);put_vector(a,10,b.force_upper);
        put_vector(a,13,b.acceleration);put_vector(a,16,b.acceleration_lower);put_vector(a,19,b.acceleration_upper);
        finite_output(a,PP_SIM_SUPPORT_BODY_COUNT);publish(a,PP_SIM_SUPPORT_BODY_COUNT);
    });
}
int32_t pp_sim_world_body_add(pp_sim_handle world,uint32_t count) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;const auto body=body_input(count);
        require(state.world.bodies().size()<PP_SIM_MAX_BODIES,PP_SIM_BUDGET_EXCEEDED,"world body budget exceeded");auto candidate=state.world;candidate.add_body(body);state.world=std::move(candidate);output_count=0;});
}
int32_t pp_sim_world_body_set(pp_sim_handle world,uint32_t count) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;const auto body=body_input(count);auto* target=state.world.find_body(body.id);
        require(target!=nullptr,PP_SIM_INVALID_ARGUMENT,"cannot set unknown body ID");*target=body;output_count=0;});
}
int32_t pp_sim_world_body_get(pp_sim_handle world,double id) {
    return guarded([&]{const auto& state=*lookup(worlds,world,0).object;const auto* body=state.world.find_body(id_from(id));
        require(body!=nullptr,PP_SIM_INVALID_ARGUMENT,"unknown body ID");const auto& b=*body;std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> v{};
        v[0]=double(b.id);v[1]=b.is_static?1:0;v[2]=b.mass;v[3]=b.radius;put_vector(v,4,b.inertia_diagonal);put_vector(v,7,b.position);
        v[10]=b.orientation.x;v[11]=b.orientation.y;v[12]=b.orientation.z;v[13]=b.orientation.w;put_vector(v,14,b.velocity);
        put_vector(v,17,b.angular_momentum);put_vector(v,20,b.force);put_vector(v,23,b.torque);v[26]=b.material.restitution;v[27]=b.material.friction;
        put_vector(v,28,b.angular_velocity());v[31]=b.kinetic_energy();v[32]=state.time;v[33]=double(state.ticks);publish(v,PP_SIM_BODY_OUTPUT_COUNT);});
}
int32_t pp_sim_world_plane_add(pp_sim_handle world,uint32_t count) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;count_is(count,PP_SIM_PLANE_INPUT_COUNT);
        require(input_f64[7]==0,PP_SIM_INVALID_ARGUMENT,"plane reserved value must be zero");
        require(state.world.planes().size()<PP_SIM_MAX_PLANES,PP_SIM_BUDGET_EXCEEDED,"world plane budget exceeded");
        dyn::Plane plane{id_from(input_f64[0]),vector_at(1),input_f64[4],{input_f64[5],input_f64[6]}};
        auto candidate=state.world;candidate.add_plane(plane);state.world=std::move(candidate);output_count=0;});
}
int32_t pp_sim_world_step(pp_sim_handle world,double dt,uint32_t steps) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;step_valid(state,dt,steps);auto candidate=state;dyn::StepStats stats;
        for(uint32_t i=0;i<steps;++i){accumulate(stats,candidate.world.step(dt,settings()));candidate.time+=dt;++candidate.ticks;}
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};put_step(values,stats,candidate);state=std::move(candidate);publish(values,PP_SIM_STEP_OUTPUT_COUNT);});
}
int32_t pp_sim_world_step_continuous(pp_sim_handle world,double dt,uint32_t count) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;count_is(count,PP_SIM_CCD_SETTINGS_COUNT);
        step_valid(state,dt,1);const auto settings=ccd_settings();auto candidate=state;
        auto report=candidate.world.step_continuous(dt,settings);
        if(report.success){candidate.time+=dt;++candidate.ticks;}
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=report.success?1:0;a[1]=int(report.failure);a[2]=report.advanced_dt;a[3]=report.candidate_time;
        a[4]=double(report.first_id);a[5]=double(report.second_id);a[6]=double(report.pair_queries);a[7]=double(report.root_evaluations);
        a[8]=double(report.free_segments);a[9]=report.maximum_propagation_error;a[10]=report.accumulated_position_roundoff;a[11]=report.time_roundoff;
        a[12]=double(report.impact_stats.contacts);a[13]=report.impact_stats.velocity_iterations;a[14]=report.impact_stats.max_penetration;
        a[15]=report.impact_stats.normal_impulse_sum;a[16]=report.impact_stats.friction_impulse_sum;a[17]=report.impact_stats.max_closing_residual;
        a[18]=double(report.events.size());a[19]=candidate.time;a[20]=double(candidate.ticks);
        finite_output(a,PP_SIM_CCD_OUTPUT_COUNT);
        if(report.success){candidate.last_ccd=std::move(report);state=std::move(candidate);}
        else state.last_ccd=std::move(report);
        publish(a,PP_SIM_CCD_OUTPUT_COUNT);});
}
int32_t pp_sim_world_ccd_event(pp_sim_handle world,uint32_t index) {
    return guarded([&]{const auto& state=*lookup(worlds,world,0).object;
        require(state.last_ccd&&index<state.last_ccd->events.size(),PP_SIM_INVALID_ARGUMENT,"No such event in last continuous attempt");
        const auto& e=state.last_ccd->events[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=e.responded_at;a[1]=e.entry_lower;a[2]=e.entry_upper;a[3]=e.maximum_gap;a[4]=e.propagation_error;
        a[5]=double(e.first_id);a[6]=double(e.second_id);a[7]=double(e.contacts);
        finite_output(a,PP_SIM_CCD_EVENT_COUNT);publish(a,PP_SIM_CCD_EVENT_COUNT);});
}
int32_t pp_sim_world_step_supported(pp_sim_handle world,double dt,uint32_t count){
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;count_is(count,PP_SIM_SUPPORTED_SETTINGS_COUNT);step_valid(state,dt,1);
        const auto settings=supported_settings();auto candidate=state;auto report=supported::step(candidate.world,dt,settings);
        if(report.success){candidate.time+=dt;++candidate.ticks;}
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=report.success?1:0;a[1]=int(report.failure);a[2]=report.advanced_dt;a[3]=report.candidate_time;
        a[4]=report.attempts;a[5]=report.accepted_segments;a[6]=report.rejected_attempts;a[7]=report.constraint_solves;a[8]=double(report.pair_queries);a[9]=double(report.guard_evaluations);a[10]=double(report.certified_intervals);
        a[11]=report.minimum_accepted_substep;a[12]=report.maximum_gap_residual;a[13]=report.maximum_velocity_residual;a[14]=report.maximum_position_error_estimate;a[15]=report.maximum_velocity_error_estimate;a[16]=report.maximum_orientation_error_estimate;
        a[17]=report.support_impulse_sum;a[18]=report.impact_impulse_sum;a[19]=report.maximum_near_contact_gap;a[20]=report.initial_mechanical_energy;a[21]=report.final_mechanical_energy;a[22]=report.held_force_work;a[23]=report.mechanical_energy_change;a[24]=report.time_roundoff;
        a[25]=int(report.last_constraint_failure);a[26]=int(report.last_guard_failure);a[27]=double(report.events.size());a[28]=double(report.first_id);a[29]=double(report.second_id);a[30]=candidate.time;a[31]=double(candidate.ticks);
        finite_output(a,PP_SIM_SUPPORTED_OUTPUT_COUNT);
        if(report.success){candidate.last_supported=std::move(report);state=std::move(candidate);}else state.last_supported=std::move(report);
        publish(a,PP_SIM_SUPPORTED_OUTPUT_COUNT);
    });
}
int32_t pp_sim_world_supported_event(pp_sim_handle world,uint32_t index){
    return guarded([&]{const auto& state=*lookup(worlds,world,0).object;
        require(state.last_supported&&index<state.last_supported->events.size(),PP_SIM_INVALID_ARGUMENT,"No such event in last supported attempt");
        const auto& e=state.last_supported->events[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=int(e.kind);a[1]=e.at;a[2]=double(e.first_id);a[3]=double(e.second_id);put_vector(a,4,e.normal);a[7]=double(e.contacts);a[8]=e.impulse_sum;a[9]=e.kinetic_before;a[10]=e.kinetic_after;a[11]=e.maximum_gap;
        finite_output(a,PP_SIM_SUPPORTED_EVENT_COUNT);publish(a,PP_SIM_SUPPORTED_EVENT_COUNT);
    });
}
pp_sim_handle pp_sim_hull_create(uint32_t vertices,uint32_t triangles) {
    pp_sim_handle handle=0;guarded([&]{const auto i=free_slot(hulls);auto candidate=hull_input(vertices,triangles);
        hulls[i].object=std::move(candidate);total_vertices+=vertices;total_triangles+=triangles;handle=encode(hulls[i],i,hull_tag);output_count=0;});return handle;
}
int32_t pp_sim_hull_replace(pp_sim_handle hull,uint32_t vertices,uint32_t triangles) {
    return guarded([&]{auto& slot=lookup(hulls,hull,hull_tag);const auto old_vertices=slot.object->mesh().positions.size(),old_triangles=slot.object->mesh().triangles.size();
        auto candidate=hull_input(vertices,triangles,old_vertices,old_triangles);slot.object.swap(candidate);total_vertices=total_vertices-old_vertices+vertices;total_triangles=total_triangles-old_triangles+triangles;output_count=0;});
}
int32_t pp_sim_hull_destroy(pp_sim_handle hull) {
    return guarded([&]{auto& slot=lookup(hulls,hull,hull_tag);const auto vertices=slot.object->mesh().positions.size(),triangles=slot.object->mesh().triangles.size();retire(slot);total_vertices-=vertices;total_triangles-=triangles;output_count=0;});
}
int32_t pp_sim_hydro_query(pp_sim_handle hull,uint32_t count) {
    return guarded([&]{const auto& source=*lookup(hulls,hull,hull_tag).object;count_is(count,PP_SIM_HYDRO_INPUT_COUNT);
        const hydro::Fluid fluid{input_f64[0],input_f64[1],input_f64[2]};hydro::Pose pose;pose.transform.position=vector_at(3);
        pose.transform.rotation={input_f64[6],input_f64[7],input_f64[8],input_f64[9]};pose.transform.scale=vector_at(10);pose.center_of_mass=vector_at(13);
        const auto result=hydro::forces(source,fluid,pose);std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};put_hydro(values,result);publish(values,PP_SIM_HYDRO_OUTPUT_COUNT);});
}
int32_t pp_sim_world_buoyancy_step(pp_sim_handle world,pp_sim_handle hull,double id,double dt,uint32_t steps,uint32_t count) {
    return guarded([&]{auto& state=*lookup(worlds,world,0).object;const auto& source=*lookup(hulls,hull,hull_tag).object;
        count_is(count,PP_SIM_BUOYANCY_INPUT_COUNT);step_valid(state,dt,steps);const auto body_id=id_from(id);
        const hydro::Fluid fluid{input_f64[0],input_f64[1],input_f64[2]};const auto origin=vector_at(3),scale=vector_at(6);
        auto candidate=state;dyn::StepStats stats;hydro::Result load;
        for(uint32_t i=0;i<steps;++i){const auto one=hydro::step_isolated_buoyant_body(candidate.world,body_id,source,dt,fluid,origin,scale,settings());
            load=one.midpoint_load;accumulate(stats,one.dynamics);candidate.time+=dt;++candidate.ticks;}
        std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> values{};put_hydro(values,load);put_step(values,stats,candidate);state=std::move(candidate);publish(values,PP_SIM_STEP_OUTPUT_COUNT);});
}
}
