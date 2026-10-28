import zipfile, csv, io, json, os, time
from collections import defaultdict, Counter

SCRATCH_BRAIN = r'C:\Users\renan\.gemini\antigravity\brain\01ee89c1-0cb6-4be4-8ef3-288e34eca1bf\scratch'
PROJ_DIR = r'C:\Projetos\MapaDaUrna'
zip_path = os.path.join(SCRATCH_BRAIN, 'votacao_secao_2026_BR.zip')

t0 = time.time()
print("Reading votacao_secao_2026_BR.csv for general T1 vs T2 stats (including ZZ)...", flush=True)

# sec_votes[k] = [t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_outros, t1_bn, t2_13, t2_22, t2_bn, nm_mun]
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

print(f"Loaded {len(sec_votes):,} total sections (BR + ZZ) in {time.time()-t0:.1f}s!", flush=True)

REGIONS = {
    'Norte': {'AC','AM','AP','PA','RO','RR','TO'},
    'Nordeste': {'AL','BA','CE','MA','PB','PE','PI','RN','SE'},
    'Sudeste': {'ES','MG','RJ','SP'},
    'Sul': {'PR','RS','SC'},
    'Centro-Oeste': {'DF','GO','MS','MT'},
    'Exterior': {'ZZ'}
}
def get_reg(uf):
    for r, ufs in REGIONS.items():
        if uf in ufs: return r
    return 'Outro'

uf_t1_t2 = defaultdict(lambda: {
    'uf': '', 'regiao': '', 'secoes': 0,
    't1_13': 0, 't1_22': 0, 't1_70': 0, 't1_14': 0, 't1_55': 0, 't1_outros': 0, 't1_3v': 0, 't1_bn': 0,
    't2_13': 0, 't2_22': 0, 't2_bn': 0,
    'flips_22_to_13': 0, 'flips_13_to_22': 0, 'keep_13': 0, 'keep_22': 0
})

reg_t1_t2 = defaultdict(lambda: {
    'regiao': '', 'secoes': 0,
    't1_13': 0, 't1_22': 0, 't1_3v': 0, 't1_bn': 0,
    't2_13': 0, 't2_22': 0, 't2_bn': 0,
    'flips_22_to_13': 0, 'flips_13_to_22': 0
})

mun_t1_t2 = defaultdict(lambda: {
    'uf': '', 'cd_mun': 0, 'municipio': '', 'secoes': 0,
    't1_13': 0, 't1_22': 0, 't1_3v': 0,
    't2_13': 0, 't2_22': 0,
    'flips_22_to_13': 0, 'flips_13_to_22': 0
})

flips_total = Counter()
lula_more_t2 = 0
flavio_more_t2 = 0
lula_grew_more = 0
flavio_grew_more = 0

top_swing_secs = []

for (uf, cd_mun, zona, secao), v in sec_votes.items():
    t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, t2_13, t2_22, t2_bn, nm_mun = v
    t1_3v = t1_70 + t1_14 + t1_55 + t1_30 + t1_out
    
    # Only count valid T2 sections or all sections
    if (t1_13 + t1_22 + t1_3v + t2_13 + t2_22) == 0:
        continue
        
    w1 = '13' if t1_13 > t1_22 else ('22' if t1_22 > t1_13 else 'Tie')
    w2 = '13' if t2_13 > t2_22 else ('22' if t2_22 > t2_13 else 'Tie')
    flips_total[f"{w1}->{w2}"] += 1
    
    d13 = t2_13 - t1_13
    d22 = t2_22 - t1_22
    if d13 > 0: lula_more_t2 += 1
    if d22 > 0: flavio_more_t2 += 1
    if d13 > d22: lula_grew_more += 1
    elif d22 > d13: flavio_grew_more += 1
    
    reg = get_reg(uf)
    u = uf_t1_t2[uf]
    u['uf'] = uf
    u['regiao'] = reg
    u['secoes'] += 1
    u['t1_13'] += t1_13
    u['t1_22'] += t1_22
    u['t1_70'] += t1_70
    u['t1_14'] += t1_14
    u['t1_55'] += t1_55
    u['t1_outros'] += (t1_30 + t1_out)
    u['t1_3v'] += t1_3v
    u['t1_bn'] += t1_bn
    u['t2_13'] += t2_13
    u['t2_22'] += t2_22
    u['t2_bn'] += t2_bn
    if w1 == '22' and w2 == '13': u['flips_22_to_13'] += 1
    elif w1 == '13' and w2 == '22': u['flips_13_to_22'] += 1
    elif w1 == '13' and w2 == '13': u['keep_13'] += 1
    elif w1 == '22' and w2 == '22': u['keep_22'] += 1
    
    r = reg_t1_t2[reg]
    r['regiao'] = reg
    r['secoes'] += 1
    r['t1_13'] += t1_13
    r['t1_22'] += t1_22
    r['t1_3v'] += t1_3v
    r['t1_bn'] += t1_bn
    r['t2_13'] += t2_13
    r['t2_22'] += t2_22
    r['t2_bn'] += t2_bn
    if w1 == '22' and w2 == '13': r['flips_22_to_13'] += 1
    elif w1 == '13' and w2 == '22': r['flips_13_to_22'] += 1
    
    m = mun_t1_t2[(uf, cd_mun)]
    m['uf'] = uf
    m['cd_mun'] = cd_mun
    m['municipio'] = nm_mun
    m['secoes'] += 1
    m['t1_13'] += t1_13
    m['t1_22'] += t1_22
    m['t1_3v'] += t1_3v
    m['t2_13'] += t2_13
    m['t2_22'] += t2_22
    if w1 == '22' and w2 == '13': m['flips_22_to_13'] += 1
    elif w1 == '13' and w2 == '22': m['flips_13_to_22'] += 1

    # Track sections with largest absolute swing (or third-party pool)
    swing = abs(d13 - d22)
    if swing >= 85 and (t2_13 + t2_22) >= 200:
        top_swing_secs.append({
            'uf': uf, 'municipio': nm_mun, 'zona': f"{zona:04d}", 'secao': f"{secao:04d}",
            't1_13': t1_13, 't1_22': t1_22, 't1_3v': t1_3v,
            't2_13': t2_13, 't2_22': t2_22,
            'delta_13': d13, 'delta_22': d22,
            'virada': f"{w1} → {w2}",
            'swing': d13 - d22
        })

top_swing_secs.sort(key=lambda x: -abs(x['swing']))

def enrich_row(d):
    t1_val = d['t1_13'] + d['t1_22'] + d['t1_3v']
    t2_val = d['t2_13'] + d['t2_22']
    d13 = d['t2_13'] - d['t1_13']
    d22 = d['t2_22'] - d['t1_22']
    return {
        **d,
        't1_lula_pct': round(d['t1_13'] / t1_val * 100, 2) if t1_val else 0,
        't1_flavio_pct': round(d['t1_22'] / t1_val * 100, 2) if t1_val else 0,
        't1_3v_pct': round(d['t1_3v'] / t1_val * 100, 2) if t1_val else 0,
        't2_lula_pct': round(d['t2_13'] / t2_val * 100, 2) if t2_val else 0,
        't2_flavio_pct': round(d['t2_22'] / t2_val * 100, 2) if t2_val else 0,
        'delta_13': d13,
        'delta_22': d22,
        'delta_13_pct': round(d13 / d['t1_13'] * 100, 2) if d['t1_13'] else 0,
        'delta_22_pct': round(d22 / d['t1_22'] * 100, 2) if d['t1_22'] else 0,
        'share_cresc_lula': round(d13 / (d13 + d22) * 100, 2) if (d13 + d22) > 0 else 0
    }

uf_list = [enrich_row(u) for u in sorted(uf_t1_t2.values(), key=lambda x: -(x['t2_13'] + x['t2_22']))]
reg_list = [enrich_row(r) for r in sorted(reg_t1_t2.values(), key=lambda x: -(x['t2_13'] + x['t2_22']))]
mun_list = [enrich_row(m) for m in sorted(mun_t1_t2.values(), key=lambda x: -(x['t2_13'] + x['t2_22']))[:300]]

with open(os.path.join(PROJ_DIR, 'data', 'dashboard_data.json'), 'r', encoding='utf-8') as f:
    dash = json.load(f)

dash['comparativo_geral_t1_t2'] = {
    'resumo_nacional': {
        'total_secoes': sum(u['secoes'] for u in uf_t1_t2.values()),
        't1_13': 53879538, 't1_13_pct': 45.07,
        't1_22': 56104503, 't1_22_pct': 46.93,
        't1_70_cury': 3448569, 't1_14_renan': 2675887, 't1_55_caiado': 2605148, 't1_30_zema': 326488, 't1_outros': 236098,
        't1_3v_total': 9292190, 't1_3v_pct': 8.00,
        't1_brancos_nulos': 5969801,
        't2_13': 64256232, 't2_13_pct': 51.79,
        't2_22': 59826041, 't2_22_pct': 48.21,
        't2_brancos_nulos': 4153801,
        'delta_13': 10376694, 'delta_13_pct': 19.26,
        'delta_22': 3721538, 'delta_22_pct': 6.63,
        'delta_bn': -1816000,
        'flips': dict(flips_total),
        'lula_more_t2': lula_more_t2,
        'flavio_more_t2': flavio_more_t2,
        'lula_grew_more': lula_grew_more,
        'flavio_grew_more': flavio_grew_more
    },
    'por_regiao': reg_list,
    'por_uf': uf_list,
    'top_300_municipios': mun_list,
    'top_swing_secoes': top_swing_secs[:200]
}

with open(os.path.join(PROJ_DIR, 'data', 'dashboard_data.json'), 'w', encoding='utf-8') as f:
    json.dump(dash, f, ensure_ascii=False, indent=2)

with open(os.path.join(PROJ_DIR, 'web', 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.ELECTION_DATA = ' + json.dumps(dash, ensure_ascii=False, indent=2) + ';\n')

print("Successfully updated dashboard_data.json and web/data.js with general T1 vs T2 comparison!")
