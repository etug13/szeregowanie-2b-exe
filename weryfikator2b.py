"""Weryfikator poprawnosci 2B: Q4 | r_j, S_ij | suma opoznien.

    weryfikator.exe <instancja> <rozwiazanie>          jeden plik
    weryfikator.exe <folder_instancji> <folder_wynikow> cala seria (wiersz po wierszu)
    weryfikator.exe --autotest                           test samego weryfikatora

Opcja --model B zmienia model czyszczenia (domyslnie A).
Model A: C_j = max(r_j, C_i + S_ij) + ceil(b_k*p_j); pierwsze zadanie: r_j + ceil(b_k*p_j).
Model B: C_j = max(r_j, C_i) + S_ij + ceil(b_k*p_j).
Kod wyjscia: 0 = wszystko poprawne, 1 = bledy.
"""
import re
import sys
import tempfile
from fractions import Fraction
from pathlib import Path


class Blad(Exception):
    pass


def wczytaj_instancje(path):
    lines = [l for l in Path(path).read_text(encoding='utf-8-sig').splitlines() if l.strip()]
    try:
        n = int(lines[0].split()[0])
    except (IndexError, ValueError):
        raise Blad('instancja: brak liczby zadan w pierwszym wierszu')
    if n < 1 or len(lines) != 2 + 2 * n:
        raise Blad(f'instancja: oczekiwano {2 + 2 * n} wierszy, jest {len(lines)}')
    b = [Fraction(x) for x in lines[1].split()]
    if len(b) != 3:
        raise Blad('instancja: wymagane 3 mnozniki w drugim wierszu')
    b.append(Fraction(1))
    jobs = []
    for j in range(n):
        t = lines[2 + j].split()
        if len(t) != 3:
            raise Blad(f'instancja: wiersz zadania {j + 1} powinien miec p r d')
        jobs.append(tuple(int(x) for x in t))
    S = []
    for j in range(n):
        row = [int(x) for x in lines[2 + n + j].split()]
        if len(row) != n:
            raise Blad(f'instancja: wiersz czyszczen {j + 1} ma {len(row)} liczb zamiast {n}')
        S.append(row)
    return n, b, jobs, S


def sprawdz(inst_path, sol_path, model='A'):
    """Zwraca przeliczone kryterium albo rzuca Blad z opisem."""
    n, b, jobs, S = wczytaj_instancje(inst_path)
    if not Path(sol_path).is_file():
        raise Blad('brak pliku rozwiazania')
    sol = Path(sol_path).read_text(encoding='utf-8-sig').splitlines()
    while len(sol) > 5 and not sol[-1].strip():
        sol.pop()
    if len(sol) == 4:
        sol.append('')
    if len(sol) != 5:
        raise Blad(f'rozwiazanie: oczekiwano 5 wierszy (kryterium + 4 maszyny), jest {len(sol)}')
    try:
        declared = int(sol[0].strip())
    except ValueError:
        raise Blad(f'rozwiazanie: pierwszy wiersz "{sol[0].strip()}" nie jest liczba calkowita')
    seen = [False] * (n + 1)
    total = 0
    for k in range(4):
        t = 0
        prev = None
        for tok in sol[k + 1].split():
            if not re.fullmatch(r'\d+', tok) or not 1 <= int(tok) <= n:
                raise Blad(f'maszyna {k + 1}: numer zadania "{tok}" poza zakresem 1..{n}')
            job = int(tok)
            if seen[job]:
                raise Blad(f'zadanie {job} wystepuje wiecej niz raz')
            seen[job] = True
            p, r, d = jobs[job - 1]
            dur = -(-b[k].numerator * p // b[k].denominator)
            if prev is None:
                start = r
            elif model == 'A':
                start = max(r, t + S[prev][job - 1])
            else:
                start = max(r, t) + S[prev][job - 1]
            t = start + dur
            total += max(0, t - d)
            prev = job - 1
    brak = [j for j in range(1, n + 1) if not seen[j]]
    if brak:
        raise Blad(f'brakuje {len(brak)} zadan, np. {brak[:5]}')
    if total != declared:
        raise Blad(f'zadeklarowano {declared}, przeliczono {total}')
    return total


def klucz(path):
    """in_159876_50.txt -> ('159876', 50); sortowanie po autorze i n."""
    parts = Path(path).stem.split('_')
    try:
        return parts[1], int(parts[-1])
    except (IndexError, ValueError):
        return Path(path).stem, 0


def znajdz_wynik(folder, inst):
    """Dla in_A_n.txt szuka out_A_n.txt albo out_A_<cokolwiek>_n.txt."""
    autor, n = klucz(inst)
    exact = folder / f'out_{autor}_{n}.txt'
    if exact.is_file():
        return exact
    found = sorted(folder.glob(f'out_{autor}_*_{n}.txt'))
    return found[0] if found else None


def seria(inst_dir, wyn_dir, model):
    inst_dir, wyn_dir = Path(inst_dir), Path(wyn_dir)
    insts = sorted(inst_dir.glob('in_*.txt'), key=klucz)
    if not insts:
        print(f'Brak plikow in_*.txt w {inst_dir}')
        return 1
    print(f'Weryfikacja serii, model {model}: {len(insts)} instancji, wyniki z {wyn_dir}\n')
    column, bledy = [], 0
    for inst in insts:
        out = znajdz_wynik(wyn_dir, inst)
        try:
            if out is None:
                raise Blad('brak pliku out_* dla tej instancji')
            value = sprawdz(inst, out, model)
            print(f'{inst.name:<24} OK    {value}', flush=True)
            column.append(str(value))
        except Blad as e:
            print(f'{inst.name:<24} BLAD  {e}', flush=True)
            column.append('BŁĄD')
            bledy += 1
        except Exception as e:  # nieczytelny plik itp.
            print(f'{inst.name:<24} BLAD  odczyt: {e}', flush=True)
            column.append('BŁĄD')
            bledy += 1
    plik = wyn_dir / 'KRYTERIUM.txt'
    plik.write_text('\n'.join(column) + '\n', encoding='utf-8')
    print(f'\nPoprawne: {len(insts) - bledy}/{len(insts)}. Kolumna do arkusza: {plik}')
    print('\n'.join(column))
    return 1 if bledy else 0


def autotest():
    inst = ['5', '2.0 1.5 1.2', '4 0 5', '3 0 5', '5 0 7', '2 0 4', '3 0 8',
            '0 2 2 2 1', '2 0 2 2 2', '2 2 0 2 2', '2 2 2 0 2', '4 2 2 2 0']
    cases = [(['0', '4', '2', '3', '1 5'], True), (['6', '4', '2', '3', '5 1'], True),
             (['0', '4', '2', '3', '1 5', '', ''], True), (['0', '1 2 3 4 5', '', '', ''], False),
             (['1', '4', '2', '3', '1 5'], False), (['0', '4', '2', '3', '1 1'], False),
             (['0', '4', '2', '3', '1'], False), (['0', '4', '2', '3', '1 6'], False),
             (['0', '4 2 3 1 5'], False)]
    models = [(['2', '1.0 1.0 1.0', '10 0 0', '4 20 0', '0 5', '7 0'], ['34', '', '', '', '1 2'], 'A'),
              (['2', '1.0 1.0 1.0', '10 0 0', '4 20 0', '0 5', '7 0'], ['39', '', '', '', '1 2'], 'B')]
    with tempfile.TemporaryDirectory() as tmp:
        ip, op = Path(tmp) / 'in.txt', Path(tmp) / 'out.txt'
        tests = [(inst, s, ok, 'A') for s, ok in cases] + [(i, s, True, m) for i, s, m in models]
        for i, s, ok, m in tests:
            ip.write_text('\n'.join(i) + '\n')
            op.write_text('\n'.join(s) + '\n')
            try:
                sprawdz(ip, op, m)
                got = True
            except Blad:
                got = False
            if got != ok:
                print(f'AUTOTEST NIE PRZESZEDL: {s} model {m}')
                return 1
    print(f'Autotest weryfikatora 2B: OK ({len(tests)} przypadkow).')
    return 0


def main(argv):
    model = 'A'
    if '--model' in argv:
        i = argv.index('--model')
        model = argv[i + 1].upper()
        del argv[i:i + 2]
    if argv == ['--autotest']:
        return autotest()
    if len(argv) != 2:
        print(__doc__)
        if len(argv) == 0 and sys.stdin and sys.stdin.isatty():
            input('Enter zamyka okno...')
        return 2
    a, b = Path(argv[0]), Path(argv[1])
    if a.is_dir():
        return seria(a, b, model)
    try:
        value = sprawdz(a, b, model)
        print(f'OK  kryterium = {value}  (model {model})')
        return 0
    except Blad as e:
        print(f'BLAD  {e}')
        return 1
    except Exception as e:
        print(f'BLAD  odczyt: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
