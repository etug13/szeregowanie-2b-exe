$ErrorActionPreference = 'Stop'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $tmp | Out-Null
try {
    $inputPath = Join-Path $tmp 'in.txt'
    $outPath = Join-Path $tmp 'out.txt'
    # Przyklad reczny: b=(2.0,1.5,1.2,1), wynik 0 dla M4: 1 5 oraz 6 dla M4: 5 1.
    @('5', '2.0 1.5 1.2', '4 0 5', '3 0 5', '5 0 7', '2 0 4', '3 0 8',
      '0 2 2 2 1', '2 0 2 2 2', '2 2 0 2 2', '2 2 2 0 2', '4 2 2 2 0') |
        Set-Content -LiteralPath $inputPath -Encoding ASCII
    $cases = @(
        @{lines=@('0','4','2','3','1 5'); ok=$true},
        @{lines=@('6','4','2','3','5 1'); ok=$true},
        @{lines=@('0','4','2','3','1 5','',''); ok=$true},
        @{lines=@('0','1 2 3 4 5','','',''); ok=$false},
        @{lines=@('1','4','2','3','1 5'); ok=$false},
        @{lines=@('0','4','2','3','1 1'); ok=$false},
        @{lines=@('0','4','2','3','1'); ok=$false},
        @{lines=@('0','4','2','3','1 6'); ok=$false},
        @{lines=@('0','4 2 3 1 5'); ok=$false}
    )
    foreach ($case in $cases) {
        $case.lines | Set-Content -LiteralPath $outPath -Encoding ASCII
        $result = & (Join-Path $PSScriptRoot 'weryfikuj.ps1') -Instancja $inputPath -Rozwiazanie $outPath
        if ($result.OK -ne $case.ok) { throw "Autotest weryfikatora nie przeszedl ($($case.lines -join '|')): $($result.Opis)" }
    }
    # Rozroznienie modeli: C_i=10, r_j=20, S=5, produkcja 4 -> A: 24, B: 29 (d=0 => 10+24 / 10+29).
    @('2', '1.0 1.0 1.0', '10 0 0', '4 20 0', '0 5', '7 0') | Set-Content -LiteralPath $inputPath -Encoding ASCII
    @('34', '', '', '', '1 2') | Set-Content -LiteralPath $outPath -Encoding ASCII
    if (-not (& (Join-Path $PSScriptRoot 'weryfikuj.ps1') -Instancja $inputPath -Rozwiazanie $outPath -Model A).OK) { throw 'Autotest modelu A nie przeszedl' }
    @('39', '', '', '', '1 2') | Set-Content -LiteralPath $outPath -Encoding ASCII
    if (-not (& (Join-Path $PSScriptRoot 'weryfikuj.ps1') -Instancja $inputPath -Rozwiazanie $outPath -Model B).OK) { throw 'Autotest modelu B nie przeszedl' }
    Write-Host 'Autotest weryfikatora 2B: OK (11 przypadkow).'
} finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force
}
