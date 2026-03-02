import random
from datetime import datetime

# Algoritmo Oficial da SIFEN (Módulo 11)
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
    if dv >= 10:
        dv = 0
    return str(dv)

def gerar_cdc_sifen(ruc_emissor, tipo_doc="01", estab="001", pex="001", numero_nota="0000001", data_emissao=None, tipo_emissao="1"):
    if not data_emissao:
        data_emissao = datetime.now()
    
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
    cdc_real = gerar_cdc_sifen(dados.ruc_emissor)
    csc = config_empresa.get("csc", "0000000000000000")
    data_hora_atual = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    # Estrutura raiz obrigatória da DNIT (rDE)
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
        </DE>
</rDE>"""
    
    return xml_bruto, cdc_real