param(
    [Parameter(Mandatory=$true)][string]$Instancja,
    [Parameter(Mandatory=$true)][string]$Rozwiazanie,
    [ValidateSet('A','B')][string]$Model = 'A'
)
# Weryfikator poprawnosci 2B (bez Pythona). Zwraca obiekt: OK, Kryterium, Opis.
# Model A: C_j = max(r_j, C_i + S_ij) + ceil(b_k*p_j)
# Model B: C_j = max(r_j, C_i) + S_ij + ceil(b_k*p_j)
# Pierwsze zadanie na maszynie: C_j = r_j + ceil(b_k*p_j). b liczone dokladnie ([decimal]).
$ErrorActionPreference = 'Stop'
$inv = [Globalization.CultureInfo]::InvariantCulture
function Wynik($ok, $k, $opis) { [pscustomobject]@{ OK = $ok; Kryterium = $k; Opis = $opis } }
try {
    $lines = @([IO.File]::ReadAllLines((Resolve-Path -LiteralPath $Instancja).Path) | Where-Object { $_.Trim() -ne '' })
    $n = [int]$lines[0].Trim()
    if ($n -lt 1 -or $lines.Count -ne 2 + 2 * $n) { return (Wynik $false $null 'instancja: zla liczba wierszy') }
    $b = @($lines[1].Trim() -split '\s+' | ForEach-Object { [decimal]::Parse($_, $inv) }) + @([decimal]1)
    if ($b.Count -ne 4) { return (Wynik $false $null 'instancja: wymagane 3 mnozniki') }
    $p = New-Object 'int[]' $n; $r = New-Object 'long[]' $n; $d = New-Object 'long[]' $n
    for ($j = 0; $j -lt $n; $j++) {
        $t = $lines[2 + $j].Trim() -split '\s+'
        $p[$j] = [int]$t[0]; $r[$j] = [long]$t[1]; $d[$j] = [long]$t[2]
    }
    $S = New-Object 'object[]' $n
    for ($j = 0; $j -lt $n; $j++) {
        $row = [long[]]($lines[2 + $n + $j].Trim() -split '\s+')
        if ($row.Count -ne $n) { return (Wynik $false $null "instancja: wiersz czyszczen $($j+1) ma $($row.Count) liczb") }
        $S[$j] = $row
    }

    if (-not (Test-Path -LiteralPath $Rozwiazanie)) { return (Wynik $false $null 'brak pliku rozwiazania') }
    $sol = [System.Collections.Generic.List[string]]::new()
    foreach ($l in [IO.File]::ReadAllLines((Resolve-Path -LiteralPath $Rozwiazanie).Path)) { $sol.Add($l) }
    while ($sol.Count -gt 5 -and $sol[$sol.Count - 1].Trim() -eq '') { $sol.RemoveAt($sol.Count - 1) }
    if ($sol.Count -eq 4) { $sol.Add('') }
    if ($sol.Count -ne 5) { return (Wynik $false $null "rozwiazanie: oczekiwano 5 wierszy, jest $($sol.Count)") }
    $declared = [long]$sol[0].Trim()

    $seen = New-Object 'bool[]' ($n + 1)
    $count = 0
    [long]$total = 0
    for ($k = 0; $k -lt 4; $k++) {
        $txt = $sol[$k + 1].Trim()
        if ($txt -eq '') { continue }
        [long]$fin = 0; $prev = -1
        foreach ($tok in ($txt -split '\s+')) {
            $job = 0
            if (-not [int]::TryParse($tok, [ref]$job) -or $job -lt 1 -or $job -gt $n) {
                return (Wynik $false $null "maszyna $($k+1): numer zadania '$tok' poza zakresem 1..$n")
            }
            if ($seen[$job]) { return (Wynik $false $null "zadanie $job wystepuje wiecej niz raz") }
            $seen[$job] = $true; $count++
            $j = $job - 1
            $dur = [long][decimal]::Ceiling($b[$k] * $p[$j])
            if ($prev -lt 0) { $start = $r[$j] }
            elseif ($Model -eq 'A') { $start = [Math]::Max($r[$j], $fin + $S[$prev][$j]) }
            else { $start = [Math]::Max($r[$j], $fin) + $S[$prev][$j] }
            $fin = $start + $dur
            if ($fin -gt $d[$j]) { $total += $fin - $d[$j] }
            $prev = $j
        }
    }
    if ($count -ne $n) { return (Wynik $false $null "brakuje zadan: jest $count z $n") }
    if ($total -ne $declared) { return (Wynik $false $total "zadeklarowano $declared, przeliczono $total") }
    return (Wynik $true $total "OK; suma opoznien = $total; model $Model")
} catch {
    return (Wynik $false $null ('blad odczytu: ' + $_.Exception.Message))
}
