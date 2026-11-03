@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/interval.cpp /Fobuild/polarized-packet-proof/interval.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/optical_bounds.cpp /Fobuild/polarized-packet-proof/optical_bounds.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/optical_route.cpp /Fobuild/polarized-packet-proof/optical_route.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/polarized_route.cpp /Fobuild/polarized-packet-proof/polarized_route.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/polarized_packet.cpp /Fobuild/polarized-packet-proof/polarized_packet.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include tests/polarized_packet_tests.cpp /Fobuild/polarized-packet-proof/tests.obj build/polarized-packet-proof/interval.obj build/polarized-packet-proof/optical_bounds.obj build/polarized-packet-proof/optical_route.obj build/polarized-packet-proof/polarized_route.obj build/polarized-packet-proof/polarized_packet.obj /Febuild/polarized-packet-proof/packet-tests.exe


