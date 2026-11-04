#pragma once
// Original full diagnostic JSON writers shared only by this new test executable.
#include "pikapika/sphere_triangle_mesh.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
namespace entry_fixture {
namespace mesh=pikapika::sphere_triangle_mesh;
namespace single=pikapika::sphere_triangle;
using pikapika::Vec3;
using I=pikapika::interval::Interval;
inline void require(bool b,const char* message){if(!b)throw std::runtime_error(message);}
inline void number(double x){require(std::isfinite(x),"Nonfinite fixture output");if(x==0&&std::signbit(x))std::cout<<"-0";else std::cout<<x;}
inline void json(I x){std::cout<<'[';number(x.lower());std::cout<<',';number(x.upper());std::cout<<']';}
inline void json(const single::Bounds3&v){std::cout<<'[';for(unsigned i=0;i<3;++i){if(i)std::cout<<',';json(v[i]);}std::cout<<']';}
inline void json(Vec3 v){std::cout<<'[';number(v.x);std::cout<<',';number(v.y);std::cout<<',';number(v.z);std::cout<<']';}
inline void triangle_json(const single::StaticTriangle&t){std::cout<<"{\"id\":"<<t.id<<",\"vertices\":[";for(unsigned i=0;i<3;++i){if(i)std::cout<<',';json(t.vertices[i]);}std::cout<<"]}";}
inline void single_json(const single::Result&r){
    std::cout<<"{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"geometry\":";
    if(r.geometry){const auto&g=*r.geometry;std::cout<<"{\"surfaceId\":"<<g.surface_id<<",\"survivingFeatures\":"<<g.surviving_features<<",\"barycentric\":";json(g.barycentric);std::cout<<",\"closestLocal\":";json(g.closest_local);std::cout<<",\"closest\":";json(g.closest);std::cout<<",\"delta\":";json(g.delta);std::cout<<",\"normal\":";json(g.normal);std::cout<<",\"spherePoint\":";json(g.sphere_point);std::cout<<",\"squaredDistance\":";json(g.squared_distance);std::cout<<",\"distance\":";json(g.distance);std::cout<<",\"gap\":";json(g.gap);std::cout<<",\"relation\":"<<unsigned(g.relation)<<'}';}else std::cout<<"null";
    std::cout<<",\"squaredCross\":";if(r.squared_cross)json(*r.squared_cross);else std::cout<<"null";std::cout<<",\"sineSquared\":";if(r.sine_squared)json(*r.sine_squared);else std::cout<<"null";
    std::cout<<",\"candidates\":[";for(std::size_t i=0;i<r.candidates.size();++i){if(i)std::cout<<',';const auto&c=r.candidates[i];std::cout<<"{\"feature\":"<<unsigned(c.feature)<<",\"disposition\":"<<unsigned(c.disposition)<<",\"barycentric\":";json(c.barycentric);std::cout<<",\"kkt\":[";json(c.kkt[0]);std::cout<<',';json(c.kkt[1]);std::cout<<"],\"kktCount\":"<<c.kkt_count<<'}';}
    std::cout<<"],\"candidatesExamined\":"<<r.candidates_examined<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtRefinementLimited\":"<<(r.sqrt_refinement_limited?"true":"false")<<'}';
}
inline void mesh_json(const mesh::Result& r){
    std::cout<<"{\"status\":"<<unsigned(r.status)<<",\"reason\":"<<unsigned(r.reason)<<",\"failedIndex\":";if(r.failed_index)std::cout<<*r.failed_index;else std::cout<<"null";
    std::cout<<",\"firstFailedRow\":";if(r.first_failed_row)std::cout<<*r.first_failed_row;else std::cout<<"null";
    std::cout<<",\"rows\":[";for(std::size_t j=0;j<r.rows.size();++j){if(j)std::cout<<',';std::cout<<"{\"triangle\":";triangle_json(r.rows[j].triangle);std::cout<<",\"query\":";if(r.rows[j].query)single_json(*r.rows[j].query);else std::cout<<"null";std::cout<<'}';}
    std::cout<<"],\"nearest\":";if(r.nearest){const auto& n=*r.nearest;std::cout<<"{\"squaredDistance\":";json(n.squared_distance);std::cout<<",\"distance\":";json(n.distance);std::cout<<",\"gap\":";json(n.gap);std::cout<<",\"possibleSurfaceIds\":[";for(std::size_t j=0;j<n.possible_surface_ids.size();++j){if(j)std::cout<<',';std::cout<<n.possible_surface_ids[j];}std::cout<<"]}";}else std::cout<<"null";
    std::cout<<",\"queries\":"<<r.queries<<",\"candidatesExamined\":"<<r.candidates_examined<<",\"sqrtRefinements\":"<<r.sqrt_refinements<<",\"sqrtLimitedRows\":"<<r.sqrt_limited_rows<<",\"failedRows\":"<<r.failed_rows<<'}';
}
}
