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
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <exception>
#include <memory>
#include <new>
#include <optional>
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
struct Failure {int32_t code;const char* message;};
void require(bool value,int32_t code,const char* message){if(!value)throw Failure{code,message};}
std::array<double,PP_SIM_INPUT_F64_CAPACITY> input_f64{};
std::array<uint32_t,PP_SIM_INPUT_U32_CAPACITY> input_u32{};
std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> output{};
uint32_t output_count{};
std::optional<route::Result> route_record;
int32_t status{};
std::array<char,PP_SIM_ERROR_CAPACITY> error{};
constexpr uint32_t hull_tag=0x80000000U,max_generation=0x7fffffU;
struct WorldState {dyn::World world;double time{};uint64_t ticks{};std::optional<dyn::CcdReport> last_ccd;std::optional<support::Result> last_support;};
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
optical_bounds::Bounds3 bounds_at(std::size_t offset) {
    using I=pikapika::interval::Interval;
    return {I(input_f64[offset],input_f64[offset+1]),I(input_f64[offset+2],input_f64[offset+3]),I(input_f64[offset+4],input_f64[offset+5])};
}
void publish_bounded_geometry(const optical_bounds::Result& r) {
    std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
    a[0]=int(r.status);a[1]=int(r.reason);a[2]=r.nearest?1:0;a[3]=r.root_count;
    a[4]=r.considered_count;a[5]=r.sqrt_refinements;a[6]=r.refinement_limited?1:0;
    a[7]=r.discriminant?1:0;if(r.discriminant){a[8]=r.discriminant->lower();a[9]=r.discriminant->upper();}
    for(std::size_t i=0;i<2;++i){const auto& c=r.candidates[i];const auto o=10+i*4;
        a[o]=c.parameter.lower();a[o+1]=c.parameter.upper();a[o+2]=int(c.state);a[o+3]=int(c.reason);}
    if(r.nearest){const auto& h=*r.nearest;a[18]=h.parameter.lower();a[19]=h.parameter.upper();
        a[20]=h.physical_distance.lower();a[21]=h.physical_distance.upper();put_bounds(a,22,h.position);
        put_bounds(a,28,h.geometric_normal);put_bounds(a,34,h.incident_normal);a[40]=h.front_face?1:0;}
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
int32_t pp_sim_reset(void){return guarded([]{for(auto& slot:worlds)if(slot.object)retire(slot);for(auto& slot:hulls)if(slot.object)retire(slot);route_record.reset();total_vertices=0;total_triangles=0;output_count=0;});}
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
        const auto& s=route_record->segments[index];std::array<double,PP_SIM_OUTPUT_F64_CAPACITY> a{};
        a[0]=int(s.branch);a[1]=s.geometry.nearest?1:0;a[2]=int(s.geometry.status);a[3]=int(s.geometry.reason);a[4]=s.interface?1:0;
        if(s.interface){a[5]=int(s.interface->kind);a[6]=int(s.interface->reason);}a[7]=s.outgoing?1:0;a[8]=s.factor?1:0;a[9]=s.accumulated?1:0;
        put_bounds(a,10,s.incoming.origin);put_bounds(a,16,s.incoming.direction);a[22]=s.incoming.minimum_parameter;a[23]=s.incoming.maximum_parameter;
        a[24]=s.incident_index.lower();a[25]=s.incident_index.upper();a[26]=s.other_index.lower();a[27]=s.other_index.upper();
        if(s.geometry.nearest){const auto& h=*s.geometry.nearest;put_bounds(a,28,h.position);a[34]=h.parameter.lower();a[35]=h.parameter.upper();
            a[36]=h.physical_distance.lower();a[37]=h.physical_distance.upper();put_bounds(a,38,h.incident_normal);a[62]=h.front_face?1:0;}
        if(s.outgoing)put_bounds(a,44,s.outgoing->direction);if(s.factor){a[50]=s.factor->lower();a[51]=s.factor->upper();}
        if(s.accumulated){const auto& t=*s.accumulated;a[52]=t.distance.lower();a[53]=t.distance.upper();a[54]=t.optical_path_length.lower();a[55]=t.optical_path_length.upper();a[56]=t.throughput.lower();a[57]=t.throughput.upper();}
        a[58]=s.geometry.sqrt_refinements;a[59]=s.geometry.refinement_limited?1:0;if(s.interface){a[58]+=s.interface->sqrt_refinements;a[59]=a[59]||s.interface->refinement_limited;}
        a[60]=s.geometry.considered_count;a[61]=s.geometry.root_count;finite_output(a,PP_SIM_ROUTE_SEGMENT_COUNT);publish(a,PP_SIM_ROUTE_SEGMENT_COUNT);
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
