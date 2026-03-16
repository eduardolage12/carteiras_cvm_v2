"""
SCRIPT 03 - APP DE CONSULTA (STREAMLIT)
"""

from __future__ import annotations

import io
import os
from typing import Iterable

import pandas as pd
import streamlit as st


def encontrar_coluna(df: pd.DataFrame, opcoes: Iterable[str]) -> str | None:
    for col in opcoes:
        if col in df.columns:
            return col
    return None


def fmt_brl(valor: object) -> str:
    if pd.isna(valor):
        return ""
    try:
        texto = f"{float(valor):,.2f}"
        texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
        return f"R$ {texto}"
    except Exception:  # noqa: BLE001
        return str(valor)


def fmt_pct(valor: object) -> str:
    if pd.isna(valor):
        return ""
    try:
        texto = f"{float(valor):,.2f}"
        texto = texto.replace(",", "_").replace(".", ",").replace("_", ".")
        return f"{texto}%"
    except Exception:  # noqa: BLE001
        return str(valor)


def fmt_bool_sim_nao(valor: object) -> str:
    if pd.isna(valor):
        return ""
    return "Sim" if bool(valor) else "Nao"


st.set_page_config(page_title="Carteiras de Fundos CVM", layout="wide")

POSSIVEIS_LOGOS = [
    "assets/logo_af_ultra.png",
    "assets/logo_af_ultra.jpg",
    "assets/logo_af_ultra.jpeg",
    "assets/logo_af_ultra.webp",
    "base_emissores/logo_af_ultra.png",
]

logo_path = next((p for p in POSSIVEIS_LOGOS if os.path.exists(p)), None)
if logo_path:
    topo_logo, topo_titulo = st.columns([0.35, 5])
    with topo_logo:
        st.image(logo_path, width=56)
    with topo_titulo:
        st.markdown("## Consulta de Carteiras de Fundos (CVM)")
else:
    st.title("Consulta de Carteiras de Fundos (CVM)")


@st.cache_data
def carregar_dados() -> pd.DataFrame:
    return pd.read_parquet("dados_processados/carteiras_consolidadas.parquet")


try:
    df = carregar_dados()
except FileNotFoundError:
    st.error(
        "Base de dados nao encontrada "
        "(`dados_processados/carteiras_consolidadas.parquet`).\n\n"
        "**Na nuvem (Streamlit Cloud):** execute o workflow "
        "'Atualizar dados CVM' no GitHub Actions para gerar o arquivo "
        "automaticamente.\n\n"
        "**Localmente:** execute os scripts abaixo:"
    )
    st.code("python 01_baixar_dados.py\npython 02_processar_dados.py")
    st.stop()

COL_CNPJ = encontrar_coluna(df, ["CNPJ_FUNDO_CLASSE", "CNPJ_FUNDO"])
COL_NOME_FUNDO = encontrar_coluna(
    df,
    [
        "DENOM_SOCIAL",
        "NM_FUNDO_CLASSE",
        "DENOM_SOCIAL_CLASSE_REG",
        "DENOM_SOCIAL_FUNDO_REG",
        "DENOM_SOCIAL_CAD",
    ],
)
COL_ATIVO = encontrar_coluna(df, ["DS_ATIVO", "NM_FUNDO_COTA"])
COL_CD_ATIVO = encontrar_coluna(df, ["CD_ATIVO"])
COL_EMISSOR = encontrar_coluna(df, ["EMISSOR_BASE", "EMISSOR_MAP", "EMISSOR"])
COL_VALOR = encontrar_coluna(df, ["VL_MERC_POS_FINAL", "VL_MERCADO_POS_FINAL", "VL_MERC_POSICAO_FINAL"])
COL_PL = encontrar_coluna(
    df,
    [
        "VL_PATRIMONIO_BASE",
        "PATRIMONIO_LIQUIDO_CLASSE_REG",
        "VL_PATRIM_LIQ",
        "PATRIMONIO_LIQUIDO_FUNDO_REG",
        "VL_PATRIM_LIQ_CAD",
        "PATRIMONIO_LIQUIDO",
    ],
)
COL_GESTOR = encontrar_coluna(df, ["GESTOR_REG", "GESTOR", "GESTOR_CAD"])
COL_CLASSE = encontrar_coluna(df, ["CLASSE_ANBIMA_REG", "CLASSE_ANBIMA", "CLASSE_ANBIMA_CAD"])
COL_TIPO = encontrar_coluna(df, ["TIPO_FUNDO_REG", "TP_FUNDO_CLASSE", "TP_FUNDO"])
COL_DATA = encontrar_coluna(df, ["MES_SELECIONADO_FMT", "MES_REF", "DT_COMPTC"])

COL_MES_ALVO = "MES_ALVO_FMT" if "MES_ALVO_FMT" in df.columns else None
COL_MES_SELECIONADO = "MES_SELECIONADO_FMT" if "MES_SELECIONADO_FMT" in df.columns else None
COL_USOU_FALLBACK = "USOU_FALLBACK" if "USOU_FALLBACK" in df.columns else None
COL_DEFASAGEM = "DEFASAGEM_MESES" if "DEFASAGEM_MESES" in df.columns else None
COL_DATA_BASE_EFETIVA = "DATA_BASE_EFETIVA" if "DATA_BASE_EFETIVA" in df.columns else None
COL_DISCLAIMER = "DISCLAIMER" if "DISCLAIMER" in df.columns else None

st.sidebar.header("Resumo")
if COL_MES_ALVO and not df.empty:
    st.sidebar.write(f"Mes-alvo: {df[COL_MES_ALVO].dropna().iloc[0]}")
if COL_CNPJ:
    st.sidebar.write(f"Fundos unicos: {df[COL_CNPJ].nunique():,}")
st.sidebar.write(f"Total de posicoes: {len(df):,}")

df_base = df.copy()
if COL_USOU_FALLBACK:
    fundos_total = df[COL_CNPJ].nunique() if COL_CNPJ else 0
    fundos_fallback = df.loc[df[COL_USOU_FALLBACK] == True, COL_CNPJ].nunique() if COL_CNPJ else 0  # noqa: E712
    st.sidebar.write(f"Fundos com fallback: {fundos_fallback:,}")
    incluir_fallback = st.sidebar.checkbox("Incluir fundos com fallback", value=True)
    if not incluir_fallback:
        df_base = df_base[df_base[COL_USOU_FALLBACK] != True]  # noqa: E712
    if fundos_fallback > 0:
        st.info(
            f"Ha {fundos_fallback:,} fundos sem carteira no mes-alvo. "
            "Nesses casos foi usada a ultima carteira disponivel."
        )
    if fundos_total > 0:
        st.caption(
            f"Fallback em {fundos_fallback / fundos_total:.1%} dos fundos considerados."
        )

aba1, aba2 = st.tabs(["Pesquisar por Ativo/Emissor", "Pesquisar por Fundo"])

with aba2:
    st.subheader("Pesquisar por Fundo")
    termo_fundo = st.text_input("Digite nome ou CNPJ do fundo", key="termo_fundo")
    if termo_fundo:
        mascara = pd.Series(False, index=df_base.index)
        for col in [COL_NOME_FUNDO, COL_CNPJ]:
            if col:
                mascara |= df_base[col].astype(str).str.contains(termo_fundo, case=False, na=False)
        resultado_fundo = df_base[mascara].copy()

        if resultado_fundo.empty:
            st.warning("Nenhum fundo encontrado.")
        else:
            if COL_CNPJ and COL_NOME_FUNDO:
                fundos = resultado_fundo[[COL_CNPJ, COL_NOME_FUNDO]].drop_duplicates()
                opcoes = fundos.apply(lambda r: f"{r[COL_NOME_FUNDO]} ({r[COL_CNPJ]})", axis=1).tolist()
                escolhido = st.selectbox("Selecione o fundo", options=opcoes)
                cnpj = escolhido.rsplit("(", 1)[-1].replace(")", "").strip()
                resultado_fundo = resultado_fundo[resultado_fundo[COL_CNPJ].astype(str) == cnpj]

            if COL_VALOR and COL_VALOR in resultado_fundo.columns:
                resultado_fundo = resultado_fundo.sort_values(COL_VALOR, ascending=False)

            if not resultado_fundo.empty and COL_USOU_FALLBACK:
                info = resultado_fundo.iloc[0]
                if COL_MES_ALVO and COL_MES_SELECIONADO:
                    st.caption(
                        f"Mes-alvo: {info.get(COL_MES_ALVO, '')} | "
                        f"Data usada: {info.get(COL_MES_SELECIONADO, '')} | "
                        f"Fallback: {fmt_bool_sim_nao(info.get(COL_USOU_FALLBACK))}"
                    )
                if COL_DISCLAIMER and info.get(COL_DISCLAIMER):
                    st.warning(str(info.get(COL_DISCLAIMER)))

            colunas = [
                c
                for c in [
                    COL_ATIVO,
                    COL_CD_ATIVO,
                    COL_VALOR,
                    COL_PL,
                    "PCT_PL",
                    "BLOCO",
                    COL_MES_SELECIONADO,
                    COL_DATA_BASE_EFETIVA,
                    COL_USOU_FALLBACK,
                    COL_DEFASAGEM,
                    COL_DISCLAIMER,
                ]
                if c and c in resultado_fundo.columns
            ]
            exibir_fundo = resultado_fundo[colunas].copy()
            if COL_VALOR and COL_VALOR in exibir_fundo.columns:
                exibir_fundo[COL_VALOR] = exibir_fundo[COL_VALOR].map(fmt_brl)
            if COL_PL and COL_PL in exibir_fundo.columns:
                exibir_fundo[COL_PL] = exibir_fundo[COL_PL].map(fmt_brl)
            if "PCT_PL" in exibir_fundo.columns:
                exibir_fundo["PCT_PL"] = exibir_fundo["PCT_PL"].map(fmt_pct)
            if COL_USOU_FALLBACK and COL_USOU_FALLBACK in exibir_fundo.columns:
                exibir_fundo[COL_USOU_FALLBACK] = exibir_fundo[COL_USOU_FALLBACK].map(fmt_bool_sim_nao)

            st.dataframe(exibir_fundo, use_container_width=True, height=520)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                resultado_fundo[colunas].to_excel(writer, index=False, sheet_name="carteira")
            st.download_button(
                "Baixar Excel",
                data=buffer.getvalue(),
                file_name="carteira_fundo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

with aba1:
    st.subheader("Pesquisar por Ativo/Emissor")
    termo_g = st.text_input(
        "Digite um ativo ou emissor para consolidar por gestora",
        key="termo_gestora",
    )
    if not COL_GESTOR:
        st.warning("Coluna de gestora nao encontrada na base.")
    elif termo_g:
        mascara = pd.Series(False, index=df_base.index)
        for col in [COL_ATIVO, COL_CD_ATIVO, COL_EMISSOR]:
            if col:
                mascara |= df_base[col].astype(str).str.contains(termo_g, case=False, na=False)
        resultado_g = df_base[mascara].copy()

        if resultado_g.empty:
            st.warning("Nenhum resultado encontrado para esse ativo.")
        elif not COL_VALOR:
            st.warning("Coluna de valor nao encontrada para consolidacao.")
        else:
            agrupado = (
                resultado_g.groupby(COL_GESTOR, dropna=False)
                .agg(
                    valor_total=(COL_VALOR, "sum"),
                    qtd_fundos=(COL_CNPJ, "nunique") if COL_CNPJ else (COL_GESTOR, "count"),
                    posicao_media=(COL_VALOR, "mean"),
                )
                .reset_index()
                .sort_values("valor_total", ascending=False)
            )

            exibir = agrupado.rename(
                columns={
                    COL_GESTOR: "Gestora",
                    "valor_total": "Valor Total (R$)",
                    "qtd_fundos": "No de Fundos",
                    "posicao_media": "Posicao Media (R$)",
                }
            )
            exibir["Valor Total (R$)"] = exibir["Valor Total (R$)"].map(fmt_brl)
            exibir["Posicao Media (R$)"] = exibir["Posicao Media (R$)"].map(fmt_brl)
            st.dataframe(exibir, use_container_width=True, height=450)

            escolhas = agrupado[COL_GESTOR].fillna("SEM_GESTORA").astype(str).tolist()
            gestora = st.selectbox("Detalhar gestora", escolhas if escolhas else [])
            if gestora:
                detalhe = resultado_g[resultado_g[COL_GESTOR].fillna("SEM_GESTORA").astype(str) == gestora].copy()
                colunas_fundo = [c for c in [COL_NOME_FUNDO, COL_CNPJ] if c and c in detalhe.columns]
                if colunas_fundo and COL_VALOR and COL_VALOR in detalhe.columns:
                    agregacoes: dict[str, tuple[str, str]] = {
                        "VALOR_TOTAL_EMISSOR": (COL_VALOR, "sum"),
                        "QTD_ATIVOS": (COL_VALOR, "size"),
                    }
                    if "PCT_PL" in detalhe.columns:
                        agregacoes["PCT_PL_TOTAL"] = ("PCT_PL", "sum")
                    if COL_PL and COL_PL in detalhe.columns:
                        agregacoes["PL_FUNDO"] = (COL_PL, "first")
                    if COL_MES_SELECIONADO and COL_MES_SELECIONADO in detalhe.columns:
                        agregacoes["MES_CARTEIRA"] = (COL_MES_SELECIONADO, "first")
                    if COL_USOU_FALLBACK and COL_USOU_FALLBACK in detalhe.columns:
                        agregacoes["USOU_FALLBACK_FUNDO"] = (COL_USOU_FALLBACK, "first")
                    if COL_DEFASAGEM and COL_DEFASAGEM in detalhe.columns:
                        agregacoes["DEFASAGEM_MESES_FUNDO"] = (COL_DEFASAGEM, "first")

                    detalhe_por_fundo = (
                        detalhe.groupby(colunas_fundo, dropna=False)
                        .agg(**agregacoes)
                        .reset_index()
                        .sort_values("VALOR_TOTAL_EMISSOR", ascending=False)
                    )

                    st.markdown("**Posicao consolidada por fundo no termo pesquisado**")
                    exibir_det = detalhe_por_fundo.copy()
                    exibir_det["VALOR_TOTAL_EMISSOR"] = exibir_det["VALOR_TOTAL_EMISSOR"].map(fmt_brl)
                    if "PL_FUNDO" in exibir_det.columns:
                        exibir_det["PL_FUNDO"] = exibir_det["PL_FUNDO"].map(fmt_brl)
                    if "PCT_PL_TOTAL" in exibir_det.columns:
                        exibir_det["PCT_PL_TOTAL"] = exibir_det["PCT_PL_TOTAL"].map(fmt_pct)
                    if "USOU_FALLBACK_FUNDO" in exibir_det.columns:
                        exibir_det["USOU_FALLBACK_FUNDO"] = exibir_det["USOU_FALLBACK_FUNDO"].map(fmt_bool_sim_nao)

                    st.dataframe(exibir_det, use_container_width=True, height=360)
                else:
                    st.warning("Nao foi possivel consolidar por fundo (faltou CNPJ/nome ou valor).")

                if COL_CNPJ and COL_NOME_FUNDO and COL_CNPJ in detalhe.columns and COL_NOME_FUNDO in detalhe.columns:
                    fundos_gestora = detalhe[[COL_CNPJ, COL_NOME_FUNDO]].drop_duplicates()
                    if len(fundos_gestora) >= 1:
                        opcoes_fundo = fundos_gestora.apply(
                            lambda r: f"{r[COL_NOME_FUNDO]} ({r[COL_CNPJ]})", axis=1
                        ).tolist()
                        escolhido_fundo = st.selectbox(
                            "Detalhar fundo especifico",
                            options=opcoes_fundo,
                            key="fundo_gestora",
                        )
                        if escolhido_fundo:
                            cnpj_fundo = escolhido_fundo.rsplit("(", 1)[-1].replace(")", "").strip()
                            detalhe_fundo = detalhe[detalhe[COL_CNPJ].astype(str) == cnpj_fundo].copy()

                            st.markdown(f"**Posicoes do fundo selecionado** ({len(detalhe_fundo)} ativos)")

                            colunas_fundo = [
                                c
                                for c in [
                                    COL_ATIVO,
                                    COL_CD_ATIVO,
                                    COL_EMISSOR,
                                    COL_VALOR,
                                    "PCT_PL",
                                    COL_MES_SELECIONADO,
                                    COL_DATA_BASE_EFETIVA,
                                    COL_USOU_FALLBACK,
                                    COL_DEFASAGEM,
                                ]
                                if c and c in detalhe_fundo.columns
                            ]
                            exibir_fundo = detalhe_fundo[colunas_fundo].copy()
                            if COL_VALOR and COL_VALOR in exibir_fundo.columns:
                                exibir_fundo[COL_VALOR] = exibir_fundo[COL_VALOR].map(fmt_brl)
                            if "PCT_PL" in exibir_fundo.columns:
                                exibir_fundo["PCT_PL"] = exibir_fundo["PCT_PL"].map(fmt_pct)
                            if COL_USOU_FALLBACK and COL_USOU_FALLBACK in exibir_fundo.columns:
                                exibir_fundo[COL_USOU_FALLBACK] = exibir_fundo[COL_USOU_FALLBACK].map(fmt_bool_sim_nao)

                            st.dataframe(exibir_fundo, use_container_width=True, height=360)

st.caption("Fonte: Dados abertos CVM (carteiras com defasagem e fallback por fundo quando necessario).")
