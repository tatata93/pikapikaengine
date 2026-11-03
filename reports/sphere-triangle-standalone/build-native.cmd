@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include core/src/interval.cpp core/src/sphere_triangle.cpp tests/sphere_triangle_tests.cpp /Febuild\sphere-triangle-core\sphere-triangle-tests.exe /Fobuild\sphere-triangle-core\ /link /INCREMENTAL:NO
