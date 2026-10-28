"""
Decodificador ASN.1 DER do Boletim de Urna (-bu.dat) e Parser Recursivo de Logs (-log.jez)
===========================================================================================

Este módulo resolve duas questões técnicas centrais da auditoria:
1. Decodifica diretamente os arquivos binários `-bu.dat` (padrão ASN.1 DER da Justiça Eleitoral)
   para extrair:
   - `dataHoraAbertura` e `dataHoraEncerramento` do relógio interno da urna;
   - `dataHoraEmissao` do Boletim de Urna;
   - Eleitores aptos, comparecimento e total de votos nominais (13 vs 22), brancos e nulos.
2. Corrige o bug de Urnas de Contingência presente em `apolinario/urnas-tardias`:
   - Quando uma urna é substituída por outra de contingência, o arquivo `-log.jez` contém
     tanto o `logd.dat` da urna substituta quanto um arquivo `.jez` aninhado (ex: `*-01.jez`
     ou `*01ME.jez`) com o log da urna original.
   - A função `parse_log_jez_recursive()` descompacta recursivamente quaisquer arquivos `.jez`
     internos antes de decodificar o texto `latin1`, preservando o horário real de abertura
     matinal (08:00) e todos os votos computados na primeira urna.
"""

import io
import zipfile
import urllib.request


def decode_der_nodes(b: bytes, offset: int = 0):
    """Decodifica recursivamente uma estrutura binária ASN.1 DER em árvore de tuplas (tag, valor)."""
    nodes = []
    while offset < len(b):
        tag = b[offset]
        offset += 1
        length = b[offset]
        offset += 1
        if length & 0x80:
            nbytes = length & 0x7F
            length = int.from_bytes(b[offset : offset + nbytes], "big")
            offset += nbytes
        val = b[offset : offset + length]
        offset += length
        if (tag & 0x20) or (tag == 0x04 and len(val) > 10 and val[0] == 0x30):
            nodes.append((tag, decode_der_nodes(val, 0)))
        else:
            nodes.append((tag, val))
    return nodes


def extract_bu_info(b: bytes, cod_eleicao: int = 6258) -> dict:
    """
    Extrai os metadados de horário e os votos para Presidente (cargo 1) da eleição 6258
    (2º Turno Presidencial 2026) a partir dos bytes brutos de um arquivo `-bu.dat`.
    """
    tree = decode_der_nodes(b)
    info = {
        "abertura": None,
        "encerramento": None,
        "emissao": None,
        "aptos": 0,
        "comp": 0,
        "v13": 0,
        "v22": 0,
        "brancos": 0,
        "nulos": 0,
    }

    def walk(nodes):
        for tag, val in nodes:
            if isinstance(val, list):
                if tag == 0xA0 and len(val) == 2 and val[0][0] == 0x1B and val[1][0] == 0x1B:
                    info["abertura"] = val[0][1].decode("ascii", errors="ignore")
                    info["encerramento"] = val[1][1].decode("ascii", errors="ignore")
                if (
                    tag == 0x30
                    and len(val) >= 5
                    and val[0][0] == 0x02
                    and int.from_bytes(val[0][1], "big") == cod_eleicao
                ):
                    info["aptos"] = int.from_bytes(val[1][1], "big")
                    for _, sub_v in val[4][1]:
                        if (
                            isinstance(sub_v, list)
                            and len(sub_v) >= 3
                            and sub_v[0][0] == 0x0A
                            and int.from_bytes(sub_v[0][1], "big") == 1
                        ):
                            info["comp"] = int.from_bytes(sub_v[1][1], "big")

                            def walk_votes(vnodes):
                                for vt, vv in vnodes:
                                    if isinstance(vv, list):
                                        if vt == 0x30 and len(vv) >= 3 and vv[0][0] == 0x81 and vv[1][0] == 0x82:
                                            tp = int.from_bytes(vv[0][1], "big")
                                            qtd = int.from_bytes(vv[1][1], "big")
                                            if tp == 1 and vv[2][0] == 0xA3:
                                                cand = int.from_bytes(vv[2][1][0][1], "big")
                                                if cand == 13:
                                                    info["v13"] += qtd
                                                elif cand == 22:
                                                    info["v22"] += qtd
                                            elif tp == 2:
                                                info["brancos"] += qtd
                                            elif tp == 3:
                                                info["nulos"] += qtd
                                        walk_votes(vv)

                            walk_votes(sub_v)
                walk(val)
            else:
                if tag == 0x1B and info["emissao"] is None and len(val) == 15 and val.startswith(b"2026"):
                    info["emissao"] = val.decode("ascii", errors="ignore")

    walk(tree)
    return info


def parse_log_jez_recursive(raw_zip_bytes: bytes, target_date: str = "25/10/2026") -> dict:
    """
    Lê um arquivo `-log.jez` descompactando recursivamente eventuais arquivos `.jez` aninhados
    de urnas substituídas por contingência.
    """
    result = {
        "arquivos": [],
        "pronta": [],
        "encerramento": [],
        "votos_timestamps": [],
        "votos_total": 0,
        "contingencia": False,
    }

    def process_zip(z_bytes: bytes):
        with zipfile.ZipFile(io.BytesIO(z_bytes)) as zf:
            for nm in zf.namelist():
                result["arquivos"].append(nm)
                content = zf.read(nm)
                if nm.lower().endswith(".jez") or content[:2] == b"PK":
                    result["contingencia"] = True
                    process_zip(content)
                else:
                    for line in content.decode("latin1", errors="replace").splitlines():
                        parts = line.split("\t")
                        if len(parts) < 5 or not parts[0].startswith(target_date):
                            continue
                        t, ev = parts[0][11:], parts[4]
                        if ev == "O voto do eleitor foi computado":
                            result["votos_total"] += 1
                            result["votos_timestamps"].append(t)
                        elif ev == "Urna pronta para receber votos":
                            result["pronta"].append(t)
                        elif ev == "Procedimento de encerramento confirmado":
                            result["encerramento"].append(t)

    process_zip(raw_zip_bytes)
    result["pronta"].sort()
    result["encerramento"].sort()
    result["votos_timestamps"].sort()
    return result
