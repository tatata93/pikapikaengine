@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/interval.cpp /Fobuild/polarized-route-proof/interval.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/optical_bounds.cpp /Fobuild/polarized-route-proof/optical_bounds.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/optical_route.cpp /Fobuild/polarized-route-proof/optical_route.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/polarized_route.cpp /Fobuild/polarized-route-proof/polarized_route.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include tests/polarized_route_tests.cpp /Fobuild/polarized-route-proof/tests.obj build/polarized-route-proof/interval.obj build/polarized-route-proof/optical_bounds.obj build/polarized-route-proof/optical_route.obj build/polarized-route-proof/polarized_route.obj /Febuild/polarized-route-proof/polarized-tests.exe

