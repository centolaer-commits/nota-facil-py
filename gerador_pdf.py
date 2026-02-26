from fpdf import FPDF
import os
import qrcode

def gerar_pdf_nota(dados_nota, cdc):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "FACTURA ELECTRÓNICA SIFEN", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, f"RUC Emisor: {dados_nota.ruc_emissor}", ln=True, align="C")
    pdf.ln(5)
    
    # Corpo
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DATOS DE LA OPERACIÓN", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(2)
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(0, 10, f"Cliente: {dados_nota.nome_cliente}", ln=True)
    pdf.ln(5)

    # Tabela de Produtos (NOVO)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(90, 8, "Descripción", border=1)
    pdf.cell(25, 8, "Cant.", border=1, align="C")
    pdf.cell(35, 8, "Precio Uni.", border=1, align="R")
    pdf.cell(40, 8, "Subtotal", border=1, align="R")
    pdf.ln(8)

    pdf.set_font("Arial", "", 10)
    for item in dados_nota.itens:
        subtotal = item.quantidade * item.preco_unitario
        pdf.cell(90, 8, str(item.descricao)[:40], border=1)
        pdf.cell(25, 8, str(item.quantidade), border=1, align="C")
        pdf.cell(35, 8, f"Gs. {item.preco_unitario:,.0f}", border=1, align="R")
        pdf.cell(40, 8, f"Gs. {subtotal:,.0f}", border=1, align="R")
        pdf.ln(8)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"TOTAL: Gs. {dados_nota.valor_total:,.0f}", ln=True, align="R")
    
    # Rodapé com CDC e QR Code
    pdf.ln(5)
    pdf.set_font("Arial", "I", 9)
    pdf.multi_cell(0, 5, f"CDC (Código de Control): {cdc}")
    
    url_consulta = f"https://ekuatia.set.gov.py/consultas/qr?nId={cdc}"
    qr = qrcode.make(url_consulta)
    temp_qr = f"temp_qr_{cdc[:10]}.png"
    qr.save(temp_qr)
    
    pdf.image(temp_qr, x=80, y=pdf.get_y() + 5, w=50)
    
    pdf.set_y(pdf.get_y() + 60)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Consulte la validez en el sitio web de la SET/DNIT", ln=True, align="C")

    if not os.path.exists("notas_pdf"):
        os.makedirs("notas_pdf")

    nome_arquivo = f"notas_pdf/nota_{cdc[:10]}.pdf"
    pdf.output(nome_arquivo)
    
    if os.path.exists(temp_qr):
        os.remove(temp_qr)
    
    return nome_arquivo