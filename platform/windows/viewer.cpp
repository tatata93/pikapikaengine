#include <windows.h>
#include <d3d12.h>
#include <dxgi1_6.h>
#include <d3dcompiler.h>
#include <wrl/client.h>
#include <shellapi.h>
#include "pikapika/core.hpp"
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstring>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#ifdef _MSC_VER
#include <intrin.h>
#endif

using Microsoft::WRL::ComPtr;
namespace {
std::string utf8(const wchar_t* value) {
    const int size=WideCharToMultiByte(CP_UTF8,0,value,-1,nullptr,0,nullptr,nullptr);
    if(size<=1) return {};
    std::string output(std::size_t(size),'\0');
    WideCharToMultiByte(CP_UTF8,0,value,-1,output.data(),size,nullptr,nullptr);output.pop_back();return output;
}
std::string json_string(const std::string& value) {
    std::ostringstream output; output<<'"';
    for(unsigned char c:value) {
        if(c=='"'||c=='\\') output<<'\\'<<char(c);
        else if(c<32) output<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<unsigned(c)<<std::dec;
        else output<<char(c);
    }
    output<<'"';return output.str();
}
std::string timestamp_utc() {
    SYSTEMTIME time{};GetSystemTime(&time);
    std::ostringstream output;output<<std::setfill('0')<<std::setw(4)<<time.wYear<<'-'<<std::setw(2)<<time.wMonth
        <<'-'<<std::setw(2)<<time.wDay<<'T'<<std::setw(2)<<time.wHour<<':'<<std::setw(2)<<time.wMinute
        <<':'<<std::setw(2)<<time.wSecond<<'.'<<std::setw(3)<<time.wMilliseconds<<'Z';return output.str();
}
void write_environment(std::ostream& output) {
    MEMORYSTATUSEX memory{};memory.dwLength=sizeof(memory);const bool memory_available=GlobalMemoryStatusEx(&memory)!=FALSE;
    SYSTEM_INFO system{};GetNativeSystemInfo(&system);
    std::string brand="unavailable";
#ifdef _MSC_VER
    int registers[4]{};__cpuid(registers,int(0x80000000U));
    if(static_cast<unsigned>(registers[0])>=0x80000004U) {
        char text[49]{};
        for(unsigned i=0;i<3;++i) {__cpuid(registers,int(0x80000002U+i));std::memcpy(text+i*16,registers,16);}
        brand=text;
    }
#endif
    output<<",\"cpu_brand\":"<<json_string(brand)<<",\"logical_processors\":"<<system.dwNumberOfProcessors
          <<",\"physical_ram_bytes\":";
    if(memory_available)output<<memory.ullTotalPhys;else output<<"null";
    using VersionFunction=LONG(WINAPI*)(OSVERSIONINFOW*);
    const auto version_function=reinterpret_cast<VersionFunction>(GetProcAddress(GetModuleHandleW(L"ntdll.dll"),"RtlGetVersion"));
    OSVERSIONINFOW version{};version.dwOSVersionInfoSize=sizeof(version);
    output<<",\"os_version\":";
    if(version_function&&version_function(&version)==0) {
        output<<json_string("Windows "+std::to_string(version.dwMajorVersion)+'.'+std::to_string(version.dwMinorVersion)+'.'+std::to_string(version.dwBuildNumber));
    } else output<<"null";
}
void checked(HRESULT hr,const char* what) {
    if(FAILED(hr)) throw std::runtime_error(std::string(what)+" HRESULT="+std::to_string(static_cast<unsigned long>(hr)));
}
struct Vertex { float x,y,z,r,g,b; };
LRESULT CALLBACK window_proc(HWND window,UINT message,WPARAM wparam,LPARAM lparam) {
    if(message==WM_DESTROY) { PostQuitMessage(0); return 0; }
    if(message==WM_KEYDOWN&&wparam==VK_ESCAPE) { DestroyWindow(window); return 0; }
    return DefWindowProc(window,message,wparam,lparam);
}
void box(std::vector<Vertex>& vertices,const pikapika::Transform& transform,pikapika::Vec3 half,
         std::array<float,3> color) {
    const std::array<pikapika::Vec3,8> points={{{-half.x,-half.y,-half.z},{half.x,-half.y,-half.z},
        {half.x,half.y,-half.z},{-half.x,half.y,-half.z},{-half.x,-half.y,half.z},
        {half.x,-half.y,half.z},{half.x,half.y,half.z},{-half.x,half.y,half.z}}};
    const int faces[6][6]={{0,2,1,0,3,2},{4,5,6,4,6,7},{0,4,7,0,7,3},
                         {1,2,6,1,6,5},{3,7,6,3,6,2},{0,1,5,0,5,4}};
    const float light[6]={0.6f,0.8f,0.45f,0.9f,1.f,0.3f};
    for(int f=0;f<6;++f) for(int i:faces[f]) {
        const auto p=transform.apply(points[i]);
        vertices.push_back({float(p.x),float(p.y),float(p.z),color[0]*light[f],color[1]*light[f],color[2]*light[f]});
    }
}
const char* shader=R"(
cbuffer View : register(b0) { float4 camera; float4 projection; };
struct Input { float3 position:POSITION; float3 color:COLOR; };
struct Output { float4 position:SV_POSITION; float3 color:COLOR; };
Output vs(Input v) {
  float3 r=v.position-camera.xyz;
  float sn=sin(camera.w), cs=cos(camera.w);
  float x=r.x*cs-r.z*sn, z=-r.x*sn-r.z*cs;
  float py=r.y*cos(projection.w)-z*sin(projection.w);
  float pz=r.y*sin(projection.w)+z*cos(projection.w);
  Output o;
  o.position=float4(x/projection.x,py/projection.y,projection.z*pz-0.10001,pz);
  o.color=v.color; return o;
}
float4 ps(Output v):SV_TARGET {
  float3 mapped=v.color/(1+v.color);
  return float4(pow(saturate(mapped),1.0/2.2),1);
}
)";
struct Viewer {
    static constexpr UINT width=1280,height=720;
    HWND window{};
    ComPtr<ID3D12Device> device;
    ComPtr<ID3D12CommandQueue> queue;
    ComPtr<IDXGISwapChain3> swapchain;
    ComPtr<ID3D12DescriptorHeap> rtv_heap,dsv_heap;
    ComPtr<ID3D12Resource> targets[2],depth,vertex_buffer;
    ComPtr<ID3D12CommandAllocator> allocator;
    ComPtr<ID3D12GraphicsCommandList> commands;
    ComPtr<ID3D12RootSignature> root_signature;
    ComPtr<ID3D12PipelineState> pipeline;
    ComPtr<ID3D12Fence> fence;
    HANDLE event_handle{};
    UINT rtv_size{},vertex_count{},geometry_count{};
    UINT64 fence_value{};
    D3D12_VERTEX_BUFFER_VIEW vertex_view{};
    pikapika::Vec3 camera{0,5,18};
    double yaw{},pitch{-0.15};
    bool warp{};
    DXGI_ADAPTER_DESC1 adapter_description{};
    ~Viewer() { if(event_handle) CloseHandle(event_handle); if(window&&IsWindow(window)) DestroyWindow(window); }
    void initialize(HINSTANCE instance,bool smoke,const pikapika::Scene& scene) {
        WNDCLASS wc{}; wc.lpfnWndProc=window_proc; wc.hInstance=instance; wc.lpszClassName=L"PikapikaDX12";
        wc.hCursor=LoadCursor(nullptr,IDC_ARROW); RegisterClass(&wc);
        RECT rect{0,0,LONG(width),LONG(height)}; AdjustWindowRect(&rect,WS_OVERLAPPEDWINDOW,FALSE);
        window=CreateWindow(wc.lpszClassName,L"pikapikaengine | DirectX 12 | WASD move, Q/E turn, arrows look, Esc exit",
            WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,rect.right-rect.left,rect.bottom-rect.top,
            nullptr,nullptr,instance,nullptr);
        if(!window) throw std::runtime_error("CreateWindow failed");
        ComPtr<IDXGIFactory4> factory; checked(CreateDXGIFactory1(IID_PPV_ARGS(&factory)),"DXGI factory");
        HRESULT result=D3D12CreateDevice(nullptr,D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device));
        if(FAILED(result)) {
            ComPtr<IDXGIAdapter> adapter; checked(factory->EnumWarpAdapter(IID_PPV_ARGS(&adapter)),"WARP adapter");
            checked(D3D12CreateDevice(adapter.Get(),D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device)),"D3D12 WARP device"); warp=true;
        }
        ComPtr<IDXGIAdapter1> selected_adapter;
        checked(factory->EnumAdapterByLuid(device->GetAdapterLuid(),IID_PPV_ARGS(&selected_adapter)),"selected adapter lookup");
        checked(selected_adapter->GetDesc1(&adapter_description),"selected adapter description");
        D3D12_COMMAND_QUEUE_DESC q{}; q.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;
        checked(device->CreateCommandQueue(&q,IID_PPV_ARGS(&queue)),"command queue");
        DXGI_SWAP_CHAIN_DESC1 swap{}; swap.Width=width; swap.Height=height; swap.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
        swap.SampleDesc.Count=1; swap.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT; swap.BufferCount=2;
        swap.SwapEffect=DXGI_SWAP_EFFECT_FLIP_DISCARD;
        ComPtr<IDXGISwapChain1> original;
        checked(factory->CreateSwapChainForHwnd(queue.Get(),window,&swap,nullptr,nullptr,&original),"swapchain");
        checked(original.As(&swapchain),"swapchain interface");
        factory->MakeWindowAssociation(window,DXGI_MWA_NO_ALT_ENTER);
        D3D12_DESCRIPTOR_HEAP_DESC heap{}; heap.NumDescriptors=2; heap.Type=D3D12_DESCRIPTOR_HEAP_TYPE_RTV;
        checked(device->CreateDescriptorHeap(&heap,IID_PPV_ARGS(&rtv_heap)),"RTV heap");
        rtv_size=device->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);
        auto handle=rtv_heap->GetCPUDescriptorHandleForHeapStart();
        for(UINT i=0;i<2;++i) {
            checked(swapchain->GetBuffer(i,IID_PPV_ARGS(&targets[i])),"swapchain buffer");
            device->CreateRenderTargetView(targets[i].Get(),nullptr,handle); handle.ptr+=rtv_size;
        }
        heap.NumDescriptors=1; heap.Type=D3D12_DESCRIPTOR_HEAP_TYPE_DSV;
        checked(device->CreateDescriptorHeap(&heap,IID_PPV_ARGS(&dsv_heap)),"DSV heap");
        D3D12_HEAP_PROPERTIES memory{}; memory.Type=D3D12_HEAP_TYPE_DEFAULT;
        D3D12_RESOURCE_DESC resource{}; resource.Dimension=D3D12_RESOURCE_DIMENSION_TEXTURE2D;
        resource.Width=width; resource.Height=height; resource.DepthOrArraySize=1; resource.MipLevels=1;
        resource.Format=DXGI_FORMAT_D32_FLOAT; resource.SampleDesc.Count=1; resource.Flags=D3D12_RESOURCE_FLAG_ALLOW_DEPTH_STENCIL;
        D3D12_CLEAR_VALUE clear{}; clear.Format=DXGI_FORMAT_D32_FLOAT; clear.DepthStencil.Depth=1;
        checked(device->CreateCommittedResource(&memory,D3D12_HEAP_FLAG_NONE,&resource,D3D12_RESOURCE_STATE_DEPTH_WRITE,&clear,IID_PPV_ARGS(&depth)),"depth texture");
        device->CreateDepthStencilView(depth.Get(),nullptr,dsv_heap->GetCPUDescriptorHandleForHeapStart());
        D3D12_ROOT_PARAMETER parameter{}; parameter.ParameterType=D3D12_ROOT_PARAMETER_TYPE_32BIT_CONSTANTS;
        parameter.Constants.Num32BitValues=8; parameter.Constants.ShaderRegister=0;
        parameter.ShaderVisibility=D3D12_SHADER_VISIBILITY_VERTEX;
        D3D12_ROOT_SIGNATURE_DESC signature{}; signature.NumParameters=1; signature.pParameters=&parameter;
        signature.Flags=D3D12_ROOT_SIGNATURE_FLAG_ALLOW_INPUT_ASSEMBLER_INPUT_LAYOUT;
        ComPtr<ID3DBlob> serialized,error;
        checked(D3D12SerializeRootSignature(&signature,D3D_ROOT_SIGNATURE_VERSION_1,&serialized,&error),"root serialization");
        checked(device->CreateRootSignature(0,serialized->GetBufferPointer(),serialized->GetBufferSize(),IID_PPV_ARGS(&root_signature)),"root signature");
        ComPtr<ID3DBlob> vertex_shader,pixel_shader;
        const auto compile=[&](const char* entry,const char* target,ComPtr<ID3DBlob>& output) {
            const HRESULT hr=D3DCompile(shader,std::strlen(shader),"pikapika-native",nullptr,nullptr,entry,target,D3DCOMPILE_ENABLE_STRICTNESS,0,&output,&error);
            if(FAILED(hr)&&error) throw std::runtime_error(std::string("shader compile: ")+static_cast<const char*>(error->GetBufferPointer()));
            checked(hr,"shader compilation");
        };
        compile("vs","vs_5_0",vertex_shader); compile("ps","ps_5_0",pixel_shader);
        D3D12_INPUT_ELEMENT_DESC input[]={{"POSITION",0,DXGI_FORMAT_R32G32B32_FLOAT,0,0,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0},
            {"COLOR",0,DXGI_FORMAT_R32G32B32_FLOAT,0,12,D3D12_INPUT_CLASSIFICATION_PER_VERTEX_DATA,0}};
        D3D12_GRAPHICS_PIPELINE_STATE_DESC state{}; state.pRootSignature=root_signature.Get();
        state.VS={vertex_shader->GetBufferPointer(),vertex_shader->GetBufferSize()};
        state.PS={pixel_shader->GetBufferPointer(),pixel_shader->GetBufferSize()}; state.InputLayout={input,2};
        state.RasterizerState.FillMode=D3D12_FILL_MODE_SOLID; state.RasterizerState.CullMode=D3D12_CULL_MODE_NONE;
        state.RasterizerState.DepthClipEnable=TRUE;
        state.BlendState.RenderTarget[0].RenderTargetWriteMask=D3D12_COLOR_WRITE_ENABLE_ALL;
        state.DepthStencilState.DepthEnable=TRUE; state.DepthStencilState.DepthWriteMask=D3D12_DEPTH_WRITE_MASK_ALL;
        state.DepthStencilState.DepthFunc=D3D12_COMPARISON_FUNC_LESS;
        state.SampleMask=UINT_MAX; state.PrimitiveTopologyType=D3D12_PRIMITIVE_TOPOLOGY_TYPE_TRIANGLE;
        state.NumRenderTargets=1; state.RTVFormats[0]=DXGI_FORMAT_R8G8B8A8_UNORM; state.DSVFormat=DXGI_FORMAT_D32_FLOAT;
        state.SampleDesc.Count=1;
        checked(device->CreateGraphicsPipelineState(&state,IID_PPV_ARGS(&pipeline)),"graphics pipeline");
        std::vector<Vertex> vertices;
        bool camera_found=false;
        for(const auto& entity:scene.entities) {
            if(entity.type=="camera") {
                if(!camera_found) {
                    camera=entity.transform.position;
                    const auto forward=entity.transform.rotation.rotate({0,0,-1});
                    yaw=std::atan2(-forward.x,-forward.z); pitch=std::asin(std::clamp(forward.y,-1.0,1.0));
                    camera_found=true;
                }
                continue;
            }
            if(entity.type=="source"||entity.type=="listener") continue;
            ++geometry_count;
            if(entity.type=="robot") {
                box(vertices,entity.transform,{0.8,1.4,0.5},{0.06f,1.2f,1.5f});
                auto head=entity.transform; head.position=head.position+head.rotation.rotate({0,1.8,0});
                box(vertices,head,{0.45,0.35,0.4},{1.5f,0.6f,0.08f});
            } else box(vertices,entity.transform,entity.type=="plane"?pikapika::Vec3{0.5,0.01,0.5}:pikapika::Vec3{0.5,0.5,0.5},
                entity.type=="plane"?std::array<float,3>{0.08f,0.12f,0.2f}:std::array<float,3>{0.7f,0.2f,0.12f});
        }
        if(vertices.empty()) throw std::runtime_error("scene has no drawable entities");
        vertex_count=UINT(vertices.size()); memory.Type=D3D12_HEAP_TYPE_UPLOAD;
        resource={}; resource.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER; resource.Width=vertices.size()*sizeof(Vertex);
        resource.Height=1; resource.DepthOrArraySize=1; resource.MipLevels=1; resource.SampleDesc.Count=1;
        resource.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
        checked(device->CreateCommittedResource(&memory,D3D12_HEAP_FLAG_NONE,&resource,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&vertex_buffer)),"vertex buffer");
        void* mapped{}; D3D12_RANGE empty{0,0}; checked(vertex_buffer->Map(0,&empty,&mapped),"vertex mapping");
        std::memcpy(mapped,vertices.data(),vertices.size()*sizeof(Vertex)); vertex_buffer->Unmap(0,nullptr);
        vertex_view={vertex_buffer->GetGPUVirtualAddress(),UINT(vertices.size()*sizeof(Vertex)),sizeof(Vertex)};
        checked(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator)),"command allocator");
        checked(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),pipeline.Get(),IID_PPV_ARGS(&commands)),"command list");
        checked(commands->Close(),"initial command close");
        checked(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)),"frame fence");
        event_handle=CreateEvent(nullptr,FALSE,FALSE,nullptr); if(!event_handle) throw std::runtime_error("CreateEvent failed");
        if(!smoke) ShowWindow(window,SW_SHOW);
    }
    void wait_gpu() {
        ++fence_value; checked(queue->Signal(fence.Get(),fence_value),"queue signal");
        if(fence->GetCompletedValue()<fence_value) {
            checked(fence->SetEventOnCompletion(fence_value,event_handle),"fence event");
            if(WaitForSingleObject(event_handle,10000)!=WAIT_OBJECT_0) throw std::runtime_error("GPU frame timeout");
        }
    }
    void update(double dt) {
        if(GetForegroundWindow()!=window) return;
        const auto down=[](int key){return (GetAsyncKeyState(key)&0x8000)!=0;};
        yaw+=(int(down('Q'))-int(down('E')))*dt;
        pitch+=(int(down(VK_UP))-int(down(VK_DOWN)))*dt;
        pitch=std::clamp(pitch,-1.1,1.1);
        const double f=int(down('W'))-int(down('S')),r=int(down('D'))-int(down('A'));
        const double speed=down(VK_SHIFT)?30:10;
        camera=camera+pikapika::Vec3{r*std::cos(yaw)-f*std::sin(yaw),0,-r*std::sin(yaw)-f*std::cos(yaw)}*(dt*speed);
    }
    void draw(bool capture=false) {
        checked(allocator->Reset(),"allocator reset"); checked(commands->Reset(allocator.Get(),pipeline.Get()),"command reset");
        const UINT index=swapchain->GetCurrentBackBufferIndex();
        D3D12_RESOURCE_BARRIER barrier{}; barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
        barrier.Transition.pResource=targets[index].Get(); barrier.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
        barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_PRESENT; barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_RENDER_TARGET;
        commands->ResourceBarrier(1,&barrier);
        auto target=rtv_heap->GetCPUDescriptorHandleForHeapStart(); target.ptr+=SIZE_T(index)*rtv_size;
        const auto depth_view=dsv_heap->GetCPUDescriptorHandleForHeapStart();
        commands->OMSetRenderTargets(1,&target,FALSE,&depth_view);
        const float clear[]={0.012f,0.025f,0.055f,1}; commands->ClearRenderTargetView(target,clear,0,nullptr);
        commands->ClearDepthStencilView(depth_view,D3D12_CLEAR_FLAG_DEPTH,1,0,0,nullptr);
        const D3D12_VIEWPORT viewport{0,0,float(width),float(height),0,1}; const D3D12_RECT scissor{0,0,LONG(width),LONG(height)};
        commands->RSSetViewports(1,&viewport); commands->RSSetScissorRects(1,&scissor);
        commands->SetGraphicsRootSignature(root_signature.Get());
        const float constants[]={float(camera.x),float(camera.y),float(camera.z),float(yaw),
            float(width)/height*0.577350269f,0.577350269f,1000.f/999.9f,float(pitch)};
        commands->SetGraphicsRoot32BitConstants(0,8,constants,0);
        commands->IASetPrimitiveTopology(D3D_PRIMITIVE_TOPOLOGY_TRIANGLELIST); commands->IASetVertexBuffers(0,1,&vertex_view);
        commands->DrawInstanced(vertex_count,1,0,0);
        ComPtr<ID3D12Resource> readback;
        D3D12_PLACED_SUBRESOURCE_FOOTPRINT footprint{};
        if(capture) {
            const auto texture=targets[index]->GetDesc(); UINT64 bytes{};
            device->GetCopyableFootprints(&texture,0,1,0,&footprint,nullptr,nullptr,&bytes);
            D3D12_HEAP_PROPERTIES memory{}; memory.Type=D3D12_HEAP_TYPE_READBACK;
            D3D12_RESOURCE_DESC buffer{}; buffer.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;
            buffer.Width=bytes; buffer.Height=1; buffer.DepthOrArraySize=1; buffer.MipLevels=1;
            buffer.SampleDesc.Count=1; buffer.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
            checked(device->CreateCommittedResource(&memory,D3D12_HEAP_FLAG_NONE,&buffer,D3D12_RESOURCE_STATE_COPY_DEST,nullptr,IID_PPV_ARGS(&readback)),"capture buffer");
            barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_RENDER_TARGET; barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_COPY_SOURCE;
            commands->ResourceBarrier(1,&barrier);
            D3D12_TEXTURE_COPY_LOCATION source{}; source.pResource=targets[index].Get(); source.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
            D3D12_TEXTURE_COPY_LOCATION destination{}; destination.pResource=readback.Get(); destination.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
            destination.PlacedFootprint=footprint;
            commands->CopyTextureRegion(&destination,0,0,0,&source,nullptr);
            barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_COPY_SOURCE;
        } else barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_RENDER_TARGET;
        barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_PRESENT; commands->ResourceBarrier(1,&barrier);
        checked(commands->Close(),"command close"); ID3D12CommandList* lists[]={commands.Get()}; queue->ExecuteCommandLists(1,lists);
        checked(swapchain->Present(1,0),"present"); wait_gpu();
        if(capture) {
            unsigned char* pixels{}; checked(readback->Map(0,nullptr,reinterpret_cast<void**>(&pixels)),"capture map");
            BITMAPFILEHEADER file{}; file.bfType=0x4d42; file.bfOffBits=sizeof(file)+sizeof(BITMAPINFOHEADER);
            file.bfSize=file.bfOffBits+width*height*4;
            BITMAPINFOHEADER info{}; info.biSize=sizeof(info); info.biWidth=width; info.biHeight=-LONG(height);
            info.biPlanes=1; info.biBitCount=32; info.biCompression=BI_RGB; info.biSizeImage=width*height*4;
            std::ofstream image("native-smoke.bmp",std::ios::binary);
            image.write(reinterpret_cast<const char*>(&file),sizeof(file)); image.write(reinterpret_cast<const char*>(&info),sizeof(info));
            for(UINT y=0;y<height;++y) for(UINT x=0;x<width;++x) {
                const auto p=pixels+footprint.Offset+SIZE_T(y)*footprint.Footprint.RowPitch+x*4;
                const char bgra[]={char(p[2]),char(p[1]),char(p[0]),char(p[3])}; image.write(bgra,4);
            }
            readback->Unmap(0,nullptr); if(!image) throw std::runtime_error("capture write failed");
        }
    }
};
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR,int) {
    bool smoke=false;
    try {
        int argument_count=0; auto* arguments=CommandLineToArgvW(GetCommandLineW(),&argument_count);
        if(!arguments) throw std::runtime_error("argument parsing failed");
        std::vector<std::wstring> options;
        for(int i=1;i<argument_count;++i) options.emplace_back(arguments[i]); LocalFree(arguments);
        std::filesystem::path scene_path;
        for(std::size_t i=0;i<options.size();++i) {
            if(options[i]==L"--smoke-test") smoke=true;
            else if(options[i]==L"--scene"&&i+1<options.size()) scene_path=options[++i];
            else throw std::runtime_error("usage: pikapika-viewer [--smoke-test] [--scene scene-path]");
        }
        pikapika::Scene scene;
        // Default content uses the same Scene API and units as the CLI/browser.
        scene.entities={{1,"robot","Player",{{0,1.5,0},{},{1,1,1}},1},
                        {2,"box","Target",{{0,1,-20},{},{2,2,2}},2},
                        {3,"plane","Ground",{{0,0,0},{},{100,1,100}},0},
                        {4,"camera","Main camera",{{0,18,65},{},{1,1,1}},0},
                        {5,"source","Direct sound source",{{-20,5,-10},{},{1,1,1}},0},
                        {6,"listener","Direct sound listener",{{0,5,30},{},{1,1,1}},0}};
        if(!scene_path.empty()) {
            std::ifstream input(scene_path); if(!input) throw std::runtime_error("cannot open scene"); scene=pikapika::Scene::load(input);
        }
        Viewer viewer; viewer.initialize(instance,smoke,scene); pikapika::FixedClock clock;
        std::vector<double> intervals,submission_times;
        auto previous=std::chrono::steady_clock::now(); unsigned frames=0; bool running=true;
        while(running) {
            MSG message{}; while(PeekMessage(&message,nullptr,0,0,PM_REMOVE)) {
                if(message.message==WM_QUIT) running=false; TranslateMessage(&message); DispatchMessage(&message);
            }
            if(!running) break;
            const auto now=std::chrono::steady_clock::now(); const double elapsed=std::chrono::duration<double>(now-previous).count(); previous=now;
            clock.advance(elapsed,[&](double dt){viewer.update(dt);});
            const auto before_draw=std::chrono::steady_clock::now(); viewer.draw(smoke&&frames==119);
            const auto after_draw=std::chrono::steady_clock::now();
            if(smoke) {
                intervals.push_back(elapsed*1000);
                submission_times.push_back(std::chrono::duration<double,std::milli>(after_draw-before_draw).count());
            }
            ++frames;
            if(smoke&&frames>=120) running=false;
        }
        viewer.wait_gpu();
        if(smoke) {
            if(intervals.empty()) throw std::runtime_error("smoke test ended before any frame was submitted");
            std::ofstream raw("native-frames.csv"); raw<<"frame,loop_interval_ms,submit_present_wait_ms\n";
            for(std::size_t i=0;i<intervals.size();++i) raw<<i<<','<<intervals[i]<<','<<submission_times[i]<<'\n';
            auto sorted=intervals; std::sort(sorted.begin(),sorted.end());
            const auto percentile=[&](double p){return sorted[std::size_t(std::ceil(p*sorted.size()))-1];};
            const auto over=std::count_if(intervals.begin(),intervals.end(),[](double t){return t>1000./60;});
            std::ofstream report("native-smoke.json");
            report<<"{\"backend\":\"DirectX12\",\"timestamp_utc\":"<<json_string(timestamp_utc())
                <<",\"code_revision_base\":"<<json_string(PIKAPIKA_CODE_REVISION_BASE)
                <<",\"worktree_dirty_at_configure\":"<<(PIKAPIKA_WORKTREE_DIRTY?"true":"false")
                <<",\"viewer_source_sha256\":"<<json_string(PIKAPIKA_VIEWER_SOURCE_SHA256)
                <<",\"core_source_sha256\":"<<json_string(PIKAPIKA_CORE_SOURCE_SHA256)
                <<",\"adapter_description\":"<<json_string(utf8(viewer.adapter_description.Description))
                <<",\"adapter_vendor_id\":"<<viewer.adapter_description.VendorId<<",\"adapter_device_id\":"<<viewer.adapter_description.DeviceId
                <<",\"dedicated_video_memory_bytes\":"<<viewer.adapter_description.DedicatedVideoMemory
                <<",\"shared_system_memory_bytes\":"<<viewer.adapter_description.SharedSystemMemory
                <<",\"target_width\":"<<Viewer::width<<",\"target_height\":"<<Viewer::height
                <<",\"smoke_window_visible\":false,\"frames_submitted\":"<<frames<<",\"warp\":"<<(viewer.warp?"true":"false")
                <<",\"geometry_entities\":"<<viewer.geometry_count<<",\"camera_m\":["<<viewer.camera.x<<','<<viewer.camera.y<<','<<viewer.camera.z<<']'
                <<",\"fixed_ticks\":"<<clock.ticks()<<",\"dropped_seconds\":"<<clock.dropped_seconds()
                <<",\"loop_interval_p50_ms\":"<<percentile(0.5)<<",\"loop_interval_p95_ms\":"<<percentile(0.95)
                <<",\"loop_interval_p99_ms\":"<<percentile(0.99)<<",\"loop_interval_max_ms\":"<<sorted.back()
                <<",\"loop_intervals_over_16_67ms\":"<<over
                <<",\"gpu_time_ms\":null,\"display_60fps_verified\":false";
            write_environment(report); report<<"}\n";
        }
        return 0;
    } catch(const std::exception& error) {
        if(smoke) { std::ofstream report("native-smoke-error.txt"); report<<error.what()<<'\n'; }
        else MessageBoxA(nullptr,error.what(),"pikapikaengine DirectX 12 startup failed",MB_OK|MB_ICONERROR);
        return 1;
    }
}
