from fpdf import FPDF
import os

def gerar_pdf_nota(dados_nota, cdc):
    pdf = FPDF()
    pdf.add_page()
    
    # Cabeçalho - Nome da Empresa
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "NOTA FÁCIL PY - EMISSOR SIFEN", ln=True, align="C")
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 7, f"RUC Emissor: {dados_nota.ruc_emissor}", ln=True, align="C")
    pdf.ln(10) # Pula linha
    
    # Corpo da Nota
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DADOS DA OPERAÇÃO", ln=True)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y()) # Linha horizontal
    
    pdf.set_font("Arial", "", 11)
    pdf.cell(100, 10, f"Cliente: {dados_nota.nome_cliente}", ln=False)
    pdf.cell(0, 10, f"Total: Gs. {dados_nota.valor_total:,.0f}", ln=True, align="R")
    
    pdf.ln(5)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 10, f"CDC (Id de Controle): {cdc}", ln=True)
    
    # Rodapé com QR Code fictício (Espaço reservado)
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 10, "Consulte a validade no site da SET/DNIT", ln=True, align="C")

    # Criamos uma pasta para salvar os PDFs se ela não existir
    if not os.path.exists("notas_pdf"):
        os.makedirs("notas_pdf")

    nome_arquivo = f"notas_pdf/nota_{cdc[:10]}.pdf"
    pdf.output(nome_arquivo)
    
    return nome_arquivo