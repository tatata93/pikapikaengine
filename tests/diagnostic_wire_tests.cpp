#include "pikapika/diagnostic_wire.hpp"
#include <algorithm>
#include <array>
#include <bit>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string_view>
#include <vector>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
namespace d=pikapika::diagnostic_wire;
namespace {
void need(bool b) {if(!b) throw std::runtime_error("diagnostic wire assertion");}
void ok(d::Status s) {need(s==d::Status::ok);}
std::span<const std::byte> raw(std::string_view s) {return std::as_bytes(std::span(s.data(),s.size()));}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,largest=0,fail_at=0,throw_at=0,reentry_checks=0;
    d::Writer* writer=nullptr;
    d::Writer* other=nullptr;
    bool reenter=false;
    Capture() {data.reserve(8192);}
    static bool sink(void* user,std::span<const std::byte> chunk) {
        auto& c=*static_cast<Capture*>(user);
        ++c.calls;c.largest=std::max(c.largest,chunk.size());
        need(!chunk.empty() && chunk.size()<=d::max_chunk);
        if(c.reenter) {
            auto& w=*c.writer;
            const double n=0;
            const std::array results{w.begin(1),w.null_value(),w.boolean(false),w.u32(0),w.u64(0),w.i64(0),w.f64(n),w.bytes({}),w.enumeration(0),w.object(),w.array(),w.absent(),w.present(),w.variant(0),w.key({}),w.end(),w.finish()};
            for(const auto s:results) {need(s==d::Status::reentrant);++c.reentry_checks;}
            need(w.status()==d::Status::ok && !w.complete());
        }
        if(c.other) {ok(c.other->u32(static_cast<std::uint32_t>(c.calls)));}
        // Deliberately consume even a rejected chunk: rejection is not rollback.
        c.data.insert(c.data.end(),chunk.begin(),chunk.end());
        if(c.throw_at==c.calls) throw 7;
        return c.fail_at!=c.calls;
    }
};
constexpr std::array<std::uint64_t,16> bits{
    0,0x8000000000000000ull,1,0x8000000000000001ull,
    0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
    0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
    0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
void fixture(d::Writer& w) {
    ok(w.begin(0x44544731));ok(w.object());
    ok(w.key(raw("bits")));ok(w.array());
    for(const auto b:bits) {const auto n=std::bit_cast<double>(b);ok(w.f64(n));}
    ok(w.end());
    ok(w.key(raw("integers")));ok(w.array());
    ok(w.u32(0));ok(w.u32(UINT32_MAX));ok(w.u64(0));ok(w.u64(UINT64_MAX));ok(w.u64(9007199254740993ull));
    ok(w.i64(INT64_MIN));ok(w.i64(-1));ok(w.i64(INT64_MAX));ok(w.enumeration(UINT32_MAX));ok(w.end());
    ok(w.key(raw("optional")));ok(w.array());ok(w.absent());ok(w.present());ok(w.null_value());ok(w.end());ok(w.end());
    ok(w.key(raw("variant")));ok(w.variant(UINT32_MAX));ok(w.object());
    ok(w.key(raw("")));ok(w.boolean(true));ok(w.key(raw("zero")));ok(w.boolean(false));ok(w.end());ok(w.end());
    ok(w.key(raw("bytes")));
    std::array<std::byte,769> data{};
    for(std::size_t i=0;i<data.size();++i) data[i]=static_cast<std::byte>(i&255u);
    ok(w.bytes(data));
    // Byte strings and field keys are opaque, including NUL and invalid UTF-8.
    const std::array key{std::byte{0},std::byte{0xff},std::byte{0xc0}};
    ok(w.key(key));ok(w.bytes({}));ok(w.end());ok(w.finish());need(w.complete());
}
void run() {
    Capture base;d::Writer w(Capture::sink,&base);fixture(w);
    need(base.largest==256 && base.data.size()>1000);
    // Exercise every actual callback boundary, including header and completion.
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture c;c.fail_at=throws?0:i;c.throw_at=throws?i:0;d::Writer out(Capture::sink,&c);
            try {fixture(out);} catch(const std::runtime_error&) {}
            const auto expected=throws?d::Status::sink_exception:d::Status::sink_stopped;
            need(out.status()==expected && !out.complete() && c.calls==i);
            need(c.data.size()<=base.data.size() && std::equal(c.data.begin(),c.data.end(),base.data.begin()));
            const auto before=c.data;need(out.finish()==expected && out.u32(1)==expected && c.data==before);
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.reenter=true;fixture(rw);
    need(re.data==base.data && re.reentry_checks==17*base.calls);
    Capture a,b;d::Writer aw(Capture::sink,&a),bw(Capture::sink,&b);
    ok(bw.begin(2));ok(bw.array());a.other=&bw;fixture(aw);ok(bw.end());ok(bw.finish());
    need(a.data==base.data && bw.complete());
    std::size_t invalid=0;
    for(unsigned which=0;which<15;++which) {
        Capture c;d::Writer out(Capture::sink,&c);d::Status s=d::Status::ok;
        if(which==0) s=out.u32(1);
        else if(which==1) s=out.begin(0);
        else {
            ok(out.begin(1));
            switch(which) {
            case 2:s=out.begin(1);break;
            case 3:s=out.finish();break;
            case 4:s=out.end();break;
            case 5:s=out.key({});break;
            case 6:ok(out.object());s=out.u32(1);break;
            case 7:ok(out.object());ok(out.key({}));s=out.end();break;
            case 8:ok(out.object());ok(out.key({}));s=out.key({});break;
            case 9:ok(out.present());s=out.end();break;
            case 10:ok(out.variant(1));s=out.end();break;
            case 11:ok(out.present());ok(out.u32(1));s=out.u32(2);break;
            case 12:ok(out.u32(1));s=out.u32(2);break;
            case 13:ok(out.array());s=out.finish();break;
            default:ok(out.null_value());ok(out.finish());s=out.finish();break;
            }
        }
        need(s==d::Status::invalid_state);const auto n=c.calls;need(out.array()==s && c.calls==n);++invalid;
    }
    Capture depth;d::Writer dw(Capture::sink,&depth);ok(dw.begin(1));
    for(std::size_t i=0;i<64;++i) ok(dw.array());
    const auto n=depth.calls;need(dw.array()==d::Status::depth_limit && depth.calls==n && !dw.complete());
    Capture exact;d::Writer ew(Capture::sink,&exact);ok(ew.begin(1));
    for(std::size_t i=0;i<64;++i) ok(ew.array());
    ok(ew.null_value());for(std::size_t i=0;i<64;++i) ok(ew.end());ok(ew.finish());
    d::Writer missing(nullptr,nullptr);need(missing.begin(1)==d::Status::missing_sink);
    std::cout<<"{\"status\":\"PASS\",\"fixtureBytes\":"<<base.data.size()<<",\"callbackBoundaries\":"<<base.calls
             <<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentry_checks
             <<",\"invalidGrammarCases\":"<<invalid<<",\"depthBoundary\":64,\"floatBitPatterns\":16}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            Capture c;d::Writer w(Capture::sink,&c);fixture(w);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));
            return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
