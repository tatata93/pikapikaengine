#include "pikapika/dynamics.hpp"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>

using namespace pikapika;
using namespace pikapika::dynamics;
namespace {
std::string utc_timestamp() {
    const auto raw=std::chrono::system_clock::to_time_t(std::chrono::system_clock::now());std::tm utc{};
#ifdef _WIN32
    gmtime_s(&utc,&raw);
#else
    gmtime_r(&raw,&utc);
#endif
    std::ostringstream out;out<<std::put_time(&utc,"%Y-%m-%dT%H:%M:%SZ");return out.str();
}
RigidBody rotation(double dt) {
    World world;world.gravity={};auto body=make_sphere(1,1,1);body.inertia_diagonal={2,3,4};body.angular_momentum={1.1,2.2,3.3};world.add_body(body);
    for(unsigned i=0;i<unsigned(std::lround(4/dt));++i)world.step(dt);return *world.find_body(1);
}
double error(Quaternion a,Quaternion b) {
    double sum=0;for(const auto axis:{Vec3{1,0,0},Vec3{0,1,0},Vec3{0,0,1}}) {const auto delta=a.rotate(axis)-b.rotate(axis);sum+=delta.dot(delta);}return std::sqrt(sum);
}
double energy(const World& world) {double sum=0;for(const auto& body:world.bodies())sum+=body.kinetic_energy();return sum;}
}
int main(int argc,char** argv) {
    try {
        unsigned steps=1200;std::string csv_path;
        for(int i=1;i<argc;++i) {
            const std::string argument=argv[i];
            if(argument=="--steps"&&i+1<argc) {
                const std::string token=argv[++i];std::size_t used{};const auto value=std::stoul(token,&used);
                if(used!=token.size()||value<1||value>60000)throw std::runtime_error("steps must be 1..60000");steps=unsigned(value);
            } else if(argument=="--csv"&&i+1<argc)csv_path=argv[++i];
            else if(argument=="--help") {
                std::cout<<"pikapika-dynamics [--steps 1..60000] [--csv path]\n"
                    <<"Native six-DOF sphere/plane subset, fixed 1/120s, 64 bodies, 16 contact iterations.\n"
                    <<"CPU physics-step timing only; no rendering, vehicle, aircraft, rail, joints or CCD claim.\n";return 0;
            } else throw std::runtime_error("usage: pikapika-dynamics [--steps count] [--csv path]");
        }
        std::ofstream csv;if(!csv_path.empty()){csv.open(csv_path);if(!csv)throw std::runtime_error("cannot create raw timing CSV");csv<<"step,cpu_physics_ms,contacts,max_penetration_m,kinetic_energy_J\n";}
        World world;world.add_plane({1000});SolverSettings settings;
        for(unsigned i=0;i<64;++i) {
            auto body=make_sphere(i+1,0.45,1+0.25*(i%3),{double(i%8)*1.05,1+0.08*((i*7)%9),double(i/8)*1.05});
            body.velocity={0.1*double(int(i%5)-2),0,0.08*double(int(i%7)-3)};
            body.inertia_diagonal={0.1,0.14,0.18};body.angular_momentum={0,0.01,0};world.add_body(body);
        }
        const double initial_energy=energy(world);std::vector<double> timings;timings.reserve(steps);
        std::size_t contacts=0,max_contacts=0;double max_penetration=0,max_residual=0;
        for(unsigned i=0;i<steps;++i) {
            const auto start=std::chrono::steady_clock::now();const auto stats=world.step(1./120,settings);
            const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
            timings.push_back(ms);contacts+=stats.contacts;max_contacts=std::max(max_contacts,stats.contacts);
            max_penetration=std::max(max_penetration,stats.max_penetration);max_residual=std::max(max_residual,stats.max_closing_residual);
            if(csv)csv<<i<<','<<std::setprecision(12)<<ms<<','<<stats.contacts<<','<<stats.max_penetration<<','<<energy(world)<<'\n';
        }
        if(csv.is_open()) {csv.flush();if(!csv)throw std::runtime_error("raw timing CSV write failed");}
        auto sorted=timings;std::sort(sorted.begin(),sorted.end());
        unsigned overruns=0,consecutive=0,max_consecutive=0;
        for(double ms:timings) {if(ms>1000./120){++overruns;++consecutive;max_consecutive=std::max(max_consecutive,consecutive);}else consecutive=0;}
        const auto percentile=[&](double p){return sorted[std::size_t(std::ceil(p*sorted.size()))-1];};
        const auto reference=rotation(1./15360),coarse=rotation(1./30),fine=rotation(1./60),finer=rotation(1./120);
        const double ec=error(coarse.orientation,reference.orientation),ef=error(fine.orientation,reference.orientation),eff=error(finer.orientation,reference.orientation);
        const auto delta=reference.angular_momentum-Vec3{1.1,2.2,3.3};
        std::cout<<std::setprecision(12)<<"{\"benchmark\":\"native-six-dof-sphere-plane\",\"timestamp_utc\":\""<<utc_timestamp()
            <<"\",\"code_revision_base\":\""<<PP_DYN_REVISION_BASE<<"\",\"worktree_dirty_at_configure\":"<<(PP_DYN_DIRTY?"true":"false")
            <<",\"dynamics_source_sha256\":\""<<PP_DYN_SOURCE_HASH<<"\",\"dynamics_header_sha256\":\""<<PP_DYN_HEADER_HASH
            <<"\",\"benchmark_source_sha256\":\""<<PP_DYN_BENCH_HASH<<"\",\"core_source_sha256\":\""<<PP_DYN_CORE_HASH
            <<"\",\"core_header_sha256\":\""<<PP_DYN_CORE_HEADER_HASH<<"\",\"compiler_id\":\""<<PP_DYN_COMPILER_ID
            <<"\",\"compiler_version\":\""<<PP_DYN_COMPILER_VERSION<<"\",\"build_config\":\""<<PP_DYN_BUILD_CONFIG<<"\",\"dt_s\":"<<1./120
            <<",\"steps\":"<<steps<<",\"bodies\":64,\"planes\":1,\"sphere_radius_m\":0.45,\"sphere_mass_range_kg\":[1,1.5],\"body_principal_inertia_kg_m2\":[0.1,0.14,0.18]"
            <<",\"gravity_m_s2\":["<<world.gravity.x<<','<<world.gravity.y<<','<<world.gravity.z<<']'
            <<",\"velocity_iterations\":"<<settings.velocity_iterations<<",\"contact_budget\":"<<settings.max_contacts
            <<",\"contact_margin_m\":"<<settings.contact_margin<<",\"penetration_slop_m\":"<<settings.penetration_slop
            <<",\"position_correction\":"<<settings.position_correction<<",\"max_position_correction_m\":"<<settings.max_position_correction
            <<",\"restitution_threshold_m_s\":"<<settings.restitution_velocity_threshold<<",\"max_angular_increment_rad\":"<<settings.max_angular_increment
            <<",\"material_friction\":0.6,\"material_restitution\":0,\"friction_disk_bisection_iterations\":48,\"contacts_total\":"<<contacts
            <<",\"max_contacts\":"<<max_contacts<<",\"max_penetration_m\":"<<max_penetration<<",\"max_closing_residual_m_s\":"<<max_residual
            <<",\"kinetic_energy_initial_J\":"<<initial_energy<<",\"kinetic_energy_final_J\":"<<energy(world)
            <<",\"cpu_physics_ms\":{\"p50\":"<<percentile(.5)<<",\"p95\":"<<percentile(.95)<<",\"p99\":"<<percentile(.99)<<",\"max\":"<<sorted.back()<<'}'
            <<",\"physics_tick_budget_ms\":"<<1000./120<<",\"cpu_tick_budget_overruns\":"<<overruns<<",\"max_consecutive_cpu_overruns\":"<<max_consecutive
            <<",\"rotation_basis_error_dt_1_30\":"<<ec<<",\"rotation_basis_error_dt_1_60\":"<<ef<<",\"rotation_basis_error_dt_1_120\":"<<eff
            <<",\"rotation_error_ratio_coarse_fine\":"<<ec/ef<<",\"world_L_error\":"<<delta.length()
            <<",\"presentation_60fps_verified\":false,\"assumptions\":\"discrete sphere proxies;static infinite planes;no CCD,joints,vehicle,aircraft or rail model;rotation reference is numerical self-convergence\"}\n";
        return 0;
    } catch(const std::exception& error) {std::cerr<<"pikapika-dynamics: "<<error.what()<<'\n';return 1;}
}
