def assinar_documento(xml_string):
    # NOTA: No futuro, usaremos a biblioteca 'signxml' aqui para ler o arquivo .p12
    # do cliente e aplicar a criptografia real (padrão RSA-SHA256) exigida pela DNIT.
    
    # Por enquanto, vamos injetar a estrutura oficial da assinatura digital 
    # para deixarmos o XML no formato final perfeito para os nossos testes.
    
    bloco_assinatura = """
  <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
    <SignedInfo>
      <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
      <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
      <Reference URI="#01234567890123456789012345678901234567890123">
        <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
        <DigestValue>VALOR_HASH_CRIPTOGRAFICO_DE_TESTE=</DigestValue>
      </Reference>
    </SignedInfo>
    <SignatureValue>AQUI_ENTRARA_A_CRIPTOGRAFIA_GIGANTE_DO_CERTIFICADO_REAL</SignatureValue>
  </Signature>
</rDE>"""
    
    # A assinatura digital sempre entra no final do arquivo, logo antes de fechar a tag </rDE>
    # Então substituímos a tag de fechamento pelo bloco de assinatura inteiro.
    xml_assinado = xml_string.replace("</rDE>", bloco_assinatura)
    
    return xml_assinado