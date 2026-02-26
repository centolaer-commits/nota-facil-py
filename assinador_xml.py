import os
from lxml import etree
from signxml import XMLSigner
from cryptography.hazmat.primitives.serialization import pkcs12

# --- CONFIGURAÇÃO DO CERTIFICADO DO CLIENTE ---
# Quando o cliente te der o certificado, você colocará o nome do arquivo e a senha aqui
CAMINHO_CERTIFICADO = "certificado_empresa.p12"
SENHA_CERTIFICADO = b"senha_do_cliente_aqui" 
# (A letra 'b' antes das aspas é obrigatória no Python para senhas de criptografia)

def assinar_documento(xml_string):
    """
    Tenta assinar com o Certificado Real. Se não encontrar o arquivo,
    usa o modo de simulação para não travar o desenvolvimento.
    """
    if not os.path.exists(CAMINHO_CERTIFICADO):
        print("⚠️ AVISO: Certificado .p12 não encontrado. Usando Assinatura Simulada.")
        return assinatura_simulada(xml_string)
        
    try:
        # 1. Abre o "cofre" do certificado .p12
        with open(CAMINHO_CERTIFICADO, "rb") as arquivo_cert:
            p12_dados = arquivo_cert.read()

        # 2. Usa a senha para extrair a Chave Privada da empresa
        private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
            p12_dados, 
            SENHA_CERTIFICADO
        )

        # 3. Prepara o XML para ser carimbado
        root = etree.fromstring(xml_string.encode('utf-8'))

        # 4. Aplica a Criptografia (Padrão SIFEN RSA-SHA256)
        signer = XMLSigner(signature_algorithm="rsa-sha256", digest_algorithm="sha256")
        xml_assinado = signer.sign(root, key=private_key, cert=certificate)

        # 5. Devolve o XML pronto e legalmente válido
        return etree.tostring(xml_assinado, encoding="utf-8").decode("utf-8")

    except ValueError:
        print("❌ ERRO: A senha do certificado está incorreta!")
        raise Exception("Senha do certificado digital inválida.")
    except Exception as e:
        print(f"❌ ERRO na Assinatura Digital: {e}")
        raise Exception("Falha ao assinar o documento.")

def assinatura_simulada(xml_string):
    """
    Função de "estepe" que mantém o sistema funcionando na sua máquina
    enquanto o cliente não compra o certificado real.
    """
    assinatura_falsa = """
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
            <Reference URI="">
                <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                <DigestValue>simulacao_digest_value_base64_aqui</DigestValue>
            </Reference>
        </SignedInfo>
        <SignatureValue>simulacao_assinatura_criptografica_aqui</SignatureValue>
    </Signature>
    """
    # Insere a assinatura falsa no final do XML antes de fechar a tag principal
    xml_string = xml_string.replace("</rDE>", f"{assinatura_falsa}</rDE>")
    return xml_string