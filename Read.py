

def read_nwjssp(filepath: str):

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
