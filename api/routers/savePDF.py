from fastapi import APIRouter
import sys
import os
import io
import os
from fastapi.responses import StreamingResponse
from typing import Optional
from fastapi import BackgroundTasks

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from routers.utils import send_email_with_retry, ReportData, build_pdf_report_tecnico

router = APIRouter()


@router.post("/generate-report")
async def generate_from_json(
    data: ReportData,
    background_tasks: BackgroundTasks,
    email:  Optional[str] = "mauro.oliveri16@gmail.com"
):
    
    # Generate PDF TECNICO & CLIENTE
    pdf_tecnico = build_pdf_report_tecnico(data)


    # SEND EMAIL
    background_tasks.add_task(send_email_with_retry,email, pdf_tecnico, "report_intervento_tecnico.pdf")  #send_email_with_retry(email, pdf_tecnico, "report_intervento_tecnico.pdf")

    buffer = io.BytesIO(pdf_tecnico)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=posa_layout.pdf"
    })
    


# @router.get("/generate-layout2")
# def generate_layout22():
#     pdf = FPDF()
#     pdf.add_page()
#     pdf.set_font("Arial", size=12)

#     def cell(w, h, txt, fill=False, align="L"):
#         pdf.cell(w, h, txt, border=1, ln=0, align=align, fill=fill)

#     def linebreak(h=8):
#         pdf.ln(h)

#     # Title
#     pdf.set_font(style="B")
#     pdf.cell(0, 10, "Report Commessa\nPosa in Opera", align="C", ln=True)
#     pdf.set_font(style="")

#     # Cliente info
#     cell(40, 8, "Cliente")
#     cell(60, 8, "")
#     cell(40, 8, "Ordine")
#     cell(50, 8, "")
#     linebreak()

#     cell(40, 8, "SQUADRA Posatori")
#     cell(60, 8, "")
#     cell(40, 8, "Data")
#     cell(50, 8, "")
#     linebreak()

#     # Stato posa
#     pdf.set_fill_color(255, 255, 0)
#     cell(40, 8, "STATO 1° POSA", fill=True)
#     cell(40, 8, "Completata", fill=True)
#     cell(40, 8, "", fill=True)
#     cell(40, 8, "Da Completare", fill=True)
#     linebreak()

#     cell(190, 8, "Resta da fare")
#     linebreak()

#     # Materiale mancante
#     cell(80, 8, "Materiale mancante")
#     cell(30, 8, "Ordinare")
#     cell(30, 8, "Magaz.")
#     cell(30, 8, "Verificare")
#     linebreak()

#     for _ in range(3):
#         cell(80, 8, "")
#         for val in ["TRUE", "FALSE", "FALSE"]:
#             pdf.set_fill_color(255, 255, 0)
#             cell(30, 8, val, fill=True)
#         linebreak()

#     # Materiale rientrato
#     cell(80, 8, "Materiale rientrato")
#     cell(30, 8, "Riportare")
#     cell(30, 8, "Reso")
#     cell(30, 8, "Avanzo")
#     linebreak()

#     for _ in range(3):
#         cell(80, 8, "")
#         for val in ["FALSE", "FALSE", "FALSE"]:
#             pdf.set_fill_color(255, 255, 0)
#             cell(30, 8, val, fill=True)
#         linebreak()

#     # Ore previste
#     cell(80, 8, "Ore previste finitura")
#     cell(110, 8, "Per numero posatori")
#     linebreak()

#     # Notes
#     pdf.set_font(size=10)
#     pdf.multi_cell(0, 7, """
# PULIZIA DEI VETRI E/O FINESTRE (CONTROLLO SE PRESENZA DI DIFETTI) - TOGLIERE ETICHETTE
# GIRO CON IL CLIENTE, PRODOTTO PER PRODOTTO SU CORRETTA FUNZIONALITA'
# """)
#     # Optional booleans
#     cell(100, 8, "")
#     for val in ["FALSE", "FALSE"]:
#         pdf.set_fill_color(255, 255, 0)
#         cell(30, 8, val, fill=True)
#     linebreak()

#     # Return PDF in memory
#     buffer = io.BytesIO(pdf.output(dest="S"))
#     return StreamingResponse(buffer, media_type="application/pdf", headers={
#         "Content-Disposition": "attachment; filename=posa_report.pdf"
#     })

