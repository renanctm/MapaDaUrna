import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'C:\Projetos\MapaDaUrna\data\dashboard_data.json', encoding='utf-8') as f:
    d = json.load(f)['comparativo_geral_t1_t2']['por_uf']

print("UF | Regiao       | 1T %22 | Comp 1T    -> Comp 2T    | dComp (%)        | d13        | d22       | 3aVia 1T  | dBN")
print("-" * 115)
rows = []
for u in d:
    c1 = u['t1_13'] + u['t1_22'] + u['t1_3v'] + u['t1_bn']
    c2 = u['t2_13'] + u['t2_22'] + u['t2_bn']
    dc = c2 - c1
    pct_dc = dc / c1 * 100.0
    dbn = u['t2_bn'] - u['t1_bn']
    rows.append((pct_dc, u, c1, c2, dc, dbn))

for pct_dc, u, c1, c2, dc, dbn in sorted(rows, key=lambda x: x[0]):
    print(f"{u['uf']:2s} | {u['regiao']:12s} | {u['t1_flavio_pct']:5.1f}% | {c1:10,d} -> {c2:10,d} | {dc:+9,d} ({pct_dc:+5.2f}%) | {u['delta_13']:+10,d} | {u['delta_22']:+9,d} | {u['t1_3v']:9,d} | {dbn:+8,d}")
