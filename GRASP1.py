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


#  Construcción GRASP (una iteración)
def _grasp_construction(n, ops, release_dates, alpha, offsets, totals, machine_map):
    tracker = {}
    unscheduled = list(range(n))
    scheduled = []
    start_times = [0] * n

    while unscheduled:
        candidates = []
        for j in unscheduled:
            s_j = _earliest_start(j, release_dates, machine_map[j], tracker)
            C_j = s_j + totals[j]
            candidates.append((j, s_j, C_j))

        C_min = min(c[2] for c in candidates)
        C_max = max(c[2] for c in candidates)
        threshold = C_min + alpha * (C_max - C_min)

        rcl = [(j, s_j) for j, s_j, C_j in candidates if C_j <= threshold]
        j_sel, s_sel = random.choice(rcl)

        start_times[j_sel] = s_sel
        _update_tracker(tracker, j_sel, s_sel, ops[j_sel], offsets[j_sel])
        scheduled.append(j_sel)
        unscheduled.remove(j_sel)

    flow_times = [start_times[j] + totals[j] for j in range(n)]
    Z = sum(flow_times)
    return scheduled, start_times, flow_times, Z


#  Algoritmo GRASP
def GRASP1(n, m, ops, release_dates, alpha, nsol):

    t_start = time.time()
    offsets, totals, machine_map = _precompute(n, ops)

    best_Z = float("inf")
    best_S = best_start = best_flow = None

    for _ in range(nsol):
        S, st, ft, Z = _grasp_construction(
            n, ops, release_dates, alpha, offsets, totals, machine_map
        )
        if Z < best_Z:
            best_Z, best_S, best_start, best_flow = Z, S[:], st[:], ft[:]

    return best_Z, best_S, best_start, best_flow, (time.time() - t_start) * 1000