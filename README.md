# Mapa da Urna — Análise & Auditoria das Eleições Presidenciais 2026 (TSE)

Plataforma aberta e independente de análise estatística, auditoria de dados e visualização interativa das **Eleições Presidenciais de 2026 (1º Turno em 04/10/2026 e 2º Turno em 25/10/2026)**, baseada no cruzamento censitário das **499.206 seções eleitorais** (Brasil e Exterior) a partir dos pacotes públicos do Tribunal Superior Eleitoral (TSE).

* **Acesso Público no Ar:** [https://mapadaurna.web.app](https://mapadaurna.web.app)
* **Manifesto Criptográfico:** [https://mapadaurna.web.app/hashes.txt](https://mapadaurna.web.app/hashes.txt)
* **Base Censitária:** Repositório de Dados Abertos do TSE — Totalização oficial 100% consolidada em **26/10/2026 às 18:30:00 BRT**.

---

## Destaques Metodológicos e Inovações Técnicas

1. **Controle por Linha de Base do 1º Turno no Fechamento das Urnas:**
   * Corrige o viés clássico de variável omitida (*confounding*): demonstra empiricamente que as seções com encerramento posterior às 17h/17h45 já apresentavam votação majoritária de Lula desde o 1º turno (periferias urbanas e regiões metropolitanas com gargalos de transporte e lentidão de biometria).
   * A taxa de crescimento relativo ($\Delta$ intrasseção) no 2º turno nessas urnas acompanha o padrão do respectivo território, refutando hipóteses de anomalia causal decorrente do horário.

2. **Inferência Ecológica Microterritorial (UF × Capital vs. Interior):**
   * Mitiga o viés de agregação espacial (*falácia ecológica*) ao substituir matrizes nacionais uniformes por **85 recortes territoriais independentes** (26 UFs desmembradas em Capital e Interior + DF + Exterior ZZ).
   * **Regularização Bayesiana (*Empirical Bayes Shrinkage*):** Introduz priors informativos derivados do comportamento das urnas de alta densidade de cada candidato, impedindo soluções de canto artificiais ($0,0\%$ e $100,0\%$) e estabilizando estratos com amostras reduzidas.
   * **Fechamento Contábil Estrito:** Cumpre com exatidão matemática as condições de Karush-Kuhn-Tucker (KKT) no suporte físico $[5\%, 95\%]$ com zero erro contábil ($\sum V_k \cdot \beta_{13, k} = \Delta 13$).
   * **Bandas de Credibilidade (IC 95%):** Quantificação da incerteza amostral e paramétrica em cada taxa de transição.

3. **Integridade Cadastral e Mesas Receptoras:**
   * Verificação cadastral longitudinal para assegurar que as seções destacadas no explorador de maiores variações correspondem a mesas receptoras regulares em ambos os turnos, evitando falsas anomalias geradas por fusão ou desmembramento físico de seções pelo TSE.

4. **Inviolabilidade do Sigilo do Voto (RDV):**
   * O Registro Digital do Voto (RDV) grava cada cédula eletrônica com permutação pseudoaleatória e sem carimbo de tempo (*timestamp*). Os modelos trabalham estritamente com agregados de seção e contagens de eventos do log, respeitando o sigilo constitucional do voto individual.

---

## Documentação de Dependências e Ambiente de Execução

O pipeline de dados foi desenvolvido para ser de altíssimo desempenho, reprodutível e com o menor número possível de dependências externas. O solver quadrático de Karush-Kuhn-Tucker (KKT) foi implementado nativamente com operações vetoriais de álgebra linear sobre o NumPy.

### 1. Requisitos do Sistema
* **Linguagem:** Python 3.11+ (homologado na versão `3.11.4 64-bit AMD64`)
* **Gerenciador de Pacotes:** `pip` (versão 23.0+)
* **Ambiente de Deploy Web (Opcional):** Node.js >= 18 com `firebase-tools == 15.28.1`

### 2. Tabela de Dependências Python

| Pacote | Versão Mínima | Versão no Ambiente de Produção | Finalidade / Módulos Utilizados |
| :--- | :---: | :---: | :--- |
| **`numpy`** | `>= 1.24.0` | `1.25.2` | Operações matriciais de projeção $X^T X$, resolução de sistemas lineares regularizados de Tikhonov (`np.linalg.solve`, `np.linalg.pinv`), cálculo da matriz de covariância residual e otimização convexa KKT via bisseção vetorial com suporte físico restrito. |
| **`Pillow`** | `>= 10.0.0` | `10.4.0` | Processamento de imagens e renderização do favicon oficial multirresolução (`favicon.ico` com camadas de `16x16`, `32x32`, `48x48` e `64x64`). |
| **`scipy`** *(opcional)* | `>= 1.11.0` | *N/A (Nativo no NumPy)* | Utilizado opcionalmente para validação cruzada independente via `scipy.optimize.nnls` e cálculo de quantis da distribuição $t$ de Student. O pipeline principal não requer scipy em virtude do solver KKT nativo vetorial. |

### 3. Módulos Nativos da Standard Library Utilizados
Os scripts de ingestão e decodificação utilizam extensivamente bibliotecas embutidas do Python:
* **`zipfile` & `io`:** Leitura e descompressão de arquivos brutos do TSE (`votacao_secao_2026_BR.zip` e `-log.jez`).
* **`csv`:** Ingestão de alta performance com codificação `latin1` e delimitador `;`.
* **`json`:** Serialização dos agregados censitários e matrizes de transição microterritoriais.
* **`hashlib`:** Geração dos hashes de integridade criptográfica SHA-256 para o manifesto [hashes.txt](file:///C:/Projetos/MapaDaUrna/web/hashes.txt).
* **`http.server` & `threading`:** Servidor HTTP local para bateria de testes automatizados de renderização mobile headless.
* **`subprocess`:** Execução automatizada do Chromium/Edge headless para testes de viewport (`320px`, `360px`, `390px`).

### 4. Instalação das Dependências

Para instalar as dependências em um ambiente virtual limpo:

```powershell
# Criação do ambiente virtual (recomendado)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instalação dos pacotes
pip install -r requirements.txt
```

---

## Estrutura do Repositório

```text
MapaDaUrna/
├── data/
│   ├── dashboard_data.json         # Base consolidada em JSON com todas as agregações
│   └── eco_inference_slices.json   # 85 matrizes ecológicas (UF x Capital vs. Interior)
├── src/
│   ├── compute_eco_uf_cap_int.py   # Ingestão das 499k seções e estimador KKT bayesiano
│   ├── apply_constrained_eco.py    # Otimização restrita KKT nacional
│   ├── build_general_t1_t2.py      # Agregação censitária geral 1ºT vs 2ºT
│   ├── run_deep_migration.py       # Extração de faixas de predominância e 3ª via
│   ├── update_top_secoes.py        # Ranking de seções com auditoria cadastral
│   ├── test_mobile_render.py       # Auditoria de renderização mobile headless
│   ├── bu_decoder.py               # Decodificador ASN.1 DER e parser de logs da urna
│   └── crawl_extended_bus.py       # Coletor de Boletins de Urna com rate limiting
├── web/
│   ├── index.html                  # Interface do painel (HTML5, CSS moderno, sem frameworks)
│   ├── data.js                     # Carga dos dados no escopo window.ELECTION_DATA
│   ├── hashes.txt                  # Manifesto público de integridade SHA-256
│   ├── favicon.svg                 # Favicon vetorial da urna eletrônica
│   ├── favicon.ico                 # Favicon binário multirresolução
│   ├── requirements.txt            # Espelho de dependências para download web
│   └── src/                        # Espelho público dos scripts Python servidos na web
├── firebase.json                   # Configuração de rotas e headers do Firebase Hosting
├── .firebaserc                     # Configuração do projeto Firebase (mapadaurna)
├── requirements.txt                # Arquivo canônico de dependências Python
└── README.md                       # Documentação técnica do projeto
```

---

## Como Executar o Projeto Localmente

### 1. Visualizar o Dashboard Interativo
Como o frontend é estático e desacoplado, basta iniciar um servidor local na pasta `web/`:

```powershell
cd C:\Projetos\MapaDaUrna\web
python -m http.server 8080
```
Em seguida, acesse no navegador: `http://localhost:8080`.

### 2. Executar a Decomposição Ecológica Microterritorial
Para reprocessar os 85 recortes a partir dos dados de votação por seção:

```powershell
python C:\Projetos\MapaDaUrna\src\compute_eco_uf_cap_int.py
```

### 3. Rodar a Bateria de Testes de Renderização Mobile
Para verificar que a interface não apresenta cortes ou estouro horizontal em celulares (`320px`, `360px`, `390px`):

```powershell
python C:\Projetos\MapaDaUrna\src\test_mobile_render.py
```

---

## Governança e Manifesto de Hashes (SHA-256)

Para garantir que terceiros possam reproduzir e auditar com precisão os cálculos sem qualquer divergência de versão, o manifesto [hashes.txt](file:///C:/Projetos/MapaDaUrna/web/hashes.txt) lista os hashes SHA-256 de todos os artefatos.

Para validar um arquivo localmente no PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 .\data\dashboard_data.json
Get-FileHash -Algorithm SHA256 .\data\eco_inference_slices.json
```

O manifesto público oficial pode ser inspecionado diretamente em:
**[https://mapadaurna.web.app/hashes.txt](https://mapadaurna.web.app/hashes.txt)**
