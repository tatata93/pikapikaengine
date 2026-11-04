@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include core/src/interval.cpp core/src/sphere_triangle.cpp core/src/sphere_triangle_mesh.cpp tests/sphere_triangle_mesh_tests.cpp /Febuild\sphere-triangle-mesh-core\mesh-tests.exe /Fobuild\sphere-triangle-mesh-core\ /link /INCREMENTAL:NO
