import os
import json
import psycopg2

# Puxa a senha secreta que você configurou no Render
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conexao():
    # Conecta no banco de dados na Nuvem
    return psycopg2.connect(DATABASE_URL)

def inicializar_banco():
    conexao = get_conexao()
    cursor = conexao.cursor()

    # 1. Tabela de Notas Fiscais
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas (
            id SERIAL PRIMARY KEY,
            ruc_emissor TEXT,
            nome_cliente TEXT,
            valor_total REAL,
            cdc TEXT,
            itens TEXT,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Tabela de Produtos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            codigo_barras TEXT PRIMARY KEY,
            descricao TEXT NOT NULL,
            categoria TEXT,
            subcategoria TEXT,
            preco_custo REAL,
            preco_venda REAL NOT NULL,
            quantidade INTEGER DEFAULT 0
        )
    ''')

    # 3. Tabela de Configuração da Empresa
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresa (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nome_empresa TEXT,
            ruc TEXT,
            endereco TEXT,
            senha_certificado TEXT,
            caminho_certificado TEXT
        )
    ''')
    cursor.execute('INSERT INTO empresa (id, nome_empresa, ruc) VALUES (1, \'Mi Empresa S.A.\', \'80012345-6\') ON CONFLICT (id) DO NOTHING')

    # 4. Tabela de Categorias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            nome TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute('INSERT INTO categorias (nome) VALUES (\'General\') ON CONFLICT (nome) DO NOTHING')

    conexao.commit()
    cursor.close()
    conexao.close()

# Inicia o banco automaticamente se a senha estiver configurada
if DATABASE_URL:
    inicializar_banco()

# --- FUNÇÕES DE CATEGORIAS ---
def cadastrar_categoria(nome):
    try:
        conexao = get_conexao()
        cursor = conexao.cursor()
        cursor.execute('INSERT INTO categorias (nome) VALUES (%s)', (nome,))
        conexao.commit()
        return True
    except psycopg2.IntegrityError:
        return False
    finally:
        if 'conexao' in locals(): conexao.close()

def listar_categorias():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT id, nome FROM categorias ORDER BY nome ASC')
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome": l[1]} for l in linhas]

def deletar_categoria(id_categoria):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM categorias WHERE id = %s', (id_categoria,))
    conexao.commit()
    conexao.close()

# --- FUNÇÕES DE CONFIGURAÇÃO DA EMPRESA ---
def obter_configuracao():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT nome_empresa, ruc, endereco, senha_certificado, caminho_certificado FROM empresa WHERE id = 1')
    linha = cursor.fetchone()
    conexao.close()
    if linha: return {"nome_empresa": linha[0], "ruc": linha[1], "endereco": linha[2], "senha_certificado": linha[3], "caminho_certificado": linha[4]}
    return None

def salvar_configuracao_texto(nome, ruc, endereco, senha):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('UPDATE empresa SET nome_empresa = %s, ruc = %s, endereco = %s, senha_certificado = %s WHERE id = 1', (nome, ruc, endereco, senha))
    conexao.commit()
    conexao.close()

def salvar_caminho_certificado(caminho):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('UPDATE empresa SET caminho_certificado = %s WHERE id = 1', (caminho,))
    conexao.commit()
    conexao.close()

# --- FUNÇÕES DE ESTOQUE ---
def cadastrar_produto(codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('''
        INSERT INTO produtos (codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (codigo_barras) DO UPDATE SET
        descricao = EXCLUDED.descricao,
        categoria = EXCLUDED.categoria,
        subcategoria = EXCLUDED.subcategoria,
        preco_custo = EXCLUDED.preco_custo,
        preco_venda = EXCLUDED.preco_venda,
        quantidade = EXCLUDED.quantidade
    ''', (codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade))
    conexao.commit()
    conexao.close()

def listar_produtos():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT * FROM produtos')
    linhas = cursor.fetchall()
    conexao.close()
    return [{"codigo_barras": l[0], "descricao": l[1], "categoria": l[2], "subcategoria": l[3], "preco_custo": l[4], "preco_venda": l[5], "quantidade": l[6]} for l in linhas]

def buscar_produto_por_codigo(codigo_barras):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT * FROM produtos WHERE codigo_barras = %s', (codigo_barras,))
    l = cursor.fetchone()
    conexao.close()
    if l: return {"descricao": l[1], "preco_venda": l[5]}
    return None

def atualizar_estoque(codigo_barras, quantidade_vendida):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('UPDATE produtos SET quantidade = quantidade - %s WHERE codigo_barras = %s', (quantidade_vendida, codigo_barras))
    conexao.commit()
    conexao.close()

def deletar_produto(codigo_barras):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM produtos WHERE codigo_barras = %s', (codigo_barras,))
    conexao.commit()
    conexao.close()

# --- FUNÇÕES DE VENDAS E DASHBOARD ---
def salvar_nota(ruc, cliente, valor, cdc, itens):
    itens_json = json.dumps([item.dict() for item in itens])
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('INSERT INTO notas (ruc_emissor, nome_cliente, valor_total, cdc, itens) VALUES (%s, %s, %s, %s, %s)',
                   (ruc, cliente, valor, cdc, itens_json))
    for item in itens:
        if hasattr(item, 'codigo_barras') and item.codigo_barras:
            cursor.execute('UPDATE produtos SET quantidade = quantidade - %s WHERE codigo_barras = %s', (item.quantidade, item.codigo_barras))
    conexao.commit()
    conexao.close()

def listar_todas_notas(busca=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    if busca: 
        # No Postgres usamos ILIKE para ignorar letras maiúsculas/minúsculas na busca
        cursor.execute("SELECT * FROM notas WHERE nome_cliente ILIKE %s OR cdc ILIKE %s ORDER BY id DESC", (f"%{busca}%", f"%{busca}%"))
    else: 
        cursor.execute('SELECT * FROM notas ORDER BY id DESC')
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome_cliente": l[2], "valor_total": l[3], "cdc": l[4]} for l in linhas]

def obter_dados_dashboard():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT valor_total, itens FROM notas')
    notas = cursor.fetchall()
    conexao.close()
    
    total_vendas = 0
    total_notas = len(notas)
    produtos_vendidos = {}
    
    for nota in notas:
        total_vendas += nota[0]
        itens = json.loads(nota[1]) 
        for item in itens:
            nome = item.get("descricao", "Manual / Otros")
            qtd = item.get("quantidade", 0)
            if nome in produtos_vendidos:
                produtos_vendidos[nome] += qtd
            else:
                produtos_vendidos[nome] = qtd
                
    top_produtos = sorted(produtos_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_vendas": total_vendas,
        "total_notas": total_notas,
        "top_produtos": [{"nome": p[0], "quantidade": p[1]} for p in top_produtos]
    }