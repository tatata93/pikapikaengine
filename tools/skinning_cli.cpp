#include "pikapika/skinning_io.hpp"
#include <cerrno>
#include <charconv>
#include <cmath>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <system_error>
#include <fcntl.h>
#include <sys/stat.h>
#ifdef _WIN32
#include <io.h>
#else
#include <unistd.h>
#endif
namespace {
namespace io=pikapika::skinning_io;
double number(const char* text){const std::string s(text);double x{};const char* first=s.data()+(s.starts_with('+')?1:0);const auto r=std::from_chars(first,s.data()+s.size(),x,std::chars_format::general);if(r.ec!=std::errc{}||r.ptr!=s.data()+s.size()||!std::isfinite(x))throw std::invalid_argument("Expected finite decimal");if(x==0)for(char c:s){if(c=='e'||c=='E')break;if(c>='1'&&c<='9')throw std::invalid_argument("Nonzero decimal underflows to zero");}return x;}
std::size_t index(const char* text){const double x=number(text);if(x<0||x>=2048||std::floor(x)!=x)throw std::invalid_argument("Expected vertex index0..2047");return std::size_t(x);}
std::uint64_t id(const char* text){const double x=number(text);if(x<1||x>9007199254740991.||std::floor(x)!=x)throw std::invalid_argument("Expected exact bone ID");return std::uint64_t(x);}
io::Source load(const char* path){std::ifstream in(std::filesystem::path(path),std::ios::binary);if(!in)throw std::runtime_error("Cannot open skin source");return io::Source::load(in);}
void save_new(const io::Source&source,const char* filename){
    std::ostringstream candidate;source.save(candidate);const auto text=candidate.str();const std::filesystem::path path(filename);
#ifdef _WIN32
    const int fd=_wopen(path.c_str(),_O_WRONLY|_O_CREAT|_O_EXCL|_O_BINARY,_S_IREAD|_S_IWRITE);
#else
    const int fd=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL,0600);
#endif
    if(fd<0)throw std::system_error(errno,std::generic_category(),"Skin output must be a new exclusively created file");
#ifdef _WIN32
    std::FILE* file=_fdopen(fd,"wb");
#else
    std::FILE* file=fdopen(fd,"wb");
#endif
    if(!file){const int error=errno;
#ifdef _WIN32
        _close(fd);
#else
        ::close(fd);
#endif
        std::error_code ignored;std::filesystem::remove(path,ignored);throw std::system_error(error,std::generic_category(),"Cannot open skin output stream");}
    const bool written=std::fwrite(text.data(),1,text.size(),file)==text.size();const int closed=std::fclose(file);if(!written||closed!=0){std::error_code ignored;std::filesystem::remove(path,ignored);throw std::runtime_error("Cannot finish skin output; new partial file removed when possible");}
}
void num(double x){if(!std::isfinite(x))throw std::runtime_error("Nonfinite skin JSON output");if(x==0&&std::signbit(x))std::cout<<"-0";else std::cout<<x;}
void inspect(const io::Source&s){std::cout<<"{\"version\":1,\"kind\":\"mesh-skin-binding\",\"name\":"<<std::quoted(s.name)<<",\"objectId\":"<<std::quoted(s.target.object_id)<<",\"nativeId\":"<<std::quoted(s.target.native_id)<<",\"fingerprint\":"<<std::quoted(s.fingerprint)<<",\"vertices\":"<<s.mesh.positions.size()<<",\"triangles\":"<<s.mesh.triangles.size()<<",\"joints\":"<<s.joints.size()<<",\"restBones\":"<<s.rest_bones.size()<<",\"structurallyValid\":true,\"evaluationNotImplied\":true}\n";}
void sample(const pikapika::skinning::DeformResult&r){const char* names[]{"completed","invalid_input","budget_exceeded","ill_conditioned","numerical_failure"};std::cout<<"{\"status\":"<<std::quoted(names[int(r.status)])<<",\"positions\":";
    if(r.positions){std::cout<<'[';for(std::size_t j=0;j<r.positions->size();++j){if(j)std::cout<<',';const auto p=(*r.positions)[j];std::cout<<'[';num(p.x);std::cout<<',';num(p.y);std::cout<<',';num(p.z);std::cout<<']';}std::cout<<']';}else std::cout<<"null";
    std::cout<<",\"diagnostics\":[";for(std::size_t j=0;j<r.inverse_diagnostics.size();++j){if(j)std::cout<<',';const auto&d=r.inverse_diagnostics[j];std::cout<<"{\"id\":"<<d.bone_id<<",\"condition\":";if(d.linear_condition)num(*d.linear_condition);else std::cout<<"null";std::cout<<",\"residual\":";if(d.inverse_residual)num(*d.inverse_residual);else std::cout<<"null";std::cout<<",\"pivotFailure\":"<<(d.pivot_failure?"true":"false")<<'}';}std::cout<<"],\"weightResiduals\":[";for(std::size_t j=0;j<r.weight_residuals.size();++j){if(j)std::cout<<',';num(r.weight_residuals[j]);}std::cout<<"]}\n";
}
}
int main(int argc,char**argv){try{
    std::cout<<std::setprecision(std::numeric_limits<double>::max_digits10);const std::string command=argc>1?argv[1]:"help";
    if(command=="help"){std::cout<<"pikapika-skin init newfile\npikapika-skin inspect file\npikapika-skin roundtrip in newout\npikapika-skin weight in newout vertex boneId weight\npikapika-skin sample file seconds [loop]\npikapika-skin match file scene\n";return 0;}
    if(command=="init"&&argc==3){save_new(io::example(),argv[2]);return 0;}
    if(command=="inspect"&&argc==3){inspect(load(argv[2]));return 0;}
    if(command=="roundtrip"&&argc==4){save_new(load(argv[2]),argv[3]);return 0;}
    if(command=="weight"&&argc==7){auto source=load(argv[2]);source.set_weight(index(argv[4]),id(argv[5]),number(argv[6]));save_new(source,argv[3]);return 0;}
    if(command=="sample"&&(argc==4||argc==5)){if(argc==5&&std::string(argv[4])!="loop")throw std::invalid_argument("Optional playback argument must be loop");sample(load(argv[2]).sample(number(argv[3]),argc==5?pikapika::motion::Playback::loop:pikapika::motion::Playback::clamp));return 0;}
    if(command=="match"&&argc==4){const auto source=load(argv[2]);std::ifstream in(std::filesystem::path(argv[3]),std::ios::binary);if(!in)throw std::runtime_error("Cannot open scene context");source.match(pikapika::Scene::load(in));std::cout<<"{\"matches\":true,\"nativeId\":"<<std::quoted(source.target.native_id)<<",\"browserAliasNotInterpreted\":true}\n";return 0;}
    throw std::invalid_argument("Invalid skin command; run help");
}catch(const std::exception&e){std::cerr<<"ERROR "<<e.what()<<'\n';return 1;}}
