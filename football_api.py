import requests
import pandas as pd
from datetime import datetime
import streamlit as st # <-- Importa o Streamlit para usar o cache

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
    # Adicionei xG e Gols Evitados, se a API suportar
    "expected_goals": "Gols Esperados (xG)", 
    "goals_prevented": "Gols Evitados"
}

@st.cache_data(ttl=3600)  # Cache por 1 hora
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

@st.cache_data(ttl=600)  # Cache por 10 minutos
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
                metric_pt = STATS_TRANSLATE.get(metric, metric)
                if metric_pt not in metrics:
                    metrics[metric_pt] = {"Estatística": metric_pt, "Mandante": None, "Visitante": None}
                metrics[metric_pt][side] = val if val not in [None, "null"] else 0
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
# FUNÇÃO ATUALIZADA: Inclui 'Logo URL'
# ====================================================================
@st.cache_data(ttl=3600)  # Cache por 1 hora
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
        
        df = pd.DataFrame([{
            "Posição": t.get("rank"),
            "Time": t.get("team", {}).get("name"),
            "Logo URL": t.get("team", {}).get("logo"),  # <--- NOVA LINHA ADICIONADA
            "Pontos": t.get("points"),
            "Jogos": t.get("all", {}).get("played"),
            "Vitórias": t.get("all", {}).get("win"),
            "Empates": t.get("all", {}).get("draw"),
            "Derrotas": t.get("all", {}).get("lose"),
            "Gols Pró": t.get("all", {}).get("goals", {}).get("for"),
            "Gols Contra": t.get("all", {}).get("goals", {}).get("against"),
        } for t in table])
        
        return df
    except requests.exceptions.RequestException:
        return pd.DataFrame()
# ====================================================================

@st.cache_data(ttl=3600)  # Cache por 1 hora
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
            
            adversario = teams["away"]["name"] if teams["home"]["id"] == team_id else teams["home"]["name"]
            placar = f"{goals['home']} - {goals['away']}"
            
            resultado = "D"
            if teams["home"].get("winner") is True:
                resultado = "W" if teams["home"]["id"] == team_id else "L"
            elif teams["away"].get("winner") is True:
                resultado = "W" if teams["away"]["id"] == team_id else "L"
            
            jogos.append({
                "Data": fixture.get("date", "")[:10],
                "Adversário": adversario,
                "Placar": placar,
                "Resultado": resultado
            })
        return jogos
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_recent_matches_all_seasons(team_id, league_id=None, limit=10):
    temporadas = [datetime.today().year, datetime.today().year - 1, datetime.today().year - 2]
    todos_jogos = []
    for temporada in temporadas:
        jogos = get_last_matches(team_id, season=temporada, league_id=league_id, limit=limit - len(todos_jogos))
        todos_jogos.extend(jogos)
        if len(todos_jogos) >= limit:
            break
    return todos_jogos[:limit]

@st.cache_data(ttl=3600)  # Cache por 1 hora
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
            
            placar = f"{goals['home']} - {goals['away']}"
            mandante = teams.get("home", {}).get("name")
            visitante = teams.get("away", {}).get("name")
            data_jogo = fixture.get("date", "")[:10]
            
            confrontos.append({
                "Data": data_jogo,
                "Mandante": mandante,
                "Visitante": visitante,
                "Placar": placar
            })
        return confrontos
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_teams_by_league(league_id, season):
    url = f"{BASE_URL}/teams"
    params = {"league": league_id, "season": season}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.json().get("response", [])
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_squad_by_team(team_id, season):
    """Busca o elenco de um time em uma temporada específica."""
    url = f"{BASE_URL}/players/squads"
    params = {"team": team_id, "season": season}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        response = r.json().get("response", [])
        return response[0].get("players", []) if response else []
    except requests.exceptions.RequestException:
        return []

@st.cache_data(ttl=3600)  # Cache por 1 hora
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