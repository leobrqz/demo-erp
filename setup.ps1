# Leonardo Briquezi
# github: https://github.com/leobrqz
# linkedin: https://www.linkedin.com/in/leonardobri
[CmdletBinding()]
param(
    [switch]$EnableLocalAI
)

$ErrorActionPreference = "Stop"
$projectDirectory = $PSScriptRoot
$envPath = Join-Path $projectDirectory ".env"
Set-Location -LiteralPath $projectDirectory

function New-RandomSecret {
    param([Parameter(Mandatory)][int]$Length)

    $alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    $bytes = New-Object byte[] $Length
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }

    $builder = New-Object System.Text.StringBuilder
    foreach ($byte in $bytes) {
        [void]$builder.Append($alphabet[[int]$byte % $alphabet.Length])
    }
    return $builder.ToString()
}

function Read-EnvValues {
    param([Parameter(Mandatory)][string]$Path)

    $values = @{}
    if (Test-Path -LiteralPath $Path) {
        foreach ($line in Get-Content -Encoding UTF8 -LiteralPath $Path) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$') {
                $values[$matches[1]] = $matches[2]
            }
        }
    }
    return $values
}

function Write-EnvValues {
    param([Parameter(Mandatory)][hashtable]$Values)

    $databaseUrl = "postgresql+psycopg://$($Values.POSTGRES_USER):$($Values.POSTGRES_PASSWORD)@postgres:5432/$($Values.POSTGRES_DB)"
    $lines = @(
        "APP_ENV=local",
        "POSTGRES_DB=$($Values.POSTGRES_DB)",
        "POSTGRES_USER=$($Values.POSTGRES_USER)",
        "POSTGRES_PASSWORD=$($Values.POSTGRES_PASSWORD)",
        "POSTGRES_VOLUME_NAME=$($Values.POSTGRES_VOLUME_NAME)",
        "REDIS_VOLUME_NAME=$($Values.REDIS_VOLUME_NAME)",
        "MODEL_CACHE_VOLUME_NAME=$($Values.MODEL_CACHE_VOLUME_NAME)",
        "DATABASE_URL=$databaseUrl",
        "REDIS_URL=redis://redis:6379/0",
        "JWT_SECRET_KEY=$($Values.JWT_SECRET_KEY)",
        "JWT_ACCESS_TOKEN_MINUTES=60",
        "ADMIN_USERNAME=$($Values.ADMIN_USERNAME)",
        "ADMIN_PASSWORD=$($Values.ADMIN_PASSWORD)",
        "ADMIN_EMAIL=$($Values.ADMIN_EMAIL)",
        "LOW_STOCK_THRESHOLD=10",
        "AI_PROVIDER=$($Values.AI_PROVIDER)",
        "LLM_BASE_URL=http://model-server:8080/v1",
        "LLM_API_KEY=local-no-auth",
        "LLM_MODEL=MiniCPM5-2B",
        "LLM_MODEL_REPO=openbmb/MiniCPM5-2B-GGUF:Q4_K_M",
        "LLM_CONTEXT_SIZE=4096",
        "LLM_TIMEOUT_SECONDS=60"
    )
    [System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))
}

function Set-EnvValue {
    param(
        [Parameter(Mandatory)][string]$Key,
        [Parameter(Mandatory)][string]$Value
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    $found = $false
    foreach ($line in Get-Content -Encoding UTF8 -LiteralPath $envPath) {
        if ($line -match "^\s*$([regex]::Escape($Key))\s*=") {
            $lines.Add("$Key=$Value")
            $found = $true
        }
        else {
            $lines.Add($line)
        }
    }
    if (-not $found) {
        $lines.Add("$Key=$Value")
    }
    [System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))
}

function Remove-EnvValues {
    param([Parameter(Mandatory)][string[]]$Keys)

    $lines = [System.Collections.Generic.List[string]]::new()
    foreach ($line in Get-Content -Encoding UTF8 -LiteralPath $envPath) {
        $removeLine = $false
        foreach ($key in $Keys) {
            if ($line -match "^\s*$([regex]::Escape($key))\s*=") {
                $removeLine = $true
                break
            }
        }
        if (-not $removeLine) {
            $lines.Add($line)
        }
    }
    [System.IO.File]::WriteAllLines($envPath, $lines, [System.Text.UTF8Encoding]::new($false))
}

function Test-DockerEngine {
    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
        $dockerExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
    return $dockerExitCode -eq 0
}

function Test-DockerVolume {
    param([Parameter(Mandatory)][string]$Name)

    $previousErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & docker volume inspect $Name 2>$null | Out-Null
        $dockerExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
    return $dockerExitCode -eq 0
}

function Stop-LegacyComposeProject {
    param(
        [Parameter(Mandatory)][string]$LegacyProjectName,
        [Parameter(Mandatory)][string]$ProjectDirectory
    )

    $legacyContainers = @(& docker ps -aq --filter "label=com.docker.compose.project=$LegacyProjectName" 2>$null)
    if ($LASTEXITCODE -ne 0 -or $legacyContainers.Count -eq 0) {
        return
    }

    $expectedDirectory = [System.IO.Path]::GetFullPath($ProjectDirectory).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    $belongsToThisDirectory = $false
    foreach ($containerId in $legacyContainers) {
        try {
            $containerInfo = @(& docker inspect $containerId 2>$null | ConvertFrom-Json)
            if ($LASTEXITCODE -ne 0 -or $containerInfo.Count -eq 0) {
                continue
            }
            $workingDirectory = $containerInfo[0].Config.Labels.'com.docker.compose.project.working_dir'
        }
        catch {
            continue
        }
        if (-not $workingDirectory) {
            continue
        }
        try {
            $actualDirectory = [System.IO.Path]::GetFullPath("$workingDirectory").TrimEnd(
                [System.IO.Path]::DirectorySeparatorChar,
                [System.IO.Path]::AltDirectorySeparatorChar
            )
            if ([string]::Equals(
                $actualDirectory,
                $expectedDirectory,
                [System.StringComparison]::OrdinalIgnoreCase
            )) {
                $belongsToThisDirectory = $true
                break
            }
        }
        catch {
            continue
        }
    }

    if (-not $belongsToThisDirectory) {
        return
    }

    Write-Host "Encerrando os containers antigos desse projeto sem remover os volumes..."
    & docker compose --project-directory $ProjectDirectory --project-name $LegacyProjectName down
    if ($LASTEXITCODE -ne 0) {
        throw "NÃ£o consegui encerrar o projeto Compose antigo ($LegacyProjectName). Confira os containers antes de continuar."
    }
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI não encontrado. Instale o Docker Desktop e rode este script de novo."
}

if (-not (Test-DockerEngine)) {
    $desktopCandidates = @(
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Docker\Docker\Docker Desktop.exe")
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

    if ($desktopCandidates.Count -gt 0) {
        Write-Host "Iniciando Docker Desktop e aguardando o mecanismo de containers..."
        try {
            Start-Process -FilePath $desktopCandidates[0] -WindowStyle Hidden
            $dockerDeadline = [DateTime]::UtcNow.AddMinutes(2)
            while (-not (Test-DockerEngine) -and [DateTime]::UtcNow -lt $dockerDeadline) {
                Start-Sleep -Seconds 4
            }
        }
        catch {
            Write-Warning "Não consegui iniciar o Docker Desktop automaticamente. Abra-o manualmente e aguarde o Engine ficar pronto."
        }
    }

    if (-not (Test-DockerEngine)) {
        throw "O Docker Engine não iniciou. Abra o Docker Desktop, aguarde ficar pronto e rode .\setup.ps1 novamente."
    }
}

$envValues = Read-EnvValues -Path $envPath
$legacyComposeProject = (Split-Path -Leaf $projectDirectory).ToLowerInvariant()
$composeProject = if ($env:COMPOSE_PROJECT_NAME) {
    $env:COMPOSE_PROJECT_NAME
}
elseif ($envValues.COMPOSE_PROJECT_NAME) {
    $envValues.COMPOSE_PROJECT_NAME
}
else {
    "erp-assistant-demo"
}

$volumeDefaults = @{
    POSTGRES_VOLUME_NAME = $composeProject + "_postgres_data"
    REDIS_VOLUME_NAME = $composeProject + "_redis_data"
    MODEL_CACHE_VOLUME_NAME = $composeProject + "_model_cache"
}
foreach ($volumeKey in $volumeDefaults.Keys) {
    $legacyVolumeName = if ($volumeKey -eq "MODEL_CACHE_VOLUME_NAME") {
        $legacyComposeProject + "_model_cache"
    }
    else {
        $legacyComposeProject + "_" + $volumeKey.Replace("_VOLUME_NAME", "").ToLowerInvariant() + "_data"
    }
    if ($envValues[$volumeKey]) {
        if ($envValues[$volumeKey] -ne $volumeDefaults[$volumeKey]) {
            continue
        }
        if ($legacyComposeProject -ne $composeProject -and (Test-DockerVolume -Name $legacyVolumeName)) {
            $envValues[$volumeKey] = $legacyVolumeName
            continue
        }
        if (Test-DockerVolume -Name $envValues[$volumeKey]) {
            continue
        }
    }
    if ($legacyComposeProject -ne $composeProject -and (Test-DockerVolume -Name $legacyVolumeName)) {
        $envValues[$volumeKey] = $legacyVolumeName
    }
    elseif (Test-DockerVolume -Name $volumeDefaults[$volumeKey]) {
        $envValues[$volumeKey] = $volumeDefaults[$volumeKey]
    }
    else {
        $envValues[$volumeKey] = $volumeDefaults[$volumeKey]
    }
}

$isExampleCredentials = (
    $envValues.POSTGRES_PASSWORD -eq "erp_local_only" -and
    $envValues.JWT_SECRET_KEY -eq "replace-with-a-long-random-secret-before-any-shared-deployment" -and
    $envValues.ADMIN_PASSWORD -eq "change-this-local-demo-password"
)

$postgresVolumeExists = Test-DockerVolume -Name $envValues.POSTGRES_VOLUME_NAME

if ($isExampleCredentials -and $postgresVolumeExists) {
    Write-Warning "O .env de exemplo foi mantido porque já existe um volume PostgreSQL; assim o acesso aos dados não é alterado."
}
elseif (-not (Test-Path -LiteralPath $envPath) -or $isExampleCredentials) {
    $envValues = @{
        POSTGRES_DB = "erp"
        POSTGRES_USER = "erp"
        POSTGRES_PASSWORD = New-RandomSecret -Length 32
        POSTGRES_VOLUME_NAME = $envValues.POSTGRES_VOLUME_NAME
        REDIS_VOLUME_NAME = $envValues.REDIS_VOLUME_NAME
        MODEL_CACHE_VOLUME_NAME = $envValues.MODEL_CACHE_VOLUME_NAME
        JWT_SECRET_KEY = New-RandomSecret -Length 64
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = New-RandomSecret -Length 24
        ADMIN_EMAIL = "admin@example.test"
        AI_PROVIDER = "rules"
    }
    Write-EnvValues -Values $envValues
    $envValues = Read-EnvValues -Path $envPath
    Write-Host "Criei .env com senhas aleatórias. O arquivo é ignorado pelo Git."
}
else {
    Write-Host "Já existe um .env personalizado; mantive as configurações e credenciais atuais."
}

foreach ($volumeKey in $volumeDefaults.Keys) {
    Set-EnvValue -Key $volumeKey -Value $envValues[$volumeKey]
}
$envValues = Read-EnvValues -Path $envPath

if (-not $envValues.LLM_TIMEOUT_SECONDS) {
    Set-EnvValue -Key "LLM_TIMEOUT_SECONDS" -Value "60"
    $envValues = Read-EnvValues -Path $envPath
}

if ($envValues.AI_PROVIDER -eq "ollama") {
    Set-EnvValue -Key "AI_PROVIDER" -Value "local"
    $envValues = Read-EnvValues -Path $envPath
}
Remove-EnvValues -Keys @("OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_VOLUME_NAME")

if (-not $envValues.LLM_BASE_URL) {
    Set-EnvValue -Key "LLM_BASE_URL" -Value "http://model-server:8080/v1"
}
if (-not $envValues.LLM_API_KEY) {
    Set-EnvValue -Key "LLM_API_KEY" -Value "local-no-auth"
}
if (-not $envValues.LLM_MODEL) {
    Set-EnvValue -Key "LLM_MODEL" -Value "MiniCPM5-2B"
}
if (-not $envValues.LLM_MODEL_REPO) {
    Set-EnvValue -Key "LLM_MODEL_REPO" -Value "openbmb/MiniCPM5-2B-GGUF:Q4_K_M"
}
if (-not $envValues.LLM_CONTEXT_SIZE) {
    Set-EnvValue -Key "LLM_CONTEXT_SIZE" -Value "4096"
}
$envValues = Read-EnvValues -Path $envPath

if ($EnableLocalAI) {
    Set-EnvValue -Key "AI_PROVIDER" -Value "local"
    $envValues = Read-EnvValues -Path $envPath
}

$requiredKeys = @(
    "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "DATABASE_URL",
    "REDIS_URL", "JWT_SECRET_KEY", "ADMIN_USERNAME", "ADMIN_PASSWORD",
    "ADMIN_EMAIL", "AI_PROVIDER"
)
$missingKeys = @($requiredKeys | Where-Object { -not $envValues[$_] })
if ($missingKeys.Count -gt 0) {
    throw "O .env não tem todas as configurações necessárias. Faltam: $($missingKeys -join ', ')."
}

$useLocalAI = $EnableLocalAI -or $envValues.AI_PROVIDER -eq "local"
$composeArguments = @()
if ($useLocalAI) {
    $composeArguments += @("--profile", "ai")
}
$composeArguments += @("up", "--remove-orphans", "--build", "--detach")

Write-Host "Validando o Compose..."
& docker compose config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "A configuração do Docker Compose está inválida."
}

Write-Host "Buildando e iniciando os serviços em containers separados..."
if ($legacyComposeProject -ne $composeProject) {
    Stop-LegacyComposeProject -LegacyProjectName $legacyComposeProject -ProjectDirectory $projectDirectory
}

& docker compose @composeArguments
if ($LASTEXITCODE -ne 0) {
    throw "O Docker Compose não conseguiu buildar ou iniciar os serviços. Confira: docker compose logs"
}

$readyDeadline = [DateTime]::UtcNow.AddMinutes(3)
$apiReady = $false
while (-not $apiReady -and [DateTime]::UtcNow -lt $readyDeadline) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health/ready" -TimeoutSec 3
        $apiReady = $health.status -eq "ready"
    }
    catch {
        Start-Sleep -Seconds 3
    }
}

if (-not $apiReady) {
    Write-Warning "Os containers foram iniciados, mas a API ainda não confirmou prontidão. Veja os logs com: docker compose logs"
}
else {
    Write-Host "API pronta em http://localhost:8000 (documentação: http://localhost:8000/docs)."
}

if ($useLocalAI) {
    Write-Host "Baixando MiniCPM5-2B do Hugging Face na primeira inicialização. O arquivo Q4 ocupa cerca de 1,56 GB."
    $modelReady = $false
    $modelDeadline = [DateTime]::UtcNow.AddMinutes(15)
    while (-not $modelReady -and [DateTime]::UtcNow -lt $modelDeadline) {
        try {
            $modelHealth = Invoke-RestMethod -Uri "http://localhost:8081/health" -TimeoutSec 5
            $modelReady = $modelHealth.status -eq "ok"
        }
        catch {
            Start-Sleep -Seconds 5
        }
    }
    if (-not $modelReady) {
        throw "O servidor do modelo não ficou pronto em 15 minutos. Confira: docker compose logs model-server"
    }
    Write-Host "Modelo local pronto em http://localhost:8081."
}

$frontendReady = $false
$frontendDeadline = [DateTime]::UtcNow.AddMinutes(1)
while (-not $frontendReady -and [DateTime]::UtcNow -lt $frontendDeadline) {
    try {
        $null = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8080/" -TimeoutSec 3
        $frontendReady = $true
    }
    catch {
        Start-Sleep -Seconds 3
    }
}
if ($frontendReady) {
    Write-Host "Frontend ready at http://localhost:8080."
}
else {
    Write-Warning "The API is available, but the frontend did not respond at http://localhost:8080. See: docker compose logs frontend"
}

& docker compose ps
Write-Host "Usuário inicial: $($envValues.ADMIN_USERNAME). A senha gerada está no campo ADMIN_PASSWORD do arquivo .env."
Write-Host "Para parar os serviços, rode: docker compose down"
