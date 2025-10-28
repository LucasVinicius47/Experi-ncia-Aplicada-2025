import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go
import plotly.express as px
import re
import logging
from typing import Any, Optional

# NOTE: Certifique-se de que o arquivo 'football_api.py' existe e está no mesmo diretório.
# O código assume que as funções de API estão em 'football_api.py'
from football_api import (
    get_leagues,
    get_fixtures_by_date,
    get_match_statistics,
    get_match_lineups,
    get_standings,
    get_standings_by_side, 
    get_last_matches,
    get_recent_matches_all_seasons,
    get_head_to_head,
    get_teams_by_league,
    get_squad_by_team,
    get_player_stats,
)
from utills import normalize_standings_df, safe_get_standings, safe_get_standings_by_side

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- CACHES E WRAPPERS SEGUROS -----------------
@st.cache_data(ttl=60)
def cached_get_leagues():
    try:
        return get_leagues()
    except Exception as e:
        logger.exception("Erro em get_leagues")
        return []

@st.cache_data(ttl=60)
def cached_get_standings_safe(*args, **kwargs):
    """
    Tenta chamar get_standings com assinatura de 1 ou 2 argumentos.
    Retorna DataFrame-like (lista/dict) ou None.
    """
    try:
        return get_standings(*args, **kwargs)
    except TypeError:
        try:
            # fallback para versões que aceitam apenas liga_id
            if len(args) >= 1:
                return get_standings(args[0])
            # talvez temporada seja passada como kwarg diferente
            if 'league_id' in kwargs:
                return get_standings(kwargs['league_id'])
        except Exception:
            logger.exception("Falha no fallback de get_standings")
            return None
    except Exception:
        logger.exception("Erro inesperado em get_standings")
        return None

@st.cache_data(ttl=60)
def cached_get_standings_by_side_safe(*args, **kwargs):
    try:
        return get_standings_by_side(*args, **kwargs)
    except TypeError:
        try:
            # tenta chamadas alternativas comuns
            if len(args) >= 2:
                # (liga_id, temporada, side=...)
                return get_standings_by_side(args[0], args[1])
            if len(args) >= 1:
                return get_standings_by_side(args[0])
        except Exception:
            logger.exception("Falha no fallback de get_standings_by_side")
            return None
    except Exception:
        logger.exception("Erro inesperado em get_standings_by_side")
        return None

# ----------------- NORMALIZAÇÃO DA TABELA -----------------
def normalize_standings_df(df: Any) -> Optional[Any]:
    """
    Normaliza nomes de colunas e a coluna 'Forma' para lista de letras ['V','E','D'].
    Aceita list/dict/DataFrame; retorna DataFrame quando aplicável.
    """
    if df is None:
        return None
    try:
        # Se for lista de dicts, transforma em DataFrame
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
            'goals_for': 'Gols Pró', 'gf': 'Gols Pró', 'for': 'Gols Pró',
            'goals_against': 'Gols Contra', 'ga': 'Gols Contra', 'against': 'Gols Contra',
            'position': 'Posição', 'pos': 'Posição', 'posição': 'Posição'
        }

        rename_map = {}
        for col in list(df.columns):
            lower = col.lower()
            if lower in mapping:
                rename_map[col] = mapping[lower]
        if rename_map:
            df = df.rename(columns=rename_map)

        # Se 'Time' for objeto/dict, tenta extrair nome e logo
        if 'Time' in df.columns:
            if df['Time'].apply(lambda x: isinstance(x, dict)).any():
                def extract_name(val):
                    if isinstance(val, dict):
                        # estruturas comuns: {'team': {'name':...}} ou {'name':..., 'logo':...}
                        if 'name' in val and isinstance(val['name'], str):
                            return val['name']
                        if 'team' in val and isinstance(val['team'], dict):
                            return val['team'].get('name', str(val))
                        # ultimo recurso
                        for v in val.values():
                            if isinstance(v, str):
                                return v
                    return str(val)
                df['Time'] = df['Time'].apply(extract_name)

        # Tenta extrair logo de colunas com "logo" no nome
        if 'Logo URL' not in df.columns:
            for col in df.columns:
                if 'logo' in col.lower() or 'badge' in col.lower():
                    df = df.rename(columns={col: 'Logo URL'})
                    break
            else:
                # procura dentro de estruturas em 'Time' para logo
                if 'Time' in df.columns and df['Time'].apply(lambda x: isinstance(x, dict)).any():
                    def extract_logo(val):
                        if isinstance(val, dict):
                            for k in ('logo', 'photo', 'image'):
                                if k in val and isinstance(val[k], str):
                                    return val[k]
                            if 'team' in val and isinstance(val['team'], dict):
                                return val['team'].get('logo')
                        return None
                    df['Logo URL'] = df.get('Logo URL', df['Time'].apply(extract_logo))

        # Normaliza Forma -> lista ['V','E','D']
        if 'Forma' in df.columns:
            def parse_form(cell):
                if cell is None:
                    return []
                if isinstance(cell, list):
                    return [str(x).upper()[:1] for x in cell if x]
                s = str(cell).strip().upper()
                # extrai V, E, D
                found = re.findall(r'[VED]', s)
                if found:
                    return found
                # separadores comuns
                parts = re.split(r'[\s,;|/-]+', s)
                res = []
                for p in parts:
                    if p:
                        res.append(p[0])
                return res
            df['Forma'] = df['Forma'].apply(parse_form)
        else:
            df['Forma'] = [[] for _ in range(len(df))]

        # garante Posicão numérica se existir
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
# === FUNÇÃO DE VISUALIZAÇÃO DE DADOS (GRÁFICO ESTILO FINAL) ===
# =================================================================
def create_comparison_chart(stats_df, mandante, visitante, list_of_stats, title):
    """
    Cria um Gráfico de Barras Horizontal de Comparação (Pyramid Chart). 
    """
    if stats_df is None or stats_df.empty:
        return None

    if 'Estatística' not in stats_df.columns or 'Mandante' not in stats_df.columns or 'Visitante' not in stats_df.columns:
        return None 
    
    # Prepara o DataFrame para plotagem
    df_plot = stats_df.rename(columns={
        'Mandante': 'Mandante_Valor', 
        'Visitante': 'Visitante_Valor'
    }).copy()
    
    # 🚨 FILTRAGEM: APLICA O FILTRO DAS ESTATÍSTICAS DESEJADAS
    df_plot = df_plot[df_plot['Estatística'].isin(list_of_stats)].copy()

    # 🚨 ETAPA DE ROBUSTEZ: Limpeza e Conversão para Números
    for col in ['Mandante_Valor', 'Visitante_Valor']:
        # Remove o '%' se existir para a conversão numérica
        df_plot[col] = df_plot[col].astype(str).str.replace('%', '', regex=False)
        df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
        
    df_plot.dropna(subset=['Mandante_Valor', 'Visitante_Valor'], how='all', inplace=True)

    if df_plot.empty:
        return None
        
    # 1. Transformar os dados para o formato longo (melt)
    df_long = df_plot.melt(
        id_vars='Estatística',
        value_vars=['Mandante_Valor', 'Visitante_Valor'],
        var_name='Time_Aux',
        value_name='Valor_Original'
    )
    
    # Adicionar o nome do time real
    df_long['Time'] = df_long['Time_Aux'].apply(lambda x: mandante if 'Mandante' in x else visitante)

    # 2. Ajustar o valor do Mandante para ser negativo (para o gráfico pirâmide)
    df_long['Valor_Ajustado'] = df_long.apply(
        lambda row: -row['Valor_Original'] if row['Time'] == mandante else row['Valor_Original'],
        axis=1
    )
    
    if df_long['Valor_Ajustado'].abs().sum() == 0:
        return None 

    # 3. Criar o gráfico base
    try:
        # Altura mantida em 70 pixels por item (V7) para espaçamento vertical
        fig = px.bar(
            df_long,
            y='Estatística',
            x='Valor_Ajustado',
            color='Time',
            orientation='h',
            # CORES ESTILIZADAS: Mandante (Vermelho) e Visitante (Branco)
            color_discrete_map={mandante: '#EF5350', visitante: 'white'}, 
            text_auto=False,
            # Altura por item: 70 pixels. 
            height=df_plot.shape[0] * 70 + 100 
        )
    except Exception as e:
        return None


    # 4. CONFIGURAÇÕES DE LAYOUT (Estilo limpo com Eixo Y oculto)
    
    # Fator de Espaçamento Horizontal (para os números laterais)
    x_offset_factor = 1.05 

    # Calcula o máximo absoluto para definir o range
    abs_max_plot = df_long['Valor_Ajustado'].abs().max() * 1.1 
    
    # Range do Eixo X com margem (1.25 * abs_max) para garantir que as anotações laterais fiquem visíveis.
    x_range_max = abs_max_plot * 1.25 
    
    # Configurações de Layout
    fig.update_layout(
        bargap=0, 
        xaxis=dict(
            showticklabels=False,  
            showgrid=False,        
            title="",              
            range=[-x_range_max, x_range_max] 
        ),
        yaxis=dict(
            showticklabels=False,  
            title="",              
            showgrid=False
        ),
        legend=dict(
            orientation="h",       
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        legend_title_text='Time',
        title_text=f'Comparativo de Estatísticas: {title}', 
        plot_bgcolor='rgba(0,0,0,0)', 
        paper_bgcolor='#0e1117',
        font_color='white'
    )
    
    # Reduz a largura da barra (width)
    fig.update_traces(textposition='none', width=0.3) 
    
    # 5. ADICIONAR ANOTAÇÕES LATERAIS E CENTRAIS (O visual final)
    annotations = []
    
    # Obtém a lista de estatísticas na ordem plotada para iterar corretamente o eixo Y
    y_order = df_long['Estatística'].unique()
    
    # Aumentar ligeiramente o offset vertical (0.1 garante que o rótulo comece 
    # ligeiramente acima do ponto 'bottom' da categoria)
    y_offset = 0.1 

    for i, estatistica in enumerate(y_order):
        # Encontra os valores de mandante e visitante para essa estatística
        val_mandante = df_long[(df_long['Estatística'] == estatistica) & (df_long['Time'] == mandante)]['Valor_Original'].iloc[0] if not df_long[(df_long['Estatística'] == estatistica) & (df_long['Time'] == mandante)].empty else 0
        val_visitante = df_long[(df_long['Estatística'] == estatistica) & (df_long['Time'] == visitante)]['Valor_Original'].iloc[0] if not df_long[(df_long['Estatística'] == estatistica) & (df_long['Time'] == visitante)].empty else 0
        
        # Define a formatação (inteiro ou float)
        def format_value(val, stat_name):
            if val is None:
                return "0"
                
            # Adiciona o '%' à posse de bola e Precisão dos Passes
            if stat_name in ["Posse de Bola", "Precisão dos Passes"]:
                return f"{int(val)}%" if isinstance(val, (int, float)) and val == round(val) else f"{val:.0f}%"
                
            # Formatação especial para Passes (Valores altos, sem %)
            if stat_name in ["Passes Totais", "Passes Precisos"]:
                return f"{int(val)}" if isinstance(val, (int, float)) and val == round(val) else f"{val:.0f}"
                
            # Formatação para Gols Esperados (xG) ou rating (float)
            if isinstance(val, float) and val != round(val):
                return f"{val:.2f}"
            
            # Padrão para inteiros
            return f"{val:.0f}"

        text_mandante = format_value(val_mandante, estatistica)
        text_visitante = format_value(val_visitante, estatistica)
        
        # Plotly usa o nome da categoria como coordenada Y.
        y_coord_nome = estatistica
        
        # A) Anotação do Mandante (Esquerda - Valor)
        annotations.append(dict(
            x=-abs_max_plot * x_offset_factor,  
            y=y_coord_nome,                     
            text=text_mandante,
            showarrow=False,
            font=dict(color='white', size=16), 
            xanchor='left',            
            yanchor='middle' 
        ))

        # B) Anotação do Visitante (Direita - Valor)
        annotations.append(dict(
            x=abs_max_plot * x_offset_factor,  
            y=y_coord_nome,                     
            text=text_visitante,
            showarrow=False,
            font=dict(color='white', size=16), 
            xanchor='right',         
            yanchor='middle' 
        ))

        # C) Anotação Central (Nome da Estatística - FLUTUANDO BEM ACIMA)
        annotations.append(dict(
            x=0,                     
            text=estatistica,
            showarrow=False,
            font=dict(color='white', size=16), 
            xanchor='center',
            yanchor='bottom',
            yref='y', # Usa o índice para posicionamento relativo
            y=i + y_offset 
        ))

    fig.update_layout(annotations=annotations)
    
    return fig


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
    # Mantemos o balão para a Posição, que geralmente funciona bem.
    style = f"background-color: {background_color}; color: {text_color}; border-radius: 50%; width: 25px; height: 25px; line-height: 25px; text-align: center; font-weight: bold; margin: auto; display: block;"
    
    # Retorna o HTML com o balão (div wrapper)
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


# 🚨 FUNÇÃO REVERTIDA: Retorna o HTML do balão circular com cores
def format_form_column_html(row):
    """
    Gera a coluna 'Forma' como uma série de balões HTML coloridos.
    """
    form_list = row.get('Forma', []) 
    
    html_output = '<div style="display: flex; gap: 4px; justify-content: center; align-items: center;">' # Flex container

    for result in form_list:
        res = str(result).upper()
        
        background_color = ""
        text_color = ""
        
        if res == 'V':
            # Vitória (Verde)
            background_color = "#4CAF50"  
            text_color = "white"
        elif res == 'E':
            # Empate (Amarelo)
            background_color = "#FFEB3B"  
            text_color = "black"
        elif res == 'D':
            # Derrota (Vermelho)
            background_color = "#F44336"  
            text_color = "white"
        else:
            # Padrão
            background_color = "#E0E0E0"
            text_color = "black"

        # CSS do Balão (Circular) - INLINE
        style = f"""
        background-color: {background_color}; 
        color: {text_color}; 
        border-radius: 50%; 
        width: 25px; 
        height: 25px; 
        line-height: 25px; 
        text-align: center; 
        font-weight: bold; 
        flex-shrink: 0;
        """
        
        html_output += f'<span style="{style}">{res}</span>'

    html_output += '</div>'
    return html_output

# FUNÇÃO DE DESTAQUE CORRIGIDA E ROBUSTA
def highlight_match_teams_styler_final(row, mandante, visitante):
    """
    Aplica destaque AZUL ESCURO na linha se for um dos times da partida,
    usando a coluna 'Time_Puro' para comparação.
    """
    # A coluna 'Time_Puro' é mantida no DataFrame interno do Styler
    if row.get('Time_Puro') in [mandante, visitante]:
        # COR NOVA: Azul Escuro (#1E90FF)
        return ['background-color: #1E90FF; color: white'] * len(row)
    # Retorna uma lista de strings vazias para células não destacadas
    return [''] * len(row)

# =================================================================
# === FUNÇÃO AUXILIAR PARA EXIBIR A TABELA ESTILIZADA ===
# =================================================================

def display_styled_table(df, mandante, visitante, title="Classificação"):
    """
    Exibe uma tabela de classificação estilizada (para Casa/Fora),
    sendo robusta a DataFrames vazios ou None.
    """
    # 🚨 VERIFICAÇÃO DE ROBUSTEZ ADICIONAL
    if df is None or df.empty:
        st.info(f"ℹ {title} não disponível.")
        return
        
    try:
        tabela_html = df.copy()
        
        # Verifica as colunas essenciais
        if 'Time' not in tabela_html.columns or 'Logo URL' not in tabela_html.columns:
            st.warning(f"⚠ Colunas essenciais ('Time', 'Logo URL') não encontradas em {title}. Exibindo classificação padrão.")
            st.dataframe(df, use_container_width=True)
            return

        # CRIA COLUNAS PURAS (necessário para highlight e posição)
        tabela_html['Time_Puro'] = tabela_html['Time'] 
        if 'Posição' in tabela_html.columns:
            tabela_html['Posicao_Pura'] = tabela_html['Posição']
            tabela_html = tabela_html.drop(columns=['Posição']) # Removes the original column to use the balloon
        else:
            # Caso a API não retorne a coluna 'Posição' (como no caso de Casa/Fora)
            tabela_html['Posicao_Pura'] = tabela_html.index + 1
            
        
        # 1. Aplica a estilização HTML para Posição e Time
        tabela_html['#'] = tabela_html.apply(format_position_column_html, axis=1) # Reutiliza a função de balão colorido
        tabela_html['EQUIPE'] = tabela_html.apply(format_team_column_html, axis=1) # Reutiliza a função de logo e nome
        
        # 2. Define colunas finais para exibição (sem a 'Forma' que só existe na Geral)
        # A ordem deve ser estrita: Posição, Nome, Pts, J, V, E, D, GP, GC
        cols_raw = ['#', 'EQUIPE', 'Pontos', 'Jogos', 'Vitórias', 'Empates', 'Derrotas', 'Gols Pró', 'Gols Contra', 'Time_Puro', 'Posicao_Pura']
        cols_display_names = ["#", "EQUIPE", "Pts", "J", "V", "E", "D", "GP", "GC", "Time_Puro", "Posicao_Pura"]
        
        final_cols_map = dict(zip(cols_raw, cols_display_names))
        # Filtra as colunas que realmente existem no DataFrame
        cols_to_use = [col for col in cols_raw if col in tabela_html.columns]
        tabela_final = tabela_html[cols_to_use]
        tabela_final.columns = [final_cols_map.get(col, col) for col in cols_to_use]
        
        # 3. APLICA O STYLER (destaque de linha)
        styler = tabela_final.style.apply(
            highlight_match_teams_styler_final, 
            axis=1, 
            mandante=mandante, 
            visitante=visitante
        )
        
        # 4. Remove colunas auxiliares
        styler = styler.hide(subset=['Time_Puro', 'Posicao_Pura'], axis="columns") 
        
        # 5. Renderiza
        # ADICIONA CSS (Global para a tabela)
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
        th:nth-child(2), td:nth-child(2) {
            text-align: left !important;
        }
        /* Alinhamento de todas as células de dados (exceto a de nome) */
        th:nth-child(1), td:nth-child(1), th:nth-child(n+3), td:nth-child(n+3) {
            text-align: center !important;
        }
        td {
            border: 1px solid #1f2730;
            padding: 4px 8px;
            font-size: 14px;
            line-height: 25px; 
        }
        
        /* Regra para garantir o alinhamento central */
        .stDataFrame table td > div {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            height: 100% !important;
        }

        </style>
        """
        st.markdown(css_styles, unsafe_allow_html=True)
        tabela_html_final = styler.to_html(escape=False, index=False)
        st.markdown(tabela_html_final, unsafe_allow_html=True)

    except Exception as e:
        # 🚨 Captura o erro e mostra a tabela padrão como fallback
        st.warning(f"Erro ao exibir a {title} estilizada: {e}. Exibindo classificação padrão.")
        st.dataframe(df, use_container_width=True)


# =================================================================
# === BLOCO DE PROTEÇÃO DO DASHBOARD (INÍCIO DA UI) ===
# =================================================================

# --- MOCK DE AUTENTICAÇÃO ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = True
    st.session_state['user_email'] = 'teste@teste.com'
    
if st.session_state['logged_in']: # MOCK DE LOGIN
    
    st.set_page_config(page_title="⚽ Dash Gol", layout="wide")
    st.title("⚽ Dash Gol")
    
    # Adiciona o botão de Sair (se estiver usando login)
    if st.sidebar.button("Sair", key="logout_btn"):
        st.session_state['logged_in'] = False
        st.session_state['mode'] = 'login'
        st.rerun()
        
    st.sidebar.success(f"Logado como: {st.session_state.get('user_email', 'Usuário Mock')}") 
    
    # Sidebar
    st.sidebar.header("📌 Filtros")
    
    # Slider para o Autorefresh
    refresh_interval = st.sidebar.slider("⏱ Atualizar a cada (segundos)", 15, 120, 30)
    st_autorefresh(interval=refresh_interval * 1000, key="refresh_app")

    ligas_df = pd.DataFrame(cached_get_leagues())
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
                        st.markdown(f"- {jogo['Data']} vs {jogo['Adversário']} | Placar: {jogo['Placar']} | Resultado: {jogo['Resultado']}")
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
        st.markdown(f"{mandante}")
        exibir_jogos_com_emoji(jogos_mandante, mandante)
    with col2:
        st.markdown(f"{visitante}")
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

    # Gráfico de desempenho (Vitórias, Empates, Derrotas)
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
        go.Bar(name=mandante, x=["Vitórias", "Empates", "Derrotas"], y=[v1, e1, d1], marker_color='#EF5350'), # Vermelho (Mandante)
        go.Bar(name=visitante, x=["Vitórias", "Empates", "Derrotas"], y=[v2, e2, d2], marker_color='white') # Branco (Visitante)
    ])
    fig.update_layout(title="Desempenho nos últimos jogos", barmode='group', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='#0e1117', font_color='white')
    st.plotly_chart(fig, use_container_width=True)

    # Abas
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Estatísticas", "👕 Escalações", "🏆 Classificação", "👨‍選手 Análise de Jogador"])

    # ==============================================================================
    # TAB 1: ESTATÍSTICAS
    # ==============================================================================
    with tab1:
        st.subheader("📊 Estatísticas da Partida")
        
        stats_data = get_match_statistics(fixture_id)
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
        else:
            stats_df = pd.DataFrame() 

        if stats_df.empty:
            st.info("ℹ Estatísticas não disponíveis.")
        else:
            # GRUPO 1: CONTADORES (Ofensa, Posse, Defesa/Disciplina)
            stats_contadores = [
                "Gols Esperados (xG)",
                "Chutes Totais",
                "Chutes no Gol",
                "Chutes para Fora",
                "Chutes Bloqueados",
                "Chutes Dentro da Área",
                "Chutes Fora da Área",
                "Escanteios",
                "Posse de Bola", 
                "Impedimentos",
                "Faltas",
                "Cartões Amarelos",
                "Cartões Vermelhos",
                "Defesas do Goleiro",
                "Gols Evitados"
            ]
            
            # GRUPO 2: VOLUME (Passes)
            stats_volume = [
                "Passes Totais", 
                "Passes Precisos", 
                "Precisão dos Passes"
            ]
            
            
            # --- PLOTAGEM DO GRÁFICO 1: CONTADORES ---
            st.markdown("### Contadores e Eficiência (Ataque, Posse e Defesa)")
            comparison_fig_contadores = create_comparison_chart(
                stats_df, mandante, visitante, 
                list_of_stats=stats_contadores, 
                title="Ataque, Posse e Defesa" 
            )
            
            if comparison_fig_contadores:
                st.plotly_chart(comparison_fig_contadores, use_container_width=True)
            
            st.markdown("---") 

            # --- PLOTAGEM DO GRÁFICO 2: VOLUME ---
            st.markdown("### Estatísticas de Volume (Passes)")
            comparison_fig_volume = create_comparison_chart(
                stats_df, mandante, visitante, 
                list_of_stats=stats_volume, 
                title="Passes"
            )
            
            if comparison_fig_volume:
                st.plotly_chart(comparison_fig_volume, use_container_width=True)
            
            
            # Fallback final
            if not comparison_fig_contadores and not comparison_fig_volume:
                st.info("ℹ Não foi possível gerar os gráficos de comparação. Exibindo tabela de dados brutos.")
                st.dataframe(stats_df, use_container_width=True)


    with tab2:
        st.subheader("👕 Escalações")
        lineups = get_match_lineups(fixture_id)
        if not lineups:
            st.info("ℹ Escalações não disponíveis.")
        else:
            for equipe in lineups:
                st.markdown(f"{equipe['team']['name']}")
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
    # TAB 3: CLASSIFICAÇÃO
    # ==============================================================================
    with tab3:
        st.subheader("🏆 Classificação da Liga")
        
        # 1. Busca as três tabelas
        tabela_geral = cached_get_standings_safe(liga_id, temporada)
        tabela_casa = cached_get_standings_by_side_safe(liga_id, temporada, side="home")
        tabela_fora = cached_get_standings_by_side_safe(liga_id, temporada, side="away")
        
        # Normaliza os dataframes/estruturas retornadas pela API
        tabela_geral = normalize_standings_df(tabela_geral) if tabela_geral is not None else None
        tabela_casa = normalize_standings_df(tabela_casa) if tabela_casa is not None else None
        tabela_fora = normalize_standings_df(tabela_fora) if tabela_fora is not None else None
        
        # 2. Cria as abas de navegação
        tab_geral, tab_home, tab_away = st.tabs(["Geral", "Em Casa", "Fora"])

        with tab_geral:
            st.subheader("Classificação Geral")
            
            # Bloco de código ORIGINAL para Tabela GERAL (com a coluna FORMA)
            if tabela_geral is None or tabela_geral.empty: 
                st.warning("⚠ Classificação Geral não disponível para esta liga/temporada.")
            elif 'Logo URL' not in tabela_geral.columns or 'Forma' not in tabela_geral.columns:
                st.warning("⚠ Colunas essenciais faltando (Logo URL ou Forma). Exibindo classificação padrão.")
                st.dataframe(tabela_geral, use_container_width=True) 
            else:
                try:
                    tabela_html = tabela_geral.copy()
                    
                    # CRIA COLUNAS PURAS para o Styler usar na lógica
                    tabela_html['Time_Puro'] = tabela_html['Time'] 
                    if 'Posição' in tabela_html.columns:
                        tabela_html['Posicao_Pura'] = tabela_html['Posição']
                        tabela_html = tabela_html.drop(columns=['Posição']) 
                    else:
                        tabela_html['Posicao_Pura'] = tabela_html.index + 1

                    # Aplica as 3 funções de formatação HTML
                    tabela_html['#'] = tabela_html.apply(format_position_column_html, axis=1)
                    tabela_html['EQUIPE'] = tabela_html.apply(format_team_column_html, axis=1)
                    
                    # 🚨 NOVO/REVERTIDO: Formata a coluna 'Forma' para retornar o HTML com os balões
                    tabela_html['FORMA'] = tabela_html.apply(format_form_column_html, axis=1) 

                    # Seleciona e Renomeia as colunas finais
                    cols_raw = ['#', 'EQUIPE', 'Pontos', 'Jogos', 'Vitórias', 'Empates', 'Derrotas', 'Gols Pró', 'Gols Contra', 'FORMA', 'Time_Puro', 'Posicao_Pura']
                    cols_display_names = ["#", "EQUIPE", "Pts", "J", "V", "E", "D", "GP", "GC", "FORMA", "Time_Puro", "Posicao_Pura"]
                    
                    final_cols_map = dict(zip(cols_raw, cols_display_names))
                    cols_to_use = [col for col in cols_raw if col in tabela_html.columns]
                    tabela_final = tabela_html[cols_to_use]
                    tabela_final.columns = [final_cols_map.get(col, col) for col in cols_to_use]
                    
                    # 3. APLICA O STYLER
                    styler = tabela_final.style.apply(
                        highlight_match_teams_styler_final, 
                        axis=1, 
                        mandante=mandante, 
                        visitante=visitante
                    )
                    
                    # 🚨 IMPORTANTE: NENHUM applymap na coluna FORMA para não quebrar o HTML.
                    
                    styler = styler.hide(subset=['Time_Puro', 'Posicao_Pura'], axis="columns") 
                    
                    # CSS BÁSICO (Para a tabela)
                    css_styles = """
                    <style>
                    /* Estilos básicos da tabela (MANTIDOS) */
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
                    /* Força o alinhamento esquerdo para o nome do time */
                    th:nth-child(2), td:nth-child(2) {
                        text-align: left !important;
                    }
                    /* Alinhamento central para todas as outras células */
                    th:nth-child(1), td:nth-child(1), th:nth-child(n+3), td:nth-child(n+3) {
                        text-align: center !important;
                    }
                    td {
                        border: 1px solid #1f2730;
                        padding: 4px 8px;
                        font-size: 14px;
                        line-height: 25px; 
                    }
                    
                    /* Regra para garantir o alinhamento central */
                    .stDataFrame table td > div {
                        display: flex !important;
                        align-items: center !important;
                        justify-content: center !important;
                        height: 100% !important;
                    }

                    </style>
                    """
                    
                    tabela_html_final = styler.to_html(escape=False, index=False)

                    st.markdown(css_styles, unsafe_allow_html=True)
                    st.markdown(tabela_html_final, unsafe_allow_html=True)
                    
                    # Legendas da Classificação
                    st.markdown("---")
                    st.markdown("### 🎨 Legenda da Classificação")
                    
                    col_legenda1, col_legenda2, col_legenda3, col_legenda4 = st.columns(4)
                    
                    with col_legenda1:
                        st.markdown(
                            "<div style='padding: 5px; background-color: #66BB6A; color: black; border-radius: 5px; font-size: 14px;'>🏆 1º ao 4º: Libertadores (Grupos)</div>", 
                            unsafe_allow_html=True
                        )
                    
                    with col_legenda2:
                        st.markdown(
                            "<div style='padding: 5px; background-color: #007BFF; color: white; border-radius: 5px; font-size: 14px;'>🟦 5º ao 6º: Libertadores (Qualif.)</div>", 
                            unsafe_allow_html=True
                        )
                        
                    with col_legenda3:
                        st.markdown(
                            "<div style='padding: 5px; background-color: #00BFFF; color: black; border-radius: 5px; font-size: 14px;'>🏅 7º ao 12º: Sul-Americana</div>", 
                            unsafe_allow_html=True
                        )
                        
                    with col_legenda4:
                        st.markdown(
                            "<div style='padding: 5px; background-color: #EF5350; color: white; border-radius: 5px; font-size: 14px;'>🔻 17º em diante: Rebaixamento</div>", 
                            unsafe_allow_html=True
                        )
                        
                    # LEGENDA DO DESTAQUE: AZUL ESCURO
                    st.markdown(
                        "<div style='width: 25%; margin-top: 10px; padding: 5px; background-color: #1E90FF; color: white; border-radius: 5px; font-size: 14px;'>⚽ Destaque: Time da Partida</div>", 
                        unsafe_allow_html=True
                    )

                    st.markdown("---")
                    
                except Exception as e:
                    st.warning(f"Erro ao exibir a tabela estilizada em HTML: {e}. Exibindo classificação padrão.")
                    st.dataframe(tabela_geral, use_container_width=True)


        with tab_home:
            st.subheader("Classificação: Jogos Em Casa")
            # Usa a função auxiliar de display
            display_styled_table(tabela_casa, mandante, visitante, title="Tabela Casa")

        with tab_away:
            st.subheader("Classificação: Jogos Fora")
            # Usa a função auxiliar de display
            display_styled_table(tabela_fora, mandante, visitante, title="Tabela Fora")
    
    # ==============================================================================
    # TAB 4: ANÁLISE DE JOGADOR
    # ==============================================================================

    with tab4:
        st.subheader("👨‍選手 Análise de Jogador")
        
        # 1. Seleciona o time
        try:
            teams_data = get_teams_by_league(liga_id, temporada)
            if teams_data:
                df_times = pd.DataFrame([{
                    "id": t["team"]["id"],
                    "name": t["team"]["name"]
                } for t in teams_data])
                
                # Prepara opções e seleção inicial
                all_team_names = sorted(list(set(df_times["name"].tolist())))
                initial_selection = mandante if mandante in all_team_names else all_team_names[0] if all_team_names else None
                
                initial_index = all_team_names.index(initial_selection) if initial_selection and initial_selection in all_team_names else 0

                team_selecionado = st.selectbox(
                    "Selecione um time", 
                    all_team_names, 
                    index=initial_index
                )
                id_time_selecionado = df_times[df_times["name"] == team_selecionado]["id"].values[0]

            else:
                st.warning("⚠ Nenhum time encontrado para esta liga/temporada.")
                id_time_selecionado = None
                team_selecionado = None
        
        except Exception as e:
            st.error(f"Erro ao carregar lista de times: {e}")
            id_time_selecionado = None
            team_selecionado = None


        if id_time_selecionado:
            # 2. Seleciona o jogador
            elenco = get_squad_by_team(id_time_selecionado, temporada)
            
            if not elenco:
                st.info("ℹ Elenco não disponível para o time selecionado.")
            else:
                df_jogadores = pd.DataFrame(elenco)
                df_jogadores = df_jogadores.sort_values(by='name') 
                
                jogador_selecionado = st.selectbox("Selecione um jogador", df_jogadores["name"])
                id_jogador_selecionado = df_jogadores[df_jogadores["name"] == jogador_selecionado]["id"].values[0]

                # 3. Exibe as estatísticas
                if jogador_selecionado:
                    try:
                        jogador_stats = get_player_stats(id_jogador_selecionado, temporada, liga_id)
                        
                        if jogador_stats and 'player' in jogador_stats and 'statistics' in jogador_stats and jogador_stats['statistics']:
                            jogador_info = jogador_stats.get("player", {})
                            jogador_estatisticas = jogador_stats.get("statistics", [{}])[0]
                            
                            st.header(f"Detalhes de {jogador_info.get('name')}")
                            
                            col_foto, col_info = st.columns([1, 2])
                            with col_foto:
                                # Adiciona a imagem se a URL existir
                                photo_url = jogador_info.get("photo")
                                if photo_url:
                                    st.image(photo_url, width=150)
                                else:
                                    st.info("Foto não disponível.")
                                    
                            with col_info:
                                st.markdown(f"*Nome:* {jogador_info.get('name')}")
                                st.markdown(f"*Idade:* {jogador_info.get('age')}")
                                st.markdown(f"*Nacionalidade:* {jogador_info.get('nationality')}")
                                st.markdown(f"*Posição:* {jogador_estatisticas.get('games', {}).get('position')}")
                                
                            st.markdown("### Estatísticas da Temporada")
                            
                            stats = jogador_estatisticas
                            
                            def get_stat(category, sub_category=None, key=None):
                                if sub_category and key:
                                    return stats.get(category, {}).get(sub_category, {}).get(key, 0)
                                elif key:
                                    return stats.get(category, {}).get(key, 0)
                                return 0

                            df_estatisticas = pd.DataFrame([
                                {"Categoria": "Jogos Disputados",   "Valor": get_stat('games', key='appearences')},
                                {"Categoria": "Jogos Titular",      "Valor": get_stat('games', key='lineups')},
                                {"Categoria": "Minutos Jogados",    "Valor": get_stat('games', key='minutes')},
                                {"Categoria": "Nota Média (Rating)", "Valor": stats.get('games', {}).get('rating', 'N/A')}, 
                                {"Categoria": "Gols Marcados",      "Valor": get_stat('goals', key='total')},
                                {"Categoria": "Assistências",       "Valor": get_stat('goals', key='assists')},
                                {"Categoria": "Total de Passes",    "Valor": get_stat('passes', key='total')},
                                {"Categoria": "Passes Chave",       "Valor": get_stat('passes', key='key')},
                                {"Categoria": "Precisão de Passes", "Valor": stats.get('passes', {}).get('accuracy', 'N/A')}, 
                                {"Categoria": "Chutes Totais",      "Valor": get_stat('shots', key='total')},
                                {"Categoria": "Chutes no Gol",      "Valor": get_stat('shots', key='on')},
                                {"Categoria": "Faltas Cometidas",   "Valor": get_stat('fouls', key='committed')},
                                {"Categoria": "Cartões Amarelos",  "Valor": get_stat('cards', key='yellow')},
                                {"Categoria": "Cartões Vermelhos",  "Valor": get_stat('cards', key='red')},
                                # Goleiro (se aplicável)
                                {"Categoria": "Gols Sofridos (Goleiro)",   "Valor": get_stat('goals', key='conceded')},
                                {"Categoria": "Total de Defesas (Goleiro)", "Valor": get_stat('goals', key='saves')},
                                # Dribles 
                                {"Categoria": "Dribles Tentados", "Valor": get_stat('dribbles', key='attempts')},
                                {"Categoria": "Dribles Bem Sucedidos", "Valor": get_stat('dribbles', key='success')},
                                # Combates (Duels)
                                {"Categoria": "Duelos Totais", "Valor": get_stat('duels', key='total')},
                                {"Categoria": "Duelos Ganhos", "Valor": get_stat('duels', key='won')},
                            ])
                            
                            # Filtra para remover linhas com valor 0, mantendo as mais importantes e N/A
                            important_stats = ["Gols Marcados", "Assistências", "Jogos Disputados", "Nota Média (Rating)"]
                            
                            df_estatisticas_filtrado = df_estatisticas[
                                (df_estatisticas['Valor'] != 0) | 
                                (df_estatisticas['Valor'] == 'N/A') |
                                (df_estatisticas['Categoria'].isin(important_stats))
                            ].drop_duplicates(subset=['Categoria'], keep='first')
                            
                            st.dataframe(df_estatisticas_filtrado.set_index("Categoria"), use_container_width=True)
                        
                        else:
                            st.warning("⚠ Estatísticas do jogador não disponíveis para esta temporada/liga.")
                        
                    except Exception as e:
                        st.error(f"Erro ao buscar estatísticas do jogador: {e}")