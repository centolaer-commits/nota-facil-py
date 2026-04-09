import sys
import hashlib
import traceback
import os
import json
import psycopg2
import hashlib
import sys
from datetime import date, timedelta

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conexao():
    return psycopg2.connect(DATABASE_URL)

def hash_senha(senha):
    """Retorna hash SHA256 da senha"""
    return hashlib.sha256(senha.encode()).hexdigest()

def inicializar_banco():
    conexao = get_conexao()
    cursor = conexao.cursor()

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
            plano TEXT DEFAULT 'Inicial',
            status_assinatura TEXT DEFAULT 'Activo',
            data_vencimento DATE,
            valor_mensalidade REAL DEFAULT 0,
            csc TEXT DEFAULT ''
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL REFERENCES empresas(id) ON DELETE CASCADE,
            nome TEXT NOT NULL,
            email TEXT UNIQUE,
            senha_hash TEXT NOT NULL,
            rol TEXT NOT NULL CHECK (rol IN ('cajero', 'gerente')),
            ativo BOOLEAN DEFAULT TRUE,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proveedores (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER DEFAULT 1,
            nome TEXT NOT NULL,
            ruc TEXT,
            telefone TEXT,
            email TEXT,
            endereco TEXT,
            UNIQUE(empresa_id, ruc)
        )
    ''')

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS compras (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER DEFAULT 1,
                proveedor_id INTEGER,
                numero_factura TEXT,
                data_emissao DATE,
                valor_total REAL,
                itens TEXT,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    except Exception as e:
        pass

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS autofacturas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER DEFAULT 1,
                nome_vendedor TEXT,
                cedula_vendedor TEXT,
                endereco_vendedor TEXT,
                cdc TEXT,
                valor_total REAL,
                itens TEXT,
                data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                link_pdf TEXT DEFAULT '',
                link_qrcode TEXT DEFAULT ''
            )
        ''')
    except Exception as e:
        pass

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mermas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER DEFAULT 1,
                codigo_barras TEXT,
                descricao TEXT,
                quantidade INTEGER,
                custo_unitario REAL,
                motivo TEXT,
                data_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    except Exception as e:
        pass

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notas_credito (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER DEFAULT 1,
                cdc_referencia TEXT,
                cdc_novo TEXT,
                nome_cliente TEXT,
                valor_total REAL,
                itens TEXT,
                data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                link_pdf TEXT DEFAULT ''
            )
        ''')
    except Exception as e:
        pass
        
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notas_remision (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER DEFAULT 1,
                ruc_destinatario TEXT,
                nome_destinatario TEXT,
                motivo TEXT,
                chapa_vehiculo TEXT,
                dados_chofer TEXT,
                cdc TEXT,
                itens TEXT,
                data_emissao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                link_pdf TEXT DEFAULT '',
                link_qrcode TEXT DEFAULT ''
            )
        ''')
    except Exception as e:
        pass

    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auditorias (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER DEFAULT 1,
                data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                impacto_financeiro REAL DEFAULT 0,
                total_itens INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auditorias_itens (
                id SERIAL PRIMARY KEY,
                auditoria_id INTEGER,
                codigo_barras TEXT,
                descricao TEXT,
                qtd_sistema INTEGER,
                qtd_fisica INTEGER,
                diferenca INTEGER,
                custo_unitario REAL
            )
        ''')
        
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS plano TEXT DEFAULT 'Inicial'")
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS status_assinatura TEXT DEFAULT 'Activo'")
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS data_vencimento DATE")
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS valor_mensalidade REAL DEFAULT 0")
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS csc TEXT DEFAULT ''")
        # HERE IS THE NEW MERCADO PAGO TOKEN COLUMN
        cursor.execute("ALTER TABLE empresas ADD COLUMN IF NOT EXISTS mercado_pago_token TEXT DEFAULT ''")
    except Exception as e:
        pass

    try:
        vencimento_inicial = date.today() + timedelta(days=365)
        cursor.execute('''
            INSERT INTO empresas (id, nome_empresa, ruc, senha_admin, senha_caixa, plano, status_assinatura, data_vencimento, valor_mensalidade) 
            VALUES (1, 'Mi Empresa S.A.', '80012345-6', 'admin123', 'caja123', 'VIP', 'Activo', %s, 0) 
            ON CONFLICT DO NOTHING
        ''', (vencimento_inicial,))
        
        cursor.execute("SELECT 1 FROM categorias WHERE nome = 'General' AND empresa_id = 1")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO categorias (empresa_id, nome) VALUES (1, 'General')")
    except Exception as e:
        pass
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faturas_saas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER,
                valor REAL,
                data_vencimento TIMESTAMP,
                status TEXT DEFAULT 'Pendente',
                id_pagamento_mp TEXT
            )
        ''')
    except Exception as e:
        pass
    conexao.commit()
    cursor.close()
    conexao.close()

if DATABASE_URL:
    inicializar_banco()


def hash_senha(senha):
    """Retorna hash SHA256 da senha (consistente com frontend)"""
    return hashlib.sha256(senha.encode()).hexdigest()

def validar_plano_funcionario(plano_empresa, rol_funcionario):
    """Valida se o plano da empresa permite o tipo de funcionário"""
    # Gerentes só em planos VIP/Premium
    if rol_funcionario == 'gerente' and plano_empresa not in ['VIP', 'Premium']:
        return "Su plan actual no permite acceso como Gerente. Actualice al Plan VIP."
    
    # Cajeros em plano Inicial não são permitidos
    if rol_funcionario == 'cajero' and plano_empresa == 'Inicial':
        return "El Plan Inicial es para 1 solo usuario (el dueño). Actualice al Plan Crecimiento."
    
    return None # Sem restrições

def autenticar_usuario(identificador, senha_fornecida):
    """Autentica usuários com busca flexível (RUC -> Email fallback)"""
    print(f"[AUTH DEBUG] Tentativa de autenticação com identificador: '{identificador}'", file=sys.stderr)
    
    conexao = get_conexao()
    cursor = conexao.cursor()

    try:
        # ====================================================================
        # FASE 1: Buscar empresa por RUC (para donos e caixas legados)
        # ====================================================================
        cursor.execute("""
        SELECT id, senha_admin, senha_caixa, plano, nome_empresa
        FROM empresas
        WHERE ruc = %s
    """, (identificador,))

    empresa = cursor.fetchone()

    if empresa:
        emp_id, senha_admin, senha_caixa, plano, nome_empresa = empresa
        print(f"[AUTH DEBUG] Empresa encontrada via RUC: ID {emp_id}")

        # Verificar senhas de dono/admin (texto plano - legado)
        if senha_fornecida == senha_admin:
            print("[AUTH DEBUG] Senha de ADMIN correta")
            cursor.close()
            conexao.close()
            return {
                "sucesso": True,
                "empresa_id": emp_id,
                "rol": "admin",
                "plano": plano,
                "nome_empresa": nome_empresa
            }
        
        # Verificar senha de caixa (texto plano - legado)
        if senha_fornecida == senha_caixa:
                print(f"[AUTH DEBUG] Senha de CAJA correta", file=sys.stderr)
                cursor.close()
                conexao.close()
                return {
                    "sucesso": True,
                    "empresa_id": emp_id,
                    "rol": "cajero",
                    "plano": plano,
                    "nome_empresa": nome_empresa
                }

        # ====================================================================
        # FASE 2: Buscar funcionário por EMAIL (fallback)
        # ====================================================================
        print(f"[AUTH DEBUG] Buscando funcionário por email...", file=sys.stderr)
        
        cursor.execute("""
            SELECT f.id, f.rol, f.nome, f.email, f.empresa_id, e.plano, e.nome
            FROM funcionarios f
            JOIN empresas e ON f.empresa_id = e.id
            WHERE f.email = %s AND f.ativo = TRUE
        """, (identificador,))
        
        funcionario = cursor.fetchone()

        if funcionario:
            func_id, rol, nome_func, email, emp_id, plano, nome_empresa = funcionario
            
            # Verificar hash da senha
            senha_hash = hash_senha(senha_fornecida)
            cursor.execute("""
                SELECT id FROM funcionarios 
                WHERE id = %s AND senha_hash = %s
            """, (func_id, senha_hash))
            
            if cursor.fetchone():
                print(f"[AUTH DEBUG] Hash da senha do funcionário verificado com sucesso", file=sys.stderr)
                
                # Validar restrições de plano
                erro_plano = validar_plano_funcionario(plano, rol)
                if erro_plano:
                    cursor.close()
                    conexao.close()
                    return {"sucesso": False, "mensagem": erro_plano}
                
                cursor.close()
                conexao.close()
                return {
                    "sucesso": True,
                    "empresa_id": emp_id,
                    "rol": rol,
                    "plano": plano,
                    "funcionario_id": func_id,
                    "nome": nome_func,
                    "email": email,
                    "nome_empresa": nome_empresa
                }
            else:
                print(f"[AUTH DEBUG] Hash da senha do funcionário INCORRETO", file=sys.stderr)
                cursor.close()
                conexao.close()
                return {"sucesso": False, "mensagem": "Contraseña incorrecta"}

        # ====================================================================
        # FASE 3: Nenhum usuário encontrado
        # ====================================================================
        cursor.close()
        conexao.close()
        
        if '@' in identificador:
            return {"sucesso": False, "mensagem": "Email no registrado en el sistema"}
        else:
            return {"sucesso": False, "mensagem": "Empresa no registrada con ese RUC"}

    except Exception as e:
        print(f"[AUTH ERROR] Erro durante autenticação: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        try:
            cursor.close()
            conexao.close()
        except:
            pass
        return {"sucesso": False, "mensagem": "Error interno del servidor. Intente nuevamente."}

def adicionar_funcionario(empresa_id, nome, email, senha, rol):
    """Adiciona um novo funcionário para a empresa"""
    senha_hash = hash_senha(senha)
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("""
            INSERT INTO funcionarios (empresa_id, nome, email, senha_hash, rol)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (empresa_id, nome, email, senha_hash, rol))
        funcionario_id = cursor.fetchone()[0]
        conexao.commit()
        return {"sucesso": True, "id": funcionario_id}
    except psycopg2.IntegrityError as e:
        conexao.rollback()
        if "email" in str(e):
            return {"sucesso": False, "mensagem": "Email já cadastrado"}
        return {"sucesso": False, "mensagem": "Erro ao adicionar funcionário"}
    except Exception as e:
        conexao.rollback()
        return {"sucesso": False, "mensagem": f"Erro: {e}"}
    finally:
        cursor.close()
        conexao.close()

def listar_funcionarios(empresa_id):
    """Lista todos os funcionários de uma empresa"""
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT id, nome, email, rol, ativo, data_criacao
        FROM funcionarios
        WHERE empresa_id = %s
        ORDER BY nome
    """, (empresa_id,))
    resultados = cursor.fetchall()
    cursor.close()
    conexao.close()
    return [
        {
            "id": r[0],
            "nome": r[1],
            "email": r[2],
            "rol": r[3],
            "ativo": r[4],
            "data_criacao": r[5].isoformat() if r[5] else None
        }
        for r in resultados
    ]

def remover_funcionario(empresa_id, funcionario_id):
    """Remove ou desativa um funcionário"""
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        # Verificar se o funcionário pertence à empresa
        cursor.execute("SELECT id FROM funcionarios WHERE id = %s AND empresa_id = %s", (funcionario_id, empresa_id))
        if not cursor.fetchone():
            return {"sucesso": False, "mensagem": "Funcionário não encontrado"}
        
        # Desativar em vez de excluir (soft delete)
        cursor.execute("UPDATE funcionarios SET ativo = FALSE WHERE id = %s", (funcionario_id,))
        conexao.commit()
        return {"sucesso": True}
    except Exception as e:
        conexao.rollback()
        return {"sucesso": False, "mensagem": f"Erro: {e}"}
    finally:
        cursor.close()
        conexao.close()

def atualizar_funcionario(empresa_id, funcionario_id, nome=None, email=None, senha=None, rol=None, ativo=None):
    """Atualiza os dados de um funcionário"""
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        # Verificar se o funcionário pertence à empresa
        cursor.execute("SELECT id FROM funcionarios WHERE id = %s AND empresa_id = %s", (funcionario_id, empresa_id))
        if not cursor.fetchone():
            return {"sucesso": False, "mensagem": "Funcionário não encontrado"}
        
        updates = []
        params = []
        if nome is not None:
            updates.append("nome = %s")
            params.append(nome)
        if email is not None:
            updates.append("email = %s")
            params.append(email)
        if senha is not None:
            updates.append("senha_hash = %s")
            params.append(hash_senha(senha))
        if rol is not None:
            updates.append("rol = %s")
            params.append(rol)
        if ativo is not None:
            updates.append("ativo = %s")
            params.append(ativo)
        
        if not updates:
            return {"sucesso": False, "mensagem": "Nenhum campo para atualizar"}
        
        params.append(funcionario_id)
        cursor.execute(f"""
            UPDATE funcionarios 
            SET {', '.join(updates)}
            WHERE id = %s
        """, tuple(params))
        conexao.commit()
        return {"sucesso": True}
    except psycopg2.IntegrityError as e:
        conexao.rollback()
        if "email" in str(e):
            return {"sucesso": False, "mensagem": "Email já cadastrado"}
        return {"sucesso": False, "mensagem": "Erro ao atualizar funcionário"}
    except Exception as e:
        conexao.rollback()
        return {"sucesso": False, "mensagem": f"Erro: {e}"}
    finally:
        cursor.close()
        conexao.close()

def obter_metricas_saas():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("UPDATE empresas SET status_assinatura = 'Vencido' WHERE data_vencimento < CURRENT_DATE AND status_assinatura = 'Activo'")
    conexao.commit()
    cursor.execute("SELECT COUNT(*) FROM empresas WHERE status_assinatura = 'Activo'")
    clientes_ativos = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(valor_mensalidade) FROM empresas WHERE status_assinatura = 'Activo'")
    mrr = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM empresas WHERE status_assinatura = 'Vencido'")
    clientes_vencidos = cursor.fetchone()[0]
    conexao.close()
    return {"mrr": mrr, "clientes_ativos": clientes_ativos, "clientes_vencidos": clientes_vencidos}

def listar_todas_empresas():
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome_empresa, ruc, ambiente_sifen, plano, status_assinatura, data_vencimento, valor_mensalidade FROM empresas ORDER BY id ASC")
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome": l[1], "ruc": l[2], "ambiente": l[3], "plano": l[4], "status": l[5], "vencimento": str(l[6]) if l[6] else "N/A", "valor": l[7]} for l in linhas]

def criar_nova_empresa(nome, ruc, senha_admin, senha_caixa, plano, valor):
    conexao = get_conexao()
    cursor = conexao.cursor()
    vencimento = date.today() + timedelta(days=30)
    try:
        cursor.execute("INSERT INTO empresas (nome_empresa, ruc, senha_admin, senha_caixa, plano, valor_mensalidade, status_assinatura, data_vencimento) VALUES (%s, %s, %s, %s, %s, %s, 'Activo', %s)", (nome, ruc, senha_admin, senha_caixa, plano, valor, vencimento))
        conexao.commit()
        return True, "Empresa creada exitosamente."
    except psycopg2.IntegrityError:
        return False, "Ya existe una empresa con este RUC."
    finally:
        conexao.close()

def atualizar_plano_empresa(empresa_id, novo_plano, novo_valor):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("UPDATE empresas SET plano = %s, valor_mensalidade = %s WHERE id = %s", (novo_plano, novo_valor, empresa_id))
    conexao.commit()
    conexao.close()
    return True

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
    return True, "Caja abierta con Ã©xito."

def fechar_caixa(empresa_id, valor_fechamento):
    atual = status_caixa_atual(empresa_id)
    if not atual["aberto"]: return False, "No hay caja abierta."
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("UPDATE caixa_sessoes SET status = 'FECHADO', data_fechamento = CURRENT_TIMESTAMP, valor_fechamento = %s WHERE id = %s AND empresa_id = %s", (valor_fechamento, atual["caixa_id"], empresa_id))
    conexao.commit()
    conexao.close()
    return True, "Caja cerrada con Ã©xito."

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
        if cursor.fetchone(): return False
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
    # ADDED mercado_pago_token TO THE SELECT HERE
    cursor.execute('SELECT nome_empresa, ruc, endereco, senha_certificado, caminho_certificado, ambiente_sifen, csc, mercado_pago_token FROM empresas WHERE id = %s', (empresa_id,))
    linha = cursor.fetchone()
    conexao.close()
    if linha: return {"nome_empresa": linha[0], "ruc": linha[1], "endereco": linha[2], "senha_certificado": linha[3], "caminho_certificado": linha[4], "ambiente_sifen": linha[5], "csc": linha[6], "mercado_pago_token": linha[7]}
    return None

# UPDATED TO RECEIVE AND SAVE mercado_pago_token
def salvar_configuracao_texto(empresa_id, nome, ruc, endereco, senha, csc, mercado_pago_token=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('UPDATE empresas SET nome_empresa = %s, ruc = %s, endereco = %s, senha_certificado = %s, csc = %s, mercado_pago_token = %s WHERE id = %s', (nome, ruc, endereco, senha, csc, mercado_pago_token, empresa_id))
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

def salvar_auditoria_estoque(empresa_id, itens_auditados):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute("INSERT INTO auditorias (empresa_id) VALUES (%s) RETURNING id", (empresa_id,))
        auditoria_id = cursor.fetchone()[0]

        impacto_total = 0
        total_itens = 0

        for item in itens_auditados:
            cod = item['codigo_barras']
            fisica = item['qtd_fisica']

            cursor.execute("SELECT descricao, quantidade, preco_custo FROM produtos WHERE empresa_id = %s AND codigo_barras = %s", (empresa_id, cod))
            linha = cursor.fetchone()
            if not linha: continue

            desc, qtd_sis, custo = linha
            diferenca = fisica - qtd_sis
            impacto = diferenca * custo

            if diferenca != 0:
                impacto_total += impacto
                total_itens += 1
                cursor.execute("UPDATE produtos SET quantidade = %s WHERE empresa_id = %s AND codigo_barras = %s", (fisica, empresa_id, cod))
                cursor.execute("INSERT INTO auditorias_itens (auditoria_id, codigo_barras, descricao, qtd_sistema, qtd_fisica, diferenca, custo_unitario) VALUES (%s, %s, %s, %s, %s, %s, %s)", (auditoria_id, cod, desc, qtd_sis, fisica, diferenca, custo))

        cursor.execute("UPDATE auditorias SET impacto_financeiro = %s, total_itens = %s WHERE id = %s", (impacto_total, total_itens, auditoria_id))
        conexao.commit()
        return True, "AuditorÃ­a completada. Inventario actualizado."
    except Exception as e:
        conexao.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conexao.close()

def obter_relatorio_variancia(empresa_id, data_inicio, data_fim):
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    cursor.execute('''
        SELECT a.data AS fecha,
               ai.codigo_barras AS codigo,
               ai.descricao AS descricao,
               COALESCE(SUM(ai.diferenca), 0) AS total_unidades,
               COALESCE(SUM(ai.diferenca * ai.custo_unitario), 0) AS impacto_financeiro
        FROM auditorias a
        JOIN auditorias_itens ai ON a.id = ai.auditoria_id
        WHERE a.empresa_id = %s AND DATE(a.data) BETWEEN %s AND %s
        GROUP BY ai.codigo_barras, ai.descricao, a.data
        ORDER BY a.data DESC
    ''', (empresa_id, data_inicio, data_fim))
    
    dados = cursor.fetchall()
    conexao.close()
    
    resultado = []
    for fecha, codigo, descricao, total_unidades, impacto_financeiro in dados:
        resultado.append({
            "fecha": str(fecha)[:10],           # YYYY-MM-DD
            "codigo": codigo,                   # Código de barras
            "tipo": "Auditoria",                # Fixo para todas as linhas
            "descricao": descricao,             # Nome do produto
            "total_unidades": total_unidades,   # Soma das diferenças (pode ser negativo)
            "impacto_financeiro": impacto_financeiro  # Impacto em guaranies
        })
    
    return resultado

def listar_auditorias(empresa_id, data_inicio, data_fim):
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    cursor.execute('''
        SELECT id,
               data,
               COALESCE(impacto_financeiro, 0) AS impacto_financeiro,
               COALESCE(total_itens, 0) AS total_itens
        FROM auditorias
        WHERE empresa_id = %s AND DATE(data) BETWEEN %s AND %s
        ORDER BY data DESC
    ''', (empresa_id, data_inicio, data_fim))
    
    dados = cursor.fetchall()
    conexao.close()
    
    resultado = []
    for id, data, impacto_financeiro, total_itens in dados:
        resultado.append({
            "id": id,
            "data": str(data),                  # Data completa (YYYY-MM-DD)
            "impacto_financeiro": impacto_financeiro,  # Impacto total da auditoria
            "total_itens": total_itens          # Número de itens auditados
        })
    
    return resultado

def obter_detalhes_auditoria(empresa_id, auditoria_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('''
        SELECT codigo_barras, descricao, qtd_sistema, qtd_fisica, diferenca, custo_unitario
        FROM auditorias_itens
        WHERE auditoria_id = %s AND EXISTS (SELECT 1 FROM auditorias WHERE id = %s AND empresa_id = %s)
        ORDER BY id
    ''', (auditoria_id, auditoria_id, empresa_id))
    linhas = cursor.fetchall()
    conexao.close()
    resultado = []
    for codigo, descricao, qtd_sistema, qtd_fisica, diferenca, custo in linhas:
        resultado.append({
            "codigo": codigo,
            "descricao": descricao,
            "qtd_sistema": qtd_sistema,
            "qtd_fisica": qtd_fisica,
            "diferenca": diferenca,
            "impacto": diferenca * custo
        })
    return resultado

def registrar_merma(empresa_id, codigo_barras, quantidade, motivo):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute('SELECT descricao, preco_custo, quantidade FROM produtos WHERE empresa_id = %s AND codigo_barras = %s', (empresa_id, codigo_barras))
        prod = cursor.fetchone()
        if not prod: return False, "Producto no encontrado."
        desc, custo, qtd_atual = prod
        
        if qtd_atual < quantidade:
            return False, f"Stock insuficiente (Solo tienes {qtd_atual})."

        cursor.execute('UPDATE produtos SET quantidade = quantidade - %s WHERE empresa_id = %s AND codigo_barras = %s', (quantidade, empresa_id, codigo_barras))
        cursor.execute('INSERT INTO mermas (empresa_id, codigo_barras, descricao, quantidade, custo_unitario, motivo) VALUES (%s, %s, %s, %s, %s, %s)', (empresa_id, codigo_barras, desc, quantidade, custo, motivo))
        
        conexao.commit()
        return True, "Baja de producto registrada correctamente."
    except Exception as e:
        conexao.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conexao.close()

def listar_mermas(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT id, codigo_barras, descricao, quantidade, custo_unitario, motivo, data_registro FROM mermas WHERE empresa_id = %s ORDER BY id DESC', (empresa_id,))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "codigo": l[1], "descricao": l[2], "quantidade": l[3], "custo": l[4], "motivo": l[5], "data": str(l[6])[:16]} for l in linhas]

def salvar_nota_remision(empresa_id, ruc_dest, nome_dest, motivo, chapa, chofer, cdc, itens, link_pdf, link_qrcode):
    conexao = get_conexao()
    cursor = conexao.cursor()
    itens_json = json.dumps(itens)
    cursor.execute('''
        INSERT INTO notas_remision (empresa_id, ruc_destinatario, nome_destinatario, motivo, chapa_vehiculo, dados_chofer, cdc, itens, link_pdf, link_qrcode)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (empresa_id, ruc_dest, nome_dest, motivo, chapa, chofer, cdc, itens_json, link_pdf, link_qrcode))
    conexao.commit()
    conexao.close()

def listar_remisiones(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome_destinatario, motivo, cdc, link_pdf, data_emissao FROM notas_remision WHERE empresa_id = %s ORDER BY id DESC", (empresa_id,))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "destinatario": l[1], "motivo": l[2], "cdc": l[3], "link_pdf": l[4], "data": str(l[5])[:16]} for l in linhas]

def salvar_autofactura(empresa_id, nome_vendedor, cedula, endereco, cdc, itens, mover_stock, link_pdf, link_qrcode):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        valor_total = sum(i['quantidade'] * i['preco_unitario'] for i in itens)
        itens_json = json.dumps(itens)

        if mover_stock:
            for item in itens:
                cod = item.get('codigo_barras')
                qtd = item.get('quantidade', 0)
                preco = item.get('preco_unitario', 0)
                if cod:
                    cursor.execute('UPDATE produtos SET quantidade = quantidade + %s, preco_custo = %s WHERE empresa_id = %s AND codigo_barras = %s', (qtd, preco, empresa_id, cod))

        cursor.execute('''
            INSERT INTO autofacturas (empresa_id, nome_vendedor, cedula_vendedor, endereco_vendedor, cdc, valor_total, itens, link_pdf, link_qrcode)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (empresa_id, nome_vendedor, cedula, endereco, cdc, valor_total, itens_json, link_pdf, link_qrcode))

        caixa_atual = status_caixa_atual(empresa_id)
        if caixa_atual["aberto"]:
            cursor.execute("INSERT INTO caixa_movimentacoes (empresa_id, caixa_id, tipo, valor, motivo) VALUES (%s, %s, 'AUTOFACTURA', %s, %s)", (empresa_id, caixa_atual["caixa_id"], valor_total, f"Autofactura a {nome_vendedor}"))

        conexao.commit()
        return True, "Autofactura generada con Ã©xito."
    except Exception as e:
        conexao.rollback()
        return False, str(e)
    finally:
        cursor.close()
        conexao.close()

def listar_autofacturas(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT id, nome_vendedor, valor_total, cdc, link_pdf, data_emissao FROM autofacturas WHERE empresa_id = %s ORDER BY id DESC", (empresa_id,))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "vendedor": l[1], "valor": l[2], "cdc": l[3], "link_pdf": l[4], "data": str(l[5])[:16]} for l in linhas]

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

def salvar_nota_credito(empresa_id, cdc_ref, cdc_novo, cliente, valor, itens, link_pdf=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    itens_json = json.dumps(itens)
    
    for item in itens:
        if item.get('codigo_barras'):
            cursor.execute('UPDATE produtos SET quantidade = quantidade + %s WHERE empresa_id = %s AND codigo_barras = %s', (item.get('quantidade', 0), empresa_id, item['codigo_barras']))
            
    cursor.execute('''
        INSERT INTO notas_credito (empresa_id, cdc_referencia, cdc_novo, nome_cliente, valor_total, itens, link_pdf)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (empresa_id, cdc_ref, cdc_novo, cliente, valor, itens_json, link_pdf))
    conexao.commit()
    conexao.close()

def listar_todas_notas(empresa_id, busca="", data_inicio=None, data_fim=None):
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    query = "SELECT id, nome_cliente, valor_total, cdc, link_pdf, data_emissao, metodo_pago FROM notas WHERE empresa_id = %s"
    params = [empresa_id]
    
    if data_inicio and data_fim:
        query += " AND DATE(data_emissao) >= %s AND DATE(data_emissao) <= %s"
        params.extend([data_inicio, data_fim])
        
    if busca:
        query += " AND (nome_cliente ILIKE %s OR cdc ILIKE %s)"
        params.extend([f"%{busca}%", f"%{busca}%"])
        
    query += " ORDER BY id DESC"
    
    cursor.execute(query, tuple(params))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome_cliente": l[1], "valor_total": l[2], "cdc": l[3], "link_pdf": l[4], "data_emissao": l[5], "metodo_pago": l[6]} for l in linhas]

def gerar_vendas_mock_hoje(empresa_id):
    """Gera vendas fictícias para hoje, apenas para a demo."""
    conexao = get_conexao()
    cursor = conexao.cursor()
    # Verificar se a empresa é demo (RUC 9999999-9)
    cursor.execute('SELECT ruc FROM empresas WHERE id = %s', (empresa_id,))
    row = cursor.fetchone()
    if not row or row[0] != '9999999-9':
        conexao.close()
        return False
    # Buscar produtos existentes da empresa (todos)
    cursor.execute('SELECT codigo_barras, descricao, preco_venda FROM produtos WHERE empresa_id = %s', (empresa_id,))
    produtos = cursor.fetchall()
    if not produtos:
        conexao.close()
        return False
    import random
    from datetime import datetime, timedelta
    metodos = ['EFECTIVO', 'TARJETA', 'TRANSFERENCIA']
    clientes = ['Juan Pérez', 'María Gómez', 'Carlos López', 'Ana Martínez', 'Pedro Rodríguez',
                'Laura Silva', 'Roberto Fernández', 'Claudia Rojas', 'Miguel Ángel', 'Sofía Castro']
    # Gerar entre 5 e 15 vendas para hoje
    num_vendas = random.randint(5, 15)
    hoje = datetime.now().date()
    for i in range(num_vendas):
        # Horário aleatório ao longo do dia
        horas = random.randint(8, 20)
        minutos = random.randint(0, 59)
        data_emissao = datetime(hoje.year, hoje.month, hoje.day, horas, minutos)
        
        cliente = random.choice(clientes)
        metodo = random.choice(metodos)
        itens = []
        total = 0
        # 1 a 3 itens por venda
        for _ in range(random.randint(1, 3)):
            prod = random.choice(produtos)
            codigo = prod[0]
            descricao = prod[1]
            preco = prod[2]
            quantidade = random.randint(1, 6)
            # Calcular IVA (10%)
            iva_unitario = round(preco * 0.1, 0)
            itens.append({
                "codigo_barras": codigo,
                "descricao": descricao,
                "preco_unitario": preco,
                "quantidade": quantidade,
                "iva_unitario": int(iva_unitario),
                "subtotal": preco * quantidade,
                "iva_total": int(iva_unitario * quantidade)
            })
            total += preco * quantidade
        
        # CDC fictício
        cdc = f"1234567890{random.randint(10000, 99999)}"
        link_pdf = f"https://demo.nubepy.com/nota/{cdc}.pdf"
        
        cursor.execute('''
            INSERT INTO notas (empresa_id, nome_cliente, ruc_cliente, valor_total, itens, metodo_pago, data_emissao, ambiente, cdc, link_pdf)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (empresa_id, cliente, '123456-0', total, json.dumps(itens), metodo, data_emissao, 'testes', cdc, link_pdf))
    conexao.commit()
    cursor.close()
    conexao.close()
    print(f"[DEBUG] Geradas {num_vendas} vendas mock para hoje (empresa_id={empresa_id})")
    return True

def verificar_e_semear_demo(empresa_id):
    """Verifica se a empresa demo tem dados básicos; se não, semeia automaticamente."""
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT ruc FROM empresas WHERE id = %s', (empresa_id,))
    row = cursor.fetchone()
    if not row or row[0] != '9999999-9':
        conexao.close()
        return False  # Não é a empresa demo
    # Verificar se existem produtos
    cursor.execute('SELECT COUNT(*) FROM produtos WHERE empresa_id = %s', (empresa_id,))
    qtde_produtos = cursor.fetchone()[0]
    if qtde_produtos == 0:
        conexao.close()
        # Chamar a função de reset demo (que preenche produtos, fornecedores, categorias, vendas)
        injetar_dados_demo()
        return True  # Dados semeados
    # Verificar se há vendas hoje
    cursor.execute('SELECT COUNT(*) FROM notas WHERE empresa_id = %s AND DATE(data_emissao) = CURRENT_DATE', (empresa_id,))
    qtde_vendas_hoje = cursor.fetchone()[0]
    conexao.close()
    if qtde_vendas_hoje == 0:
        gerar_vendas_mock_hoje(empresa_id)
    return True

def obter_dados_dashboard(empresa_id):
    # Auto‑seed para demo (self‑healing)
    verificar_e_semear_demo(empresa_id)
    
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT valor_total, itens FROM notas WHERE empresa_id = %s AND DATE(data_emissao) = CURRENT_DATE', (empresa_id,))
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

def obter_fechamento_caixa(empresa_id, data_inicio=None, data_fim=None):
    conexao = get_conexao()
    cursor = conexao.cursor()
    
    if not data_inicio: data_inicio = str(date.today())
    if not data_fim: data_fim = str(date.today())
    
    cursor.execute("SELECT valor_total, itens, metodo_pago FROM notas WHERE empresa_id = %s AND DATE(data_emissao) >= %s AND DATE(data_emissao) <= %s", (empresa_id, data_inicio, data_fim))
    notas_periodo = cursor.fetchall()
    
    total_vendas_periodo = 0
    lucro_bruto_periodo = 0
    total_notas_periodo = len(notas_periodo)
    
    cursor.execute("SELECT SUM(valor) FROM caixa_movimentacoes WHERE empresa_id = %s AND tipo = 'SANGRIA' AND DATE(data) >= %s AND DATE(data) <= %s", (empresa_id, data_inicio, data_fim))
    total_sangrias = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(valor) FROM caixa_movimentacoes WHERE empresa_id = %s AND tipo = 'AUTOFACTURA' AND DATE(data) >= %s AND DATE(data) <= %s", (empresa_id, data_inicio, data_fim))
    total_autofacturas = cursor.fetchone()[0] or 0
    
    total_sangrias_geral = total_sangrias + total_autofacturas
    
    itens_agrupados = {}
    for nota in notas_periodo:
        total_vendas_periodo += nota[0]
        itens = json.loads(nota[1])
        for item in itens:
            preco_venda = item.get('preco_unitario', 0)
            preco_custo = item.get('preco_custo', 0)
            qtd = item.get('quantidade', 0)
            
            receita_item = preco_venda * qtd
            lucro_item = (preco_venda - preco_custo) * qtd
            lucro_bruto_periodo += lucro_item
            
            cod = item.get('codigo_barras')
            desc = item.get('descricao', 'Manual / Otros')
            chave = cod if cod else desc
            
            if chave not in itens_agrupados:
                itens_agrupados[chave] = {
                    "codigo_barras": cod, "descricao": desc, "vendidos": 0, "estoque_restante": 0, "receita_total": 0, "lucro_total": 0, "margem": 0
                }
            itens_agrupados[chave]["vendidos"] += qtd
            itens_agrupados[chave]["receita_total"] += receita_item
            itens_agrupados[chave]["lucro_total"] += lucro_item
            
    lista_detalhada = list(itens_agrupados.values())
    for item in lista_detalhada:
        if item["receita_total"] > 0:
            item["margem"] = round((item["lucro_total"] / item["receita_total"]) * 100, 1)
            
        if item["codigo_barras"]:
            cursor.execute("SELECT quantidade FROM produtos WHERE empresa_id = %s AND codigo_barras = %s", (empresa_id, item["codigo_barras"]))
            row = cursor.fetchone()
            item["estoque_restante"] = row[0] if row else 0
        else:
            item["estoque_restante"] = "-"

    lista_detalhada.sort(key=lambda x: x["receita_total"], reverse=True)
    
    # Construir lista de transações para tabela de cierre
    transacoes = []
    # Adicionar notas (vendas)
    cursor.execute("SELECT data_emissao, nome_cliente, valor_total, metodo_pago FROM notas WHERE empresa_id = %s AND DATE(data_emissao) >= %s AND DATE(data_emissao) <= %s ORDER BY data_emissao DESC", (empresa_id, data_inicio, data_fim))
    notas = cursor.fetchall()
    for data_emissao, nome_cliente, valor_total, metodo_pago in notas:
        transacoes.append({
            "fecha_hora": str(data_emissao)[:16],  # YYYY-MM-DD HH:MM
            "tipo": "VENTA",
            "monto": valor_total,
            "detalle": f"{nome_cliente} ({metodo_pago})"
        })
    
    # Adicionar sangrias
    cursor.execute("SELECT data, motivo, valor FROM caixa_movimentacoes WHERE empresa_id = %s AND tipo = 'SANGRIA' AND DATE(data) >= %s AND DATE(data) <= %s ORDER BY data DESC", (empresa_id, data_inicio, data_fim))
    sangrias = cursor.fetchall()
    for data, motivo, valor in sangrias:
        transacoes.append({
            "fecha_hora": str(data)[:16],
            "tipo": "SANGRIA",
            "monto": valor,
            "detalle": motivo
        })
    
    # Adicionar autofacturas
    cursor.execute("SELECT data, motivo, valor FROM caixa_movimentacoes WHERE empresa_id = %s AND tipo = 'AUTOFACTURA' AND DATE(data) >= %s AND DATE(data) <= %s ORDER BY data DESC", (empresa_id, data_inicio, data_fim))
    autofacturas = cursor.fetchall()
    for data, motivo, valor in autofacturas:
        transacoes.append({
            "fecha_hora": str(data)[:16],
            "tipo": "AUTOFACTURA",
            "monto": valor,
            "detalle": motivo
        })
    
    # Ordenar transações por data decrescente
    transacoes.sort(key=lambda x: x["fecha_hora"], reverse=True)
    
    conexao.close()
    
    return {
        "vendas_hoje": total_vendas_periodo, 
        "lucro_bruto": lucro_bruto_periodo, 
        "notas_emitidas": total_notas_periodo, 
        "total_sangrias": total_sangrias_geral, 
        "detalhes_itens": lista_detalhada,
        "transacoes": transacoes
    }

def cadastrar_proveedor(empresa_id, nome, ruc, telefone="", email="", endereco=""):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute('''
            INSERT INTO proveedores (empresa_id, nome, ruc, telefone, email, endereco)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (empresa_id, ruc) DO UPDATE SET
            nome = EXCLUDED.nome,
            telefone = EXCLUDED.telefone,
            email = EXCLUDED.email,
            endereco = EXCLUDED.endereco
        ''', (empresa_id, nome, ruc, telefone, email, endereco))
        conexao.commit()
        return True, "Proveedor guardado con Ã©xito."
    except Exception as e:
        conexao.rollback()
        return False, f"Error al guardar: {str(e)}"
    finally:
        cursor.close()
        conexao.close()

def editar_proveedor(empresa_id, proveedor_id, nome, ruc, telefone, email, endereco):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        cursor.execute('''
            UPDATE proveedores 
            SET nome = %s, ruc = %s, telefone = %s, email = %s, endereco = %s 
            WHERE id = %s AND empresa_id = %s
        ''', (nome, ruc, telefone, email, endereco, proveedor_id, empresa_id))
        conexao.commit()
        return True, "Proveedor actualizado con Ã©xito."
    except Exception as e:
        conexao.rollback()
        return False, f"Error al actualizar: {str(e)}"
    finally:
        cursor.close()
        conexao.close()

def listar_proveedores(empresa_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('SELECT id, nome, ruc, telefone, email, endereco FROM proveedores WHERE empresa_id = %s ORDER BY nome ASC', (empresa_id,))
    linhas = cursor.fetchall()
    conexao.close()
    return [{"id": l[0], "nome": l[1], "ruc": l[2], "telefone": l[3], "email": l[4], "endereco": l[5]} for l in linhas]

def deletar_proveedor(empresa_id, proveedor_id):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute('DELETE FROM proveedores WHERE empresa_id = %s AND id = %s', (empresa_id, proveedor_id))
    conexao.commit()
    conexao.close()

def salvar_entrada_factura(empresa_id, proveedor_id, numero_factura, data_emissao, itens):
    conexao = get_conexao()
    cursor = conexao.cursor()
    try:
        valor_total = 0
        itens_json = json.dumps(itens)
        
        for item in itens:
            cod = item['codigo_barras']
            qtd = item['quantidade']
            custo = item['custo_unitario']
            
            subtotal = qtd * custo
            valor_total += subtotal
            
            cursor.execute('''
                UPDATE produtos 
                SET quantidade = quantidade + %s, preco_custo = %s 
                WHERE empresa_id = %s AND codigo_barras = %s
            ''', (qtd, custo, empresa_id, cod))
        
        cursor.execute('''
            INSERT INTO compras (empresa_id, proveedor_id, numero_factura, data_emissao, valor_total, itens)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (empresa_id, proveedor_id, numero_factura, data_emissao, valor_total, itens_json))
        
        conexao.commit()
        return True, "Entrada registrada y stock actualizado."
    except Exception as e:
        conexao.rollback()
        return False, f"Error al guardar entrada: {str(e)}"
    finally:
        cursor.close()
        conexao.close()

def validar_senha_admin(empresa_id, senha):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT senha_admin FROM empresas WHERE id = %s", (empresa_id,))
    linha = cursor.fetchone()
    conexao.close()
    if linha and linha[0] == senha:
        return True
    return False

def obter_nota_por_cdc(empresa_id, cdc):
    conexao = get_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT ruc_emissor, nome_cliente, valor_total, itens, data_emissao, link_qrcode, metodo_pago FROM notas WHERE empresa_id = %s AND cdc = %s", (empresa_id, cdc))
    linha = cursor.fetchone()
    conexao.close()
    if linha:
        return {
            "ruc_emissor": linha[0], "nome_cliente": linha[1], "valor_total": linha[2],
            "itens": json.loads(linha[3]), "data_emissao": str(linha[4])[:16],
            "link_qrcode": linha[5], "metodo_pago": linha[6]
        }
    return None

def injetar_dados_demo():
    """Cria o usuÃ¡rio de teste pÃºblico (RUC 9999999-9) com dados completos de demonstraÃ§Ã£o"""
    conexao = None
    cursor = None
    try:
        import random
        from datetime import datetime, date, timedelta
        
        conexao = get_conexao()
        cursor = conexao.cursor()
        
        vencimento = date.today() + timedelta(days=365)
        
        # Verificar se empresa demo jÃ¡ existe
        cursor.execute("SELECT id FROM empresas WHERE ruc = %s", ('9999999-9',))
        existing = cursor.fetchone()
        
        if existing:
            empresa_id = existing[0]
            print(f"[DEMO] Empresa demo jÃ¡ existe (ID: {empresa_id}).")
        else:
            # Inserir empresa demo
            cursor.execute('''
                INSERT INTO empresas (nome_empresa, ruc, senha_admin, senha_caixa, plano, status_assinatura, data_vencimento, valor_mensalidade)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', ('UsuÃ¡rio PÃºblico Demo', '9999999-9', 'demo123', 'demo123', 'Demo', 'Activo', vencimento, 0))
            
            empresa_id = cursor.fetchone()[0]
            print(f"[DEMO] Empresa demo criada (ID: {empresa_id}).")
        
        # ========== LIMPEZA SELETIVA ==========
        print(f"[DEMO] LIMPEZA FORÃ‡ADA: Deletando vendas e produtos existentes para empresa ID {empresa_id}...")
        
        # 1. Notas (vendas)
        cursor.execute("DELETE FROM notas WHERE empresa_id = %s", (empresa_id,))
        notas_deleted = cursor.rowcount
        print(f"[DEMO]   - Notas removidas: {notas_deleted}")
        
        # 2. Produtos
        cursor.execute("DELETE FROM produtos WHERE empresa_id = %s", (empresa_id,))
        produtos_deleted = cursor.rowcount
        print(f"[DEMO]   - Produtos removidos: {produtos_deleted}")
        
        # 3. Outras tabelas (se existirem)
        try:
            cursor.execute("DELETE FROM compras WHERE empresa_id = %s", (empresa_id,))
            print(f"[DEMO]   - Compras removidas: {cursor.rowcount}")
        except:
            pass
        
        try:
            cursor.execute("DELETE FROM autofacturas WHERE empresa_id = %s", (empresa_id,))
            print(f"[DEMO]   - Autofacturas removidas: {cursor.rowcount}")
        except:
            pass
        
        try:
            cursor.execute("DELETE FROM mermas WHERE empresa_id = %s", (empresa_id,))
            print(f"[DEMO]   - Mermas removidas: {cursor.rowcount}")
        except:
            pass
        
        try:
            cursor.execute("DELETE FROM notas_credito WHERE empresa_id = %s", (empresa_id,))
            print(f"[DEMO]   - Notas crÃ©dito removidas: {cursor.rowcount}")
        except:
            pass
        
        try:
            cursor.execute("DELETE FROM notas_remision WHERE empresa_id = %s", (empresa_id,))
            print(f"[DEMO]   - Notas remisiÃ³n removidas: {cursor.rowcount}")
        except:
            pass
        
        # NÃƒO deletar categorias e provedores (podem ter constraints Ãºnicas)
        print(f"[DEMO] LIMPEZA FORÃ‡ADA CONCLUÃDA. Categorias e provedores mantidos.")
        
        # ========== CATEGORIAS ==========
        categorias = ['General', 'Bebidas', 'LÃ¡cteos', 'Limpeza', 'Enlatados', 'PanaderÃ­a', 'Carnes']
        total_categorias = 0
        for cat in categorias:
            cursor.execute('''
                INSERT INTO categorias (empresa_id, nome)
                VALUES (%s, %s)
            ''', (empresa_id, cat))
            total_categorias += cursor.rowcount
        print(f"[DEMO] {total_categorias}/{len(categorias)} categorias criadas.")
        
        # ========== PROVEDORES ==========
        provedores = [
            ('Distribuidora Central S.A.', '80012345-1', '021 234 567', 'ventas@distcentral.com.py', 'Av. Eusebio Ayala km 4.5, AsunciÃ³n'),
            ('Importadora del Este S.R.L.', '80023456-2', '021 345 678', 'contacto@importeste.com.py', 'Av. EspaÃ±a 1234, Ciudad del Este'),
            ('Proveedores del Sur S.A.', '80034567-3', '021 456 789', 'info@proveedorsur.com.py', 'Av. San MartÃ­n 567, EncarnaciÃ³n'),
            ('Alimentos Norte S.A.', '80045678-4', '021 567 890', 'ventas@alimentosnorte.com.py', 'Av. PerÃº 789, ConcepciÃ³n'),
            ('Mayorista Py S.R.L.', '80056789-5', '021 678 901', 'pedidos@mayoristapy.com.py', 'Av. BrasÃ­lia 456, Pedro Juan Caballero')
        ]
        
        total_provedores = 0
        for nome, ruc, telefone, email, endereco in provedores:
            cursor.execute('''
                INSERT INTO proveedores (empresa_id, nome, ruc, telefone, email, endereco)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (empresa_id, nome, ruc, telefone, email, endereco))
            total_provedores += cursor.rowcount
        print(f"[DEMO] {total_provedores}/{len(provedores)} provedores criados.")
        
        # ========== PRODUTOS ==========
        produtos = [
            # CÃ³digo, DescriÃ§Ã£o, Categoria, Subcategoria, Custo, Venda, Estoque
            ('ARR-001', 'Arroz Premium 1kg', 'General', '', 10000, 12500, 45),
            ('ACE-002', 'Aceite Girasol 900ml', 'General', '', 15000, 18500, 28),
            ('AZU-003', 'AzÃºcar Refinado 1kg', 'General', '', 7000, 8500, 62),
            ('COC-004', 'Coca-Cola 2L', 'Bebidas', 'Gaseosas', 8000, 10500, 36),
            ('SPR-005', 'Sprite 1.5L', 'Bebidas', 'Gaseosas', 7500, 9800, 42),
            ('CER-006', 'Cerveza Pilsen 1L', 'Bebidas', 'AlcohÃ³licas', 12000, 15800, 24),
            ('LEH-007', 'Leche Entera 1L', 'LÃ¡cteos', '', 6000, 8500, 58),
            ('YOU-008', 'Yogur Natural 1kg', 'LÃ¡cteos', '', 8500, 11500, 32),
            ('QUE-009', 'Queso Paraguay 500g', 'LÃ¡cteos', '', 22000, 28500, 18),
            ('JAB-010', 'JabÃ³n en Polvo 3kg', 'Limpeza', '', 25000, 32500, 22),
            ('DET-011', 'Detergente LÃ­quido 1L', 'Limpeza', '', 12000, 16500, 40),
            ('PAP-012', 'Papel HigiÃ©nico 4un', 'Limpeza', '', 15000, 19500, 55),
            ('ATA-013', 'AtÃºn en Lata 200g', 'Enlatados', '', 7500, 9800, 30),
            ('MAI-014', 'MaÃ­z en Lata 400g', 'Enlatados', '', 6500, 8200, 38),
            ('PAN-015', 'Pan FrancÃªs un', 'PanaderÃ­a', '', 1500, 2500, 120),
            ('RES-016', 'Carne Res 1kg', 'Carnes', '', 35000, 45500, 15),
            ('POL-017', 'Pollo Entero 1.5kg', 'Carnes', '', 22000, 29500, 20),
            ('JAM-018', 'JamÃ³n Cocido 200g', 'Carnes', '', 12500, 16800, 25),
            ('GAL-019', 'Galletas MarÃ­a 500g', 'PanaderÃ­a', '', 4500, 6500, 48),
            ('CAF-020', 'CafÃ© Molido 500g', 'Bebidas', '', 18000, 23500, 16)
        ]
        
        total_produtos = 0
        for cod, desc, cat, subcat, custo, venda, qtd in produtos:
            cursor.execute('''
                INSERT INTO produtos (empresa_id, codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '')
            ''', (empresa_id, cod, desc, cat, subcat, custo, venda, qtd))
            total_produtos += cursor.rowcount
        print(f"[DEMO] {total_produtos}/{len(produtos)} produtos criados.")
        
        # ========== VENDAS (ÃšLTIMOS 30 DIAS) ==========
        metodos_pago = ['Efectivo', 'Tarjeta', 'Transferencia', 'Efectivo', 'Tarjeta']
        clientes = [
            ('Consumidor Final', '80012345-1'),
            ('Juan PÃ©rez', '1234567-8'),
            ('MarÃ­a GonzÃ¡lez', '2345678-9'),
            ('Carlos LÃ³pez', '3456789-0'),
            ('Ana MartÃ­nez', '4567890-1'),
            ('Luis RodrÃ­guez', '5678901-2'),
            ('Supermercado Central', '80098765-4'),
            ('Restaurante El Buen Sabor', '80087654-3')
        ]
        
        # ========== CAIXA ABERTO (PARA DEMO) ==========
        # Verificar se jÃ¡ existe uma sessÃ£o de caixa aberta
        cursor.execute('''
            SELECT id FROM caixa_sessoes 
            WHERE empresa_id = %s AND status = 'ABERTO'
        ''', (empresa_id,))
        caixa_row = cursor.fetchone()
        if not caixa_row:
            cursor.execute('''
                INSERT INTO caixa_sessoes (empresa_id, data_abertura, valor_abertura, status)
                VALUES (%s, CURRENT_TIMESTAMP, 500000, 'ABERTO')
                RETURNING id
            ''', (empresa_id,))
            caixa_id = cursor.fetchone()[0]
            print(f"[DEMO] SessÃ£o de caixa aberta criada (ID: {caixa_id}).")
        else:
            caixa_id = caixa_row[0]
            print(f"[DEMO] SessÃ£o de caixa aberta jÃ¡ existe (ID: {caixa_id}).")
        
        # Gerar 25 vendas nos Ãºltimos 30 dias
        # As primeiras 5 vendas sÃ£o de hoje para aparecer no dashboard
        hoje = datetime.now()
        total_vendas = 0
        for i in range(25):
            # Data aleatÃ³ria nos Ãºltimos 30 dias
            if i < 5:
                dias_atras = 0  # Hoje - para dashboard
            else:
                dias_atras = random.randint(1, 30)
            horas_atras = random.randint(0, 23)
            minutos_atras = random.randint(0, 59)
            data_venda = hoje - timedelta(days=dias_atras, hours=horas_atras, minutes=minutos_atras)
            
            # Selecionar cliente aleatÃ³rio
            nome_cliente, ruc_cliente = random.choice(clientes)
            
            # Selecionar 1 a 4 produtos aleatÃ³rios para esta venda
            num_itens = random.randint(1, 4)
            itens_selecionados = random.sample(produtos[:15], num_itens)  # Usar apenas os primeiros 15 para variar
            
            itens_json = []
            valor_total = 0
            
            for prod in itens_selecionados:
                codigo, descricao, categoria, subcat, custo, venda, estoque = prod
                quantidade = random.randint(1, 3)
                subtotal = venda * quantidade
                valor_total += subtotal
                
                itens_json.append({
                    'codigo_barras': codigo,
                    'codigo': codigo,
                    'descricao': descricao,
                    'quantidade': quantidade,
                    'preco_unitario': venda,
                    'preco_custo': custo,
                    'subtotal': subtotal
                })
            
            # CDC fictÃ­cio (Ãºnico)
            cdc = f'9999999-9-{data_venda.strftime("%Y%m%d")}-{i:06d}'
            
            # MÃ©todo de pago aleatÃ³rio
            metodo = random.choice(metodos_pago)
            
            cursor.execute('''
                INSERT INTO notas (empresa_id, ruc_emissor, nome_cliente, valor_total, cdc, itens, data_emissao, metodo_pago, caixa_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                empresa_id,
                '9999999-9',
                nome_cliente,
                valor_total,
                cdc,
                json.dumps(itens_json),
                data_venda,
                metodo,
                caixa_id
            ))
            total_vendas += cursor.rowcount
        print(f"[DEMO] {total_vendas}/25 vendas histÃ³ricas criadas.")
        conexao.commit()
        print(f"[DEMO] âœ… Dados de demo completos injetados com sucesso. Empresa ID: {empresa_id}")
        print(f"[DEMO]   - {total_categorias}/{len(categorias)} categorias")
        print(f"[DEMO]   - {total_provedores}/{len(provedores)} provedores")
        print(f"[DEMO]   - {total_produtos}/{len(produtos)} produtos")
        print(f"[DEMO]   - {total_vendas}/25 vendas histÃ³ricas")
        return empresa_id
        
    except Exception as e:
        print(f"[DEMO ERRO] {e}")
        import traceback
        traceback.print_exc()
        if conexao:
            conexao.rollback()
        # NÃ£o propaga o erro para nÃ£o crashar o servidor
        return None
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()
