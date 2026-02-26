from lxml import etree
import datetime
import random

def calcular_iva(valor_total, taxa=10):
    # Regra oficial: Valor Total / 1.1 (para 10%) ou 1.05 (para 5%)
    divisor = 1.1 if taxa == 10 else 1.05
    base_gravada = round(valor_total / divisor, 2)
    valor_iva = round(valor_total - base_gravada, 2)
    return base_gravada, valor_iva

def gerar_cdc_oficial(ruc_emissor):
    # Gera o CDC de 44 dígitos (Identificador único da nota no Paraguai)
    hoje = datetime.datetime.now().strftime("%Y%m%d")
    ruc_limpo = ruc_emissor.split('-')[0].zfill(8)
    seguranca = "".join([str(random.randint(0, 9)) for _ in range(11)])
    # Tipo(2) + RUC(8) + DV(1) + Est(3) + Pnt(3) + Num(7) + Data(8) + Emis(1) + Seg(11)
    cdc = f"01{ruc_limpo}10010010000001{hoje}1{seguranca}"
    return cdc[:44]

def construir_xml_sifen(dados_nota):
    cdc = gerar_cdc_oficial(dados_nota.ruc_emissor)
    base, imposto = calcular_iva(dados_nota.valor_total, taxa=10)
    
    ns = "http://ekuatia.set.gov.py/sifen/xsd"
    rDE = etree.Element("rDE", xmlns=ns)
    etree.SubElement(rDE, "dVerFor").text = "150"
    
    DE = etree.SubElement(rDE, "DE")
    etree.SubElement(DE, "Id").text = cdc
    
    # Emissor (gEmis)
    emissor = etree.SubElement(DE, "gEmis")
    etree.SubElement(emissor, "dRucEm").text = dados_nota.ruc_emissor.split('-')[0]
    etree.SubElement(emissor, "dDVEmi").text = dados_nota.ruc_emissor.split('-')[1] if '-' in dados_nota.ruc_emissor else "0"
    etree.SubElement(emissor, "dNomEm").text = "SUA EMPRESA S.A."
    
    # Receptor (gDatRec)
    receptor = etree.SubElement(DE, "gDatRec")
    etree.SubElement(receptor, "dNomRec").text = dados_nota.nome_cliente
    
    # Totais (gTotRes)
    totais = etree.SubElement(DE, "gTotRes")
    etree.SubElement(totais, "dTotOpe").text = f"{dados_nota.valor_total:.2f}"
    
    # IVA (gPaEmiIVA) - Onde o governo valida o imposto
    iva_detalhe = etree.SubElement(totais, "gPaEmiIVA")
    etree.SubElement(iva_detalhe, "dBaseGra10").text = f"{base:.2f}"
    etree.SubElement(iva_detalhe, "dIVA10").text = f"{imposto:.2f}"

    xml_string = etree.tostring(rDE, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")
    return xml_string, cdc