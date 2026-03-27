import sqlite3
import uuid

# Conecta ao arquivo do banco de dados (se não existir, ele cria automaticamente)
conexao = sqlite3.connect("notas_fiscais.db", check_same_thread=False)
cursor = conexao.cursor()

# Cria a "tabela" (como se fosse uma aba de Excel) para guardar as notas
cursor.execute('''
    CREATE TABLE IF NOT EXISTS notas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ruc_emissor TEXT,
        nome_cliente TEXT,
        valor_total REAL,
        cdc TEXT
    )
''')
conexao.commit()

def salvar_nota(ruc, cliente, valor, cdc):
    # Insere uma nova linha na nossa tabela com os dados da venda
    cursor.execute('''
        INSERT INTO notas (ruc_emissor, nome_cliente, valor_total, cdc)
        VALUES (?, ?, ?, ?)
    ''', (ruc, cliente, valor, cdc))
    conexao.commit()

def listar_todas_notas():
    # Busca todas as notas salvas para mostrarmos no painel no futuro
    cursor.execute('SELECT * FROM notas')
    linhas = cursor.fetchall()
    
    # Formata os dados para ficarem bonitos na resposta da API
    notas_formatadas = []
    for linha in linhas:
        notas_formatadas.append({
            "id": linha[0],
            "ruc_emissor": linha[1],
            "nome_cliente": linha[2],
            "valor_total": linha[3],
            "cdc": linha[4]
        })
    return notas_formatadas