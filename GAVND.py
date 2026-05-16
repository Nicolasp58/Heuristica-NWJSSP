import time
import random

from VND import precompute, evaluate_sequence, run_vnd


# ── Operadores genéticos (autocontenidos, sin dependencia de GA.py) ───────────

def _ox_crossover(p1, p2):
    """Order Crossover (OX) — Davis, 1985. Siempre genera permutaciones válidas."""
    n = len(p1)
    a, b = sorted(random.sample(range(n), 2))

    def _build(primary, secondary):
        child = [None] * n
        child[a:b+1] = primary[a:b+1]
        segment_set  = set(primary[a:b+1])
        fill = [x for x in secondary if x not in segment_set]
        idx  = 0
        for i in list(range(b+1, n)) + list(range(0, b+1)):
            if child[i] is None:
                child[i] = fill[idx]; idx += 1
        return child

    return _build(p1, p2), _build(p2, p1)


def _mutate_reinsertion(seq):
    """Reinserción aleatoria: extrae un trabajo y lo reinserta en otra posición."""
    s = seq[:]
    n = len(s)
    if n < 3:
        return s
    i   = random.randrange(n)
    job = s.pop(i)
    j   = random.randrange(n - 1)
    if j >= i:
        j += 1
    s.insert(j, job)
    return s


def _tournament_select(population, fitnesses, k):
    """Torneo de tamaño k: selecciona k individuos al azar, devuelve el mejor."""
    candidates = random.sample(range(len(population)), k)
    best       = min(candidates, key=lambda idx: fitnesses[idx])
    return population[best][:]


def _random_individual(n):
    """Genera una permutación aleatoria de n trabajos."""
    ind = list(range(n))
    random.shuffle(ind)
    return ind


def _init_population(n, pop_size, ops, release_dates, offsets, totals, machine_map):
    """Genera la población inicial aleatoria y evalúa cada individuo."""
    population = [_random_individual(n) for _ in range(pop_size)]
    fitnesses  = []
    for ind in population:
        Z, _ = evaluate_sequence(ind, release_dates, ops, offsets, totals, machine_map)
        fitnesses.append(Z)
    return population, fitnesses


def run_gavnd(n, m, ops, release_dates,
              pop_size=100,
              p_mut=0.20,
              tournament_k=4,
              t_vnd_max=2.0,
              vnd_every_n=1,
              deadline=None):
    
    t0 = time.time()
    offsets, totals, machine_map = precompute(n, ops)
    shared_cache = {}

    # ── Población inicial (aleatoria, sin VND) ─────────────────────────────────
    population, fitnesses = _init_population(
        n, pop_size, ops, release_dates, offsets, totals, machine_map)
    evaluations = pop_size

    best_idx = min(range(pop_size), key=lambda i: fitnesses[i])
    best_seq = population[best_idx][:]
    best_Z   = fitnesses[best_idx]

    generations = 0
    vnd_calls   = 0
    time_out    = False

    # ── Ciclo evolutivo ────────────────────────────────────────────────────────
    while True:
        if deadline and time.time() >= deadline:
            time_out = True
            break

        new_population = []
        new_fitnesses  = []

        # Elitismo: el mejor pasa directamente
        new_population.append(best_seq[:])
        new_fitnesses.append(best_Z)

        # Generar hijos y añadirlos directamente (sin VND en hijos)
        while len(new_population) < pop_size:
            if deadline and time.time() >= deadline:
                time_out = True
                break

            p1 = _tournament_select(population, fitnesses, tournament_k)
            p2 = _tournament_select(population, fitnesses, tournament_k)
            c1, c2 = _ox_crossover(p1, p2)

            if random.random() < p_mut:
                c1 = _mutate_reinsertion(c1)
            if random.random() < p_mut:
                c2 = _mutate_reinsertion(c2)

            for child in (c1, c2):
                if len(new_population) >= pop_size:
                    break
                Z_child, _ = evaluate_sequence(
                    child, release_dates, ops, offsets, totals, machine_map)
                evaluations += 1
                new_population.append(child)
                new_fitnesses.append(Z_child)
                if Z_child < best_Z:
                    best_Z = Z_child; best_seq = child[:]

        if time_out:
            break

        population = new_population
        fitnesses  = new_fitnesses
        generations += 1

        # Actualizar élite
        best_idx = min(range(len(fitnesses)), key=lambda i: fitnesses[i])
        if fitnesses[best_idx] < best_Z:
            best_Z   = fitnesses[best_idx]
            best_seq = population[best_idx][:]

        # VND al mejor individuo cada vnd_every_n generaciones
        if (generations % vnd_every_n == 0
                and not (deadline and time.time() >= deadline)):
            remaining = (deadline - time.time()) if deadline else t_vnd_max
            t_call    = min(t_vnd_max, max(0.05, remaining * 0.15))
            ls_dl     = time.time() + t_call
            if deadline:
                ls_dl = min(ls_dl, deadline)
            res = run_vnd(n, m, ops, release_dates,
                          initial_sequence=best_seq, Z_initial=best_Z,
                          deadline=ls_dl, cache=shared_cache)
            vnd_calls += 1
            if res['Z'] < best_Z:
                best_Z   = res['Z']
                best_seq = res['sequence'][:]
                # Reemplazar élite en población
                population[best_idx] = best_seq[:]
                fitnesses[best_idx]  = best_Z

    # ── Resultado final ────────────────────────────────────────────────────────
    _, start_times = evaluate_sequence(
        best_seq, release_dates, ops, offsets, totals, machine_map)

    return {
        'Z'          : best_Z,
        'sequence'   : best_seq,
        'start_times': start_times,
        'generations': generations,
        'evaluations': evaluations,
        'vnd_calls'  : vnd_calls,
        'time_ms'    : (time.time() - t0) * 1000,
        'time_out'   : time_out,
    }