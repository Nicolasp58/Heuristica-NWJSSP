"""
GRASP1.py
---------
Construccion GRASP (Greedy Randomized Adaptive Search Procedure) para el NWJSSP.

Idea:
    Se repite `nsol` veces:
        1. Construccion greedy aleatorizada:
           En cada paso se construye una Restricted Candidate List (RCL) con
           los trabajos cuyo costo C_j satisface:
               C_j <= C_min + alpha * (C_max - C_min)
           Se selecciona aleatoriamente un trabajo de la RCL.
        2. Se conserva la mejor solucion encontrada.

Parametros:
    alpha : float  -> tamano relativo de la RCL
                      alpha=0 -> greedy puro | alpha=1 -> completamente aleatorio
    nsol  : int    -> numero de soluciones construidas
"""

import time
import random
from Evaluator import (
    precompute,
    make_machine_tracker,
    update_machine_tracker,
    earliest_start_tracked,
)


def _grasp_construction(n, ops, release_dates, alpha, offsets, totals, machine_map):
    """Una iteracion de la construccion GRASP."""
    tracker = make_machine_tracker(0)
    unscheduled = list(range(n))
    scheduled = []
    start_times = [0] * n

    while unscheduled:
        candidates = []
        for j in unscheduled:
            s_j = earliest_start_tracked(j, release_dates, machine_map[j], tracker)
            C_j = s_j + totals[j]
            candidates.append((j, s_j, C_j))

        C_min = min(c[2] for c in candidates)
        C_max = max(c[2] for c in candidates)
        threshold = C_min + alpha * (C_max - C_min)

        rcl = [(j, s_j) for j, s_j, C_j in candidates if C_j <= threshold]
        j_sel, s_sel = random.choice(rcl)

        start_times[j_sel] = s_sel
        update_machine_tracker(tracker, j_sel, s_sel, ops[j_sel], offsets[j_sel])
        scheduled.append(j_sel)
        unscheduled.remove(j_sel)

    flow_times = [start_times[j] + totals[j] for j in range(n)]
    Z = sum(flow_times)
    return scheduled, start_times, flow_times, Z


def GRASP1(n, m, ops, release_dates, alpha, nsol):
    """
    Algoritmo GRASP para el NWJSSP.

    Parameters
    ----------
    n, m          : int
    ops           : list[list[tuple]]
    release_dates : list[int]
    alpha         : float
    nsol          : int

    Returns
    -------
    Z, S, start_times, flow_times, t_ms
    """
    t_start = time.time()
    offsets, totals, machine_map = precompute(n, ops)

    best_Z = float("inf")
    best_S = best_start = best_flow = None

    for _ in range(nsol):
        S, st, ft, Z = _grasp_construction(
            n, ops, release_dates, alpha, offsets, totals, machine_map
        )
        if Z < best_Z:
            best_Z, best_S, best_start, best_flow = Z, S[:], st[:], ft[:]

    return best_Z, best_S, best_start, best_flow, (time.time() - t_start) * 1000
