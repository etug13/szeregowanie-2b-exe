"""Zadanie 2B: Q4 | r_j, S_ij | suma opóźnień. Plik samodzielny (pod PyInstaller).

Użycie: algorytm2b <instancja> <wynik> [limit_s]   (domyślnie limit = n/20)
Model czyszczenia: zmienna MODEL poniżej lub env ALG2B_MODEL=A|B.
  A: C_j = max(r_j, C_i + S_ij) + ceil(b_k p_j)
  B: C_j = max(r_j, C_i) + S_ij + ceil(b_k p_j)
Pierwsze zadanie na maszynie: C_j = r_j + ceil(b_k p_j) (bez czyszczenia).

Idea: kilka konstrukcji zachłannych (wstawianie zadań w kolejności EDD/slack
w najlepsze miejsce dowolnej maszyny) -> symulowane wyżarzanie z ruchami
przeniesienia i zamiany; ocena przyrostowa od zmienionej pozycji (prefiksy
czasów zakończenia), z wczesnym przerwaniem, gdy ruch na pewno odpadnie.
"""

import math
import os
import random
import sys
import time

T_START = time.perf_counter()
MODEL = os.environ.get('ALG2B_MODEL', 'A').upper()
M = 4


def read_instance(path):
    with open(path, encoding='utf-8-sig') as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    n = int(lines[0])
    speeds = []
    for tok in lines[1].split()[:3]:
        whole, _, frac = tok.partition('.')
        den = 10 ** len(frac)
        speeds.append((int(whole or '0') * den + int(frac or '0'), den))
    speeds.append((1, 1))
    p, r, d = [], [], []
    for j in range(n):
        a, b, c = map(int, lines[2 + j].split()[:3])
        p.append(a); r.append(b); d.append(c)
    S = [list(map(int, lines[2 + n + j].split())) for j in range(n)]
    # Dokładne ceil(b*p) w liczbach całkowitych (bez błędów float).
    dur = [[(num * p[j] + den - 1) // den for j in range(n)] for num, den in speeds]
    return n, r, d, S, dur


class Solver:
    def __init__(self, n, r, d, S, dur, model):
        self.n, self.r, self.d, self.S, self.dur = n, r, d, S, dur
        self.A = model == 'A'

    # --- ocena -----------------------------------------------------------
    def machine_cost(self, k, seq):
        r, d, S, du, A = self.r, self.d, self.S, self.dur[k], self.A
        t = 0; prev = -1; tot = 0
        for j in seq:
            if prev < 0:
                t = r[j] + du[j]
            elif A:
                s = t + S[prev][j]
                t = (s if s > r[j] else r[j]) + du[j]
            else:
                t = (t if t > r[j] else r[j]) + S[prev][j] + du[j]
            if t > d[j]:
                tot += t - d[j]
            prev = j
        return tot

    def build_prefix(self, k, seq):
        """fin[i] = C po i-tym zadaniu, cum[i] = suma opóźnień seq[:i+1]."""
        r, d, S, du, A = self.r, self.d, self.S, self.dur[k], self.A
        fin = []; cum = []; t = 0; prev = -1; tot = 0
        for j in seq:
            if prev < 0:
                t = r[j] + du[j]
            elif A:
                s = t + S[prev][j]
                t = (s if s > r[j] else r[j]) + du[j]
            else:
                t = (t if t > r[j] else r[j]) + S[prev][j] + du[j]
            if t > d[j]:
                tot += t - d[j]
            fin.append(t); cum.append(tot)
            prev = j
        return fin, cum

    def tail_cost(self, k, seq, start, fin, items, cap):
        """Suma opóźnień zadań `items` dopisanych po seq[:start] (fin to prefiks).
        Przerywa i zwraca None, gdy suma przekroczy cap."""
        r, d, S, du, A = self.r, self.d, self.S, self.dur[k], self.A
        if start > 0:
            t = fin[start - 1]; prev = seq[start - 1]
        else:
            t = 0; prev = -1
        tot = 0
        for j in items:
            if prev < 0:
                t = r[j] + du[j]
            elif A:
                s = t + S[prev][j]
                t = (s if s > r[j] else r[j]) + du[j]
            else:
                t = (t if t > r[j] else r[j]) + S[prev][j] + du[j]
            if t > d[j]:
                tot += t - d[j]
                if tot > cap:
                    return None
            prev = j
        return tot

    # --- konstrukcje -----------------------------------------------------
    def greedy_insert(self, order, deadline):
        """Każde zadanie wstawiane w najtańsze miejsce (maszyna, pozycja)."""
        queues = [[] for _ in range(M)]
        costs = [0] * M
        for j in order:
            best = None
            for k in range(M):
                q = queues[k]
                # Wstawianie tylko w ostatnie ~12 pozycji: tanio i zwykle wystarcza.
                lo = max(0, len(q) - 12)
                for pos in range(lo, len(q) + 1):
                    q.insert(pos, j)
                    c = self.machine_cost(k, q) - costs[k]
                    del q[pos]
                    key = (c, self.dur[k][j], k)
                    if best is None or key < best[0]:
                        best = (key, k, pos)
            _, k, pos = best
            queues[k].insert(pos, j)
            costs[k] = self.machine_cost(k, queues[k])
            if time.perf_counter() > deadline:
                # Awaryjnie: resztę dopisz na koniec najmniej obciążonej maszyny.
                rest = order[order.index(j) + 1:]
                for jj in rest:
                    k = min(range(M), key=lambda m: len(queues[m]))
                    queues[k].append(jj)
                break
        return queues

    def greedy_append(self, order):
        """Szybka: dopisanie na koniec maszyny o min. (opóźnienie, koniec)."""
        r, d, S, dur, A = self.r, self.d, self.S, self.dur, self.A
        queues = [[] for _ in range(M)]
        ends = [0] * M
        for j in order:
            best = None
            for k in range(M):
                q = queues[k]
                if not q:
                    t = r[j] + dur[k][j]
                elif A:
                    t = max(r[j], ends[k] + S[q[-1]][j]) + dur[k][j]
                else:
                    t = max(r[j], ends[k]) + S[q[-1]][j] + dur[k][j]
                key = (max(0, t - d[j]), t)
                if best is None or key < best[0]:
                    best = (key, k, t)
            _, k, t = best
            queues[k].append(j); ends[k] = t
        return queues

    def total(self, queues):
        return sum(self.machine_cost(k, q) for k, q in enumerate(queues))

    # --- wyżarzanie ------------------------------------------------------
    def anneal(self, queues, deadline, rng):
        n = self.n
        pre = [self.build_prefix(k, q) for k, q in enumerate(queues)]
        cost = [c[-1] if c else 0 for _, c in pre]
        cur = sum(cost)
        best_val, best_q = cur, [q[:] for q in queues]
        if cur == 0 or n < 2:
            return best_val, best_q
        avg = max(1.0, cur / n)
        t0, t1 = avg * 2.0, 0.05
        t_begin = time.perf_counter()
        span = max(1e-6, deadline - t_begin)
        T = t0
        it = 0
        while True:
            it += 1
            if it & 127 == 0:
                now = time.perf_counter()
                if now >= deadline:
                    break
                frac = (now - t_begin) / span
                T = t0 * (t1 / t0) ** frac
            u = rng.random()
            thr = -T * math.log(u) if u > 0 else float('inf')
            a = rng.randrange(M)
            qa = queues[a]
            if not qa:
                continue
            i = rng.randrange(len(qa))
            if rng.random() < 0.6:
                # Przeniesienie zadania qa[i] na maszynę b, pozycja pos.
                b = rng.randrange(M)
                qb = queues[b]
                job = qa[i]
                if a == b:
                    if len(qa) < 2:
                        continue
                    pos = rng.randrange(len(qa))
                    if pos == i:
                        continue
                    new = qa[:i] + qa[i + 1:]
                    new.insert(pos, job)
                    s = min(i, pos)
                    old_tail = cost[a] - (pre[a][1][s - 1] if s else 0)
                    nt = self.tail_cost(a, qa, s, pre[a][0], new[s:], old_tail + thr)
                    if nt is None:
                        continue
                    delta = nt - old_tail
                    if delta <= thr:
                        queues[a] = new
                        pre[a] = self.build_prefix(a, new)
                        cost[a] = pre[a][1][-1]
                        cur += delta
                else:
                    pos = rng.randrange(len(qb) + 1)
                    old_a = cost[a] - (pre[a][1][i - 1] if i else 0)
                    old_b = cost[b] - (pre[b][1][pos - 1] if pos else 0)
                    na = self.tail_cost(a, qa, i, pre[a][0], qa[i + 1:], old_a + old_b + thr)
                    if na is None:
                        continue
                    nb = self.tail_cost(b, qb, pos, pre[b][0], [job] + qb[pos:],
                                        old_a + old_b + thr - na)
                    if nb is None:
                        continue
                    delta = na + nb - old_a - old_b
                    if delta <= thr:
                        del qa[i]
                        qb.insert(pos, job)
                        pre[a] = self.build_prefix(a, qa)
                        pre[b] = self.build_prefix(b, qb)
                        cost[a] = pre[a][1][-1] if qa else 0
                        cost[b] = pre[b][1][-1]
                        cur += delta
            else:
                # Zamiana dwóch zadań (także między maszynami).
                b = rng.randrange(M)
                qb = queues[b]
                if not qb:
                    continue
                jdx = rng.randrange(len(qb))
                if a == b:
                    if i == jdx:
                        continue
                    s = min(i, jdx)
                    new = qa[:]
                    new[i], new[jdx] = new[jdx], new[i]
                    old_tail = cost[a] - (pre[a][1][s - 1] if s else 0)
                    nt = self.tail_cost(a, qa, s, pre[a][0], new[s:], old_tail + thr)
                    if nt is None:
                        continue
                    delta = nt - old_tail
                    if delta <= thr:
                        queues[a] = new
                        pre[a] = self.build_prefix(a, new)
                        cost[a] = pre[a][1][-1]
                        cur += delta
                else:
                    x, y = qa[i], qb[jdx]
                    old_a = cost[a] - (pre[a][1][i - 1] if i else 0)
                    old_b = cost[b] - (pre[b][1][jdx - 1] if jdx else 0)
                    na = self.tail_cost(a, qa, i, pre[a][0], [y] + qa[i + 1:], old_a + old_b + thr)
                    if na is None:
                        continue
                    nb = self.tail_cost(b, qb, jdx, pre[b][0], [x] + qb[jdx + 1:],
                                        old_a + old_b + thr - na)
                    if nb is None:
                        continue
                    delta = na + nb - old_a - old_b
                    if delta <= thr:
                        qa[i], qb[jdx] = y, x
                        pre[a] = self.build_prefix(a, qa)
                        pre[b] = self.build_prefix(b, qb)
                        cost[a] = pre[a][1][-1]
                        cost[b] = pre[b][1][-1]
                        cur += delta
            if cur < best_val:
                best_val = cur
                best_q = [q[:] for q in queues]
                if cur == 0:
                    break
        return best_val, best_q


def write_solution(path, value, queues):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'{value}\n')
        for q in queues:
            f.write(' '.join(str(j + 1) for j in q) + '\n')


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    n, r, d, S, dur = read_instance(sys.argv[1])
    limit = float(sys.argv[3]) if len(sys.argv) > 3 else n / 20
    # Limit dotyczy całego procesu; EXE (PyInstaller) traci czas na rozpakowanie.
    budget = limit * 0.6 - 0.5 if getattr(sys, 'frozen', False) else limit * 0.9 - 0.15
    deadline = T_START + max(0.05, budget)
    solver = Solver(n, r, d, S, dur, MODEL)
    rng = random.Random(12345)

    jobs = range(n)
    orders = [
        sorted(jobs, key=lambda j: (d[j], r[j])),                       # EDD
        sorted(jobs, key=lambda j: (d[j] - dur[3][j], r[j])),           # min slack
        sorted(jobs, key=lambda j: (r[j], d[j])),                       # wg gotowości
    ]
    cands = [solver.greedy_append(o) for o in orders]
    # Wstawianie jest droższe: tylko jeśli zostało dość czasu.
    ins_deadline = T_START + max(0.05, budget * 0.3)
    for o in orders[:2]:
        if time.perf_counter() < ins_deadline:
            cands.append(solver.greedy_insert(o, ins_deadline))
    queues = min(cands, key=solver.total)
    value, queues = solver.anneal(queues, deadline, rng)
    assert value == solver.total(queues)
    write_solution(sys.argv[2], value, queues)
    return 0


if __name__ == '__main__':
    sys.exit(main())
