import sys, zipfile, csv, io, json, os, time
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

PROJ_DIR = r'C:\Projetos\MapaDaUrna'
SCRATCH_BRAIN = r'C:\Users\renan\.gemini\antigravity\brain\01ee89c1-0cb6-4be4-8ef3-288e34eca1bf\scratch'
zip_path = os.path.join(SCRATCH_BRAIN, 'votacao_secao_2026_BR.zip')
dash_path = os.path.join(PROJ_DIR, 'data', 'dashboard_data.json')
web_data_js = os.path.join(PROJ_DIR, 'web', 'data.js')

CAPITALS = {
    'AC': (1392, 'Rio Branco'),
    'AL': (27855, 'Maceió'),
    'AP': (6050, 'Macapá'),
    'AM': (2550, 'Manaus'),
    'BA': (38490, 'Salvador'),
    'CE': (13897, 'Fortaleza'),
    'DF': (97012, 'Brasília'),
    'ES': (57053, 'Vitória'),
    'GO': (93734, 'Goiânia'),
    'MA': (9210, 'São Luís'),
    'MG': (41238, 'Belo Horizonte'),
    'MS': (90514, 'Campo Grande'),
    'MT': (90670, 'Cuiabá'),
    'PA': (4278, 'Belém'),
    'PB': (20516, 'João Pessoa'),
    'PE': (25313, 'Recife'),
    'PI': (12190, 'Teresina'),
    'PR': (75353, 'Curitiba'),
    'RJ': (60011, 'Rio de Janeiro'),
    'RN': (17612, 'Natal'),
    'RO': (35, 'Porto Velho'),
    'RR': (3018, 'Boa Vista'),
    'RS': (88013, 'Porto Alegre'),
    'SC': (81051, 'Florianópolis'),
    'SE': (31054, 'Aracaju'),
    'SP': (71072, 'São Paulo'),
    'TO': (73440, 'Palmas'),
}

SOURCES_DEF = [
    {'key': 'cury', 'label': '70 - Augusto Cury', 'idx': 2},
    {'key': 'renan', 'label': '14 - Renan Santos', 'idx': 3},
    {'key': 'caiado', 'label': '55 - Ronaldo Caiado', 'idx': 4},
    {'key': 'zema', 'label': '30 - Romeu Zema', 'idx': 5},
    {'key': 'outros_3v', 'label': 'Outros Candidatos (3ª Via)', 'idx': 6},
    {'key': 'conv_bn', 'label': 'Conversão de Brancos/Nulos', 'idx': None}, # t1_bn - t2_bn
    {'key': 'delta_comp', 'label': 'Redução da Abstenção (Novos Comparecentes)', 'idx': None}, # t2_comp - t1_comp
]

print("1. Ingesting section-level votes from votacao_secao_2026_BR.zip...", flush=True)
t0 = time.time()

# Map key: (uf, mu, z, s) -> [t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, t2_13, t2_22, t2_bn]
sec_votes = {}

with zipfile.ZipFile(zip_path, 'r') as zf:
    with zf.open('votacao_secao_2026_BR.csv') as cf:
        reader = csv.reader(io.TextIOWrapper(cf, encoding='latin1'), delimiter=';')
        header = next(reader)
        idx_t = header.index('NR_TURNO')
        idx_uf = header.index('SG_UF')
        idx_mu = header.index('CD_MUNICIPIO')
        idx_z = header.index('NR_ZONA')
        idx_s = header.index('NR_SECAO')
        idx_v = header.index('NR_VOTAVEL')
        idx_qt = header.index('QT_VOTOS')

        for row in reader:
            uf = row[idx_uf]
            t = row[idx_t]
            k = (uf, int(row[idx_mu]), int(row[idx_z]), int(row[idx_s]))
            v = sec_votes.get(k)
            if v is None:
                v = [0]*11
                sec_votes[k] = v
            nr = row[idx_v]
            qt = int(row[idx_qt])
            if t == '1':
                if nr == '13': v[0] += qt
                elif nr == '22': v[1] += qt
                elif nr == '70': v[2] += qt
                elif nr == '14': v[3] += qt
                elif nr == '55': v[4] += qt
                elif nr == '30': v[5] += qt
                elif nr in ('95', '96'): v[7] += qt
                else: v[6] += qt
            elif t == '2':
                if nr == '13': v[8] += qt
                elif nr == '22': v[9] += qt
                elif nr in ('95', '96'): v[10] += qt

print(f"Loaded {len(sec_votes):,} sections in {time.time()-t0:.1f}s.", flush=True)

# Build section matrix vectors grouped by slice
# Slices:
# (uf, 'total'), (uf, 'capital'), (uf, 'interior')
# and ('BR', 'total'), ('BR', 'capital'), ('BR', 'interior')
slice_data = {}

def get_slice_accum():
    return {
        'secoes': 0,
        't1_13': 0, 't1_22': 0, 't2_13': 0, 't2_22': 0,
        't1_validos': 0, 't2_validos': 0,
        'vols': [0]*7,
        'X_rows': [],
        'y_rows': []
    }

for (uf, mu, z, s), v in sec_votes.items():
    t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, t2_13, t2_22, t2_bn = v
    d13 = t2_13 - t1_13
    d22 = t2_22 - t1_22
    t1_3v = t1_70 + t1_14 + t1_55 + t1_30 + t1_out
    t1_comp = t1_13 + t1_22 + t1_3v + t1_bn
    t2_comp = t2_13 + t2_22 + t2_bn
    
    # 7 features satisfying d13 + d22 = sum(x)
    x = [
        t1_70,
        t1_14,
        t1_55,
        t1_30,
        t1_out,
        (t1_bn - t2_bn),
        (t2_comp - t1_comp)
    ]
    
    cap_info = CAPITALS.get(uf)
    is_cap = cap_info is not None and mu == cap_info[0]
    
    slice_keys = [
        ('BR', 'total'),
        ('BR', 'capital' if is_cap else 'interior'),
        (uf, 'total'),
        (uf, 'capital' if is_cap else 'interior')
    ]
    
    for sk in slice_keys:
        if sk not in slice_data:
            slice_data[sk] = get_slice_accum()
        acc = slice_data[sk]
        acc['secoes'] += 1
        acc['t1_13'] += t1_13
        acc['t1_22'] += t1_22
        acc['t2_13'] += t2_13
        acc['t2_22'] += t2_22
        acc['t1_validos'] += (t1_13 + t1_22 + t1_3v)
        acc['t2_validos'] += (t2_13 + t2_22)
        for i in range(7):
            acc['vols'][i] += x[i]
        acc['X_rows'].append(x)
        acc['y_rows'].append(d13)

print(f"Aggregated {len(slice_data)} distinct slices. Running OLS + KKT Ecological Estimations...", flush=True)

def solve_kkt_slice(vols, b_ols, target, lo_b=0.0, hi_b=1.0):
    tot_vol = sum(vols)
    if tot_vol <= 0:
        return [0.5]*len(vols)
    min_t = sum(v * lo_b for v in vols)
    max_t = sum(v * hi_b for v in vols)
    if target <= min_t:
        return [lo_b]*len(vols)
    if target >= max_t:
        return [hi_b]*len(vols)
    
    lo_lam, hi_lam = -2.0, 2.0
    while sum(v * max(lo_b, min(hi_b, b + lo_lam)) for v, b in zip(vols, b_ols)) > target:
        lo_lam *= 2.0
    while sum(v * max(lo_b, min(hi_b, b + hi_lam)) for v, b in zip(vols, b_ols)) < target:
        hi_lam *= 2.0
        
    for _ in range(60):
        mid = (lo_lam + hi_lam) / 2.0
        val = sum(v * max(lo_b, min(hi_b, b + mid)) for v, b in zip(vols, b_ols))
        if val < target:
            lo_lam = mid
        else:
            hi_lam = mid
            
    lam = (lo_lam + hi_lam) / 2.0
    return [max(lo_b, min(hi_b, b + lam)) for b in b_ols]

PRIORS = np.array([
    0.72,  # 70 - Augusto Cury (~72% Lula / 28% Flavio)
    0.56,  # 14 - Renan Santos (~56% Lula / 44% Flavio)
    0.48,  # 55 - Ronaldo Caiado (~48% Lula / 52% Flavio)
    0.22,  # 30 - Romeu Zema (~22% Lula / 78% Flavio)
    0.60,  # Outros Candidatos (3ª Via) (~60% Lula / 40% Flavio)
    0.80,  # Conversão de Brancos/Nulos (~80% Lula / 20% Flavio)
    0.58,  # Redução da Abstenção (~58% Lula / 42% Flavio)
], dtype=np.float64)

results = {}

for (geo, loc), acc in sorted(slice_data.items()):
    N = acc['secoes']
    if N == 0:
        continue
    
    X = np.array(acc['X_rows'], dtype=np.float64)
    y = np.array(acc['y_rows'], dtype=np.float64)
    vols = acc['vols']
    d13 = acc['t2_13'] - acc['t1_13']
    d22 = acc['t2_22'] - acc['t1_22']
    pool_total = d13 + d22
    
    # Empirical Bayes Shrinkage estimation
    XtX = X.T @ X
    Xty = X.T @ y
    tau = 0.06
    gamma = tau * np.diag(np.diag(XtX) + 1e-1)
    try:
        b_est = np.linalg.solve(XtX + gamma, Xty + gamma @ PRIORS)
    except Exception:
        b_est = np.linalg.pinv(XtX + gamma) @ (Xty + gamma @ PRIORS)
        
    residuals = y - X @ b_est
    ss_res = float(np.sum(residuals**2))
    ss_tot = float(np.sum((y - np.mean(y))**2))
    r2 = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot))) if ss_tot > 0 else 1.0
    s2 = ss_res / max(1, N - 7)
    
    try:
        cov_b = s2 * np.linalg.inv(XtX + gamma)
        se_b = np.sqrt(np.maximum(0.0, np.diag(cov_b)))
    except Exception:
        se_b = np.full(7, 0.04)
        
    # Adaptive interior plausibility bounds (no 0% or 100% boundary solutions)
    overall_ratio = d13 / max(1.0, float(pool_total)) if pool_total > 0 else 0.5
    lo_b = min(0.05, max(0.005, overall_ratio * 0.10))
    hi_b = max(0.95, min(0.995, 1.0 - (1.0 - overall_ratio) * 0.10))
    
    # KKT constrained projection onto [lo_b, hi_b]
    b_kkt = solve_kkt_slice(vols, b_est.tolist(), target=d13, lo_b=lo_b, hi_b=hi_b)
    
    sources_breakdown = []
    tot_calc_13 = 0
    tot_calc_22 = 0
    
    for i, sdef in enumerate(SOURCES_DEF):
        v = vols[i]
        b13 = b_kkt[i]
        b22 = 1.0 - b13
        v13 = round(v * b13)
        v22 = v - v13
        tot_calc_13 += v13
        tot_calc_22 += v22
        
        # 95% confidence intervals from Bayesian posterior clamped to [lo_b, hi_b]
        ci_lo = max(lo_b, min(hi_b, float(b13 - 1.96 * se_b[i])))
        ci_hi = max(lo_b, min(hi_b, float(b13 + 1.96 * se_b[i])))
        
        sources_breakdown.append({
            'key': sdef['key'],
            'label': sdef['label'],
            'volume': int(v),
            'pct_pool': round((v / pool_total * 100) if pool_total > 0 else 0.0, 2),
            'beta_13': round(float(b13) * 100, 2),
            'beta_22': round(float(b22) * 100, 2),
            'votos_13': int(v13),
            'votos_22': int(v22),
            'ci_95_lo': round(ci_lo * 100, 2),
            'ci_95_hi': round(ci_hi * 100, 2)
        })
        
    slice_key = f"{geo}_{loc}"
    results[slice_key] = {
        'geo': geo,
        'loc': loc,
        'capital_name': CAPITALS[geo][1] if geo in CAPITALS and loc == 'capital' else None,
        'secoes': int(N),
        't1_13': int(acc['t1_13']),
        't1_22': int(acc['t1_22']),
        't2_13': int(acc['t2_13']),
        't2_22': int(acc['t2_22']),
        'delta_13': int(d13),
        'delta_22': int(d22),
        'pool_total': int(pool_total),
        'd13_share': round((d13 / pool_total * 100) if pool_total > 0 else 0.0, 2),
        'd22_share': round((d22 / pool_total * 100) if pool_total > 0 else 0.0, 2),
        'r2': round(float(r2), 4),
        'res_std': round(float(np.sqrt(s2)), 2),
        'accounting_diff': int(tot_calc_13 - d13),
        'sources': sources_breakdown
    }

print(f"Generated {len(results)} ecological inference slices successfully!")

# Write slices json
out_json_path = os.path.join(PROJ_DIR, 'data', 'eco_inference_slices.json')
with open(out_json_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# Merge into dashboard_data.json
with open(dash_path, 'r', encoding='utf-8') as f:
    dash = json.load(f)

dash['eco_inference_slices'] = results

if 'comparativo_geral_t1_t2' in dash and 'BR_total' in results:
    dash['comparativo_geral_t1_t2']['decomposicao_ecologica'] = [
        {
            'fonte': s['label'],
            'volume': s['volume'],
            'pct_para_lula': s['beta_13'],
            'pct_para_flavio': s['beta_22'],
            'votos_para_lula': s['votos_13'],
            'votos_para_flavio': s['votos_22']
        }
        for s in results['BR_total']['sources']
    ]

with open(dash_path, 'w', encoding='utf-8') as f:
    json.dump(dash, f, ensure_ascii=False, indent=2)

# Update web/data.js
with open(web_data_js, 'w', encoding='utf-8') as f:
    f.write("window.ELECTION_DATA = ")
    json.dump(dash, f, ensure_ascii=False)
    f.write(";\n")

print(f"Saved to {out_json_path}, {dash_path}, and {web_data_js}.")
