$ErrorActionPreference = "Stop"

$scriptPath = $PSCommandPath
if (-not $scriptPath) {
    $scriptPath = $MyInvocation.MyCommand.Path
}

$scriptDir = Split-Path -Parent $scriptPath
$projectRoot = Split-Path -Parent $scriptDir
$launcherPath = Join-Path $scriptDir "Start-SpritesheetTool.ps1"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutName = "Spritesheet $([char]0x5DE5)$([char]0x5177).lnk"
$shortcutPath = Join-Path $desktopPath $shortcutName
$powerShellPath = Join-Path $PSHOME "powershell.exe"

if (-not (Test-Path -LiteralPath $launcherPath)) {
    throw "找不到启动脚本: $launcherPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $powerShellPath
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$launcherPath`""
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = "$powerShellPath,0"
$shortcut.Description = "启动本地 SpriteSheet 工具"
$shortcut.Save()

Write-Host "已创建桌面快捷方式:"
Write-Host "  $shortcutPath"
