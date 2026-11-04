@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/simulation_api.cpp /Fobuild\sphere-triangle-mesh-sdk-core\simulation_api.obj
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include tests/sphere_triangle_mesh_sdk_tests.cpp build\sphere-triangle-mesh-sdk-core\simulation_api.obj build\sphere-triangle-mesh-sdk-core\frozen-core.lib /Febuild\sphere-triangle-mesh-sdk-core\mesh-sdk-tests.exe /Fobuild\sphere-triangle-mesh-sdk-core\mesh-sdk-tests.obj /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include tools/sphere_triangle_mesh_sdk_probe.cpp build\sphere-triangle-mesh-sdk-core\simulation_api.obj build\sphere-triangle-mesh-sdk-core\frozen-core.lib /Febuild\sphere-triangle-mesh-sdk-core\mesh-sdk-probe.exe /Fobuild\sphere-triangle-mesh-sdk-core\mesh-sdk-probe.obj /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include tests/simulation_api_tests.cpp build\sphere-triangle-mesh-sdk-core\simulation_api.obj build\sphere-triangle-mesh-sdk-core\frozen-core.lib /Febuild\sphere-triangle-mesh-sdk-core\existing-api-tests.exe /Fobuild\sphere-triangle-mesh-sdk-core\existing-api-tests.obj /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
