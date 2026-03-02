import random
from datetime import datetime

# Algoritmo Oficial da SIFEN (Módulo 11) para calcular o Dígito Verificador (DV)
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

# Função que monta os 44 dígitos exatos do CDC
def gerar_cdc_sifen(ruc_emissor, tipo_doc="01", estab="001", pex="001", numero_nota="0000001", data_emissao=None, tipo_emissao="1"):
    if not data_emissao:
        data_emissao = datetime.now()
    
    # Limpar o RUC (Ex: '80012345-6' -> Base: '80012345', DV: '6')
    if "-" in ruc_emissor:
        ruc_base, ruc_dv = ruc_emissor.split("-")
    else:
        ruc_base = ruc_emissor[:-1]
        ruc_dv = ruc_emissor[-1]
    
    # A SIFEN exige que o RUC base tenha 8 dígitos (preenchido com zeros à esquerda)
    ruc_base = ruc_base.zfill(8)
    
    tipo_contribuyente = "2" # 2 = Persona Jurídica (Empresa)
    fecha_str = data_emissao.strftime("%Y%m%d")
    codigo_aleatorio = str(random.randint(1, 999999999)).zfill(9)

    # Montagem dos 43 primeiros dígitos segundo o manual
    cdc_43 = f"{tipo_doc}{ruc_base}{ruc_dv}{estab}{pex}{numero_nota}{tipo_contribuyente}{fecha_str}{tipo_emissao}{codigo_aleatorio}"
    
    # Cálculo do 44º dígito (DV do CDC)
    dv_cdc = calcular_dv_modulo11(cdc_43)
    
    cdc_completo = f"{cdc_43}{dv_cdc}"
    return cdc_completo

# Esta função será expandida na Fase 2 para gerar o XML completo
def construir_xml_sifen(dados):
    # Por enquanto, gera o CDC real validado matematicamente
    cdc_real = gerar_cdc_sifen(dados.ruc_emissor)
    
    # O XML completo faremos na Fase 2
    xml_bruto = f"<xml><cdc>{cdc_real}</cdc></xml>" 
    return xml_bruto, cdc_real