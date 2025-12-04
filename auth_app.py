# auth_app.py

import streamlit as st
from PIL import Image 
from firebase_utils import register_user, login_user, send_password_reset

# 🚨 CAMINHO DA LOGO: O arquivo 'logo_dashgol.png' deve estar acessível.
LOGO_PATH = "logo_dashgol.png" 

# =================================================================
# CSS: Apenas para o aviso e o H2
# =================================================================
CUSTOM_WARNING_STYLE = """
<style>
/* Estilo para a barra amarela (st.warning) */
div[data-testid="stAlert"] {
    font-size: 0.9em; 
    text-align: center;
    padding: 0.5rem 1rem;
}

/* Centraliza o título */
h2 {
    text-align: center;
}
</style>
"""

def display_logo_and_header(header_text):
    """
    Exibe a logo centralizada usando a largura total do app,
    e o título centalizado logo abaixo.
    """
    
    # 1. Aplica o CSS customizado
    st.markdown(CUSTOM_WARNING_STYLE, unsafe_allow_html=True)
    
    # 2. CENTRALIZAÇÃO DA LOGO: Usando colunas na largura total da tela
    # Proporções: 1 (Espaço vazio) | 0.4 (Logo) | 1 (Espaço vazio)
    # Isso centraliza o bloco da logo visualmente.
    col_vazio1, col_logo, col_vazio2 = st.columns([1, 0.4, 1], gap="small")
    
    with col_logo:
        # Tenta exibir a logo com st.image()
        try:
            logo = Image.open(LOGO_PATH)
            # A logo agora é exibida no centro de uma coluna mais estreita na largura total
            st.image(logo, width=150) 
        except FileNotFoundError:
            st.warning(f"⚠️ Logo não encontrada. Verifique o caminho: '{LOGO_PATH}'.")
            
    # 3. Exibe o título (será centralizado pelo CSS H2)
    st.markdown(f"<h2>{header_text}</h2>", unsafe_allow_html=True)
    st.markdown("---") # Linha divisória


def render_login_form():
    """Desenha o formulário de login no centro da tela principal."""
    
    # 1. Cabeçalho (Logo e Título) na largura total
    display_logo_and_header("Login")
    
    # 2. Colunas para centralizar o FORMULÁRIO (o bloco de inputs)
    col_vazio1, col_form, col_vazio2 = st.columns([1, 1, 1])
    
    with col_form:
        # TUDO DENTRO DE COL_FORM ESTÁ CENTRALIZADO NA TELA
        
        # 1. Formulário de Login
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Senha", type="password", key="login_password")
            submitted = st.form_submit_button("Entrar", type="primary")
        
            if submitted:
                success, token_or_message = login_user(email, password)
                if success:
                    st.session_state['logged_in'] = True
                    st.session_state['user_email'] = email
                    st.session_state['id_token'] = token_or_message
                    st.success("Login realizado com sucesso!")
                    st.rerun() 
                else:
                    st.error(token_or_message)
        
        st.divider()

        # 2. Navegação
        st.button("Esqueci a senha", 
                    on_click=lambda: st.session_state.update({'mode': 'reset'}), 
                    key="forgot_password_btn")
        
        st.button("Não tem conta? Cadastre-se", 
                    on_click=lambda: st.session_state.update({'mode': 'signup'}), 
                    key="nav_to_signup_btn")


def render_signup_form():
    """Desenha o formulário de cadastro no centro da tela."""
    
    display_logo_and_header("Cadastro")
    
    col_vazio1, col_form, col_vazio2 = st.columns([1, 1, 1])
    
    with col_form:
        
        with st.form("signup_form"):
            st.subheader("Crie sua conta para acessar o Dash Gol")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Nova Senha (min. 6 caracteres)", type="password", key="signup_password")
            submitted = st.form_submit_button("Cadastrar", type="primary")

            if submitted:
                success, message = register_user(email, password)
                if success:
                    st.success(message)
                    st.session_state['mode'] = 'login' 
                    st.rerun() 
                else:
                    st.error(message)

        st.divider()
        
        st.button("Já tem conta? Fazer Login", 
                    on_click=lambda: st.session_state.update({'mode': 'login'}), 
                    key="back_to_login_from_signup")


def render_reset_password():
    """Desenha o formulário de recuperação de senha no centro da tela."""
    
    display_logo_and_header("Recuperar Senha")

    col_vazio1, col_form, col_vazio2 = st.columns([1, 1, 1])
    
    with col_form:
        
        with st.form("reset_form"):
            st.subheader("Insira seu email para receber o link de recuperação.")
            email = st.text_input("Email de Recuperação", key="reset_email")
            submitted = st.form_submit_button("Enviar Link", type="primary")
            
            if submitted:
                success, message = send_password_reset(email)
                if success:
                    st.info(message)
                else:
                    st.warning(message)
        
        st.divider()

        st.button("Voltar ao Login", 
                    on_click=lambda: st.session_state.update({'mode': 'login'}), 
                    key="back_to_login_btn")


def require_login_and_render_ui():
    """Função principal de controle de acesso e renderização da interface."""
    
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'mode' not in st.session_state:
        st.session_state['mode'] = 'login' 
        
    if st.session_state['logged_in']:
        # Usuário logado: Libera o dashboard
        return True
    else:
        # Usuário não logado: Renderiza a UI de autenticação
        
        # Centraliza e reduz a barra de aviso
        col_vazio1, col_warning, col_vazio2 = st.columns([0.5, 2, 0.5])
        with col_warning:
            st.warning("🔒 Por favor, faça login ou cadastre-se para acessar o Dash Gol.")
        
        # Desenha o formulário principal com base no modo
        if st.session_state['mode'] == 'login':
            render_login_form()
            
        elif st.session_state['mode'] == 'signup':
            render_signup_form()
            
        elif st.session_state['mode'] == 'reset':
            render_reset_password()
            
        st.stop()