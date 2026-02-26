import sqlite3
import json

conexao = sqlite3.connect("notas_fiscais_v2.db", check_same_thread=False)
cursor = conexao.cursor()

# 1. Tabela de Notas Fiscais
cursor.execute('''
    CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ruc_emissor TEXT,
        nome_cliente TEXT,
        valor_total REAL,
        cdc TEXT,
        itens TEXT,
        data_emissao DATETIME DEFAULT CURRENT_TIMESTAMP
    )
''')

# 2. Tabela de Produtos (A categoria agora vai puxar o nome exato do banco)
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
cursor.execute('INSERT OR IGNORE INTO empresa (id, nome_empresa, ruc) VALUES (1, "Mi Empresa S.A.", "80012345-6")')

# 4. NOVA: Tabela de Categorias
cursor.execute('''
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL
    )
''')
cursor.execute('INSERT OR IGNORE INTO categorias (nome) VALUES ("General")')

conexao.commit()

# --- FUNÇÕES DE CATEGORIAS (NOVO) ---
def cadastrar_categoria(nome):
    try:
        cursor.execute('INSERT INTO categorias (nome) VALUES (?)', (nome,))
        conexao.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Retorna falso se já existir uma categoria com esse nome

def listar_categorias():
    cursor.execute('SELECT id, nome FROM categorias ORDER BY nome ASC')
    linhas = cursor.fetchall()
    return [{"id": l[0], "nome": l[1]} for l in linhas]

def deletar_categoria(id_categoria):
    cursor.execute('DELETE FROM categorias WHERE id = ?', (id_categoria,))
    conexao.commit()


# --- FUNÇÕES DE CONFIGURAÇÃO DA EMPRESA ---
def obter_configuracao():
    cursor.execute('SELECT nome_empresa, ruc, endereco, senha_certificado, caminho_certificado FROM empresa WHERE id = 1')
    linha = cursor.fetchone()
    if linha: return {"nome_empresa": linha[0], "ruc": linha[1], "endereco": linha[2], "senha_certificado": linha[3], "caminho_certificado": linha[4]}
    return None

def salvar_configuracao_texto(nome, ruc, endereco, senha):
    cursor.execute('UPDATE empresa SET nome_empresa = ?, ruc = ?, endereco = ?, senha_certificado = ? WHERE id = 1', (nome, ruc, endereco, senha))
    conexao.commit()

def salvar_caminho_certificado(caminho):
    cursor.execute('UPDATE empresa SET caminho_certificado = ? WHERE id = 1', (caminho,))
    conexao.commit()


# --- FUNÇÕES DE ESTOQUE ---
def cadastrar_produto(codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade):
    cursor.execute('''
        INSERT OR REPLACE INTO produtos (codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade))
    conexao.commit()

def listar_produtos():
    cursor.execute('SELECT * FROM produtos')
    linhas = cursor.fetchall()
    return [{"codigo_barras": l[0], "descricao": l[1], "categoria": l[2], "subcategoria": l[3], "preco_custo": l[4], "preco_venda": l[5], "quantidade": l[6]} for l in linhas]

def buscar_produto_por_codigo(codigo_barras):
    cursor.execute('SELECT * FROM produtos WHERE codigo_barras = ?', (codigo_barras,))
    l = cursor.fetchone()
    if l: return {"descricao": l[1], "preco_venda": l[5]}
    return None

def atualizar_estoque(codigo_barras, quantidade_vendida):
    cursor.execute('UPDATE produtos SET quantidade = quantidade - ? WHERE codigo_barras = ?', (quantidade_vendida, codigo_barras))
    conexao.commit()

def deletar_produto(codigo_barras):
    cursor.execute('DELETE FROM produtos WHERE codigo_barras = ?', (codigo_barras,))
    conexao.commit()


# --- FUNÇÕES DE VENDAS ---
def salvar_nota(ruc, cliente, valor, cdc, itens):
    itens_json = json.dumps([item.dict() for item in itens])
    cursor.execute('INSERT INTO notas (ruc_emissor, nome_cliente, valor_total, cdc, itens) VALUES (?, ?, ?, ?, ?)',
                   (ruc, cliente, valor, cdc, itens_json))
    for item in itens:
        if hasattr(item, 'codigo_barras') and item.codigo_barras:
            atualizar_estoque(item.codigo_barras, item.quantidade)
    conexao.commit()

def listar_todas_notas(busca=""):
    if busca: cursor.execute("SELECT * FROM notas WHERE nome_cliente LIKE ? OR cdc LIKE ? ORDER BY id DESC", (f"%{busca}%", f"%{busca}%"))
    else: cursor.execute('SELECT * FROM notas ORDER BY id DESC')
    linhas = cursor.fetchall()
    return [{"id": l[0], "nome_cliente": l[2], "valor_total": l[3], "cdc": l[4]} for l in linhas]