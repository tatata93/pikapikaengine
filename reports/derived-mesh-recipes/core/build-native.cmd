@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include core/src/interval.cpp core/src/derived_mesh.cpp tests/derived_mesh_tests.cpp /Febuild\derived-mesh-core\derived-mesh-tests.exe /Fobuild\derived-mesh-core\ /link /INCREMENTAL:NO
