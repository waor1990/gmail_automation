@echo off
setlocal EnableExtensions
pushd "%~dp0" >nul
call scripts\setup.cmd %*
popd >nul
