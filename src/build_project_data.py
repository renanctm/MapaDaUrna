import json, csv, os, math
from collections import defaultdict, Counter

SCRATCH_BRAIN = r'C:\Users\renan\.gemini\antigravity\brain\01ee89c1-0cb6-4be4-8ef3-288e34eca1bf\scratch'
PROJ_DIR = r'C:\Projetos\MapaDaUrna'
os.makedirs(os.path.join(PROJ_DIR, 'data'), exist_ok=True)
os.makedirs(os.path.join(PROJ_DIR, 'src'), exist_ok=True)
os.makedirs(os.path.join(PROJ_DIR, 'web'), exist_ok=True)

with open(os.path.join(SCRATCH_BRAIN, 'all_muns_votes.json'), 'r', encoding='utf-8') as f:
    muns = json.load(f)

with open(os.path.join(SCRATCH_BRAIN, 'sample_10000_bus.json'), 'r', encoding='utf-8') as f:
    sample_bus = json.load(f)

scen2_bus = []
with open(os.path.join(SCRATCH_BRAIN, 'scenario2_results.jsonl'), 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            obj = json.loads(line)
            if obj.get('status') == 'ok_bu':
                scen2_bus.append(obj)

all_bus_dict = {}
for b in sample_bus:
    all_bus_dict[(b['uf'].upper(), b['mu'], b['z'], b['s'])] = b
for b in scen2_bus:
    all_bus_dict[(b['uf'].upper(), b['mu'], b['z'], b['s'])] = b
all_bus = list(all_bus_dict.values())

def to_sec(hhmmss):
    return int(hhmmss[0:2])*3600 + int(hhmmss[2:4])*60 + int(hhmmss[4:6])

def get_tz_offset_hours(b):
    uf = b['uf'].lower()
    if uf == 'ac': return 2
    if uf in ('ms', 'mt', 'ro', 'rr'): return 1
    if uf == 'am':
        ab_h = int(b['abertura'][9:11]) if b['abertura'] else 7
        return 2 if ab_h <= 6 else 1
    if uf == 'pe' and b['abertura'] and b['abertura'][9:11] == '09':
        return -1
    return 0

# 1. Censo Exato de Encerramento e Logs (secoes.csv do urnas-tardias) + Cruzamento com nossos BUs
closing_bands_order = [
    '1. <= 17:01:00 (Imediato)',
    '2. 17:01:01 a 17:03:00 (Padrão)',
    '3. 17:03:01 a 17:05:00 (Tolerância)',
    '4. 17:05:01 a 17:10:00 (Fila curta)',
    '5. 17:10:01 a 17:30:00 (Fila moderada)',
    '6. 17:30:01 a 17:44:59 (Fila longa)',
    '7. 17:45:00 a 18:54:59 (Estendida parcial)',
    '8. >= 18:55:00 (Prorrogada até 19h STF)'
]

censo_bands = {k: {'urnas_censo': 0, 'votos_pos17_log': 0, 'votos_pos1720_log': 0, 'urnas_amostra_bu': 0, 'v13_bu': 0, 'v22_bu': 0, 'aptos_bu': 0, 'comp_bu': 0} for k in closing_bands_order}

uf_estendidas = defaultdict(lambda: {'urnas_total': 0, 'estendidas_1745': 0, 'prorrogadas_1855': 0, 'com_voto_pos17': 0, 'sem_voto_pos17': 0, 'votos_pos17': 0, 'votos_pos1720': 0, 'bu_n': 0, 'bu_v13': 0, 'bu_v22': 0})
mun_estendidas = defaultdict(lambda: {'uf': '', 'municipio': '', 'urnas_total': 0, 'estendidas': 0, 'prorrogadas_1855': 0, 'com_voto_pos17': 0, 'votos_pos17': 0, 'votos_pos1720': 0, 'bu_n': 0, 'bu_v13': 0, 'bu_v22': 0})

contingencia_bugs = []
clock_bugs = []
est_com_voto_bu = {'n': 0, 'v13': 0, 'v22': 0, 'v17': 0}
est_sem_voto_bu = {'n': 0, 'v13': 0, 'v22': 0}

with open(os.path.join(SCRATCH_BRAIN, 'secoes.csv'), 'r', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        uf = row['uf']
        if uf == 'ZZ': continue
        enc = row['encerramento_brt']
        ab = row['abertura_brt']
        v17 = int(row['votos_apos_17h'])
        v1720 = int(row['votos_apos_17h20'])
        vtot = int(row['votos_total'])
        
        if enc <= '17:01:00': bk = closing_bands_order[0]
        elif enc <= '17:03:00': bk = closing_bands_order[1]
        elif enc <= '17:05:00': bk = closing_bands_order[2]
        elif enc <= '17:10:00': bk = closing_bands_order[3]
        elif enc <= '17:30:00': bk = closing_bands_order[4]
        elif enc < '17:45:00': bk = closing_bands_order[5]
        elif enc < '18:55:00': bk = closing_bands_order[6]
        else: bk = closing_bands_order[7]
        
        censo_bands[bk]['urnas_censo'] += 1
        censo_bands[bk]['votos_pos17_log'] += v17
        censo_bands[bk]['votos_pos1720_log'] += v1720
        
        u = uf_estendidas[uf]
        u['urnas_total'] += 1
        if row['classe'] == 'estendida':
            u['estendidas_1745'] += 1
            u['votos_pos17'] += v17
            u['votos_pos1720'] += v1720
            if v17 > 0: u['com_voto_pos17'] += 1
            else: u['sem_voto_pos17'] += 1
        if enc >= '18:55:00':
            u['prorrogadas_1855'] += 1
            
        m = mun_estendidas[(uf, row['cd_mun'])]
        m['uf'] = uf
        m['municipio'] = row['municipio']
        m['urnas_total'] += 1
        if row['classe'] == 'estendida':
            m['estendidas'] += 1
            m['votos_pos17'] += v17
            m['votos_pos1720'] += v1720
            if v17 > 0: m['com_voto_pos17'] += 1
        if enc >= '18:55:00':
            m['prorrogadas_1855'] += 1
            
        if ab > '12:00:00':
            contingencia_bugs.append(row)
        if enc > '20:00:00' or enc < '16:50:00':
            clock_bugs.append(row)
            
        k = (uf, row['cd_mun'], row['zona'], row['secao'])
        if k in all_bus_dict:
            b = all_bus_dict[k]
            censo_bands[bk]['urnas_amostra_bu'] += 1
            censo_bands[bk]['v13_bu'] += b['v13']
            censo_bands[bk]['v22_bu'] += b['v22']
            censo_bands[bk]['aptos_bu'] += b['aptos']
            censo_bands[bk]['comp_bu'] += b['comp']
            if row['classe'] == 'estendida':
                u['bu_n'] += 1
                u['bu_v13'] += b['v13']
                u['bu_v22'] += b['v22']
                m['bu_n'] += 1
                m['bu_v13'] += b['v13']
                m['bu_v22'] += b['v22']
                if v17 > 0:
                    est_com_voto_bu['n'] += 1
                    est_com_voto_bu['v13'] += b['v13']
                    est_com_voto_bu['v22'] += b['v22']
                    est_com_voto_bu['v17'] += v17
                else:
                    est_sem_voto_bu['n'] += 1
                    est_sem_voto_bu['v13'] += b['v13']
                    est_sem_voto_bu['v22'] += b['v22']

# Add official municipal vote totals to mun_estendidas
mun_official = {(m['uf'].upper(), m['mu']): m for m in muns}
for (uf, cd_mun), m in mun_estendidas.items():
    off = mun_official.get((uf, cd_mun), {})
    m['mun_v13_oficial'] = off.get('v13', 0)
    m['mun_v22_oficial'] = off.get('v22', 0)
    m['mun_ht_oficial'] = off.get('ht', '')

# 2. Timeline de Totalização (por aux.hr na amostra de 9.996 BUs + por mun.ht nos 5.757 municípios)
hr_buckets = defaultdict(lambda: {'n': 0, 'v13': 0, 'v22': 0})
for b in sample_bus:
    dr = b.get('aux_dr') or ''
    hr = b.get('aux_hr') or ''
    if dr != '25/10/2026' or not hr:
        key = 'Após 21:15 / 26/10'
    else:
        hh = hr[:2]
        mm = int(hr[3:5]) // 15 * 15
        if hh < '19':
            key = '17:00 - 18:59 (Pré-pausa STF)'
        elif (hh == '21' and mm >= 15) or hh >= '22':
            key = 'Após 21:15 / 26/10'
        else:
            key = f'{hh}:{mm:02d} - {hh}:{mm+14:02d}'
    hr_buckets[key]['n'] += 1
    hr_buckets[key]['v13'] += b['v13']
    hr_buckets[key]['v22'] += b['v22']

timeline_list = []
c13, c22, cu = 0, 0, 0
tot_sample_u = len(sample_bus)
for k in sorted(hr_buckets.keys()):
    d = hr_buckets[k]
    vt = d['v13'] + d['v22']
    c13 += d['v13']
    c22 += d['v22']
    cu += d['n']
    timeline_list.append({
        'window': k,
        'urnas_sample': d['n'],
        'pct_lote_urnas': round(d['n'] / tot_sample_u * 100, 2),
        'lula_lote_pct': round(d['v13'] / vt * 100, 2) if vt else 0,
        'flavio_lote_pct': round(d['v22'] / vt * 100, 2) if vt else 0,
        'cum_urnas_pct': round(cu / tot_sample_u * 100, 2),
        'cum_lula_pct': round(c13 / (c13 + c22) * 100, 2) if (c13 + c22) else 0,
        'cum_flavio_pct': round(c22 / (c13 + c22) * 100, 2) if (c13 + c22) else 0
    })

# Build final summary object
summary_data = {
    'eleicao': {
        'pleito': '2º Turno Presidencial 2026 (25/10/2026)',
        'lula_votos': 64256232,
        'lula_pct': 51.79,
        'flavio_votos': 59826041,
        'flavio_pct': 48.21,
        'diferenca_votos': 4430191,
        'total_secoes_pais': 497882,
        'total_municipios': 5757,
        'urnas_estendidas_1745': 7352,
        'urnas_prorrogadas_1855': 6713,
        'urnas_estendidas_com_voto_pos17': 3348,
        'urnas_estendidas_sem_voto_pos17': 4004,
        'votos_pos17_nas_estendidas': 5052,
        'votos_pos1720_nas_estendidas': 3542,
        'votos_pos17_todas_urnas': 34330,
        'bus_decodificados_amostra': len(all_bus)
    },
    'closing_bands': [
        {
            'band': k,
            'urnas_censo': v['urnas_censo'],
            'pct_urnas_censo': round(v['urnas_censo'] / 497882 * 100, 2),
            'votos_pos17_log': v['votos_pos17_log'],
            'votos_pos1720_log': v['votos_pos1720_log'],
            'urnas_amostra_bu': v['urnas_amostra_bu'],
            'v13_bu': v['v13_bu'],
            'v22_bu': v['v22_bu'],
            'lula_pct_bu': round(v['v13_bu'] / (v['v13_bu'] + v['v22_bu']) * 100, 2) if (v['v13_bu'] + v['v22_bu']) else 0,
            'flavio_pct_bu': round(v['v22_bu'] / (v['v13_bu'] + v['v22_bu']) * 100, 2) if (v['v13_bu'] + v['v22_bu']) else 0,
            'abstencao_pct_bu': round((1 - v['comp_bu'] / v['aptos_bu']) * 100, 2) if v['aptos_bu'] else 0
        }
        for k, v in censo_bands.items()
    ],
    'timeline_totalizacao': timeline_list,
    'estendidas_com_vs_sem_voto': {
        'com_voto_pos17': {
            'urnas_censo': 3348,
            'votos_pos17_censo': 5052,
            'urnas_bu_amostra': est_com_voto_bu['n'],
            'lula_pct_bu': round(est_com_voto_bu['v13'] / (est_com_voto_bu['v13'] + est_com_voto_bu['v22']) * 100, 2),
            'flavio_pct_bu': round(est_com_voto_bu['v22'] / (est_com_voto_bu['v13'] + est_com_voto_bu['v22']) * 100, 2)
        },
        'sem_voto_pos17': {
            'urnas_censo': 4004,
            'votos_pos17_censo': 0,
            'urnas_bu_amostra': est_sem_voto_bu['n'],
            'lula_pct_bu': round(est_sem_voto_bu['v13'] / (est_sem_voto_bu['v13'] + est_sem_voto_bu['v22']) * 100, 2),
            'flavio_pct_bu': round(est_sem_voto_bu['v22'] / (est_sem_voto_bu['v13'] + est_sem_voto_bu['v22']) * 100, 2)
        }
    },
    'uf_summary': [
        {
            'uf': uf,
            **v,
            'pct_estendidas': round(v['estendidas_1745'] / v['urnas_total'] * 100, 2) if v['urnas_total'] else 0,
            'bu_lula_pct': round(v['bu_v13'] / (v['bu_v13'] + v['bu_v22']) * 100, 2) if (v['bu_v13'] + v['bu_v22']) else None,
            'bu_flavio_pct': round(v['bu_v22'] / (v['bu_v13'] + v['bu_v22']) * 100, 2) if (v['bu_v13'] + v['bu_v22']) else None
        }
        for uf, v in sorted(uf_estendidas.items(), key=lambda x: -x[1]['estendidas_1745'])
    ],
    'top_municipios_estendidas': [
        {
            **m,
            'pct_estendidas': round(m['estendidas'] / m['urnas_total'] * 100, 2) if m['urnas_total'] else 0,
            'mun_lula_pct_oficial': round(m['mun_v13_oficial'] / (m['mun_v13_oficial'] + m['mun_v22_oficial']) * 100, 2) if (m['mun_v13_oficial'] + m['mun_v22_oficial']) else 0,
            'mun_flavio_pct_oficial': round(m['mun_v22_oficial'] / (m['mun_v13_oficial'] + m['mun_v22_oficial']) * 100, 2) if (m['mun_v13_oficial'] + m['mun_v22_oficial']) else 0,
            'bu_est_lula_pct': round(m['bu_v13'] / (m['bu_v13'] + m['bu_v22']) * 100, 2) if (m['bu_v13'] + m['bu_v22']) else None
        }
        for m in sorted(mun_estendidas.values(), key=lambda x: -x['estendidas']) if m['estendidas'] > 0
    ],
    'auditoria_urnas_tardias': {
        'contingencia_abertura_tarde_count': len(contingencia_bugs),
        'relogio_descalibrado_count': len(clock_bugs),
        'exemplos_contingencia': [
            {
                'uf': 'AL', 'municipio': 'ANADIA', 'zona': '0048', 'secao': '0200',
                'abertura_repo': '14:01:26', 'votos_repo': 40,
                'abertura_real_bu': '08:00:01', 'votos_real_bu': 219,
                'arquivo_ignorado': '0243347925102026135737-01.jez'
            },
            {
                'uf': 'AL', 'municipio': 'OURO BRANCO', 'zona': '0050', 'secao': '0079',
                'abertura_repo': '16:52:47', 'votos_repo': 44,
                'abertura_real_bu': '08:00:01', 'votos_real_bu': 286,
                'arquivo_ignorado': '016679612510202616463301ME.jez'
            }
        ],
        'exemplos_relogio': [
            {
                'uf': 'MG', 'municipio': 'CHAPADA GAÚCHA', 'zona': '0320', 'secao': '0185',
                'abertura_brt': '23:04:03', 'encerramento_brt': '23:04:42', 'votos_total': 0,
                'motivo': 'Relógio interno da urna em 23h04 (classificada erroneamente como estendida)'
            }
        ]
    }
}

with open(os.path.join(PROJ_DIR, 'data', 'dashboard_data.json'), 'w', encoding='utf-8') as f:
    json.dump(summary_data, f, ensure_ascii=False, indent=2)

with open(os.path.join(PROJ_DIR, 'web', 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.ELECTION_DATA = ' + json.dumps(summary_data, ensure_ascii=False, indent=2) + ';\n')

print('Successfully generated dashboard_data.json and web/data.js! Total muns with extended urnas:', len(summary_data['top_municipios_estendidas']))
