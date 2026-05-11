param(
    [string]$Python = "python",
    [string]$CuratedKb = "curated_bronze_knowledge_LFQA.sqlite3",
    [string]$SnapshotDir = "snapshots\peer_empty",
    [string]$BackupRoot = "backups\peer_ablation_runs",
    [double]$SleepSeconds = 0.2
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $CuratedKb)) {
    throw "Curated KB not found: $CuratedKb"
}

$requiredSnapshotFiles = @(
    "metadata.sqlite3",
    "index.faiss",
    "id_to_text.pkl",
    "bronze_memory_peer.json"
)

foreach ($file in $requiredSnapshotFiles) {
    $path = Join-Path $SnapshotDir $file
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Snapshot file not found: $path"
    }
}

function Restore-PeerEmptySnapshot {
    param(
        [string]$SnapshotDir
    )

    Write-Host "Restoring peer empty-memory snapshot from $SnapshotDir"
    Copy-Item -LiteralPath (Join-Path $SnapshotDir "metadata.sqlite3") -Destination "vector_db_bronze_peer\metadata.sqlite3" -Force
    Copy-Item -LiteralPath (Join-Path $SnapshotDir "index.faiss") -Destination "vector_db_bronze_peer\index.faiss" -Force
    Copy-Item -LiteralPath (Join-Path $SnapshotDir "id_to_text.pkl") -Destination "vector_db_bronze_peer\id_to_text.pkl" -Force
    Copy-Item -LiteralPath (Join-Path $SnapshotDir "bronze_memory_peer.json") -Destination "bronze_memory_peer.json" -Force
}

function Backup-PeerState {
    param(
        [string]$TaskName,
        [string]$BackupRoot
    )

    $safeTaskName = $TaskName -replace "[^A-Za-z0-9_-]+", "_"
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = Join-Path $BackupRoot "$timestamp`_$safeTaskName"
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null

    Copy-Item -LiteralPath "vector_db_bronze_peer\metadata.sqlite3" -Destination (Join-Path $backupDir "metadata.sqlite3") -Force
    Copy-Item -LiteralPath "vector_db_bronze_peer\index.faiss" -Destination (Join-Path $backupDir "index.faiss") -Force
    Copy-Item -LiteralPath "vector_db_bronze_peer\id_to_text.pkl" -Destination (Join-Path $backupDir "id_to_text.pkl") -Force
    Copy-Item -LiteralPath "bronze_memory_peer.json" -Destination (Join-Path $backupDir "bronze_memory_peer.json") -Force

    Write-Host "Backed up peer state to $backupDir"
}

$tasks = @(
    @{
        Name = "MIS baseline"
        Args = @(
            "-B", "run_bronze_dialogue_tests.py",
            "--tests", "tests_peer_MIS_cases.json",
            "--architecture", "peer",
            "--output", "results_peer_MIS.json",
            "--csv-output", "results_peer_MIS.csv",
            "--qa-output", "qa_pairs_peer_MIS.json",
            "--sleep", "$SleepSeconds"
        )
    },
    @{
        Name = "MIS edited"
        Args = @(
            "-B", "run_bronze_dialogue_tests.py",
            "--tests", "tests_peer_MIS_cases.json",
            "--architecture", "peer",
            "--curated-kb", $CuratedKb,
            "--output", "results_peer_MIS_edited.json",
            "--csv-output", "results_peer_MIS_edited.csv",
            "--qa-output", "qa_pairs_peer_MIS_edited.json",
            "--sleep", "$SleepSeconds"
        )
    },
    @{
        Name = "REP baseline"
        Args = @(
            "-B", "run_bronze_dialogue_tests.py",
            "--tests", "tests_peer_REP_cases.json",
            "--architecture", "peer",
            "--output", "results_peer_REP.json",
            "--csv-output", "results_peer_REP.csv",
            "--qa-output", "qa_pairs_peer_REP.json",
            "--sleep", "$SleepSeconds"
        )
    },
    @{
        Name = "REP edited"
        Args = @(
            "-B", "run_bronze_dialogue_tests.py",
            "--tests", "tests_peer_REP_cases.json",
            "--architecture", "peer",
            "--curated-kb", $CuratedKb,
            "--output", "results_peer_REP_edited.json",
            "--csv-output", "results_peer_REP_edited.csv",
            "--qa-output", "qa_pairs_peer_REP_edited.json",
            "--sleep", "$SleepSeconds"
        )
    },
    @{
        Name = "REV baseline"
        Args = @(
            "-B", "run_bronze_dialogue_tests.py",
            "--tests", "tests_peer_REV_cases.json",
            "--architecture", "peer",
            "--output", "results_peer_REV.json",
            "--csv-output", "results_peer_REV.csv",
            "--qa-output", "qa_pairs_peer_REV.json",
            "--sleep", "$SleepSeconds"
        )
    },
    @{
        Name = "REV edited"
        Args = @(
            "-B", "run_bronze_dialogue_tests.py",
            "--tests", "tests_peer_REV_cases.json",
            "--architecture", "peer",
            "--curated-kb", $CuratedKb,
            "--output", "results_peer_REV_edited.json",
            "--csv-output", "results_peer_REV_edited.csv",
            "--qa-output", "qa_pairs_peer_REV_edited.json",
            "--sleep", "$SleepSeconds"
        )
    }
)

foreach ($task in $tasks) {
    $started = Get-Date
    Write-Host ""
    Write-Host "===== START $($task.Name) at $started ====="
    Restore-PeerEmptySnapshot -SnapshotDir $SnapshotDir
    & $Python @($task.Args)
    if ($LASTEXITCODE -ne 0) {
        throw "Task failed: $($task.Name), exit code: $LASTEXITCODE"
    }
    Backup-PeerState -TaskName $task.Name -BackupRoot $BackupRoot
    $finished = Get-Date
    Write-Host "===== DONE  $($task.Name) at $finished ====="
}
