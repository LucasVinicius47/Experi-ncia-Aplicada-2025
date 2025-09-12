import streamlit as st
from datetime import datetime, timedelta

# ========================
# CONFIGURAÇÃO DO APP
# ========================
st.set_page_config(
    page_title="⚽ Futebol Análise",
    page_icon="⚽",
    layout="wide"
)

# ========================
# HEADER
# ========================
st.title("⚽ Análise de Partidas de Futebol")

# Seleção de datas
hoje = datetime.today()
dias = [(hoje + timedelta(days=i)) for i in range(-3, 4)]
dias_formatados = {d.strftime("%a %d/%m"): d.date() for d in dias}
selected_day = st.radio(
    "Escolha o dia:",
    options=list(dias_formatados.keys()),
    horizontal=True
)
st.write(f"📅 Data selecionada: **{dias_formatados[selected_day]}**")

# Seleção de ligas (exemplo fixo, depois conectamos à API)
ligas_famosas = [
    "Premier League",
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Brasileirão Série A",
    "Champions League"
]
selected_league = st.selectbox("Selecione a Liga:", ligas_famosas)

st.markdown("---")

# ========================
# ÁREA PRINCIPAL COM TABS
# ========================
tab1, tab2, tab3 = st.tabs(["⚡ Ao Vivo", "📅 Próximos", "✅ Encerrados"])

# ------------------------
# TAB 1 - AO VIVO
# ------------------------
with tab1:
    st.subheader("Partidas Ao Vivo")

    # Card da partida
    col1, col2, col3 = st.columns([3, 1, 3])
    with col1:
        st.write("🏟️ Time A")
        st.metric("Gols", 1)
        st.progress(0.45)  # posse de bola 45%
    with col2:
        st.write("⏱️ 55'")
        st.metric("Placar", "1 - 0")
    with col3:
        st.write("Time B 🏟️")
        st.metric("Gols", 0)
        st.progress(0.55)  # posse de bola 55%

    # Estatísticas detalhadas
    st.markdown("### 📊 Estatísticas da Partida")
    stats_col1, stats_col2 = st.columns(2)

    with stats_col1:
        st.write("Finalizações: **10** (Time A) vs 7 (Time B)")
        st.write("Escanteios: **5** (Time A) vs 2 (Time B)")
        st.write("Cartões Amarelos: 1 (Time A) vs **3** (Time B)")

    with stats_col2:
        st.write("Faltas: 12 (Time A) vs **15** (Time B)")
        st.write("Chutes no alvo: **6** (Time A) vs 3 (Time B)")
        st.write("Cartões Vermelhos: 0 (Time A) vs **1** (Time B)")

    # Escalações
    st.markdown("### 📋 Escalações")
    lineup_tab1, lineup_tab2 = st.tabs(["Time A", "Time B"])

    with lineup_tab1:
        st.write("Formação: 4-2-3-1")
        st.write("**Titulares**")
        st.write("1. David de Gea (G)")
        st.write("5. Harry Maguire (D)")
        st.write("8. Bruno Fernandes (M)")
        st.write("7. Cristiano Ronaldo (F)")
        st.write("**Banco**")
        st.write("12. Victor Lindelöf (D)")
        st.write("14. Jesse Lingard (M)")
        st.write("Treinador: Erik ten Hag")

    with lineup_tab2:
        st.write("Formação: 4-3-3")
        st.write("**Titulares**")
        st.write("1. Ederson (G)")
        st.write("4. Rúben Dias (D)")
        st.write("8. İlkay Gündoğan (M)")
        st.write("9. Erling Haaland (F)")
        st.write("**Banco**")
        st.write("20. Bernardo Silva (M)")
        st.write("47. Phil Foden (F)")
        st.write("Treinador: Pep Guardiola")

# ------------------------
# TAB 2 - PRÓXIMOS
# ------------------------
with tab2:
    st.subheader("Próximas Partidas")
    st.info("Exemplo: Time X vs Time Y — amanhã às 16:00")

# ------------------------
# TAB 3 - ENCERRADOS
# ------------------------
with tab3:
    st.subheader("Partidas Encerradas")
    st.success("Exemplo: Time C 2 - 1 Time D (Final)")

# ========================
# RODAPÉ
# ========================
st.markdown("---")
st.caption("📊 Dados fornecidos pela API-Football (versão demonstrativa)")
