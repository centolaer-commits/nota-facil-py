import random
from datetime import datetime

def calcular_dv_modulo11(numero_str):
    soma = 0
    peso = 2
    for digito in reversed(numero_str):
        soma += int(digito) * peso
        peso += 1
        if peso > 7:
            peso = 2
    resto = soma % 11
    dv = 11 - resto
    if dv >= 10: dv = 0
    return str(dv)

def gerar_cdc_sifen(ruc_emissor, tipo_doc="01", estab="001", pex="001", numero_nota="0000001", data_emissao=None, tipo_emissao="1"):
    if not data_emissao: data_emissao = datetime.now()
    
    if "-" in ruc_emissor:
        ruc_base, ruc_dv = ruc_emissor.split("-")
    else:
        ruc_base = ruc_emissor[:-1]
        ruc_dv = ruc_emissor[-1]
    
    ruc_base = ruc_base.zfill(8)
    tipo_contribuyente = "2" 
    fecha_str = data_emissao.strftime("%Y%m%d")
    codigo_aleatorio = str(random.randint(1, 999999999)).zfill(9)

    cdc_43 = f"{tipo_doc}{ruc_base}{ruc_dv}{estab}{pex}{numero_nota}{tipo_contribuyente}{fecha_str}{tipo_emissao}{codigo_aleatorio}"
    dv_cdc = calcular_dv_modulo11(cdc_43)
    return f"{cdc_43}{dv_cdc}"

def construir_xml_sifen(dados, config_empresa):
    """
    Constrói a árvore XML completa com base no Manual Técnico da SIFEN (V150)
    """
    cdc_real = gerar_cdc_sifen(dados.ruc_emissor)
    csc = config_empresa.get("csc", "0000000000000000")
    data_hora_atual = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    # Dados da Empresa
    nome_empresa = config_empresa.get("nome_empresa", "Empresa S.A.")
    if "-" in dados.ruc_emissor:
        ruc_emissor_base, ruc_emissor_dv = dados.ruc_emissor.split("-")
    else:
        ruc_emissor_base = dados.ruc_emissor[:-1]
        ruc_emissor_dv = dados.ruc_emissor[-1]
        
    # Dados do Cliente (Se não tiver RUC, assumimos Consumidor Final)
    cliente_nome = dados.nome_cliente if dados.nome_cliente else "Consumidor Final"
    
    # 1. Montagem dos Itens (gCamItem) e somatórios
    xml_itens = ""
    total_iva = 0
    
    for i, item in enumerate(dados.itens, 1):
        descricao = item.descricao
        quantidade = item.quantidade
        preco_unitario = item.preco_unitario
        subtotal_item = quantidade * preco_unitario
        iva_item = round(subtotal_item / 11, 2) # Cálculo padrão IVA 10%
        total_iva += iva_item
        
        # Tag oficial de cada linha da fatura
        xml_itens += f"""
            <gCamItem>
                <dTipOp>1</dTipOp>
                <dCodInt>{item.codigo_barras or '000'}</dCodInt>
                <dDesProSer>{descricao}</dDesProSer>
                <dCantProSer>{quantidade}</dCantProSer>
                <gValorItem>
                    <dPUniProSer>{preco_unitario}</dPUniProSer>
                    <dTotBruOpeItem>{subtotal_item}</dTotBruOpeItem>
                </gValorItem>
                <gCamIVA>
                    <iAfecIVA>1</iAfecIVA>
                    <dPropIVA>100</dPropIVA>
                    <dTasaIVA>10</ddTasaIVA>
                    <dLiqIVAItem>{iva_item}</dLiqIVAItem>
                </gCamIVA>
            </gCamItem>"""

    # 2. Estrutura Raiz (rDE)
    xml_bruto = f"""<?xml version="1.0" encoding="UTF-8"?>
<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
    <dVerFor>150</dVerFor>
    <DE Id="{cdc_real}">
        <dDVId>{cdc_real[-1]}</dDVId>
        <dFecFirma>{data_hora_atual}</dFecFirma>
        <dSisFact>1</dSisFact>
        <gOpeDE>
            <iTipEmi>1</iTipEmi>
            <dDesTipEmi>Normal</dDesTipEmi>
            <dCodSeg>{csc}</dCodSeg>
        </gOpeDE>
        <gTimb>
            <iTiDE>1</iTiDE>
            <dNumTim>12345678</dNumTim>
            <dEst>001</dEst>
            <dPunExp>001</dPunExp>
            <dNumDoc>0000001</dNumDoc>
        </gTimb>
        <gDatGralOpe>
            <dFeEmiDE>{data_hora_atual}</dFeEmiDE>
            <gEmis>
                <dRucEm>{ruc_emissor_base}</dRucEm>
                <dDVEmi>{ruc_emissor_dv}</dDVEmi>
                <dNomEmi>{nome_empresa}</dNomEmi>
            </gEmis>
            <gDatRec>
                <iNatRec>1</iNatRec>
                <dNomRec>{cliente_nome}</dNomRec>
            </gDatRec>
        </gDatGralOpe>
        <gDtipDE>
            <gCamFE>
                <iIndPres>1</iIndPres>
            </gCamFE>
        </gDtipDE>
        <gTotSub>
            <dSubExe>0</dSubExe>
            <dSubExo>0</dSubExo>
            <dSub5>0</dSub5>
            <dSub10>{dados.valor_total}</dSub10>
            <dTotOpe>{dados.valor_total}</dTotOpe>
            <dTotGralOpe>{dados.valor_total}</dTotGralOpe>
            <dIVA5>0</dIVA5>
            <dIVA10>{total_iva}</dIVA10>
            <dLiqTotIVA5>0</dLiqTotIVA5>
            <dLiqTotIVA10>{total_iva}</dLiqTotIVA10>
            <dTotalIVA>{total_iva}</dTotalIVA>
        </gTotSub>
        <gDetGral>
            {xml_itens}
        </gDetGral>
    </DE>
</rDE>"""
    
    return xml_bruto, cdc_real