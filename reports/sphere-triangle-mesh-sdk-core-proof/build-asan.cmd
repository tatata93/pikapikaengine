@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /Zi /fsanitize=address /W4 /fp:strict /Icore/include /c core/src/simulation_api.cpp /Fobuild\sphere-triangle-mesh-sdk-core\asan\simulation_api.obj /Fdbuild\sphere-triangle-mesh-sdk-core\asan\api.pdb
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /Zi /fsanitize=address /W4 /fp:strict /Icore/include tests/sphere_triangle_mesh_sdk_tests.cpp build\sphere-triangle-mesh-sdk-core\asan\simulation_api.obj build\sphere-triangle-mesh-sdk-core\frozen-core.lib /Febuild\sphere-triangle-mesh-sdk-core\asan\mesh-sdk-tests.exe /Fobuild\sphere-triangle-mesh-sdk-core\asan\tests.obj /Fdbuild\sphere-triangle-mesh-sdk-core\asan\tests.pdb /link /INCREMENTAL:NO
