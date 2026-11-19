param(
    [switch]$BezPauzy,
    # Bez ucinania po n/20: program konczy sam, w arkuszu prawdziwy czas "CZAS =X".
    [switch]$BezUcinania,
    # Wybrane programy (nazwy plikow lub numery z listy), puste = wszystkie.
    [string[]]$Programy = @(),
    # Wybrane rozmiary n, puste = wszystkie 10 instancji.
    [int[]]$Rozmiary = @()
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
Add-Type -AssemblyName System.Numerics
& '.\narzedzia\autotest.ps1'
$programs = @(Get-ChildItem -LiteralPath '.\programy' -Filter '*.exe' -File | Sort-Object Name)
if ($programs.Count -eq 0) { throw 'Wloz programy grupy EXE do folderu programy i uruchom START ponownie.' }
$inputs = @(Get-ChildItem -LiteralPath '.\moje-instancje' -Filter 'in_*.txt' -File)
if ($inputs.Count -ne 10) { throw 'Folder moje-instancje musi zawierac dokladnie Twoje 10 instancji.' }

function Split-List([string]$text) { @($text -split '[,;\s]+' | Where-Object { $_ -ne '' }) }

if (-not $BezPauzy) {
    Write-Host "`nPROGRAMY:"
    for ($i = 0; $i -lt $programs.Count; $i++) { Write-Host ("  {0}. {1}" -f ($i + 1), $programs[$i].Name) }
    $a = Read-Host 'Ktore programy? Enter = wszystkie, albo numery/nazwy np. 2,5'
    if ($a.Trim()) { $Programy = Split-List $a }
    $a = Read-Host 'Ktore instancje? Enter = wszystkie, albo n np. 300,500'
    if ($a.Trim()) { $Rozmiary = @(Split-List $a | ForEach-Object { [int]$_ }) }
    $a = Read-Host 'Tryb? Enter = ucinanie po n/20, B = bez ucinania (prawdziwy czas)'
    if ($a.Trim().ToUpper() -eq 'B') { $BezUcinania = $true }
}
if ($Programy.Count -gt 0) {
    $picked = @(foreach ($p in $Programy) {
        $num = 0
        if ([int]::TryParse($p, [ref]$num) -and $num -ge 1 -and $num -le $programs.Count) { $programs[$num - 1] }
        else {
            $m = @($programs | Where-Object { $_.Name -ieq $p -or $_.BaseName -ieq $p })
            if ($m.Count -eq 0) { throw "Nie ma programu: $p" }
            $m
        }
    })
    $programs = @($picked | Sort-Object FullName -Unique | Sort-Object Name)
}

$mode = if ($BezUcinania) { 'BEZ UCINANIA (awaryjnie 10 x n/20)' } else { 'ucinanie po n/20' }
$sizes = if ($Rozmiary.Count -gt 0) { $Rozmiary -join ',' } else { 'wszystkie' }
Write-Host "Limit: n/20 sekund, tryb: $mode. Model czyszczenia A."
Write-Host "Programy: $(($programs | ForEach-Object Name) -join ', '). Instancje n: $sizes."
$run = Join-Path $PSScriptRoot ('wyniki\' + [DateTime]::Now.ToString('yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Path $run | Out-Null
foreach ($program in $programs) {
    Write-Host "`nPROGRAM: $($program.Name)"
    $folder = Join-Path $run $program.BaseName
    & '.\narzedzia\testuj.ps1' -Program $program.FullName -Instancje '.\moje-instancje' -Wyniki $folder `
        -BezUcinania:$BezUcinania -Tylko $Rozmiary
    $rows = @(Import-Csv -LiteralPath (Join-Path $folder 'czasy.csv') -Delimiter ';')
    $report = @(foreach ($row in ($rows | Sort-Object { [int]([IO.Path]::GetFileNameWithoutExtension($_.instancja) -split '_')[-1] })) {
        $output = Join-Path $folder ('out_' + [IO.Path]::GetFileNameWithoutExtension($row.instancja) + '.txt')
        $check = & '.\narzedzia\weryfikuj.ps1' -Instancja (Join-Path '.\moje-instancje' $row.instancja) -Rozwiazanie $output
        $valid = $check.OK -and $row.kod_wyjscia -eq '0'
        $value = if ($valid) { $check.Kryterium } else { "B$([char]0x141)$([char]0x104)D" }
        $time = if ($row.status -like 'CZAS*') { 'CZAS =' + $row.czas_s } else { $row.czas_s }
        $comment = if ($valid -and $row.status -eq 'DO WERYFIKACJI') { 'OK' } elseif ($valid) { $row.status + '; wynik poprawny' } else { $row.status + '; ' + $check.Opis }
        [pscustomobject]@{ instancja=$row.instancja; kryterium=$value; czas=$time; komentarz=$comment }
    })
    $report | Export-Csv -LiteralPath (Join-Path $folder 'DO-ARKUSZA.csv') -Delimiter ';' -NoTypeInformation -Encoding UTF8
    $report.kryterium | Set-Content -LiteralPath (Join-Path $folder 'KRYTERIUM.txt') -Encoding UTF8
    $report.czas | Set-Content -LiteralPath (Join-Path $folder 'CZASY.txt') -Encoding UTF8
    $report | Format-Table -AutoSize
    Write-Host "Gotowe wyniki tego programu: $folder"
    if ($Rozmiary.Count -gt 0) { Write-Host "UWAGA: tylko n = $sizes - wpisz do odpowiednich wierszy arkusza." }
    else { Write-Host 'Wpisz je teraz do arkusza (kolejnosc n=50,100,...,500).' }
    if (-not $BezPauzy) {
        $answer = Read-Host 'Enter = kolejny program; Q = zakoncz'
        if ($answer -eq 'q') { break }
    }
}
Write-Host "`nRaporty zachowane w: $run"
