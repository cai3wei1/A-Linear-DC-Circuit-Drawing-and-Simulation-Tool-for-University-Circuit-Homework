import re
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve


def parse_netlist(filepath):
    elements = []
    node_set = set()
    vsource_names = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('*'):
                continue
            parts = re.split(r'\s+', line)
            if len(parts) < 3:
                print(f"警告: 第 {line_num} 行格式不正确: {line}")
                continue
            name = parts[0]
            t = name[0].upper()
            try:
                if t == 'R':
                    n1, n2 = int(parts[1]), int(parts[2])
                    elements.append({'type': 'R', 'name': name, 'n1': n1, 'n2': n2, 'value': float(parts[3])})
                    node_set.update([n1, n2])
                elif t == 'V':
                    n1, n2 = int(parts[1]), int(parts[2])
                    elements.append({'type': 'V', 'name': name, 'n1': n1, 'n2': n2, 'value': float(parts[3])})
                    node_set.update([n1, n2])
                    vsource_names.append(name)
                elif t == 'I':
                    n1, n2 = int(parts[1]), int(parts[2])
                    elements.append({'type': 'I', 'name': name, 'n1': n1, 'n2': n2, 'value': float(parts[3])})
                    node_set.update([n1, n2])
                elif t == 'E':
                    n1, n2, nc1, nc2 = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                    elements.append({'type': 'E', 'name': name, 'n1': n1, 'n2': n2, 'nc1': nc1, 'nc2': nc2, 'gain': float(parts[5])})
                    node_set.update([n1, n2, nc1, nc2])
                    vsource_names.append(name)
                elif t == 'G':
                    n1, n2, nc1, nc2 = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                    elements.append({'type': 'G', 'name': name, 'n1': n1, 'n2': n2, 'nc1': nc1, 'nc2': nc2, 'gm': float(parts[5])})
                    node_set.update([n1, n2, nc1, nc2])
                elif t == 'H':
                    n1, n2 = int(parts[1]), int(parts[2])
                    elements.append({'type': 'H', 'name': name, 'n1': n1, 'n2': n2, 'vctrl': parts[3], 'gain': float(parts[4])})
                    node_set.update([n1, n2])
                    vsource_names.append(name)
                elif t == 'F':
                    n1, n2 = int(parts[1]), int(parts[2])
                    elements.append({'type': 'F', 'name': name, 'n1': n1, 'n2': n2, 'vctrl': parts[3], 'gain': float(parts[4])})
                    node_set.update([n1, n2])
            except Exception as e:
                print(f"错误: 第 {line_num} 行解析失败: {line}, {e}")
                raise
    if 0 not in node_set:
        raise ValueError("网表中未找到参考地节点 0")
    return elements, node_set, vsource_names


def solve_circuit(elements, node_set, vsource_names):
    non_ground = sorted([n for n in node_set if n != 0])
    node_to_idx = {n: i for i, n in enumerate(non_ground)}
    n = len(non_ground)
    vsrc_idx = {name: n + i for i, name in enumerate(vsource_names)}
    m = len(vsource_names)

    A = lil_matrix((n + m, n + m), dtype=np.float64)
    z = np.zeros(n + m, dtype=np.float64)

    def gi(node):
        return None if node == 0 else node_to_idx[node]

    def add_g(n1, n2, g):
        i, j = gi(n1), gi(n2)
        if i is not None: A[i, i] += g
        if j is not None: A[j, j] += g
        if i is not None and j is not None:
            A[i, j] -= g
            A[j, i] -= g

    def add_i(n1, n2, I):
        i, j = gi(n1), gi(n2)
        if i is not None: z[i] -= I
        if j is not None: z[j] += I

    def add_vs(n1, n2, V, k):
        i, j = gi(n1), gi(n2)
        if i is not None:
            A[i, k] += 1; A[k, i] += 1
        if j is not None:
            A[j, k] -= 1; A[k, j] -= 1
        z[k] = V

    for el in elements:
        t = el['type']
        if t == 'R':
            add_g(el['n1'], el['n2'], 1.0 / el['value'])
        elif t == 'V':
            add_vs(el['n1'], el['n2'], el['value'], vsrc_idx[el['name']])
        elif t == 'I':
            add_i(el['n1'], el['n2'], el['value'])
        elif t == 'E':
            k = vsrc_idx[el['name']]
            i, j = gi(el['n1']), gi(el['n2'])
            ic1, ic2 = gi(el['nc1']), gi(el['nc2'])
            if i is not None: A[i, k] += 1; A[k, i] += 1
            if j is not None: A[j, k] -= 1; A[k, j] -= 1
            if ic1 is not None: A[k, ic1] -= el['gain']
            if ic2 is not None: A[k, ic2] += el['gain']
        elif t == 'G':
            i, j = gi(el['n1']), gi(el['n2'])
            ic1, ic2 = gi(el['nc1']), gi(el['nc2'])
            if i is not None:
                if ic1 is not None: A[i, ic1] += el['gm']
                if ic2 is not None: A[i, ic2] -= el['gm']
            if j is not None:
                if ic1 is not None: A[j, ic1] -= el['gm']
                if ic2 is not None: A[j, ic2] += el['gm']
        elif t == 'H':
            k = vsrc_idx[el['name']]
            ck = vsrc_idx[el['vctrl']]
            i, j = gi(el['n1']), gi(el['n2'])
            if i is not None: A[i, k] += 1; A[k, i] += 1
            if j is not None: A[j, k] -= 1; A[k, j] -= 1
            A[k, ck] -= el['gain']
        elif t == 'F':
            ck = vsrc_idx[el['vctrl']]
            i, j = gi(el['n1']), gi(el['n2'])
            if i is not None: A[i, ck] += el['gain']
            if j is not None: A[j, ck] -= el['gain']

    x = spsolve(A.tocsr(), z)

    node_voltages = {0: 0.0}
    for node, idx in node_to_idx.items():
        node_voltages[node] = float(x[idx])
    vsrc_currents = {name: float(x[idx]) for name, idx in vsrc_idx.items()}

    return node_voltages, vsrc_currents