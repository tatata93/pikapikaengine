#include "pikapika/report_values_wire.hpp"
#include <algorithm>
#include <cstring>
#include <array>
#include <bit>
#include <cfenv>
#include <iostream>
#include <stdexcept>
#include <string_view>
#include <vector>
#include <type_traits>
#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#endif
namespace r=pikapika::report_values_wire;
namespace d=pikapika::diagnostic_wire;
namespace c=pikapika::world_static_mesh_flight_controlled_tick;
namespace s=pikapika::world_static_mesh_flight_scheduler;
using namespace pikapika;
namespace {
static_assert(sizeof(std::size_t)==8);
void need(bool b) {if(!b) throw std::runtime_error("report guard PlaneBoxCall assertion");}
void ok(d::Status x) {need(x==d::Status::ok);}
namespace p=pikapika::accelerated_plane_box_coverage;
namespace a=pikapika::accelerated;
struct Numbers {
    std::size_t n=0;
    double next() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        return std::bit_cast<double>(bits[n++%bits.size()]);
    }
    Vec3 vec() {return {next(),next(),next()};}
};
struct PlaneSources {
    static p::Input input(std::size_t index) {
        Numbers values;values.n=3*index;
        a::Sphere sphere{};sphere.center=values.vec();sphere.velocity=values.vec();sphere.acceleration=values.vec();sphere.radius=values.next();
        a::StaticPlane plane{};plane.normal=values.vec();plane.offset=values.next();
        const double error=values.next(),margin=values.next();
        return p::Input(sphere,plane,error,margin);
    }
    static p::Snapshot snapshot(std::size_t index) {
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,4> depths{0,32,0x80000000u,UINT32_MAX};
        Numbers values;values.n=index;
        const double horizon=values.next(),tolerance=values.next();
        return {input(index+8),horizon,{tolerance,counts[index%4],counts[(index+1)%4],depths[index%4]}};
    }
    std::array<p::Input,8> inputs{input(0),input(1),input(2),input(3),input(4),input(5),input(6),input(7)};
    std::array<p::Snapshot,8> snapshots{snapshot(0),snapshot(1),snapshot(2),snapshot(3),snapshot(4),snapshot(5),snapshot(6),snapshot(7)};
};
struct AuditPartitionSources {
    static interval::Interval part(std::size_t index) {
        constexpr std::array<std::array<std::uint64_t,2>,12> bits{{
            {0,0},{0xfff0000000000000ull,0x7ff0000000000000ull},
            {0x3ff0000000000000ull,0x3ff0000000000000ull},{0xc000000000000000ull,0xbff0000000000000ull},
            {1,2},{0x8000000000000002ull,0x8000000000000001ull},
            {0,1},{0x8000000000000001ull,0},
            {0xfff0000000000000ull,0xbff0000000000000ull},{0x3ff0000000000000ull,0x7ff0000000000000ull},
            {0x7fefffffffffffffull,0x7fefffffffffffffull},{0x0010000000000000ull,0x0020000000000000ull}
        }};
        const auto& pair=bits[index%bits.size()];
        return interval::Interval(std::bit_cast<double>(pair[0]),std::bit_cast<double>(pair[1]));
    }
    static p::Evaluation value(std::size_t index) {
        const auto start=5*index;
        return {{part(start),part(start+1),part(start+2)},part(start+3),part(start+4),part(start+5)};
    }

    std::array<p::Audit,20> audits{};
    std::array<p::PartitionLeaf,12> leaves{};
    AuditPartitionSources() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<unsigned,4> depths{0,UINT32_MAX,31,32};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        auto reason=[](std::size_t n) {const auto k=n%19;return static_cast<p::Reason>(k<17?static_cast<unsigned>(k):(k==17?0x80000000u:UINT32_MAX));};
        for(std::size_t i=0;i<audits.size();++i) {
            auto& value=audits[i];value.cell.time_bounds={std::bit_cast<double>(bits[2*i%16]),std::bit_cast<double>(bits[(2*i+1)%16])};value.cell.depth=depths[i%4];
            if(i&4) value.cell.parent_audit=static_cast<std::size_t>(counts[i%4]);
            value.call_attempted=(i&8)!=0;
            if(i&1) value.evaluation=AuditPartitionSources::value(i/2);
            value.outcome=static_cast<p::Outcome>(kinds[i%6]);value.blocked_reason=reason(i);
            if(i&2) value.split_time=std::bit_cast<double>(bits[(i+3)%16]);
        }
        for(std::size_t i=0;i<leaves.size();++i) {
            auto& value=leaves[i];value.cell.time_bounds={std::bit_cast<double>(bits[(2*i+3)%16]),std::bit_cast<double>(bits[(2*i+4)%16])};value.cell.depth=depths[(i+1)%4];
            if(i&2) value.cell.parent_audit=static_cast<std::size_t>(counts[(i/4+i)%4]);
            value.state=static_cast<p::LeafState>(kinds[i%6]);
            if(i&1) value.audit_index=static_cast<std::size_t>(counts[(i/2)%4]);
            value.blocked_reason=reason(i+7);
        }
    }
};
struct ResultSources {
    std::array<p::Result,32> values{};
    ResultSources() {
        PlaneSources snapshots;AuditPartitionSources proof;
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.status=static_cast<p::Status>(kinds[i%6]);
            const auto reason=i%19;v.reason=static_cast<p::Reason>(reason<17?static_cast<unsigned>(reason):(reason==17?0x80000000u:UINT32_MAX));
            if(i&1) v.snapshot=snapshots.snapshots[(i/2)%8];
            v.snapshot_validated=(i&8)!=0;
            if(i&2) v.failed_input=counts[(i/4+i)%4];
            v.partition_complete=(i&16)!=0;
            if(i==2) {v.audits={proof.audits[2],proof.audits[3]};v.partition={proof.leaves[4],proof.leaves[5]};v.frontier={proof.audits[6].cell,proof.audits[7].cell};}
            if(i==6) v.partition={proof.leaves[9],proof.leaves[3],proof.leaves[9]};
            if(i==7) v.audits={proof.audits[5],proof.audits[3],proof.audits[5]};
            if(i && i%7==0 && i!=7) {v.audits={proof.audits[i%20]};v.partition={proof.leaves[i%12]};v.frontier={proof.audits[(i+3)%20].cell};}
            if(i==31) {v.audits.assign(proof.audits.begin(),proof.audits.end());v.partition.assign(proof.leaves.begin(),proof.leaves.end());v.frontier={proof.audits[0].cell,proof.audits[7].cell,proof.audits[0].cell};}
            if(i&4) v.current=proof.audits[i%20].cell;
            v.work={counts[(i+1)%4],counts[(i+2)%4]};
            if(i) {const std::array<unsigned char,6> body{0x41,static_cast<unsigned char>(i),0,255,128,0x42};v.message.assign(reinterpret_cast<const char*>(body.data()),body.size());}
            if(i==31) {v.message.clear();for(unsigned j=0;j<256;++j) v.message.push_back(static_cast<char>(j));v.message.push_back('\0');}
        }
    }
};
namespace g=world_static_mesh_flight_guard;
struct Ledgers {
    g::Counter counter{0,SIZE_MAX,false};
    g::HeldLedger held{
        {0,SIZE_MAX,false},{9007199254740993ull,0,true},{SIZE_MAX,1,false},
        {17,19,true},{23,29,false},{31,37,true},{41,43,false},{47,53,true},{59,61,false}};
    g::Retained retained{0,SIZE_MAX,9007199254740993ull,0x8000000000000000ull,5,7,11,13,17,19,23,29,31};
    g::WorkGrant granted{SIZE_MAX,9007199254740993ull,0,0x8000000000000000ull,37,41,43,47,53};
    g::Reservation reservation{retained,granted,{0,1,2,3,5,8,13,21,34}};
    g::Grant grant{retained,{55,89,144,233,377,610,987,1597,2584}};
    g::MessageOmission omission{SIZE_MAX,0,9007199254740993ull,true};
};
struct PlaneBoxCallSources {
    std::array<g::PlaneBoxCall,16> values{};
    PlaneBoxCallSources() {
        PlaneSources settings;ResultSources results;Ledgers ledgers;
        constexpr std::array<std::size_t,4> counts{0,UINT64_MAX,9007199254740993ull,1ull<<63};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& v=values[i];v.state=static_cast<g::CallState>(kinds[i%6]);
            if(i&1) v.attempt_ordinal=counts[(i/2)%4];
            v.requested_settings=settings.snapshots[i%8].settings;
            v.used_settings=settings.snapshots[(i+1)%8].settings;
            v.granted=(i&4)!=0;v.grant=ledgers.grant;
            if(i&2) v.result=results.values[i==2?0:(i==15?31:(i%4==3?7:(i%8==6?6:2)))];
            v.messages={counts[i%4],counts[(i+1)%4],counts[(i+2)%4],(i&8)!=0};
        }
    }
};
void fixture(d::Writer& w,const PlaneBoxCallSources& v) {
    ok(w.begin(0x52475042));ok(w.array());
    for(const auto& value:v.values) {ok(r::write(w,value));}
    ok(w.end());ok(w.finish());need(w.complete());
}
struct Capture {
    std::vector<std::byte> data;
    std::size_t calls=0,fail_at=0,throw_at=0,reentries=0;
    d::Writer* writer=nullptr;
    const PlaneBoxCallSources* source=nullptr;
    Capture() {data.reserve(65536);}
    static bool sink(void* user,std::span<const std::byte> bytes) {
        auto& c=*static_cast<Capture*>(user);++c.calls;need(bytes.size()<=256);
        if(c.writer) {
            const auto& v=*c.source;auto& w=*c.writer;
            need(r::write(w,v.values[c.calls%16])==d::Status::reentrant);++c.reentries;
            need(r::write(w,v.values[(c.calls+7)%16])==d::Status::reentrant);++c.reentries;need(w.status()==d::Status::ok);
        }
        c.data.insert(c.data.end(),bytes.begin(),bytes.end());
        if(c.throw_at==c.calls) throw 1;
        return c.fail_at!=c.calls;
    }
};
void run() {
    need(std::fegetround()==FE_TONEAREST);
    PlaneBoxCallSources v;Capture base;d::Writer w(Capture::sink,&base);fixture(w,v);
    for(std::size_t i=1;i<=base.calls;++i) {
        for(const bool throws:{false,true}) {
            Capture x;x.fail_at=throws?0:i;x.throw_at=throws?i:0;d::Writer out(Capture::sink,&x);
            try {fixture(out,v);} catch(const std::runtime_error&) {}
            need(out.status()==(throws?d::Status::sink_exception:d::Status::sink_stopped) && !out.complete() && x.calls==i);
            need(x.data.size()<=base.data.size() && (x.data.empty() || std::memcmp(x.data.data(),base.data.data(),x.data.size())==0));
        }
    }
    Capture re;d::Writer rw(Capture::sink,&re);re.writer=&rw;re.source=&v;fixture(rw,v);need(re.data==base.data && re.reentries==2*base.calls);
    const auto saved=std::fegetround();need(saved!=-1);
    for(const auto mode:std::array<int,4>{FE_TONEAREST,FE_UPWARD,FE_DOWNWARD,FE_TOWARDZERO}) {
        need(std::fesetround(mode)==0);Capture x;d::Writer out(Capture::sink,&x);fixture(out,v);need(std::fegetround()==mode && x.data==base.data);

    }
    need(std::fesetround(saved)==0);Capture after;d::Writer aw(Capture::sink,&after);fixture(aw,v);need(after.data==base.data);
    std::cout<<"{\"status\":\"PASS\",\"mappedTypes\":1,\"mappedFields\":8,\"fixtureRecords\":16,\"fixtureBytes\":"<<base.data.size()
             <<",\"callbackBoundaries\":"<<base.calls<<",\"stopAndExceptionCases\":"<<2*base.calls<<",\"reentryRefusals\":"<<re.reentries
             <<",\"actualRoundingModesRetained\":4,\"artificialDiagnosticRecords\":16,\"actualModelCalls\":0,\"sourceRepeatedRawExact\":true}\n";
}
}
int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string_view(argv[1])=="--fixture") {
#ifdef _WIN32
            if(_setmode(_fileno(stdout),_O_BINARY)==-1) return 2;
#endif
            PlaneBoxCallSources values;Capture c;d::Writer w(Capture::sink,&c);fixture(w,values);
            std::cout.write(reinterpret_cast<const char*>(c.data.data()),static_cast<std::streamsize>(c.data.size()));return std::cout.good()?0:2;
        }
        if(argc!=2 || std::string_view(argv[1])!="--run") return 2;
        run();return 0;
    } catch(const std::exception& e) {std::cerr<<e.what()<<'\n';return 1;}
}
