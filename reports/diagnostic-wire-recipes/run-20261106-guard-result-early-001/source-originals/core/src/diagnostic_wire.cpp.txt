#include "pikapika/diagnostic_wire.hpp"
#include <algorithm>
#include <bit>
#include <limits>

namespace pikapika::diagnostic_wire {
static_assert(sizeof(double)==8 && std::numeric_limits<double>::is_iec559);
static_assert(sizeof(std::size_t)<=sizeof(std::uint64_t));
Writer::Writer(Sink sink,void* user) noexcept:sink_(sink),user_(user) {}
Status Writer::gate() noexcept {
    // Reentry is a transient refusal: it neither emits nor poisons the outer call.
    if(in_sink_) return Status::reentrant;
    return status_;
}
Status Writer::fail(Status s) noexcept {status_=s;return s;}
Status Writer::reject_invalid_value() noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    return fail(Status::invalid_state);
}
bool Writer::send(std::span<const std::byte> data) noexcept {
    while(!data.empty()) {
        const auto n=std::min(data.size(),max_chunk);
        in_sink_=true;
        bool accepted=false;
        try {accepted=sink_(user_,data.first(n));}
        catch(...) {in_sink_=false;fail(Status::sink_exception);return false;}
        in_sink_=false;
        if(!accepted) {fail(Status::sink_stopped);return false;}
        data=data.subspan(n);
    }
    return true;
}
bool Writer::token(Tag tag,std::uint64_t number,std::size_t width) noexcept {
    std::array<std::byte,9> buffer{};
    buffer[0]=static_cast<std::byte>(tag);
    for(std::size_t i=0;i<width;++i) buffer[i+1]=static_cast<std::byte>((number>>(8*i))&255u);
    return send(std::span(buffer).first(width+1));
}
Status Writer::begin(std::uint32_t schema) noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    if(active_ || complete_ || schema==0) return fail(Status::invalid_state);
    if(!sink_) return fail(Status::missing_sink);
    std::array<std::byte,12> header{std::byte{'P'},std::byte{'P'},std::byte{'D'},std::byte{'R'}};
    for(std::size_t i=0;i<4;++i) {
        header[4+i]=static_cast<std::byte>((version>>(8*i))&255u);
        header[8+i]=static_cast<std::byte>((schema>>(8*i))&255u);
    }
    if(send(header)) active_=true;
    return status_;
}
bool Writer::value() noexcept {
    if(!active_ || complete_) {fail(Status::invalid_state);return false;}
    if(depth_==0) {
        if(root_) {fail(Status::invalid_state);return false;}
        root_=true;return true;
    }
    auto& f=frames_[depth_-1];
    if(f.kind==Tag::array) return true;
    if(!f.pending) {fail(Status::invalid_state);return false;}
    f.pending=false;return true;
}
Status Writer::scalar(Tag tag,std::uint64_t n,std::size_t width) noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    if(value()) token(tag,n,width);
    return status_;
}
Status Writer::null_value() noexcept {return scalar(Tag::null_value);}
Status Writer::boolean(bool n) noexcept {return scalar(Tag::boolean,n?1u:0u,1);}
Status Writer::u32(std::uint32_t n) noexcept {return scalar(Tag::u32,n,4);}
Status Writer::u64(std::uint64_t n) noexcept {return scalar(Tag::u64,n,8);}
Status Writer::i64(std::int64_t n) noexcept {return scalar(Tag::i64,static_cast<std::uint64_t>(n),8);}
Status Writer::f64(const double& n) noexcept {return scalar(Tag::f64,std::bit_cast<std::uint64_t>(n),8);}
Status Writer::enumeration(std::uint32_t n) noexcept {return scalar(Tag::enumeration,n,4);}
Status Writer::absent() noexcept {return scalar(Tag::absent);}
Status Writer::bytes(std::span<const std::byte> data) noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    if(value() && token(Tag::bytes,static_cast<std::uint64_t>(data.size()),8)) send(data);
    return status_;
}
Status Writer::container(Tag kind,std::uint32_t ordinal) noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    if(depth_==max_depth) return fail(Status::depth_limit);
    if(value() && token(kind,ordinal,kind==Tag::variant?4u:0u)) {
        frames_[depth_++]={kind,kind==Tag::present || kind==Tag::variant};
    }
    return status_;
}
Status Writer::object() noexcept {return container(Tag::object);}
Status Writer::array() noexcept {return container(Tag::array);}
Status Writer::present() noexcept {return container(Tag::present);}
Status Writer::variant(std::uint32_t n) noexcept {return container(Tag::variant,n);}
Status Writer::key(std::span<const std::byte> data) noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    if(!active_ || !depth_ || frames_[depth_-1].kind!=Tag::object || frames_[depth_-1].pending) return fail(Status::invalid_state);
    if(token(Tag::key,static_cast<std::uint64_t>(data.size()),8) && send(data)) frames_[depth_-1].pending=true;
    return status_;
}
Status Writer::end() noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    if(!active_ || !depth_ || frames_[depth_-1].pending) return fail(Status::invalid_state);
    if(token(Tag::end)) --depth_;
    return status_;
}
Status Writer::finish() noexcept {
    if(const auto s=gate();s!=Status::ok) return s;
    if(!active_ || depth_ || !root_ || complete_) return fail(Status::invalid_state);
    if(token(Tag::finish)) {complete_=true;active_=false;}
    return status_;
}
}
