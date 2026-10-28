"""
Coletor com Controle de Taxa Adaptativo (Rate Limiter) para as Seções Estendidas (> 17h45)
==========================================================================================

Utiliza a lista exata de seções que fecharam após as 17h45 (horário de Brasília) e baixa
os Boletins de Urna (`-bu.dat`) correspondentes respeitando um limite seguro de requisições
por segundo (`RPS`, padrão 8 req/s) com backoff exponencial caso a CDN da Akamai retorne
`HTTP 429` ou `HTTP 403`.
"""

import csv
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from bu_decoder import extract_bu_info

BASE_URL = "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221"
RPS = float(os.environ.get("RPS", "8.0"))
WORKERS = int(os.environ.get("WORKERS", "16"))


class AdaptiveRateLimiter:
    def __init__(self, rps: float):
        self.rps = rps
        self.lock = threading.Lock()
        self.next_slot = time.monotonic()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            self.next_slot = max(self.next_slot, now) + (1.0 / self.rps)
            delay = self.next_slot - now - (1.0 / self.rps)
        if delay > 0:
            time.sleep(delay)

    def backoff(self):
        with self.lock:
            self.rps = max(2.0, self.rps * 0.7)
            self.next_slot = time.monotonic() + 30.0
        print(f"[RateLimiter] HTTP 429/403 detectado! Reduzindo RPS para {self.rps:.1f} e aguardando 30s...", flush=True)


limiter = AdaptiveRateLimiter(RPS)


def fetch_bytes(url: str) -> bytes:
    for attempt in range(8):
        limiter.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return urllib.request.urlopen(req, timeout=30).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            if e.code in (403, 429):
                limiter.backoff()
            time.sleep(min(60, 2**attempt) + random.random())
        except Exception:
            if attempt >= 2:
                limiter.backoff()
            time.sleep(min(60, 2**attempt) + random.random())
    raise RuntimeError(f"Falha após 8 tentativas: {url}")


def fetch_extended_bu(row: dict) -> dict:
    uf = row["uf"].lower()
    mu = row["cd_mun"]
    z = row["zona"]
    s = row["secao"]
    base_sec = f"{BASE_URL}/dados/{uf}/{mu}/{z}/{s}"
    aux_raw = fetch_bytes(f"{base_sec}/p003221-{uf}-m{mu}-z{z}-s{s}-aux.json")
    aux = json.loads(aux_raw.decode("utf-8"))
    h_obj = aux["hashes"][-1]
    h = h_obj["hash"]
    bu_nm = [a["nm"] for a in h_obj["arq"] if a["tp"] == "bu"][0]
    bu_raw = fetch_bytes(f"{base_sec}/{h}/{bu_nm}")
    info = extract_bu_info(bu_raw)
    return {
        "uf": row["uf"],
        "cd_mun": mu,
        "municipio": row["municipio"],
        "zona": z,
        "secao": s,
        "encerramento_brt": row["encerramento_brt"],
        "votos_apos_17h_log": int(row["votos_apos_17h"]),
        "votos_apos_17h20_log": int(row["votos_apos_17h20"]),
        "aux_hr": h_obj.get("hr"),
        **info,
    }
