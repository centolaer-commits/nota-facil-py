import os
import tempfile
import requests
from zeep import Client
from zeep.transports import Transport
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
import base64

def extrair_certificados_temporarios(caminho_p12, senha):
    """Extrai o certificado e a chave privada para arquivos temporários (exigência da biblioteca Requests/Zeep para mTLS)"""
    with open(caminho_p12, "rb") as f:
        p12_data = f.read()
    
    private_key, cert, _ = pkcs12.load_key_and_certificates(p12_data, senha.encode())
    
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Cria arquivos temporários invisíveis
    fd_cert, cert_path = tempfile.mkstemp(suffix=".crt")
    with os.fdopen(fd_cert, 'wb') as f:
        f.write(cert_pem)
        
    fd_key, key_path = tempfile.mkstemp(suffix=".key")
    with os.fdopen(fd_key, 'wb') as f:
        f.write(key_pem)
        
    return cert_path, key_path

def enviar_xml_para_sifen(xml_assinado, caminho_p12, senha, ambiente="testes", ruc_emissor=None):
    """Envia o XML para a SIFEN usando SOAP e mTLS"""
    
    # Escudo SIFEN: usuário demo nunca envia dados reais para a SET
    if ruc_emissor == "9999999-9":
        print(f"[SIFEN DEMO] Bloqueio de envio real para usuário demo (RUC {ruc_emissor})")
        return {
            "sucesso": True,
            "codigo_retorno": "0000",
            "mensagem_retorno": "Simulación exitosa (Modo Demo)",
            "raw_response": "DEMO-MOCK"
        }
    
    # URLs oficiais baseadas no manual
    if ambiente == "produccion":
        wsdl_url = "https://sifen.set.gov.py/de/ws/sync/recepcion.wsdl"
    else:
        wsdl_url = "https://sifen-test.set.gov.py/de/ws/sync/recepcion.wsdl"
    
    cert_path = None
    key_path = None
    
    try:
        # Prepara a criptografia da conexão
        cert_path, key_path = extrair_certificados_temporarios(caminho_p12, senha)
        
        session = requests.Session()
        session.cert = (cert_path, key_path)
        # SIFEN as vezes exige desabilitar verificação estrita em ambiente de testes
        session.verify = False 
        
        transport = Transport(session=session)
        client = Client(wsdl=wsdl_url, transport=transport)
        
        # A SIFEN espera o XML codificado em Base64 para evitar quebra de caracteres
        xml_base64 = base64.b64encode(xml_assinado.encode('utf-8')).decode('utf-8')
        
        # A chamada oficial do WebService: rEnviDe (Recepção Síncrona de 1 Documento)
        # O ID é gerado sequencialmente pela sua empresa
        resposta = client.service.rEnviDe(
            dId=1, 
            xDE=xml_base64
        )
        
        # Processa a resposta da SET
        return {
            "sucesso": True,
            "codigo_retorno": resposta.dCodRes,
            "mensagem_retorno": resposta.dMsgRes,
            "raw_response": str(resposta)
        }
        
    except Exception as e:
        return {
            "sucesso": False,
            "erro": str(e)
        }
        
    finally:
        # Limpeza de Segurança: Apaga as chaves da máquina imediatamente
        if cert_path and os.path.exists(cert_path):
            os.remove(cert_path)
        if key_path and os.path.exists(key_path):
            os.remove(key_path)