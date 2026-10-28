import json, os

SCRATCH_BRAIN = r'C:\Users\renan\.gemini\antigravity\brain\01ee89c1-0cb6-4be4-8ef3-288e34eca1bf\scratch'
PROJ_DIR = r'C:\Projetos\MapaDaUrna'

with open(os.path.join(PROJ_DIR, 'data', 'dashboard_data.json'), 'r', encoding='utf-8') as f:
    dash = json.load(f)

with open(os.path.join(SCRATCH_BRAIN, 'censo_t1_t2_exact.json'), 'r', encoding='utf-8') as f:
    censo = json.load(f)

# Update closing_bands with 100% exact T1 and T2 votes from votacao_secao_2026_BR.csv!
for b in dash['closing_bands']:
    bk = b['band']
    cb = censo['censo_bands'][bk]
    t1_val = cb['t1_13'] + cb['t1_22'] + cb['t1_terceira_via']
    t2_val = cb['t2_13'] + cb['t2_22']
    b['t1_13_censo'] = cb['t1_13']
    b['t1_22_censo'] = cb['t1_22']
    b['t1_3v_censo'] = cb['t1_terceira_via']
    b['t1_lula_pct_censo'] = round(cb['t1_13'] / t1_val * 100, 2) if t1_val else 0
    b['t1_flavio_pct_censo'] = round(cb['t1_22'] / t1_val * 100, 2) if t1_val else 0
    b['t2_13_censo'] = cb['t2_13']
    b['t2_22_censo'] = cb['t2_22']
    b['lula_pct_bu'] = round(cb['t2_13'] / t2_val * 100, 2) if t2_val else 0
    b['flavio_pct_bu'] = round(cb['t2_22'] / t2_val * 100, 2) if t2_val else 0
    b['delta_13_censo'] = cb['t2_13'] - cb['t1_13']
    b['delta_22_censo'] = cb['t2_22'] - cb['t1_22']

# Update estendidas_com_vs_sem_voto with 100% exact census T1 & T2
eg_com = censo['est_groups']['est_com_voto17']
eg_sem = censo['est_groups']['est_sem_voto17']
eg_nor = censo['est_groups']['normal']

def build_grp_summary(eg):
    t1_val = eg['t1_13'] + eg['t1_22'] + eg['t1_3v']
    t1_2c = eg['t1_13'] + eg['t1_22']
    t2_val = eg['t2_13'] + eg['t2_22']
    d13 = eg['t2_13'] - eg['t1_13']
    d22 = eg['t2_22'] - eg['t1_22']
    return {
        'urnas_censo': eg['urnas'],
        'votos_pos17_censo': eg['votos_pos17'],
        'votos_pos1720_censo': eg['votos_pos1720'],
        't1_13': eg['t1_13'],
        't1_22': eg['t1_22'],
        't1_3v': eg['t1_3v'],
        't1_lula_pct': round(eg['t1_13'] / t1_val * 100, 2) if t1_val else 0,
        't1_flavio_pct': round(eg['t1_22'] / t1_val * 100, 2) if t1_val else 0,
        't1_lula_2cand_pct': round(eg['t1_13'] / t1_2c * 100, 2) if t1_2c else 0,
        't2_13': eg['t2_13'],
        't2_22': eg['t2_22'],
        'lula_pct_bu': round(eg['t2_13'] / t2_val * 100, 2) if t2_val else 0,
        'flavio_pct_bu': round(eg['t2_22'] / t2_val * 100, 2) if t2_val else 0,
        'delta_13': d13,
        'delta_22': d22,
        'delta_13_pct': round(d13 / eg['t1_13'] * 100, 2) if eg['t1_13'] else 0,
        'delta_22_pct': round(d22 / eg['t1_22'] * 100, 2) if eg['t1_22'] else 0,
        'share_crescimento_lula_pct': round(d13 / (d13 + d22) * 100, 2) if (d13 + d22) else 0
    }

dash['estendidas_com_vs_sem_voto'] = {
    'com_voto_pos17': build_grp_summary(eg_com),
    'sem_voto_pos17': build_grp_summary(eg_sem),
    'normais_ate_1745': build_grp_summary(eg_nor)
}

dash['comparativo_t1_t2'] = {
    'flips_all': censo['flips_all'],
    'flips_est': censo['flips_est'],
    'section_growth_counts': censo['section_growth_counts'],
    'top_est_sections': censo['top_est_sections']
}

# Also enrich uf_summary and top_municipios_estendidas with exact T1 and T2 census data in extended urnas!
for u in dash['uf_summary']:
    uf_k = u['uf']
    ue = censo['uf_exact'].get(uf_k, {})
    t1_e_tot = ue.get('t1_13_est', 0) + ue.get('t1_22_est', 0) + ue.get('t1_3v_est', 0)
    t2_e_tot = ue.get('t2_13_est', 0) + ue.get('t2_22_est', 0)
    u['t1_13_est'] = ue.get('t1_13_est', 0)
    u['t1_22_est'] = ue.get('t1_22_est', 0)
    u['t2_13_est'] = ue.get('t2_13_est', 0)
    u['t2_22_est'] = ue.get('t2_22_est', 0)
    u['t1_est_lula_pct'] = round(ue.get('t1_13_est', 0) / t1_e_tot * 100, 2) if t1_e_tot else None
    u['t2_est_lula_pct'] = round(ue.get('t2_13_est', 0) / t2_e_tot * 100, 2) if t2_e_tot else None
    u['t2_est_flavio_pct'] = round(ue.get('t2_22_est', 0) / t2_e_tot * 100, 2) if t2_e_tot else None

mun_map = {(m['uf'], m['municipio']): m for m in censo['mun_exact_est']}
for m in dash['top_municipios_estendidas']:
    me = mun_map.get((m['uf'], m['municipio']), {})
    t1_e_tot = me.get('t1_13_est', 0) + me.get('t1_22_est', 0) + me.get('t1_3v_est', 0)
    t2_e_tot = me.get('t2_13_est', 0) + me.get('t2_22_est', 0)
    m['t1_13_est'] = me.get('t1_13_est', 0)
    m['t1_22_est'] = me.get('t1_22_est', 0)
    m['t2_13_est'] = me.get('t2_13_est', 0)
    m['t2_22_est'] = me.get('t2_22_est', 0)
    m['t1_est_lula_pct'] = round(me.get('t1_13_est', 0) / t1_e_tot * 100, 2) if t1_e_tot else 0
    m['t2_est_lula_pct'] = round(me.get('t2_13_est', 0) / t2_e_tot * 100, 2) if t2_e_tot else 0
    m['t2_est_flavio_pct'] = round(me.get('t2_22_est', 0) / t2_e_tot * 100, 2) if t2_e_tot else 0

with open(os.path.join(PROJ_DIR, 'data', 'dashboard_data.json'), 'w', encoding='utf-8') as f:
    json.dump(dash, f, ensure_ascii=False, indent=2)

with open(os.path.join(PROJ_DIR, 'web', 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.ELECTION_DATA = ' + json.dumps(dash, ensure_ascii=False, indent=2) + ';\n')

print("Updated C:\\Projetos\\MapaDaUrna\\data\\dashboard_data.json and web\\data.js with 100% exact census T1 vs T2!")
