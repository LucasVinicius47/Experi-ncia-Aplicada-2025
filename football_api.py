# football_api.py
import requests
from datetime import datetime

# Substitua pela sua chave da API
API_KEY = "aa51955e4752267b259885c971933c18"
BASE_URL = "https://api.api-futebol.com.br/v1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}"
}

def get_leagues():
    """
    Retorna todas as ligas disponíveis no plano gratuito.
    """
    url = f"{BASE_URL}/campeonatos"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        data = response.json()
        leagues = {league["name"]: league["id"] for league in data if league.get("status") == "ativa"}
        return leagues
    else:
        print(f"Erro ao buscar ligas: {response.status_code}")
        return {}

def get_fixtures_by_league(league_id):
    """
    Retorna partidas ao vivo e futuras de uma liga específica.
    """
    url = f"{BASE_URL}/partidas?campeonato={league_id}"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        partidas = response.json()
        fixtures = []

        for p in partidas:
            fixture = {
                "home_team": {"name": p.get("home_team", {}).get("nome", "Time A")},
                "away_team": {"name": p.get("away_team", {}).get("nome", "Time B")},
                "score": f"{p.get('placar', {}).get('home', 0)}-{p.get('placar', {}).get('away', 0)}",
                "status": p.get("status", "Futuro"),
                "date": p.get("data", datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
                "home_team_stats": p.get("estatisticas", {}).get("home", 0),
                "away_team_stats": p.get("estatisticas", {}).get("away", 0)
            }
            fixtures.append(fixture)
        return fixtures
    else:
        print(f"Erro ao buscar partidas: {response.status_code}")
        return []

if __name__ == "__main__":
    # Teste rápido
    leagues = get_leagues()
    print("Ligas disponíveis:", leagues)

    if leagues:
        first_league_id = list(leagues.values())[0]
        fixtures = get_fixtures_by_league(first_league_id)
        print("Primeiras partidas:", fixtures[:5])
