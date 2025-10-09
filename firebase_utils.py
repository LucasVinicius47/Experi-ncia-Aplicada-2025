# firebase_utils.py

import pyrebase
import streamlit as st # Importado para acessar o st.secrets se necessário no futuro

# ==========================================================
# === 🚨 CONFIGURAÇÃO FINAL DO FIREBASE 🚨 ===
# Usando suas credenciais confirmadas (incluindo a databaseURL)
# ==========================================================
FIREBASE_CONFIG = {
    'apiKey': "AIzaSyBZdYb2LKufr8dIpPmeUrim8MoZAGNvqzI", 
    'authDomain': "dash-gol-login.firebaseapp.com",
    'projectId': "dash-gol-login",
    'storageBucket': "dash-gol-login.firebasestorage.app",
    'messagingSenderId': "790776713967", 
    'appId': "1:790776713967:web:5ecd5d0e21cd722170411a",
    # CHAVE NECESSÁRIA PARA O PYREBASE4:
    'databaseURL': "https://dash-gol-login-default-rtdb.firebaseio.com" 
}
# ==========================================================

# Inicializa a conexão com o Firebase
try:
    firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
    auth = firebase.auth()
    # Adiciona uma mensagem para o terminal, útil para debug inicial
    print("Firebase inicializado com sucesso.")
except Exception as e:
    # Se a chave estiver errada, a inicialização falha aqui.
    print(f"ERRO CRÍTICO ao inicializar o Firebase: {e}")
    st.error("Erro na configuração do Firebase. Verifique as chaves.")
    
# --- Funções de Autenticação ---

def register_user(email, password):
    """
    Tenta cadastrar um novo usuário no Firebase. 
    Permite o auto-cadastro.
    """
    try:
        auth.create_user_with_email_and_password(email, password)
        return True, "Cadastro realizado com sucesso! Você já pode fazer login."
    except Exception as e:
        error_message = str(e)
        if "EMAIL_EXISTS" in error_message:
            return False, "Este email já está cadastrado."
        elif "WEAK_PASSWORD" in error_message:
            return False, "A senha deve ter pelo menos 6 caracteres."
        # Captura outros erros genéricos do Firebase
        return False, f"Erro ao cadastrar. Tente novamente."

def login_user(email, password):
    """
    Tenta fazer login de um usuário e retorna o token de sessão.
    """
    try:
        # Tenta autenticar
        user = auth.sign_in_with_email_and_password(email, password)
        # O 'idToken' é usado pelo Streamlit para confirmar que a sessão é válida
        return True, user['idToken'] 
    except Exception as e:
        # Erros comuns são e-mail/senha incorretos
        return False, "Email ou senha inválidos."

def send_password_reset(email):
    """
    Envia um email de recuperação de senha através do Firebase.
    """
    try:
        auth.send_password_reset_email(email)
        return True, "Email de recuperação enviado. Verifique sua caixa de entrada."
    except Exception as e:
        return False, "Erro: Email não encontrado ou não cadastrado."