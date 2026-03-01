import os
import json
import psycopg2
from datetime import date, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conexao():
    return psycopg2.connect(DATABASE_URL)

def inicializar_banco():
    conexao = get_conexao()
    cursor = conexao.cursor()

    # 1. CRIAR AS TABELAS BASE
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id SERIAL PRIMARY KEY,
            nome_empresa TEXT,
            ruc TEXT UNIQUE,
            endereco TEXT,
            senha_certificado TEXT,
            caminho_certificado TEXT,
            ambiente_sifen TEXT DEFAULT 'testes',
            senha_admin TEXT DEFAULT 'admin123',
            senha_caixa TEXT DEFAULT 'caja123',
            plano TEXT DEFAULT 'Básico',
            status_assinatura TEXT DEFAULT 'Activo',
            data_vencimento DATE,
            valor_mensalidade REAL DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER DEFAULT 1,
            ruc_emissor TEXT,
            nome_cliente TEXT,
            valor_total REAL,
            cdc TEXT,
            itens TEXT,
            data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            link_pdf TEXT DEFAULT '',
            link_qrcode TEXT DEFAULT '',
            metodo_pago TEXT DEFAULT 'Efectivo',
            caixa_id INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produtos (
            codigo_barras TEXT,
            empresa_id INTEGER DEFAULT 1,
            descricao TEXT NOT NULL,
            categoria TEXT,
            subcategoria TEXT,
            preco_custo REAL,
            preco_venda REAL NOT NULL,
            quantidade INTEGER DEFAULT 0,
            codigo_proveedor TEXT DEFAULT '',
            PRIMARY KEY (empresa_id, codigo_barras)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER DEFAULT 1,
            nome TEXT NOT NULL,
            UNIQUE (empresa_id, nome)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS caixa_sessoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER DEFAULT 1,
            data_abertura TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_fechamento TIMESTAMP,
            valor_abertura REAL DEFAULT 0,
            valor_fechamento REAL,
            status TEXT DEFAULT 'ABERTO'
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS caixa_movimentacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER DEFAULT 1,
            caixa_id INTEGER,
            tipo TEXT,
            valor REAL,
            motivo TEXT,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. MIGRATIONS: Atualizando para o Painel Financeiro SaaS
    try:
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS plano TEXT DEFAULT 'Básico'")
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS status_assinatura TEXT DEFAULT 'Activo'")
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS data_vencimento DATE")
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS valor_mensalidade REAL DEFAULT 0")
    except Exception as e:
        print("Aviso Migration:", e)

    # 3. INSERÇÕES INICIAIS
    try:
        vencimento_inicial = date.today() + timedelta(days=365) # A sua própria loja tem 1 ano grátis
        cursor.execute('''
            INSERT INTO empresas (id, nome_empresa, ruc, senha_admin, senha_caixa, plano, status_assinatura, data_vencimento, valor_mensalidade) 
            VALUES (1, 'Mi Empresa S.A.', '80012345-6', 'admin123', 'caja123', 'Pro', 'Activo', %s, 0) 
            ON CONFLICT DO NOTHING
        ''', (vencimento_inicial,))
        
        cursor.execute("SELECT 1 FROM categorias WHERE nome = 'General' AND empresa_id = 1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO categorias (empresa_id, nome) VALUES (1, 'General')")
    except Exception as e:
        print("Aviso Insert Inicial:", e)

    conexao.commit()
    cursor.close()
    conexao.close()

if DATABASE_URL:
    inicializar_banco()

# --- SISTEMA DE AUTENTICAÇÃO E SUPER ADMIN ---
def autenticar_usuario(ruc, senha):
    if ruc == "NUBE" and senha == "nube2026":
        return {"sucesso": True, "empresa_id": 0, "rol": "superadmin"}

    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, senha_admin, senha_caixa, status_assinatura FROM empresas WHERE ruc = %s", (ruc,))
    empresa = cursor.fetchone()
    conexao.close()

    if not empresa:
        return {"sucesso": False, "mensagem": "Empresa (RUC) no encontrada"}

    emp_id, s_admin, s_caixa, status_ass = empresa
    
    # Bloqueia se a assinatura estiver cancelada (Opcional, mas recomendado para SaaS)
    if status_ass == 'Cancelado':
        return {"sucesso": False, "mensagem": "Su suscripción está cancelada. Contacte soporte."}

    if senha == s_admin:
        return {"sucesso": True, "empresa_id": emp_id, "rol": "admin"}
    elif senha == s_caixa:
        return {"sucesso": True, "empresa_id": emp_id, "rol": "cajero"}
    else:
        return {"sucesso": False, "mensagem": "Contraseña incorrecta"}

def obter_metricas_saas():
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    # Atualiza automaticamente o status para Vencido se a data passou
    cursor.execute("UPDATE empresas SET status_assinatura = 'Vencido' WHERE data_vencimento < CURRENT_DATE AND status_assinatura = 'Activo'")
    conexao.commit()

    cursor.execute("SELECT COUNT(*) FROM empresas WHERE status_assinatura = 'Activo'")
    clientes_ativos = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(valor_mensalidade) FROM empresas WHERE status_assinatura = 'Activo'")
    mrr = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM empresas WHERE status_assinatura = 'Vencido'")
    clientes_vencidos = cursor.fetchone()[0]
    
    conexao.close()
    return {
        "mrr": mrr,
        "clientes_ativos": clientes_ativos,
        "clientes_vencidos": clientes_vencidos
    }

def listar_todas_empresas():
    conexao = get_conexao()
    cursor = conexao.cursor()
    # Puxa os dados financeiros novos
    cursor.execute("SELECT id, nome_empresa, ruc, ambiente_sifen, plano, status_assinatura, data_vencimento, valor_mensalidade FROM empresas ORDER BY id ASC")
    linhas = cursor.fetchall()
    conexao.close()
    return [{
        "id": l[0], "nome": l[1], "ruc": l[2], "ambiente": l[3], 
        "plano": l[4], "status": l[5], "vencimento": str(l[6]) if l[6] else "N/A", "valor": l[7]
    } for l in linhas]

def criar_nova_empresa(nome, ruc, senha_admin, senha_caixa, plano, valor):
    conexao = get_conexao()
    cursor = conexao.cursor()
    vencimento = date.today() + timedelta(days=30) # Vence em 30 dias
    try:
        cursor.execute(
            "INSERT INTO empresas (nome_empresa, ruc, senha_admin, senha_caixa, plano, valor_mensalidade, status_assinatura, data_vencimento) VALUES (%s, %s, %s, %s, %s, %s, 'Activo', %s)", 
            (nome, ruc, senha_admin, senha_caixa, plano, valor, vencimento)
        )
        conexao.commit()
        return True, "Empresa creada exitosamente."
    except psycopg2.IntegrityError:
        return False, "Ya existe una empresa con este RUC."
    finally:
        conexao.close()

# --- FUNÇÕES FILTRADAS POR EMPRESA_ID ---
def status_caixa_atual(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, valor_abertura, data_abertura FROM caixa_sessoes WHERE empresa_id = %s AND status = 'ABERTO' ORDER BY id DESC LIMIT 1", (empresa_id,))
    linha = cursor.fetchone()
    conexao.close()
    if linha: return {"aberto": True, "caixa_id": linha[0], "valor_abertura": linha[1], "data_abertura": linha[2]}
    return {"aberto": False}

def abrir_caixa(empresa_id, valor_inicial):
    atual = status_caixa_atual(empresa_id)
    if atual["aberto"]: return False, "Ya existe una caja abierta."
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO caixa_sessoes (empresa_id, valor_abertura, status) VALUES (%s, %s, 'ABERTO')", (empresa_id, valor_inicial))
    conexao.commit()
    conexao.close()
    return True, "Caja abierta con éxito."

def fechar_caixa(empresa_id, valor_fechamento):
    atual = status_caixa_atual(empresa_id)
    if not atual["aberto"]: return False, "No hay caja abierta."
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("UPDATE caixa_sessoes SET status = 'FECHADO', data_fechamento = CURRENT_TIMESTAMP, valor_fechamento = %s WHERE id = %s AND empresa_id = %s", (valor_fechamento, atual["caixa_id"], empresa_id))
    conexao.commit()
    conexao.close()
    return True, "Caja cerrada con éxito."

def registrar_sangria(empresa_id, valor, motivo):
    atual = status_caixa_atual(empresa_id)
    if not atual["aberto"]: return False, "La caja debe estar abierta."
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("INSERT INTO caixa_movimentacoes (empresa_id, caixa_id, tipo, valor, motivo) VALUES (%s, %s, 'SANGRIA', %s, %s)", (empresa_id, atual["caixa_id"], valor, motivo))
    conexao.commit()
    conexao.close()
    return True, "Retiro registrado."

def cadastrar_categoria(empresa_id, nome):
    try:
        conexao = get_conexao()
        cursor = conexao.cursor()
        cursor.execute("SELECT 1 FROM categorias WHERE empresa_id = %s AND nome = %s", (empresa_id, nome))
        if cursor.fetchone():
            return False
        cursor.execute('INSERT INTO categorias (empresa_id, nome) VALUES (%s, %s)', (empresa_id, nome))
        conexao.commit()
        return True
    finally:
        if 'conexao' in locals(): conexao.close()

def listar_categorias(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT id, nome FROM categorias WHERE empresa_id = %s ORDER BY nome ASC', (empresa_id,))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome": l[1]} for l in linhas]

def deletar_categoria(empresa_id, id_categoria):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM categorias WHERE id = %s AND empresa_id = %s', (id_categoria, empresa_id))
    conexao.commit()
    conexao.close()

def obter_configuracao(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT nome_empresa, ruc, endereco, senha_certificado, caminho_certificado, ambiente_sifen FROM empresas WHERE id = %s', (empresa_id,))
    linha = cursor.fetchone()
    conexao.close()
    if linha: return {"nome_empresa": linha[0], "ruc": linha[1], "endereco": linha[2], "senha_certificado": linha[3], "caminho_certificado": linha[4], "ambiente_sifen": linha[5]}
    return None

def salvar_configuracao_texto(empresa_id, nome, ruc, endereco, senha):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('UPDATE empresas SET nome_empresa = %s, ruc = %s, endereco = %s, senha_certificado = %s WHERE id = %s', (nome, ruc, endereco, senha, empresa_id))
    conexao.commit()
    conexao.close()

def salvar_caminho_certificado(empresa_id, caminho):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('UPDATE empresas SET caminho_certificado = %s WHERE id = %s', (caminho, empresa_id))
    conexao.commit()
    conexao.close()

def alternar_ambiente_sifen(empresa_id, ambiente):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('UPDATE empresas SET ambiente_sifen = %s WHERE id = %s', (ambiente, empresa_id))
    conexao.commit()
    conexao.close()

def cadastrar_produto(empresa_id, codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('''
        INSERT INTO produtos (empresa_id, codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (empresa_id, codigo_barras) DO UPDATE SET
        descricao = EXCLUDED.descricao,
        categoria = EXCLUDED.categoria,
        subcategoria = EXCLUDED.subcategoria,
        preco_custo = EXCLUDED.preco_custo,
        preco_venda = EXCLUDED.preco_venda,
        quantidade = EXCLUDED.quantidade,
        codigo_proveedor = EXCLUDED.codigo_proveedor
    ''', (empresa_id, codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor))
    conexao.commit()
    conexao.close()

def listar_produtos(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor FROM produtos WHERE empresa_id = %s', (empresa_id,))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"codigo_barras": l[0], "descricao": l[1], "categoria": l[2], "subcategoria": l[3], "preco_custo": l[4], "preco_venda": l[5], "quantidade": l[6], "codigo_proveedor": l[7]} for l in linhas]

def buscar_produto_por_codigo(empresa_id, codigo_barras):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT * FROM produtos WHERE empresa_id = %s AND codigo_barras = %s', (empresa_id, codigo_barras))
    l = cursor.fetchone()
    conexao.close()
    if l: return {"descricao": l[2], "preco_venda": l[6], "codigo_proveedor": l[8]}
    return None

def deletar_produto(empresa_id, codigo_barras):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM produtos WHERE empresa_id = %s AND codigo_barras = %s', (empresa_id, codigo_barras))
    conexao.commit()
    conexao.close()

def salvar_nota(empresa_id, ruc, cliente, valor, cdc, itens, link_pdf="", link_qrcode="", metodo_pago="Efectivo"):
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    caixa_atual = status_caixa_atual(empresa_id)
    caixa_id = caixa_atual["caixa_id"] if caixa_atual["aberto"] else 0

    itens_com_custo = []
    for item in itens:
        item_dict = item.dict() if hasattr(item, 'dict') else item
        if item_dict.get('codigo_barras'):
            cursor.execute('SELECT preco_custo FROM produtos WHERE empresa_id = %s AND codigo_barras = %s', (empresa_id, item_dict['codigo_barras']))
            row = cursor.fetchone()
            item_dict['preco_custo'] = row[0] if row else 0
            cursor.execute('UPDATE produtos SET quantidade = quantidade - %s WHERE empresa_id = %s AND codigo_barras = %s', (item_dict.get('quantidade', 0), empresa_id, item_dict['codigo_barras']))
        else:
            item_dict['preco_custo'] = 0 
        itens_com_custo.append(item_dict)

    itens_json = json.dumps(itens_com_custo)
    
    cursor.execute('''
        INSERT INTO notas (empresa_id, ruc_emissor, nome_cliente, valor_total, cdc, itens, link_pdf, link_qrcode, metodo_pago, caixa_id) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (empresa_id, ruc, cliente, valor, cdc, itens_json, link_pdf, link_qrcode, metodo_pago, caixa_id))
    conexao.commit()
    conexao.close()

def listar_todas_notas(empresa_id, busca=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    if busca: 
        cursor.execute("SELECT id, nome_cliente, valor_total, cdc, link_pdf, data_emissao, metodo_pago FROM notas WHERE empresa_id = %s AND (nome_cliente ILIKE %s OR cdc ILIKE %s) ORDER BY id DESC", (empresa_id, f"%{busca}%", f"%{busca}%"))
    else: 
        cursor.execute('SELECT id, nome_cliente, valor_total, cdc, link_pdf, data_emissao, metodo_pago FROM notas WHERE empresa_id = %s ORDER BY id DESC', (empresa_id,))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome_cliente": l[1], "valor_total": l[2], "cdc": l[3], "link_pdf": l[4], "data_emissao": l[5], "metodo_pago": l[6]} for l in linhas]

def obter_dados_dashboard(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT valor_total, itens FROM notas WHERE empresa_id = %s', (empresa_id,))
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
    return {"total_vendas": total_vendas, "total_notas": total_notas, "top_produtos": [{"nome": p[0], "quantidade": p[1]} for p in top_produtos]}

def obter_fechamento_caixa(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT valor_total, itens, metodo_pago FROM notas WHERE empresa_id = %s AND DATE(data_emissao) = CURRENT_DATE", (empresa_id,))
    notas_hoje = cursor.fetchall()
    
    total_vendas_hoje = 0
    lucro_bruto_hoje = 0
    total_notas_hoje = len(notas_hoje)
    
    cursor.execute("SELECT SUM(valor) FROM caixa_movimentacoes WHERE empresa_id = %s AND tipo = 'SANGRIA' AND DATE(data) = CURRENT_DATE", (empresa_id,))
    total_sangrias = cursor.fetchone()[0] or 0
    
    itens_agrupados = {}
    
    for nota in notas_hoje:
        total_vendas_hoje += nota[0]
        itens = json.loads(nota[1])
        for item in itens:
            preco_venda = item.get('preco_unitario', 0)
            preco_custo = item.get('preco_custo', 0)
            qtd = item.get('quantidade', 0)
            lucro_bruto_hoje += (preco_venda - preco_custo) * qtd
            
            cod = item.get('codigo_barras')
            desc = item.get('descricao', 'Manual / Otros')
            chave = cod if cod else desc
            
            if chave not in itens_agrupados:
                itens_agrupados[chave] = {"codigo_barras": cod, "descricao": desc, "vendidos": 0, "estoque_restante": 0}
            itens_agrupados[chave]["vendidos"] += qtd
            
    lista_detalhada = list(itens_agrupados.values())
    for item in lista_detalhada:
        if item["codigo_barras"]:
            cursor.execute("SELECT quantidade FROM produtos WHERE empresa_id = %s AND codigo_barras = %s", (empresa_id, item["codigo_barras"]))
            row = cursor.fetchone()
            item["estoque_restante"] = row[0] if row else 0
        else:
            item["estoque_restante"] = "-"

    lista_detalhada.sort(key=lambda x: x["vendidos"], reverse=True)
    conexao.close()
    
    return {
        "vendas_hoje": total_vendas_hoje,
        "lucro_bruto": lucro_bruto_hoje,
        "notas_emitidas": total_notas_hoje,
        "total_sangrias": total_sangrias,
        "detalhes_itens": lista_detalhada
    }