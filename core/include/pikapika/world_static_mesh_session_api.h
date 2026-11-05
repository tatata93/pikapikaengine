#ifndef PIKAPIKA_WORLD_STATIC_MESH_SESSION_API_H
#define PIKAPIKA_WORLD_STATIC_MESH_SESSION_API_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#define PP_WS_NOEXCEPT noexcept
#else
#define PP_WS_NOEXCEPT
#endif
/* Native plain-source lifecycle API, independent of pp_sim_handle. No pump,
 * mesh, arbitrary guard, JS or WASM capability. A context and all buffer access
 * require exclusive single-thread ownership and valid caller-owned pointers.
 * Context pointers cannot be validated after deletion; delete exactly once. */
typedef struct pp_ws_context pp_ws_context;
enum pp_ws_limits {PP_WS_API_VERSION=1,PP_WS_INPUT_F64_CAPACITY=512,
    PP_WS_INPUT_U32_CAPACITY=256,PP_WS_MAX_BODIES=8,PP_WS_MAX_PLANES=16};
enum pp_ws_host_status {PP_WS_OK=0,PP_WS_NULL_CONTEXT=1,PP_WS_BUSY=2,
    PP_WS_INPUT_COUNT=3,PP_WS_SOURCE_REJECTED=4,PP_WS_SOURCE_REVISION=5,
    PP_WS_NO_SOURCE=6,PP_WS_TOKEN_REJECTED=7,PP_WS_OWNER_REJECTED=8,
    PP_WS_REVISION_EXHAUSTED=9};
enum pp_ws_owner_status {PP_WS_OWNER_OK=0,PP_WS_OWNER_BUSY=1,PP_WS_OWNER_SLOT_RANGE=2,
    PP_WS_OWNER_NOT_ALIVE=3,PP_WS_OWNER_STALE=4,PP_WS_OWNER_FOREIGN=5,
    PP_WS_OWNER_FULL=6,PP_WS_OWNER_RETIRED=7,PP_WS_OWNER_SOURCE_COUNTS=8,
    PP_WS_OWNER_SETTINGS=9,PP_WS_OWNER_ALLOCATION=10,PP_WS_OWNER_EXCEPTION=11};
enum pp_ws_source_status {PP_WS_SOURCE_OK=0,PP_WS_SOURCE_WORD_COUNT=1,
    PP_WS_SOURCE_BODY_COUNT=2,PP_WS_SOURCE_PLANE_COUNT=3,PP_WS_SOURCE_FLOAT_COUNT=4,
    PP_WS_SOURCE_NONFINITE=5,PP_WS_SOURCE_STATIC=6,PP_WS_SOURCE_PLANE_ID=7,
    PP_WS_SOURCE_PLANE_ORDER=8,PP_WS_SOURCE_PLANE_INVALID=9,
    PP_WS_SOURCE_ENVIRONMENT=10,PP_WS_SOURCE_ALLOCATION=11,PP_WS_SOURCE_EXCEPTION=12};
enum pp_ws_source_part {PP_WS_PART_NONE=0,PP_WS_PART_WORDS=1,PP_WS_PART_FLOATS=2,
    PP_WS_PART_BODY=3,PP_WS_PART_PLANE=4};
enum pp_ws_token_status {PP_WS_TOKEN_OK=0,PP_WS_TOKEN_WORD_COUNT=1,
    PP_WS_TOKEN_SLOT=2,PP_WS_TOKEN_ZERO=3,PP_WS_TOKEN_RANGE=4};
#define PP_WS_NOT_CALLED UINT32_MAX
/* owner/source/token_status are native enum ordinals, UINT32_MAX when not
 * called. A source diagnostic index is UINT32_MAX when absent. Every function
 * initializes every result field; token/revision are zero when not published. */
typedef struct pp_ws_result {
    uint32_t host,owner,source,token_status,part,index;
    uint32_t revision[2],token[3];
} pp_ws_result;
typedef struct pp_ws_snapshot_info {
    uint32_t available,float_count,word_count,token[3],sequence[2];
    double backlog;
} pp_ws_snapshot_info;
uint32_t pp_ws_api_version(void) PP_WS_NOEXCEPT;
/* Explicit generation limit: 1..2^53-1, low32/high21. Invalid limit or failed
 * context allocation returns NULL. Limits below the maximum permit retirement. */
pp_ws_context* pp_ws_context_create(uint32_t limit_low,uint32_t limit_high) PP_WS_NOEXCEPT;
void pp_ws_context_delete(pp_ws_context*) PP_WS_NOEXCEPT;
double* pp_ws_input_f64(pp_ws_context*) PP_WS_NOEXCEPT;
uint32_t* pp_ws_input_u32(pp_ws_context*) PP_WS_NOEXCEPT;
/* Source v1 layout is world_static_mesh_session_source_wire.hpp. Counts are
 * exact lengths, not byte sizes. Every non-busy stage attempt invalidates the
 * previous staged source, including count/admission failure. Successful stage
 * returns a new full64 revision, never wrapping. Input edits do not edit stage.
 * create/reset require that explicit revision; no implicit old-source fallback. */
pp_ws_result pp_ws_stage(pp_ws_context*,uint32_t float_count,uint32_t word_count) PP_WS_NOEXCEPT;
pp_ws_result pp_ws_create(pp_ws_context*,uint32_t revision_low,uint32_t revision_high) PP_WS_NOEXCEPT;
pp_ws_result pp_ws_reset(pp_ws_context*,uint32_t revision_low,uint32_t revision_high,
    uint32_t slot,uint32_t generation_low,uint32_t generation_high) PP_WS_NOEXCEPT;
pp_ws_result pp_ws_destroy(pp_ws_context*,uint32_t slot,uint32_t generation_low,uint32_t generation_high) PP_WS_NOEXCEPT;
pp_ws_result pp_ws_read(pp_ws_context*,uint32_t slot,uint32_t generation_low,uint32_t generation_high) PP_WS_NOEXCEPT;
/* Successful read publishes fixed owned arrays in the same plain-source v1
 * layout plus clock backlog/sequence metadata. Other operations/failed reads
 * keep this cache unchanged, including owner reset/destroy and failed stage.
 * These const views last until next successful read or context deletion.
 * Copy values before deleting the context. No mutable World is borrowed. */
pp_ws_snapshot_info pp_ws_snapshot_info_get(const pp_ws_context*) PP_WS_NOEXCEPT;
const double* pp_ws_snapshot_f64(const pp_ws_context*) PP_WS_NOEXCEPT;
const uint32_t* pp_ws_snapshot_u32(const pp_ws_context*) PP_WS_NOEXCEPT;
#ifdef __cplusplus
}
#endif
#undef PP_WS_NOEXCEPT
#endif
