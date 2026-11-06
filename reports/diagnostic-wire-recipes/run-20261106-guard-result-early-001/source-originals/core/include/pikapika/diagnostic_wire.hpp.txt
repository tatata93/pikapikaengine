#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>

namespace pikapika::diagnostic_wire {
inline constexpr std::uint32_t version=1;
inline constexpr std::size_t max_depth=64, max_chunk=256;
enum class Status : unsigned {ok, invalid_state, depth_limit, missing_sink, sink_stopped, sink_exception, reentrant};
// Tags are part of the v1 wire contract. All integer payloads are little endian.
enum class Tag : std::uint8_t {
    finish=0, null_value=1, boolean=2, u32=3, u64=4, i64=5, f64=6,
    bytes=7, enumeration=8, object=9, array=10, absent=11, present=12,
    variant=13, end=14, key=15
};
using Sink=bool (*)(void*,std::span<const std::byte>);
// Exclusive caller, valid immutable spans through each call. Sink data is only
// borrowed through the callback. Copy it there if needed. No allocations,
// global output redirection, floating arithmetic, model calls or rollback.
// A stopped/throwing sink may already have consumed a partial chunk/document.
// Publish a document only after finish() succeeds and the transport completes.
class Writer final {
public:
    Writer(Sink,void*) noexcept;
    Writer(const Writer&)=delete;
    Writer& operator=(const Writer&)=delete;
    Writer(Writer&&)=delete;
    Writer& operator=(Writer&&)=delete;
    Status begin(std::uint32_t schema) noexcept;
    Status null_value() noexcept;
    Status boolean(bool) noexcept;
    Status u32(std::uint32_t) noexcept;
    Status u64(std::uint64_t) noexcept;
    Status i64(std::int64_t) noexcept;
    Status f64(const double&) noexcept;
    Status bytes(std::span<const std::byte>) noexcept;
    Status enumeration(std::uint32_t ordinal) noexcept;
    Status object() noexcept;
    Status array() noexcept;
    Status absent() noexcept;
    Status present() noexcept;
    Status variant(std::uint32_t ordinal) noexcept;
    Status key(std::span<const std::byte>) noexcept;
    Status end() noexcept;
    Status finish() noexcept;
    // Emit nothing. Reentry is transient; an existing failure is preserved.
    // Otherwise latch invalid_state, even before begin() or after finish().
    // This does not revoke bytes already sent or clear complete().
    Status reject_invalid_value() noexcept;
    Status status() const noexcept {return status_;}
    bool complete() const noexcept {return complete_;}
private:
    struct Frame {Tag kind; bool pending=false;};
    Sink sink_; void* user_;
    std::array<Frame,max_depth> frames_{};
    std::size_t depth_=0;
    Status status_=Status::ok;
    bool active_=false,root_=false,complete_=false,in_sink_=false;
    Status gate() noexcept;
    Status fail(Status) noexcept;
    bool send(std::span<const std::byte>) noexcept;
    bool token(Tag,std::uint64_t=0,std::size_t=0) noexcept;
    bool value() noexcept;
    Status scalar(Tag,std::uint64_t=0,std::size_t=0) noexcept;
    Status container(Tag,std::uint32_t=0) noexcept;
};
}
