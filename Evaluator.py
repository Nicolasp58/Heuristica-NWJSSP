"""
Evaluator.py
------------
Funciones de evaluacion para el NWJSSP — version optimizada.

Conceptos clave (no-wait):
    - Si el trabajo j inicia en s_j, su operacion u comienza en:
          s_j + offset_j[u]    donde offset_j[u] = sum(p_j,0 ... p_j,u-1)
    - El tiempo de completacion del trabajo j es:
          C_j = s_j + total_j

Restriccion de maquina entre trabajos k (programado) y j (candidato):
    Para cada par de operaciones que usen la misma maquina:
        s_j >= s_k + offset_k[u] + p_ku - offset_j[v]

Optimizacion principal — machine_free_time:
    En lugar de recorrer todos los trabajos programados para calcular
    earliest_start, se mantiene para cada maquina el vector de restricciones
    agregadas. Cuando se programa el trabajo k con inicio s_k, se actualiza:
        machine_constraint[machine] = max(machine_constraint[machine],
                                          s_k + offset_k[u] + p_ku)
    Luego earliest_start(j) = max(r_j, max_over_v(machine_constraint[ops_j[v].machine]
                                                   - offset_j[v]))
    Esto reduce la complejidad de O(n*m) a O(m) por candidato.
"""


def precompute(n, ops):
    """
    Precomputa offsets, totales e indice por maquina para todos los trabajos.

    Returns
    -------
    offsets     : list[list[int]]
    totals      : list[int]
    machine_map : list[dict]  machine_map[j][machine] = offset de j en esa maquina
    """
    offsets = []
    totals = []
    machine_map = []

    for j in range(n):
        off = []
        acc = 0
        mmap = {}
        for machine, proc_time in ops[j]:
            off.append(acc)
            mmap[machine] = acc
            acc += proc_time
        offsets.append(off)
        totals.append(acc)
        machine_map.append(mmap)

    return offsets, totals, machine_map


def make_machine_tracker(m_count):
    """
    Crea el diccionario de restricciones de maquina.
    machine_avail[machine] = tiempo minimo en el que una nueva operacion
                             puede INICIAR en esa maquina (teniendo en cuenta
                             el offset del trabajo candidato).
    Mas precisamente: machine_avail[machine] = max(s_k + off_k[u] + p_ku)
    sobre todos los k programados y u tal que ops[k][u].machine == machine.
    """
    return {}   # vacío al inicio; claves = machine ids


def update_machine_tracker(tracker, k, s_k, ops_k, offsets_k):
    """
    Actualiza el tracker despues de programar el trabajo k con inicio s_k.

    Para cada operacion u de k en maquina machine_u:
        tracker[machine_u] = max(tracker[machine_u],
                                 s_k + offset_k[u] + p_ku)
    """
    for u, (machine_u, p_ku) in enumerate(ops_k):
        val = s_k + offsets_k[u] + p_ku
        if machine_u not in tracker or val > tracker[machine_u]:
            tracker[machine_u] = val


def earliest_start_tracked(j, release_dates, machine_map_j, tracker):
    """
    Calcula el tiempo de inicio mas temprano para j usando el tracker.

    s_j = max(r_j,  max over v { tracker[machine_v] - offset_j[v] })

    Parameters
    ----------
    j              : int
    release_dates  : list[int]
    machine_map_j  : dict   {machine: offset_j_v}  (precomputado para j)
    tracker        : dict   {machine: valor_acumulado}

    Returns
    -------
    s_j : int
    """
    s_j = release_dates[j]
    for machine, off_j_v in machine_map_j.items():
        if machine in tracker:
            candidate = tracker[machine] - off_j_v
            if candidate > s_j:
                s_j = candidate
    return s_j


def lower_bound(n, release_dates, totals):
    """
    Cota inferior: LB = sum_j (r_j + total_j)
    (relaja todas las restricciones de conflicto de maquinas)
    """
    return sum(r + t for r, t in zip(release_dates, totals))
