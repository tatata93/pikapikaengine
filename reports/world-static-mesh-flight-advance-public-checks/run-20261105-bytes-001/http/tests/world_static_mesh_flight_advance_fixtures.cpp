#include "world_static_mesh_flight_advance_fixture_support.hpp"
#include <array>
#include <bit>
#include <charconv>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <type_traits>
#include <utility>
#include <vector>

namespace world_advance_fixture {
namespace {
namespace g=pikapika::world_static_mesh_flight_guard;
namespace p=pikapika::world_static_mesh_flight;
namespace d=pikapika::dynamics;
namespace held=pikapika::sphere_triangle_mesh_held_load;
namespace flight=pikapika::sphere_triangle_mesh_free_flight_guard;
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using Bits=std::vector<std::uint64_t>;

void require(bool condition,std::string_view message) {
    if(!condition) {throw std::runtime_error(std::string(message));}
}
std::uint64_t bits(double value) noexcept {return std::bit_cast<std::uint64_t>(value);}
void flag(std::ostream& out,bool value) {out<<(value?"true":"false");}
void number(std::ostream& out,double value) {
    require(std::isfinite(value),"Nonfinite transaction fixture value");
    if(value==0&&std::signbit(value)) {out<<"-0";}
    else {out<<std::setprecision(std::numeric_limits<double>::max_digits10)<<value;}
}
void quoted(std::ostream& out,std::string_view value) {
    // Native diagnostics currently are ASCII. Valid UTF-8 is also retained as
    // original bytes; reject invalid sequences rather than silently replacing.
    for(std::size_t i=0;i<value.size();) {
        const auto ch=static_cast<unsigned char>(value[i]);
        if(ch<0x80U) {++i;continue;}
        const unsigned n=ch>=0xc2U&&ch<=0xdfU?2U:ch>=0xe0U&&ch<=0xefU?3U:ch>=0xf0U&&ch<=0xf4U?4U:0U;
        require(n!=0&&value.size()-i>=n,"Invalid UTF-8 fixture string");
        for(unsigned j=1;j<n;++j) {
            const auto next=static_cast<unsigned char>(value[i+j]);
            require(next>=0x80U&&next<=0xbfU,"Invalid UTF-8 continuation");
        }
        const auto second=static_cast<unsigned char>(value[i+1]);
        require(!(ch==0xe0U&&second<0xa0U)&&!(ch==0xedU&&second>=0xa0U)&&
                !(ch==0xf0U&&second<0x90U)&&!(ch==0xf4U&&second>=0x90U),"Invalid UTF-8 scalar");
        i+=n;
    }
    constexpr char hex[]="0123456789abcdef";
    out<<'"';
    for(char raw:value) {
        const auto ch=static_cast<unsigned char>(raw);
        if(ch=='"'||ch=='\\') {out<<'\\'<<raw;}
        else if(ch<0x20U) {out<<"\\u00"<<hex[ch>>4U]<<hex[ch&15U];}
        else {out<<raw;}
    }
    out<<'"';
}
template<class Enum,std::size_t N>
const char* name(Enum value,const char* const (&names)[N]) {
    const auto index=static_cast<std::underlying_type_t<Enum>>(value);
    require(index<N,"Unknown transaction fixture enum");
    return names[index];
}
template<class Enum> void enum_range(Enum value,Enum last) {
    using U=std::underlying_type_t<Enum>;
    require(static_cast<U>(value)<=static_cast<U>(last),"Unknown nested fixture enum");
}
const char* status(advance::Status value) {
    constexpr const char* names[]={"committed","not_certified","invalid_input","unsupported_environment","numerical_failure"};
    return name(value,names);
}
const char* reason(advance::Reason value) {
    constexpr const char* names[]={"none","environment","binding_unsupported","horizon","progress_time","progress_ticks",
        "tick_limit","time_overflow","time_limit","time_resolution","clock_enclosure","guard_failed","guard_incomplete",
        "origin_mismatch","candidate_mismatch","candidate_validation","destination_mismatch","allocation_failure","unexpected_exception"};
    return name(value,names);
}
const char* stage(advance::Stage value) {
    constexpr const char* names[]={"environment","binding","clock","guard","commit_preparation","candidate_validation"};
    return name(value,names);
}
const char* kind(p::ObjectKind value) {
    constexpr const char* names[]={"settings","world","body","plane","mesh","face"};
    return name(value,names);
}
template<class T> void index(std::ostream& out,const std::optional<T>& value) {
    if(value) {out<<*value;} else {out<<"null";}
}
void progress_json(std::ostream& out,advance::Progress value) {
    require(value.ticks<=advance::maximum_ticks,"Progress ticks outside declared exact-integer domain");
    out<<"{\"time\":";number(out,value.time);out<<",\"ticks\":"<<value.ticks<<'}';
}
void interval_json(std::ostream& out,pikapika::interval::Interval value) {
    out<<'[';number(out,value.lower());out<<',';number(out,value.upper());out<<']';
}
void validate_binding(const g::BindingInfo& value) {
    enum_range(value.mode,g::BindingMode::source_enforced);
    enum_range(value.state,g::BindingState::ready);
    bool terminated=false;
    for(char ch:value.build_id) {
        if(ch=='\0') {terminated=true;}
        else {
            require(!terminated&&((ch>='0'&&ch<='9')||(ch>='a'&&ch<='f')),"Invalid owned binding ID");
        }
    }
    require(terminated,"Unterminated owned binding ID");
}
void validate_location(const p::FailureLocation& value) {enum_range(value.kind,p::ObjectKind::face);}
void validate_mesh(const mesh::Result& value) {
    enum_range(value.status,mesh::Status::unsupported_environment);enum_range(value.reason,mesh::Reason::environment);
    for(const auto& row:value.rows) {
        if(!row.query) {continue;}
        const auto& q=*row.query;
        enum_range(q.status,single::Status::unsupported_environment);enum_range(q.reason,single::Reason::environment);
        if(q.geometry) {enum_range(q.geometry->relation,single::Relation::boundary_unresolved);}
        for(const auto& c:q.candidates) {
            enum_range(c.feature,single::Feature::vertex_c);enum_range(c.disposition,single::Disposition::kkt_violated);
        }
    }
}
void validate_held(const held::Result& value) {
    enum_range(value.status,held::Status::numerical_failure);enum_range(value.reason,held::Reason::derived_domain);
    for(const auto& a:value.audits) {
        enum_range(a.kind,held::AuditKind::cell);enum_range(a.outcome,held::Outcome::unresolved);
        if(a.mesh_status) {enum_range(*a.mesh_status,mesh::Status::unsupported_environment);}
        if(a.mesh_reason) {enum_range(*a.mesh_reason,mesh::Reason::environment);}
    }
    for(const auto& leaf:value.partition) {
        enum_range(leaf.state,held::LeafState::current);enum_range(leaf.blocked_reason,held::Reason::derived_domain);
    }
    if(value.last_mesh) {validate_mesh(*value.last_mesh);}
}
void validate_child(const flight::Result& value) {
    enum_range(value.status,flight::Status::numerical_failure);enum_range(value.reason,flight::Reason::coverage_inconsistent);
    if(value.flight_failure) {enum_range(*value.flight_failure,d::CcdFailure::numerical_failure);}
    if(value.inflated) {validate_held(*value.inflated);}
}
template<class Coverage> void validate_child(const Coverage& value) {
    using S=std::remove_cvref_t<decltype(value.status)>;
    using R=std::remove_cvref_t<decltype(value.reason)>;
    enum_range(value.status,S::unsupported_environment);enum_range(value.reason,R::coverage_inconsistent);
    for(const auto& a:value.audits) {
        using O=std::remove_cvref_t<decltype(a.outcome)>;
        enum_range(a.outcome,O::blocked);enum_range(a.blocked_reason,R::coverage_inconsistent);
    }
    for(const auto& leaf:value.partition) {
        using L=std::remove_cvref_t<decltype(leaf.state)>;
        enum_range(leaf.state,L::current);enum_range(leaf.blocked_reason,R::coverage_inconsistent);
    }
}
template<class Call> void validate_call(const Call& call) {
    enum_range(call.state,g::CallState::nonreturned);
    if(call.result) {validate_child(*call.result);}
}
void validate_guard(const g::GuardResult& value) {
    enum_range(value.status,g::Status::numerical_failure);enum_range(value.reason,g::Reason::environment);validate_binding(value.binding);
    if(value.failure&&value.failure->preparation) {validate_location(*value.failure->preparation);}
    if(value.preparation) {
        const auto& prep=*value.preparation;
        enum_range(prep.status,p::Status::numerical_failure);enum_range(prep.reason,p::Reason::unexpected_exception);
        enum_range(prep.capture,p::CaptureState::complete);
        if(prep.failure) {validate_location(*prep.failure);}
        if(prep.inventory) {
            for(const auto& pair:prep.inventory->pairs) {
                enum_range(pair.kind,p::PairKind::body_body);
                enum_range(pair.first.kind,p::ColliderKind::mesh);enum_range(pair.second.kind,p::ColliderKind::mesh);
            }
        }
    }
    for(const auto& body:value.bodies) {enum_range(body.state,g::SeedState::unexamined);}
    for(const auto& pair:value.pairs) {
        enum_range(pair.state,g::PairState::dependency_failed);enum_range(pair.reason,g::Reason::environment);
        require(!pair.child.valueless_by_exception(),"Valueless child variant");
        std::visit([](const auto& child) {
            using C=std::remove_cvref_t<decltype(child)>;
            if constexpr(std::is_same_v<C,g::PlaneCalls>) {validate_call(child.metric);validate_call(child.box);}
            else {validate_call(child);}
        },pair.child);
    }
}

// Older nested writers use std::cout internally. Give them the same classic
// locale/precision/format as the destination; restore all changed cout state.
class CoutFormat {
    std::ios::fmtflags flags_=std::cout.flags();
    std::streamsize precision_=std::cout.precision();
    std::locale locale_=std::cout.getloc();
public:
    CoutFormat() {
        std::cout.imbue(std::locale::classic());std::cout.flags(std::ios::dec);
        std::cout.precision(std::numeric_limits<double>::max_digits10);
    }
    ~CoutFormat() noexcept {
        try {std::cout.flags(flags_);std::cout.precision(precision_);std::cout.imbue(locale_);} catch(...) {}
    }
    CoutFormat(const CoutFormat&)=delete;
    CoutFormat& operator=(const CoutFormat&)=delete;
};
template<class Writer> std::string capture(Writer writer) {
    std::ostringstream out;out.imbue(std::locale::classic());
    out.exceptions(std::ios::badbit|std::ios::failbit);
    out<<std::setprecision(std::numeric_limits<double>::max_digits10);
    writer(out);return out.str();
}

// Independent structural check of the completed writer output. This is a JSON
// grammar/finite-number gate, NOT an independent physics or transaction proof.
class JsonSyntax {
    std::string_view text_;
    std::size_t offset_{};
    void whitespace() {
        while(offset_<text_.size()&&(text_[offset_]==' '||text_[offset_]=='\n'||text_[offset_]=='\r'||text_[offset_]=='\t')) {++offset_;}
    }
    bool consume(char ch) {
        whitespace();
        if(offset_<text_.size()&&text_[offset_]==ch) {++offset_;return true;}
        return false;
    }
    void expect(char ch) {require(consume(ch),"Invalid completed transaction JSON punctuation");}
    static bool digit(char ch) noexcept {return ch>='0'&&ch<='9';}
    void string() {
        expect('"');bool closed=false;
        while(offset_<text_.size()) {
            const auto ch=static_cast<unsigned char>(text_[offset_++]);
            if(ch=='"') {closed=true;break;}
            require(ch>=0x20U,"Unescaped transaction JSON control byte");
            if(ch!='\\') {continue;}
            require(offset_<text_.size(),"Incomplete transaction JSON escape");
            const char escaped=text_[offset_++];
            if(escaped=='u') {
                for(unsigned j=0;j<4;++j) {
                    require(offset_<text_.size(),"Incomplete transaction JSON unicode escape");
                    const char h=text_[offset_++];
                    require(digit(h)||(h>='a'&&h<='f')||(h>='A'&&h<='F'),"Invalid transaction JSON unicode escape");
                }
            } else {
                require(escaped=='"'||escaped=='\\'||escaped=='/'||escaped=='b'||escaped=='f'||escaped=='n'||escaped=='r'||escaped=='t',
                        "Invalid transaction JSON escape");
            }
        }
        require(closed,"Unterminated transaction JSON string");
    }
    void numeric() {
        const auto start=offset_;
        if(offset_<text_.size()&&text_[offset_]=='-') {++offset_;}
        require(offset_<text_.size(),"Incomplete transaction JSON number");
        if(text_[offset_]=='0') {++offset_;}
        else {
            require(text_[offset_]>='1'&&text_[offset_]<='9',"Invalid transaction JSON integer");
            while(offset_<text_.size()&&digit(text_[offset_])) {++offset_;}
        }
        if(offset_<text_.size()&&text_[offset_]=='.') {
            ++offset_;const auto fraction=offset_;
            while(offset_<text_.size()&&digit(text_[offset_])) {++offset_;}
            require(offset_>fraction,"Missing transaction JSON fraction");
        }
        if(offset_<text_.size()&&(text_[offset_]=='e'||text_[offset_]=='E')) {
            ++offset_;
            if(offset_<text_.size()&&(text_[offset_]=='+'||text_[offset_]=='-')) {++offset_;}
            const auto exponent=offset_;
            while(offset_<text_.size()&&digit(text_[offset_])) {++offset_;}
            require(offset_>exponent,"Missing transaction JSON exponent");
        }
        double parsed{};
        const auto conversion=std::from_chars(text_.data()+start,text_.data()+offset_,parsed,std::chars_format::general);
        require(conversion.ec==std::errc{}&&conversion.ptr==text_.data()+offset_&&std::isfinite(parsed),
                "Nonfinite or unrepresentable completed transaction JSON number");
    }
    void value(unsigned depth) {
        require(depth<=128,"Excessive transaction JSON nesting");whitespace();
        require(offset_<text_.size(),"Missing transaction JSON value");
        if(text_[offset_]=='{') {
            ++offset_;if(consume('}')) {return;}
            do {string();expect(':');value(depth+1);} while(consume(','));
            expect('}');return;
        }
        if(text_[offset_]=='[') {
            ++offset_;if(consume(']')) {return;}
            do {value(depth+1);} while(consume(','));
            expect(']');return;
        }
        if(text_[offset_]=='"') {string();return;}
        for(std::string_view literal:{"true","false","null"}) {
            if(text_.substr(offset_,literal.size())==literal) {offset_+=literal.size();return;}
        }
        numeric();
    }
public:
    explicit JsonSyntax(std::string_view text):text_(text) {}
    void check() {value(0);whitespace();require(offset_==text_.size(),"Trailing transaction JSON data");}
};
void vector_bits(Bits& out,pikapika::Vec3 value) {
    out.push_back(bits(value.x));out.push_back(bits(value.y));out.push_back(bits(value.z));
}
Bits source_bits(const std::vector<g::StaticMeshSource>& sources) {
    Bits out{static_cast<std::uint64_t>(sources.size())};
    for(const auto& m:sources) {
        out.push_back(m.id);out.push_back(m.revision);out.push_back(static_cast<std::uint64_t>(m.triangles.size()));
        for(const auto& t:m.triangles) {out.push_back(t.id);for(const auto& v:t.vertices) {vector_bits(out,v);}}
    }
    return out;
}
Bits plane_bits(const d::World& world) {
    Bits out{static_cast<std::uint64_t>(world.planes().size())};
    for(const auto& plane:world.planes()) {
        out.push_back(plane.id);vector_bits(out,plane.normal);out.push_back(bits(plane.offset));
        out.push_back(bits(plane.material.restitution));out.push_back(bits(plane.material.friction));
    }
    return out;
}
Bits gravity_bits(const d::World& world) {Bits out;vector_bits(out,world.gravity);return out;}

struct Pointers {
    const d::RigidBody* body_data{};
    const d::Plane* plane_data{};
    const g::StaticMeshSource* mesh_data{};
    std::vector<const d::RigidBody*> bodies,lookups;
    std::vector<std::uint64_t> ids;
    std::vector<const single::StaticTriangle*> faces;
    explicit Pointers(const world_guard_fixture::Case& input):body_data(input.world.bodies().data()),
        plane_data(input.world.planes().data()),mesh_data(input.meshes.data()) {
        for(const auto& body:input.world.bodies()) {bodies.push_back(&body);ids.push_back(body.id);lookups.push_back(input.world.find_body(body.id));}
        for(const auto& m:input.meshes) {faces.push_back(m.triangles.data());}
    }
    void json(std::ostream& out,const world_guard_fixture::Case& after) const {
        out<<"{\"bodyCountUnchanged\":";flag(out,bodies.size()==after.world.bodies().size());
        out<<",\"bodyStorageStable\":";flag(out,body_data==after.world.bodies().data());
        out<<",\"planeStorageStable\":";flag(out,plane_data==after.world.planes().data());
        out<<",\"meshStorageStable\":";flag(out,mesh_data==after.meshes.data());
        out<<",\"bodies\":[";
        for(std::size_t i=0;i<bodies.size();++i) {
            if(i) {out<<',';}
            const auto* lookup=after.world.find_body(ids[i]);
            out<<"{\"ordinal\":"<<i<<",\"originalId\":"<<ids[i]<<",\"sameOrdinalAddress\":";
            flag(out,i<after.world.bodies().size()&&bodies[i]==&after.world.bodies()[i]);
            out<<",\"sameLookupResult\":";flag(out,lookups[i]==lookup);
            out<<",\"lookupBeforeMatchesOrdinal\":";flag(out,lookups[i]==bodies[i]);
            out<<",\"lookupAfterMatchesOrdinal\":";flag(out,i<after.world.bodies().size()&&lookup==&after.world.bodies()[i]);out<<'}';
        }
        out<<"],\"meshFaceStorageStable\":[";
        for(std::size_t i=0;i<faces.size();++i) {
            if(i) {out<<',';}
            flag(out,i<after.meshes.size()&&faces[i]==after.meshes[i].triangles.data());
        }
        out<<"]}";
    }
};
void transaction_json(std::ostream& out,const world_guard_fixture::Case& original) {
    // Copy the SOURCE, never a previous report. Address observations are taken
    // from this live transaction, not from the separate original/corpus copy.
    auto input=original;
    advance::Progress progress{initial_time,initial_ticks};const auto before_progress=progress;
    const Pointers pointers(input);
    const auto before_input=capture([&](auto& stream){world_guard_fixture::input_json(stream,input);});
    const auto before_world=capture([&](auto& stream){world_guard_fixture::world_json(stream,input.world);});
    const auto before_settings=capture([&](auto& stream){world_guard_fixture::settings_json(stream,input.settings);});
    const auto before_sources=source_bits(input.meshes),before_planes=plane_bits(input.world),before_gravity=gravity_bits(input.world);
    const auto before_horizon=bits(input.horizon);
    const auto report=advance::advance(input.world,input.meshes,input.horizon,input.settings,progress); // ONE call.
    require(report.advance_profile_checked&&report.advance_profile_matches,
            "Full transaction corpus requires the matching configured advance profile; no refusal substitution");
    const auto after_input=capture([&](auto& stream){world_guard_fixture::input_json(stream,input);});
    const auto after_world=capture([&](auto& stream){world_guard_fixture::world_json(stream,input.world);});
    const auto after_settings=capture([&](auto& stream){world_guard_fixture::settings_json(stream,input.settings);});
    out<<"{\"name\":";quoted(out,original.name);out<<",\"input\":"<<before_input<<",\"inputAfter\":"<<after_input;
    out<<",\"worldBefore\":"<<before_world<<",\"worldAfter\":"<<after_world<<",\"progressBefore\":";
    progress_json(out,before_progress);out<<",\"progressAfter\":";progress_json(out,progress);
    out<<",\"report\":";report_json(out,report);
    out<<",\"observations\":{\"captureComplete\":true,\"advanceCalls\":1,\"sourceUnchanged\":";
    flag(out,before_sources==source_bits(input.meshes));out<<",\"settingsUnchanged\":";flag(out,before_settings==after_settings);
    out<<",\"horizonUnchanged\":";flag(out,before_horizon==bits(input.horizon));
    out<<",\"planesUnchanged\":";flag(out,before_planes==plane_bits(input.world));
    out<<",\"gravityUnchanged\":";flag(out,before_gravity==gravity_bits(input.world));
    out<<",\"worldUnchanged\":";flag(out,before_world==after_world);
    const bool clock_same=bits(before_progress.time)==bits(progress.time)&&before_progress.ticks==progress.ticks;
    out<<",\"progressUnchanged\":";flag(out,clock_same);
    out<<",\"failureAtomicObserved\":";
    if(report.committed) {out<<"null";} else {flag(out,before_world==after_world&&clock_same);}
    out<<",\"pointerStability\":";pointers.json(out,input);out<<"}}";
}
}

void report_json(std::ostream& out,const advance::AdvanceReport& report) {
    // Range checks precede every legacy enum-indexing writer. This does not
    // replace the independent mathematical/transaction checker to be added.
    const auto* s=status(report.status);const auto* r=reason(report.reason);validate_binding(report.binding);
    if(report.guard) {validate_guard(*report.guard);}
    out<<"{\"status\":";quoted(out,s);out<<",\"reason\":";quoted(out,r);
    out<<",\"committed\":";flag(out,report.committed);out<<",\"requestedDt\":";number(out,report.requested_dt);
    out<<",\"advancedDt\":";number(out,report.advanced_dt);out<<",\"originalProgress\":";progress_json(out,report.original_progress);
    out<<",\"proposedProgress\":";if(report.proposed_progress) {progress_json(out,*report.proposed_progress);} else {out<<"null";}
    out<<",\"clock\":";
    if(report.clock) {
        out<<"{\"timeSum\":";interval_json(out,report.clock->time_sum);
        out<<",\"representedDifference\":";interval_json(out,report.clock->represented_difference);
        out<<",\"sumRoundingError\":";interval_json(out,report.clock->sum_rounding_error);
        out<<",\"representedDt\":";number(out,report.clock->represented_dt);out<<'}';
    } else {out<<"null";}
    out<<",\"binding\":";world_guard_fixture::binding_json(out,report.binding);
    out<<",\"advanceProfileChecked\":";flag(out,report.advance_profile_checked);
    out<<",\"advanceProfileMatches\":";flag(out,report.advance_profile_matches);
    out<<",\"failure\":";
    if(report.failure) {
        out<<"{\"stage\":";quoted(out,stage(report.failure->stage));out<<",\"object\":";
        if(report.failure->object) {
            const auto& location=*report.failure->object;
            out<<"{\"kind\":";quoted(out,kind(location.kind));out<<",\"index\":";index(out,location.index);
            out<<",\"faceIndex\":";index(out,location.face_index);out<<'}';
        } else {out<<"null";}
        out<<'}';
    } else {out<<"null";}
    out<<",\"guard\":";if(report.guard) {world_guard_fixture::result_json(out,*report.guard);} else {out<<"null";}
    // The existing guard writer intentionally omits GuardResult.message. Keep
    // that ACTUAL outer message separately; stripped child text is not rebuilt.
    out<<",\"guardMessage\":";if(report.guard) {quoted(out,report.guard->message);} else {out<<"null";}
    const auto& w=report.work;
    out<<",\"work\":{\"guardQueriesAttempted\":"<<w.guard_queries_attempted<<",\"guardQueriesReturned\":"<<w.guard_queries_returned;
    out<<",\"pairRecordsChecked\":"<<w.pair_records_checked<<",\"callRecordsChecked\":"<<w.call_records_checked;
    out<<",\"originBodiesChecked\":"<<w.origin_bodies_checked<<",\"originPlanesChecked\":"<<w.origin_planes_checked;
    out<<",\"originMeshesChecked\":"<<w.origin_meshes_checked<<",\"originFacesChecked\":"<<w.origin_faces_checked;
    out<<",\"candidatesCopied\":"<<w.candidates_copied<<",\"candidateValidationsAttempted\":"<<w.candidate_validations_attempted;
    out<<",\"candidatesValidated\":"<<w.candidates_validated<<",\"destinationLookups\":"<<w.destination_lookups;
    out<<",\"destinationsResolved\":"<<w.destinations_resolved<<",\"bodyAssignments\":"<<w.body_assignments;
    out<<",\"progressAssignments\":"<<w.progress_assignments<<'}';
    const auto& storage=report.storage;
    out<<",\"storage\":{\"bodyBufferSlots\":"<<storage.body_buffer_slots<<",\"destinationSlots\":"<<storage.destination_slots;
    out<<",\"bodyBufferSizeofBytes\":"<<storage.body_buffer_sizeof_bytes<<",\"destinationBufferSizeofBytes\":"<<storage.destination_buffer_sizeof_bytes<<'}';
    out<<",\"message\":";quoted(out,report.message);out<<'}';
}

void emit_fixtures(std::ostream& output) {
    const CoutFormat cout_format;
    const auto corpus=world_guard_fixture::cases();
    require(corpus.size()==51,"Expected original complete guard51 corpus");
    const auto document=capture([&](auto& out) {
        out<<"{\"schema\":1,\"kind\":\"world-static-mesh-flight-advance-transaction-fixtures\",\"scope\":";
        quoted(out,"Actual one-call transactions; no independent mathematical checker or complete machine clock/commit proof is asserted by this serializer.");
        out<<",\"initialProgress\":";progress_json(out,{initial_time,initial_ticks});
        out<<",\"layoutSizes\":";world_guard_fixture::layout_sizes_json(out);
        out<<",\"advanceLayoutSizes\":{\"AdvanceReport\":"<<sizeof(advance::AdvanceReport)<<",\"Progress\":"<<sizeof(advance::Progress);
        out<<",\"ClockAudit\":"<<sizeof(advance::ClockAudit)<<",\"CommitWork\":"<<sizeof(advance::CommitWork)<<",\"CommitStorage\":"<<sizeof(advance::CommitStorage)<<'}';
        out<<",\"fixtures\":[";
        for(std::size_t i=0;i<corpus.size();++i) {if(i) {out<<',';}transaction_json(out,corpus[i]);}
        out<<"]}\n";
    });
    // All captures and serializations have completed before the first output
    // byte. A failed write still exits nonzero; consumers must check exit status.
    JsonSyntax(document).check();
    require(document.size()<=static_cast<std::size_t>(std::numeric_limits<std::streamsize>::max()),"Transaction JSON exceeds output stream size");
    output.write(document.data(),static_cast<std::streamsize>(document.size()));
    require(static_cast<bool>(output),"Transaction fixture output failure");
}
}

int main(int argc,char** argv) {
    try {
        if(argc!=2||std::string_view(argv[1])!="--fixtures") {
            std::cerr<<"Usage: world_static_mesh_flight_advance_fixtures --fixtures\n";return 2;
        }
        world_advance_fixture::emit_fixtures(std::cout);return 0;
    } catch(const std::exception& error) {
        std::cerr<<"Advance transaction fixture serialization failed: "<<error.what()<<'\n';return 1;
    } catch(...) {
        std::cerr<<"Advance transaction fixture serialization failed: unknown exception\n";return 1;
    }
}
