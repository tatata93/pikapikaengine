@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /W4 /fp:strict /Zi /fsanitize=address /Icore/include build/skinning-sort/before-skinning.cpp core/src/motion.cpp tests/skinning_tests.cpp /Febuild\skinning-sort\asan-before/skinning.exe /Fobuild\skinning-sort\asan-before/ /Fdbuild\skinning-sort\asan-before/skinning.pdb /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
build\skinning-sort\asan-before\skinning.exe
exit /b %errorlevel%
