from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
from signxml import XMLSigner, methods
from lxml import etree
import os

def carregar_certificado_p12(caminho_p12, senha):
    """Abre o ficheiro .p12 e extrai a Chave Privada e o Certificado Público."""
    with open(caminho_p12, "rb") as f:
        p12_data = f.read()
    
    # Extrai os dados usando a password fornecida pelo lojista
    private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
        p12_data, senha.encode()
    )
    return private_key, certificate

def assinar_documento(xml_string, caminho_p12, senha):
    """Aplica a assinatura XMLDSig Enveloped exigida pela SIFEN."""
    try:
        private_key, cert = carregar_certificado_p12(caminho_p12, senha)
        
        # Converte o XML de texto para um objeto manipulável
        root = etree.fromstring(xml_string.encode('utf-8'))
        
        # Prepara as chaves no formato PEM
        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Assinatura Enveloped (SHA256) conforme o manual técnico da DNIT
        signer = XMLSigner(method=methods.enveloped, signature_algorithm="rsa-sha256", digest_algorithm="sha256")
        signed_root = signer.sign(root, key=key_pem, cert=cert_pem)
        
        # Devolve o XML final já carimbado
        return etree.tostring(signed_root, encoding='unicode')
        
    except Exception as e:
        print(f"Erro na assinatura digital: {e}")
        raise e