@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Icore/include core/src/skinning.cpp core/src/motion.cpp tests/skinning_tests.cpp /Febuild/skinning-proof/skinning-native.exe /Fobuild/skinning-proof/ /link /INCREMENTAL:NO
exit /b %errorlevel%
