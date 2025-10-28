import re
import logging
from typing import Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

def safe_get_standings(raw_get_standings, *args, **kwargs) -> Optional[Any]:
    try:
        return raw_get_standings(*args, **kwargs)
    except TypeError:
        try:
            if len(args) >= 1:
                return raw_get_standings(args[0])
        except Exception:
            logger.exception("Falha no fallback de get_standings")
            return None
    except Exception:
        logger.exception("Erro inesperado em get_standings")
        return None

def safe_get_standings_by_side(raw_get_standings_by_side, *args, **kwargs) -> Optional[Any]:
    try:
        return raw_get_standings_by_side(*args, **kwargs)
    except TypeError:
        try:
            if len(args) >= 2:
                return raw_get_standings_by_side(args[0], args[1])
            if len(args) >= 1:
                return raw_get_standings_by_side(args[0])
        except Exception:
            logger.exception("Falha no fallback de get_standings_by_side")
            return None
    except Exception:
        logger.exception("Erro inesperado em get_standings_by_side")
        return None

def normalize_standings_df(df: Any) -> Optional[pd.DataFrame]:
    if df is None:
        return None
    try:
        if isinstance(df, list):
            df = pd.DataFrame(df)
        if not hasattr(df, 'columns'):
            return df

        mapping = {
            'team': 'Time', 'name': 'Time', 'team_name': 'Time',
            'logo': 'Logo URL', 'logo_url': 'Logo URL', 'team_logo': 'Logo URL',
            'form': 'Forma', 'forma': 'Forma',
            'points': 'Pontos', 'pts': 'Pontos',
            'played': 'Jogos', 'games': 'Jogos',
            'wins': 'Vitórias', 'win': 'Vitórias',
            'draws': 'Empates', 'draw': 'Empates',
            'losses': 'Derrotas', 'loss': 'Derrotas',
            'goals_for': 'Gols Pró', 'gf': 'Gols Pró',
            'goals_against': 'Gols Contra', 'ga': 'Gols Contra',
            'position': 'Posição', 'pos': 'Posição', 'posição': 'Posição'
        }

        rename_map = {}
        for col in list(df.columns):
            lower = col.lower()
            if lower in mapping:
                rename_map[col] = mapping[lower]
        if rename_map:
            df = df.rename(columns=rename_map)

        if 'Time' in df.columns and df['Time'].apply(lambda x: isinstance(x, dict)).any():
            def extract_name(val):
                if isinstance(val, dict):
                    if 'name' in val and isinstance(val['name'], str):
                        return val['name']
                    if 'team' in val and isinstance(val['team'], dict):
                        return val['team'].get('name', str(val))
                    for v in val.values():
                        if isinstance(v, str):
                            return v
                return str(val)
            df['Time'] = df['Time'].apply(extract_name)

        if 'Logo URL' not in df.columns:
            for col in df.columns:
                if 'logo' in col.lower() or 'badge' in col.lower():
                    df = df.rename(columns={col: 'Logo URL'})
                    break

        if 'Forma' in df.columns:
            def parse_form(cell):
                if cell is None:
                    return []
                if isinstance(cell, list):
                    return [str(x).upper()[:1] for x in cell if x]
                s = str(cell).strip().upper()
                found = re.findall(r'[VED]', s)
                if found:
                    return found
                parts = re.split(r'[\s,;|/-]+', s)
                return [p[0] for p in parts if p]
            df['Forma'] = df['Forma'].apply(parse_form)
        else:
            df['Forma'] = [[] for _ in range(len(df))]

        if 'Posição' in df.columns:
            def to_int(x):
                try:
                    return int(x)
                except Exception:
                    return None
            df['Posição'] = df['Posição'].apply(to_int)

        return df
    except Exception:
        logger.exception("Erro ao normalizar standings")
        return df