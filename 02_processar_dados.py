"""
SCRIPT 02 - PROCESSAR DADOS
"""

from __future__ import annotations

import glob
import os
from datetime import datetime
from typing import Iterable

import pandas as pd


MESES_JANELA_PADRAO = 6
SOMENTE_RENDA_FIXA_PADRAO = True
BLOCOS_RENDA_FIXA = {1, 4, 5, 6}
BLOCOS_TODOS = {1, 2, 3, 4, 5, 6, 7, 8}
ARQUIVO_EMISSORES_PADRAO = "base_emissores/base_emissores.xlsx"


def encontrar_coluna(df: pd.DataFrame, opcoes: Iterable[str]) -> str | None:
    for col in opcoes:
        if col in df.columns:
            return col
    return None


def normalizar_cnpj(serie: pd.Series) -> pd.Series:
    return serie.astype(str).str.replace(r"\D", "", regex=True).str.zfill(14)


def converter_numero(serie: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(serie):
        return pd.to_numeric(serie, errors="coerce")

    texto = serie.astype(str).str.strip()
    texto = texto.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA})

    numero = pd.to_numeric(texto, errors="coerce")
    faltantes = numero.isna() & texto.notna()
    if faltantes.any():
        texto_br = (
            texto[faltantes]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        numero.loc[faltantes] = pd.to_numeric(texto_br, errors="coerce")
    return numero


def coalescer_colunas(df: pd.DataFrame, colunas: list[str]) -> pd.Series:
    if not colunas:
        return pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    resultado = df[colunas[0]].copy()
    for col in colunas[1:]:
        resultado = resultado.where(resultado.notna(), df[col])
    return resultado


def filtrar_renda_fixa_bloco_4(df: pd.DataFrame) -> pd.DataFrame:
    if "BLOCO" not in df.columns:
        return df

    mask_bloco_4 = df["BLOCO"] == 4
    if not mask_bloco_4.any():
        return df

    colunas_texto = [c for c in ["TP_APLIC", "TP_ATIVO", "DS_ATIVO", "CD_ATIVO"] if c in df.columns]
    if not colunas_texto:
        # Sem colunas para identificar tipo do ativo: remove bloco 4 por seguranca
        return df[~mask_bloco_4].copy()

    texto_ref = pd.Series("", index=df.index, dtype="string")
    for col in colunas_texto:
        texto_ref = texto_ref + " " + df[col].astype("string").fillna("")

    # Inclui apenas credito/renda fixa codificada no bloco 4
    regex_rf = r"DEB|CRI|CRA|CDB|LCI|LCA|LETRA FINANCEIRA|NOTA COMERCIAL|CREDITO"
    mask_rf_bloco_4 = texto_ref.str.contains(regex_rf, case=False, na=False)

    return df[(~mask_bloco_4) | (mask_bloco_4 & mask_rf_bloco_4)].copy()


def parse_nome_bloco(nome_arquivo: str) -> tuple[int, str] | None:
    # Exemplo: cda_fi_BLC_1_202512.csv
    base = nome_arquivo.replace(".csv", "")
    partes = base.split("_")
    if len(partes) < 5:
        return None
    try:
        bloco = int(partes[3])
    except ValueError:
        return None
    ano_mes = partes[4]
    if len(ano_mes) != 6 or not ano_mes.isdigit():
        return None
    return bloco, ano_mes


def formatar_ano_mes(ano_mes: str) -> str:
    if not isinstance(ano_mes, str):
        return ""
    if len(ano_mes) != 6 or not ano_mes.isdigit():
        return ""
    return f"{ano_mes[4:]}/{ano_mes[:4]}"


def diferenca_meses(ano_mes_ref: str, ano_mes_base: str) -> int:
    a1 = int(ano_mes_ref[:4])
    m1 = int(ano_mes_ref[4:])
    a2 = int(ano_mes_base[:4])
    m2 = int(ano_mes_base[4:])
    return (a1 - a2) * 12 + (m1 - m2)


def ler_csv_bloco(caminho: str) -> pd.DataFrame:
    try:
        return pd.read_csv(
            caminho,
            sep=";",
            encoding="latin1",
            decimal=",",
            low_memory=False,
        )
    except Exception as erro:  # noqa: BLE001
        print(f"Leitura padrao falhou em {os.path.basename(caminho)}: {erro}")
        print("Tentando leitura alternativa ignorando linhas com problema...")
        return pd.read_csv(
            caminho,
            sep=";",
            encoding="latin1",
            decimal=",",
            engine="python",
            on_bad_lines="skip",
        )


def carregar_registro_classe() -> pd.DataFrame | None:
    caminho = "dados_brutos/registro_classe.csv"
    if not os.path.exists(caminho):
        return None

    reg = pd.read_csv(caminho, sep=";", encoding="latin1", low_memory=False)
    colunas = [
        "ID_Registro_Fundo",
        "CNPJ_Classe",
        "Denominacao_Social",
        "Situacao",
        "Classificacao_Anbima",
        "Patrimonio_Liquido",
        "Data_Patrimonio_Liquido",
    ]
    reg = reg[[c for c in colunas if c in reg.columns]].copy()
    reg = reg.rename(
        columns={
            "ID_Registro_Fundo": "ID_REGISTRO_FUNDO",
            "CNPJ_Classe": "CNPJ_CLASSE_REG",
            "Denominacao_Social": "DENOM_SOCIAL_CLASSE_REG",
            "Situacao": "SITUACAO_CLASSE_REG",
            "Classificacao_Anbima": "CLASSE_ANBIMA_REG",
            "Patrimonio_Liquido": "PATRIMONIO_LIQUIDO_CLASSE_REG",
            "Data_Patrimonio_Liquido": "DATA_PATRIMONIO_LIQ_CLASSE_REG",
        }
    )
    reg["_CNPJ_KEY"] = normalizar_cnpj(reg["CNPJ_CLASSE_REG"])
    reg = reg.drop_duplicates(subset=["_CNPJ_KEY"], keep="first")
    return reg


def carregar_registro_fundo() -> pd.DataFrame | None:
    caminho = "dados_brutos/registro_fundo.csv"
    if not os.path.exists(caminho):
        return None

    reg = pd.read_csv(caminho, sep=";", encoding="latin1", low_memory=False)
    colunas = [
        "ID_Registro_Fundo",
        "CNPJ_Fundo",
        "Denominacao_Social",
        "Situacao",
        "Tipo_Fundo",
        "Patrimonio_Liquido",
        "Data_Patrimonio_Liquido",
        "Administrador",
        "Gestor",
    ]
    reg = reg[[c for c in colunas if c in reg.columns]].copy()
    reg = reg.rename(
        columns={
            "ID_Registro_Fundo": "ID_REGISTRO_FUNDO",
            "CNPJ_Fundo": "CNPJ_FUNDO_REG",
            "Denominacao_Social": "DENOM_SOCIAL_FUNDO_REG",
            "Situacao": "SITUACAO_FUNDO_REG",
            "Tipo_Fundo": "TIPO_FUNDO_REG",
            "Patrimonio_Liquido": "PATRIMONIO_LIQUIDO_FUNDO_REG",
            "Data_Patrimonio_Liquido": "DATA_PATRIMONIO_LIQ_FUNDO_REG",
            "Administrador": "ADMIN_REG",
            "Gestor": "GESTOR_REG",
        }
    )
    reg = reg.drop_duplicates(subset=["ID_REGISTRO_FUNDO"], keep="first")
    return reg


def carregar_cad_fi() -> pd.DataFrame | None:
    caminho = "dados_brutos/cad_fi.csv"
    if not os.path.exists(caminho):
        return None

    cad = pd.read_csv(caminho, sep=";", encoding="latin1", low_memory=False)
    colunas = [
        "CNPJ_FUNDO",
        "DENOM_SOCIAL",
        "SIT",
        "VL_PATRIM_LIQ",
        "DT_PATRIM_LIQ",
        "CLASSE_ANBIMA",
        "GESTOR",
        "ADMIN",
    ]
    cad = cad[[c for c in colunas if c in cad.columns]].copy()
    cad = cad.rename(
        columns={
            "CNPJ_FUNDO": "CNPJ_FUNDO_CAD",
            "DENOM_SOCIAL": "DENOM_SOCIAL_CAD",
            "SIT": "SIT_CAD",
            "VL_PATRIM_LIQ": "VL_PATRIM_LIQ_CAD",
            "DT_PATRIM_LIQ": "DT_PATRIM_LIQ_CAD",
            "CLASSE_ANBIMA": "CLASSE_ANBIMA_CAD",
            "GESTOR": "GESTOR_CAD",
            "ADMIN": "ADMIN_CAD",
        }
    )
    cad["_CNPJ_KEY"] = normalizar_cnpj(cad["CNPJ_FUNDO_CAD"])
    cad = cad.drop_duplicates(subset=["_CNPJ_KEY"], keep="first")
    return cad


def carregar_base_emissores(caminho: str = ARQUIVO_EMISSORES_PADRAO) -> pd.DataFrame | None:
    if not os.path.exists(caminho):
        return None

    base = pd.read_excel(caminho)
    if base.empty:
        return None

    colunas = list(base.columns)
    colunas_lower = {str(c).strip().lower(): c for c in colunas}

    col_ticker = colunas_lower.get("ticker")
    col_emissor = colunas_lower.get("emissor")

    if col_ticker is None or col_emissor is None:
        if len(colunas) < 2:
            return None
        col_ticker = colunas[0]
        col_emissor = colunas[1]

    saida = base[[col_ticker, col_emissor]].copy()
    saida.columns = ["TICKER_MAP", "EMISSOR_MAP"]

    saida["TICKER_MAP"] = saida["TICKER_MAP"].astype("string").str.strip().str.upper()
    saida["EMISSOR_MAP"] = saida["EMISSOR_MAP"].astype("string").str.strip()
    saida = saida[saida["TICKER_MAP"].notna() & (saida["TICKER_MAP"] != "")]
    saida = saida.drop_duplicates(subset=["TICKER_MAP"], keep="first")
    return saida


def carregar_pl_cda(meses: list[str]) -> pd.DataFrame | None:
    """Carrega PL dos arquivos cda_fi_PL (mesmo periodo das carteiras)."""
    import glob as glob_mod

    arquivos: list[str] = []
    for mes in meses:
        arquivos.extend(glob_mod.glob(f"dados_brutos/cda_fi_PL_{mes}.csv"))

    if not arquivos:
        return None

    partes: list[pd.DataFrame] = []
    for caminho in arquivos:
        try:
            df = pd.read_csv(
                caminho,
                sep=";",
                encoding="latin1",
                usecols=["CNPJ_FUNDO_CLASSE", "VL_PATRIM_LIQ"],
                low_memory=False,
            )
            partes.append(df)
        except Exception as erro:  # noqa: BLE001
            print(f"Erro ao ler PL de {os.path.basename(caminho)}: {erro}")

    if not partes:
        return None

    pl = pd.concat(partes, ignore_index=True)
    pl["_CNPJ_KEY"] = normalizar_cnpj(pl["CNPJ_FUNDO_CLASSE"])
    pl["VL_PATRIM_LIQ_CDA"] = converter_numero(pl["VL_PATRIM_LIQ"])
    pl = pl.drop_duplicates(subset=["_CNPJ_KEY"], keep="first")
    return pl[["_CNPJ_KEY", "VL_PATRIM_LIQ_CDA"]]


def processar_dados(
    meses_janela: int = MESES_JANELA_PADRAO,
    somente_renda_fixa: bool = SOMENTE_RENDA_FIXA_PADRAO,
) -> None:
    os.makedirs("dados_processados", exist_ok=True)

    arquivos_brutos = glob.glob("dados_brutos/cda_fi_BLC_*_*.csv")
    if not arquivos_brutos:
        print("Nenhum arquivo de carteira encontrado. Execute 01_baixar_dados.py primeiro.")
        return

    meta_arquivos: list[dict[str, object]] = []
    for caminho in arquivos_brutos:
        nome = os.path.basename(caminho)
        parsed = parse_nome_bloco(nome)
        if not parsed:
            continue
        bloco, ano_mes = parsed
        meta_arquivos.append(
            {
                "caminho": caminho,
                "nome": nome,
                "bloco": bloco,
                "ano_mes": ano_mes,
            }
        )

    if not meta_arquivos:
        print("Nao foi possivel identificar arquivos de blocos validos.")
        return

    meses_disponiveis = sorted({m["ano_mes"] for m in meta_arquivos}, reverse=True)
    mes_alvo = meses_disponiveis[0]
    meses_considerados = meses_disponiveis[:meses_janela]
    blocos_considerados = BLOCOS_RENDA_FIXA if somente_renda_fixa else BLOCOS_TODOS

    print(f"Mes-alvo: {formatar_ano_mes(mes_alvo)}")
    print("Meses considerados: " + ", ".join(formatar_ano_mes(m) for m in meses_considerados))
    if somente_renda_fixa:
        print(f"Modo renda fixa ativo (blocos: {sorted(blocos_considerados)})")
    else:
        print(f"Modo completo ativo (blocos: {sorted(blocos_considerados)})")

    lista_dfs: list[pd.DataFrame] = []
    for meta in sorted(meta_arquivos, key=lambda x: (x["ano_mes"], x["bloco"]), reverse=True):
        ano_mes = str(meta["ano_mes"])
        bloco = int(meta["bloco"])
        if ano_mes not in meses_considerados or bloco not in blocos_considerados:
            continue

        nome = str(meta["nome"])
        caminho = str(meta["caminho"])
        print(f"Lendo {nome} ...")
        try:
            df_bloco = ler_csv_bloco(caminho)
            df_bloco["BLOCO"] = bloco
            df_bloco["ANO_MES_ARQUIVO"] = ano_mes
            lista_dfs.append(df_bloco)
            print(f"  -> {len(df_bloco):,} linhas")
        except Exception as erro:  # noqa: BLE001
            print(f"Erro ao ler {nome}: {erro}")

    if not lista_dfs:
        print("Nenhum bloco valido foi carregado.")
        return

    carteiras = pd.concat(lista_dfs, ignore_index=True)
    print(f"Total de registros brutos: {len(carteiras):,}")

    if somente_renda_fixa:
        antes_filtro_bloco4 = len(carteiras)
        carteiras = filtrar_renda_fixa_bloco_4(carteiras)
        print(
            "Apos filtro de renda fixa no bloco 4: "
            f"{antes_filtro_bloco4:,} -> {len(carteiras):,} registros"
        )

    cnpj_carteira = encontrar_coluna(carteiras, ["CNPJ_FUNDO_CLASSE", "CNPJ_FUNDO"])
    if not cnpj_carteira:
        print("Coluna de CNPJ nao encontrada nas carteiras.")
        return

    carteiras["_CNPJ_KEY"] = normalizar_cnpj(carteiras[cnpj_carteira])
    carteiras["_FUNDO_KEY"] = carteiras["_CNPJ_KEY"]

    # Escolha de data-base por fundo:
    # - usa mes-alvo se existir
    # - senao usa ultima carteira disponivel daquele fundo na janela
    fundos_base = carteiras[["_FUNDO_KEY", "ANO_MES_ARQUIVO"]].dropna()
    ultima_por_fundo = fundos_base.groupby("_FUNDO_KEY")["ANO_MES_ARQUIVO"].max().rename("MES_ULTIMA_DISP")
    fundos_no_mes_alvo = set(
        fundos_base.loc[fundos_base["ANO_MES_ARQUIVO"] == mes_alvo, "_FUNDO_KEY"].tolist()
    )

    mapa_fundo = ultima_por_fundo.to_frame()
    mapa_fundo["TEM_MES_ALVO"] = mapa_fundo.index.isin(fundos_no_mes_alvo)
    mapa_fundo["MES_SELECIONADO"] = mapa_fundo["MES_ULTIMA_DISP"]
    mapa_fundo.loc[mapa_fundo["TEM_MES_ALVO"], "MES_SELECIONADO"] = mes_alvo
    mapa_fundo = mapa_fundo.reset_index()

    carteiras = carteiras.merge(mapa_fundo, on="_FUNDO_KEY", how="left")
    carteiras = carteiras[carteiras["ANO_MES_ARQUIVO"] == carteiras["MES_SELECIONADO"]].copy()

    carteiras["MES_ALVO"] = mes_alvo
    carteiras["USOU_FALLBACK"] = ~carteiras["TEM_MES_ALVO"].fillna(False)
    carteiras["DEFASAGEM_MESES"] = carteiras["MES_SELECIONADO"].astype(str).map(
        lambda x: diferenca_meses(mes_alvo, x) if len(x) == 6 and x.isdigit() else pd.NA
    )
    carteiras["MES_ALVO_FMT"] = carteiras["MES_ALVO"].astype(str).map(formatar_ano_mes)
    carteiras["MES_SELECIONADO_FMT"] = carteiras["MES_SELECIONADO"].astype(str).map(formatar_ano_mes)

    if "DT_COMPTC" in carteiras.columns:
        datas_ref = pd.to_datetime(carteiras["DT_COMPTC"], errors="coerce")
    else:
        datas_ref = pd.to_datetime(
            carteiras["MES_SELECIONADO"].astype(str) + "01",
            format="%Y%m%d",
            errors="coerce",
        )
    carteiras["DATA_BASE_EFETIVA"] = datas_ref.dt.strftime("%d/%m/%Y")
    carteiras["DISCLAIMER"] = ""
    mascara_fallback = carteiras["USOU_FALLBACK"] == True  # noqa: E712
    carteiras.loc[mascara_fallback, "DISCLAIMER"] = (
        "Sem carteira no mes-alvo "
        + carteiras.loc[mascara_fallback, "MES_ALVO_FMT"]
        + ". Usada carteira de "
        + carteiras.loc[mascara_fallback, "MES_SELECIONADO_FMT"]
        + "."
    )

    print(
        "Apos consolidacao por fundo: "
        f"{len(carteiras):,} registros "
        f"({carteiras['_FUNDO_KEY'].nunique():,} fundos)"
    )

    reg_classe = carregar_registro_classe()
    if reg_classe is not None:
        print("Mesclando com registro_classe.csv ...")
        carteiras = carteiras.merge(reg_classe, on="_CNPJ_KEY", how="left")
    else:
        print("registro_classe.csv nao encontrado.")

    reg_fundo = carregar_registro_fundo()
    if reg_fundo is not None and "ID_REGISTRO_FUNDO" in carteiras.columns:
        print("Mesclando com registro_fundo.csv ...")
        carteiras = carteiras.merge(reg_fundo, on="ID_REGISTRO_FUNDO", how="left")
    else:
        print("registro_fundo.csv nao encontrado (ou sem chave para merge).")

    cad = carregar_cad_fi()
    if cad is not None:
        print("Mesclando com cad_fi.csv (fallback) ...")
        carteiras = carteiras.merge(cad, on="_CNPJ_KEY", how="left")
    else:
        print("cad_fi.csv nao encontrado.")

    pl_cda = carregar_pl_cda(meses_considerados)
    if pl_cda is not None:
        print("Mesclando PL do CDA (cda_fie) ...")
        carteiras = carteiras.merge(pl_cda, on="_CNPJ_KEY", how="left")
    else:
        print("Arquivos cda_fie nao encontrados para PL.")

    base_emissores = carregar_base_emissores()
    if base_emissores is not None and "CD_ATIVO" in carteiras.columns:
        print("Mesclando com base de emissores (ticker -> emissor) ...")
        carteiras["_TICKER_KEY"] = carteiras["CD_ATIVO"].astype("string").str.strip().str.upper()
        carteiras = carteiras.merge(
            base_emissores,
            left_on="_TICKER_KEY",
            right_on="TICKER_MAP",
            how="left",
        )
        print(
            "Mapeamentos de emissor encontrados: "
            f"{carteiras['EMISSOR_MAP'].notna().sum():,}"
        )
    else:
        print("Base de emissores nao encontrada ou sem CD_ATIVO para merge.")

    colunas_emissor = [c for c in ["EMISSOR", "EMISSOR_MAP"] if c in carteiras.columns]
    if colunas_emissor:
        carteiras["EMISSOR_BASE"] = coalescer_colunas(carteiras, colunas_emissor)

    col_valor = encontrar_coluna(
        carteiras,
        [
            "VL_MERC_POS_FINAL",
            "VL_MERCADO_POS_FINAL",
            "VL_MERC_POSICAO_FINAL",
        ],
    )
    if not col_valor:
        print("Coluna de valor de mercado nao encontrada.")
        return
    carteiras[col_valor] = converter_numero(carteiras[col_valor])

    col_pl_unificada = "VL_PATRIMONIO_BASE"
    if "VL_PATRIM_LIQ_CDA" in carteiras.columns:
        carteiras[col_pl_unificada] = pd.to_numeric(
            carteiras["VL_PATRIM_LIQ_CDA"], errors="coerce"
        )
        print("PL sourced from CDA files (cda_fie).")
    else:
        colunas_pl = [
            c
            for c in [
                "PATRIMONIO_LIQUIDO_CLASSE_REG",
                "VL_PATRIM_LIQ",
                "PATRIMONIO_LIQUIDO_FUNDO_REG",
                "VL_PATRIM_LIQ_CAD",
                "PATRIMONIO_LIQUIDO",
            ]
            if c in carteiras.columns
        ]
        for c in colunas_pl:
            carteiras[c] = converter_numero(carteiras[c])
        if colunas_pl:
            carteiras[col_pl_unificada] = coalescer_colunas(carteiras, colunas_pl)
        else:
            carteiras[col_pl_unificada] = pd.NA
        print("AVISO: PL do CDA nao disponivel, usando fallback de multiplas fontes.")

    carteiras["PCT_PL"] = (
        carteiras[col_valor] / pd.to_numeric(carteiras[col_pl_unificada], errors="coerce") * 100
    ).round(4)
    print("Coluna PCT_PL calculada.")

    # Situcao consolidada para filtro
    colunas_situacao = [
        c
        for c in [
            "SITUACAO_CLASSE_REG",
            "SITUACAO_FUNDO_REG",
            "SIT_CAD",
            "SIT",
            "SITUACAO",
        ]
        if c in carteiras.columns
    ]
    if colunas_situacao:
        carteiras["SITUACAO_BASE"] = coalescer_colunas(carteiras, colunas_situacao)
    else:
        carteiras["SITUACAO_BASE"] = pd.NA

    print("Aplicando filtros ...")
    n_antes = len(carteiras)
    carteiras = carteiras[
        carteiras["SITUACAO_BASE"].astype(str).str.contains("FUNCIONAMENTO NORMAL", case=False, na=False)
    ]
    print(f"Apos filtro de situacao: {len(carteiras):,} registros")

    carteiras = carteiras[pd.to_numeric(carteiras[col_pl_unificada], errors="coerce") >= 1_000_000]
    print(f"Apos filtro PL >= 1.000.000: {len(carteiras):,} registros")

    carteiras = carteiras[carteiras[col_valor].notna() & (carteiras[col_valor] != 0)]
    print(f"Apos filtro valor != 0: {len(carteiras):,} registros")

    print(f"Reducao total: {n_antes:,} -> {len(carteiras):,}")

    if "DT_COMPTC" in carteiras.columns:
        datas = pd.to_datetime(carteiras["DT_COMPTC"], errors="coerce")
        carteiras["DATA_REF"] = datas
    else:
        carteiras["DATA_REF"] = pd.to_datetime(
            carteiras["MES_SELECIONADO"].astype(str) + "01",
            format="%Y%m%d",
            errors="coerce",
        )
    carteiras["MES_REF"] = carteiras["MES_SELECIONADO_FMT"]

    fundos_fallback = carteiras[carteiras["USOU_FALLBACK"] == True].copy()  # noqa: E712
    nome_col_fundo = encontrar_coluna(
        carteiras,
        [
            "DENOM_SOCIAL",
            "NM_FUNDO_CLASSE",
            "DENOM_SOCIAL_CLASSE_REG",
            "DENOM_SOCIAL_FUNDO_REG",
            "DENOM_SOCIAL_CAD",
        ],
    )
    colunas_fallback = ["_FUNDO_KEY", cnpj_carteira, "MES_ALVO_FMT", "MES_SELECIONADO_FMT", "DEFASAGEM_MESES", "DISCLAIMER"]
    if nome_col_fundo:
        colunas_fallback.insert(2, nome_col_fundo)
    colunas_fallback = [c for c in colunas_fallback if c in fundos_fallback.columns]
    if not fundos_fallback.empty:
        fundos_fallback[colunas_fallback].drop_duplicates().to_csv(
            "dados_processados/fundos_sem_mes_alvo.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig",
        )
        print("Arquivo salvo: dados_processados/fundos_sem_mes_alvo.csv")

    # Evita erro do parquet com mistura de tipos em colunas object
    colunas_objeto = carteiras.select_dtypes(include=["object"]).columns
    for col in colunas_objeto:
        carteiras[col] = carteiras[col].astype("string")

    out_parquet = "dados_processados/carteiras_consolidadas.parquet"
    carteiras.to_parquet(out_parquet, index=False)
    print(f"Arquivo salvo: {out_parquet}")

    try:
        if len(carteiras) > 500_000:
            out_excel = "dados_processados/carteiras_amostra.xlsx"
            carteiras.head(500_000).to_excel(out_excel, index=False)
            print(f"Arquivo Excel salvo (amostra): {out_excel}")
        else:
            out_excel = "dados_processados/carteiras_consolidadas.xlsx"
            carteiras.to_excel(out_excel, index=False)
            print(f"Arquivo Excel salvo: {out_excel}")
    except Exception as erro:  # noqa: BLE001
        print(f"Falha ao salvar Excel: {erro}")

    col_ativo = encontrar_coluna(carteiras, ["DS_ATIVO", "NM_FUNDO_COTA", "CD_ATIVO"])
    print("=" * 48)
    print("ESTATISTICAS FINAIS")
    print("=" * 48)
    print(f"Fundos unicos: {carteiras['_FUNDO_KEY'].nunique():,}")
    if col_ativo:
        print(f"Ativos unicos: {carteiras[col_ativo].nunique():,}")
    print(f"Total de posicoes: {len(carteiras):,}")
    print(f"Mes-alvo: {formatar_ano_mes(mes_alvo)}")
    qtd_fundos_fallback = carteiras.loc[carteiras["USOU_FALLBACK"] == True, "_FUNDO_KEY"].nunique()  # noqa: E712
    print(f"Fundos usando fallback: {qtd_fundos_fallback:,}")


if __name__ == "__main__":
    processar_dados()
