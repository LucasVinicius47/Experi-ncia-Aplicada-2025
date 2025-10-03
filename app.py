import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
from football_api import (
    get_leagues,
    get_fixtures_by_date,
    get_match_statistics,
    get_match_lineups,
    get_standings,
    get_last_matches,
    get_recent_matches_all_seasons,
    get_head_to_head,
    get_teams_by_league,
    get_squad_by_team,
    get_player_stats,
)

st.set_page_config(page_title="⚽ Dash Gol", layout="wide")
st.title("⚽ Dash Gol")

# Sidebar
st.sidebar.header("📌 Filtros")
refresh_interval = st.sidebar.slider("⏱ Atualizar a cada (segundos)", 15, 120, 30)
st_autorefresh(interval=refresh_interval * 1000, key="refresh_app")

ligas_df = pd.DataFrame(get_leagues())
if ligas_df.empty:
    st.sidebar.error("❌ Nenhuma liga encontrada.")
    st.stop()

liga_nome = st.sidebar.selectbox("Selecione a Liga", ligas_df["name"])
liga_id = ligas_df[ligas_df["name"] == liga_nome]["id"].values[0]
data_escolhida = st.sidebar.date_input("Escolha a data", datetime.today())
temporada = datetime.today().year

# Partidas
partidas = get_fixtures_by_date(liga_id, data_escolhida, temporada)
if not partidas:
    st.warning("⚠ Nenhuma partida encontrada.")
    st.stop()

partida_selecionada = st.sidebar.selectbox(
    "Selecione a partida",
    [f"{p['teams']['home']['name']} x {p['teams']['away']['name']}" for p in partidas]
)

partida = next(
    (p for p in partidas if f"{p['teams']['home']['name']} x {p['teams']['away']['name']}" == partida_selecionada),
    None
)

if not partida:
    st.error("❌ Partida não encontrada.")
    st.stop()

fixture_id = partida["fixture"]["id"]
mandante = partida["teams"]["home"]["name"]
visitante = partida["teams"]["away"]["name"]
id_mandante = partida["teams"]["home"]["id"]
id_visitante = partida["teams"]["away"]["id"]

# Cabeçalho da Partida
st.header(f"🏟 {mandante} x {visitante}")
col1, col2, col3 = st.columns([2, 1, 2])
with col1:
    st.image(partida["teams"]["home"]["logo"], width=60)
    st.caption(mandante)
with col2:
    st.markdown(f"⏱ {partida['fixture']['status']['long']}")
    st.markdown(f"### {partida['goals']['home']} - {partida['goals']['away']}")
with col3:
    st.image(partida["teams"]["away"]["logo"], width=60)
    st.caption(visitante)

# Últimos 5 Jogos
with st.expander("⚽ Últimos 5 Jogos"):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(mandante)
        jogos_mandante_recentes = get_last_matches(id_mandante, limit=5)
        if jogos_mandante_recentes:
            for jogo in jogos_mandante_recentes:
                st.markdown(f"- **{jogo['Data']}** vs {jogo['Adversário']} | Placar: **{jogo['Placar']}** | Resultado: {jogo['Resultado']}")
        else:
            st.info("Nenhum jogo recente encontrado.")

    with col2:
        st.subheader(visitante)
        jogos_visitante_recentes = get_last_matches(id_visitante, limit=5)
        if jogos_visitante_recentes:
            for jogo in jogos_visitante_recentes:
                st.markdown(f"- **{jogo['Data']}** vs {jogo['Adversário']} | Placar: **{jogo['Placar']}** | Resultado: {jogo['Resultado']}")
        else:
            st.info("Nenhum jogo recente encontrado.")

# Últimos jogos (versão completa com 10 jogos)
def exibir_jogos(jogos, nome_time):
    if not jogos:
        st.warning(f"⚠ Nenhum jogo recente encontrado para {nome_time}.")
        return
    resultado_emoji = {"W": "✅", "D": "➖", "L": "❌"}
    for jogo in jogos:
        emoji = resultado_emoji.get(jogo["Resultado"], "")
        st.markdown(
            f"- {jogo['Data']} — {nome_time} vs {jogo['Adversário']} | Placar: {jogo['Placar']} {emoji}"
        )

st.subheader("📅 Histórico de Últimos Jogos (10 jogos)")
jogos_mandante = get_recent_matches_all_seasons(id_mandante, league_id=liga_id, limit=10)
jogos_visitante = get_recent_matches_all_seasons(id_visitante, league_id=liga_id, limit=10)

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**{mandante}**")
    exibir_jogos(jogos_mandante, mandante)
with col2:
    st.markdown(f"**{visitante}**")
    exibir_jogos(jogos_visitante, visitante)

# Confrontos Diretos
def exibir_confrontos(confrontos):
    if not confrontos:
        st.info("ℹ Nenhum confronto direto encontrado.")
        return
    for c in confrontos:
        st.markdown(
            f"- {c['Data']} — {c['Mandante']} x {c['Visitante']} | Placar: {c['Placar']}"
        )

st.subheader("🤝 Confrontos Diretos")
confrontos = get_head_to_head(id_mandante, id_visitante, limit=10)
exibir_confrontos(confrontos)

# Gráfico de desempenho
def contar_resultados(jogos):
    v, e, d = 0, 0, 0
    for j in jogos:
        if j["Resultado"] == "W": v += 1
        elif j["Resultado"] == "D": e += 1
        elif j["Resultado"] == "L": d += 1
    return v, e, d

v1, e1, d1 = contar_resultados(jogos_mandante)
v2, e2, d2 = contar_resultados(jogos_visitante)

fig = go.Figure(data=[
    go.Bar(name=mandante, x=["Vitórias", "Empates", "Derrotas"], y=[v1, e1, d1], marker_color='blue'),
    go.Bar(name=visitante, x=["Vitórias", "Empates", "Derrotas"], y=[v2, e2, d2], marker_color='red')
])
fig.update_layout(title="Desempenho nos últimos jogos", barmode='group')
st.plotly_chart(fig, use_container_width=True)

# Abas
tab1, tab2, tab3, tab4 = st.tabs(["📊 Estatísticas", "👕 Escalações", "🏆 Classificação", "👨‍選手 Análise de Jogador"])

with tab1:
    st.subheader("📊 Estatísticas da Partida")
    stats_df = pd.DataFrame(get_match_statistics(fixture_id))
    if stats_df.empty:
        st.info("ℹ Estatísticas não disponíveis.")
    else:
        st.dataframe(stats_df, use_container_width=True)

with tab2:
    st.subheader("👕 Escalações")
    lineups = get_match_lineups(fixture_id)
    if not lineups:
        st.info("ℹ Escalações não disponíveis.")
    else:
        for equipe in lineups:
            st.markdown(f"**{equipe['team']['name']}**")
            titulares = equipe.get("startXI", [])
            if titulares:
                df_titulares = pd.DataFrame([
                    {
                        "Nº": j["player"]["number"],
                        "Jogador": j["player"]["name"],
                        "Posição": j["player"]["pos"]
                    }
                    for j in titulares
                ])
                st.dataframe(df_titulares, use_container_width=True)
            else:
                st.write("Nenhum titular disponível.")

with tab3:
    st.subheader("🏆 Classificação da Liga")
    tabela = get_standings(liga_id, temporada)
    if tabela.empty:
        st.warning("⚠ Classificação não disponível.")
    else:
        destaque = [mandante, visitante]
        def highlight(row):
            return ['background-color: yellow' if row["Time"] in destaque else '' for _ in row]
        st.dataframe(tabela.style.apply(highlight, axis=1), use_container_width=True)

with tab4:
    st.subheader("👨‍選手 Análise de Jogador")
    
    times_exploraveis = get_teams_by_league(liga_id, temporada)
    if not times_exploraveis:
        st.warning("⚠ Nenhum time encontrado para esta liga/temporada.")
    else:
        df_times = pd.DataFrame([{
            "id": t["team"]["id"],
            "name": t["team"]["name"]
        } for t in times_exploraveis])
        
        time_selecionado = st.selectbox("Selecione um time", df_times["name"])
        id_time_selecionado = df_times[df_times["name"] == time_selecionado]["id"].values[0]

        elenco = get_squad_by_team(id_time_selecionado, temporada)
        if not elenco:
            st.info("ℹ Elenco não disponível.")
        else:
            df_jogadores = pd.DataFrame(elenco)
            jogador_selecionado = st.selectbox("Selecione um jogador", df_jogadores["name"])
            id_jogador_selecionado = df_jogadores[df_jogadores["name"] == jogador_selecionado]["id"].values[0]

            if jogador_selecionado:
                jogador_stats = get_player_stats(id_jogador_selecionado, temporada, liga_id)
                if jogador_stats:
                    jogador_info = jogador_stats.get("player", {})
                    jogador_estatisticas = jogador_stats.get("statistics", [{}])[0]
                    
                    st.header(f"Detalhes de {jogador_info.get('name')}")
                    
                    col_foto, col_info = st.columns([1, 2])
                    with col_foto:
                        st.image(jogador_info.get("photo"), width=150)
                    with col_info:
                        st.markdown(f"**Nome:** {jogador_info.get('name')}")
                        st.markdown(f"**Idade:** {jogador_info.get('age')}")
                        st.markdown(f"**Nacionalidade:** {jogador_info.get('nationality')}")
                        st.markdown(f"**Posição:** {jogador_estatisticas.get('games', {}).get('position')}")
                    
                    st.markdown("### Estatísticas da Temporada")
                    df_estatisticas = pd.DataFrame([
                        {
                            "Categoria": "Jogos Disputados",
                            "Valor": jogador_estatisticas.get('games', {}).get('appearences')
                        },
                        {
                            "Categoria": "Gols",
                            "Valor": jogador_estatisticas.get('goals', {}).get('total')
                        },
                        {
                            "Categoria": "Assistências",
                            "Valor": jogador_estatisticas.get('goals', {}).get('assists')
                        },
                        {
                            "Categoria": "Cartões Amarelos",
                            "Valor": jogador_estatisticas.get('cards', {}).get('yellow')
                        },
                        {
                            "Categoria": "Cartões Vermelhos",
                            "Valor": jogador_estatisticas.get('cards', {}).get('red')
                        }
                    ])
                    st.dataframe(df_estatisticas.set_index("Categoria"), use_container_width=True)
                else:
                    st.warning("⚠️ Estatísticas do jogador não disponíveis para esta temporada/liga.")