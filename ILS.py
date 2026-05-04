import time
import math
import random

from VND import run_vnd, precompute, evaluate_sequence

# ── Parámetros ────────────────────────────────────────────────────────────────
DEFAULT_PERTURB_K = 4
VND_INIT_MARGIN   = 1.5    # VND inicial = t_conv * 1.5
MAX_INIT_FRAC     = 0.40   # VND inicial nunca supera el 40% del presupuesto
VND_INT_MARGIN    = 1.5    # VND interno = t_conv * 1.5 ...
MAX_INT_FRAC      = 0.50   # ... pero nunca supera el 50% del tiempo RESTANTE
MIN_VND_T         = 0.05   # mínimo absoluto para un VND (instancias triviales)
T_INITIAL         = 0.02   # temperatura inicial SA


def _perturb(seq, k):
    """k-reinsert aleatorio. Orden superior a swap/insert/2-opt."""
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


def _accept(Z_new, Z_best, T):
    """Aceptación probabilística SA."""
    if Z_new < Z_best:
        return True
    if T <= 0:
        return False
    delta = (Z_new - Z_best) / Z_best
    return random.random() < math.exp(-delta / T)


def run_ils(n, m, ops, release_dates,
            initial_sequence, Z_initial,
            perturb_k=DEFAULT_PERTURB_K,
            t_conv_s=None,
            t_initial=None,
            deadline=None,
            cache=None):
    
    if cache is None:
        cache = {}

    offsets, totals, machine_map = precompute(n, ops)
    t0           = time.time()
    total_budget = (deadline - t0) if deadline else float('inf')
    # temperatura efectiva: parámetro externo o constante global
    T_EFF = t_initial if t_initial is not None else T_INITIAL

    # tiempo base para VNDs
    t_conv = max(t_conv_s if t_conv_s else 0.0, MIN_VND_T)

    # ── VND inicial: 1.5x t_conv, máx 40% del presupuesto ───────────────────
    vnd_init_t = min(t_conv * VND_INIT_MARGIN,
                     total_budget * MAX_INIT_FRAC)
    vnd_init_t = max(vnd_init_t, MIN_VND_T)

    if deadline:
        init_deadline = min(t0 + vnd_init_t, deadline)
    else:
        init_deadline = None

    res0 = run_vnd(n, m, ops, release_dates,
                   initial_sequence, Z_initial,
                   deadline=init_deadline,
                   cache=cache)

    best_seq       = res0['sequence'][:]
    best_Z         = res0['Z']
    cur_seq        = best_seq[:]
    cur_Z          = best_Z
    tot_its        = res0['iterations']
    tot_ev         = res0['evaluations']
    ils_iters      = 0
    accepted_worse = 0
    history        = []

    # tiempo base del VND interno (fijo para toda la ejecución)
    vnd_int_base = max(t_conv * VND_INT_MARGIN, MIN_VND_T)

    # ── Bucle ILS ─────────────────────────────────────────────────────────────
    while True:
        # ── Chequeo deadline global — ÚNICA fuente de parada por tiempo ───────
        if deadline and time.time() >= deadline:
            break

        t_remaining = (deadline - time.time()) if deadline else float('inf')

        # si queda menos de MIN_VND_T no vale la pena una iteración más
        if t_remaining < MIN_VND_T:
            break

        # temperatura actual (enfriamiento lineal)
        if deadline:
            t_elapsed = time.time() - t0
            T = T_EFF * max(0.0, 1.0 - t_elapsed / total_budget)
        else:
            T = 0.0

        # perturbación
        s_pert = _perturb(cur_seq, perturb_k)
        Z_pert, _ = evaluate_sequence(
            s_pert, release_dates, ops, offsets, totals, machine_map)
        tot_ev += 1

        # ── Tiempo del VND interno ────────────────────────────────────────────
        # Usar 1.5x t_conv, pero acotado al 50% del tiempo restante.
        # Esto garantiza que si queda tiempo, siempre hay margen para
        # al menos otra iteración después de este VND.
        if deadline:
            t_remaining_now = deadline - time.time()
            vnd_int_t = min(vnd_int_base,
                            t_remaining_now * MAX_INT_FRAC)
            vnd_int_t = max(vnd_int_t, MIN_VND_T)
            vnd_deadline = min(time.time() + vnd_int_t, deadline)
        else:
            vnd_int_t    = vnd_int_base
            vnd_deadline = None

        res = run_vnd(n, m, ops, release_dates,
                      s_pert, Z_pert,
                      deadline=vnd_deadline,
                      cache=cache)

        tot_its   += res['iterations']
        tot_ev    += res['evaluations']
        ils_iters += 1
        # ── time_out del VND interno NO para el bucle ILS ────────────────────
        # El bucle solo para por el deadline global (chequeo al inicio del while)

        Z_candidate = res['Z']
        accepted    = _accept(Z_candidate, cur_Z, T)

        if accepted:
            cur_seq = res['sequence'][:]
            cur_Z   = Z_candidate
            if Z_candidate < best_Z:
                best_seq = cur_seq[:]
                best_Z   = Z_candidate
            elif Z_candidate > best_Z:
                accepted_worse += 1

        history.append((ils_iters, Z_pert, Z_candidate, best_Z, accepted))

    _, start_times = evaluate_sequence(
        best_seq, release_dates, ops, offsets, totals, machine_map)

    # vnd_int_t final reportado (el de la última iteración o el base si no hubo)
    final_vnd_int = round(min(vnd_int_base,
                              total_budget * MAX_INT_FRAC), 3) if deadline else round(vnd_int_base, 3)

    return {
        'Z'             : best_Z,
        'sequence'      : best_seq,
        'start_times'   : start_times,
        'iterations'    : tot_its,
        'ils_iters'     : ils_iters,
        'evaluations'   : tot_ev,
        'time_ms'       : (time.time() - t0) * 1000,
        'time_out'      : True,   # siempre para por deadline (o por MIN_VND_T)
        'history'       : history,
        'accepted_worse': accepted_worse,
        'perturb_k'     : perturb_k,
        'T_initial'     : T_EFF,
        'vnd_init_t'    : round(vnd_init_t, 3),
        'vnd_int_t'     : final_vnd_int,
        't_conv_s'      : round(t_conv, 3),
    }