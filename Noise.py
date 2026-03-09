"""
Noise.py
--------
Metodo con Ruido (Noising Method) para el NWJSSP.

Idea:
    Se repite `nsol` veces:
        1. Construccion greedy con ruido multiplicativo:
           Al costo C_j de cada candidato se le agrega ruido:
               C_j_ruidoso = C_j * (1 + r * uniform(-1, 1))
           Se selecciona el candidato con menor costo ruidoso.
        2. Se conserva la mejor solucion encontrada.

    El ruido perturba la guia greedy sin eliminarla, permitiendo escapar de
    soluciones suboptimas que el greedy deterministico siempre elegiria.

Parametros:
    r    : float -> amplitud del ruido (r=0 -> greedy puro)
    nsol : int   -> numero de soluciones construidas
"""

import time
import random
from Evaluator import (
    precompute,
    make_machine_tracker,
    update_machine_tracker,
    earliest_start_tracked,
)


def _noise_construction(n, ops, release_dates, r, offsets, totals, machine_map):
    """Una iteracion de la construccion con ruido."""
    tracker = make_machine_tracker(0)
    unscheduled = list(range(n))
    scheduled = []
    start_times = [0] * n

    while unscheduled:
        best_job   = None
        best_noisy = float("inf")
        best_s     = 0

        for j in unscheduled:
            s_j = earliest_start_tracked(j, release_dates, machine_map[j], tracker)
            C_j = s_j + totals[j]
            C_j_noisy = C_j * (1.0 + r * random.uniform(-1.0, 1.0))

            if C_j_noisy < best_noisy:
                best_noisy = C_j_noisy
                best_job   = j
                best_s     = s_j

        start_times[best_job] = best_s
        update_machine_tracker(tracker, best_job, best_s, ops[best_job], offsets[best_job])
        scheduled.append(best_job)
        unscheduled.remove(best_job)

    flow_times = [start_times[j] + totals[j] for j in range(n)]
    Z = sum(flow_times)
    return scheduled, start_times, flow_times, Z


def Noise(n, m, ops, release_dates, r, nsol):
    """
    Noising Method para el NWJSSP.

    Parameters
    ----------
    n, m          : int
    ops           : list[list[tuple]]
    release_dates : list[int]
    r             : float
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
        S, st, ft, Z = _noise_construction(
            n, ops, release_dates, r, offsets, totals, machine_map
        )
        if Z < best_Z:
            best_Z, best_S, best_start, best_flow = Z, S[:], st[:], ft[:]

    return best_Z, best_S, best_start, best_flow, (time.time() - t_start) * 1000
