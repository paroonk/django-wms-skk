Set WinScriptHost = CreateObject("WScript.Shell")
WinScriptHost.Run Chr(34) & "D:\VSC\django-wms-skk\mysite\runserver.bat" & Chr(34), 0
Set WinScriptHost = Nothing