param(
    [string]$Program = ".\algorytm.exe",
    [string]$Instancje = ".\instancje",
    [string]$Wyniki = ".\wyniki"
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

foreach ($inputFile in $inputs) {
    $n = [int]((Get-Content -LiteralPath $inputFile.FullName -TotalCount 1).Trim() -split '\s+')[0]
    if ($n -le 0) { throw "Niepoprawne n: $($inputFile.Name)" }
    $limit = $n / 20.0
    $limitText = $limit.ToString([Globalization.CultureInfo]::InvariantCulture)
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
        $remaining = [Math]::Max(1, [int]($limit * 1000 - $watch.Elapsed.TotalMilliseconds))
        $finished = $process.WaitForExit($remaining)
        $watch.Stop()
        if (-not $finished) {
            # Zabij tez proces potomny tworzony przez jednoplikowy PyInstaller.
            $savedPreference = $ErrorActionPreference
            try {
                $ErrorActionPreference = 'Continue'
                & taskkill.exe /PID $process.Id /T /F 2>&1 | Out-Null
            } finally { $ErrorActionPreference = $savedPreference }
            $status = "CZAS"
        } else {
            $process.WaitForExit()
            $exitCode = $process.ExitCode
            if ($watch.Elapsed.TotalSeconds -gt $limit) { $status = "CZAS" }
            elseif ($null -ne $exitCode -and $exitCode -ne 0) { $status = "BLAD PROGRAMU (kod $exitCode)" }
            elseif (Test-Path -LiteralPath $output) {
                $value = Get-Content -LiteralPath $output -TotalCount 1
                $status = if ($null -eq $exitCode) { "NIEZNANY KOD - DO WERYFIKACJI" } else { "DO WERYFIKACJI" }
            } else { $status = "BRAK WYNIKU" }
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
Write-Host "Tabela: $csv"
Write-Host "Wartosci kryterium pochodza z EXE. Pliki out_*.txt sprawdz weryfikatorem poprawnosci."
