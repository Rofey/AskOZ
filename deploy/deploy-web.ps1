# Build the website as static files and publish them to Firebase Hosting.
#   powershell -File deploy/deploy-web.ps1
# NEXT_PUBLIC_* values are baked into the JavaScript at build time and are
# visible to every visitor: only ever public values (like the API's URL) here.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path (Split-Path $PSScriptRoot -Parent) "web")

$env:NEXT_PUBLIC_API_URL = gcloud run services describe askoz-api `
  --region=australia-southeast1 --format="value(status.url)"
if (-not $env:NEXT_PUBLIC_API_URL) { throw "couldn't find the askoz-api URL" }

if (Test-Path out) { Remove-Item -Recurse -Force out }
npm run build
if ($LASTEXITCODE -ne 0) { throw "build failed" }

npx --yes firebase-tools@15 deploy --only hosting --project askoz-app
if ($LASTEXITCODE -ne 0) { throw "deploy failed" }
