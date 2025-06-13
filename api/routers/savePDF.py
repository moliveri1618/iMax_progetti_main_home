from fastapi import APIRouter, HTTPException
import sys
import os
import io
from fastapi import HTTPException
from fastapi.responses import FileResponse
import uuid
import os
from fpdf import FPDF
from fastapi.responses import StreamingResponse

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))

from schemas.savePDF import RecordData

router = APIRouter()


from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List
from fpdf import FPDF
import io

class MaterialeItem(BaseModel):
    materiale: str
    ordinare: bool
    magazzino: bool
    verificare: bool

class ReportData(BaseModel):
    cliente: str
    ordine: str
    squadra_posatori: str
    stato_posa: str
    resta_da_fare: str
    cliente_materiale_mancante: List[MaterialeItem]
    cliente_materiale_rientrato: List[MaterialeItem]
    ore_previste_finitura: str
    per_numero_posatori: str

app = FastAPI()

@app.post("/generate-from-json")
async def generate_from_json(data: ReportData):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    def write_cell(w, h, text='', fill=False, align='L', bold=False):
        if bold:
            pdf.set_font(style="B")
        else:
            pdf.set_font(style="")
        pdf.cell(w, h, text, border=1, fill=fill, align=align)

    pdf.set_fill_color(255, 255, 0)  # yellow

    # Header
    pdf.set_font("Arial", style="B", size=14)
    pdf.cell(0, 10, "Report Commessa Posa in Opera", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.ln(3)

    # Cliente/Ordine row
    write_cell(50, 10, "Cliente", bold=True)
    write_cell(70, 10, data.cliente)
    write_cell(30, 10, "Ordine", bold=True)
    write_cell(40, 10, data.ordine)
    pdf.ln()

    # Squadra/Data row
    write_cell(50, 10, "SQUADRA Posatori", bold=True)
    write_cell(70, 10, data.squadra_posatori)
    write_cell(30, 10, "Data", bold=True)
    write_cell(40, 10, "")  # Not in schema
    pdf.ln()

    # Stato POSA
    write_cell(50, 10, "STATO 1° POSA", bold=True, fill=True)
    write_cell(70, 10, "Completata" if data.stato_posa == "Completata" else "", fill=(data.stato_posa == "Completata"))
    write_cell(70, 10, "Da Completare" if data.stato_posa != "Completata" else "", fill=(data.stato_posa != "Completata"))
    pdf.ln()

    # Resta da fare
    write_cell(190, 10, data.resta_da_fare)
    pdf.ln()

    # Materiale mancante header
    write_cell(80, 10, "Materiale mancante", bold=True)
    write_cell(30, 10, "Ordinare", bold=True)
    write_cell(30, 10, "Magaz.", bold=True)
    write_cell(30, 10, "Verificare", bold=True)
    pdf.ln()

    for item in data.cliente_materiale_mancante:
        write_cell(80, 10, item.materiale)
        write_cell(30, 10, str(item.ordinare).upper(), fill=item.ordinare)
        write_cell(30, 10, str(item.magazzino).upper(), fill=item.magazzino)
        write_cell(30, 10, str(item.verificare).upper(), fill=item.verificare)
        pdf.ln()

    # Materiale rientrato header
    write_cell(80, 10, "Materiale rientrato", bold=True)
    write_cell(30, 10, "Riportare", bold=True)
    write_cell(30, 10, "Reso", bold=True)
    write_cell(30, 10, "Avanzo", bold=True)
    pdf.ln()

    for item in data.cliente_materiale_rientrato:
        write_cell(80, 10, item.materiale)
        write_cell(30, 10, str(item.ordinare).upper(), fill=item.ordinare)
        write_cell(30, 10, str(item.magazzino).upper(), fill=item.magazzino)
        write_cell(30, 10, str(item.verificare).upper(), fill=item.verificare)
        pdf.ln()

    # Ore previste
    write_cell(80, 10, "Ore previste finitura", bold=True)
    write_cell(110, 10, data.ore_previste_finitura)
    pdf.ln()

    write_cell(80, 10, "Per numero posatori", bold=True)
    write_cell(110, 10, data.per_numero_posatori)
    pdf.ln()

    # Notes
    pdf.ln(3)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 8, "PULIZIA DEI VETRI E/O FINESTRE (CONTROLLO SE PRESENZA DI DIFETTI) - TOGLIERE ETICHETTE\nGIRO CON IL CLIENTE, PRODOTTO PER PRODOTTO SU CORRETTA FUNZIONALITA'")
    pdf.ln()

    # Extra dummy TRUE/FALSE values if needed (for layout)
    write_cell(95, 10, "")
    write_cell(30, 10, "FALSE", fill=True)
    write_cell(30, 10, "FALSE", fill=True)
    pdf.ln()

    buffer = io.BytesIO(pdf.output(dest='S'))
    return StreamingResponse(buffer, media_type="application/pdf", headers={
        "Content-Disposition": "attachment; filename=posa_layout.pdf"
    })



@app.get("/generate-layout2")
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

