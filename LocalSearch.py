import time

INSERT_K   = 3
TWOOPT_L   = 5
TWOOPT_MIN = 3
MAX_CACHE  = 80_000


#  Precómputo
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


#  Evaluación
def evaluate_sequence(sequence, release_dates, ops, offsets, totals, machine_map):
    """Z = Σ C_j. Complejidad O(n·m)."""
    n, tracker, start_times = len(sequence), {}, [0] * len(sequence)
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
    Z = sum(start_times[j] + totals[j] for j in range(n))
    return Z, start_times


def _cached_eval(seq, release_dates, ops, offsets, totals, machine_map, cache):
    key = tuple(seq)
    if key in cache:
        return cache[key], True
    Z, _ = evaluate_sequence(seq, release_dates, ops, offsets, totals, machine_map)
    if len(cache) < MAX_CACHE:
        cache[key] = Z
    return Z, False


#  Movimientos
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


#  Generadores de movimientos
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


def _gen_2opt(n, min_len=TWOOPT_MIN, max_len=TWOOPT_L):
    
    for i in range(n):
        for length in range(min_len, max_len + 1):
            j = i + length - 1
            if j >= n:
                break
            yield (i, j)


def _get_moves_and_fn(neighborhood, n):
    if neighborhood == 'swap':
        return _gen_swap(n), _do_swap
    elif neighborhood == 'insert':
        return _gen_insert(n), _do_insert
    else:
        return _gen_2opt(n), _do_2opt


#  Best Improvement
def local_search_BI(sequence, Z_init, release_dates, ops,
                    offsets, totals, machine_map,
                    neighborhood, deadline, cache):
    
    n        = len(sequence)
    cur_seq  = sequence[:]
    cur_Z    = Z_init
    iters    = 0
    evals    = 0
    improved = True

    while improved:
        if deadline and time.time() >= deadline:
            break
        improved    = False
        best_cand   = None
        best_cand_Z = cur_Z
        gen, fn     = _get_moves_and_fn(neighborhood, n)

        for move in gen:
            if deadline and time.time() >= deadline:
                break
            cand       = fn(cur_seq, *move)
            Z_cand, fc = _cached_eval(cand, release_dates, ops,
                                      offsets, totals, machine_map, cache)
            if not fc:
                evals += 1
            if Z_cand < best_cand_Z:
                best_cand_Z = Z_cand
                best_cand   = cand

        if best_cand is not None:
            cur_seq  = best_cand
            cur_Z    = best_cand_Z
            improved = True
            iters   += 1

    return cur_seq, cur_Z, iters, evals


#  First Improvement
def local_search_FI(sequence, Z_init, release_dates, ops,
                    offsets, totals, machine_map,
                    neighborhood, deadline, cache):
    
    n        = len(sequence)
    cur_seq  = sequence[:]
    cur_Z    = Z_init
    iters    = 0
    evals    = 0
    improved = True

    while improved:
        if deadline and time.time() >= deadline:
            break
        improved = False
        gen, fn  = _get_moves_and_fn(neighborhood, n)

        for move in gen:
            if deadline and time.time() >= deadline:
                break
            cand       = fn(cur_seq, *move)
            Z_cand, fc = _cached_eval(cand, release_dates, ops,
                                      offsets, totals, machine_map, cache)
            if not fc:
                evals += 1
            if Z_cand < cur_Z:
                cur_seq  = cand
                cur_Z    = Z_cand
                improved = True
                iters   += 1
                break    # ← primer mejora encontrada, reiniciar exploración

    return cur_seq, cur_Z, iters, evals


#  Interfaz pública
NEIGHBORHOODS = ['swap', 'insert', '2opt']
CRITERIA      = ['BI', 'FI']
_LS_FN        = {'BI': local_search_BI, 'FI': local_search_FI}


def run_local_search(n, m, ops, release_dates,
                     initial_sequence, Z_initial,
                     neighborhood, criterion,
                     deadline=None,    # tiempo absoluto (time.time()+s), o None = sin límite
                     cache=None):
    
    if cache is None:
        cache = {}

    offsets, totals, machine_map = precompute(n, ops)

    key_init = tuple(initial_sequence)
    if len(cache) < MAX_CACHE:
        cache[key_init] = Z_initial

    t0    = time.time()
    ls_fn = _LS_FN[criterion]

    best_seq, best_Z, iters, evals = ls_fn(
        initial_sequence, Z_initial,
        release_dates, ops, offsets, totals, machine_map,
        neighborhood, deadline, cache
    )

    _, start_times = evaluate_sequence(
        best_seq, release_dates, ops, offsets, totals, machine_map)

    flow_times = [start_times[j] + totals[j] for j in range(n)]
    t_ms       = (time.time() - t0) * 1000

    return {
        'Z'          : best_Z,
        'sequence'   : best_seq,
        'start_times': start_times,
        'flow_times' : flow_times,
        'iterations' : iters,
        'evaluations': evals,
        'time_ms'    : t_ms,
    }