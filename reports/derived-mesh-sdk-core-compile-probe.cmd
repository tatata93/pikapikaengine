@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /permissive- /Icore/include tools/derived_mesh_probe.cpp "C:\Users\tak01\github\pikapikaengine\pikapikaengine\build\derived-mesh-sdk\dependency-core.lib" /Fe"C:\Users\tak01\github\pikapikaengine\pikapikaengine\build\derived-mesh-sdk\run-ab0vhb2y\pikapika-derived-probe.exe" /Fo"C:\Users\tak01\github\pikapikaengine\pikapikaengine\build\derived-mesh-sdk\run-ab0vhb2y\compile-probe/" /link /INCREMENTAL:NO
