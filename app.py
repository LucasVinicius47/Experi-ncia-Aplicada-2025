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
    initial_sidebar_state="collapsed",
)

st.title("⚽ Dash Gol")

# ========================
# Sidebar - Filtros
# ========================
st.sidebar.header("📌 Filtros")
refresh_interval = st.sidebar.slider("⏱ Atualizar a cada (segundos)", 15, 120, 15, step=5)
st_autorefresh(interval=refresh_interval * 1000, key="refresh")

# ========================
# Seleção de Liga
# ========================
ligas = get_leagues()
ligas_df = pd.DataFrame(ligas)

if ligas_df.empty:
    st.sidebar.error("❌ Nenhuma liga encontrada. Verifique sua API Key.")
    st.stop()

liga_nome = st.sidebar.selectbox("Selecione a Liga", ligas_df["name"])
liga_id = ligas_df[ligas_df["name"] == liga_nome]["id"].values[0]

# ========================
# Seleção de Data e Temporada
# ========================
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
mandante = partida["teams"]["home"]["name"]
visitante = partida["teams"]["away"]["name"]
st.session_state["time_atual"] = mandante

# ========================
# Informações da Partida
# ========================
st.header(f"🏟 {mandante} x {visitante}")

col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    st.image(partida["teams"]["home"]["logo"], width=80)
    st.caption(mandante)
with col2:
    st.markdown(f"**⏱ {partida['fixture']['status']['long']}**")
    st.markdown(f"### {partida['goals']['home']} - {partida['goals']['away']}")
with col3:
    st.image(partida["teams"]["away"]["logo"], width=80)
    st.caption(visitante)

# ========================
# Estatísticas
# ========================
st.subheader("📊 Estatísticas da Partida")
stats = get_match_statistics(fixture_id)

if not stats:
    st.info("ℹ Estatísticas não disponíveis para esta partida.")
else:
    stats_df = pd.DataFrame(stats)
    if not stats_df.empty:
        st.dataframe(stats_df, use_container_width=True, height=400)
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
        st.markdown(f"**{team_name}**")
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
            st.dataframe(df_titulares, use_container_width=True, height=400)

# ========================
# Função para renderizar tabela de classificação com estilo
# ========================
def render_classification_table(df, team_col, highlight_teams):
    def highlight_team(row):
        if row[team_col] in highlight_teams:
            return ['background-color: yellow; font-weight: bold' for _ in row]
        else:
            return ['background-color: #f2f2f2; color: black' for _ in row]

    styled_df = df.style.apply(highlight_team, axis=1)\
                        .set_table_styles([{
                            'selector': 'th',
                            'props': [('background-color', '#f2f2f2'),
                                      ('color', '#1f77b4'),
                                      ('border', '1px solid #ddd'),
                                      ('text-align', 'center'),
                                      ('font-weight', 'bold'),
                                      ('padding', '4px')]
                        }])\
                        .set_properties(**{'border': '1px solid #ddd', 
                                           'text-align': 'center', 
                                           'padding': '4px'})
    st.dataframe(styled_df, use_container_width=True)

# ========================
# Classificação da Liga
# ========================
st.subheader("🏆 Classificação da Liga")
tabela = get_standings(liga_id, temporada)

if tabela is None or tabela.empty:
    st.warning("⚠ Nenhuma informação da classificação disponível")
else:
    tabela_exibicao = tabela.copy()
    possible_team_cols = ["Time", "Team", "Nome", "Clube"]
    team_col = next((col for col in possible_team_cols if col in tabela_exibicao.columns), None)

    if not team_col:
        st.warning("⚠ Não foi possível encontrar a coluna de times na tabela.")
        st.dataframe(tabela_exibicao, use_container_width=True, height=500)
    else:
        # Organizar colunas principais
        colunas_ordem = [team_col, "Posição", "Jogos", "Vitórias", "Empates", "Derrotas", "Gols", "Pontos"]
        tabela_exibicao = tabela_exibicao[[c for c in colunas_ordem if c in tabela_exibicao.columns]]

        # Renderizar tabela estilizada
        render_classification_table(tabela_exibicao, team_col, [mandante, visitante])
