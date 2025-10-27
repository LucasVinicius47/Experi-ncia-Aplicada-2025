import requests
import pandas as pd
from datetime import datetime
import streamlit as st 

# Atenção: Você deve substituir "08fd60ff25a20412131549c50401864f"
# pela sua chave de API real se o app não funcionar.
API_KEY = "08fd60ff25a20412131549c50401864f" 
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

STATS_TRANSLATE = {
    "Shots on Goal": "Chutes no Gol",
    "Shots off Goal": "Chutes para Fora",
    "Total Shots": "Chutes Totais",
    "Blocked Shots": "Chutes Bloqueados",
    "Shots insidebox": "Chutes Dentro da Área",
    "Shots outsidebox": "Chutes Fora da Área",
    "Fouls": "Faltas",
    "Corner Kicks": "Escanteios",
    "Offsides": "Impedimentos",
    "Ball Possession": "Posse de Bola",
    "Yellow Cards": "Cartões Amarelos",
    "Red Cards": "Cartões Vermelhos",
    "Goalkeeper Saves": "Defesas do Goleiro",
    "Total passes": "Passes Totais",
    "Passes accurate": "Passes Precisos",
    "Passes %": "Precisão dos Passes",
    "expected_goals": "Gols Esperados (xG)", 
    "goals_prevented": "Gols Evitados"
}

@st.cache_data(ttl=3600) # Cache por 1 hora
def get_leagues():
    url = f"{BASE_URL}/leagues"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json().get("response", [])
        leagues = []
        for l in data:
            league = l.get("league", {})
            country = l.get("country", {}).get("name", "")
            leagues.append({
                "id": league.get("id"),
                "name": f"{league.get('name', 'N/A')} ({country})"
            })
        return leagues
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=600) # Cache por 10 minutos
def get_fixtures_by_date(league_id, date, season):
    url = f"{BASE_URL}/fixtures"
    params = {
        "league": league_id,
        "date": date.strftime("%Y-%m-%d"),
        "season": season
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("response", [])
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=60) # Cache por 1 minuto, para estatísticas em tempo real
def get_match_statistics(fixture_id):
    url = f"{BASE_URL}/fixtures/statistics"
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        stats = r.json().get("response", [])
        if len(stats) < 2:
            return []
        
        home_id = stats[0]["team"]["id"]
        metrics = {}
        for team_stats in stats:
            team_id = team_stats["team"]["id"]
            side = "Mandante" if team_id == home_id else "Visitante"
            for s in team_stats.get("statistics", []):
                metric = s.get("type")
                val = s.get("value")
                
                # Tratamento de valores nulos, vazios ou com '%'
                if val is None or val in ["null", ""]:
                    val = 0
                elif isinstance(val, str) and "%" in val:
                    try:
                        # Remove o '%' e converte para int/float
                        val = int(val.strip().replace('%', '')) 
                    except ValueError:
                        val = 0
                
                metric_pt = STATS_TRANSLATE.get(metric, metric)
                if metric_pt not in metrics:
                    metrics[metric_pt] = {"Estatística": metric_pt, "Mandante": None, "Visitante": None}
                metrics[metric_pt][side] = val
        return list(metrics.values())
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=60) # Cache por 1 minuto
def get_match_lineups(fixture_id):
    url = f"{BASE_URL}/fixtures/lineups"
    params = {"fixture": fixture_id}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("response", [])
    except requests.exceptions.RequestException:
        return []

# ====================================================================
# FUNÇÃO EXISTENTE: Busca a forma (V, E, D) dos últimos jogos
# ====================================================================
@st.cache_data(ttl=3600) 
def get_team_form(team_id, league_id, season, limit=5):
    """
    Busca os resultados (V, E, D) dos últimos N jogos do time para a coluna FORMA.
    """
    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "status": "FT",
        "league": league_id,
        "season": season,
        "last": limit 
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("response", [])
        
        form_results = []
        for item in data:
            teams = item.get("teams", {})
            
            resultado = "E" # Padrão para Empate (Draw)
            
            # Nota: A API usa 'winner': True/False no time, o que simplifica a lógica.
            if teams["home"].get("winner") is True:
                resultado = "V" if teams["home"]["id"] == team_id else "D"
            elif teams["away"].get("winner") is True:
                resultado = "V" if teams["away"]["id"] == team_id else "D"
            
            form_results.append(resultado)

        # Retorna a lista de resultados, reversa para que o mais antigo (último) fique à esquerda no display
        return form_results[::-1] 
    except requests.exceptions.RequestException:
        return []
# ====================================================================

# ====================================================================
# FUNÇÃO CORRIGIDA: Classificação Geral (com 'Forma')
# ====================================================================
@st.cache_data(ttl=3600) # Cache por 1 hora
def get_standings(league_id, season):
    url = f"{BASE_URL}/standings"
    params = {"league": league_id, "season": season}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        standings = r.json().get("response", [])
        if not standings:
            return pd.DataFrame()
        
        table = standings[0].get("league", {}).get("standings", [[]])[0]
        
        data_list = []
        for t in table:
            team_id = t.get("team", {}).get("id")
            # CHAMADA PARA PEGAR A FORMA
            team_form = get_team_form(team_id, league_id, season, limit=5)
            
            # CORREÇÃO: Usa o bloco 'all' para Jogos e Gols. Pontos é nível superior.
            all_stats = t.get("all", {})
            
            data_list.append({
                "Posição": t.get("rank"),
                "Time": t.get("team", {}).get("name"),
                "Logo URL": t.get("team", {}).get("logo"),
                "Pontos": t.get("points"), # Pontos geralmente está no nível superior
                "Jogos": all_stats.get("played"),
                "Vitórias": all_stats.get("win"),
                "Empates": all_stats.get("draw"),
                "Derrotas": all_stats.get("lose"),
                "Gols Pró": all_stats.get("goals", {}).get("for"),
                "Gols Contra": all_stats.get("goals", {}).get("against"),
                "Forma": team_form 
            })
            
        return pd.DataFrame(data_list)
    except requests.exceptions.RequestException:
        return pd.DataFrame()
# ====================================================================

# ====================================================================
# FUNÇÃO CORRIGIDA: Classificação por Lado (Casa ou Fora)
# ====================================================================
@st.cache_data(ttl=3600) # Cache por 1 hora
def get_standings_by_side(league_id, season, side="home"):
    """
    Busca a classificação de uma liga filtrada por jogos em 'home' (casa) ou 'away' (fora).
    """
    url = f"{BASE_URL}/standings"
    params = {"league": league_id, "season": season}
    
    if side not in ["home", "away"]:
        raise ValueError("O parâmetro 'side' deve ser 'home' ou 'away'.")
        
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        standings = r.json().get("response", [])
        if not standings:
            return pd.DataFrame()
        
        table = standings[0].get("league", {}).get("standings", [[]])[0]
        
        data_list = []
        for t in table:
            # Seleciona o bloco de estatísticas: 'home' ou 'away'
            stats_block = t.get(side, {}) 

            # Garante que as estatísticas do bloco existem para evitar falha
            if not stats_block:
                 continue

            data_list.append({
                "Time": t.get("team", {}).get("name"),
                "Logo URL": t.get("team", {}).get("logo"),
                # CORREÇÃO: Pontos são CALCULADOS: (V * 3) + E
                "Pontos": (stats_block.get("win", 0) * 3) + stats_block.get("draw", 0),
                "Jogos": stats_block.get("played"),
                "Vitórias": stats_block.get("win"),
                "Empates": stats_block.get("draw"),
                "Derrotas": stats_block.get("lose"),
                "Gols Pró": stats_block.get("goals", {}).get("for"),
                "Gols Contra": stats_block.get("goals", {}).get("against"),
            })
        
        df = pd.DataFrame(data_list)
        
        if not df.empty:
            # 1. Classifica a tabela
            df['Saldo de Gols'] = df['Gols Pró'] - df['Gols Contra']
            df = df.sort_values(
                by=["Pontos", "Saldo de Gols", "Gols Pró"], 
                ascending=[False, False, False]
            ).reset_index(drop=True)
            
            # Remove a coluna auxiliar
            df = df.drop(columns=['Saldo de Gols'])
            
            # 2. Atribui uma nova posição (rank) baseada na classificação específica
            df.insert(0, "Posição", df.index + 1)

        return df
    except requests.exceptions.RequestException:
        return pd.DataFrame()
# ====================================================================


@st.cache_data(ttl=3600) # Cache por 1 hora
def get_last_matches(team_id, season=None, league_id=None, limit=5):
    url = f"{BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "status": "FT",
        "season": season if season else datetime.today().year,
        "last": limit 
    }
    if league_id:
        params["league"] = league_id
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("response", [])
        jogos = []
        for item in data:
            fixture = item.get("fixture", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})
            if not fixture or not teams or not goals:
                continue
            
            # Tratamento para data no formato DD/MM/AAAA
            date_str = fixture.get("date")
            data_jogo = datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%d/%m/%Y") 
            
            adversario = teams["away"]["name"] if teams["home"]["id"] == team_id else teams["home"]["name"]
            placar = f"{goals['home']} - {goals['away']}"
            
            resultado = "D"
            if teams["home"].get("winner") is True:
                resultado = "W" if teams["home"]["id"] == team_id else "L"
            elif teams["away"].get("winner") is True:
                resultado = "W" if teams["away"]["id"] == team_id else "L"
            
            jogos.append({
                "Data": data_jogo, # Data formatada
                "Adversário": adversario,
                "Placar": placar,
                "Resultado": resultado
            })
        return jogos
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600) # Cache por 1 hora
def get_recent_matches_all_seasons(team_id, league_id=None, limit=10):
    temporadas = [datetime.today().year, datetime.today().year - 1, datetime.today().year - 2]
    todos_jogos = []
    for temporada in temporadas:
        # Pede apenas o número de jogos restante até o limite
        jogos = get_last_matches(team_id, season=temporada, league_id=league_id, limit=limit - len(todos_jogos))
        todos_jogos.extend(jogos)
        if len(todos_jogos) >= limit:
            break
    return todos_jogos[:limit]

@st.cache_data(ttl=3600) # Cache por 1 hora
def get_head_to_head(team1_id, team2_id, limit=10):
    url = f"{BASE_URL}/fixtures/headtohead"
    params = {
        "h2h": f"{team1_id}-{team2_id}",
        "status": "FT"
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("response", [])[:limit]
        confrontos = []
        for item in data:
            fixture = item.get("fixture", {})
            teams = item.get("teams", {})
            goals = item.get("goals", {})
            if not fixture or not teams or not goals:
                continue
            
            # Tratamento para data no formato DD/MM/AAAA
            date_str = fixture.get("date")
            data_jogo = datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            
            placar = f"{goals['home']} - {goals['away']}"
            mandante = teams.get("home", {}).get("name")
            visitante = teams.get("away", {}).get("name")
            
            confrontos.append({
                "Data": data_jogo, # Data formatada
                "Mandante": mandante,
                "Visitante": visitante,
                "Placar": placar
            })
        return confrontos
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600) # Cache por 1 hora
def get_teams_by_league(league_id, season):
    url = f"{BASE_URL}/teams"
    params = {"league": league_id, "season": season}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("response", [])
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600) # Cache por 1 hora
def get_squad_by_team(team_id, season):
    """Busca o elenco de um time em uma temporada específica."""
    url = f"{BASE_URL}/players/squads"
    params = {"team": team_id, "season": season}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        response = r.json().get("response", [])
        return response[0].get("players", []) if response and response[0].get("players") else []
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600) # Cache por 1 hora
def get_player_stats(player_id, season, league_id):
    """Busca estatísticas detalhadas de um jogador em uma temporada e liga."""
    url = f"{BASE_URL}/players"
    params = {"id": player_id, "season": season, "league": league_id}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        response = r.json().get("response", [])
        return response[0] if response else None
    except requests.exceptions.RequestException:
        return None