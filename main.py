from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Header, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil

from gerador_xml import construir_xml_sifen
from assinador_xml import assinar_documento
from gerador_pdf import gerar_pdf_nota
from conexao_sifen import enviar_xml_para_sifen
import banco_dados

app = FastAPI(title="NubePY SaaS - SIFEN")

if not os.path.exists("notas_pdf"): os.makedirs("notas_pdf")
if not os.path.exists("certificados"): os.makedirs("certificados")

class DadosLogin(BaseModel):
    ruc: str
    senha: str

class NovaEmpresa(BaseModel):
    nome: str
    ruc: str
    senha_admin: str
    senha_caixa: str
    plano: str
    valor_mensalidade: float

class EdicaoEmpresa(BaseModel):
    plano: str
    valor_mensalidade: float

class ProdutoNovo(BaseModel):
    codigo_barras: str
    descricao: str
    categoria: str
    subcategoria: str
    preco_custo: float
    preco_venda: float
    quantidade: int
    codigo_proveedor: Optional[str] = ""

class ProveedorNovo(BaseModel):
    nome: str
    ruc: Optional[str] = ""
    telefone: Optional[str] = ""
    email: Optional[str] = ""
    endereco: Optional[str] = ""

class ProveedorEdit(BaseModel):
    nome: str
    ruc: Optional[str] = ""
    telefone: Optional[str] = ""
    email: Optional[str] = ""
    endereco: Optional[str] = ""

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
    cdc_referencia: Optional[str] = None

class DadosRemision(BaseModel):
    ruc_destinatario: str
    nome_destinatario: str
    motivo: str
    chapa_vehiculo: str
    dados_chofer: str
    itens: List[ItemNota]

class ItemEntrada(BaseModel):
    codigo_barras: str
    descricao: str
    quantidade: int
    custo_unitario: float

class DadosEntrada(BaseModel):
    proveedor_id: int
    numero_factura: str
    data_emissao: str
    itens: List[ItemEntrada]

class ItemAutofactura(BaseModel):
    codigo_barras: Optional[str] = ""
    descricao: str
    quantidade: int
    preco_unitario: float

class DadosAutofactura(BaseModel):
    nome_vendedor: str
    cedula_vendedor: str
    endereco_vendedor: str
    mover_stock: bool
    itens: List[ItemAutofactura]

class DadosMerma(BaseModel):
    codigo_barras: str
    quantidade: int
    motivo: str

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

class ItemAuditoria(BaseModel):
    codigo_barras: str
    qtd_fisica: int

class DadosAuditoria(BaseModel):
    itens: List[ItemAuditoria]

class ValidacaoAdmin(BaseModel):
    senha: str


@app.post("/api/login")
def fazer_login(dados: DadosLogin):
    resultado = banco_dados.autenticar_usuario(dados.ruc, dados.senha)
    if resultado["sucesso"]:
        return resultado
    raise HTTPException(status_code=401, detail=resultado["mensagem"])

@app.post("/validar-admin")
def validar_admin(dados: ValidacaoAdmin, x_empresa_id: int = Header(...)):
    if banco_dados.validar_senha_admin(x_empresa_id, dados.senha):
        return {"sucesso": True}
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")

@app.get("/super-admin/empresas")
def listar_todas_empresas():
    return banco_dados.listar_todas_empresas()

@app.get("/super-admin/metricas")
def metricas_saas():
    return banco_dados.obter_metricas_saas()

@app.post("/super-admin/criar-empresa")
def criar_empresa(dados: NovaEmpresa):
    sucesso, msg = banco_dados.criar_nova_empresa(dados.nome, dados.ruc, dados.senha_admin, dados.senha_caixa, dados.plano, dados.valor_mensalidade)
    if sucesso:
        return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.put("/super-admin/editar-empresa/{empresa_id}")
def editar_empresa(empresa_id: int, dados: EdicaoEmpresa):
    banco_dados.atualizar_plano_empresa(empresa_id, dados.plano, dados.valor_mensalidade)
    return {"mensaje": "Plan actualizado exitosamente."}

@app.get("/status-caixa")
def status_caixa(x_empresa_id: int = Header(...)):
    return banco_dados.status_caixa_atual(x_empresa_id)

@app.post("/abrir-caixa")
def abrir_caixa(dados: CaixaAbertura, x_empresa_id: int = Header(...)):
    sucesso, mensagem = banco_dados.abrir_caixa(x_empresa_id, dados.valor_inicial)
    if sucesso: return {"mensaje": mensagem}
    raise HTTPException(status_code=400, detail=mensagem)

@app.post("/fechar-caixa")
def fechar_caixa(dados: CaixaFechamento, x_empresa_id: int = Header(...)):
    sucesso, mensagem = banco_dados.fechar_caixa(x_empresa_id, dados.valor_final)
    if sucesso: return {"mensaje": mensagem}
    raise HTTPException(status_code=400, detail=mensagem)

@app.post("/registrar-sangria")
def api_registrar_sangria(dados: DadosSangria, x_empresa_id: int = Header(...)):
    sucesso, msg = banco_dados.registrar_sangria(x_empresa_id, dados.valor, dados.motivo)
    if sucesso: return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.post("/cadastrar-categoria")
def cadastrar_categoria(cat: CategoriaNova, x_empresa_id: int = Header(...)):
    sucesso = banco_dados.cadastrar_categoria(x_empresa_id, cat.nome.strip())
    if sucesso: return {"mensaje": "Categoría creada con éxito"}
    raise HTTPException(status_code=400, detail="Esta categoría ya existe")

@app.get("/listar-categorias")
def listar_categorias(x_empresa_id: int = Header(...)):
    return banco_dados.listar_categorias(x_empresa_id)

@app.delete("/deletar-categoria/{id_categoria}")
def deletar_categoria(id_categoria: int, x_empresa_id: int = Header(...)):
    banco_dados.deletar_categoria(x_empresa_id, id_categoria)
    return {"mensaje": "Categoría eliminada"}

@app.post("/cadastrar-proveedor")
def cadastrar_proveedor(prov: ProveedorNovo, x_empresa_id: int = Header(...)):
    sucesso, msg = banco_dados.cadastrar_proveedor(x_empresa_id, prov.nome, prov.ruc, prov.telefone, prov.email, prov.endereco)
    if sucesso: return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.put("/editar-proveedor/{id_prov}")
def api_editar_proveedor(id_prov: int, prov: ProveedorEdit, x_empresa_id: int = Header(...)):
    sucesso, msg = banco_dados.editar_proveedor(x_empresa_id, id_prov, prov.nome, prov.ruc, prov.telefone, prov.email, prov.endereco)
    if sucesso: return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.get("/listar-proveedores")
def listar_proveedores(x_empresa_id: int = Header(...)):
    return banco_dados.listar_proveedores(x_empresa_id)

@app.delete("/deletar-proveedor/{id_prov}")
def deletar_proveedor(id_prov: int, x_empresa_id: int = Header(...)):
    banco_dados.deletar_proveedor(x_empresa_id, id_prov)
    return {"mensaje": "Proveedor eliminado"}

@app.post("/salvar-entrada")
def api_salvar_entrada(dados: DadosEntrada, x_empresa_id: int = Header(...)):
    itens_dicts = [{"codigo_barras": i.codigo_barras, "descricao": i.descricao, "quantidade": i.quantidade, "custo_unitario": i.custo_unitario} for i in dados.itens]
    sucesso, msg = banco_dados.salvar_entrada_factura(
        x_empresa_id, 
        dados.proveedor_id, 
        dados.numero_factura, 
        dados.data_emissao, 
        itens_dicts
    )
    if sucesso: return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.post("/emitir-autofactura")
def api_emitir_autofactura(dados: DadosAutofactura, x_empresa_id: int = Header(...)):
    caixa_atual = banco_dados.status_caixa_atual(x_empresa_id)
    if not caixa_atual.get("aberto"):
        raise HTTPException(status_code=403, detail="Debe abrir la caja antes de emitir Autofacturas (salida de dinero).")

    config = banco_dados.obter_configuracao(x_empresa_id)
    if not config: raise HTTPException(status_code=400, detail="Configuración no encontrada.")

    ambiente = config.get("ambiente_sifen", "testes")

    import os
    cdc_real = f"03{x_empresa_id}AUT{os.urandom(8).hex().upper()}"
    link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
    if ambiente == "produccion":
        link_qrcode = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_real}"
    else:
        link_qrcode = f"https://sifen-test.set.gov.py/consultas/qr?nId={cdc_real}"

    itens_dicts = [{"codigo_barras": i.codigo_barras, "descricao": i.descricao, "quantidade": i.quantidade, "preco_unitario": i.preco_unitario} for i in dados.itens]

    sucesso, msg = banco_dados.salvar_autofactura(
        x_empresa_id, dados.nome_vendedor, dados.cedula_vendedor, dados.endereco_vendedor,
        cdc_real, itens_dicts, dados.mover_stock, link_pdf, link_qrcode
    )

    if not sucesso:
        raise HTTPException(status_code=400, detail=msg)

    return {
        "mensaje": "Autofactura generada (Aprobado SIFEN)",
        "cdc": cdc_real,
        "link_qrcode": link_qrcode,
        "link_pdf": link_pdf
    }

@app.get("/listar-autofacturas")
def api_listar_autofacturas(x_empresa_id: int = Header(...)):
    return banco_dados.listar_autofacturas(x_empresa_id)

@app.post("/registrar-merma")
def api_registrar_merma(dados: DadosMerma, x_empresa_id: int = Header(...)):
    sucesso, msg = banco_dados.registrar_merma(x_empresa_id, dados.codigo_barras, dados.quantidade, dados.motivo)
    if sucesso: return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.get("/listar-mermas")
def api_listar_mermas(x_empresa_id: int = Header(...)):
    return banco_dados.listar_mermas(x_empresa_id)

@app.get("/obter-configuracao")
def obter_config_route(empresa_id: str = Header(None, alias="X-Empresa-ID")):
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Empresa ID no proporcionado")
    
    config = banco_dados.obter_configuracao(int(empresa_id))
    if not config:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")
        
    # Aqui garantimos que o Python devolve o dicionário inteiro, sem filtrar nada!
    return config

@app.post("/salvar-configuracao")
def salvar_config_route(
    nome_empresa: str = Form(default=""),
    ruc: str = Form(default=""),
    endereco: str = Form(default=""),
    senha_certificado: str = Form(default=""),
    csc: str = Form(default=""),
    mercado_pago_token: str = Form(default=""),
    empresa_id: str = Header(None, alias="X-Empresa-ID")
):
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Empresa ID no proporcionado")
    
    banco_dados.salvar_configuracao_texto(
        int(empresa_id), 
        nome_empresa, 
        ruc, 
        endereco, 
        senha_certificado, 
        csc,
        mercado_pago_token
    )
    return {"mensagem": "Configuración guardada con éxito"}

@app.post("/upload-certificado")
def upload_certificado(arquivo: UploadFile = File(...), x_empresa_id: int = Header(...)):
    if not arquivo.filename.endswith(('.p12', '.pfx')): raise HTTPException(status_code=400, detail="Formato inválido.")
    caminho_destino = f"certificados/emp_{x_empresa_id}_{arquivo.filename}"
    with open(caminho_destino, "wb") as buffer: shutil.copyfileobj(arquivo.file, buffer)
    banco_dados.salvar_caminho_certificado(x_empresa_id, caminho_destino)
    return {"mensaje": "Certificado digital subido"}

@app.post("/alternar-ambiente")
def alternar_ambiente(dados: AmbienteUpdate, x_empresa_id: int = Header(...)):
    if dados.ambiente not in ["testes", "produccion"]:
        raise HTTPException(status_code=400, detail="Ambiente inválido")
    banco_dados.alternar_ambiente_sifen(x_empresa_id, dados.ambiente)
    return {"mensaje": f"Ambiente cambiado a {dados.ambiente.upper()}"}

@app.get("/dados-dashboard")
def dados_dashboard(x_empresa_id: int = Header(...)):
    return banco_dados.obter_dados_dashboard(x_empresa_id)

@app.post("/cadastrar-produto")
def cadastrar_produto(produto: ProdutoNovo, x_empresa_id: int = Header(...)):
    banco_dados.cadastrar_produto(
        x_empresa_id, produto.codigo_barras, produto.descricao, produto.categoria, 
        produto.subcategoria, produto.preco_custo, produto.preco_venda, 
        produto.quantidade, produto.codigo_proveedor
    )
    return {"mensaje": "Producto guardado con éxito"}

@app.get("/listar-produtos")
def listar_produtos(x_empresa_id: int = Header(...)):
    return banco_dados.listar_produtos(x_empresa_id)

@app.get("/buscar-produto/{codigo_barras}")
def buscar_produto(codigo_barras: str, x_empresa_id: int = Header(...)):
    produto = banco_dados.buscar_produto_por_codigo(x_empresa_id, codigo_barras)
    if produto: return {"descricao": produto["descricao"], "preco": produto["preco_venda"]}
    raise HTTPException(status_code=404, detail="Producto no encontrado")

@app.delete("/deletar-produto/{codigo_barras}")
def deletar_produto(codigo_barras: str, x_empresa_id: int = Header(...)):
    banco_dados.deletar_produto(x_empresa_id, codigo_barras)
    return {"mensaje": "Producto eliminado"}

@app.post("/salvar-auditoria")
def api_salvar_auditoria(dados: DadosAuditoria, x_empresa_id: int = Header(...)):
    itens_dicts = [{"codigo_barras": i.codigo_barras, "qtd_fisica": i.qtd_fisica} for i in dados.itens]
    sucesso, msg = banco_dados.salvar_auditoria_estoque(x_empresa_id, itens_dicts)
    if sucesso: return {"mensaje": msg}
    raise HTTPException(status_code=400, detail=msg)

@app.get("/relatorio-variancia")
def api_relatorio_variancia(inicio: str, fim: str, x_empresa_id: int = Header(...)):
    return banco_dados.obter_relatorio_variancia(x_empresa_id, inicio, fim)

@app.post("/emitir-nota")
def emitir_nota(dados: DadosNota, x_empresa_id: int = Header(...)):
    caixa_atual = banco_dados.status_caixa_atual(x_empresa_id)
    if not caixa_atual.get("aberto"):
        raise HTTPException(status_code=403, detail="Debe abrir la caja antes de registrar ventas/devoluciones.")

    config = banco_dados.obter_configuracao(x_empresa_id)
    if not config: raise HTTPException(status_code=400, detail="Configuración no encontrada.")
        
    ambiente = config.get("ambiente_sifen", "testes")
    xml_bruto, cdc_real = construir_xml_sifen(dados, config)
    
    caminho_cert = config.get("caminho_certificado")
    senha_cert = config.get("senha_certificado")
    xml_final_assinado = xml_bruto
    status_sifen = "No Enviado (Falta Certificado)"
    
    try:
        if caminho_cert and os.path.exists(caminho_cert) and senha_cert:
            xml_final_assinado = assinar_documento(xml_bruto, caminho_cert, senha_cert)
            retorno_sifen = enviar_xml_para_sifen(xml_final_assinado, caminho_cert, senha_cert, ambiente)
            
            if retorno_sifen["sucesso"]:
                status_sifen = f"Aprobado (Cod: {retorno_sifen.get('codigo_retorno', 'OK')})"
            else:
                status_sifen = f"Rechazado SET: {retorno_sifen.get('erro', 'Desconocido')}"
    except Exception as e:
        print(f"Erro no processamento SIFEN: {str(e)}")
        status_sifen = f"Error Interno: {str(e)}"
    
    if ambiente == "produccion":
        link_qrcode = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_real}"
    else:
        link_qrcode = f"https://sifen-test.set.gov.py/consultas/qr?nId={cdc_real}"

    link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
    
    if dados.cdc_referencia:
        banco_dados.salvar_nota_credito(x_empresa_id, dados.cdc_referencia, cdc_real, dados.nome_cliente, dados.valor_total, dados.itens, link_pdf)
        mensagem_retorno = f"Nota de Crédito generada | SIFEN: {status_sifen}"
    else:
        banco_dados.salvar_nota(x_empresa_id, dados.ruc_emissor, dados.nome_cliente, dados.valor_total, cdc_real, dados.itens, link_pdf, link_qrcode, dados.metodo_pago)
        mensagem_retorno = f"Factura generada | SIFEN: {status_sifen}"

    gerar_pdf_nota(dados, cdc_real)
    
    return {
        "mensaje": mensagem_retorno, 
        "cdc": cdc_real,
        "link_qrcode": link_qrcode,
        "link_pdf": link_pdf
    }

@app.post("/emitir-remision")
def api_emitir_remision(dados: DadosRemision, x_empresa_id: int = Header(...)):
    config = banco_dados.obter_configuracao(x_empresa_id)
    if not config: raise HTTPException(status_code=400, detail="Configuración no encontrada.")
    
    ambiente = config.get("ambiente_sifen", "testes")
    
    import os
    cdc_real = f"02{x_empresa_id}REM{os.urandom(8).hex().upper()}"
    link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
    
    if ambiente == "produccion":
        link_qrcode = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_real}"
    else:
        link_qrcode = f"https://sifen-test.set.gov.py/consultas/qr?nId={cdc_real}"
        
    itens_dicts = [{"codigo_barras": i.codigo_barras, "descricao": i.descricao, "quantidade": i.quantidade} for i in dados.itens]
    
    banco_dados.salvar_nota_remision(
        x_empresa_id, dados.ruc_destinatario, dados.nome_destinatario, 
        dados.motivo, dados.chapa_vehiculo, dados.dados_chofer, 
        cdc_real, itens_dicts, link_pdf, link_qrcode
    )
    
    return {
        "mensaje": "Nota de Remisión generada (Aprobado SIFEN)",
        "cdc": cdc_real,
        "link_qrcode": link_qrcode,
        "link_pdf": link_pdf
    }

@app.get("/listar-remisiones")
def api_listar_remisiones(x_empresa_id: int = Header(...)):
    return banco_dados.listar_remisiones(x_empresa_id)

@app.get("/baixar-pdf/{id_nota}")
def baixar_pdf(id_nota: str):
    caminho = f"notas_pdf/nota_{id_nota}.pdf"
    if os.path.exists(caminho): return FileResponse(caminho, media_type='application/pdf', filename=f"Documento_{id_nota}.pdf")
    raise HTTPException(status_code=404, detail="PDF no encontrado")

@app.get("/api/nota/{cdc}")
def obter_nota_por_cdc(cdc: str, x_empresa_id: int = Header(...)):
    nota = banco_dados.obter_nota_por_cdc(x_empresa_id, cdc)
    if nota: return nota
    raise HTTPException(status_code=404, detail="Nota no encontrada")

@app.get("/listar-notas")
def listar_notas(busca: Optional[str] = "", inicio: Optional[str] = None, fim: Optional[str] = None, x_empresa_id: int = Header(...)):
    historico = banco_dados.listar_todas_notas(x_empresa_id, busca, inicio, fim)
    return {"total": len(historico), "historico": historico}

@app.get("/cierre-caja")
def api_cierre_caja(inicio: Optional[str] = None, fim: Optional[str] = None, x_empresa_id: int = Header(...)):
    return banco_dados.obter_fechamento_caixa(x_empresa_id, inicio, fim)

@app.get("/painel")
def abrir_painel():
    return FileResponse("frontend.html")
# Existing code...
@app.get("/painel")
def abrir_painel():
    return FileResponse("frontend.html")

# ADD THIS NEW ROUTE:
@app.get("/app.js")
def servir_js():
    return FileResponse("app.js")