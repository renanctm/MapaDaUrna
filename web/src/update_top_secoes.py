import sys, zipfile, csv, io, json, os, time, heapq

sys.stdout.reconfigure(encoding='utf-8')

SCRATCH_BRAIN = r'C:\Users\renan\.gemini\antigravity\brain\01ee89c1-0cb6-4be4-8ef3-288e34eca1bf\scratch'
PROJ_DIR = r'C:\Projetos\MapaDaUrna'
zip_path = os.path.join(SCRATCH_BRAIN, 'votacao_secao_2026_BR.zip')

t0 = time.time()
print("Reading votacao_secao_2026_BR.csv to extract top swing sections...", flush=True)

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
                v = [0, 0, 0, 0, 0, row[idx_nm_mu]] # t1_13, t1_22, t1_3v, t2_13, t2_22, nm_mun
                sec_votes[k] = v
            nr = row[idx_v]
            qt = int(row[idx_qt])
            if t == '1':
                if nr == '13': v[0] += qt
                elif nr == '22': v[1] += qt
                elif nr not in ('95', '96'): v[2] += qt
            elif t == '2':
                if nr == '13': v[3] += qt
                elif nr == '22': v[4] += qt

print(f"Loaded {len(sec_votes):,} sections in {time.time()-t0:.1f}s.", flush=True)

all_rows = []
for (uf, cd_mun, zona, secao), v in sec_votes.items():
    t1_13, t1_22, t1_3v, t2_13, t2_22, nm_mun = v
    if (t1_13 + t1_22 + t1_3v) == 0 or (t2_13 + t2_22) == 0:
        continue
    d13 = t2_13 - t1_13
    d22 = t2_22 - t1_22
    w1 = '13' if t1_13 > t1_22 else ('22' if t1_22 > t1_13 else 'Empate')
    w2 = '13' if t2_13 > t2_22 else ('22' if t2_22 > t1_13 else 'Empate')
    swing = d13 - d22
    var_abs = abs(d13) + abs(d22)
    if abs(swing) >= 45 or var_abs >= 65 or (w1 != w2 and abs(swing) >= 25):
        all_rows.append({
            'uf': uf, 'municipio': nm_mun, 'zona': f"{zona:04d}", 'secao': f"{secao:04d}",
            't1_13': t1_13, 't1_22': t1_22, 't1_3v': t1_3v,
            't2_13': t2_13, 't2_22': t2_22,
            'delta_13': d13, 'delta_22': d22,
            'virada': f"{w1} → {w2}",
            'swing': swing,
            'var_abs': var_abs
        })

top_geral = heapq.nlargest(50, all_rows, key=lambda x: abs(x['swing']))
top_lula = heapq.nlargest(50, all_rows, key=lambda x: x['delta_13'])
top_flavio = heapq.nlargest(50, all_rows, key=lambda x: x['delta_22'])
top_flip_13 = heapq.nlargest(50, [r for r in all_rows if r['virada'] == '22 → 13'], key=lambda x: x['swing'])
top_flip_22 = heapq.nlargest(50, [r for r in all_rows if r['virada'] == '13 → 22'], key=lambda x: -x['swing'])

# Deduplicate into a combined pool while preserving order, and also store categorized lists
seen = set()
combined = []
for lst in (top_geral, top_lula, top_flavio, top_flip_13, top_flip_22):
    for r in lst:
        key = (r['uf'], r['municipio'], r['zona'], r['secao'])
        if key not in seen:
            seen.add(key)
            combined.append(r)

print(f"Combined pool: {len(combined)} sections (Top 10 geral swing range: {abs(top_geral[0]['swing'])}..{abs(top_geral[9]['swing'])})")

dash_path = os.path.join(PROJ_DIR, 'data', 'dashboard_data.json')
with open(dash_path, 'r', encoding='utf-8') as f:
    dash = json.load(f)

dash['comparativo_geral_t1_t2']['top_swing_secoes'] = combined

with open(dash_path, 'w', encoding='utf-8') as f:
    json.dump(dash, f, ensure_ascii=False, indent=2)

web_js_path = os.path.join(PROJ_DIR, 'web', 'data.js')
with open(web_js_path, 'w', encoding='utf-8') as f:
    f.write('window.ELECTION_DATA = ')
    json.dump(dash, f, ensure_ascii=False)
    f.write(';\n')

print("Updated top_swing_secoes in dashboard_data.json and web/data.js!")
