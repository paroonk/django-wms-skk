Set WinScriptHost = CreateObject("WScript.Shell")
WinScriptHost.Run Chr(34) & "C:\Users\SCG\PycharmProjects\django-wms\mysite\runserver.bat" & Chr(34), 0
Set WinScriptHost = Nothing