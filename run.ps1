[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,

    [int]$MaxOrders,

    [string]$Config = ".\automation_config.json",

    [string]$LogLevel = "INFO"
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    throw "Nao foi encontrado o Python do ambiente virtual em $python. Execute a criacao da venv antes de usar este script."
}

$argsList = @(
    '-m', 'src.main',
    '--output-dir', $OutputDir,
    '--config', $Config,
    '--log-level', $LogLevel
)

if ($PSBoundParameters.ContainsKey('MaxOrders')) {
    $argsList += @('--max-orders', $MaxOrders)
}

Push-Location $projectRoot
try {
    & $python @argsList
} finally {
    Pop-Location
}
