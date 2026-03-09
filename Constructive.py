"""
Constructive.py
---------------
Metodo Constructivo Greedy Deterministico para el NWJSSP.

Idea:
    En cada paso, del conjunto de trabajos no programados se selecciona aquel
    que produce el menor tiempo de completacion C_j = s_j + total_j al ser
    el siguiente en el schedule.
    Desempate: menor tiempo total de procesamiento (criterio SPT-like).

    Se mantiene un tracker de disponibilidad de maquinas que permite calcular
    el earliest_start en O(m) en vez de O(n*m), reduciendo la complejidad
    total del algoritmo de O(n^2 * m) a O(n^2 + n*m).
"""

import time
from Evaluator import (
    precompute,
    make_machine_tracker,
    update_machine_tracker,
    earliest_start_tracked,
    lower_bound,
)


def Constructive(n, m, ops, release_dates):
    """
    Algoritmo constructivo greedy deterministico.

    Parameters
    ----------
    n             : int
    m             : int
    ops           : list[list[tuple(int,int)]]
    release_dates : list[int]

    Returns
    -------
    Z           : int
    S           : list[int]   orden de programacion
    start_times : list[int]   start_times[j] = tiempo de inicio de j
    flow_times  : list[int]   flow_times[j]  = tiempo de completacion de j
    t_ms        : float
    """
    t_start = time.time()

    offsets, totals, machine_map = precompute(n, ops)
    tracker = make_machine_tracker(m)

    unscheduled = set(range(n))
    scheduled = []
    start_times = [0] * n

    while unscheduled:
        best_job   = None
        best_C     = float("inf")
        best_total = float("inf")
        best_s     = 0

        for j in unscheduled:
            s_j = earliest_start_tracked(j, release_dates, machine_map[j], tracker)
            C_j = s_j + totals[j]

            if C_j < best_C or (C_j == best_C and totals[j] < best_total):
                best_job   = j
                best_C     = C_j
                best_total = totals[j]
                best_s     = s_j

        start_times[best_job] = best_s
        update_machine_tracker(tracker, best_job, best_s, ops[best_job], offsets[best_job])
        scheduled.append(best_job)
        unscheduled.remove(best_job)

    flow_times = [start_times[j] + totals[j] for j in range(n)]
    Z = sum(flow_times)
    t_ms = (time.time() - t_start) * 1000

    return Z, scheduled, start_times, flow_times, t_ms
