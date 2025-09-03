from fastapi import APIRouter
import sys
import os
import io
import os
from fpdf import FPDF
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
from routers.utils import send_email, ReportData, build_report_pdf, build_report_pdf2

router = APIRouter()


### TEST OBJ ###
'''
{
  "cliente": "Mario Rossi",
  "ordine": "ORD-2025-001",
  "squadra_posatori": "Squadra A",
  "stato_posa": "Completata",
  "resta_da_fare": "Nessuna attività residua",
  "cliente_materiale_mancante": [
    {
      "materiale": "Vite autofilettante",
      "ordinare": true,
      "magazzino": false,
      "verificare": false
    },
    {
      "materiale": "Silicone trasparente",
      "ordinare": false,
      "magazzino": true,
      "verificare": true
    }
  ],
  "cliente_materiale_rientrato": [
    {
      "materiale": "Guarnizione",
      "ordinare": false,
      "magazzino": true,
      "verificare": false
    },
    {
      "materiale": "Tasselli",
      "ordinare": false,
      "magazzino": false,
      "verificare": true
    }
  ],
  "ore_previste_finitura": "4 ore",
  "per_numero_posatori": "2"
}
'''


@router.post("/generate-report")
async def generate_from_json(
    data: ReportData,
    report_type: Optional[int] = None,
    email:  Optional[str] = None
):
    
    # # Generate PDF
    # pdf_bytes = build_report_pdf(data)
    pdf_bytes = build_report_pdf2(data)
    
    # SEND EMAIL
    #send_email(pdf_bytes, filename="posa_layout.pdf")

    buffer = io.BytesIO(pdf_bytes)
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=posa_layout.pdf"
    })
    


@router.get("/generate-layout2")
def generate_layout22():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    def cell(w, h, txt, fill=False, align="L"):
        pdf.cell(w, h, txt, border=1, ln=0, align=align, fill=fill)

    def linebreak(h=8):
        pdf.ln(h)

    # Title
    pdf.set_font(style="B")
    pdf.cell(0, 10, "Report Commessa\nPosa in Opera", align="C", ln=True)
    pdf.set_font(style="")

    # Cliente info
    cell(40, 8, "Cliente")
    cell(60, 8, "")
    cell(40, 8, "Ordine")
    cell(50, 8, "")
    linebreak()

    cell(40, 8, "SQUADRA Posatori")
    cell(60, 8, "")
    cell(40, 8, "Data")
    cell(50, 8, "")
    linebreak()

    # Stato posa
    pdf.set_fill_color(255, 255, 0)
    cell(40, 8, "STATO 1° POSA", fill=True)
    cell(40, 8, "Completata", fill=True)
    cell(40, 8, "", fill=True)
    cell(40, 8, "Da Completare", fill=True)
    linebreak()

    cell(190, 8, "Resta da fare")
    linebreak()

    # Materiale mancante
    cell(80, 8, "Materiale mancante")
    cell(30, 8, "Ordinare")
    cell(30, 8, "Magaz.")
    cell(30, 8, "Verificare")
    linebreak()

    for _ in range(3):
        cell(80, 8, "")
        for val in ["TRUE", "FALSE", "FALSE"]:
            pdf.set_fill_color(255, 255, 0)
            cell(30, 8, val, fill=True)
        linebreak()

    # Materiale rientrato
    cell(80, 8, "Materiale rientrato")
    cell(30, 8, "Riportare")
    cell(30, 8, "Reso")
    cell(30, 8, "Avanzo")
    linebreak()

    for _ in range(3):
        cell(80, 8, "")
        for val in ["FALSE", "FALSE", "FALSE"]:
            pdf.set_fill_color(255, 255, 0)
            cell(30, 8, val, fill=True)
        linebreak()

    # Ore previste
    cell(80, 8, "Ore previste finitura")
    cell(110, 8, "Per numero posatori")
    linebreak()

    # Notes
    pdf.set_font(size=10)
    pdf.multi_cell(0, 7, """
PULIZIA DEI VETRI E/O FINESTRE (CONTROLLO SE PRESENZA DI DIFETTI) - TOGLIERE ETICHETTE
GIRO CON IL CLIENTE, PRODOTTO PER PRODOTTO SU CORRETTA FUNZIONALITA'
""")
    # Optional booleans
    cell(100, 8, "")
    for val in ["FALSE", "FALSE"]:
        pdf.set_fill_color(255, 255, 0)
        cell(30, 8, val, fill=True)
    linebreak()

    # Return PDF in memory
    buffer = io.BytesIO(pdf.output(dest="S"))
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=posa_report.pdf"
    })

