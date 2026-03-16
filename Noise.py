import time
import random


#  Funciones de evaluación (autocontenidas)
def _precompute(n, ops):
    offsets = []
    totals = []
    machine_map = []
    for j in range(n):
        acc = 0
        off = []
        mmap = {}
        for machine, p in ops[j]:
            off.append(acc)
            mmap[machine] = acc
            acc += p
        offsets.append(off)
        totals.append(acc)
        machine_map.append(mmap)
    return offsets, totals, machine_map


def _earliest_start(j, release_dates, machine_map_j, tracker):
    s_j = release_dates[j]
    for machine, off_v in machine_map_j.items():
        if machine in tracker:
            candidate = tracker[machine] - off_v
            if candidate > s_j:
                s_j = candidate
    return s_j


def _update_tracker(tracker, k, s_k, ops_k, offsets_k):
    for u, (maq_u, p_ku) in enumerate(ops_k):
        val = s_k + offsets_k[u] + p_ku
        if maq_u not in tracker or val > tracker[maq_u]:
            tracker[maq_u] = val


#  Construcción con ruido (una iteración)
def _noise_construction(n, ops, release_dates, r, offsets, totals, machine_map):
    tracker = {}
    unscheduled = list(range(n))
    scheduled = []
    start_times = [0] * n

    while unscheduled:
        best_job   = None
        best_noisy = float("inf")
        best_s     = 0

        for j in unscheduled:
            s_j = _earliest_start(j, release_dates, machine_map[j], tracker)
            C_j = s_j + totals[j]
            C_j_noisy = C_j * (1.0 + r * random.uniform(-1.0, 1.0))

            if C_j_noisy < best_noisy:
                best_noisy = C_j_noisy
                best_job   = j
                best_s     = s_j

        start_times[best_job] = best_s
        _update_tracker(tracker, best_job, best_s, ops[best_job], offsets[best_job])
        scheduled.append(best_job)
        unscheduled.remove(best_job)

    flow_times = [start_times[j] + totals[j] for j in range(n)]
    Z = sum(flow_times)
    return scheduled, start_times, flow_times, Z


#  Algoritmo Noise
def Noise(n, m, ops, release_dates, r, nsol):

    t_start = time.time()
    offsets, totals, machine_map = _precompute(n, ops)

    best_Z = float("inf")
    best_S = best_start = best_flow = None

    for _ in range(nsol):
        S, st, ft, Z = _noise_construction(
            n, ops, release_dates, r, offsets, totals, machine_map
        )
        if Z < best_Z:
            best_Z, best_S, best_start, best_flow = Z, S[:], st[:], ft[:]

    return best_Z, best_S, best_start, best_flow, (time.time() - t_start) * 1000