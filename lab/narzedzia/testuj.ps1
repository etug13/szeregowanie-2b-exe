param(
    [string]$Program = ".\algorytm.exe",
    [string]$Instancje = ".\instancje",
    [string]$Wyniki = ".\wyniki",
    # Bez ucinania: program dziala do konca (najwyzej Awaryjny * n/20), czas jest prawdziwy.
    [switch]$BezUcinania,
    [double]$Awaryjny = 10,
    # Tylko wybrane rozmiary n (np. 300,500); puste = wszystkie instancje.
    [int[]]$Tylko = @()
)

$ErrorActionPreference = "Stop"
$exe = (Resolve-Path -LiteralPath $Program).Path
$inputs = @(Get-ChildItem -LiteralPath $Instancje -Filter "in_*.txt" -File |
    Sort-Object Name)
if ($inputs.Count -eq 0) { throw "Brak plikow in_*.txt w folderze $Instancje" }
New-Item -ItemType Directory -Force -Path $Wyniki | Out-Null
$folder = (Resolve-Path -LiteralPath $Wyniki).Path
$csv = Join-Path $folder "czasy.csv"
if (Test-Path -LiteralPath $csv) {
    throw "Plik $csv juz istnieje. Podaj nowy folder wynikow przez -Wyniki."
}
if ($BezUcinania) { Write-Host "Tryb BEZ UCINANIA: program konczy sam (awaryjnie po $Awaryjny x limit)." }

$done = 0
foreach ($inputFile in $inputs) {
    $n = [int]((Get-Content -LiteralPath $inputFile.FullName -TotalCount 1).Trim() -split '\s+')[0]
    if ($n -le 0) { throw "Niepoprawne n: $($inputFile.Name)" }
    if ($Tylko.Count -gt 0 -and $Tylko -notcontains $n) { continue }
    $done++
    $limit = $n / 20.0
    $limitText = $limit.ToString([Globalization.CultureInfo]::InvariantCulture)
    $wait = if ($BezUcinania) { $limit * $Awaryjny } else { $limit }
    $output = Join-Path $folder ("out_" + $inputFile.BaseName + ".txt")
    Remove-Item -LiteralPath $output -ErrorAction SilentlyContinue
    $value = ""
    $exitCode = $null
    $status = "BLAD"
    $watch = [Diagnostics.Stopwatch]::StartNew()
    try {
        $arguments = '"{0}" "{1}" {2}' -f $inputFile.FullName, $output, $limitText
        $process = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru -NoNewWindow `
            -RedirectStandardOutput (Join-Path $folder ($inputFile.BaseName + ".log")) `
            -RedirectStandardError (Join-Path $folder ($inputFile.BaseName + ".err"))
        # Zachowaj uchwyt przed zakonczeniem procesu (Windows PowerShell 5.1).
        $null = $process.Handle
        $remaining = [Math]::Max(1, [int]($wait * 1000 - $watch.Elapsed.TotalMilliseconds))
        $finished = $process.WaitForExit($remaining)
        $watch.Stop()
        if (-not $finished) {
            # Zabij tez proces potomny tworzony przez jednoplikowy PyInstaller.
            $savedPreference = $ErrorActionPreference
            try {
                $ErrorActionPreference = 'Continue'
                & taskkill.exe /PID $process.Id /T /F 2>&1 | Out-Null
                # Kod taskkill nie jest wynikiem testu (nie psuj kodu wyjscia skryptu).
                $global:LASTEXITCODE = 0
            } finally { $ErrorActionPreference = $savedPreference }
            $status = if ($BezUcinania) { "CZAS (przerwany awaryjnie)" } else { "CZAS" }
        } else {
            $process.WaitForExit()
            $exitCode = $process.ExitCode
            $late = $watch.Elapsed.TotalSeconds -gt $limit
            if ($late -and -not $BezUcinania) { $status = "CZAS" }
            elseif ($null -ne $exitCode -and $exitCode -ne 0) { $status = "BLAD PROGRAMU (kod $exitCode)" }
            elseif (Test-Path -LiteralPath $output) {
                $value = Get-Content -LiteralPath $output -TotalCount 1
                $status = if ($late) { "CZAS" } elseif ($null -eq $exitCode) { "NIEZNANY KOD - DO WERYFIKACJI" } else { "DO WERYFIKACJI" }
            } else { $status = if ($late) { "CZAS" } else { "BRAK WYNIKU" } }
        }
    } catch {
        $watch.Stop()
        $status = "BLAD: " + $_.Exception.Message
    }
    $seconds = [Math]::Round($watch.Elapsed.TotalSeconds, 3)
    [pscustomobject]@{
        instancja = $inputFile.Name
        kryterium = $value
        czas_s = $seconds
        limit_s = $limit
        status = $status
        kod_wyjscia = $exitCode
    } | Export-Csv -LiteralPath $csv -Delimiter ';' -NoTypeInformation -Encoding UTF8 -Append
    Write-Host "$($inputFile.Name): $status | wynik=$value | $seconds s / $limit s"
}
if ($done -eq 0) { throw "Zadna instancja nie pasuje do wybranych n: $($Tylko -join ',')" }
Write-Host "Tabela: $csv"
Write-Host "Wartosci kryterium pochodza z EXE. Pliki out_*.txt sprawdz weryfikatorem poprawnosci."
