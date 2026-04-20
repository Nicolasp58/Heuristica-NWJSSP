"""
main2.py
========
Orquestador principal – Trabajo 2, Heurística EAFIT.
Búsqueda local PURA (sin Multi-Start).

Distribución del tiempo
-----------------------
Las instancias pequeñas terminan en milisegundos (convergen al óptimo
local rápidamente). Las instancias grandes necesitan tiempo porque cada
evaluación de la FO es costosa y el vecindario es enorme.

El tiempo total (1 hora) se distribuye proporcionalmente al "peso" de
cada instancia, calculado como:  peso = n * m
Esto asigna más tiempo a instancias con más operaciones totales.
Las instancias pequeñas igual terminan antes del deadline — el sobrante
no se puede recuperar en búsqueda local pura, lo cual es correcto.

Ejecución: SECUENCIAL con deadlines absolutos por combinación.
Esto garantiza que el tiempo de reloj sea exacto.

Formato Excel (Anexo 3):
  A1 = Z,  B1 = tiempo_ms
  Fila 2 = s_0, s_1, ..., s_{n-1}

Solución inicial: Noise(r=0.5, nsol=1).
  Costo idéntico al Constructivo (~5% overhead).
  Produce una solución más débil que el greedy puro, dando más
  margen de mejora a la búsqueda local.
"""

import os
import time
from openpyxl import Workbook

from Read        import read_nwjssp
from Noise       import Noise
from LocalSearch import run_local_search, NEIGHBORHOODS, CRITERIA

# Parámetros de la solución inicial
NOISE_R    = 0.5   # ruido fuerte → solución peor que greedy, más margen de mejora
NOISE_NSOL = 1     # una sola construcción → costo idéntico al constructivo

INSTANCES_FOLDER = "NWJSSP Instances"
LB_FILE          = "lb.txt"
MAX_INSTANCES    = 14
TOTAL_TIME_S     = 3_600
STUDENT_NAME     = "NicolasPena"


def load_lower_bounds(lb_path):
    with open(lb_path) as f:
        return [int(line.strip()) for line in f if line.strip()]


def _instance_weight(n, m):
    """
    Peso de una instancia para distribución de tiempo.
    Proporcional al número total de operaciones: n * m.
    """
    return n * m


def _write_sheet_annex3(ws, Z, t_ms, start_times, n):
    """Formato exacto Anexo 3: fila 1 = Z, t_ms. Fila 2 = start times."""
    ws.cell(row=1, column=1, value=Z)
    ws.cell(row=1, column=2, value=round(t_ms))
    for j in range(n):
        ws.cell(row=2, column=j + 1, value=start_times[j])


def _build_excel(neighborhood, criterion, results_dict, instance_names):
    fname = f"NWJSSP_{STUDENT_NAME}_LS_{neighborhood}_{criterion}.xlsx"
    wb    = Workbook()
    wb.remove(wb.active)
    for iname in instance_names:
        if iname not in results_dict:
            continue
        rec = results_dict[iname]
        ws  = wb.create_sheet(title=iname[:31])
        _write_sheet_annex3(ws, rec['Z'], rec['time_ms'], rec['start_times'], rec['n'])
    wb.save(fname)
    print(f"  → {fname}")


def main():
    print("=" * 60)
    print("  NWJSSP — Búsqueda Local Pura (Trabajo 2)")
    print(f"  {STUDENT_NAME} — Universidad EAFIT")
    print("=" * 60)

    if not os.path.isdir(INSTANCES_FOLDER):
        print(f"ERROR: No se encontró '{INSTANCES_FOLDER}/'."); return
    if not os.path.isfile(LB_FILE):
        print(f"ERROR: No se encontró '{LB_FILE}'."); return

    lb_list        = load_lower_bounds(LB_FILE)
    all_files      = sorted(f for f in os.listdir(INSTANCES_FOLDER)
                            if f.endswith(".txt"))
    instance_files = all_files[:MAX_INSTANCES]
    n_inst         = len(instance_files)

    # Leer dimensiones para calcular pesos
    print("\n  Calculando distribución de tiempo por tamaño de instancia...")
    instance_dims = []
    for fname in instance_files:
        fp = os.path.join(INSTANCES_FOLDER, fname)
        n, m, _, _ = read_nwjssp(fp)
        instance_dims.append((n, m))

    weights      = [_instance_weight(n, m) for n, m in instance_dims]
    total_weight = sum(weights)
    n_combos     = len(NEIGHBORHOODS) * len(CRITERIA)   # 6

    # Tiempo por instancia proporcional a su peso
    time_per_inst = [TOTAL_TIME_S * w / total_weight for w in weights]

    print(f"\n  {'Instancia':<28} {'n':>6} {'m':>6} {'peso':>12} {'tiempo(s)':>10}")
    print(f"  {'─'*28} {'─'*6} {'─'*6} {'─'*12} {'─'*10}")
    for i, (fname, (n, m), t) in enumerate(zip(instance_files, instance_dims, time_per_inst)):
        iname = fname.replace(".txt", "")
        print(f"  {iname:<28} {n:>6} {m:>6} {n*m:>12,} {t:>10.1f}s")
    print(f"\n  Total: {sum(time_per_inst):.1f}s  |  {n_combos} combos/instancia\n")

    all_results    = {f"{nbh}_{crit}": {} for nbh in NEIGHBORHOODS for crit in CRITERIA}
    instance_names = []
    t_start        = time.time()

    for idx, filename in enumerate(instance_files):
        iname    = filename.replace(".txt", "")
        filepath = os.path.join(INSTANCES_FOLDER, filename)
        lb       = lb_list[idx] if idx < len(lb_list) else 0
        n, m     = instance_dims[idx]

        # Deadline absoluto del último slot de esta instancia
        # = inicio + suma de tiempos de todas las instancias hasta esta inclusive
        elapsed_before = sum(time_per_inst[:idx])
        elapsed_after  = sum(time_per_inst[:idx + 1])
        secs_per_combo = time_per_inst[idx] / n_combos

        print(f"\n{'─'*60}")
        print(f"  [{idx+1}/{n_inst}] {iname}  (LB={lb:,})")
        print(f"  n={n}, m={m}  |  tiempo asignado: {time_per_inst[idx]:.1f}s  "
              f"({secs_per_combo:.1f}s/combo)")
        print(f"{'─'*60}")

        _, ops, rd = read_nwjssp(filepath)[1], read_nwjssp(filepath)[2], read_nwjssp(filepath)[3]
        n2, m2, ops, rd = read_nwjssp(filepath)
        Z_init, seq_init, _, _, t_c = Noise(n2, m2, ops, rd, NOISE_R, NOISE_NSOL)
        gap_c = round((Z_init - lb) / lb * 100, 2) if lb > 0 else 0
        print(f"  Noise(r={NOISE_R}, nsol={NOISE_NSOL}): Z={Z_init:,}  gap={gap_c}%  t={round(t_c)}ms")

        instance_names.append(iname)
        combo_idx = 0

        for nbh in NEIGHBORHOODS:
            for crit in CRITERIA:
                # Deadline absoluto para esta combinación
                combo_start_offset = elapsed_before + combo_idx * secs_per_combo
                deadline = t_start + combo_start_offset + secs_per_combo
                combo_idx += 1

                # Ajuste si el proceso anterior se demoró más
                now = time.time()
                if deadline <= now:
                    deadline = now + 2.0   # mínimo 2s para al menos intentar

                res = run_local_search(
                    n2, m2, ops, rd,
                    seq_init, Z_init,
                    nbh, crit,
                    deadline=deadline
                )
                gap = round((res['Z'] - lb) / lb * 100, 2) if lb > 0 else 0
                print(f"  {nbh:6s}-{crit}: Z={res['Z']:,}  gap={gap}%  "
                      f"iters={res['iterations']}  evals={res['evaluations']}  "
                      f"t={round(res['time_ms'])}ms")

                all_results[f"{nbh}_{crit}"][iname] = {**res, 'n': n2}

    print(f"\n{'='*60}")
    print("  Generando archivos Excel (formato Anexo 3)...")
    for nbh in NEIGHBORHOODS:
        for crit in CRITERIA:
            _build_excel(nbh, crit, all_results[f"{nbh}_{crit}"], instance_names)

    elapsed_min = (time.time() - t_start) / 60
    print(f"\n  Tiempo total: {elapsed_min:.2f} minutos")
    print("  ¡Listo!")


if __name__ == "__main__":
    main()