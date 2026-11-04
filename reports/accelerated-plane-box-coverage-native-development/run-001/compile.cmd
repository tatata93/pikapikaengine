@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl.exe @"C:\Users\tak01\github\pikapikaengine\pikapikaengine\reports\accelerated-plane-box-coverage-native-development\run-001\compile.rsp"
exit /b %errorlevel%
