' 띵조 AI 실행 (콘솔창 없이). 이 파일 더블클릭 = 네이티브 창만 뜸.
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = root & "\backend"
' 0 = 창 숨김, False = 기다리지 않음
sh.Run "uv run desktop.py", 0, False
