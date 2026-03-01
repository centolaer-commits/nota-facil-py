from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil

from gerador_xml import construir_xml_sifen
from assinador_xml import assinar_documento
from gerador_pdf import gerar_pdf_nota
import banco_dados

app = FastAPI(title="NubePY SaaS - SIFEN")

if not os.path.exists("notas_pdf"): os.makedirs("notas_pdf")
if not os.path.exists("certificados"): os.makedirs("certificados")

# --- MODELOS DE DADOS ---
class ProdutoNovo(BaseModel):
    codigo_barras: str
    descricao: str
    categoria: str
    subcategoria: str
    preco_custo: float
    preco_venda: float
    quantidade: int
    codigo_proveedor: Optional[str] = ""

class ItemNota(BaseModel):
    codigo_barras: Optional[str] = None
    descricao: str
    quantidade: int
    preco_unitario: float

class DadosNota(BaseModel):
    ruc_emissor: str
    nome_cliente: str
    valor_total: float
    itens: List[ItemNota]
    metodo_pago: Optional[str] = "Efectivo"

class CategoriaNova(BaseModel):
    nome: str

class CaixaAbertura(BaseModel):
    valor_inicial: float

class CaixaFechamento(BaseModel):
    valor_final: float

class DadosSangria(BaseModel):
    valor: float
    motivo: str

class AmbienteUpdate(BaseModel):
    ambiente: str

# --- ROTAS DE CONTROLE DE CAIXA E SANGRÍA ---
@app.get("/status-caixa")
def status_caixa(x_empresa_id: int = Header(1)):
    return banco_dados.status_caixa_atual(x_empresa_id)

@app.post("/abrir-caixa")
def abrir_caixa(dados: CaixaAbertura, x_empresa_id: int = Header(1)):
    sucesso, mensagem = banco_dados.abrir_caixa(x_empresa_id, dados.valor_inicial)
    if sucesso: return {"mensaje": mensagem}
    raise HTTPException(status_code=400, detail=mensagem)

@app.post("/fechar-caixa")
def fechar_caixa(dados: CaixaFechamento, x_empresa_id: int = Header(1)):
    sucesso, mensagem = banco_dados.fechar_caixa(x_empresa_id, dados.valor_final)
    if sucesso: return {"mensaje": mensagem}
    raise HTTPException(status_code=400, detail=mensagem)

@app.post("/registrar-sangria")
def api_registrar_sangria(dados: DadosSangria, x_empresa_id: int = Header(1)):
    sucesso, msg = banco_dados.registrar_sangria(x_empresa_id, dados.valor, dados.motivo)
    if sucesso: return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

# --- ROTAS DE CATEGORIAS ---
@app.post("/cadastrar-categoria")
def cadastrar_categoria(cat: CategoriaNova, x_empresa_id: int = Header(1)):
    sucesso = banco_dados.cadastrar_categoria(x_empresa_id, cat.nome.strip())
    if sucesso: return {"mensaje": "Categoría creada con éxito"}
    raise HTTPException(status_code=400, detail="Esta categoría ya existe")

@app.get("/listar-categorias")
def listar_categorias(x_empresa_id: int = Header(1)):
    return banco_dados.listar_categorias(x_empresa_id)

@app.delete("/deletar-categoria/{id_categoria}")
def deletar_categoria(id_categoria: int, x_empresa_id: int = Header(1)):
    banco_dados.deletar_categoria(x_empresa_id, id_categoria)
    return {"mensaje": "Categoría eliminada"}

# --- ROTAS DE CONFIGURAÇÃO DA EMPRESA ---
@app.get("/obter-configuracao")
def obter_configuracao(x_empresa_id: int = Header(1)):
    return banco_dados.obter_configuracao(x_empresa_id)

@app.post("/salvar-configuracao")
def salvar_configuracao(nome_empresa: str = Form(...), ruc: str = Form(...), endereco: str = Form(""), senha_certificado: str = Form(""), x_empresa_id: int = Header(1)):
    banco_dados.salvar_configuracao_texto(x_empresa_id, nome_empresa, ruc, endereco, senha_certificado)
    return {"mensaje": "Datos guardados"}

@app.post("/upload-certificado")
def upload_certificado(arquivo: UploadFile = File(...), x_empresa_id: int = Header(1)):
    if not arquivo.filename.endswith(('.p12', '.pfx')): raise HTTPException(status_code=400, detail="Formato inválido.")
    caminho_destino = f"certificados/emp_{x_empresa_id}_{arquivo.filename}"
    with open(caminho_destino, "wb") as buffer: shutil.copyfileobj(arquivo.file, buffer)
    banco_dados.salvar_caminho_certificado(x_empresa_id, caminho_destino)
    return {"mensaje": "Certificado digital subido"}

# NOVO: ROTA PARA ALTERAR O AMBIENTE SIFEN (TESTE VS PRODUÇÃO)
@app.post("/alternar-ambiente")
def alternar_ambiente(dados: AmbienteUpdate, x_empresa_id: int = Header(1)):
    if dados.ambiente not in ["testes", "produccion"]:
        raise HTTPException(status_code=400, detail="Ambiente inválido")
    banco_dados.alternar_ambiente_sifen(x_empresa_id, dados.ambiente)
    return {"mensaje": f"Ambiente cambiado a {dados.ambiente.upper()}"}

# --- ROTAS DE ESTOQUE E VENDAS ---
@app.get("/dados-dashboard")
def dados_dashboard(x_empresa_id: int = Header(1)):
    return banco_dados.obter_dados_dashboard(x_empresa_id)

@app.post("/cadastrar-produto")
def cadastrar_produto(produto: ProdutoNovo, x_empresa_id: int = Header(1)):
    banco_dados.cadastrar_produto(
        x_empresa_id, produto.codigo_barras, produto.descricao, produto.categoria, 
        produto.subcategoria, produto.preco_custo, produto.preco_venda, 
        produto.quantidade, produto.codigo_proveedor
    )
    return {"mensaje": "Producto guardado con éxito"}

@app.get("/listar-produtos")
def listar_produtos(x_empresa_id: int = Header(1)):
    return banco_dados.listar_produtos(x_empresa_id)

@app.get("/buscar-produto/{codigo_barras}")
def buscar_produto(codigo_barras: str, x_empresa_id: int = Header(1)):
    produto = banco_dados.buscar_produto_por_codigo(x_empresa_id, codigo_barras)
    if produto: return {"descricao": produto["descricao"], "preco": produto["preco_venda"]}
    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.delete("/deletar-produto/{codigo_barras}")
def deletar_produto(codigo_barras: str, x_empresa_id: int = Header(1)):
    banco_dados.deletar_produto(x_empresa_id, codigo_barras)
    return {"mensaje": "Producto eliminado"}

@app.post("/emitir-nota")
def emitir_nota(dados: DadosNota, x_empresa_id: int = Header(1)):
    caixa_atual = banco_dados.status_caixa_atual(x_empresa_id)
    if not caixa_atual.get("aberto"):
        raise HTTPException(status_code=403, detail="Debe abrir la caja antes de registrar ventas.")

    config = banco_dados.obter_configuracao(x_empresa_id)
    ambiente = config.get("ambiente_sifen", "testes") if config else "testes"

    xml_bruto, cdc_real = construir_xml_sifen(dados)
    xml_final_assinado = assinar_documento(xml_bruto)
    
    link_qrcode = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_real}"
    link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
    
    banco_dados.salvar_nota(x_empresa_id, dados.ruc_emissor, dados.nome_cliente, dados.valor_total, cdc_real, dados.itens, link_pdf, link_qrcode, dados.metodo_pago)
    
    gerar_pdf_nota(dados, cdc_real)
    
    return {
        "mensaje": f"Factura generada ({ambiente.upper()})", "cdc": cdc_real,
        "link_qrcode": link_qrcode,
        "link_pdf": link_pdf
    }

@app.get("/baixar-pdf/{id_nota}")
def baixar_pdf(id_nota: str):
    caminho = f"notas_pdf/nota_{id_nota}.pdf"
    if os.path.exists(caminho): return FileResponse(caminho, media_type='application/pdf', filename=f"Factura_{id_nota}.pdf")
    raise HTTPException(status_code=404, detail="PDF no encontrado")

@app.get("/listar-notas")
def listar_notas(busca: Optional[str] = "", x_empresa_id: int = Header(1)):
    historico = banco_dados.listar_todas_notas(x_empresa_id, busca)
    return {"total": len(historico), "historico": historico}

@app.get("/cierre-caja")
def api_cierre_caja(x_empresa_id: int = Header(1)):
    return banco_dados.obter_fechamento_caixa(x_empresa_id)

@app.get("/painel")
def abrir_painel():
    return FileResponse("frontend.html")