#pragma once
// No STL or OS types: this scalar subset is callable from native and WASM hosts.
#ifdef __cplusplus
extern "C" {
#endif
// Inputs are caller-validated finite SI values. A negative result means no hit.
double pp_sweep_fraction(double mx,double my,double mz,double dx,double dy,double dz,double combined_radius);
double pp_direct_delay(double distance_m,double sound_speed_m_per_s);
double pp_direct_pressure_gain(double distance_m,double reference_m);
double pp_integrate_velocity(double position_m,double velocity_m_per_s,double dt_s);
#ifdef __cplusplus
}
#endif
