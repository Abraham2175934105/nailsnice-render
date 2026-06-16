# upload_repo.ps1
# Uso: abre PowerShell, sitúate en esta carpeta y ejecuta:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
#   .\upload_repo.ps1

Param()

Write-Output "Starting upload script..."

# Abortar si hay .env locales
if ( (Test-Path '.env') -or (Test-Path '.env.local') -or (Test-Path '.env.production') ) {
  Write-Error "Se encontró un archivo .env en la carpeta. Muévelo/ignóralo antes de push para evitar filtrar secretos."
  exit 1
}

# Obtén el token desde la variable de entorno si ya la exportaste en la sesión
# (recomendado):
if (-not $env:GITHUB_TOKEN) {
  # Si no existe, intenta leer del placeholder dentro del archivo (legacy)
  # (Si quieres, edita el script y coloca tu token en la variable abajo).
  $env:GITHUB_TOKEN = 'PUT_YOUR_TOKEN_HERE'
}

if ($env:GITHUB_TOKEN -eq 'PUT_YOUR_TOKEN_HERE' -or [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
  Write-Error "No se encontró GITHUB_TOKEN. Exporta la variable en la sesión o edita upload_repo.ps1 para añadir tu PAT con scope 'repo'."
  exit 1
}

# Cabeceras para la API
$headers = @{
  Authorization = "token $env:GITHUB_TOKEN"
  'User-Agent'  = 'upload-script'
  Accept        = 'application/vnd.github.v3+json'
}

# Verificar token y obtener usuario
try {
  $user = (Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $headers -ErrorAction Stop).login
} catch {
  Write-Error "401 Unauthorized al verificar token. Asegúrate de que el PAT es válido y tiene scope 'repo'."
  exit 1
}
Write-Output "GitHub user detected: $user"

# Nombre del repo (si ya existe se usará uno con timestamp)
$repoName = 'nails_nice'
$body = @{ name = $repoName; private = $false } | ConvertTo-Json

try {
  Invoke-RestMethod -Method Post -Uri 'https://api.github.com/user/repos' -Headers $headers -Body $body -ErrorAction Stop
  Write-Output "Repo creado: $user/$repoName"
} catch {
  $repoName = "nails_nice_$((Get-Date).ToString('yyyyMMddHHmmss'))"
  $body = @{ name = $repoName; private = $false } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri 'https://api.github.com/user/repos' -Headers $headers -Body $body -ErrorAction Stop
  Write-Output "Repo original existía; creado: $user/$repoName"
}

# Añadir remote y push (envío token en header http.extraheader)
git remote remove origin 2>$null
git remote add origin "https://github.com/$user/$repoName.git"
git -c http.extraheader="AUTHORIZATION: bearer $env:GITHUB_TOKEN" push -u origin main
git -c http.extraheader="AUTHORIZATION: bearer $env:GITHUB_TOKEN" push -u origin develop

# Limpieza del token en la sesión
Remove-Item Env:\GITHUB_TOKEN -ErrorAction SilentlyContinue

Write-Output "Push completado. Repo: https://github.com/$user/$repoName"
