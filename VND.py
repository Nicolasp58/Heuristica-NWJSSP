import time

# ── Parámetros de vecindarios ─────────────────────────────────────────────────
INSERT_K   = 3
TWOOPT_LEN = 3   # segmento exactamente de longitud 3 (antes era 3..5)
MAX_CACHE  = 80_000

NEIGHBORHOODS_VND = ['swap', 'insert', '2opt']


# ── Precómputo ────────────────────────────────────────────────────────────────
def precompute(n, ops):
    offsets, totals, machine_map = [], [], []
    for j in range(n):
        acc, off, mmap = 0, [], {}
        for machine, p in ops[j]:
            off.append(acc)
            mmap[machine] = acc
            acc += p
        offsets.append(off)
        totals.append(acc)
        machine_map.append(mmap)
    return offsets, totals, machine_map


# ── Evaluación ────────────────────────────────────────────────────────────────
def evaluate_sequence(sequence, release_dates, ops, offsets, totals, machine_map):
    tracker, start_times = {}, [0] * len(sequence)
    for job in sequence:
        s_j = release_dates[job]
        for machine, off_v in machine_map[job].items():
            if machine in tracker:
                candidate = tracker[machine] - off_v
                if candidate > s_j:
                    s_j = candidate
        start_times[job] = s_j
        for u, (maq_u, p_u) in enumerate(ops[job]):
            val = s_j + offsets[job][u] + p_u
            if maq_u not in tracker or val > tracker[maq_u]:
                tracker[maq_u] = val
    Z = sum(start_times[j] + totals[j] for j in range(len(sequence)))
    return Z, start_times


def _cached_eval(seq, release_dates, ops, offsets, totals, machine_map, cache):
    key = tuple(seq)
    if key in cache:
        return cache[key], True
    Z, _ = evaluate_sequence(seq, release_dates, ops, offsets, totals, machine_map)
    if len(cache) < MAX_CACHE:
        cache[key] = Z
    return Z, False


# ── Movimientos ───────────────────────────────────────────────────────────────
def _do_swap(seq, i):
    s = seq[:]
    s[i], s[i + 1] = s[i + 1], s[i]
    return s

def _do_insert(seq, i, j_dest):
    s = seq[:]
    job = s.pop(i)
    s.insert(j_dest, job)
    return s

def _do_2opt(seq, i, j):
    s = seq[:]
    s[i:j + 1] = s[i:j + 1][::-1]
    return s


# ── Generadores de movimientos ────────────────────────────────────────────────
def _gen_swap(n):
    for i in range(n - 1):
        yield (i,)

def _gen_insert(n, k=INSERT_K):
    for i in range(n):
        lo = max(0, i - k)
        hi = min(n - 1, i + k)
        for j_orig in range(lo, hi + 1):
            if j_orig in (i - 1, i, i + 1):
                continue
            j_dest = j_orig if j_orig < i else j_orig - 1
            yield (i, j_dest)

def _gen_2opt(n, length=TWOOPT_LEN):
    """Genera solo segmentos de longitud exacta = TWOOPT_LEN."""
    for i in range(n - length + 1):
        yield (i, i + length - 1)

def _get_gen_fn(nbh, n):
    if nbh == 'swap':
        return _gen_swap(n), _do_swap
    elif nbh == 'insert':
        return _gen_insert(n), _do_insert
    else:
        return _gen_2opt(n), _do_2opt


# ── Un paso FI en vecindario N_j ──────────────────────────────────────────────
def _fi_step(seq, cur_Z, nbh,
             release_dates, ops, offsets, totals, machine_map,
             cache, deadline):
    """
    First Improvement: devuelve el primer vecino que mejore.
    Si no hay mejora devuelve (seq, cur_Z, evals, False).
    """
    n = len(seq)
    evals = 0
    gen, fn = _get_gen_fn(nbh, n)

    for move in gen:
        if deadline and time.time() >= deadline:
            return seq, cur_Z, evals, True   # time_out
        cand = fn(seq, *move)
        Z_cand, fc = _cached_eval(cand, release_dates, ops,
                                  offsets, totals, machine_map, cache)
        if not fc:
            evals += 1
        if Z_cand < cur_Z:
            return cand, Z_cand, evals, False  # mejora encontrada

    return seq, cur_Z, evals, False  # sin mejora


# ── VND principal ─────────────────────────────────────────────────────────────
def run_vnd(n, m, ops, release_dates,
            initial_sequence, Z_initial,
            deadline=None,
            cache=None):
    
    if cache is None:
        cache = {}

    offsets, totals, machine_map = precompute(n, ops)

    key_init = tuple(initial_sequence)
    if len(cache) < MAX_CACHE:
        cache[key_init] = Z_initial

    t0       = time.time()
    cur_seq  = initial_sequence[:]
    cur_Z    = Z_initial
    tot_its  = 0
    tot_ev   = 0
    improv   = {nbh: 0 for nbh in NEIGHBORHOODS_VND}
    time_out = False

    j = 0
    while j < len(NEIGHBORHOODS_VND):
        if deadline and time.time() >= deadline:
            time_out = True
            break

        nbh = NEIGHBORHOODS_VND[j]
        new_seq, new_Z, ev, timed = _fi_step(
            cur_seq, cur_Z, nbh,
            release_dates, ops, offsets, totals, machine_map,
            cache, deadline
        )
        tot_ev += ev

        if timed:
            time_out = True
            break

        if new_Z < cur_Z:      # mejoró → volver a N1
            cur_seq = new_seq
            cur_Z   = new_Z
            improv[nbh] += 1
            tot_its += 1
            j = 0
        else:                   # no mejoró → avanzar
            j += 1

    _, start_times = evaluate_sequence(
        cur_seq, release_dates, ops, offsets, totals, machine_map)

    return {
        'Z'           : cur_Z,
        'sequence'    : cur_seq,
        'start_times' : start_times,
        'iterations'  : tot_its,
        'evaluations' : tot_ev,
        'time_ms'     : (time.time() - t0) * 1000,
        'improvements': improv,
        'time_out'    : time_out,
    }