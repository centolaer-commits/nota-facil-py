import os
import json
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conexao():
    return psycopg2.connect(DATABASE_URL)

def inicializar_banco():
    conexao = get_conexao()
    cursor = conexao.cursor()

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            nome TEXT UNIQUE NOT NULL
        )
    ''')
    cursor.execute('INSERT INTO categorias (nome) VALUES (\'General\') ON CONFLICT (nome) DO NOTHING')

    try:
        cursor.execute('ALTER TABLE produtos ADD COLUMN IF NOT EXISTS codigo_proveedor TEXT DEFAULT \'\'')
        cursor.execute('ALTER TABLE notas ADD COLUMN IF NOT EXISTS link_pdf TEXT DEFAULT \'\'')
        cursor.execute('ALTER TABLE notas ADD COLUMN IF NOT EXISTS link_qrcode TEXT DEFAULT \'\'')
    except Exception as e:
        print("Aviso na migração:", e)

    conexao.commit()
    cursor.close()
    conexao.close()

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
def cadastrar_produto(codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('''
        INSERT INTO produtos (codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (codigo_barras) DO UPDATE SET
        descricao = EXCLUDED.descricao,
        categoria = EXCLUDED.categoria,
        subcategoria = EXCLUDED.subcategoria,
        preco_custo = EXCLUDED.preco_custo,
        preco_venda = EXCLUDED.preco_venda,
        quantidade = EXCLUDED.quantidade,
        codigo_proveedor = EXCLUDED.codigo_proveedor
    ''', (codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor))
    conexao.commit()
    conexao.close()

def listar_produtos():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor FROM produtos')
    linhas = cursor.fetchall()
    conexao.close()
    return [{"codigo_barras": l[0], "descricao": l[1], "categoria": l[2], "subcategoria": l[3], "preco_custo": l[4], "preco_venda": l[5], "quantidade": l[6], "codigo_proveedor": l[7]} for l in linhas]

def buscar_produto_por_codigo(codigo_barras):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT * FROM produtos WHERE codigo_barras = %s', (codigo_barras,))
    l = cursor.fetchone()
    conexao.close()
    if l: return {"descricao": l[1], "preco_venda": l[5], "codigo_proveedor": l[7]}
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
def salvar_nota(ruc, cliente, valor, cdc, itens, link_pdf="", link_qrcode=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    itens_com_custo = []
    
    for item in itens:
        item_dict = item.dict() if hasattr(item, 'dict') else item
        
        if item_dict.get('codigo_barras'):
            cursor.execute('SELECT preco_custo FROM produtos WHERE codigo_barras = %s', (item_dict['codigo_barras'],))
            row = cursor.fetchone()
            item_dict['preco_custo'] = row[0] if row else 0
            cursor.execute('UPDATE produtos SET quantidade = quantidade - %s WHERE codigo_barras = %s', (item_dict.get('quantidade', 0), item_dict['codigo_barras']))
        else:
            item_dict['preco_custo'] = 0 
            
        itens_com_custo.append(item_dict)

    itens_json = json.dumps(itens_com_custo)
    
    cursor.execute('INSERT INTO notas (ruc_emissor, nome_cliente, valor_total, cdc, itens, link_pdf, link_qrcode) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                   (ruc, cliente, valor, cdc, itens_json, link_pdf, link_qrcode))
    conexao.commit()
    conexao.close()

def listar_todas_notas(busca=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    if busca: 
        cursor.execute("SELECT id, nome_cliente, valor_total, cdc, link_pdf, data_emissao FROM notas WHERE nome_cliente ILIKE %s OR cdc ILIKE %s ORDER BY id DESC", (f"%{busca}%", f"%{busca}%"))
    else: 
        cursor.execute('SELECT id, nome_cliente, valor_total, cdc, link_pdf, data_emissao FROM notas ORDER BY id DESC')
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome_cliente": l[1], "valor_total": l[2], "cdc": l[3], "link_pdf": l[4], "data_emissao": l[5]} for l in linhas]

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
            produtos_vendidos[nome] = produtos_vendidos.get(nome, 0) + qtd
                
    top_produtos = sorted(produtos_vendidos.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_vendas": total_vendas,
        "total_notas": total_notas,
        "top_produtos": [{"nome": p[0], "quantidade": p[1]} for p in top_produtos]
    }

# --- NOVO: CIERRE DE CAJA DETALHADO ITEM A ITEM ---
def obter_fechamento_caixa():
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT valor_total, itens FROM notas WHERE DATE(data_emissao) = CURRENT_DATE")
    notas_hoje = cursor.fetchall()
    
    total_vendas_hoje = 0
    lucro_bruto_hoje = 0
    total_notas_hoje = len(notas_hoje)
    
    # Agrupador inteligente de itens
    itens_agrupados = {}
    
    for nota in notas_hoje:
        total_vendas_hoje += nota[0]
        itens = json.loads(nota[1])
        for item in itens:
            preco_venda = item.get('preco_unitario', 0)
            preco_custo = item.get('preco_custo', 0)
            qtd = item.get('quantidade', 0)
            lucro_bruto_hoje += (preco_venda - preco_custo) * qtd
            
            # Agrupa para o relatório
            cod = item.get('codigo_barras')
            desc = item.get('descricao', 'Manual / Otros')
            chave = cod if cod else desc
            
            if chave not in itens_agrupados:
                itens_agrupados[chave] = {
                    "codigo_barras": cod,
                    "descricao": desc,
                    "vendidos": 0,
                    "estoque_restante": 0
                }
            itens_agrupados[chave]["vendidos"] += qtd
            
    # Busca o estoque restante ATUAL apenas para os itens que foram vendidos hoje
    lista_detalhada = list(itens_agrupados.values())
    for item in lista_detalhada:
        if item["codigo_barras"]:
            cursor.execute("SELECT quantidade FROM produtos WHERE codigo_barras = %s", (item["codigo_barras"],))
            row = cursor.fetchone()
            item["estoque_restante"] = row[0] if row else 0
        else:
            item["estoque_restante"] = "-" # Itens manuais não tem estoque

    # Ordena para os mais vendidos aparecerem no topo da tabela
    lista_detalhada.sort(key=lambda x: x["vendidos"], reverse=True)
    
    conexao.close()
    
    return {
        "vendas_hoje": total_vendas_hoje,
        "lucro_bruto": lucro_bruto_hoje,
        "notas_emitidas": total_notas_hoje,
        "detalhes_itens": lista_detalhada
    }