# auth_app.py

import streamlit as st
# Importa as funções de comunicação com o Firebase do seu outro arquivo
from firebase_utils import register_user, login_user, send_password_reset

def render_login_form():
    """Desenha o formulário de login no centro da tela principal."""
    st.header("🔑 Login")
    
    # 1. Centraliza o formulário na tela
    col_vazio1, col_form, col_vazio2 = st.columns([1, 1, 1])
    
    with col_form:
        # 2. Formulário de Login
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Senha", type="password", key="login_password")
            submitted = st.form_submit_button("Entrar")
    
            if submitted:
                success, token_or_message = login_user(email, password)
                if success:
                    # Se o login for OK, define as variáveis de sessão e recarrega o app
                    st.session_state['logged_in'] = True
                    st.session_state['user_email'] = email
                    st.session_state['id_token'] = token_or_message
                    st.success("Login realizado com sucesso!")
                    # CORRIGIDO: Usando o novo método st.rerun()
                    st.rerun() 
                else:
                    st.error(token_or_message)
        
        # 3. Botão para Esqueci a Senha
        st.button("Esqueci a senha", 
                  on_click=lambda: st.session_state.update({'mode': 'reset'}), 
                  key="forgot_password_btn")
        
        # 4. Botão para Cadastro (Navegação)
        st.button("Não tem conta? Cadastre-se", 
                  on_click=lambda: st.session_state.update({'mode': 'signup'}), 
                  key="nav_to_signup_btn")


def render_signup_form():
    """Desenha o formulário de cadastro no centro da tela."""
    st.header("✍️ Cadastro (Sign Up)")
    col_vazio1, col_form, col_vazio2 = st.columns([1, 1, 1])
    
    with col_form:
        with st.form("signup_form"):
            st.subheader("Cadastre-se para acessar o Dash Gol")
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Nova Senha (min. 6 caracteres)", type="password", key="signup_password")
            submitted = st.form_submit_button("Cadastrar")

            if submitted:
                success, message = register_user(email, password)
                if success:
                    st.success(message)
                    # Redireciona para a tela de login após um cadastro bem-sucedido
                    st.session_state['mode'] = 'login' 
                    # CORRIGIDO: Usando o novo método st.rerun()
                    st.rerun() 
                else:
                    st.error(message)

        # Botão para Login (Navegação)
        st.button("Já tem conta? Fazer Login", 
                  on_click=lambda: st.session_state.update({'mode': 'login'}), 
                  key="back_to_login_from_signup")


def render_reset_password():
    """Desenha o formulário de recuperação de senha no centro da tela."""
    st.header("❓ Recuperar Senha")
    col_vazio1, col_form, col_vazio2 = st.columns([1, 1, 1])
    
    with col_form:
        with st.form("reset_form"):
            st.subheader("Insira seu email para receber o link de recuperação.")
            email = st.text_input("Email de Recuperação", key="reset_email")
            submitted = st.form_submit_button("Enviar Link")
            
            if submitted:
                success, message = send_password_reset(email)
                if success:
                    st.info(message)
                else:
                    st.warning(message)
        
        # Botão para voltar ao login
        st.button("Voltar ao Login", 
                  on_click=lambda: st.session_state.update({'mode': 'login'}), 
                  key="back_to_login_btn")


def require_login_and_render_ui():
    """Função principal de controle de acesso e renderização da interface."""
    
    # Inicializa o estado de sessão se ainda não existir
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'mode' not in st.session_state:
        st.session_state['mode'] = 'login' 
        
    if st.session_state['logged_in']:
        # Usuário logado: Retorna True para liberar o dashboard no app.py
        return True
    else:
        # Usuário não logado: Renderiza a UI de autenticação
        
        # AVISO CENTRALIZADO
        st.warning("🔒 Por favor, faça login ou cadastre-se para acessar o Dash Gol.")
        
        # Desenha o formulário principal com base no modo
        if st.session_state['mode'] == 'login':
            render_login_form()
            
        elif st.session_state['mode'] == 'signup':
            render_signup_form()
            
        elif st.session_state['mode'] == 'reset':
            render_reset_password()
            
        st.stop() # Bloqueia a execução do dashboard no app.py