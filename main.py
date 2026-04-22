from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Header, Query#
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import mercadopago
import urllib.request
import json

from gerador_xml import construir_xml_sifen
from assinador_xml import assinar_documento
from gerador_pdf import gerar_pdf_nota
from conexao_sifen import enviar_xml_para_sifen
import banco_dados

app = FastAPI(title="NubePY SaaS - SIFEN")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # O asterisco permite que o seu novo domínio se conecte
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("notas_pdf"): os.makedirs("notas_pdf")
if not os.path.exists("certificados"): os.makedirs("certificados")

@app.on_event("startup")
def startup_event():
    """Injeta dados de demo no banco ao iniciar o servidor"""
    banco_dados.injetar_dados_demo()
    print("[STARTUP] Dados de demo verificados/injetados.")

class DadosLogin(BaseModel):
    ruc: str
    senha: str

class NovaEmpresa(BaseModel):
    nome: str
    ruc: str
    senha_admin: str
    senha_caixa: str = ""
    plano: str
    valor_mensalidade: float

class EdicaoEmpresa(BaseModel):
    plano: str
    valor_mensalidade: float

class AlterarCredenciaisAdmin(BaseModel):
    senha_atual: str
    novo_login: str
    nova_senha: str

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
class PedidoPix(BaseModel):
    valor_guaranis: float

def obter_taxa_cambio():
    try:
        req = urllib.request.Request("https://economia.awesomeapi.com.br/last/BRL-PYG", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as response:
            dados = json.loads(response.read().decode())
            return float(dados["BRLPYG"]["ask"])
    except Exception:
        return 1450.0
    

 
@app.post("/gerar-pix")


def gerar_pix_dinamico(
    pedido: PedidoPix, 
    empresa_id: str = Header(None, alias="X-Empresa-ID")
):
    if not empresa_id:
        raise HTTPException(status_code=400, detail="Empresa ID no proporcionado")
        
    # 1. Buscar o Token do lojista no nosso cofre
    config = banco_dados.obter_configuracao(int(empresa_id))
    token_mp = config.get("mercado_pago_token", "")
    
    if not token_mp or token_mp.strip() == "":
        raise HTTPException(status_code=400, detail="El comercio no ha configurado su Token de Mercado Pago.")

    # 2. Conversão de Moeda (MVP: Taxa fixa de 1 BRL = 1450 PYG)
    # No futuro, moveremos esta taxa para a tela de Ajustes.
    taxa_cambio = obter_taxa_cambio()
    valor_reais = round(pedido.valor_guaranis / taxa_cambio, 2)
    
    if valor_reais < 0.10:
        raise HTTPException(status_code=400, detail="El valor mínimo para PIX es R$ 0,10")

    # 3. Comunicação com o Mercado Pago
   # 3. Comunicação com o Mercado Pago
    try:
        sdk = mercadopago.SDK(token_mp)
        
        dados_pagamento = {
            "transaction_amount": valor_reais,
            "description": f"Venta NubePY - Emp {empresa_id}",
            "payment_method_id": "pix",
            "payer": {
                "email": "comprador@nubepy.com",
                "first_name": "Cliente",
                "last_name": "Mostrador"
            }
        }
        
        resposta = sdk.payment().create(dados_pagamento)
        pagamento = resposta["response"]
        
        # O NOSSO NOVO ESCUDO DEFENSIVO:
        # Verifica se o Mercado Pago enviou um erro em vez do PIX
        if "point_of_interaction" not in pagamento:
            erro_mp = pagamento.get("message", "Error de validación")
            raise HTTPException(status_code=400, detail=f"MP Info: {erro_mp}")
            
        # O MP devolve a linha "Copia e Cola" e a imagem do QR Code em Base64
        codigo_copia_cola = pagamento["point_of_interaction"]["transaction_data"]["qr_code"]
        qr_code_img = pagamento["point_of_interaction"]["transaction_data"]["qr_code_base64"]
        
        return {
            "sucesso": True,
            "valor_reais": valor_reais,
            "qr_code_base64": qr_code_img,
            "copia_cola": codigo_copia_cola,
            "id_pagamento_mp": pagamento["id"]
        }
        
    except HTTPException:
        raise # Deixa passar os nossos próprios erros (como o escudo acima)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo del servidor: {str(e)}")


class FuncionarioNovo(BaseModel):
    nome: str
    email: str
    senha: str
    rol: str

class FuncionarioEditar(BaseModel):
    nome: Optional[str] = None
    email: Optional[str] = None
    senha: Optional[str] = None
    rol: Optional[str] = None
    ativo: Optional[bool] = None

@app.post("/api/login")
def fazer_login(dados: DadosLogin):
    resultado = banco_dados.autenticar_usuario(dados.ruc, dados.senha)
    if resultado["sucesso"]:
        # Se for a conta demo (RUC 9999999-9), garantir que os dados demo existam
        if dados.ruc == "9999999-9":
            # Executar a geração de dados demo em background (sem bloquear a resposta)
            import threading
            def gerar_dados_demo():
                banco_dados.injetar_dados_demo()
            threading.Thread(target=gerar_dados_demo).start()
        return resultado
    raise HTTPException(status_code=401, detail=resultado["mensagem"])

@app.post("/validar-admin")
def validar_admin(dados: ValidacaoAdmin, x_empresa_id: int = Header(...)):
    if banco_dados.validar_senha_admin(x_empresa_id, dados.senha):
        return {"sucesso": True}
    raise HTTPException(status_code=401, detail="Contraseña incorrecta")


@app.get("/")
async def root():
    """Rota raiz - serve o sistema principal"""
    return FileResponse("frontend.html", media_type="text/html")

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

# ============================================================================
# Endpoints para Gestão de Equipe (Funcionários)
# ============================================================================

@app.post("/equipo/adicionar")
def adicionar_funcionario(dados_func: FuncionarioNovo, x_empresa_id: int = Header(...)):
    resultado = banco_dados.adicionar_funcionario(
        empresa_id=x_empresa_id,
        nome=dados_func.nome,
        email=dados_func.email,
        senha=dados_func.senha,
        rol=dados_func.rol
    )
    
    if resultado["sucesso"]:
        return {"mensagem": "Usuário adicionado com sucesso", "id": resultado.get("id")}
    else:
        raise HTTPException(status_code=400, detail=resultado["mensagem"])

@app.get("/equipo/listar")
def listar_funcionarios(x_empresa_id: int = Header(...)):
    """Lista todos os funcionários da empresa"""
    return banco_dados.listar_funcionarios(x_empresa_id)

@app.put("/equipo/editar/{funcionario_id}")
def editar_funcionario(funcionario_id: int, func: FuncionarioEditar, x_empresa_id: int = Header(...)):
    """Edita os dados de um funcionário"""
    resultado = banco_dados.atualizar_funcionario(
        empresa_id=x_empresa_id,
        funcionario_id=funcionario_id,
        nome=func.nome,
        email=func.email,
        senha=func.senha,
        rol=func.rol,
        ativo=func.ativo
    )
    if resultado["sucesso"]:
        return {"mensaje": "Funcionário atualizado com sucesso"}
    raise HTTPException(status_code=400, detail=resultado["mensagem"])

@app.delete("/equipo/remover/{funcionario_id}")
def remover_funcionario(funcionario_id: int, x_empresa_id: int = Header(...)):
    """Remove/desativa um funcionário"""
    resultado = banco_dados.remover_funcionario(x_empresa_id, funcionario_id)
    if resultado["sucesso"]:
        return {"mensaje": "Funcionário removido com sucesso"}
    raise HTTPException(status_code=400, detail=resultado["mensagem"])

@app.post("/api/admin/credenciais")
def alterar_credenciais_admin(dados: AlterarCredenciaisAdmin, x_empresa_id: int = Header(...)):
    """
    Altera o login (RUC) e senha do administrador da empresa.
    Requer senha atual para confirmação.
    """
    resultado = banco_dados.alterar_credenciais_admin(
        empresa_id=x_empresa_id,
        senha_atual=dados.senha_atual,
        novo_ruc=dados.novo_login,
        nova_senha=dados.nova_senha
    )
    
    if resultado["sucesso"]:
        return {"mensagem": resultado["mensagem"]}
    else:
        raise HTTPException(status_code=400, detail=resultado["mensagem"])

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

    # Verificar se o plano permite emissão SIFEN
    plano = banco_dados.obter_plano_empresa(x_empresa_id)
    permite_sifen = banco_dados.plano_permite_sifen(plano)

    ambiente = config.get("ambiente_sifen", "testes")

    import os
    if not permite_sifen:
        # Modo interno para planos Lite/Lite Premium
        cdc_real = f"INT-AUT-{os.urandom(6).hex().upper()}"
        link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
        link_qrcode = ""
        mensaje = "Autofactura generada (Uso Interno)"
    else:
        cdc_real = f"03{x_empresa_id}AUT{os.urandom(8).hex().upper()}"
        link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
        if ambiente == "produccion":
            link_qrcode = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_real}"
        else:
            link_qrcode = f"https://sifen-test.set.gov.py/consultas/qr?nId={cdc_real}"
        mensaje = "Autofactura generada (Aprobado SIFEN)"

    itens_dicts = [{"codigo_barras": i.codigo_barras, "descricao": i.descricao, "quantidade": i.quantidade, "preco_unitario": i.preco_unitario} for i in dados.itens]

    sucesso, msg = banco_dados.salvar_autofactura(
        x_empresa_id, dados.nome_vendedor, dados.cedula_vendedor, dados.endereco_vendedor,
        cdc_real, itens_dicts, dados.mover_stock, link_pdf, link_qrcode
    )

    if not sucesso:
        raise HTTPException(status_code=400, detail=msg)

    return {
        "mensaje": mensaje,
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

@app.get("/listar-auditorias")
def api_listar_auditorias(inicio: str = Query(None), fim: str = Query(None), x_empresa_id: int = Header(...)):
    # Se não fornecer datas, usa intervalo padrão dos últimos 30 dias
    import datetime
    hoje = datetime.date.today()
    if fim is None:
        fim = hoje.strftime('%Y-%m-%d')
    if inicio is None:
        inicio = (hoje - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    return banco_dados.listar_auditorias(x_empresa_id, inicio, fim)

@app.get("/detalhes-auditoria/{auditoria_id}")
def api_detalhes_auditoria(auditoria_id: int, x_empresa_id: int = Header(...)):
    return banco_dados.obter_detalhes_auditoria(x_empresa_id, auditoria_id)

@app.post("/emitir-nota")
def emitir_nota(dados: DadosNota, x_empresa_id: int = Header(...)):
    caixa_atual = banco_dados.status_caixa_atual(x_empresa_id)
    if not caixa_atual.get("aberto"):
        raise HTTPException(status_code=403, detail="Debe abrir la caja antes de registrar ventas/devoluciones.")

    config = banco_dados.obter_configuracao(x_empresa_id)
    if not config: raise HTTPException(status_code=400, detail="Configuración no encontrada.")
    
    # Verificar se o plano permite emissão SIFEN
    plano = banco_dados.obter_plano_empresa(x_empresa_id)
    permite_sifen = banco_dados.plano_permite_sifen(plano)

    # Modo demo para RUC 9999999-9
    if dados.ruc_emissor == '9999999-9':
        # Gerar CDC fake para registro local
        import random
        cdc_real = f"DEMO-{random.randint(100000, 999999)}"
        link_pdf = ""
        link_qrcode = ""
        if dados.cdc_referencia:
            banco_dados.salvar_nota_credito(x_empresa_id, dados.cdc_referencia, cdc_real, dados.nome_cliente, dados.valor_total, dados.itens, link_pdf)
            mensagem_retorno = "Nota de Crédito generada (Demo)"
        else:
            banco_dados.salvar_nota(x_empresa_id, dados.ruc_emissor, dados.nome_cliente, dados.valor_total, cdc_real, dados.itens, link_pdf, link_qrcode, dados.metodo_pago)
            mensagem_retorno = "Factura generada (Demo)"
        return {
            "demo_mode": True,
            "mensaje": "Venta procesada con éxito (Modo Demo). No enviada a la SET.",
            "cdc": cdc_real,
            "link_qrcode": link_qrcode,
            "link_pdf": link_pdf
        }
        
    if not permite_sifen:
        # Modo interno para planos Lite/Lite Premium
        import random
        cdc_real = f"INT-{random.randint(100000, 999999)}"
        link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
        link_qrcode = ""
        if dados.cdc_referencia:
            banco_dados.salvar_nota_credito(x_empresa_id, dados.cdc_referencia, cdc_real, dados.nome_cliente, dados.valor_total, dados.itens, link_pdf)
            mensagem_retorno = "Nota de Crédito generada (Uso Interno)"
        else:
            banco_dados.salvar_nota(x_empresa_id, dados.ruc_emissor, dados.nome_cliente, dados.valor_total, cdc_real, dados.itens, link_pdf, link_qrcode, dados.metodo_pago)
            mensagem_retorno = "Comprobante de Venta Interno generado"
        gerar_pdf_nota(dados, cdc_real, interno=True)
        return {
            "interno": True,
            "mensaje": mensagem_retorno,
            "cdc": cdc_real,
            "link_qrcode": link_qrcode,
            "link_pdf": link_pdf
        }
    
    # Fluxo normal SIFEN
    ambiente = config.get("ambiente_sifen", "testes")
    xml_bruto, cdc_real = construir_xml_sifen(dados, config)
    
    caminho_cert = config.get("caminho_certificado")
    senha_cert = config.get("senha_certificado")
    xml_final_assinado = xml_bruto
    status_sifen = "No Enviado (Falta Certificado)"
    
    try:
        if caminho_cert and os.path.exists(caminho_cert) and senha_cert:
            xml_final_assinado = assinar_documento(xml_bruto, caminho_cert, senha_cert)
            retorno_sifen = enviar_xml_para_sifen(xml_final_assinado, caminho_cert, senha_cert, ambiente, ruc_emissor=config['ruc'])
            
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

    gerar_pdf_nota(dados, cdc_real, interno=False)
    
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
    
    # Verificar se o plano permite emissão SIFEN
    plano = banco_dados.obter_plano_empresa(x_empresa_id)
    permite_sifen = banco_dados.plano_permite_sifen(plano)
    
    ambiente = config.get("ambiente_sifen", "testes")
    
    import os
    if not permite_sifen:
        # Modo interno para planos Lite/Lite Premium
        cdc_real = f"INT-REM-{os.urandom(6).hex().upper()}"
        link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
        link_qrcode = ""
        mensaje = "Nota de Remisión generada (Uso Interno)"
    else:
        cdc_real = f"02{x_empresa_id}REM{os.urandom(8).hex().upper()}"
        link_pdf = f"/baixar-pdf/{cdc_real[:10]}"
        if ambiente == "produccion":
            link_qrcode = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_real}"
        else:
            link_qrcode = f"https://sifen-test.set.gov.py/consultas/qr?nId={cdc_real}"
        mensaje = "Nota de Remisión generada (Aprobado SIFEN)"
        
    itens_dicts = [{"codigo_barras": i.codigo_barras, "descricao": i.descricao, "quantidade": i.quantidade} for i in dados.itens]
    
    banco_dados.salvar_nota_remision(
        x_empresa_id, dados.ruc_destinatario, dados.nome_destinatario, 
        dados.motivo, dados.chapa_vehiculo, dados.dados_chofer, 
        cdc_real, itens_dicts, link_pdf, link_qrcode
    )
    
    return {
        "mensaje": mensaje,
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
@app.get("/status-pix/{pagamento_id}")
def verificar_status_pix(pagamento_id: str, empresa_id: str = Header(None, alias="X-Empresa-ID")):
    try:
        config = banco_dados.obter_configuracao(int(empresa_id))
        token_mp = config.get("mercado_pago_token", "")
        
        if not token_mp:
            raise HTTPException(status_code=400, detail="Token MP não configurado")
            
        sdk = mercadopago.SDK(token_mp)
        resposta = sdk.payment().get(pagamento_id)
        pagamento = resposta["response"]
        
        # Retorna o status oficial (ex: "pending", "approved", "rejected")
        return {"sucesso": True, "status": pagamento.get("status", "pending")}
        
    except Exception as e:
        return {"sucesso": False, "erro": str(e)}
    
  # ==========================================
# ROTAS DO SUPER ADMIN (COBRANÇA SIPAP)
# ==========================================

@app.post("/super-admin/gerar-fatura/{empresa_id}")
def gerar_fatura_manual(empresa_id: int):
    try:
        from datetime import datetime, timedelta
        conn = banco_dados.get_conexao()
        cursor = conn.cursor()
        
        # Busca o valor que o cliente tem de pagar
        cursor.execute("SELECT valor_mensalidade FROM empresas WHERE id = %s", (empresa_id,))
        cliente = cursor.fetchone()
        
        if not cliente:
            return {"sucesso": False, "detail": "Empresa não encontrada."}
            
        # CORREÇÃO: Lê o valor direto da primeira posição da tupla
        valor = float(cliente[0]) if cliente[0] else 0.0
        
        if valor <= 0:
            return {"sucesso": False, "detail": "Este plano é gratuito."}
            
        # Dá 5 dias de prazo para o cliente pagar
        vencimento = datetime.now() + timedelta(days=5) 
        
        # Salva a conta como Pendente
        cursor.execute('''
            INSERT INTO faturas_saas (empresa_id, valor, data_vencimento, status, id_pagamento_mp)
            VALUES (%s, %s, %s, 'Pendente', 'SIPAP')
        ''', (empresa_id, valor, vencimento))
        
        conn.commit()
        return {"sucesso": True, "detail": "Factura generada con éxito!"}
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return {"sucesso": False, "detail": str(e)}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.get("/super-admin/faturas")
def listar_faturas():
    try:
        conn = banco_dados.get_conexao()
        cursor = conn.cursor()
        # Puxa o nome da empresa e os dados da fatura
        cursor.execute('''
            SELECT f.id, e.nome_empresa, f.valor, f.data_vencimento, f.status 
            FROM faturas_saas f
            JOIN empresas e ON f.empresa_id = e.id
            ORDER BY f.id DESC
        ''')
        faturas = cursor.fetchall()
        return faturas
    except Exception as e:
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.put("/super-admin/faturas/{fatura_id}/pagar")
def aprovar_pagamento(fatura_id: int):
    try:
        conn = banco_dados.get_conexao()
        cursor = conn.cursor()
        # Muda o status para Pago
        cursor.execute("UPDATE faturas_saas SET status = 'Pago' WHERE id = %s", (fatura_id,))
        conn.commit()
        return {"sucesso": True}
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return {"sucesso": False}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
@app.get("/super-admin/faturas")
def listar_faturas():
    try:
        conn = banco_dados.conectar()
        cursor = conn.cursor()
        # Puxa o nome da empresa e os dados da fatura
        cursor.execute('''
            SELECT f.id, e.nome_empresa, f.valor, f.data_vencimento, f.status 
            FROM faturas_saas f
            JOIN empresas e ON f.empresa_id = e.id
            ORDER BY f.id DESC
        ''')
        faturas = cursor.fetchall()
        return faturas
    except Exception as e:
        return []
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.put("/super-admin/faturas/{fatura_id}/pagar")
def aprovar_pagamento(fatura_id: int):
    try:
        conn = banco_dados.conectar()
        cursor = conn.cursor()
        # Muda o status para Pago
        cursor.execute("UPDATE faturas_saas SET status = 'Pago' WHERE id = %s", (fatura_id,))
        conn.commit()
        return {"sucesso": True}
    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        return {"sucesso": False}
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.get("/logo_main.svg")
def get_logo_main():
    return FileResponse("logo_main.svg")

@app.get("/logo_icon.svg")
def get_logo_icon():
    return FileResponse("logo_icon.svg")

@app.get("/demo")
async def pagina_demo():
    """Login automático para demo e entrega do sistema completo"""
    try:
        print(f"[DEMO] Iniciando login automático para RUC 9999999-9...")
        
        # 1. Tentar autenticar usuário demo
        resultado = banco_dados.autenticar_usuario('9999999-9', 'demo123')
        print(f"[DEMO] Resultado da autenticação: {resultado}")
        
        # 2. Se falhar, tentar criar dados demo
        if not resultado.get("sucesso"):
            print("[DEMO] Autenticação falhou, injetando dados demo...")
            empresa_id_criada = banco_dados.injetar_dados_demo()
            print(f"[DEMO] Retorno de injetar_dados_demo: {empresa_id_criada}")
            
            # Tentar autenticar novamente após criação
            resultado = banco_dados.autenticar_usuario('9999999-9', 'demo123')
            print(f"[DEMO] Resultado da autenticação após injeção: {resultado}")
        
        # 3. Se ainda falhar, tentar criar usuário diretamente como último recurso
        if not resultado.get("sucesso"):
            print("[DEMO] Fallback: criando usuário diretamente...")
            # Buscar diretamente no banco ou criar via SQL
            conexao = banco_dados.get_conexao()
            cursor = conexao.cursor()
            try:
                cursor.execute("SELECT id FROM empresas WHERE ruc = %s", ('9999999-9',))
                row = cursor.fetchone()
                if row:
                    empresa_id = row[0]
                    rol = 'admin'
                    plano = 'Demo'
                    print(f"[DEMO] Usuário encontrado diretamente no banco: ID {empresa_id}")
                    resultado = {"sucesso": True, "empresa_id": empresa_id, "rol": rol, "plano": plano}
                else:
                    # Criar empresa diretamente
                    from datetime import date, timedelta
                    vencimento = date.today() + timedelta(days=365)
                    cursor.execute('''
                        INSERT INTO empresas (nome_empresa, ruc, senha_admin, senha_caixa, plano, status_assinatura, data_vencimento, valor_mensalidade)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    ''', ('Usuário Público Demo', '9999999-9', 'demo123', 'demo123', 'Demo', 'Activo', vencimento, 0))
                    empresa_id = cursor.fetchone()[0]
                    
                    # Criar categoria
                    cursor.execute("INSERT INTO categorias (empresa_id, nome) VALUES (%s, %s) ON CONFLICT DO NOTHING", (empresa_id, 'General'))
                    
                    # Criar produtos
                    produtos = [
                        ('ARR-001', 'Arroz Premium 1kg', 'General', '', 10000, 12500, 45, ''),
                        ('ACE-002', 'Aceite Girasol 900ml', 'General', '', 15000, 18500, 28, ''),
                        ('AZU-003', 'Azúcar Refinado 1kg', 'General', '', 7000, 8500, 62, '')
                    ]
                    for cod, desc, cat, subcat, custo, venda, qtd, prov in produtos:
                        cursor.execute('''
                            INSERT INTO produtos (empresa_id, codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        ''', (empresa_id, cod, desc, cat, subcat, custo, venda, qtd, prov))
                    
                    conexao.commit()
                    rol = 'admin'
                    plano = 'Demo'
                    resultado = {"sucesso": True, "empresa_id": empresa_id, "rol": rol, "plano": plano}
                    print(f"[DEMO] Usuário criado diretamente no banco: ID {empresa_id}")
            finally:
                cursor.close()
                conexao.close()
        
        # 4. Verificar se a autenticação foi bem-sucedida
        if not resultado.get("sucesso"):
            raise HTTPException(
                status_code=500,
                detail="Não foi possível criar ou autenticar o usuário demo. Tente novamente mais tarde."
            )
        
        # 4.1 Garantir que os dados demo estejam presentes (produtos, vendas, etc.)
        banco_dados.injetar_dados_demo()
        
        # 5. Extrair dados com verificação de chaves
        empresa_id = resultado.get("empresa_id")
        rol = resultado.get("rol")
        plano = resultado.get("plano")
        
        if empresa_id is None or rol is None or plano is None:
            raise HTTPException(
                status_code=500,
                detail=f"Dados de autenticação incompletos: {resultado}"
            )
        
        plano_primeira = str(plano).split(' ')[0]
        
        print(f"[DEMO] Autenticação bem-sucedida: empresa_id={empresa_id}, rol={rol}, plano={plano}")
        
        # 6. Ler o frontend.html original
        with open("frontend.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # 7. Script de autologin a ser injetado antes do fechamento do </body>
        script_autologin = f"""
    <script>
        // Injeção automática de credenciais demo (execução imediata)
        empresaAtualId = {empresa_id};
        rolUsuario = '{rol}';
        planoAtivo = '{plano}';
        
        // Esconder tela de login e mostrar aplicativo
        const loginScreen = document.getElementById('login-screen');
        if (loginScreen) loginScreen.classList.add('hidden');
        
        const appScreen = document.getElementById('app-screen');
        if (appScreen) {{
            appScreen.classList.remove('hidden');
            appScreen.classList.add('flex');
        }}
        
        const mobileHeader = document.getElementById('mobile-header');
        if (mobileHeader) mobileHeader.classList.remove('hidden');
        
        const sidebarRol = document.getElementById('sidebar-rol-loja');
        if (sidebarRol) sidebarRol.innerText = (rolUsuario === 'admin') ? 
            `Dueño | Plan {plano_primeira}` : `Cajero | Plan {plano_primeira}`;
        
        // Mostrar todos os elementos de navegação
        const idsTodos = ['nav-group-inventario','nav-btn-dashboard','nav-group-reportes',
            'btn-nav-stocktake','btn-nav-stocktakereport','btn-nav-proveedores','btn-nav-entrada',
            'btn-nav-remision','btn-nav-autofactura','btn-nav-variancia','nav-btn-config',
            'nav-btn-ayuda','btn-cerrar-turno'];
        idsTodos.forEach(id => {{
            const el = document.getElementById(id);
            if(el) el.style.display = '';
        }});
        
        const boxNovoProv = document.getElementById('box-novo-prov');
        if(boxNovoProv) boxNovoProv.style.display = 'block';
        
        console.log('[DEMO] Login automático realizado: Empresa ID', empresaAtualId, 'Rol', rolUsuario);
    </script>
    </body>
    """
        
        # Substituir o fechamento </body> pelo script + </body>
        html_content = html_content.replace('</body>', script_autologin)
        
        return HTMLResponse(content=html_content, media_type="text/html")
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEMO ERRO CRÍTICO] {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno na preparação da demo: {str(e)}"
        )

@app.get("/reset-demo")
def reset_demo():
    """Manual trigger to rebuild the demo showroom with 5 providers, 20 products, 25 sales"""
    import json
    import random
    from datetime import datetime, date, timedelta
    
    conexao = None
    cursor = None
    try:
        conexao = banco_dados.get_conexao()
        cursor = conexao.cursor()
        
        # 1. Find or create demo enterprise
        cursor.execute("SELECT id FROM empresas WHERE ruc = %s", ('9999999-9',))
        existing = cursor.fetchone()
        
        if existing:
            empresa_id = existing[0]
            print(f"[RESET DEMO] Enterprise found (ID: {empresa_id})")
        else:
            # Create enterprise
            vencimento = date.today() + timedelta(days=365)
            cursor.execute('''
                INSERT INTO empresas (nome_empresa, ruc, senha_admin, senha_caixa, plano, status_assinatura, data_vencimento, valor_mensalidade)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', ('Usuário Público Demo', '9999999-9', 'demo123', 'demo123', 'Demo', 'Activo', vencimento, 0))
            empresa_id = cursor.fetchone()[0]
            print(f"[RESET DEMO] Enterprise created (ID: {empresa_id})")
        
        # 2. FORCE DELETE ALL DATA FOR THIS ENTERPRISE (except categories and providers that might be shared)
        print(f"[RESET DEMO] Deleting existing sales and products for enterprise {empresa_id}...")
        cursor.execute("DELETE FROM notas WHERE empresa_id = %s", (empresa_id,))
        notas_deleted = cursor.rowcount
        cursor.execute("DELETE FROM produtos WHERE empresa_id = %s", (empresa_id,))
        produtos_deleted = cursor.rowcount
        # Do NOT delete categories and providers; they might be shared or have constraints
        categorias_deleted = 0
        provedores_deleted = 0
        
        # 3. Ensure categories exist (use ON CONFLICT to avoid duplicate key errors)
        categorias_list = ['General', 'Bebidas', 'Lácteos', 'Limpeza', 'Enlatados', 'Panadería', 'Carnes']
        categories_created = 0
        for cat in categorias_list:
            # Try to insert, if conflict (name already exists), do nothing
            cursor.execute('''
                INSERT INTO categorias (empresa_id, nome)
                VALUES (%s, %s)
                ON CONFLICT (nome) DO NOTHING
            ''', (empresa_id, cat))
            categories_created += cursor.rowcount
        print(f"[RESET DEMO] Categories ensured: {categories_created} new, {len(categorias_list)-categories_created} already exist.")
        
        # 4. Insert providers with ON CONFLICT
        provedores = [
            ('Distribuidora Central S.A.', '80012345-1', '021 234 567', 'ventas@distcentral.com.py', 'Av. Eusebio Ayala km 4.5, Asunción'),
            ('Importadora del Este S.R.L.', '80023456-2', '021 345 678', 'contacto@importeste.com.py', 'Av. España 1234, Ciudad del Este'),
            ('Proveedores del Sur S.A.', '80034567-3', '021 456 789', 'info@proveedorsur.com.py', 'Av. San Martín 567, Encarnación'),
            ('Alimentos Norte S.A.', '80045678-4', '021 567 890', 'ventas@alimentosnorte.com.py', 'Av. Perú 789, Concepción'),
            ('Mayorista Py S.R.L.', '80056789-5', '021 678 901', 'pedidos@mayoristapy.com.py', 'Av. Brasília 456, Pedro Juan Caballero')
        ]
        providers_created = 0
        for nome, ruc, telefone, email, endereco in provedores:
            cursor.execute('''
                INSERT INTO proveedores (empresa_id, nome, ruc, telefone, email, endereco)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (empresa_id, ruc) DO NOTHING
            ''', (empresa_id, nome, ruc, telefone, email, endereco))
            providers_created += cursor.rowcount
        print(f"[RESET DEMO] Providers ensured: {providers_created} new, {len(provedores)-providers_created} already exist.")
        
        # 5. Insert 20 products
        produtos = [
            ('ARR-001', 'Arroz Premium 1kg', 'General', '', 10000, 12500, 45),
            ('ACE-002', 'Aceite Girasol 900ml', 'General', '', 15000, 18500, 28),
            ('AZU-003', 'Azúcar Refinado 1kg', 'General', '', 7000, 8500, 62),
            ('COC-004', 'Coca-Cola 2L', 'Bebidas', 'Gaseosas', 8000, 10500, 36),
            ('SPR-005', 'Sprite 1.5L', 'Bebidas', 'Gaseosas', 7500, 9800, 42),
            ('CER-006', 'Cerveza Pilsen 1L', 'Bebidas', 'Alcohólicas', 12000, 15800, 24),
            ('LEH-007', 'Leche Entera 1L', 'Lácteos', '', 6000, 8500, 58),
            ('YOU-008', 'Yogur Natural 1kg', 'Lácteos', '', 8500, 11500, 32),
            ('QUE-009', 'Queso Paraguay 500g', 'Lácteos', '', 22000, 28500, 18),
            ('JAB-010', 'Jabón en Polvo 3kg', 'Limpeza', '', 25000, 32500, 22),
            ('DET-011', 'Detergente Líquido 1L', 'Limpeza', '', 12000, 16500, 40),
            ('PAP-012', 'Papel Higiénico 4un', 'Limpeza', '', 15000, 19500, 55),
            ('ATA-013', 'Atún en Lata 200g', 'Enlatados', '', 7500, 9800, 30),
            ('MAI-014', 'Maíz en Lata 400g', 'Enlatados', '', 6500, 8200, 38),
            ('PAN-015', 'Pan Francês un', 'Panadería', '', 1500, 2500, 120),
            ('RES-016', 'Carne Res 1kg', 'Carnes', '', 35000, 45500, 15),
            ('POL-017', 'Pollo Entero 1.5kg', 'Carnes', '', 22000, 29500, 20),
            ('JAM-018', 'Jamón Cocido 200g', 'Carnes', '', 12500, 16800, 25),
            ('GAL-019', 'Galletas María 500g', 'Panadería', '', 4500, 6500, 48),
            ('CAF-020', 'Café Molido 500g', 'Bebidas', '', 18000, 23500, 16)
        ]
        for cod, desc, cat, subcat, custo, venda, qtd in produtos:
            cursor.execute('''
                INSERT INTO produtos (empresa_id, codigo_barras, descricao, categoria, subcategoria, preco_custo, preco_venda, quantidade, codigo_proveedor)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '')
            ''', (empresa_id, cod, desc, cat, subcat, custo, venda, qtd))
        
        # 5.5 Ensure open cash session and get its ID
        cursor.execute("SELECT id FROM caixa_sessoes WHERE empresa_id = %s AND status = 'ABERTO'", (empresa_id,))
        caixa_row = cursor.fetchone()
        if not caixa_row:
            cursor.execute('''
                INSERT INTO caixa_sessoes (empresa_id, data_abertura, valor_abertura, status)
                VALUES (%s, CURRENT_TIMESTAMP, 500000, 'ABERTO')
                RETURNING id
            ''', (empresa_id,))
            caixa_id = cursor.fetchone()[0]
        else:
            caixa_id = caixa_row[0]
        print(f"[RESET DEMO] Using cash session ID: {caixa_id}")
        
        # 6. Generate 25 sales in the last 30 days
        metodos_pago = ['Efectivo', 'Tarjeta', 'Transferencia', 'Efectivo', 'Tarjeta']
        clientes = [
            ('Consumidor Final', '80012345-1'),
            ('Juan Pérez', '1234567-8'),
            ('María González', '2345678-9'),
            ('Carlos López', '3456789-0'),
            ('Ana Martínez', '4567890-1'),
            ('Luis Rodríguez', '5678901-2'),
            ('Supermercado Central', '80098765-4'),
            ('Restaurante El Buen Sabor', '80087654-3')
        ]
        
        hoje = datetime.now()
        for i in range(25):
            if i < 5:
                dias_atras = 0  # Today - for dashboard
            else:
                dias_atras = random.randint(1, 30)
            horas_atras = random.randint(0, 23)
            minutos_atras = random.randint(0, 59)
            data_venda = hoje - timedelta(days=dias_atras, hours=horas_atras, minutes=minutos_atras)
            
            nome_cliente, ruc_cliente = random.choice(clientes)
            num_itens = random.randint(1, 4)
            itens_selecionados = random.sample(produtos[:15], num_itens)
            
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
            
            cdc = f'9999999-9-{data_venda.strftime("%Y%m%d")}-{i:06d}'
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
        

        
        conexao.commit()
        
        # Inject cash withdrawals (sangrias) for the demo
        motivos_sangria = ["Pago a proveedor", "Gastos operativos", "Retiro de efectivo"]
        for _ in range(3):
            valor_sangria = random.randint(150000, 300000)
            motivo = random.choice(motivos_sangria)
            cursor.execute('''
                INSERT INTO caixa_movimentacoes (empresa_id, caixa_id, tipo, valor, motivo, data)
                VALUES (%s, %s, 'SANGRIA', %s, %s, %s)
            ''', (empresa_id, caixa_id, valor_sangria, motivo, hoje - timedelta(days=random.randint(0, 30))))
        
        # Inject 3 stock take audits for demo (spread over last 30 days)
        for _ in range(3):
            data_auditoria = (hoje - timedelta(days=random.randint(1, 30))).date()
            cursor.execute('''
                INSERT INTO auditorias (empresa_id, data, impacto_financeiro, total_itens)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (empresa_id, data_auditoria, 0, 0))
            auditoria_id = cursor.fetchone()[0]
            
            # Pick 3-5 random products for this audit
            produtos_auditoria = random.sample(produtos[:12], random.randint(3, 5))
            impacto_total = 0
            total_itens = 0
            for prod in produtos_auditoria:
                codigo, descricao, categoria, subcat, custo, venda, estoque = prod
                # Ensure there is a variance (non-zero difference)
                diferenca = random.choice([-2, -1, 1, 2])
                qtd_sistema = estoque
                qtd_fisica = qtd_sistema + diferenca
                custo_unitario = custo
                impacto = diferenca * custo_unitario
                impacto_total += impacto
                total_itens += 1
                cursor.execute('''
                    INSERT INTO auditorias_itens (auditoria_id, codigo_barras, descricao, qtd_sistema, qtd_fisica, diferenca, custo_unitario)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (auditoria_id, codigo, descricao, qtd_sistema, qtd_fisica, diferenca, custo_unitario))
            
            # Update audit total
            cursor.execute('''
                UPDATE auditorias SET impacto_financeiro = %s, total_itens = %s WHERE id = %s
            ''', (impacto_total, total_itens, auditoria_id))
        
        conexao.commit()
        
        return {
            "status": "Success",
            "message": "Showroom built",
            "enterprise_id": empresa_id,
            "deleted": {
                "notas": notas_deleted,
                "produtos": produtos_deleted,
                "categorias": categorias_deleted,
                "provedores": provedores_deleted
            },
            "created": {
                "categorias": categories_created,
                "categorias_total": len(categorias_list),
                "provedores": providers_created,
                "provedores_total": len(provedores),
                "produtos": len(produtos),
                "vendas": 25
            }
        }
        
    except Exception as e:
        # Return exact error
        error_msg = str(e)
        print(f"[RESET DEMO ERROR] {error_msg}")
        if conexao:
            conexao.rollback()
        return {
            "status": "Error",
            "message": error_msg
        }
    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()