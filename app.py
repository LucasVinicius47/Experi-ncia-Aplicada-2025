import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
from football_api import (
    get_leagues,
    get_fixtures_by_date,
    get_match_statistics,
    get_match_lineups,
    get_standings,
)

# ========================
# Configuração da Página
# ========================
st.set_page_config(
    page_title="⚽ Dash Gol",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("⚽ Dash Gol")

# ========================
# Sidebar - Seleções
# ========================
st.sidebar.header("📌 Filtros")

# Intervalo de atualização configurável
refresh_interval = st.sidebar.slider("⏱ Atualizar a cada (segundos)", 15, 120, 30, step=5)
st_autorefresh(interval=refresh_interval * 1000, key="refresh")

ligas = get_leagues()
ligas_df = pd.DataFrame(ligas)

if ligas_df.empty:
    st.sidebar.error("❌ Nenhuma liga encontrada. Verifique sua API Key.")
    st.stop()

liga_nome = st.sidebar.selectbox("Selecione a Liga", ligas_df["name"])
liga_id = ligas_df[ligas_df["name"] == liga_nome]["id"].values[0]

data_escolhida = st.sidebar.date_input("Escolha a data", datetime.today())
temporada = datetime.today().year

# ========================
# Buscar Partidas
# ========================
partidas = get_fixtures_by_date(liga_id, data_escolhida, temporada)

if not partidas:
    st.warning("⚠ Nenhuma partida encontrada para esta data.")
    st.stop()

st.sidebar.subheader("📅 Partidas do dia")
partida_selecionada = st.sidebar.selectbox(
    "Selecione a partida",
    [f"{p['teams']['home']['name']} x {p['teams']['away']['name']}" for p in partidas],
)

partida = [
    p for p in partidas if f"{p['teams']['home']['name']} x {p['teams']['away']['name']}" == partida_selecionada
][0]

fixture_id = partida["fixture"]["id"]

# Guardar o time atual em sessão para destacar na tabela
st.session_state["time_atual"] = partida["teams"]["home"]["name"]

# ========================
# Exibir Informações da Partida
# ========================
st.header(f"🏟 {partida['teams']['home']['name']} x {partida['teams']['away']['name']}")

col1, col2, col3 = st.columns([2, 1, 2])

with col1:
    st.image(partida["teams"]["home"]["logo"], width=100)
    st.subheader(partida["teams"]["home"]["name"])

with col2:
    st.markdown(f"### ⏱ {partida['fixture']['status']['long']}")
    st.markdown(f"## {partida['goals']['home']} - {partida['goals']['away']}")

with col3:
    st.image(partida["teams"]["away"]["logo"], width=100)
    st.subheader(partida["teams"]["away"]["name"])

# ========================
# Estatísticas da Partida
# ========================
st.subheader("📊 Estatísticas da Partida")
stats = get_match_statistics(fixture_id)

if not stats:
    st.info("ℹ Estatísticas não disponíveis para esta partida.")
else:
    stats_df = pd.DataFrame(stats)

    if not stats_df.empty:
        st.dataframe(
            stats_df.style.set_properties(**{'color': 'white'}),
            use_container_width=True
        )
    else:
        st.info("ℹ Estatísticas ainda não foram carregadas.")

# ========================
# Escalações
# ========================
st.subheader("👕 Escalações")
lineups = get_match_lineups(fixture_id)

if not lineups:
    st.info("ℹ Escalações não disponíveis.")
else:
    for equipe in lineups:
        team_name = equipe.get("team", {}).get("name", "N/D")
        st.markdown(f"### {team_name}")

        titulares = equipe.get("startXI", [])
        if not titulares:
            st.write("Nenhum titular disponível.")
        else:
            df_titulares = pd.DataFrame([
                {
                    "Nº": j["player"]["number"],
                    "Jogador": j["player"]["name"],
                    "Posição": j["player"]["pos"]
                }
                for j in titulares
            ])
            st.dataframe(df_titulares, use_container_width=True)

# ========================
# Classificação
# ========================
st.subheader("🏆 Classificação da Liga")

tabela = get_standings(liga_id, temporada)

if tabela is None or tabela.empty:
    st.warning("⚠ Nenhuma informação da classificação disponível")
else:
    tabela_exibicao = tabela.copy()

    if "time_atual" in st.session_state:
        time_destacado = st.session_state["time_atual"]

        def highlight_team(row):
            if row["Time"] == time_destacado:
                return ['background-color: yellow; color: black; font-weight: bold'] * len(row)
            return [''] * len(row)

        st.dataframe(
            tabela_exibicao.style.apply(highlight_team, axis=1),
            use_container_width=True
        )
    else:
        st.dataframe(tabela_exibicao, use_container_width=True)
