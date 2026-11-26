"""Weryfikator czasu dzialania (zadanie 2B).

    czas.exe <program.exe> <instancja> <wynik> [limit_s]     jedno uruchomienie
    czas.exe <program.exe> <folder_instancji> <folder_wynikow> cala seria (wiersz po wierszu)

Limit domyslnie n/20 s (mozna wymusic opcja --limit X dla serii).
W serii pliki wynikowe maja nazwy out_<autor>_<program>_<n>.txt,
a na koniec powstaje CZASY.txt (kolumna do arkusza, przekroczenie: "CZAS =X").
Po przekroczeniu limitu program dostaje jeszcze chwile, zeby zmierzyc rzeczywisty czas,
potem jest zabijany. Kod wyjscia: 0 = wszystkie w limicie, 1 = przekroczenia/bledy.
"""
import os
import subprocess
import sys
import time
from pathlib import Path


def liczba_zadan(inst):
    with open(inst, encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():
                return int(line.split()[0])
    raise ValueError('pusty plik instancji')


def fmt(x):
    return f'{x:.3f}'.replace('.', ',')


def zabij(proc):
    if os.name == 'nt':  # jednoplikowy PyInstaller ma proces potomny
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc.kill()
    proc.wait()


def uruchom(program, inst, out, limit, log=None):
    """Zwraca (czas_s, status), status: OK / CZAS / KOD x / BRAK WYNIKU."""
    out = Path(out)
    if out.exists():
        out.unlink()
    limit_txt = f'{limit:g}'
    stream = open(log, 'w') if log else subprocess.DEVNULL
    try:
        t0 = time.perf_counter()
        proc = subprocess.Popen([str(program), str(inst), str(out), limit_txt],
                                stdout=stream, stderr=subprocess.STDOUT if log else subprocess.DEVNULL)
        try:
            code = proc.wait(timeout=2 * limit + 2)
            el = time.perf_counter() - t0
        except subprocess.TimeoutExpired:
            el = time.perf_counter() - t0
            zabij(proc)
            return el, 'CZAS (zabity)'
    finally:
        if log:
            stream.close()
    if el > limit:
        return el, 'CZAS'
    if code != 0:
        return el, f'KOD {code}'
    if not out.is_file():
        return el, 'BRAK WYNIKU'
    return el, 'OK'


def klucz(path):
    parts = Path(path).stem.split('_')
    try:
        return parts[1], int(parts[-1])
    except (IndexError, ValueError):
        return Path(path).stem, 0


def seria(program, inst_dir, wyn_dir, limit_force):
    insts = sorted(Path(inst_dir).glob('in_*.txt'), key=klucz)
    if not insts:
        print(f'Brak plikow in_*.txt w {inst_dir}')
        return 1
    wyn_dir = Path(wyn_dir)
    wyn_dir.mkdir(parents=True, exist_ok=True)
    name = Path(program).stem
    print(f'Program {Path(program).name}: {len(insts)} instancji, limit '
          f'{"n/20" if limit_force is None else limit_force} s, wyniki w {wyn_dir}\n')
    column, bad = [], 0
    for inst in insts:
        autor, n = klucz(inst)
        limit = limit_force if limit_force is not None else liczba_zadan(inst) / 20
        out = wyn_dir / f'out_{autor}_{name}_{n}.txt'
        el, status = uruchom(program, inst, out, limit, wyn_dir / f'log_{autor}_{n}.txt')
        if status.startswith('CZAS'):
            column.append(f'CZAS ={fmt(el)}')
        else:
            column.append(fmt(el))
        bad += status != 'OK'
        print(f'{inst.name:<24} {fmt(el):>8} s / {limit:g} s   {status}', flush=True)
    plik = wyn_dir / 'CZASY.txt'
    plik.write_text('\n'.join(column) + '\n', encoding='utf-8')
    print(f'\nW limicie i z wynikiem: {len(insts) - bad}/{len(insts)}. Kolumna do arkusza: {plik}')
    print('\n'.join(column))
    print(f'\nTeraz kryterium:  weryfikator.exe "{inst_dir}" "{wyn_dir}"')
    return 1 if bad else 0


def main(argv):
    limit_force = None
    if '--limit' in argv:
        i = argv.index('--limit')
        limit_force = float(argv[i + 1].replace(',', '.'))
        del argv[i:i + 2]
    if len(argv) not in (3, 4):
        print(__doc__)
        if len(argv) == 0 and sys.stdin and sys.stdin.isatty():
            input('Enter zamyka okno...')
        return 2
    program = Path(argv[0]).resolve()
    if not program.is_file():
        print(f'Nie ma programu {argv[0]}')
        return 2
    if Path(argv[1]).is_dir():
        return seria(program, argv[1], argv[2], limit_force)
    limit = float(argv[3].replace(',', '.')) if len(argv) == 4 else liczba_zadan(argv[1]) / 20
    el, status = uruchom(program, argv[1], argv[2], limit)
    print(f'czas {fmt(el)} s / limit {limit:g} s   {status}')
    return 0 if status == 'OK' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
