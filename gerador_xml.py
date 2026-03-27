from lxml import etree

def construir_xml_sifen(dados_nota):
    # 1. Cria a tag principal do sistema SIFEN (rDE)
    rDE = etree.Element("rDE", xmlns="http://ekuatia.set.gov.py/sifen/xsd")
    
    # 2. Versão do Formato
    dVerFor = etree.SubElement(rDE, "dVerFor")
    dVerFor.text = "150" 
    
    # 3. Bloco do Documento Eletrônico (DE)
    DE = etree.SubElement(rDE, "DE")
    
    id_nota = etree.SubElement(DE, "Id")
    id_nota.text = "01234567890123456789012345678901234567890123"
    
    # 4. Dados do Emissor
    emissor = etree.SubElement(DE, "Emissor")
    ruc_em = etree.SubElement(emissor, "dRucEm")
    ruc_em.text = dados_nota.ruc_emissor
    
    # 5. Dados do Recebedor
    recebedor = etree.SubElement(DE, "Recebedor")
    nom_rec = etree.SubElement(recebedor, "dNomRec")
    nom_rec.text = dados_nota.nome_cliente
    
    # 6. Totais e CÁLCULO INTELIGENTE DO IMPOSTO (IVA 10%)
    totais = etree.SubElement(DE, "Totais")
    val_tot = etree.SubElement(totais, "dTotOpe")
    val_tot.text = str(dados_nota.valor_total)

    # A matemática: Arredondamos para 2 casas decimais para evitar erros com centavos
    valor_iva_calculado = round(dados_nota.valor_total / 11, 2)

    # Criamos a tag de impostos que a Receita exige
    impostos = etree.SubElement(totais, "Impostos")
    iva_10 = etree.SubElement(impostos, "dIVA10")
    iva_10.text = str(valor_iva_calculado)

    # Converte para XML formatado
    xml_string = etree.tostring(rDE, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode("utf-8")
    
    return xml_string