"""
Read.py
-------
Lectura de instancias NWJSSP desde archivos .txt

Formato esperado:
    Primera línea: n  m
    Siguientes n líneas: maq_1 p_1 maq_2 p_2 ... maq_m p_m  r_j

Retorna:
    n   -> número de trabajos
    m   -> número de máquinas
    ops -> lista de listas: ops[j] = [(maq, p_time), ...] en orden de operaciones
    r   -> lista de release dates: r[j]
"""


def read_nwjssp(filepath: str):
    """
    Lee una instancia NWJSSP desde un archivo .txt

    Parameters
    ----------
    filepath : str
        Ruta completa al archivo .txt de la instancia

    Returns
    -------
    n   : int               -> número de trabajos
    m   : int               -> número de máquinas
    ops : list[list[tuple]] -> ops[j] = [(machine, proc_time), ...] para cada operación de j
    r   : list[int]         -> r[j] = release date del trabajo j
    """
    with open(filepath, "r") as f:
        lines = [line.strip() for line in f if line.strip()]

    # Primera línea: n y m
    first = lines[0].split()
    n, m = int(first[0]), int(first[1])

    ops = []
    r = []

    for i in range(1, n + 1):
        tokens = lines[i].split()
        values = [int(t) for t in tokens]

        # Los últimos valor es el release date
        release_date = values[-1]

        # Los 2*m valores anteriores son pares (machine, proc_time)
        job_ops = []
        for k in range(m):
            machine = values[2 * k]
            proc_time = values[2 * k + 1]
            job_ops.append((machine, proc_time))

        ops.append(job_ops)
        r.append(release_date)

    return n, m, ops, r
