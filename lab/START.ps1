param([switch]$BezPauzy)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Add-Type -AssemblyName System.Numerics
& '.\narzedzia\autotest.ps1'
$programs = @(Get-ChildItem -LiteralPath '.\programy' -Filter '*.exe' -File | Sort-Object Name)
if ($programs.Count -eq 0) { throw 'Wloz programy grupy EXE do folderu programy i uruchom START ponownie.' }
$inputs = @(Get-ChildItem -LiteralPath '.\moje-instancje' -Filter 'in_*.txt' -File)
if ($inputs.Count -ne 10) { throw 'Folder moje-instancje musi zawierac dokladnie Twoje 10 instancji.' }
Write-Host 'Limit: n/20 sekund. Model czyszczenia A. Kazdy EXE bedzie testowany na Twoich 10 instancjach.'
$run = Join-Path $PSScriptRoot ('wyniki\' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $run | Out-Null
foreach ($program in $programs) {
    Write-Host "`nPROGRAM: $($program.Name)"
    $folder = Join-Path $run $program.BaseName
    & '.\narzedzia\testuj.ps1' -Program $program.FullName -Instancje '.\moje-instancje' -Wyniki $folder
    $rows = @(Import-Csv -LiteralPath (Join-Path $folder 'czasy.csv') -Delimiter ';')
    $report = @(foreach ($row in ($rows | Sort-Object { [int]([IO.Path]::GetFileNameWithoutExtension($_.instancja) -split '_')[-1] })) {
        $output = Join-Path $folder ('out_' + [IO.Path]::GetFileNameWithoutExtension($row.instancja) + '.txt')
        $check = & '.\narzedzia\weryfikuj.ps1' -Instancja (Join-Path '.\moje-instancje' $row.instancja) -Rozwiazanie $output
        $valid = $check.OK -and $row.kod_wyjscia -eq '0'
        $value = if ($valid) { $check.Kryterium } else { "B$([char]0x141)$([char]0x104)D" }
        $time = if ($row.status -eq 'CZAS') { 'CZAS =' + $row.czas_s } else { $row.czas_s }
        $comment = if ($valid -and $row.status -eq 'DO WERYFIKACJI') { 'OK' } elseif ($valid) { $row.status } else { $row.status + '; ' + $check.Opis }
        [pscustomobject]@{ instancja=$row.instancja; kryterium=$value; czas=$time; komentarz=$comment }
    })
    $report | Export-Csv -LiteralPath (Join-Path $folder 'DO-ARKUSZA.csv') -Delimiter ';' -NoTypeInformation -Encoding UTF8
    $report.kryterium | Set-Content -LiteralPath (Join-Path $folder 'KRYTERIUM.txt') -Encoding UTF8
    $report.czas | Set-Content -LiteralPath (Join-Path $folder 'CZASY.txt') -Encoding UTF8
    $report | Format-Table -AutoSize
    Write-Host "Gotowe wyniki tego programu: $folder"
    Write-Host 'Wpisz je teraz do arkusza (kolejnosc n=50,100,...,500).'
    if (-not $BezPauzy) {
        $answer = Read-Host 'Enter = kolejny program; Q = zakoncz'
        if ($answer -eq 'q') { break }
    }
}
Write-Host "`nRaporty zachowane w: $run"
