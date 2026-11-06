#pragma once
#include "pikapika/accelerated_pair_coverage.hpp"
#include <array>
#include <bit>
#include <cstdint>
#include <stdexcept>
namespace pikapika_report_pair_result_sources {
using namespace pikapika;
inline void need(bool b) {if(!b) throw std::runtime_error("pair Result artificial source assertion");}
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
struct OriginalCoefficients {
    std::array<a::Sphere,2> spheres{};
    std::array<a::StaticPlane,2> planes{};
    OriginalCoefficients() {
        Numbers values;
        for(auto& v:spheres) {v.center=values.vec();v.velocity=values.vec();v.acceleration=values.vec();v.radius=values.next();}
        for(auto& v:planes) {v.normal=values.vec();v.offset=values.next();}
        need(values.n==28);
    }
};
namespace p=pikapika::accelerated_pair_coverage;
struct PairSources {
    std::array<p::SpherePair,2> pairs{};
    std::array<p::SpherePlane,2> planes{};
    PairSources() {
        OriginalCoefficients original;
        pairs[0]={original.spheres[0],original.spheres[1]};
        pairs[1]={original.spheres[1],original.spheres[0]};
        planes[0]={original.spheres[0],original.planes[0]};
        planes[1]={original.spheres[1],original.planes[1]};
    }
};
struct InputSources {
    std::array<p::Input,4> values;
    InputSources() {PairSources v;values={p::Input{v.pairs[0]},p::Input{v.pairs[1]},p::Input{v.planes[0]},p::Input{v.planes[1]}};}
};
struct SnapshotSources {
    std::array<p::Snapshot,16> values{};
    SnapshotSources() {
        InputSources original;Numbers horizons,tolerances;tolerances.n=5;
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<unsigned,4> depths{0,UINT32_MAX,31,32};
        for(std::size_t i=0;i<values.size();++i) {
            auto& value=values[i];value.input=original.values[i%4];value.horizon=horizons.next();
            value.settings.time_tolerance=tolerances.next();value.settings.max_evaluations=static_cast<std::size_t>(counts[i%4]);
            value.settings.max_leaves=static_cast<std::size_t>(counts[(i+1)%4]);value.settings.max_depth=depths[(i+2)%4];
        }
    }
};
struct AuditPartitionSources {
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
        auto reason=[](std::size_t n) {const auto k=n%17;return static_cast<p::Reason>(k<15?static_cast<unsigned>(k):(k==15?0x80000000u:UINT32_MAX));};
        for(std::size_t i=0;i<audits.size();++i) {
            auto& value=audits[i];value.cell.time_bounds={std::bit_cast<double>(bits[2*i%16]),std::bit_cast<double>(bits[(2*i+1)%16])};value.cell.depth=depths[i%4];
            if(i&4) value.cell.parent_audit=static_cast<std::size_t>(counts[i%4]);
            value.call_attempted=(i&8)!=0;
            if(i&1) {
                switch((i/2)%5) {
                case 0:value.value=interval::Interval::point(0);break;
                case 1:value.value=interval::Interval::whole();break;
                case 2:value.value=interval::Interval(std::bit_cast<double>(bits[9]),std::bit_cast<double>(bits[8]));break;
                case 3:value.value=interval::Interval(std::bit_cast<double>(bits[2]),std::bit_cast<double>(bits[5]));break;
                default:value.value=interval::Interval(-1,std::bit_cast<double>(bits[3]));break;
                }
            }
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
struct CellWorkSources {
    std::array<p::Cell,8> cells{};
    std::array<p::Work,4> works{};
    CellWorkSources() {
        constexpr std::array<std::uint64_t,16> bits{0,0x8000000000000000ull,1,0x8000000000000001ull,
            0x000fffffffffffffull,0x0010000000000000ull,0x3ff0000000000000ull,0xbff0000000000000ull,
            0x7fefffffffffffffull,0xffefffffffffffffull,0x7ff0000000000000ull,0xfff0000000000000ull,
            0x7ff8000000000042ull,0xfff8000000001234ull,0x7ff0000000000001ull,0xfff0000000000001ull};
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<unsigned,4> depths{0,UINT32_MAX,31,32};
        for(std::size_t i=0;i<cells.size();++i) {
            cells[i].time_bounds={std::bit_cast<double>(bits[2*i]),std::bit_cast<double>(bits[2*i+1])};
            cells[i].depth=depths[i%4];if(i>=4) cells[i].parent_audit=static_cast<std::size_t>(counts[i-4]);
        }
        for(std::size_t i=0;i<works.size();++i) works[i]={static_cast<std::size_t>(counts[i]),static_cast<std::size_t>(counts[(i+1)%4]),static_cast<std::size_t>(counts[(i+2)%4]),static_cast<std::size_t>(counts[(i+3)%4])};
    }
};

struct ResultSources {
    std::array<p::Result,17> values{};
    ResultSources() {
        SnapshotSources snapshots;AuditPartitionSources rows;CellWorkSources counts_source;
        constexpr std::array<std::uint64_t,4> counts{0,UINT64_MAX,9007199254740993ull,0x8000000000000000ull};
        constexpr std::array<unsigned,6> kinds{0,1,2,3,0x80000000u,UINT32_MAX};
        for(std::size_t i=0;i<values.size();++i) {
            auto& value=values[i];value.status=static_cast<p::Status>(kinds[i%6]);
            value.reason=static_cast<p::Reason>(i<15?static_cast<unsigned>(i):(i==15?0x80000000u:UINT32_MAX));
            if(i&1) value.snapshot=snapshots.values[(i/2)%16];
            value.snapshot_validated=((i&1)!=0)!=((i&2)!=0);
            if(i&2) value.failed_input=static_cast<std::size_t>(counts[(i/4+i)%4]);
            value.partition_complete=((i&2)!=0)!=((i&4)!=0);
            for(std::size_t j=0;j<i%3;++j) {value.audits.push_back(rows.audits[(i+j)%20]);value.partition.push_back(rows.leaves[(i+j)%12]);}
            for(std::size_t j=0;j<i%4;++j) value.frontier.push_back(rows.audits[(i+3*j)%20].cell);
            if(i&4) value.current=rows.audits[i%20].cell;
            value.work=counts_source.works[(i+1)%4];
            if(i) {
                const std::array<unsigned char,6> body{0x41,static_cast<unsigned char>(i),0,0xff,0x80,0x42};
                value.message.assign(reinterpret_cast<const char*>(body.data()),body.size());
            }
        }
        values[7].audits={rows.audits[5],rows.audits[3],rows.audits[5]};
        values[6].partition={rows.leaves[9],rows.leaves[3],rows.leaves[9]};
        auto& last=values.back();last.audits.assign(rows.audits.begin(),rows.audits.end());last.partition.assign(rows.leaves.begin(),rows.leaves.end());
        last.frontier={rows.audits[0].cell,rows.audits[7].cell,rows.audits[0].cell};
        std::array<unsigned char,256> body{};for(std::size_t i=0;i<body.size();++i) body[i]=static_cast<unsigned char>(i);
        last.message.assign(reinterpret_cast<const char*>(body.data()),body.size());last.message.push_back('\0');
    }
};
}
