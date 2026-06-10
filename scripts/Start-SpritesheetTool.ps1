param(
    [switch] $PreflightOnly
)

$ErrorActionPreference = "Stop"

$scriptPath = $PSCommandPath
if (-not $scriptPath) {
    $scriptPath = $MyInvocation.MyCommand.Path
}

$scriptDir = Split-Path -Parent $scriptPath
$projectRoot = Split-Path -Parent $scriptDir
$backendPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendDir = Join-Path $projectRoot "frontend"
$nodeModulesDir = Join-Path $frontendDir "node_modules"
$npmCommand = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
$hostName = "127.0.0.1"
$backendPort = 8765
$frontendPort = 5173
$toolUrl = "http://${hostName}:$frontendPort"
$backendProcess = $null
$frontendProcess = $null
$startupSucceeded = $false
$logDir = Join-Path $env:TEMP "SpritesheetTool"
$backendOutLog = Join-Path $logDir "backend.out.log"
$backendErrLog = Join-Path $logDir "backend.err.log"
$frontendOutLog = Join-Path $logDir "frontend.out.log"
$frontendErrLog = Join-Path $logDir "frontend.err.log"

function Write-SetupError {
    param(
        [string] $Message,
        [string[]] $Commands = @()
    )

    Write-Host ""
    Write-Host $Message -ForegroundColor Red

    if ($Commands.Count -gt 0) {
        Write-Host ""
        Write-Host "建议修复方式:" -ForegroundColor Yellow
        foreach ($command in $Commands) {
            Write-Host "  $command"
        }
    }

    Write-Host ""
    if (-not $PreflightOnly) {
        Read-Host "按 Enter 关闭"
    }
    exit 1
}

function Stop-ProcessTree {
    param([int] $ProcessId)

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTree -ProcessId $child.ProcessId
    }

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Test-PortAvailable {
    param(
        [string] $HostName,
        [int] $Port
    )

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $asyncResult = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $asyncResult.AsyncWaitHandle.WaitOne(500)) {
            return $true
        }

        try {
            $client.EndConnect($asyncResult)
            return $false
        }
        catch {
            return $true
        }
    }
    finally {
        $client.Close()
    }
}

function Wait-ForUrl {
    param(
        [string] $Url,
        [int] $TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 1 | Out-Null
            return $true
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    return $false
}

function Test-UrlAvailable {
    param([string] $Url)

    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Open-ExistingTool {
    if (Test-UrlAvailable -Url $toolUrl) {
        if ($PreflightOnly) {
            Write-Host "工具已在运行。"
            exit 0
        }

        Start-Process $toolUrl
        Write-Host ""
        Write-Host "SpriteSheet 工具已在运行，已打开页面。" -ForegroundColor Green
        Write-Host "前端: $toolUrl"
        Write-Host ""
        Read-Host "按 Enter 关闭此窗口"
        exit 0
    }
}

function Stop-StartedServers {
    if ($backendProcess) {
        Stop-ProcessTree -ProcessId $backendProcess.Id
    }

    if ($frontendProcess) {
        Stop-ProcessTree -ProcessId $frontendProcess.Id
    }
}

function Reset-Logs {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Remove-Item -LiteralPath $backendOutLog, $backendErrLog, $frontendOutLog, $frontendErrLog -ErrorAction SilentlyContinue
}

function Write-StartupLogs {
    Write-Host ""
    Write-Host "启动日志:" -ForegroundColor Yellow
    foreach ($logPath in @($backendOutLog, $backendErrLog, $frontendOutLog, $frontendErrLog)) {
        Write-Host "  $logPath"
        if (Test-Path -LiteralPath $logPath) {
            $content = Get-Content -LiteralPath $logPath -Raw -ErrorAction SilentlyContinue
            if ($content) {
                Write-Host $content
            }
        }
    }
}

function New-EncodedPowerShellArgs {
    param([string] $Command)

    $encodedCommand = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($Command))
    return @(
        "-NoExit",
        "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", $encodedCommand
    )
}

if (-not (Test-Path -LiteralPath $backendPython)) {
    Write-SetupError "缺少后端 Python 环境: $backendPython" @(
        "cd `"$projectRoot`"",
        "python -m venv .venv",
        ".\.venv\Scripts\python -m pip install -e .\backend[dev]"
    )
}

if (-not $npmCommand) {
    Write-SetupError "PATH 中找不到 npm。请先安装 Node.js，然后安装前端依赖。" @(
        "cd `"$frontendDir`"",
        "npm install"
    )
}

& $backendPython -c "import uvicorn, fastapi" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-SetupError "虚拟环境中缺少后端依赖。" @(
        "cd `"$projectRoot`"",
        ".\.venv\Scripts\python -m pip install -e .\backend[dev]"
    )
}

if (-not (Test-Path -LiteralPath $nodeModulesDir)) {
    Write-SetupError "缺少前端依赖: $nodeModulesDir" @(
        "cd `"$frontendDir`"",
        "npm install"
    )
}

if (-not (Test-PortAvailable -HostName $hostName -Port $backendPort)) {
    Open-ExistingTool
    Write-SetupError "后端端口 $backendPort 已被占用。请停止占用该端口的进程后重新启动。"
}

if (-not (Test-PortAvailable -HostName $hostName -Port $frontendPort)) {
    Open-ExistingTool
    Write-SetupError "前端端口 $frontendPort 已被占用。请停止占用该端口的进程后重新启动。"
}

if ($PreflightOnly) {
    Write-Host "预检通过。"
    exit 0
}

Set-Location -LiteralPath $projectRoot

$escapedProjectRoot = $projectRoot.Replace("'", "''")
$escapedFrontendDir = $frontendDir.Replace("'", "''")
$escapedBackendPython = $backendPython.Replace("'", "''")
$escapedNpmCommand = $npmCommand.Replace("'", "''")

$backendCommand = @"
Set-Location -LiteralPath '$escapedProjectRoot'
& '$escapedBackendPython' -m uvicorn app.main:app --app-dir backend --host $hostName --port $backendPort
"@

$frontendCommand = @"
Set-Location -LiteralPath '$escapedFrontendDir'
& '$escapedNpmCommand' run dev -- --host $hostName --port $frontendPort --strictPort
"@

$backendArgs = New-EncodedPowerShellArgs $backendCommand
$frontendArgs = New-EncodedPowerShellArgs $frontendCommand

try {
    Write-Host "正在启动 SpriteSheet 工具..." -ForegroundColor Cyan
    Write-Host "项目路径: $projectRoot"
    Reset-Logs

    $backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $backendArgs -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $backendOutLog -RedirectStandardError $backendErrLog -PassThru
    $frontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList $frontendArgs -WorkingDirectory $frontendDir -WindowStyle Hidden -RedirectStandardOutput $frontendOutLog -RedirectStandardError $frontendErrLog -PassThru

    Write-Host "正在等待前端响应: $toolUrl ..."
    if (-not (Wait-ForUrl -Url $toolUrl -TimeoutSeconds 30)) {
        Write-StartupLogs
        throw "前端在 30 秒内未响应: $toolUrl。启动已停止。"
    }

    Start-Process $toolUrl
    $startupSucceeded = $true

    Write-Host ""
    Write-Host "SpriteSheet 工具正在运行。" -ForegroundColor Green
    Write-Host "后端:  http://127.0.0.1:$backendPort"
    Write-Host "前端: $toolUrl"
    Write-Host "日志: $logDir"
    Write-Host ""
    Write-Host "停止方式:" -ForegroundColor Yellow
    Write-Host "  在此启动器窗口按 Enter 停止两个服务。"
    Write-Host ""

    Read-Host "按 Enter 停止 SpriteSheet 工具"
}
catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "正在停止已启动的服务进程..." -ForegroundColor Yellow
    Stop-StartedServers
    Read-Host "按 Enter 关闭"
}
finally {
    if ($startupSucceeded) {
        Write-Host "正在停止服务..."
    }

    Stop-StartedServers

    if ($startupSucceeded) {
        Write-Host "已停止。"
    }
}
