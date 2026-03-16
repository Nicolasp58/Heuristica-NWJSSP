import time


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


#  Algoritmo constructivo
def Constructive(n, m, ops, release_dates):

    t_start = time.time()

    offsets, totals, machine_map = _precompute(n, ops)
    tracker = {}

    unscheduled = list(range(n))
    scheduled = []
    start_times = [0] * n

    # Paso 1: primer trabajo por menor tiempo total
    first_job = min(unscheduled, key=lambda j: totals[j])
    s_first = _earliest_start(first_job, release_dates, machine_map[first_job], tracker)
    start_times[first_job] = s_first
    _update_tracker(tracker, first_job, s_first, ops[first_job], offsets[first_job])
    scheduled.append(first_job)
    unscheduled.remove(first_job)

    # ── Paso 2: selección dinámica por menor C_j
    while unscheduled:
        best_job   = None
        best_C     = float("inf")
        best_total = float("inf")
        best_s     = 0

        for j in unscheduled:
            s_j = _earliest_start(j, release_dates, machine_map[j], tracker)
            C_j = s_j + totals[j]

            if C_j < best_C or (C_j == best_C and totals[j] < best_total):
                best_job   = j
                best_C     = C_j
                best_total = totals[j]
                best_s     = s_j

        start_times[best_job] = best_s
        _update_tracker(tracker, best_job, best_s, ops[best_job], offsets[best_job])
        scheduled.append(best_job)
        unscheduled.remove(best_job)

    flow_times = [start_times[j] + totals[j] for j in range(n)]
    Z = sum(flow_times)
    t_ms = (time.time() - t_start) * 1000

    return Z, scheduled, start_times, flow_times, t_ms