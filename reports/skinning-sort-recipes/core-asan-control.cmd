@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++20 /EHsc /MD /O2 /Zi /fsanitize=address build/skinning-sort/asan-control.cpp /Febuild/skinning-sort/asan-control.exe /Fobuild/skinning-sort/ /Fdbuild/skinning-sort/asan-control.pdb /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
build\skinning-sort\asan-control.exe
exit /b %errorlevel%
