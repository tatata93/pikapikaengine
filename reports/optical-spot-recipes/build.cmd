@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/interval.cpp /Fobuild/optical-spot-proof/interval.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/optical_bounds.cpp /Fobuild/optical-spot-proof/optical_bounds.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/optical_route.cpp /Fobuild/optical-spot-proof/optical_route.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/optical_spot.cpp /Fobuild/optical-spot-proof/optical_spot.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include tests/optical_spot_tests.cpp /Fobuild/optical-spot-proof/tests.obj build/optical-spot-proof/interval.obj build/optical-spot-proof/optical_bounds.obj build/optical-spot-proof/optical_route.obj build/optical-spot-proof/optical_spot.obj /Febuild/optical-spot-proof/spot-tests.exe
