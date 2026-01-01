# E2E presign upload/download test script
# Run from repository root: powershell -ExecutionPolicy Bypass -File backend/scripts/run_e2e_presign.ps1
try {
    Write-Output "Creating sample.pdf..."
    Set-Content -Path sample.pdf -Value "This is a sample file for presign upload/download test." -Encoding UTF8

    Write-Output "Generating JWT for user 'live_test_user' inside app container..."
    $token = docker compose exec -T app python -c "from app.core.auth import create_access_token; print(create_access_token({'sub':'live_test_user'}))" | Out-String
    $token = $token.Trim()
    if (-not $token) { throw "Failed to obtain token" }
    Write-Output "Token obtained."

    Write-Output "Requesting presigned PUT URL (presign)..."
    $presignResp = & curl.exe -s -X POST "http://localhost:8000/tickets/1/attachments/presign" -H "Content-Type: application/json" -H "Authorization: Bearer $token" -d '{"original_filename":"test.pdf","mime":"application/pdf","size":1234}' | Out-String
    if (-not $presignResp) { throw "Presign request returned empty response" }
    $presignJson = $presignResp | ConvertFrom-Json
    $attachment_id = $presignJson.attachment_id

























}    exit 2    Write-Error "E2E script failed: $_"} catch {    exit 0    Write-Output "E2E flow completed. Files: sample.pdf, downloaded.pdf"    curl.exe -s -o downloaded.pdf "$download_url"    Write-Output "Downloading file to downloaded.pdf..."    Write-Output "Download URL: $download_url"    $download_url = $downloadJson.download_url    $downloadJson = $downloadResp | ConvertFrom-Json    $downloadResp = curl.exe -s -H "Authorization: Bearer $token" "http://localhost:8000/tickets/1/attachments/$attachment_id/download" | Out-String    Write-Output "Requesting presigned GET URL (download)..."    docker compose exec -T postgres psql -U postgres -d ticketing_db -c "UPDATE attachments SET scanned_status='CLEAN' WHERE id=$attachment_id;"    Write-Output "Marking attachment as CLEAN in DB..."    Write-Output "Upload HTTP status: $putResp"    $putResp = curl.exe -s -o /dev/null -w "%{http_code}" -X PUT -H "Content-Type: application/pdf" --data-binary @sample.pdf "$upload_url"    Write-Output "Uploading sample.pdf to presigned PUT URL..."    Write-Output "Presign response: attachment_id=$attachment_id, upload_url=$upload_url"n    $upload_url = $presignJson.upload_url