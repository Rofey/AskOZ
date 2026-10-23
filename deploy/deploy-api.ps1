# Build the API image on Cloud Build and roll it out to Cloud Run.
#   powershell -File deploy/deploy-api.ps1
# Each image gets a unique tag (time + git commit) so any release can be
# redeployed or rolled back by name; "latest" would be ambiguous.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$region = "australia-southeast1"
$project = "askoz-app"
$image = "$region-docker.pkg.dev/$project/askoz/api"
$commit = (git rev-parse --short HEAD).Trim()
$dirty = if (git status --porcelain) { "-dirty" } else { "" }
$tag = "$(Get-Date -Format yyyyMMdd-HHmm)-$commit$dirty"

gcloud builds submit --region=$region --config=cloudbuild.yaml --substitutions="_TAG=$tag" .
if ($LASTEXITCODE -ne 0) { throw "build failed" }

# Secrets are mounted from Secret Manager; only the askoz-api service account
# can read them. Plain settings live in deploy/api.env.yaml.
gcloud run deploy askoz-api `
  --image="${image}:$tag" `
  --region=$region `
  --service-account="askoz-api@$project.iam.gserviceaccount.com" `
  --add-cloudsql-instances="${project}:${region}:askoz-db" `
  --set-secrets="ASKOZ_DATABASE_URL=askoz-database-url:latest,ASKOZ_REDIS_URL=askoz-redis-url:latest,ASKOZ_ANTHROPIC_API_KEY=askoz-anthropic-api-key:latest,ASKOZ_IP_HASH_SECRET=askoz-ip-hash-secret:latest" `
  --env-vars-file=deploy/api.env.yaml `
  --cpu=1 --memory=2Gi --concurrency=16 --timeout=120 `
  --min-instances=0 --max-instances=2 --cpu-boost `
  --allow-unauthenticated --quiet
if ($LASTEXITCODE -ne 0) { throw "deploy failed" }

$url = gcloud run services describe askoz-api --region=$region --format="value(status.url)"
Invoke-RestMethod "$url/health"
