#include "pikapika/world_static_mesh_session_api.h"
/* Compiled as C, then linked with the real C++ API and dependencies. */
uint32_t pp_ws_c_header_smoke(void) {
    pp_ws_context* c=pp_ws_context_create(1,0);
    pp_ws_result stage,made,read,reset;
    double* f;uint32_t* w;
    if(!c||pp_ws_api_version()!=1) {return 1;}
    f=pp_ws_input_f64(c);w=pp_ws_input_u32(c);
    f[5]=1.0/120.0;w[2]=4;
    stage=pp_ws_stage(c,6,5);
    made=pp_ws_create(c,stage.revision[0],stage.revision[1]);
    read=pp_ws_read(c,made.token[0],made.token[1],made.token[2]);
    reset=pp_ws_reset(c,stage.revision[0],stage.revision[1],made.token[0],made.token[1],made.token[2]);
    if(stage.host||made.host||read.host||reset.host!=PP_WS_OWNER_REJECTED||reset.owner!=PP_WS_OWNER_RETIRED||
       pp_ws_snapshot_info_get(c).available!=1||pp_ws_snapshot_info_get(c).float_count!=6||pp_ws_snapshot_f64(c)[5]!=f[5]) {
        pp_ws_context_delete(c);return 2;
    }
    if(pp_ws_destroy(c,made.token[0],made.token[1],made.token[2]).host||pp_ws_snapshot_info_get(c).available!=1) {
        pp_ws_context_delete(c);return 3;
    }
    pp_ws_context_delete(c);return 0;
}
