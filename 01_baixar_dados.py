"""
SCRIPT 01 - BAIXAR DADOS DA CVM
"""

from __future__ import annotations

import calendar
import os
import re
import zipfile
from datetime import datetime

import requests


BASE_CDA = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS"
URL_CAD = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
URL_REGISTRO = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
MESES_JANELA_PADRAO = 6
MESES_ATRAS_INICIO_PADRAO = 0
MESES_ATRAS_MAX_PADRAO = 12


def subtrair_meses(data: datetime, meses: int) -> datetime:
    ano = data.year
    mes = data.month - meses
    while mes <= 0:
        mes += 12
        ano -= 1
    dia = min(data.day, calendar.monthrange(ano, mes)[1])
    return data.replace(year=ano, month=mes, day=dia)


def baixar_arquivo(url: str, destino: str, timeout: int = 120) -> bool:
    try:
        with requests.get(url, timeout=timeout, stream=True) as resp:
            if resp.status_code != 200:
                print(f"Nao encontrado ({resp.status_code})")
                return False

            with open(destino, "wb") as arquivo:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        arquivo.write(chunk)
        return True
    except requests.RequestException as erro:
        print(f"Erro de rede: {erro}")
        return False


def listar_meses_disponiveis_cvm(timeout: int = 30) -> list[str]:
    try:
        resp = requests.get(f"{BASE_CDA}/", timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as erro:
        print(f"Falha ao listar diretorio da CVM: {erro}")
        return []

    meses = sorted(set(re.findall(r"cda_fi_(\d{6})\.zip", resp.text)), reverse=True)
    return meses


def baixar_carteiras(
    meses_janela: int = MESES_JANELA_PADRAO,
    meses_atras_inicio: int = MESES_ATRAS_INICIO_PADRAO,
    meses_atras_max: int = MESES_ATRAS_MAX_PADRAO,
) -> list[str]:
    os.makedirs("dados_brutos", exist_ok=True)

    meses_baixados: list[str] = []
    meses_disponiveis_cvm = listar_meses_disponiveis_cvm()
    if meses_disponiveis_cvm:
        print(
            "Ultimo mes de carteira disponivel na CVM: "
            f"{meses_disponiveis_cvm[0][:4]}/{meses_disponiveis_cvm[0][4:]}"
        )
        meses_tentativa = meses_disponiveis_cvm
    else:
        hoje = datetime.now()
        meses_tentativa = []
        for meses_atras in range(meses_atras_inicio, meses_atras_max + 1):
            data_ref = subtrair_meses(hoje, meses_atras)
            meses_tentativa.append(data_ref.strftime("%Y%m"))

    for ano_mes in meses_tentativa:
        if len(meses_baixados) >= meses_janela:
            break

        nome_zip = f"cda_fi_{ano_mes}.zip"
        url = f"{BASE_CDA}/{nome_zip}"
        caminho_zip = os.path.join("dados_brutos", nome_zip)

        if os.path.exists(caminho_zip):
            print(f"Arquivo ja existe, pulando download: {nome_zip}")
            try:
                with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
                    zip_ref.extractall("dados_brutos")
                meses_baixados.append(ano_mes)
                continue
            except zipfile.BadZipFile:
                print(f"ZIP local invalido, baixando novamente: {nome_zip}")

        print(f"Tentando baixar {nome_zip} ...")
        if not baixar_arquivo(url, caminho_zip):
            continue

        try:
            with zipfile.ZipFile(caminho_zip, "r") as zip_ref:
                zip_ref.extractall("dados_brutos")
                print(f"Baixado e extraido: {nome_zip} ({len(zip_ref.namelist())} arquivos)")
            meses_baixados.append(ano_mes)
        except zipfile.BadZipFile:
            print(f"Arquivo invalido: {nome_zip}")

    if not meses_baixados:
        print("Nao foi possivel baixar nenhum ZIP de carteira.")
        return []

    print("Baixando cadastro de fundos (cad_fi.csv) ...")
    cad_destino = os.path.join("dados_brutos", "cad_fi.csv")
    if baixar_arquivo(URL_CAD, cad_destino, timeout=180):
        print("Cadastro de fundos baixado com sucesso.")
    else:
        print("Falha ao baixar cadastro de fundos.")

    print("Baixando registro_fundo_classe.zip ...")
    registro_zip = os.path.join("dados_brutos", "registro_fundo_classe.zip")
    if baixar_arquivo(URL_REGISTRO, registro_zip, timeout=180):
        try:
            with zipfile.ZipFile(registro_zip, "r") as zip_ref:
                zip_ref.extractall("dados_brutos")
                print(
                    "Registro de classes/fundos extraido "
                    f"({len(zip_ref.namelist())} arquivos)."
                )
        except zipfile.BadZipFile:
            print("Falha ao extrair registro_fundo_classe.zip.")
    else:
        print("Falha ao baixar registro_fundo_classe.zip.")

    meses_baixados = sorted(set(meses_baixados), reverse=True)
    mes_alvo = meses_baixados[0]
    print(
        "Meses de carteira disponiveis para processamento: "
        + ", ".join(f"{m[:4]}/{m[4:]}" for m in meses_baixados)
    )
    print(f"Mes-alvo sugerido: {mes_alvo[:4]}/{mes_alvo[4:]}")
    return meses_baixados


if __name__ == "__main__":
    meses = baixar_carteiras()
    if meses:
        print("Download concluido.")
