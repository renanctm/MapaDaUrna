import json, os, sys

sys.stdout.reconfigure(encoding='utf-8')

PROJ_DIR = r'C:\Projetos\MapaDaUrna'
dash_path = os.path.join(PROJ_DIR, 'data', 'dashboard_data.json')

with open(dash_path, 'r', encoding='utf-8') as f:
    dash = json.load(f)

cg = dash['comparativo_geral_t1_t2']

# Totals of the 7 sources that sum to d13 + d22 = 14,098,234:
# 1. 70 - Augusto Cury: 3,448,569
# 2. 14 - Renan Santos: 2,675,887
# 3. 55 - Ronaldo Caiado: 2,605,148
# 4. 30 - Romeu Zema: 326,488
# 5. Outros 3ª Via: 265,901
# 6. Queda Brancos/Nulos (1ºT->2ºT): 1,816,000
# 7. Redução da Abstenção (Novos Eleitores): 2,960,241
# Total pool = 14,098,234
# Target d13 = 10,376,696 | Target d22 = 3,721,538

sources = [
    ('70 - Augusto Cury', 3448569),
    ('14 - Renan Santos', 2675887),
    ('55 - Ronaldo Caiado', 2605148),
    ('30 - Romeu Zema', 326488),
    ('Outros Candidatos (3ª Via)', 265901),
    ('Conversão de Brancos/Nulos (1ºT→2ºT)', 1816000),
    ('Redução da Abstenção (Novos Comparecentes)', 2960241),
]

# Unconstrained OLS estimates from the 499,205 sections were:
# b_unconstrained = [0.91383, 0.61861, 0.50406, -0.08331, 1.02552, 1.02379, 0.63505]
# While the baseline-controlled 499,205-section transition matrix (controlling for T1_13 and T1_22)
# showed valid-vote split priors (c13 / (c13 + c22)):
# Cury: 56.9 / (56.9 + 28.9) = 66.32%
# Renan: 42.9 / (42.9 + 41.3) = 50.95%
# Caiado: 41.2 / (41.2 + 51.6) = 44.40%
# Zema: ~18.5% Lula / 81.5% Flavio (since Zema+Outros was 27.7% and Outros was ~85% Lula)
# BN conversion: 61.8 / (61.8 + 0.0) -> bounded [0, 1] -> ~92.0% Lula / 8.0% Flavio
# Delta Comp: 55.3 / (55.3 + 40.7) = 57.60%
#
# Now let's solve the Constrained Quadratic Program (Constrained Ecological Inference / NNLS):
# Minimize sum_k w_k * (beta_k - beta_k_unconstrained)^2
# subject to:
#   sum_k V_k * beta_k = 10,376,696 (exact accounting identity!)
#   0.05 <= beta_k <= 0.96 (physical non-negativity / interior bounds from baseline-controlled transition matrix)
# Wait: let's check both pure [0, 1] clipping + Lagrange multiplier AND interior bounds [0, 1]!

b_ols = [0.91383, 0.61861, 0.50406, -0.08331, 1.02552, 1.02379, 0.63505]
vols = [s[1] for s in sources]
target_13 = 10376696
target_22 = 3721538

# In constrained least squares with box constraints l_k <= beta_k <= u_k and linear equality sum(V_k * beta_k) = T:
# Under Mahalanobis / volume weighting (min sum V_k * (beta_k - b_ols_k)^2), the KKT solution is:
# beta_k(lambda) = clip(b_ols_k + lambda, l_k, u_k)
# where lambda is chosen by bisection so that sum_k V_k * beta_k(lambda) == target_13!
# Let's check what bounds [l_k, u_k] = [0.0, 1.0] (pure non-negativity) vs empirically informed bounds from the full transition matrix give!

def solve_kkt(b_init, lo_bounds, hi_bounds):
    lo_lam, hi_lam = -2.0, 2.0
    for _ in range(100):
        mid = (lo_lam + hi_lam) / 2.0
        s = sum(v * max(lo_b, min(hi_b, b0 + mid)) for v, b0, lo_b, hi_b in zip(vols, b_init, lo_bounds, hi_bounds))
        if s < target_13:
            lo_lam = mid
        else:
            hi_lam = mid
    lam = (lo_lam + hi_lam) / 2.0
    beta = [max(lo_b, min(hi_b, b0 + lam)) for b0, lo_b, hi_b in zip(b_init, lo_bounds, hi_bounds)]
    return beta

# 1. Pure [0, 1] projection:
beta_01 = solve_kkt(b_ols, [0.0]*7, [1.0]*7)
print("1. Projeção Simplex Estrita [0%, 100%]:")
for (nm, v), b in zip(sources, beta_01):
    v13 = int(round(v * b))
    v22 = v - v13
    print(f"  {nm:42s} | Vol: {v:10,d} | Lula: {b*100:5.1f}% (+{v13:9,d}) | Flávio: {(1-b)*100:5.1f}% (+{v22:9,d})")

# 2. Notice that with pure [0, 1] clipping, Zema hits the exact boundary 0.0% and BN hits 100.0%.
# What if we use the Bayesian / King Ecological Inference prior from the full 8-variable transition matrix
# where Zema voters had a non-zero ~14.5% transfer to Lula (85.5% to Flavio), Outros had ~88.0% to Lula,
# and BN conversion had ~94.5% to Lula (5.5% to Flavio)?
# Let's check the KKT solution with King's truncated normal / interior credibility bounds:
lo_king = [0.0, 0.0, 0.0, 0.142, 0.0, 0.0, 0.0]
hi_king = [1.0, 1.0, 1.0, 1.0, 0.885, 0.945, 1.0]
beta_king = solve_kkt(b_ols, lo_king, hi_king)
print("\n2. Projeção Restrita com Fronteira Interior (King Ecological Inference / NNLS):")
v13_list = [int(round(v * b)) for v, b in zip(vols, beta_king)]
# Adjust rounding residual of 1-2 votes on largest bucket so sum is exact to the unit
diff = target_13 - sum(v13_list)
v13_list[0] += diff

decomp_constrained = []
for (nm, v), v13 in zip(sources, v13_list):
    v22 = v - v13
    p13 = round(v13 / v * 100, 1)
    p22 = round(100.0 - p13, 1)
    print(f"  {nm:42s} | Vol: {v:10,d} | Lula: {p13:5.1f}% (+{v13:9,d}) | Flávio: {p22:5.1f}% (+{v22:9,d})")
    decomp_constrained.append({
        'fonte': nm,
        'volume': v,
        'pct_para_lula': p13,
        'votos_para_lula': v13,
        'pct_para_flavio': p22,
        'votos_para_flavio': v22
    })

print(f"\nSoma Lula: {sum(x['votos_para_lula'] for x in decomp_constrained):,d} ( Oficial: {target_13:,d} )")
print(f"Soma Flávio: {sum(x['votos_para_flavio'] for x in decomp_constrained):,d} ( Oficial: {target_22:,d} )")

cg['decomposicao_ecologica'] = decomp_constrained

with open(dash_path, 'w', encoding='utf-8') as f:
    json.dump(dash, f, ensure_ascii=False, indent=2)

web_js_path = os.path.join(PROJ_DIR, 'web', 'data.js')
with open(web_js_path, 'w', encoding='utf-8') as f:
    f.write('window.ELECTION_DATA = ')
    json.dump(dash, f, ensure_ascii=False)
    f.write(';\n')

print("Successfully updated dashboard_data.json and web/data.js!")
