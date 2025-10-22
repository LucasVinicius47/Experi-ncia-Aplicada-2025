import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

# 🚨 1. IMPORTAÇÃO DA LÓGICA DE AUTENTICAÇÃO
# NOTE: Certifique-se de que o arquivo 'auth_app.py' existe e está no mesmo diretório.
from auth_app import require_login_and_render_ui

# NOTE: Certifique-se de que o arquivo 'football_api.py' existe e está no mesmo diretório.
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


# =================================================================
# FUNÇÃO: TRADUÇÃO E CRONÔMETRO
# =================================================================

def get_translated_status_and_time(fixture_status):
    """
    Traduz o status da partida e formata o tempo decorrido (cronômetro).
    """
    status_long = fixture_status.get('long', 'Não Encontrado')
    elapsed = fixture_status.get('elapsed')

    # Mapeamento do Status e Tradução
    status_map = {
        'Not Started': 'Não Iniciado',
        'Time to be defined': 'Horário a Definir',
        'Match Postponed': 'Partida Adiada',
        'Match Cancelled': 'Partida Cancelada',
        'Match Interrupted': 'Partida Interrompida',
        'Match Suspended': 'Partida Suspensa',
        # Status de Partida em Andamento
        'First Half': '1º Tempo',
        'Halftime': 'Intervalo',
        'Second Half': '2º Tempo',
        # Status de Partida Finalizada/Pausada
        'Extra Time': 'Prorrogação',
        'Break Time': 'Intervalo da Prorrogação',
        'Penalty Shootout': 'Pênaltis',
        'Match Finished': 'Fim de Jogo',
        'After Penalty': 'Fim de Jogo (Pênaltis)',
        'Abandoned': 'Abandonada'
    }

    translated_status = status_map.get(status_long, status_long)
    
    # Formatação do Cronômetro (apenas para jogos em andamento)
    if translated_status in ['1º Tempo', '2º Tempo']:
        display_text = f"{translated_status} | {elapsed}'"
    elif translated_status in ['Prorrogação', 'Pênaltis', 'Intervalo da Prorrogação']:
        display_text = translated_status
    elif translated_status == 'Intervalo':
        display_text = translated_status
    else:
        display_text = translated_status

    return display_text

# =================================================================
# === FUNÇÕES DE ESTILIZAÇÃO (FLASH SCORE) ===
# =================================================================

def format_position_column_html(row):
    """
    Cria a coluna de Posição como um balão HTML, aplicando a lógica de cores de zona.
    Regras de Cor: 1-4 (Verde), 5-6 (Azul Forte), 7-12 (Azul Claro), 17+ (Vermelho)
    """
    try:
        # Usa 'Posicao_Pura' para garantir que a cor seja aplicada corretamente
        posicao = int(row['Posicao_Pura'])
    except (TypeError, ValueError):
        return str(row.get('Posicao_Pura', ''))
        
    background_color = "#E0E0E0"  # Cinza padrão (Neutro)
    text_color = "black"
    
    # Lógica de Zonas de Classificação (Referência Brasileirão/Liga padrão 20 times)
    if 1 <= posicao <= 4:
        # 1. Libertadores - Fase de Grupos (Verde)
        background_color = "#66BB6A"
    elif 5 <= posicao <= 6:
        # 2. Libertadores - Qualificação (Azul Forte)
        background_color = "#007BFF" 
        text_color = "white"
    elif 7 <= posicao <= 12:
        # 3. Sul-Americana - Fase de Grupos (Azul Claro/Ciano)
        background_color = "#00BFFF" 
        text_color = "black"
    elif posicao >= 17:
        # 4. Rebaixamento (Vermelho)
        background_color = "#EF5350"
        text_color = "white"

    # Estilo do balão
    style = f"background-color: {background_color}; color: {text_color}; border-radius: 50%; width: 25px; height: 25px; line-height: 25px; text-align: center; font-weight: bold; margin: auto; display: block;"
    
    return f'<div style="{style}">{posicao}</div>'

def format_team_column_html(row):
    """
    Cria a coluna de Time como Logo + Nome.
    """
    # Verifica se a URL da logo existe para evitar erro
    logo_url = row.get("Logo URL", "")
    if logo_url:
        logo_html = f'<img src="{logo_url}" style="width: 20px; height: 20px; vertical-align: middle; margin-right: 5px;">'
    else:
        logo_html = '<span style="width: 20px; height: 20px; display: inline-block; vertical-align: middle; margin-right: 5px;"></span>' # Espaço vazio

    # Usa 'Time_Puro' para garantir que o nome seja exibido corretamente no HTML
    return f'<div style="display: flex; align-items: center; justify-content: start; white-space: nowrap;">{logo_html}<strong>{row["Time_Puro"]}</strong></div>'


# FUNÇÃO DE DESTAQUE CORRIGIDA E ROBUSTA (AGORA COM COR AZUL ESCURO #1E90FF)
def highlight_match_teams_styler_final(row, mandante, visitante):
    """
    Aplica destaque AZUL ESCURO na linha se for um dos times da partida,
    usando a coluna 'Time_Puro' para comparação.
    """
    # A coluna 'Time_Puro' é mantida no DataFrame interno do Styler
    if row.get('Time_Puro') in [mandante, visitante]:
        # 🚨 COR NOVA: Azul Escuro (#1E90FF)
        # Nota: Ajustei a cor da fonte para branco, pois o fundo azul escuro precisa de um texto claro.
        return ['background-color: #1E90FF; color: white'] * len(row)
    return [''] * len(row)

# =================================================================
# === 🚨 2. BLOCO DE PROTEÇÃO DO DASHBOARD (A PARTIR DAQUI) ===
# =================================================================
if require_login_and_render_ui():
    
    st.set_page_config(page_title="⚽ Dash Gol", layout="wide")
    st.title("⚽ Dash Gol")
    
    # Adiciona o botão de Sair
    if st.sidebar.button("Sair", key="logout_btn"):
        st.session_state['logged_in'] = False
        st.session_state['mode'] = 'login'
        st.rerun()  
        
    st.sidebar.success(f"Logado como: {st.session_state['user_email']}") 
    
    # Sidebar
    st.sidebar.header("📌 Filtros")
    
    # Slider para o Autorefresh
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

    # CRONÔMETRO E STATUS
    fixture_status = partida['fixture']['status']
    match_status_text = get_translated_status_and_time(fixture_status)

    # Cabeçalho da Partida
    st.header(f"🏟 {mandante} x {visitante}")
    
    col1, col2, col3 = st.columns([2, 1, 2])
    with col1:
        st.image(partida["teams"]["home"]["logo"], width=60)
        st.caption(mandante)
    with col2:
        st.markdown(f"⌚ {match_status_text}")
        st.markdown(f"### {partida['goals']['home']} - {partida['goals']['away']}")
    with col3:
        st.image(partida["teams"]["away"]["logo"], width=60)
        st.caption(visitante)

    # Últimos 5 Jogos
    with st.expander("⚽ Últimos 5 Jogos"):
        col1, col2 = st.columns(2)

        def exibir_jogos_simples(jogos, nome_time, col):
            with col:
                st.subheader(nome_time)
                if jogos:
                    for jogo in jogos:
                        st.markdown(f"- *{jogo['Data']}* vs {jogo['Adversário']} | Placar: *{jogo['Placar']}* | Resultado: {jogo['Resultado']}")
                else:
                    st.info("Nenhum jogo recente encontrado.")

        jogos_mandante_recentes = get_last_matches(id_mandante, limit=5)
        jogos_visitante_recentes = get_last_matches(id_visitante, limit=5)
        exibir_jogos_simples(jogos_mandante_recentes, mandante, col1)
        exibir_jogos_simples(jogos_visitante_recentes, visitante, col2)

    # Histórico completo de 10 jogos
    def exibir_jogos_com_emoji(jogos, nome_time):
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
        exibir_jogos_com_emoji(jogos_mandante, mandante)
    with col2:
        st.markdown(f"**{visitante}**")
        exibir_jogos_com_emoji(jogos_visitante, visitante)

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

    # ==============================================================================
    # TAB 3: CLASSIFICAÇÃO (ESTILO FLASH SCORE FINAL E CORRIGIDO O DESTAQUE)
    # ==============================================================================
    with tab3:
        st.subheader("🏆 Classificação da Liga")
        tabela = get_standings(liga_id, temporada)
        
        if tabela is None or tabela.empty: 
            st.warning("⚠ Classificação não disponível para esta liga/temporada.")
        elif 'Logo URL' not in tabela.columns:
            st.warning("⚠ Classificação disponível, mas a coluna 'Logo URL' não foi encontrada. Verifique a função `get_standings`.")
            # Exibe a tabela padrão como fallback se a logo falhar
            st.dataframe(tabela, use_container_width=True) 
        else:
            try:
                tabela_html = tabela.copy()
                
                # CRIA COLUNAS PURAS para o Styler usar na lógica
                tabela_html['Time_Puro'] = tabela_html['Time'] 
                if 'Posição' in tabela_html.columns:
                    tabela_html['Posicao_Pura'] = tabela_html['Posição']
                    tabela_html = tabela_html.drop(columns=['Posição']) 
                else:
                     # Se 'Posição' não existe, usa o índice como substituto (fallback)
                    tabela_html['Posicao_Pura'] = tabela_html.index + 1

                # 1. Cria as colunas de Posição (Balão) e Time (Logo + Nome) em HTML
                tabela_html['#'] = tabela_html.apply(format_position_column_html, axis=1)
                tabela_html['EQUIPE'] = tabela_html.apply(format_team_column_html, axis=1)

                # 2. Seleciona e Renomeia as colunas finais (incluindo as puras para o Styler)
                cols_raw = ['#', 'EQUIPE', 'Pontos', 'Jogos', 'Vitórias', 'Empates', 'Derrotas', 'Gols Pró', 'Gols Contra', 'Time_Puro', 'Posicao_Pura']
                cols_display_names = ["#", "EQUIPE", "Pts", "J", "V", "E", "D", "GP", "GC", "Time_Puro", "Posicao_Pura"]
                
                # Garantir a ordem e existência das colunas
                final_cols_map = dict(zip(cols_raw, cols_display_names))
                cols_to_use = [col for col in cols_raw if col in tabela_html.columns]
                tabela_final = tabela_html[cols_to_use]
                tabela_final.columns = [final_cols_map.get(col, col) for col in cols_to_use]
                
                # 3. APLICA O STYLER USANDO A COLUNA 'Time_Puro'
                styler = tabela_final.style.apply(
                    highlight_match_teams_styler_final, 
                    axis=1, 
                    mandante=mandante, 
                    visitante=visitante
                )
                
                # 4. Remove a coluna 'Time_Puro' e 'Posicao_Pura' antes de renderizar
                styler = styler.hide(subset=['Time_Puro', 'Posicao_Pura'], axis="columns") 
                
                # 5. Adiciona CSS customizado
                css_styles = """
                <style>
                table {
                    background-color: #0e1117; 
                    color: white;
                    border-collapse: collapse;
                }
                th {
                    background-color: #1f2730 !important;
                    color: white;
                    text-align: center; 
                    font-size: 14px;
                }
                /* Garante que a coluna 'EQUIPE' (índice 2) seja alinhada à esquerda */
                th:nth-child(2), td:nth-child(2) {
                    text-align: left !important;
                }
                /* Garante que a primeira coluna (#) e as colunas numéricas (Pts, J, etc) sejam centradas */
                th:nth-child(1), td:nth-child(1), th:nth-child(n+3), td:nth-child(n+3) {
                    text-align: center !important;
                }
                td {
                    border: 1px solid #1f2730;
                    padding: 4px 8px;
                    font-size: 14px;
                    line-height: 25px;
                }
                </style>
                """
                
                # Converte para HTML e remove o índice do Pandas (index=False)
                tabela_html_final = styler.to_html(escape=False, index=False)

                # Renderiza o CSS e o HTML da tabela
                st.markdown(css_styles, unsafe_allow_html=True)
                st.markdown(tabela_html_final, unsafe_allow_html=True)
                
            except Exception as e:
                st.warning(f"Erro ao exibir a tabela estilizada em HTML: {e}. Exibindo classificação padrão.")
                st.dataframe(tabela, use_container_width=True)

            # ==============================================================================
            # BLOCO DE LEGENDA DE CORES (ATUALIZADO COM #1E90FF)
            # ==============================================================================
            st.markdown("---")
            st.markdown("### 🎨 Legenda da Classificação")
            
            col_legenda1, col_legenda2, col_legenda3, col_legenda4 = st.columns(4)
            
            with col_legenda1:
                st.markdown(
                    "<div style='padding: 5px; background-color: #66BB6A; color: black; border-radius: 5px; font-size: 14px;'>🏆 1º ao 4º: **Libertadores (Grupos)**</div>", 
                    unsafe_allow_html=True
                )
            
            with col_legenda2:
                st.markdown(
                    "<div style='padding: 5px; background-color: #007BFF; color: white; border-radius: 5px; font-size: 14px;'>🟦 5º ao 6º: **Libertadores (Qualif.)**</div>", 
                    unsafe_allow_html=True
                )
                
            with col_legenda3:
                st.markdown(
                    "<div style='padding: 5px; background-color: #00BFFF; color: black; border-radius: 5px; font-size: 14px;'>🏅 7º ao 12º: **Sul-Americana**</div>", 
                    unsafe_allow_html=True
                )
            
            with col_legenda4:
                st.markdown(
                    "<div style='padding: 5px; background-color: #EF5350; color: white; border-radius: 5px; font-size: 14px;'>🔻 17º em diante: **Rebaixamento**</div>", 
                    unsafe_allow_html=True
                )
                
            # LEGENDA DO DESTAQUE: AZUL ESCURO (com texto branco para contraste)
            st.markdown(
                "<div style='width: 25%; margin-top: 10px; padding: 5px; background-color: #1E90FF; color: white; border-radius: 5px; font-size: 14px;'>⚽ Destaque: **Time da Partida**</div>", 
                unsafe_allow_html=True
            )

            st.markdown("---")
            # ==============================================================================


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
                            st.markdown(f"*Nome:* {jogador_info.get('name')}")
                            st.markdown(f"*Idade:* {jogador_info.get('age')}")
                            st.markdown(f"*Nacionalidade:* {jogador_info.get('nationality')}")
                            st.markdown(f"*Posição:* {jogador_estatisticas.get('games', {}).get('position')}")
                        
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
                        st.warning("⚠ Estatísticas do jogador não disponíveis para esta temporada/liga.")