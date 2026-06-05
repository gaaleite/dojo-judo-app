import streamlit as st
import sqlite3
import os
from PIL import Image
import time
import subprocess

# Configuração inicial da página para Mobile-First
st.set_page_config(page_title="Judô Gestão", layout="centered")

# Criar pasta para salvar as fotos dos alunos se não existir
if not os.path.exists("fotos_alunos"):
    os.makedirs("fotos_alunos")

# --- FUNÇÃO DE SINCRONIZAÇÃO COM O GITHUB ---
def salvar_dados_no_github():
    if os.path.exists(".git"):
        try:
            subprocess.run(["git", "config", "--global", "user.email", "dojo_bot@email.com"], check=True)
            subprocess.run(["git", "config", "--global", "user.name", "Dojo Bot"], check=True)
            subprocess.run(["git", "add", "judo_escola.db", "fotos_alunos/*"], check=True)
            subprocess.run(["git", "commit", "-m", "Auto-update dados dojo"], check=True)
            subprocess.run(["git", "push"], check=True)
        except Exception as e:
            pass

# --- FUNÇÃO CALLBACK PARA ADICIONAR MELHORIA ---
def adicionar_melhoria_callback(id_do_aluno, lista_atual):
    chave_input = f"add_item_{id_do_aluno}"
    texto_digitado = st.session_state[chave_input].strip()
    if texto_digitado:
        lista_atual.append(texto_digitado)
        nova_string = "\n".join(lista_atual)
        
        conn_cb = sqlite3.connect("judo_escola.db")
        cursor_cb = conn_cb.cursor()
        cursor_cb.execute("UPDATE proficiencia SET melhorias = ? WHERE aluno_id = ?", (nova_string, id_do_aluno))
        conn_cb.commit()
        conn_cb.close()
        
        st.session_state[chave_input] = ""

# --- CONEXÃO COM O BANCO DE DADOS ---
def conectar_bd():
    conn = sqlite3.connect("judo_escola.db")
    cursor = conn.cursor()
    
    # 1. Tabela de Alunos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            idade INTEGER,
            altura REAL,
            peso REAL,
            foto_path TEXT
        )
    ''')
    
    try:
        cursor.execute("SELECT faixa FROM alunos LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE alunos ADD COLUMN faixa TEXT DEFAULT 'Branca (Iniciante)'")
        conn.commit()
    
    # 2. Tabela de Proficiência (Waza)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proficiencia (
            aluno_id INTEGER UNIQUE,
            nage_waza TEXT,
            katame_waza TEXT,
            FOREIGN KEY (aluno_id) REFERENCES alunos (id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    
    try:
        cursor.execute("SELECT rendimento FROM proficiencia LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE proficiencia ADD COLUMN rendimento TEXT DEFAULT 'Médio'")
        conn.commit()
        
    try:
        cursor.execute("SELECT melhorias FROM proficiencia LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE proficiencia ADD COLUMN melhorias TEXT DEFAULT ''")
        conn.commit()
        
    return conn, cursor

conn, cursor = conectar_bd()

# --- DADOS DO JUDÔ ---
lista_graduacoes = [
    "Branca (Iniciante)", "Branca / Cinza (11º kyu)", "Cinza (10º kyu)", "Cinza / Azul (9º kyu)",
    "Azul (8º kyu)", "Azul / Amarela (7º kyu)", "Amarela (6º kyu)", "Amarela / Laranja (5º kyu)",
    "Laranja (4º kyu)", "Verde (3º kyu)", "Roxa (2º kyu)", "Marrom (1º kyu)",
    "Preta (1º dan)", "Preta (2º dan)", "Preta (3º dan)", "Preta (4º dan)", "Preta (5º dan)",
    "Vermelha e branca (6º dan)", "Vermelha e branca (7º dan)", "Vermelha e branca (8º dan)",
    "Vermelha (9º dan)", "Vermelha (10º dan)"
]

lista_rendimento = ["Baixo", "Médio", "Bom", "Alto"]

def obter_emoji_faixa(graduacao_texto):
    texto = graduacao_texto.lower()
    if "vermelha e branca" in texto: return "🔴⚪"
    elif "branca / cinza" in texto: return "⚪🔘"  
    elif "cinza / azul" in texto: return "🔘🔵"
    elif "azul / amarela" in texto: return "🔵🟡"
    elif "amarela / laranja" in texto: return "🟡🟠"
    elif "vermelha" in texto: return "🔴"
    elif "preta" in texto: return "⚫"
    elif "marrom" in texto: return "🟤"
    elif "roxa" in texto: return "🟣"
    elif "verde" in texto: return "🟢"
    elif "laranja" in texto: return "🟠"
    elif "amarela" in texto: return "🟡"
    elif "azul" in texto: return "🔵"
    elif "cinza" in texto: return "🔘"  
    return "⚪"

# --- INTERFACE DO USUÁRIO ---
st.title("🥋 Sistema Dojo Judô")

aba_cadastro, aba_lista = st.tabs(["📝 Cadastrar Aluno", "👥 Lista e Graduação"])

# --- ABA 1: CADASTRO DE ALUNOS ---
with aba_cadastro:
    st.subheader("Novo Cadastro")
    
    with st.form("form_cadastro", clear_on_submit=True):
        nome = st.text_input("Nome Completo:")
        idade = st.number_input("Idade:", min_value=3, max_value=100, step=1)
        altura = st.number_input("Altura (m):", min_value=0.5, max_value=2.5, step=0.01)
        peso = st.number_input("Peso (kg):", min_value=10.0, max_value=200.0, step=0.1)
        foto = st.file_uploader("Foto do Aluno (Opcional)", type=["png", "jpg", "jpeg"], key="cadastro_foto")
        botao_cadastrar = st.form_submit_button("Salvar Aluno")
        
        if botao_cadastrar:
            if nome:
                foto_path = ""
                if foto is not None:
                    foto_path = f"fotos_alunos/{int(time.time())}_{nome.replace(' ', '_').lower()}.jpg"
                    image = Image.open(foto)
                    image.save(foto_path)
                
                cursor.execute(
                    "INSERT INTO alunos (nome, idade, altura, peso, foto_path, faixa) VALUES (?, ?, ?, ?, ?, ?)",
                    (nome, idade, altura, peso, foto_path, "Branca (Iniciante)")
                )
                aluno_id = cursor.lastrowid
                
                cursor.execute(
                    "INSERT INTO proficiencia (aluno_id, nage_waza, katame_waza, rendimento, melhorias) VALUES (?, ?, ?, ?, ?)",
                    (aluno_id, "Nenhum", "Nenhum", "Médio", "")
                )
                conn.commit()
                salvar_dados_no_github()
                st.success(f"Aluno {nome} cadastrado!")
                st.rerun()
            else:
                st.error("O campo Nome é obrigatório.")

# --- ABA 2: LISTA, PESQUISA E ATUALIZAÇÃO ---
with aba_lista:
    st.subheader("Gerenciamento de Alunos")
    pesquisa = st.text_input("🔍 Buscar aluno pelo nome:")
    
    if pesquisa:
        cursor.execute('''
            SELECT a.id, a.nome, a.idade, a.altura, a.peso, a.foto_path, a.faixa, 
                   p.nage_waza, p.katame_waza, p.rendimento, p.melhorias 
            FROM alunos a 
            JOIN proficiencia p ON a.id = p.aluno_id 
            WHERE a.nome LIKE ?
        ''', (f"%{pesquisa}%",))
    else:
        cursor.execute('''
            SELECT a.id, a.nome, a.idade, a.altura, a.peso, a.foto_path, a.faixa, 
                   p.nage_waza, p.katame_waza, p.rendimento, p.melhorias 
            FROM alunos a 
            JOIN proficiencia p ON a.id = p.aluno_id
        ''')
        
    alunos = cursor.fetchall()
    opcoes_nivel = ["Nenhum", "Básico", "Intermediário", "Graduado", "Graduado Superior"]
    
    if not alunos:
        st.info("Nenhum aluno encontrado.")
    
    for aluno in alunos:
        aluno_id, a_nome, a_idade, a_altura, a_peso, a_foto, a_faixa, n_waza, k_waza, p_rendimento, p_melhorias = aluno
        if not a_faixa or a_faixa not in lista_graduacoes: a_faixa = "Branca (Iniciante)"
        if not p_rendimento or p_rendimento not in lista_rendimento: p_rendimento = "Médio"
        if not p_melhorias: p_melhorias = ""
        
        emoji_cor = obter_emoji_faixa(a_faixa)
        
        with st.expander(f"{emoji_cor} {a_nome} | {a_faixa}"):
            col1, col2 = st.columns(2)
            with col1:
                if a_foto and os.path.exists(a_foto):
                    st.image(a_foto, width=110)
                    nova_foto = st.file_uploader("🔄 Alterar foto", type=["png", "jpg", "jpeg"], key=f"change_pic_{aluno_id}")
                else:
                    st.warning("⚠️ Sem foto")
                    nova_foto = st.file_uploader("📸 Adicionar foto", type=["png", "jpg", "jpeg"], key=f"add_pic_{aluno_id}")
                
                if nova_foto is not None:
                    if a_foto and os.path.exists(a_foto):
                        try: os.remove(a_foto)
                        except: pass
                    novo_caminho = f"fotos_alunos/{int(time.time())}_{a_nome.replace(' ', '_').lower()}.jpg"
                    image = Image.open(nova_foto)
                    image.save(novo_caminho)
                    cursor.execute("UPDATE alunos SET foto_path = ? WHERE id = ?", (novo_caminho, aluno_id))
                    conn.commit()
                    salvar_dados_no_github()
                    st.success("Foto atualizada!")
                    st.rerun()
            
            with col2:
                st.write(f"**Idade:** {a_idade} anos")
                st.write(f"**Altura:** {a_altura}m")
                st.write(f"**Peso:** {a_peso}kg")
            
            st.markdown("---")
            st.write("🏅 **Graduação do Aluno**")
            nova_faixa = st.selectbox("Selecione a Graduação Atual:", lista_graduacoes, index=lista_graduacoes.index(a_faixa), key=f"faixa_{aluno_id}")
            
            st.markdown("---")
            st.write("🥋 **Proficiência de Técnicas (Waza)**")
            novo_nage = st.selectbox("Nage-Waza (Projeção):", opcoes_nivel, index=opcoes_nivel.index(n_waza) if n_waza in opcoes_nivel else 0, key=f"nage_{aluno_id}")
            novo_katame = st.selectbox("Katame-Waza (Controle):", opcoes_nivel, index=opcoes_nivel.index(k_waza) if k_waza in opcoes_nivel else 0, key=f"katame_{aluno_id}")
            
            # --- EXIBIÇÃO DO RENDIMENTO GERAL (DE VOLTA!) ---
            st.markdown("---")
