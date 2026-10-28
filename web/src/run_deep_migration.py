import sys, zipfile, csv, io, json, os, time
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

SCRATCH_BRAIN = r'C:\Users\renan\.gemini\antigravity\brain\01ee89c1-0cb6-4be4-8ef3-288e34eca1bf\scratch'
PROJ_DIR = r'C:\Projetos\MapaDaUrna'
zip_path = os.path.join(SCRATCH_BRAIN, 'votacao_secao_2026_BR.zip')
secoes_csv_path = os.path.join(SCRATCH_BRAIN, 'secoes.csv')

t0 = time.time()
print("1. Loading municipal electorate (te) from all_muns_ab.json...", flush=True)
mun_te = {}
ab_path = os.path.join(SCRATCH_BRAIN, 'all_muns_ab.json')
if os.path.exists(ab_path):
    with open(ab_path, 'r', encoding='utf-8') as f:
        for m in json.load(f):
            mun_te[(m['uf'].upper(), int(m['mu']))] = int(m['te'])
print(f"Loaded electorate for {len(mun_te):,} municipalities (Total Aptos: {sum(mun_te.values()):,}).")
sec_aptos = {}

print("2. Loading votacao_secao_2026_BR.csv...", flush=True)
sec_votes = {}
with zipfile.ZipFile(zip_path, 'r') as zf:
    with zf.open('votacao_secao_2026_BR.csv') as cf:
        reader = csv.reader(io.TextIOWrapper(cf, encoding='latin1'), delimiter=';')
        header = next(reader)
        idx_t = header.index('NR_TURNO')
        idx_uf = header.index('SG_UF')
        idx_mu = header.index('CD_MUNICIPIO')
        idx_nm_mu = header.index('NM_MUNICIPIO')
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
                v = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, row[idx_nm_mu]]
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

print(f"Loaded {len(sec_votes):,} sections in {time.time()-t0:.1f}s.")

FLAVIO_BANDS = [
    ('< 20% (Reduto Lula)', 0.0, 20.0),
    ('20% a 35% (Forte Lula)', 20.0, 35.0),
    ('35% a 45% (Vantagem Lula)', 35.0, 45.0),
    ('45% a 50% (Disputada - Vant. Lula/3ªVia)', 45.0, 50.0),
    ('50% a 55% (Disputada - Vant. Flávio)', 50.0, 55.0),
    ('55% a 65% (Forte Flávio)', 55.0, 65.0),
    ('65% a 75% (Muito Forte Flávio)', 65.0, 75.0),
    ('>= 75% (Reduto Extremo Flávio)', 75.0, 100.01)
]

THIRD_BANDS = [
    ('< 4% (Baixa 3ª Via)', 0.0, 4.0),
    ('4% a 7% (Média-Baixa 3ª Via)', 4.0, 7.0),
    ('7% a 10% (Média 3ª Via)', 7.0, 10.0),
    ('10% a 13% (Média-Alta 3ª Via)', 10.0, 13.0),
    ('13% a 17% (Alta 3ª Via)', 13.0, 17.0),
    ('>= 17% (Reduto 3ª Via)', 17.0, 100.01)
]

def make_bucket():
    return {
        'secoes': 0, 'aptos': 0, 'aptos_secoes': 0,
        't1_13': 0, 't1_22': 0, 't1_70': 0, 't1_14': 0, 't1_55': 0, 't1_30': 0, 't1_out': 0, 't1_3v': 0, 't1_bn': 0, 't1_comp': 0,
        't2_13': 0, 't2_22': 0, 't2_bn': 0, 't2_comp': 0,
        'abst_up_secoes': 0, 'abst_down_secoes': 0, 'abst_same_secoes': 0,
        'd13_neg_secoes': 0, 'd22_neg_secoes': 0,
        'aptos_t1_comp': 0, 'aptos_t2_comp': 0
    }

flavio_stats = {b[0]: make_bucket() for b in FLAVIO_BANDS}
third_stats = {b[0]: make_bucket() for b in THIRD_BANDS}
leader_3v_stats = {
    '70 - Augusto Cury (>= 5% na seção)': make_bucket(),
    '14 - Renan Santos (>= 5% na seção)': make_bucket(),
    '55 - Ronaldo Caiado (>= 5% na seção)': make_bucket(),
    '30 - Romeu Zema (>= 3% na seção)': make_bucket(),
    '70 - Augusto Cury (>= 10% na seção)': make_bucket(),
    '14 - Renan Santos (>= 10% na seção)': make_bucket(),
    '55 - Ronaldo Caiado (>= 10% na seção)': make_bucket(),
    '30 - Romeu Zema (>= 5% na seção)': make_bucket(),
}

def add_to_bucket(bk, v, aptos):
    t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, t2_13, t2_22, t2_bn, _ = v
    t1_3v = t1_70 + t1_14 + t1_55 + t1_30 + t1_out
    t1_comp = t1_13 + t1_22 + t1_3v + t1_bn
    t2_comp = t2_13 + t2_22 + t2_bn
    bk['secoes'] += 1
    bk['t1_13'] += t1_13
    bk['t1_22'] += t1_22
    bk['t1_70'] += t1_70
    bk['t1_14'] += t1_14
    bk['t1_55'] += t1_55
    bk['t1_30'] += t1_30
    bk['t1_out'] += t1_out
    bk['t1_3v'] += t1_3v
    bk['t1_bn'] += t1_bn
    bk['t1_comp'] += t1_comp
    bk['t2_13'] += t2_13
    bk['t2_22'] += t2_22
    bk['t2_bn'] += t2_bn
    bk['t2_comp'] += t2_comp
    if t2_comp < t1_comp:
        bk['abst_up_secoes'] += 1
    elif t2_comp > t1_comp:
        bk['abst_down_secoes'] += 1
    else:
        bk['abst_same_secoes'] += 1
    if t2_13 < t1_13:
        bk['d13_neg_secoes'] += 1
    if t2_22 < t1_22:
        bk['d22_neg_secoes'] += 1
    if aptos > 0 and aptos >= max(t1_comp, t2_comp):
        bk['aptos'] += aptos
        bk['aptos_secoes'] += 1
        bk['aptos_t1_comp'] += t1_comp
        bk['aptos_t2_comp'] += t2_comp

# Ecological regression:
# We want to explain how each new source of votes in T2 split between Lula (d13) and Flavio (d22):
# Notice the exact accounting identity in every section:
# d13 + d22 = t1_70 + t1_14 + t1_55 + t1_30 + t1_out + (t1_bn - t2_bn) + (t2_comp - t1_comp)
# Let X = [t1_70, t1_14, t1_55, t1_30, t1_out, (t1_bn - t2_bn), (t2_comp - t1_comp), t1_13, t1_22]
# Wait: if we regress d13 on X1=[t1_70, t1_14, t1_55, t1_30, t1_out, (t1_bn - t2_bn), (t2_comp - t1_comp)]
# AND also do a full transition regression:
# Y = [t2_13, t2_22, t2_bn, abst_t2] on X_full = [t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, abst_t1]
# Let's compute BOTH normal equations (X^T X and X^T Y)!

P_ident = 7 # [t1_70, t1_14, t1_55, t1_30, t1_out, drop_bn, gain_comp]
XtX_id = [[0.0]*P_ident for _ in range(P_ident)]
XtY_id_13 = [0.0]*P_ident
XtY_id_22 = [0.0]*P_ident

P_full = 8 # [t1_13, t1_22, t1_70, t1_14, t1_55, t1_30_out, t1_bn, abst_t1]
XtX_full = [[0.0]*P_full for _ in range(P_full)]
XtY_full_13 = [0.0]*P_full
XtY_full_22 = [0.0]*P_full
XtY_full_bn = [0.0]*P_full
XtY_full_ab = [0.0]*P_full

total_both = make_bucket()
abst_up_bucket = make_bucket()
abst_down_bucket = make_bucket()
d22_neg_bucket = make_bucket()
d13_neg_bucket = make_bucket()

for k, v in sec_votes.items():
    uf, cd_mun, zona, secao = k
    t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, t2_13, t2_22, t2_bn, nm_mun = v
    t1_val = t1_13 + t1_22 + t1_70 + t1_14 + t1_55 + t1_30 + t1_out
    t2_val = t2_13 + t2_22
    t1_comp = t1_val + t1_bn
    t2_comp = t2_val + t2_bn
    if t1_val == 0 or t2_val == 0:
        continue
        
    aptos = sec_aptos.get(k, 0)
    add_to_bucket(total_both, v, aptos)
    
    if t2_comp < t1_comp:
        add_to_bucket(abst_up_bucket, v, aptos)
    elif t2_comp > t1_comp:
        add_to_bucket(abst_down_bucket, v, aptos)
        
    if t2_22 < t1_22:
        add_to_bucket(d22_neg_bucket, v, aptos)
    if t2_13 < t1_13:
        add_to_bucket(d13_neg_bucket, v, aptos)
    
    pct_22_t1 = (t1_22 / t1_val) * 100.0
    pct_3v_t1 = ((t1_70 + t1_14 + t1_55 + t1_30 + t1_out) / t1_val) * 100.0
    
    for label, lo, hi in FLAVIO_BANDS:
        if lo <= pct_22_t1 < hi:
            add_to_bucket(flavio_stats[label], v, aptos)
            break
            
    for label, lo, hi in THIRD_BANDS:
        if lo <= pct_3v_t1 < hi:
            add_to_bucket(third_stats[label], v, aptos)
            break
            
    cands_3v = [(t1_70, '70'), (t1_14, '14'), (t1_55, '55'), (t1_30, '30')]
    cands_3v.sort(reverse=True)
    top_votes, top_code = cands_3v[0]
    top_pct = (top_votes / t1_val) * 100.0
    if top_code == '70' and top_pct >= 5.0:
        add_to_bucket(leader_3v_stats['70 - Augusto Cury (>= 5% na seção)'], v, aptos)
    elif top_code == '14' and top_pct >= 5.0:
        add_to_bucket(leader_3v_stats['14 - Renan Santos (>= 5% na seção)'], v, aptos)
    elif top_code == '55' and top_pct >= 5.0:
        add_to_bucket(leader_3v_stats['55 - Ronaldo Caiado (>= 5% na seção)'], v, aptos)
    elif top_code == '30' and top_pct >= 3.0:
        add_to_bucket(leader_3v_stats['30 - Romeu Zema (>= 3% na seção)'], v, aptos)
        
    if (t1_70 / t1_val)*100 >= 10.0:
        add_to_bucket(leader_3v_stats['70 - Augusto Cury (>= 10% na seção)'], v, aptos)
    if (t1_14 / t1_val)*100 >= 10.0:
        add_to_bucket(leader_3v_stats['14 - Renan Santos (>= 10% na seção)'], v, aptos)
    if (t1_55 / t1_val)*100 >= 10.0:
        add_to_bucket(leader_3v_stats['55 - Ronaldo Caiado (>= 10% na seção)'], v, aptos)
    if (t1_30 / t1_val)*100 >= 5.0:
        add_to_bucket(leader_3v_stats['30 - Romeu Zema (>= 5% na seção)'], v, aptos)
        
    # Identity regression row
    d13 = float(t2_13 - t1_13)
    d22 = float(t2_22 - t1_22)
    drop_bn = float(t1_bn - t2_bn)
    gain_comp = float(t2_comp - t1_comp)
    x_id = [float(t1_70), float(t1_14), float(t1_55), float(t1_30), float(t1_out), drop_bn, gain_comp]
    for i in range(P_ident):
        xi = x_id[i]
        XtY_id_13[i] += xi * d13
        XtY_id_22[i] += xi * d22
        for j in range(i, P_ident):
            XtX_id[i][j] += xi * x_id[j]
            
    x_f = [float(t1_13), float(t1_22), float(t1_70), float(t1_14), float(t1_55), float(t1_30 + t1_out), float(t1_bn), float(t2_comp - t1_comp)]
    for i in range(P_full):
        xi = x_f[i]
        XtY_full_13[i] += xi * t2_13
        XtY_full_22[i] += xi * t2_22
        XtY_full_bn[i] += xi * t2_bn
        for j in range(i, P_full):
            XtX_full[i][j] += xi * x_f[j]

for i in range(P_ident):
    for j in range(i):
        XtX_id[i][j] = XtX_id[j][i]
for i in range(P_full):
    for j in range(i):
        XtX_full[i][j] = XtX_full[j][i]

def solve_linear(A, b):
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for i in range(n):
        piv = i
        for r in range(i+1, n):
            if abs(M[r][i]) > abs(M[piv][i]):
                piv = r
        M[i], M[piv] = M[piv], M[i]
        div = M[i][i]
        for c in range(i, n+1):
            M[i][c] /= div
        for r in range(n):
            if r != i:
                f = M[r][i]
                for c in range(i, n+1):
                    M[r][c] -= f * M[i][c]
    return [M[i][n] for i in range(n)]

b_id_13 = solve_linear(XtX_id, XtY_id_13)
b_id_22 = solve_linear(XtX_id, XtY_id_22)

b_f_13 = solve_linear(XtX_full, XtY_full_13)
b_f_22 = solve_linear(XtX_full, XtY_full_22)
b_f_bn = solve_linear(XtX_full, XtY_full_bn)

print("\n=== DECOMPOSIÇÃO EXATA DO CRESCIMENTO (d13 + d22 = 3aVia + Queda_BN + Ganho_Comp) ===")
id_names = ['70 - Augusto Cury', '14 - Renan Santos', '55 - Ronaldo Caiado', '30 - Romeu Zema', 'Outros 3ª Via', 'Queda Brancos/Nulos (1ºT->2ºT)', 'Redução da Abstenção (Novos Eleitores)']
id_totals = [total_both['t1_70'], total_both['t1_14'], total_both['t1_55'], total_both['t1_30'], total_both['t1_out'], total_both['t1_bn'] - total_both['t2_bn'], total_both['t2_comp'] - total_both['t1_comp']]
for name, tot, c13, c22 in zip(id_names, id_totals, b_id_13, b_id_22):
    print(f"  {name:38s} | Volume: {tot:10,d} | -> Lula: {c13*100:5.1f}% ({int(round(tot*c13)):+10,d}) | -> Flávio: {c22*100:5.1f}% ({int(round(tot*c22)):+10,d})")

print("\n=== MATRIZ DE TRANSIÇÃO ECOLÓGICA COMPLETA (499.205 SEÇÕES) ===")
f_names = ['Lula (13) no 1ºT', 'Flávio (22) no 1ºT', 'Augusto Cury (70) no 1ºT', 'Renan Santos (14) no 1ºT', 'Ronaldo Caiado (55) no 1ºT', 'Zema (30) + Outros no 1ºT', 'Brancos/Nulos no 1ºT', 'Variação Comparecimento (ΔComp)']
for name, c13, c22, cbn in zip(f_names, b_f_13, b_f_22, b_f_bn):
    print(f"  {name:32s} | -> Lula 2ºT: {c13*100:5.1f}% | -> Flávio 2ºT: {c22*100:5.1f}% | -> BN 2ºT: {cbn*100:5.1f}%")

def summarize_bk(label, b):
    t1_val = b['t1_13'] + b['t1_22'] + b['t1_3v']
    t2_val = b['t2_13'] + b['t2_22']
    d_comp = b['t2_comp'] - b['t1_comp']
    d13 = b['t2_13'] - b['t1_13']
    d22 = b['t2_22'] - b['t1_22']
    d_bn = b['t2_bn'] - b['t1_bn']
    abst_t1_pct = ((b['aptos'] - b['aptos_t1_comp']) / b['aptos'] * 100.0) if b['aptos'] else 0.0
    abst_t2_pct = ((b['aptos'] - b['aptos_t2_comp']) / b['aptos'] * 100.0) if b['aptos'] else 0.0
    tot_gain = d13 + d22
    return {
        'label': label,
        'secoes': b['secoes'],
        'aptos': b['aptos'],
        't1_13': b['t1_13'],
        't1_22': b['t1_22'],
        't1_70': b['t1_70'],
        't1_14': b['t1_14'],
        't1_55': b['t1_55'],
        't1_30': b['t1_30'],
        't1_3v': b['t1_3v'],
        't1_bn': b['t1_bn'],
        't1_comp': b['t1_comp'],
        't1_lula_pct': round(b['t1_13'] / t1_val * 100, 2) if t1_val else 0,
        't1_flavio_pct': round(b['t1_22'] / t1_val * 100, 2) if t1_val else 0,
        't1_3v_pct': round(b['t1_3v'] / t1_val * 100, 2) if t1_val else 0,
        't2_13': b['t2_13'],
        't2_22': b['t2_22'],
        't2_bn': b['t2_bn'],
        't2_comp': b['t2_comp'],
        't2_lula_pct': round(b['t2_13'] / t2_val * 100, 2) if t2_val else 0,
        't2_flavio_pct': round(b['t2_22'] / t2_val * 100, 2) if t2_val else 0,
        'delta_13': d13,
        'delta_13_pct': round(d13 / b['t1_13'] * 100, 2) if b['t1_13'] else 0,
        'delta_22': d22,
        'delta_22_pct': round(d22 / b['t1_22'] * 100, 2) if b['t1_22'] else 0,
        'delta_bn': d_bn,
        'delta_comp': d_comp,
        'delta_comp_pct': round(d_comp / b['t1_comp'] * 100, 2) if b['t1_comp'] else 0,
        'abst_t1_pct': round(abst_t1_pct, 2),
        'abst_t2_pct': round(abst_t2_pct, 2),
        'delta_abst_pp': round(abst_t2_pct - abst_t1_pct, 2),
        'abst_up_secoes': b['abst_up_secoes'],
        'abst_up_secoes_pct': round(b['abst_up_secoes'] / b['secoes'] * 100, 2) if b['secoes'] else 0,
        'd13_neg_secoes': b['d13_neg_secoes'],
        'd13_neg_secoes_pct': round(b['d13_neg_secoes'] / b['secoes'] * 100, 2) if b['secoes'] else 0,
        'd22_neg_secoes': b['d22_neg_secoes'],
        'd22_neg_secoes_pct': round(b['d22_neg_secoes'] / b['secoes'] * 100, 2) if b['secoes'] else 0,
        'share_crescimento_lula': round(d13 / tot_gain * 100, 1) if tot_gain > 0 else 0
    }

print("\n=== RESUMO SEÇÕES COM AUMENTO DE ABSTENÇÃO vs QUEDA DE ABSTENÇÃO ===")
for nm, bk in [('Total Geral (499.205 seções)', total_both),
               ('Seções onde Abstenção SUBIU no 2ºT (Comparecimento caiu)', abst_up_bucket),
               ('Seções onde Abstenção CAIU no 2ºT (Comparecimento subiu)', abst_down_bucket),
               ('Seções onde Flávio PERDEU votos no 2ºT (d22 < 0)', d22_neg_bucket),
               ('Seções onde Lula PERDEU votos no 2ºT (d13 < 0)', d13_neg_bucket)]:
    s = summarize_bk(nm, bk)
    print(f"\n[{nm}]: {s['secoes']:,} seções ({s['secoes']/total_both['secoes']*100:.1f}%)")
    print(f"  1ºT: Lula {s['t1_lula_pct']}% | Flávio {s['t1_flavio_pct']}% | 3ªVia {s['t1_3v_pct']}% | Abstenção 1ºT: {s['abst_t1_pct']}% -> 2ºT: {s['abst_t2_pct']}% ({s['delta_abst_pp']:+.2f} p.p.)")
    print(f"  Δ Comp: {s['delta_comp']:+,} ({s['delta_comp_pct']:+.2f}%) | Δ Lula: {s['delta_13']:+,} ({s['delta_13_pct']:+.2f}%) | Δ Flávio: {s['delta_22']:+,} ({s['delta_22_pct']:+.2f}%) | Δ BN: {s['delta_bn']:+,}")
    print(f"  Seções c/ queda de votos Flávio (d22<0): {s['d22_neg_secoes']:,} ({s['d22_neg_secoes_pct']}%) | Queda votos Lula (d13<0): {s['d13_neg_secoes']:,} ({s['d13_neg_secoes_pct']}%)")

print("\n=== TABELA DE ABSTENÇÃO REAL (% APTOS) POR FAIXA DE PREDOMINÂNCIA DE FLÁVIO NO 1ºT ===")
for b_label, _, _ in FLAVIO_BANDS:
    s = summarize_bk(b_label, flavio_stats[b_label])
    print(f"  {b_label:40s} | Seções: {s['secoes']:7,d} | Abst 1ºT: {s['abst_t1_pct']:5.2f}% -> 2ºT: {s['abst_t2_pct']:5.2f}% ({s['delta_abst_pp']:+5.2f}pp) | Seções Abst Subiu: {s['abst_up_secoes_pct']:4.1f}% | Seções d22<0: {s['d22_neg_secoes_pct']:4.1f}% | d13: {s['delta_13_pct']:+6.2f}% | d22: {s['delta_22_pct']:+5.2f}%")

# Save to dashboard_data.json and web/data.js
dash_path = os.path.join(PROJ_DIR, 'data', 'dashboard_data.json')
with open(dash_path, 'r', encoding='utf-8') as f:
    dash = json.load(f)

dash['comparativo_geral_t1_t2']['faixas_predominancia_flavio'] = [summarize_bk(b[0], flavio_stats[b[0]]) for b in FLAVIO_BANDS]
dash['comparativo_geral_t1_t2']['faixas_terceira_via'] = [summarize_bk(b[0], third_stats[b[0]]) for b in THIRD_BANDS]
dash['comparativo_geral_t1_t2']['lideres_terceira_via'] = [summarize_bk(k, v) for k, v in leader_3v_stats.items()]
dash['comparativo_geral_t1_t2']['cortes_abstencao_e_queda'] = {
    'total': summarize_bk('Total Geral', total_both),
    'abst_subiu': summarize_bk('Seções onde Abstenção SUBIU no 2ºT', abst_up_bucket),
    'abst_caiu': summarize_bk('Seções onde Abstenção CAIU no 2ºT', abst_down_bucket),
    'flavio_caiu': summarize_bk('Seções onde Flávio PERDEU votos (Δ22 < 0)', d22_neg_bucket),
    'lula_caiu': summarize_bk('Seções onde Lula PERDEU votos (Δ13 < 0)', d13_neg_bucket),
}
dash['comparativo_geral_t1_t2']['decomposicao_ecologica'] = [
    {
        'fonte': name,
        'volume': tot,
        'pct_para_lula': round(c13 * 100, 1),
        'votos_para_lula': int(round(tot * c13)),
        'pct_para_flavio': round(c22 * 100, 1),
        'votos_para_flavio': int(round(tot * c22))
    }
    for name, tot, c13, c22 in zip(id_names, id_totals, b_id_13, b_id_22)
]

with open(dash_path, 'w', encoding='utf-8') as f:
    json.dump(dash, f, ensure_ascii=False, indent=2)

web_js_path = os.path.join(PROJ_DIR, 'web', 'data.js')
with open(web_js_path, 'w', encoding='utf-8') as f:
    f.write('window.ELECTION_DATA = ')
    json.dump(dash, f, ensure_ascii=False)
    f.write(';\n')

print("\nUpdated dashboard_data.json and web/data.js successfully!")
