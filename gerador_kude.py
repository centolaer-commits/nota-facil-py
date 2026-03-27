import qrcode
from io import BytesIO
from fastapi.responses import StreamingResponse

def gerar_qr_code_sifen(cdc_id: str):
    # Essa é a URL real do governo paraguaio para consulta de notas!
    # O "cdc_id" é aquele código de 44 dígitos (Código de Control)
    url_consulta = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc_id}"
    
    # Cria a imagem do QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url_consulta)
    qr.make(fit=True)
    
    # Pinta o QR Code (fundo branco, linhas pretas)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Salva a imagem na memória (para não precisarmos criar arquivos inúteis no seu PC)
    memoria = BytesIO()
    img.save(memoria, format="PNG")
    memoria.seek(0)
    
    # Retorna a imagem diretamente para a tela do usuário
    return StreamingResponse(memoria, media_type="image/png")