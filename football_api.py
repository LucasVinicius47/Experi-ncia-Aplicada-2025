import requests
import pandas as pd
from datetime import datetime

# ========================
# Configuração da API
# ========================
API_KEY = "08fd60ff25a20412131549c50401864f" #chave da API-Football
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

# Dicionário para traduzir estatísticas
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

# ========================
# Ligas disponíveis
# ========================
def get_leagues():
    url = f"{BASE_URL}/leagues"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return []
    data = r.json().get("response", [])
    leagues = []
    for l in data:
        league = l.get("league", {})
        country = l.get("country", {}).get("name", "")
        leagues.append({
            "id": league.get("id"),
            "name": f"{league.get('name')} ({country})"
        })
    return leagues

# ========================
# Jogos por data e liga
# ========================
def get_fixtures_by_date(league_id, date, season):
    url = f"{BASE_URL}/fixtures"
    params = {
        "league": league_id,
        "date": str(date),
        "season": season
    }
    r = requests.get(url, headers=HEADERS, params=params)
    if r.status_code != 200:
        return []
    return r.json().get("response", [])

# ========================
# Estatísticas da partida
# ========================
def get_match_statistics(fixture_id):
    url = f"{BASE_URL}/fixtures/statistics"
    params = {"fixture": fixture_id}
    r = requests.get(url, headers=HEADERS, params=params)
    if r.status_code != 200:
        return []

    stats = r.json().get("response", [])
    if len(stats) != 2:
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

# ========================
# Escalações
# ========================
def get_match_lineups(fixture_id):
    url = f"{BASE_URL}/fixtures/lineups"
    params = {"fixture": fixture_id}
    r = requests.get(url, headers=HEADERS, params=params)
    if r.status_code != 200:
        return []

    lineups = r.json().get("response", [])
    return lineups

# ========================
# Tabela da competição
# ========================
def get_standings(league_id, season):
    url = f"{BASE_URL}/standings"
    params = {"league": league_id, "season": season}
    r = requests.get(url, headers=HEADERS, params=params)
    if r.status_code != 200:
        return pd.DataFrame()

    standings = r.json().get("response", [])
    if not standings:
        return pd.DataFrame()

    table = standings[0].get("league", {}).get("standings", [[]])[0]
    df = pd.DataFrame([{
        "Posição": t.get("rank"),
        "Time": t.get("team", {}).get("name"),
        "Pontos": t.get("points"),
        "Jogos": t.get("all", {}).get("played"),
        "Vitórias": t.get("all", {}).get("win"),
        "Empates": t.get("all", {}).get("draw"),
        "Derrotas": t.get("all", {}).get("lose"),
        "Gols Pró": t.get("all", {}).get("goals", {}).get("for"),
        "Gols Contra": t.get("all", {}).get("goals", {}).get("against"),
    } for t in table])

    return df