"""Test gotowego EXE na sztucznych instancjach: poprawność, kryterium (model A), limit n/20."""
import random, subprocess, sys, tempfile, time
from fractions import Fraction
from pathlib import Path


def make(n, seed):
    rng = random.Random(seed)
    b = [f'{rng.uniform(1.05, 2.0):.2f}' for _ in range(3)]
    jobs = []
    for _ in range(n):
        p = rng.randint(5, 100); r = rng.randint(0, n * 25); d = r + rng.randint(p, 6 * p)
        jobs.append((p, r, d))
    S = [[0 if i == j else rng.randint(1, 30) for j in range(n)] for i in range(n)]
    text = f'{n}\n{" ".join(b)}\n' + ''.join(f'{p} {r} {d}\n' for p, r, d in jobs) \
        + ''.join(' '.join(map(str, row)) + '\n' for row in S)
    return text, [Fraction(x) for x in b] + [Fraction(1)], jobs, S


def evaluate(speeds, jobs, S, queues):
    ids = [j for q in queues for j in q]
    assert sorted(ids) == list(range(1, len(jobs) + 1)), 'zadania nie tworzą permutacji 1..n'
    tot = 0
    for k, q in enumerate(queues):
        t = 0; prev = None
        for job in q:
            p, r, d = jobs[job - 1]
            dur = -(-speeds[k].numerator * p // speeds[k].denominator)
            t = (r if prev is None else max(r, t + S[prev][job - 1])) + dur
            tot += max(0, t - d); prev = job - 1
    return tot


def main(exe):
    fails = 0
    with tempfile.TemporaryDirectory() as tmp:
        for n in (50, 100, 250, 500):
            text, speeds, jobs, S = make(n, n)
            inp, out = Path(tmp) / f'in_{n}.txt', Path(tmp) / f'out_{n}.txt'
            inp.write_text(text)
            limit = n / 20
            t0 = time.perf_counter()
            subprocess.run([exe, str(inp), str(out), str(limit)], check=True)
            el = time.perf_counter() - t0
            lines = out.read_text().splitlines()
            lines += [''] * (5 - len(lines))
            declared = int(lines[0])
            queues = [list(map(int, l.split())) for l in lines[1:5]]
            actual = evaluate(speeds, jobs, S, queues)
            ok = actual == declared and el <= limit
            fails += not ok
            print(f'n={n} kryterium={actual} deklarowane={declared} czas={el:.2f}s limit={limit}s {"OK" if ok else "BŁĄD"}')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main(sys.argv[1])
