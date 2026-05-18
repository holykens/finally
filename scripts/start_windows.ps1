param([switch]$Build)

$ImageName = "finally-app"
$ContainerName = "finally-app"
$Port = 8000

# Check if already running
$running = docker ps --filter "name=$ContainerName" --format "{{.Names}}" 2>$null
if ($running -eq $ContainerName) {
    Write-Host "FinAlly is already running at http://localhost:$Port"
    exit 0
}

# Check if image exists
$imageExists = docker images --format "{{.Repository}}" 2>$null | Where-Object { $_ -eq $ImageName }
if ($Build -or -not $imageExists) {
    Write-Host "Building Docker image (this takes a few minutes)..."
    docker build -t $ImageName .
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Docker build failed"
        exit 1
    }
}

# Remove any stopped container with same name
docker rm $ContainerName 2>$null

# Check .env file exists
if (-not (Test-Path ".env")) {
    Write-Warning ".env file not found. Copying from .env.example..."
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
    } else {
        Write-Error ".env.example not found. Please create .env manually."
        exit 1
    }
}

# Run the container
Write-Host "Starting FinAlly..."
docker run -d `
    --name $ContainerName `
    -v finally-data:/app/db `
    -p "${Port}:8000" `
    --env-file .env `
    $ImageName

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "FinAlly is running! Open: http://localhost:$Port"
} else {
    Write-Error "Failed to start container"
    exit 1
}
