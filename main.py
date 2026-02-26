from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil

from gerador_xml import construir_xml_sifen
from assinador_xml import assinar_documento
from gerador_pdf import gerar_pdf_nota
import banco_dados

app = FastAPI(title="Facturación y ERP SIFEN PY")

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

# NOVO: Modelo para a Categoria
class CategoriaNova(BaseModel):
    nome: str

# --- ROTAS DE CATEGORIAS (NOVO) ---
@app.post("/cadastrar-categoria")
def cadastrar_categoria(cat: CategoriaNova):
    sucesso = banco_dados.cadastrar_categoria(cat.nome.strip())
    if sucesso:
        return {"mensaje": "Categoría creada con éxito"}
    raise HTTPException(status_code=400, detail="Esta categoría ya existe")

@app.get("/listar-categorias")
def listar_categorias():
    return banco_dados.listar_categorias()

@app.delete("/deletar-categoria/{id_categoria}")
def deletar_categoria(id_categoria: int):
    banco_dados.deletar_categoria(id_categoria)
    return {"mensaje": "Categoría eliminada"}

# --- ROTAS DE CONFIGURAÇÃO DA EMPRESA ---
@app.get("/obter-configuracao")
def obter_configuracao():
    return banco_dados.obter_configuracao()

@app.post("/salvar-configuracao")
def salvar_configuracao(nome_empresa: str = Form(...), ruc: str = Form(...), endereco: str = Form(""), senha_certificado: str = Form("")):
    banco_dados.salvar_configuracao_texto(nome_empresa, ruc, endereco, senha_certificado)
    return {"mensaje": "Datos guardados"}

@app.post("/upload-certificado")
def upload_certificado(arquivo: UploadFile = File(...)):
    if not arquivo.filename.endswith(('.p12', '.pfx')): raise HTTPException(status_code=400, detail="Formato inválido.")
    caminho_destino = f"certificados/{arquivo.filename}"
    with open(caminho_destino, "wb") as buffer: shutil.copyfileobj(arquivo.file, buffer)
    banco_dados.salvar_caminho_certificado(caminho_destino)
    return {"mensaje": "Certificado digital subido"}


# --- ROTAS DE ESTOQUE E VENDAS ---
@app.post("/cadastrar-produto")
def cadastrar_produto(produto: ProdutoNovo):
    banco_dados.cadastrar_produto(
        produto.codigo_barras, produto.descricao, produto.categoria, 
        produto.subcategoria, produto.preco_custo, produto.preco_venda, produto.quantidade
    )
    return {"mensaje": "Producto guardado con éxito"}

@app.get("/listar-produtos")
def listar_produtos():
    return banco_dados.listar_produtos()

@app.get("/buscar-produto/{codigo_barras}")
def buscar_produto(codigo_barras: str):
    produto = banco_dados.buscar_produto_por_codigo(codigo_barras)
    if produto: return {"descricao": produto["descricao"], "preco": produto["preco_venda"]}
    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.delete("/deletar-produto/{codigo_barras}")
def deletar_produto(codigo_barras: str):
    banco_dados.deletar_produto(codigo_barras)
    return {"mensaje": "Producto eliminado"}

@app.post("/emitir-nota")
def emitir_nota(dados: DadosNota):
    xml_bruto, cdc_real = construir_xml_sifen(dados)
    xml_final_assinado = assinar_documento(xml_bruto)
    banco_dados.salvar_nota(dados.ruc_emissor, dados.nome_cliente, dados.valor_total, cdc_real, dados.itens)
    gerar_pdf_nota(dados, cdc_real)
    return {
        "mensaje": "Factura generada", "cdc": cdc_real,
        "link_qrcode": f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_real}",
        "link_pdf": f"/baixar-pdf/{cdc_real[:10]}"
    }

@app.get("/baixar-pdf/{id_nota}")
def baixar_pdf(id_nota: str):
    caminho = f"notas_pdf/nota_{id_nota}.pdf"
    if os.path.exists(caminho): return FileResponse(caminho, media_type='application/pdf', filename=f"Factura_{id_nota}.pdf")
    raise HTTPException(status_code=404, detail="PDF no encontrado")

@app.get("/listar-notas")
def listar_notas(busca: Optional[str] = ""):
    historico = banco_dados.listar_todas_notas(busca)
    return {"total": len(historico), "historico": historico}

@app.get("/painel")
def abrir_painel():
    return FileResponse("frontend.html")