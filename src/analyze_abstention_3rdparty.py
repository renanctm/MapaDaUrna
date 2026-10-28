import sys, zipfile, csv, io, json, os, time
from collections import defaultdict
import math

sys.stdout.reconfigure(encoding='utf-8')

SCRATCH_BRAIN = r'C:\Users\renan\.gemini\antigravity\brain\01ee89c1-0cb6-4be4-8ef3-288e34eca1bf\scratch'
PROJ_DIR = r'C:\Projetos\MapaDaUrna'
zip_path = os.path.join(SCRATCH_BRAIN, 'votacao_secao_2026_BR.zip')
secoes_csv_path = os.path.join(SCRATCH_BRAIN, 'apolinario_secoes.csv')

t0 = time.time()
print("1. Loading aptos from apolinario_secoes.csv...", flush=True)
sec_aptos = {}
if os.path.exists(secoes_csv_path):
    with open(secoes_csv_path, 'r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            k = (row['uf'], int(row['municipio_codigo']), int(row['zona']), int(row['secao']))
            sec_aptos[k] = int(row['aptos']) if row.get('aptos') else 0
print(f"Loaded aptos for {len(sec_aptos):,} sections.")

print("2. Loading votacao_secao_2026_BR.csv...", flush=True)
# v = [t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, t2_13, t2_22, t2_bn, nm_mun]
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

# Filter to sections that functioned in BOTH T1 and T2 (so turnout changes aren't distorted by missing sections)
valid_both = 0
only_t1 = 0
only_t2 = 0

# Band definitions for Flavio T1 share (% of valid votes in T1)
FLAVIO_BANDS = [
    ('< 20% (Reduto Lula)', 0.0, 20.0),
    ('20% a 35% (Forte Lula)', 20.0, 35.0),
    ('35% a 45% (Vantagem Lula)', 35.0, 45.0),
    ('45% a 50% (Disputada - Lula/3ªVia)', 45.0, 50.0),
    ('50% a 55% (Vantagem Flávio)', 50.0, 55.0),
    ('55% a 65% (Forte Flávio)', 55.0, 65.0),
    ('65% a 75% (Muito Forte Flávio)', 65.0, 75.0),
    ('>= 75% (Reduto Extremo Flávio)', 75.0, 100.01)
]

# Band definitions for 3rd party T1 share (% of valid votes in T1)
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
        'aptos_t1_comp': 0, 'aptos_t2_comp': 0
    }

flavio_stats = {b[0]: make_bucket() for b in FLAVIO_BANDS}
third_stats = {b[0]: make_bucket() for b in THIRD_BANDS}
leader_3v_stats = {
    '70 - Augusto Cury líder 3ªVia (>=5% na urna)': make_bucket(),
    '14 - Renan Santos líder 3ªVia (>=5% na urna)': make_bucket(),
    '55 - Ronaldo Caiado líder 3ªVia (>=5% na urna)': make_bucket(),
    '30 - Romeu Zema líder 3ªVia (>=3% na urna)': make_bucket(),
}

# Also check by Region how abstention behaved
reg_abst = defaultdict(make_bucket)
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
        bk['abst_up_secoes'] += 1 # turnout fell -> abstention increased
    elif t2_comp > t1_comp:
        bk['abst_down_secoes'] += 1 # turnout rose -> abstention decreased
    else:
        bk['abst_same_secoes'] += 1
    if aptos > 0 and aptos >= max(t1_comp, t2_comp):
        bk['aptos'] += aptos
        bk['aptos_secoes'] += 1
        bk['aptos_t1_comp'] += t1_comp
        bk['aptos_t2_comp'] += t2_comp

# Ecological regression data (using shares of T1 total turnout or shares of T1 valid votes)
# Wait: let's also fit an exact linear system (OLS) predicting:
# d13 = t2_13 - t1_13 and d22 = t2_22 - t1_22 as a function of (t1_70, t1_14, t1_55, t1_30, t1_out, d_bn_inv, d_comp, t1_13, t1_22)
# Even cleaner: let's predict T2 outcomes [t2_13, t2_22, t2_bn, abst_t2] from T1 inputs [t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, abst_t1]
# across all sections with aptos > 0!

ols_rows = []
total_both = make_bucket()

for k, v in sec_votes.items():
    uf, cd_mun, zona, secao = k
    t1_13, t1_22, t1_70, t1_14, t1_55, t1_30, t1_out, t1_bn, t2_13, t2_22, t2_bn, nm_mun = v
    t1_val = t1_13 + t1_22 + t1_70 + t1_14 + t1_55 + t1_30 + t1_out
    t2_val = t2_13 + t2_22
    t1_comp = t1_val + t1_bn
    t2_comp = t2_val + t2_bn
    
    if t1_comp == 0 and t2_comp > 0:
        only_t2 += 1
        continue
    if t2_comp == 0 and t1_comp > 0:
        only_t1 += 1
        continue
    if t1_val == 0 or t2_val == 0:
        continue
        
    valid_both += 1
    aptos = sec_aptos.get(k, 0)
    add_to_bucket(total_both, v, aptos)
    add_to_bucket(reg_abst[get_reg(uf)], v, aptos)
    
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
            
    # Check leader of 3rd party in this section
    cands_3v = [(t1_70, '70'), (t1_14, '14'), (t1_55, '55'), (t1_30, '30')]
    cands_3v.sort(reverse=True)
    top_votes, top_code = cands_3v[0]
    top_pct = (top_votes / t1_val) * 100.0
    if top_code == '70' and top_pct >= 5.0:
        add_to_bucket(leader_3v_stats['70 - Augusto Cury líder 3ªVia (>=5% na urna)'], v, aptos)
    elif top_code == '14' and top_pct >= 5.0:
        add_to_bucket(leader_3v_stats['14 - Renan Santos líder 3ªVia (>=5% na urna)'], v, aptos)
    elif top_code == '55' and top_pct >= 5.0:
        add_to_bucket(leader_3v_stats['55 - Ronaldo Caiado líder 3ªVia (>=5% na urna)'], v, aptos)
    elif top_code == '30' and top_pct >= 3.0:
        add_to_bucket(leader_3v_stats['30 - Romeu Zema líder 3ªVia (>=3% na urna)'], v, aptos)

print(f"\nSections functioning in both T1 and T2: {valid_both:,} (Only T1: {only_t1}, Only T2: {only_t2})")

def print_table(title, stats_dict, keys_order=None):
    print(f"\n==================== {title} ====================")
    if keys_order is None:
        keys_order = list(stats_dict.keys())
    for k in keys_order:
        b = stats_dict[k]
        if b['secoes'] == 0: continue
        t1_val = b['t1_13'] + b['t1_22'] + b['t1_3v']
        t2_val = b['t2_13'] + b['t2_22']
        d_comp = b['t2_comp'] - b['t1_comp'] # negative means abstention increased!
        d_abst = -d_comp # positive means more abstention in T2 than T1
        pct_d_comp = (d_comp / b['t1_comp'] * 100.0) if b['t1_comp'] else 0
        pct_sec_abst_up = (b['abst_up_secoes'] / b['secoes'] * 100.0)
        
        abst_t1_pct = ((b['aptos'] - b['aptos_t1_comp']) / b['aptos'] * 100.0) if b['aptos'] else 0
        abst_t2_pct = ((b['aptos'] - b['aptos_t2_comp']) / b['aptos'] * 100.0) if b['aptos'] else 0
        d_abst_pp = abst_t2_pct - abst_t1_pct
        
        d13 = b['t2_13'] - b['t1_13']
        d22 = b['t2_22'] - b['t1_22']
        d_bn = b['t2_bn'] - b['t1_bn']
        
        # Share of (d13 + d22) captured by Lula vs Flavio
        tot_gain = d13 + d22
        share_d13 = (d13 / tot_gain * 100.0) if tot_gain > 0 else 0
        share_d22 = (d22 / tot_gain * 100.0) if tot_gain > 0 else 0
        
        print(f"\n[{k}] ({b['secoes']:,} seções)")
        print(f"  1ºT Válidos: Lula {b['t1_13']:,} ({b['t1_13']/t1_val*100:.2f}%) | Flávio {b['t1_22']:,} ({b['t1_22']/t1_val*100:.2f}%) | 3ªVia {b['t1_3v']:,} ({b['t1_3v']/t1_val*100:.2f}%)")
        print(f"  2ºT Válidos: Lula {b['t2_13']:,} ({b['t2_13']/t2_val*100:.2f}%) | Flávio {b['t2_22']:,} ({b['t2_22']/t2_val*100:.2f}%)")
        print(f"  Comparecimento: 1ºT {b['t1_comp']:,} -> 2ºT {b['t2_comp']:,} | Δ Comp: {d_comp:+,} ({pct_d_comp:+.2f}%) | Δ Abstenção: {d_abst:+,} votos")
        print(f"  Taxa Abstenção (seções c/ aptos): 1ºT {abst_t1_pct:.2f}% -> 2ºT {abst_t2_pct:.2f}% ({d_abst_pp:+.2f} p.p.) | Seções c/ aumento de abstenção: {b['abst_up_secoes']:,} ({pct_sec_abst_up:.1f}%)")
        print(f"  Fluxo de Votos (2ºT - 1ºT): Δ Lula = {d13:+,} (+{d13/b['t1_13']*100:.2f}%) | Δ Flávio = {d22:+,} (+{d22/b['t1_22']*100:.2f}%) | Δ Brancos/Nulos = {d_bn:+,}")
        print(f"  Divisão do Crescimento Líquido (Δ13 vs Δ22): Lula {share_d13:.1f}% vs Flávio {share_d22:.1f}%")

print_table("TOTAL BRASIL + EXTERIOR (SEÇÕES ATIVAS EM AMBOS OS TURNOS)", {'Total Geral': total_both})
print_table("FAIXAS DE PREDOMINÂNCIA DE FLÁVIO NO 1º TURNO (% VÁLIDOS 1ºT)", flavio_stats, [b[0] for b in FLAVIO_BANDS])
print_table("FAIXAS DE DESEMPENHO DA 3ª VIA NO 1º TURNO (% VÁLIDOS 1ºT)", third_stats, [b[0] for b in THIRD_BANDS])
print_table("PERFIL POR LÍDER DA 3ª VIA NA SEÇÃO ELEITORAL", leader_3v_stats)
print_table("COMPORTAMENTO DA ABSTENÇÃO E MIGRAÇÃO POR REGIÃO", reg_abst, ['Nordeste', 'Norte', 'Sudeste', 'Centro-Oeste', 'Sul', 'Exterior'])
