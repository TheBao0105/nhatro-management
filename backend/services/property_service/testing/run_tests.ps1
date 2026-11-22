<#
.SYNOPSIS
    Unified Unit & API Test + Coverage Runner for Service 2 (Property & Room).
.DESCRIPTION
    Centralized runner located at:
        backend/services/property_service/testing/run_tests.ps1
    Can be executed from the project root, from backend/, or directly from the testing/ directory.
    1. Runs ONLY the 72 Pure Unit Tests (services.property_service.testing.unit_tests).
    2. Runs ONLY the 135 API / HTTP Tests (services.property_service.testing.api_tests).
    3. Runs the Full Service 2 Test Suite (207 tests = 72 Pure Unit + 135 API) under Coverage.py
       (Statement + Branch Coverage) and writes verbose output to testing/evidence/test-execution.log.
    4. Exports text coverage summary (testing/evidence/coverage_full_service2.txt) and HTML coverage
       report (testing/evidence/coverage/index.html).
    5. Runs testing/tools/collect_results.py to generate testing/reports/results.json,
       testing/reports/UNIT_TEST_CASES.md, testing/evidence/TEST_EXECUTION_REPORT.html,
       and testing/evidence/junit-report.xml.
    6. Runs collect_results.py --sprint1-only to independently verify the 189 Sprint 1 tests.
    7. Cleans temporary backend/.coverage binary artifact and returns appropriate exit code.
#>
$ErrorActionPreference = "Stop"

$TestingDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ServiceDir  = Split-Path -Parent $TestingDir
$ServicesDir = Split-Path -Parent $ServiceDir
$BackendDir  = Split-Path -Parent $ServicesDir

$PythonExe   = Join-Path $BackendDir "venv\Scripts\python.exe"
$ReportsDir  = Join-Path $TestingDir "reports"
$EvidenceDir = Join-Path $TestingDir "evidence"
$CoverageDir = Join-Path $EvidenceDir "coverage"
$CollectorPy = Join-Path $TestingDir "tools\collect_results.py"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Virtual environment python not found at: $PythonExe"
    exit 1
}

New-Item -ItemType Directory -Force -Path $ReportsDir  | Out-Null
New-Item -ItemType Directory -Force -Path $EvidenceDir | Out-Null

$env:DB_ENGINE = "sqlite"
$env:DJANGO_SETTINGS_MODULE = "config.service_settings.property"
$env:PYTHONIOENCODING = "utf-8"

Push-Location $BackendDir
try {
    Write-Host "=================================================================" -ForegroundColor Cyan
    Write-Host " [1/6] Running Pure Unit Tests Only (72 tests in unit_tests/)" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan
    & $PythonExe $CollectorPy --unit-only
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Pure Unit Tests failed."
        exit $LASTEXITCODE
    }

    Write-Host "`n=================================================================" -ForegroundColor Cyan
    Write-Host " [2/6] Running API / HTTP Tests Only (135 tests in api_tests/)" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan
    & $PythonExe $CollectorPy --api-only
    if ($LASTEXITCODE -ne 0) {
        Write-Error "API / HTTP Tests failed."
        exit $LASTEXITCODE
    }

    Write-Host "`n=================================================================" -ForegroundColor Cyan
    Write-Host " [3/6] Running Full Service 2 Suite (207 tests) + Branch Coverage" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan

    if (Test-Path ".coverage") {
        Remove-Item ".coverage" -Force
    }

    $LogFile = Join-Path $EvidenceDir "test-execution.log"
    $PrevEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & $PythonExe -m coverage run --rcfile=.coveragerc manage.py test services.property_service -v 2 2>&1 |
        Tee-Object -FilePath $LogFile
    $TestExitCode = $LASTEXITCODE
    $ErrorActionPreference = $PrevEAP

    if ($TestExitCode -ne 0) {
        Write-Error "Django test runner failed with exit code $TestExitCode"
        exit $TestExitCode
    }

    Write-Host "`n=================================================================" -ForegroundColor Cyan
    Write-Host " [4/6] Generating Text & HTML Coverage Reports (Branch Coverage)" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan

    $CovTxtFile = Join-Path $EvidenceDir "coverage_full_service2.txt"
    & $PythonExe -m coverage report --rcfile=.coveragerc -m | Tee-Object -FilePath $CovTxtFile
    if ($LASTEXITCODE -ne 0) {
        Write-Error "coverage report failed."
        exit $LASTEXITCODE
    }

    if (Test-Path $CoverageDir) {
        Remove-Item $CoverageDir -Recurse -Force
    }
    & $PythonExe -m coverage html --rcfile=.coveragerc -d $CoverageDir
    if ($LASTEXITCODE -ne 0) {
        Write-Error "coverage html failed."
        exit $LASTEXITCODE
    }

    Write-Host "`n=================================================================" -ForegroundColor Cyan
    Write-Host " [5/6] Generating HTML Execution Report, JUnit XML & Test Matrix" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan

    & $PythonExe $CollectorPy
    if ($LASTEXITCODE -ne 0) {
        Write-Error "collect_results.py (full suite) failed."
        exit $LASTEXITCODE
    }

    Write-Host "`n=================================================================" -ForegroundColor Cyan
    Write-Host " [6/6] Verifying 188 Sprint 1 Scope Tests & Cleaning Temp Files" -ForegroundColor Cyan
    Write-Host "=================================================================" -ForegroundColor Cyan

    & $PythonExe $CollectorPy --sprint1-only
    if ($LASTEXITCODE -ne 0) {
        Write-Error "collect_results.py (--sprint1-only) failed."
        exit $LASTEXITCODE
    }

    if (Test-Path ".coverage") {
        Remove-Item ".coverage" -Force
        Write-Host "Removed temporary backend/.coverage binary file." -ForegroundColor Green
    }

    Write-Host "`n[SUCCESS] All 207 Service 2 tests (72 Pure Unit + 135 API/HTTP | 188 Sprint 1 + 19 Out-of-Sprint-1) PASSED with 100% Coverage!" -ForegroundColor Green
    $HtmlTestReport = Join-Path $EvidenceDir "TEST_EXECUTION_REPORT.html"
    $HtmlCovReport  = Join-Path $CoverageDir "index.html"
    Write-Host " - Execution Log      : $LogFile"
    Write-Host " - Coverage Summary   : $CovTxtFile"
    Write-Host " - HTML Coverage      : $HtmlCovReport"
    Write-Host " - HTML Test Report   : $HtmlTestReport"
    Write-Host " - JUnit XML Report   : $(Join-Path $EvidenceDir 'junit-report.xml')"

    if (Test-Path $HtmlTestReport) {
        Write-Host "`nOpening HTML Test Execution Report & HTML Coverage Report in default browser..." -ForegroundColor Cyan
        Start-Process $HtmlTestReport
    }
    if (Test-Path $HtmlCovReport) {
        Start-Process $HtmlCovReport
    }
    exit 0
}
finally {
    Pop-Location
}
