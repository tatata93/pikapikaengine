@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include /c core/src/motion.cpp /Fobuild/motion-proof/motion.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include tests/motion_tests.cpp /Fobuild/motion-proof/tests.obj build/motion-proof/motion.obj /Febuild/motion-proof/motion-tests.exe
