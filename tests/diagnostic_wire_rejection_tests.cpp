#include "pikapika/diagnostic_wire.hpp"
#include <algorithm>
#include <array>
#include <cfenv>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <utility>
#include <vector>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
namespace d=pikapika::diagnostic_wire;
namespace {
void need(bool value) {if(!value) throw std::runtime_error("diagnostic rejection assertion");}
void ok(d::Status status) {need(status==d::Status::ok);}
static_assert(static_cast<unsigned>(d::Status::ok)==0 && static_cast<unsigned>(d::Status::reentrant)==6);
static_assert(static_cast<unsigned>(d::Tag::finish)==0 && static_cast<unsigned>(d::Tag::key)==15);
static_assert(noexcept(std::declval<d::Writer&>().reject_invalid_value()));
struct Capture {
    std::vector<std::byte> bytes;
    std::size_t calls=0,stop_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    d::Writer* other=nullptr;
    bool reenter=false;
    static bool sink(void* user,std::span<const std::byte> chunk) {
        auto& c=*static_cast<Capture*>(user);++c.calls;
        need(!chunk.empty() && chunk.size()<=d::max_chunk);
        if(c.reenter) {
            const auto calls=c.calls,bytes=c.bytes.size();
            need(c.writer->reject_invalid_value()==d::Status::reentrant);
            need(c.writer->status()==d::Status::ok && !c.writer->complete());
            need(c.calls==calls && c.bytes.size()==bytes);++c.reentries;
        }
        if(c.other) ok(c.other->u32(static_cast<std::uint32_t>(c.calls)));
        // Rejected chunks can already have been consumed by the transport.
        c.bytes.insert(c.bytes.end(),chunk.begin(),chunk.end());
        if(c.calls==c.throw_at) throw 7;
        return c.calls!=c.stop_at;
    }
};
void fixture(d::Writer& w) {
    ok(w.begin(0x524a4331));ok(w.array());ok(w.u32(0x12345678));
    ok(w.present());std::array<std::byte,513> payload{};
    for(std::size_t i=0;i<payload.size();++i) payload[i]=static_cast<std::byte>(i&255u);
    ok(w.bytes(payload));ok(w.end());ok(w.variant(1));ok(w.object());
    std::array<std::byte,257> key{};
    for(std::size_t i=0;i<key.size();++i) key[i]=static_cast<std::byte>((i*3)&255u);
    ok(w.key(key));ok(w.u64(UINT64_MAX));ok(w.end());ok(w.end());ok(w.end());ok(w.finish());
}
void sticky(d::Writer& w,Capture& c,d::Status expected) {
    const auto bytes=c.bytes;const auto calls=c.calls;const auto complete=w.complete();
    const double zero=0;
    const std::array statuses{w.reject_invalid_value(),w.reject_invalid_value(),w.begin(1),
        w.null_value(),w.boolean(false),w.u32(0),w.u64(0),w.i64(0),w.f64(zero),w.bytes({}),
        w.enumeration(0),w.object(),w.array(),w.absent(),w.present(),w.variant(0),w.key({}),w.end(),w.finish()};
    for(const auto s:statuses) need(s==expected);
    need(w.status()==expected && w.complete()==complete && c.calls==calls && c.bytes==bytes);
}
void phase(d::Writer& w,unsigned p) {
    if(p==0) return;
    ok(w.begin(1));if(p==1) return;
    switch(p) {
    case 2:ok(w.array());break;
    case 3:ok(w.array());ok(w.u32(3));break;
    case 4:ok(w.u32(3));break;
    case 5:ok(w.object());break;
    case 6:ok(w.object());ok(w.key({}));break;
    case 7:ok(w.object());ok(w.key({}));ok(w.u32(3));break;
    case 8:ok(w.present());break;
    case 9:ok(w.present());ok(w.u32(3));break;
    case 10:ok(w.variant(UINT32_MAX));break;
    case 11:ok(w.variant(UINT32_MAX));ok(w.u32(3));break;
    case 12:ok(w.array());ok(w.end());break;
    case 13:ok(w.null_value());ok(w.finish());break;
    default:for(std::size_t i=0;i<d::max_depth;++i) ok(w.array());break;
    }
}
void run() {
    const auto original_round=std::fegetround();need(original_round!=-1);
    std::size_t phases=0,rounds=0;
    for(const auto mode:{FE_TONEAREST,FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);++rounds;
        for(unsigned p=0;p<15;++p) {
            Capture c;d::Writer w(Capture::sink,&c);phase(w,p);
            need(w.status()==d::Status::ok);const auto complete=w.complete();
            const auto calls=c.calls;const auto bytes=c.bytes;
            need(w.reject_invalid_value()==d::Status::invalid_state);
            need(w.complete()==complete && c.calls==calls && c.bytes==bytes);
            need(complete==(p==13));sticky(w,c,d::Status::invalid_state);
            need(std::fegetround()==mode);++phases;
        }
    }
    need(std::fesetround(original_round)==0);
    std::size_t failures=0;
    for(unsigned p=0;p<5;++p) {
        Capture c;d::Writer w(p==2?nullptr:Capture::sink,&c);
        d::Status expected=d::Status::invalid_state;
        if(p==0) need(w.finish()==expected);
        if(p==1) {
            ok(w.begin(1));for(std::size_t i=0;i<d::max_depth;++i) ok(w.array());
            expected=d::Status::depth_limit;need(w.array()==expected);
        }
        if(p==2) {expected=d::Status::missing_sink;need(w.begin(1)==expected);}
        if(p==3) {c.stop_at=1;expected=d::Status::sink_stopped;need(w.begin(1)==expected);}
        if(p==4) {c.throw_at=1;expected=d::Status::sink_exception;need(w.begin(1)==expected);}
        sticky(w,c,expected);++failures;
    }
    Capture base;d::Writer bw(Capture::sink,&base);fixture(bw);
    need(bw.status()==d::Status::ok && bw.complete());
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.reenter=true;fixture(rw);
    need(re.bytes==base.bytes && re.calls==base.calls && re.reentries==base.calls);
    std::size_t stopped=0;
    for(std::size_t at=1;at<=base.calls;++at) {
        for(const bool throws:{false,true}) {
            Capture c;c.stop_at=throws?0:at;c.throw_at=throws?at:0;
            d::Writer w(Capture::sink,&c);c.writer=&w;c.reenter=true;
            try {fixture(w);} catch(const std::runtime_error&) {}
            const auto expected=throws?d::Status::sink_exception:d::Status::sink_stopped;
            need(w.status()==expected && !w.complete() && c.calls==at && c.reentries==at);
            need(c.bytes.size()<=base.bytes.size() && std::equal(c.bytes.begin(),c.bytes.end(),base.bytes.begin()));
            sticky(w,c,expected);++stopped;
        }
    }
    Capture outer,inner;d::Writer ow(Capture::sink,&outer),iw(Capture::sink,&inner);
    ok(iw.begin(2));ok(iw.array());outer.writer=&ow;outer.reenter=true;outer.other=&iw;
    fixture(ow);ok(iw.end());ok(iw.finish());need(outer.bytes==base.bytes && iw.complete());
    // A second writer's explicit refusal does not poison the completed first writer.
    const auto first=outer.bytes;need(iw.reject_invalid_value()==d::Status::invalid_state);
    need(iw.complete() && ow.status()==d::Status::ok && ow.complete() && outer.bytes==first);
    std::cout<<"{\"status\":\"PASS\",\"rejectionPhaseCases\":"<<phases
             <<",\"roundingModes\":"<<rounds<<",\"existingStickyFailures\":"<<failures
             <<",\"fixtureBytes\":"<<base.bytes.size()<<",\"callbackBoundaries\":"<<base.calls
             <<",\"stopAndExceptionCases\":"<<stopped<<",\"successfulReentryRefusals\":"<<re.reentries
             <<",\"explicitRejectionBytes\":0,\"explicitRejectionCallbacks\":0,\"completeAfterFinishedRejectionPreserved\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            Capture c;d::Writer w(Capture::sink,&c);fixture(w);
            std::cout.write(reinterpret_cast<const char*>(c.bytes.data()),static_cast<std::streamsize>(c.bytes.size()));
            return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
