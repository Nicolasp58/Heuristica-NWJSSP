import time
import random

from VND import precompute, evaluate_sequence, run_vnd


# ── Decoder ───────────────────────────────────────────────────────────────────

def _decode(chromosome):
    """Convierte un cromosoma real [0,1]^n en una permutación de n trabajos.
    El trabajo con la clave más pequeña va primero (argsort ascendente)."""
    return sorted(range(len(chromosome)), key=lambda i: chromosome[i])


# ── Operadores BRKGA ──────────────────────────────────────────────────────────

def _random_chromosome(n):
    """Cromosoma aleatorio: n reales uniformes en [0,1]."""
    return [random.random() for _ in range(n)]


def _biased_crossover(elite_chr, nonelite_chr, p_bias):
    """Cruce paramétrico sesgado. Cada gen se toma del élite con prob p_bias."""
    return [elite_chr[i] if random.random() < p_bias else nonelite_chr[i]
            for i in range(len(elite_chr))]


def _perturb_ils(seq, k):
    """k-reinserciones aleatorias sobre la permutación (igual que ILS.py)."""
    s = seq[:]
    n = len(s)
    k = min(k, n)
    positions = random.sample(range(n), k)
    positions.sort(reverse=True)
    jobs = [s.pop(pos) for pos in positions]
    random.shuffle(jobs)
    for job in jobs:
        s.insert(random.randint(0, len(s)), job)
    return s


def _seq_to_chromosome(seq):
    """Convierte una permutación a un cromosoma de claves ordenadas.
    Asigna rangos equiespaciados: trabajo en posición i → clave i/(n-1).
    Así decode(_seq_to_chromosome(seq)) == seq exactamente."""
    n = len(seq)
    chr_ = [0.0] * n
    for rank, job in enumerate(seq):
        chr_[job] = rank / max(n - 1, 1)
    return chr_


# ── Evaluación de cromosoma ───────────────────────────────────────────────────

def _eval_chromosome(chromosome, release_dates, ops, offsets, totals, machine_map, cache):
    seq = _decode(chromosome)
    key = tuple(seq)
    if key in cache:
        return cache[key], seq, True
    Z, _ = evaluate_sequence(seq, release_dates, ops, offsets, totals, machine_map)
    if len(cache) < 80_000:
        cache[key] = Z
    return Z, seq, False


# ── Población inicial ─────────────────────────────────────────────────────────

def _init_population(n, pop_size, release_dates, ops, offsets, totals, machine_map, cache):
    population = [_random_chromosome(n) for _ in range(pop_size)]
    fitnesses  = []
    seqs       = []
    for chr_ in population:
        Z, seq, _ = _eval_chromosome(chr_, release_dates, ops, offsets, totals, machine_map, cache)
        fitnesses.append(Z)
        seqs.append(seq)
    return population, fitnesses, seqs


# ── ILS interno (perturbación + VND) ─────────────────────────────────────────

def _run_ils_step(best_seq, best_Z, n, m, ops, release_dates,
                  perturb_k, t_ils_max, deadline, cache):
    
    s_pert = _perturb_ils(best_seq, perturb_k)
    offsets, totals, machine_map = precompute(n, ops)
    Z_pert, _ = evaluate_sequence(s_pert, release_dates, ops, offsets, totals, machine_map)

    remaining = (deadline - time.time()) if deadline else t_ils_max
    t_call    = min(t_ils_max, max(0.05, remaining * 0.15))
    vnd_dl    = time.time() + t_call
    if deadline:
        vnd_dl = min(vnd_dl, deadline)

    res = run_vnd(n, m, ops, release_dates,
                  initial_sequence=s_pert, Z_initial=Z_pert,
                  deadline=vnd_dl, cache=cache)

    if res['Z'] < best_Z:
        return res['sequence'][:], res['Z'], True
    return best_seq, best_Z, False


# ── BRKGA+ILS principal ───────────────────────────────────────────────────────

def run_brkga_ils(n, m, ops, release_dates,
                  pop_size=100,
                  p_elite=0.15,
                  p_mutant=0.10,
                  p_bias=0.70,
                  ils_perturb_k=4,
                  t_ils_max=2.0,
                  ils_every_n=1,
                  deadline=None):
    
    t0 = time.time()
    offsets, totals, machine_map = precompute(n, ops)
    cache = {}

    # Tamaños de subpoblaciones
    n_elite   = max(1, int(round(pop_size * p_elite)))
    n_mutant  = max(1, int(round(pop_size * p_mutant)))
    n_crossed = pop_size - n_elite - n_mutant

    # ── Población inicial ──────────────────────────────────────────────────────
    population, fitnesses, seqs = _init_population(
        n, pop_size, release_dates, ops, offsets, totals, machine_map, cache)
    evaluations = pop_size

    # Ordenar por fitness (menor es mejor) — élite = los primeros n_elite
    order = sorted(range(pop_size), key=lambda i: fitnesses[i])
    population = [population[i] for i in order]
    fitnesses  = [fitnesses[i]  for i in order]
    seqs       = [seqs[i]       for i in order]

    best_Z   = fitnesses[0]
    best_seq = seqs[0][:]

    generations  = 0
    ils_calls    = 0
    ils_improved = 0
    time_out     = False

    # ── Ciclo BRKGA ────────────────────────────────────────────────────────────
    while True:
        if deadline and time.time() >= deadline:
            time_out = True
            break

        new_population = []
        new_fitnesses  = []
        new_seqs       = []

        # 1. Copiar élite intacta
        for i in range(n_elite):
            new_population.append(population[i][:])
            new_fitnesses.append(fitnesses[i])
            new_seqs.append(seqs[i][:])

        # 2. Generar mutantes
        for _ in range(n_mutant):
            if deadline and time.time() >= deadline:
                time_out = True
                break
            chr_ = _random_chromosome(n)
            Z, seq, _ = _eval_chromosome(
                chr_, release_dates, ops, offsets, totals, machine_map, cache)
            evaluations += 1
            new_population.append(chr_)
            new_fitnesses.append(Z)
            new_seqs.append(seq)

        if time_out:
            break

        # 3. Generar cruzados (élite × no-élite)
        for _ in range(n_crossed):
            if deadline and time.time() >= deadline:
                time_out = True
                break
            elite_idx    = random.randrange(n_elite)
            nonelite_idx = random.randint(n_elite, pop_size - 1)
            child_chr    = _biased_crossover(
                population[elite_idx], population[nonelite_idx], p_bias)
            Z, seq, _ = _eval_chromosome(
                child_chr, release_dates, ops, offsets, totals, machine_map, cache)
            evaluations += 1
            new_population.append(child_chr)
            new_fitnesses.append(Z)
            new_seqs.append(seq)

        if time_out:
            break

        # 4. Reordenar nueva población
        order      = sorted(range(len(new_fitnesses)), key=lambda i: new_fitnesses[i])
        population = [new_population[i] for i in order]
        fitnesses  = [new_fitnesses[i]  for i in order]
        seqs       = [new_seqs[i]       for i in order]

        generations += 1

        # Actualizar mejor global
        if fitnesses[0] < best_Z:
            best_Z   = fitnesses[0]
            best_seq = seqs[0][:]

        # 5. ILS sobre el mejor élite cada ils_every_n generaciones
        if (generations % ils_every_n == 0
                and not (deadline and time.time() >= deadline)):

            new_seq, new_Z, improved = _run_ils_step(
                best_seq, best_Z,
                n, m, ops, release_dates,
                ils_perturb_k, t_ils_max, deadline, cache)
            ils_calls += 1

            if improved:
                ils_improved += 1
                best_Z   = new_Z
                best_seq = new_seq[:]
                # Reinyectar en el espacio de cromosomas: reemplazar el mejor élite
                new_chr = _seq_to_chromosome(best_seq)
                population[0] = new_chr
                fitnesses[0]  = best_Z
                seqs[0]       = best_seq[:]

    # ── Resultado final ────────────────────────────────────────────────────────
    _, start_times = evaluate_sequence(
        best_seq, release_dates, ops, offsets, totals, machine_map)

    return {
        'Z'           : best_Z,
        'sequence'    : best_seq,
        'start_times' : start_times,
        'generations' : generations,
        'evaluations' : evaluations,
        'ils_calls'   : ils_calls,
        'ils_improved': ils_improved,
        'time_ms'     : (time.time() - t0) * 1000,
        'time_out'    : time_out,
    }
