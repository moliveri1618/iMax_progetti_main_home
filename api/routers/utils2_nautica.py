from typing import List, Optional, Iterable, Dict
from fastapi import HTTPException
from sqlmodel import Session, select, delete
from datetime import datetime, date
from pprint import pprint
from typing import Any, Dict, List, Optional, Sequence
import json
from pydantic import BaseModel, Field
from fpdf import FPDF
import base64, tempfile
import logging, time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import inspect

import sys
import os


if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
    
# from models.iParametriDaInserire_Nautica import ParametriDaInserireNautica  
# from schemas.iParametriDaInserire_Nautica import TEMPLATE_ROWS, MONTHS, MONTH_ORDER, MONTHS_LIST, TRIM_STARTS, TRIM_WEIGHTS
# from models.vendite import VenditeImax
# from models.iBudgetVendutoCalcoli import BudgetVendutoCalcoli
# from models.iConteggiCommessa import OrdiniPremi
logger = logging.getLogger(__name__)


class MaterialeItem(BaseModel):
    materiale: Optional[str] = None
    ordinare: Optional[bool] = None
    magazzino: Optional[bool] = None
    verificare: Optional[bool] = None


class ClienteLavoro(BaseModel):
    id: Optional[int] = None
    cliente: Optional[str] = None
    switch1: Optional[bool] = None
    switch2: Optional[bool] = None
    switch3: Optional[bool] = None


class Tecnico(BaseModel):
    cliente_materiale_mancante: Optional[List[MaterialeItem]] = None
    cliente_materiale_rientrato: Optional[List[MaterialeItem]] = None

    ticket_n: Optional[str] = None
    del_: Optional[str] = Field(default=None, alias="del")  # accepts JSON key "del"
    cliente: Optional[str] = None
    ordine_n: Optional[str] = None
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    telefono_fisso: Optional[str] = None
    cellulare: Optional[str] = None
    persona_rif: Optional[str] = None
    posatore: Optional[str] = None
    squadra: Optional[str] = None
    tempo_previsto_ore: Optional[str] = None
    int_pian_data_ora: Optional[datetime] = None
    ore_previste_riparazioni: Optional[str] = None
    per_numero_posatori: Optional[str] = None
    note: Optional[str] = None
        
    stato_lavoro: Optional[bool] = None
    informazioni: Optional[bool] = None
    tipo_riparazione: Optional[bool] = None
    fotografie_lavoro_ultimato: Optional[bool] = None
    fotografie_danni_prima_di_iniziare: Optional[bool] = None
    lavoro_non_completato_causa_nostra: Optional[bool] = None
    lavoro_non_completato_causa_cliente: Optional[bool] = None
    danni_vedi_rapporto_posa: Optional[bool] = None
    errore_progettazione: Optional[bool] = None
    errore_scelta_profili_accessori: Optional[bool] = None
    errore_misure_nel_rilievo: Optional[bool] = None
    difficolta_trasporto_non_segnalate: Optional[bool] = None
    errore_calcolo_disposizione: Optional[bool] = None
    vetro_rotto: Optional[bool] = None
    materiale_mancante_non_caricato: Optional[bool] = None
    materiali_posa_mancanti: Optional[bool] = None
    vetro_rotto_posa: Optional[bool] = None
    materiali_profili_danneggiati: Optional[bool] = None
    mancanza_attrezzature: Optional[bool] = None
    danneggiamento_casa_cliente: Optional[bool] = None
    errore_misure_ordine: Optional[bool] = None
    errore_calcolo_tempo_disposizione: Optional[bool] = None
    errore_materiale_contratto: Optional[bool] = None
    cliente_lavori_eseguiti: Optional[List[ClienteLavoro]] = None


    signature: Optional[str] = None

    model_config = {
        "populate_by_name": True,   
        "extra": "ignore",          
    }
    

    
class Cliente(BaseModel):
    cliente_ticket_n: Optional[str] = None
    cliente_del: Optional[str] = None
    cliente_cliente: Optional[str] = None
    ordine_cliente: Optional[str] = None
    indirizzo_cliente: Optional[str] = None
    citta_cliente: Optional[str] = None
    telefono_fisso_cliente: Optional[str] = None
    cellulare_cliente: Optional[str] = None
    persona_di_riferimento_cliente: Optional[str] = None
    posatore_cliente: Optional[str] = None
    squadra_cliente: Optional[str] = None
    tempo_previsto_ore_cliente: Optional[str] = None
    data_cliente: Optional[datetime] = None
    cellulare_cliente_cliente: Optional[str] = None
    signature_cliente_posatore: Optional[str] = None
    signature_cliente_cliente: Optional[str] = None
    note_cliente: Optional[str] = None

class ReportData(BaseModel):
    tecnico: Optional[Tecnico] = None
    cliente: Optional[Cliente] = None  
    

def signature_block(pdf, text, sig_data, left_w=140, right_w=50, line_h=8, pad=3):
    """
    Draws a signature block with explanatory text on the left and 
    a signature box (with optional image) on the right.

    Args:
        pdf: FPDF object
        text (str): explanatory text for the left cell
        sig_data (str): signature from JSON (data:image/png;base64,...)
        left_w (int): width of explanatory cell
        right_w (int): width of signature box
        line_h (int): line height for text
        pad (int): padding inside the signature box
    """

    # --- Save start position
    x0, y0 = pdf.get_x(), pdf.get_y()

    # --- Left explanatory cell ---
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", "B", 10)
    pdf.multi_cell(left_w, line_h, text, border=1, fill=True)
    y_after = pdf.get_y()

    # Height used
    h_box = y_after - y0

    # --- Right signature box ---
    x_box = x0 + left_w
    pdf.set_xy(x_box, y0)
    pdf.set_fill_color(255, 255, 255)
    pdf.cell(right_w, h_box, "", border=1, fill=True, align="C")

    # --- Insert signature image if present ---
    if isinstance(sig_data, str) and sig_data.startswith("data:image/"):
        try:
            header, b64 = sig_data.split(",", 1)

            # infer extension from MIME
            ext = "png"
            if header.startswith("data:image/") and ";base64" in header:
                ext = header[len("data:image/"): header.index(";base64")] or "png"

            img_bytes = base64.b64decode(b64)

            # write to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                tmp_path = tmp.name
                tmp.write(img_bytes)

            # place image with padding
            pdf.image(
                tmp_path,
                x=x_box + pad,
                y=y0 + pad,
                w=right_w - 2*pad,  # height auto to keep aspect ratio
            )

        except Exception as e:
            print(f"[signature] failed to render: {e}")
        finally:
            try:
                if 'tmp_path' in locals() and os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

    # --- Move cursor to end of block ---
    pdf.set_y(y_after)

def note_box(pdf, title, body=None, *, height=85, title_fs=12, end_gap=10):
    """
    Draw a wide note rectangle with a blue title, stopping before the page end.
    - height: requested box height
    - end_gap: space to leave between the box bottom and page bottom margin
    """
    x, y = pdf.get_x(), pdf.get_y()
    w = pdf.w - pdf.l_margin - pdf.r_margin

    # --- Outer rectangle ---
    pdf.set_draw_color(140, 140, 140)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(x, y, w, height, style="FD")

    # --- Title ---
    pdf.set_text_color(0, 0, 255)
    pdf.set_font("Arial", "", title_fs)
    pdf.set_xy(x + 5, y + 4)
    pdf.cell(w - 10, 6, title, border=0, ln=1)

    # --- Body (optional) ---
    if body:
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "", 11)
        pdf.set_xy(x + 5, y + 12)
        usable_h = height - 16  # space below the title
        pdf.multi_cell(w - 10, 6, body, border=0)

    # Move cursor below the box
    pdf.set_y(y + height)

    # reset colors
    pdf.set_text_color(0, 0, 0)
    pdf.set_draw_color(0, 0, 0)

def build_pdf_report_cliente(data):
    
    def add_pdf_header(pdf: FPDF, title: str, *, left_ratio=0.66, h=26, pad=6):
        #geometry
        x0, y0 = pdf.l_margin, pdf.get_y()
        full_w = pdf.w - pdf.l_margin - pdf.r_margin
        left_w  = full_w / 2.0               # <-- exact middle
        right_w = full_w - left_w

        # Left pane (no border so the center stays exact)
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x0, y0, left_w, h, 'F')

        # Right pane
        pdf.set_fill_color(127, 255, 212)    # your mint color
        pdf.rect(x0 + left_w, y0, right_w, h, 'F')

        # One outer border + a center divider (optional but crisp)
        pdf.set_draw_color(190, 190, 190)
        pdf.rect(x0, y0, full_w, h, 'D')             # outer frame
        pdf.line(x0 + left_w, y0, x0 + left_w, y0 + h)  # center split

        # ---- draw Mulattieri mark ----
        # red icon
        icon = h * 0.68
        ix = x0 + pad
        iy = y0 + (h - icon) / 2
        pdf.set_fill_color(230, 0, 0)
        pdf.rect(ix, iy, icon, icon, "F")
        # two white “windows”
        m = icon * 0.16
        w = icon * 0.26
        g = icon * 0.12
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(ix + m,           iy + m, w, icon - 2*m, "F")
        pdf.rect(ix + m + w + g,   iy + m, w, icon - 2*m, "F")

        # “MULATTIERI”
        tx = ix + icon + pad
        pdf.set_text_color(34, 64, 180)        # deep blue
        pdf.set_font("Arial", "B", 18)
        pdf.set_xy(tx, y0 + 3)
        pdf.cell(left_w - (tx - x0) - 4, h/2, "MULATTIERI", border=0, align="L")

        # tagline
        pdf.set_text_color(130, 130, 130)
        pdf.set_font("Arial", "", 14)
        pdf.set_xy(tx, y0 + h/2 + 1)
        pdf.cell(left_w - (tx - x0) - 4, h/2, "porte e finestre", border=0, align="L")

        # ---- right green title block ----
        pdf.set_xy(x0 + left_w, y0)
        pdf.set_fill_color(127, 255, 212)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 18)
        pdf.cell(right_w, h, title, border=0, fill=True, align="C")

        # move below header
        pdf.ln(h + 2)

        # restore defaults so later table borders don’t inherit colors
        pdf.set_draw_color(0, 0, 0)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(255, 255, 0)

    t = getattr(data, "tecnico", None) or type("Empty", (), {})()
    pdf = FPDF()
    pdf.add_page()
    add_pdf_header(pdf, title="Report Intervento Cliente")
    pdf.set_font("Arial", size=12)

    def gv(name, default=""):
        """get value from tecnico, defaulting to '' (or provided) if missing/None"""
        return getattr(t, name, None) if getattr(t, name, None) is not None else default

    def gvl(name):
        """get list value"""
        v = getattr(t, name, None)
        return v if isinstance(v, list) else []

    def gvb(name):
        """get boolean value"""
        v = getattr(t, name, None)
        return bool(v) if v is not None else False

    def fmt_dt(dt):
        v = gv(dt, None)
        if not v:
            return "", ""
        try:
            # pydantic may give datetime already; otherwise ISO string
            d = v if isinstance(v, datetime) else datetime.fromisoformat(str(v))
            return d.strftime("%d/%m/%Y"), d.strftime("%H:%M")
        except Exception:
            return str(v), ""

    def ensure_space(pdf: FPDF, needed_h: float):
        """Start a new page if the next block won't fit."""
        if pdf.get_y() + needed_h > pdf.page_break_trigger:
            pdf.add_page()

    def write_cell(w, h, text='', fill=False, align='L', bold=False):
        family = pdf.font_family or "Arial"
        size = pdf.font_size_pt or 12
        style = "B" if bold else ""
        pdf.set_font(family, style=style, size=size)
        pdf.cell(w, h, text or "", border=1, fill=fill, align=align)

    def green_rule(height=3):
        """Draw a full-width green bar at the current Y, then move cursor down."""
        x = pdf.l_margin
        y = pdf.get_y()
        w = pdf.w - pdf.l_margin - pdf.r_margin
        # draw filled green rect (no border)
        pdf.set_fill_color(127, 255, 212)
        pdf.rect(x, y, w, height, style='F')
        pdf.ln(height)
        # restore your default fill color (yellow for cells, per your code)
        pdf.set_fill_color(255, 255, 0)
        
    def green_rule(height=3, x_start=None):
        """Draw a green bar from a given X to the right margin, then move cursor down."""
        if x_start is None:
            x_start = pdf.l_margin  # fallback to left margin

        y = pdf.get_y()
        w = pdf.w - x_start - pdf.r_margin  # width from x_start to right margin

        pdf.set_fill_color(127, 255, 212)
        pdf.rect(x_start, y, w, height, style='F')
        pdf.ln(height)

        # restore default fill color (yellow, per your example)
        pdf.set_fill_color(255, 255, 0)

    def draw_checkbox(pdf, x, y, size=5, checked=False):
        # outer yellow box
        pdf.set_draw_color(0, 0, 0)
        pdf.set_fill_color(255, 235, 59)  # soft yellow (#FFEB3B)
        pdf.rect(x, y, size, size, 'DF')

        # inner light square
        pad = 1.2
        pdf.set_fill_color(245, 245, 245)  # very light gray
        pdf.rect(x + pad, y + pad, size - 2*pad, size - 2*pad, 'F')

        # checkmark if selected
        if checked:
            pdf.set_draw_color(0, 128, 0)
            pdf.set_line_width(0.6)
            pdf.line(x + 0.8, y + size*0.55, x + size*0.45, y + size - 0.9)
            pdf.line(x + size*0.45, y + size - 0.9, x + size - 0.8, y + 1.0)
        pdf.set_line_width(0.2)  # reset

    def three_checkbox_cell_right_optional(
        pdf,
        cell_h,
        materiale,
        ordinare=None,
        magazzino=None,
        verificare=None,
        *,
        green_rgb=(0, 255, 0),
        yellow_rgb=(255, 255, 0),
        mat_fill_rgb=(255, 255, 255),
    ):
        """
        States:
        True   -> green background + checkbox with checkmark
        False  -> yellow background + empty checkbox
        None/""-> horizontal lines only (no box, no fill)
        """
        x0, y0 = pdf.get_x(), pdf.get_y()

        # Left description cell 
        pdf.set_fill_color(*mat_fill_rgb)
        pdf.rect(x0, y0, 100, cell_h, 'F')   
        pdf.set_draw_color(0, 0, 0)
        pdf.line(x0, y0, x0, y0 + cell_h)
        pdf.line(x0, y0, x0 + 100, y0)
        pdf.line(x0, y0 + cell_h, x0 + 100, y0 + cell_h)
        pdf.set_xy(x0 + 2, y0)
        pdf.cell(96, cell_h, materiale or "", border=0, align="L")

        def norm_state(v):
            if v is True:
                return "checked"
            if v is False:
                return "unchecked"
            if v is None or (isinstance(v, str) and v.strip() == ""):
                return "empty"
            return "checked" if bool(v) else "unchecked"

        def box_cell(x, v):
            state = norm_state(v)

            if state == "checked":
                pdf.set_fill_color(*green_rgb)
                pdf.rect(x, y0, 30, cell_h, 'DF')
                size = 5
                bx = x + (30 - size) / 2
                by = y0 + (cell_h - size) / 2
                draw_checkbox(pdf, bx, by, size=size, checked=True)

            elif state == "unchecked":
                pdf.set_fill_color(*yellow_rgb)
                pdf.rect(x, y0, 30, cell_h, 'DF')
                size = 5
                bx = x + (30 - size) / 2
                by = y0 + (cell_h - size) / 2
                draw_checkbox(pdf, bx, by, size=size, checked=False)

            else:  # "empty"
                # only horizontal lines (top and bottom)
                pdf.set_draw_color(0, 0, 0)
                pdf.line(x, y0, x + 30, y0)             # top line
                pdf.line(x, y0 + cell_h, x + 30, y0 + cell_h)  # bottom line

        box_cell(x0 + 100, ordinare)
        box_cell(x0 + 130, magazzino)
        box_cell(x0 + 160, verificare)

        pdf.set_xy(x0, y0 + cell_h)

    def one_checkbox_cell_right(
        pdf,
        cell_h,
        materiale,
        checked=None,                      # True -> green + check, False -> yellow empty, None -> only horizontals
        *,
        left_w=160,                        # width of "materiale" cell
        box_w=30,                          # width of the right checkbox cell
        green_rgb=(0, 255, 0),
        yellow_rgb=(255, 255, 0),
        mat_fill_rgb=(255, 255, 255),      # fill for "materiale"
        empty_fill_rgb=None,               # optional fill for empty state; None keeps only horizontals
    ):
        """
        Draws: [  materiale (left_w)  |  checkbox (box_w)  ]
        Borders: left cell has LEFT+TOP+BOTTOM; no right border (to avoid vertical seam).
                Right cell: filled (F) with no borders for checked/unchecked; only top/bottom lines for empty.
        """
        x0, y0 = pdf.get_x(), pdf.get_y()

        # --- Left "materiale" cell ---
        pdf.set_fill_color(*mat_fill_rgb)
        pdf.rect(x0, y0, left_w, cell_h, 'F')                 # fill only
        pdf.set_draw_color(0, 0, 0)
        pdf.line(x0, y0, x0, y0 + cell_h)                     # left border
        pdf.line(x0, y0, x0 + left_w, y0)                     # top
        pdf.line(x0, y0 + cell_h, x0 + left_w, y0 + cell_h)   # bottom
        pdf.set_xy(x0 + 2, y0)
        pdf.set_font("Arial", "", 12)
        pdf.cell(left_w - 4, cell_h, materiale or "", border=0, align="L")

        # --- Right checkbox cell ---
        x_box = x0 + left_w
        state = (
            "checked"   if checked is True else
            "unchecked" if checked is False else
            "empty"
        )

        if state in ("checked", "unchecked"):
            # background fill without borders
            pdf.set_fill_color(*(green_rgb if state == "checked" else yellow_rgb))
            pdf.rect(x_box, y0, box_w, cell_h, 'DF')

            # checkbox graphic
            size = 5
            bx = x_box + (box_w - size) / 2
            by = y0 + (cell_h - size) / 2
            draw_checkbox(pdf, bx, by, size=size, checked=(state == "checked"))

        else:  # empty -> only horizontals (optional fill)
            if empty_fill_rgb is not None:
                pdf.set_fill_color(*empty_fill_rgb)
                pdf.rect(x_box, y0, box_w, cell_h, 'DF')
            pdf.set_draw_color(0, 0, 0)
            pdf.line(x_box, y0, x_box + box_w, y0)                # top
            pdf.line(x_box, y0 + cell_h, x_box + box_w, y0 + cell_h)  # bottom

        # erase any left seam from previous cell (defensive)
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.2)
        pdf.line(x_box, y0, x_box, y0 + cell_h)
        pdf.set_line_width(0.2)
        pdf.set_draw_color(0, 0, 0)

        # move to next row
        pdf.set_xy(x0, y0 + cell_h)

    def three_checkbox_cell_right(pdf, cell_h, materiale,
                                ordinare=False, magazzino=False, verificare=False,
                                green_rgb=(0, 255, 0), yellow_rgb=(255, 255, 0)):
        """
        Draw a row with Materiale description and 3 checkboxes (Ordinare, Magaz., Verificare).
        If checked, cell background is green; otherwise yellow.
        """
        x0, y0 = pdf.get_x(), pdf.get_y()

        # --- Materiale cell (left column, stays white always) ---
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x0, y0, 100, cell_h, 'DF')
        pdf.set_xy(x0 + 2, y0)
        pdf.cell(100 - 4, cell_h, materiale or "", border=0, align="L")

        # --- Helper for the 3 checkbox cells ---
        def box_cell(x, checked):
            if checked:
                pdf.set_fill_color(*green_rgb)   # green if checked
            else:
                pdf.set_fill_color(*yellow_rgb)  # yellow if not checked
            pdf.rect(x, y0, 30, cell_h, 'DF')

            # Draw checkbox inside
            size = 5
            box_x = x + (30 - size) / 2
            box_y = y0 + (cell_h - size) / 2
            draw_checkbox(pdf, box_x, box_y, size=size, checked=checked)

        # --- Three checkbox cells ---
        box_cell(x0 + 100, ordinare)
        box_cell(x0 + 130, magazzino)
        box_cell(x0 + 160, verificare)

        # --- Move cursor to next row ---
        pdf.set_xy(x0, y0 + cell_h)

    def checkbox_cell_split(pdf, cell_w, cell_h, label, checked, *,
                        font_size=12, box_col_w=10, gap=2,
                        green_rgb=(0, 255, 0), yellow_rgb=(255, 255, 0)):
        """
        [ left column (green if checked, yellow if not) | label column ]
        """
        x0, y0 = pdf.get_x(), pdf.get_y()

        # Save current font
        cur_font, cur_style, cur_size = pdf.font_family, pdf.font_style, pdf.font_size_pt

        # --- Left column (checkbox area background) ---
        if checked:
            pdf.set_fill_color(*green_rgb)   # green if checked
        else:
            pdf.set_fill_color(*yellow_rgb)  # yellow if not checked
        pdf.rect(x0, y0, box_col_w, cell_h, 'DF')

        # draw the checkbox square inside
        size = 5
        bx = x0 + (box_col_w - size) / 2
        by = y0 + (cell_h - size) / 2
        draw_checkbox(pdf, bx, by, size=size, checked=checked)

        # --- Right column (label) ---
        pdf.set_fill_color(255, 255, 255)  # always white
        pdf.rect(x0 + box_col_w, y0, cell_w - box_col_w, cell_h, 'DF')
        pdf.set_font(cur_font, cur_style, font_size)
        pdf.set_xy(x0 + box_col_w + gap, y0)
        pdf.cell(cell_w - box_col_w - 2*gap, cell_h, label or "", border=0, align="L")

    sections = [
        # --- First block: fotografie + danni ---
        {
            "header": None,  # no section header here
            "rows": [
                ("FOTOGRAFIE PER TUTELA DANNI PRIMA DI INIZIARE I LAVORI", gvb("fotografie_danni_prima_di_iniziare"), (255, 0, 0)),
                ("FOTOGRAFIE LAVORO ULTIMATO",                             gvb("fotografie_lavoro_ultimato"),          (255, 255, 255)),
                ("LAVORO NON COMPLETATO CAUSA NOSTRA",                     gvb("lavoro_non_completato_causa_nostra"),  (255, 255, 255)),
                ("LAVORO NON COMPLETATO CAUSA CLIENTE",                    gvb("lavoro_non_completato_causa_cliente"), (255, 255, 255)),
                ("SONO STATI ARRECATI DANNI VEDI RAPPORTO POSA",           gvb("danni_vedi_rapporto_posa"),            (255, 255, 255)),
            ],
        },

        # --- Second block: TECNICO ---
        {
            "header": "TECNICO",
            "rows": [
                ("ERRORE PROGETTAZIONE",                gvb("errore_progettazione"),               (230, 230, 230)),
                ("ERRORE SCELTA PROFILI ACCESSORI",     gvb("errore_scelta_profili_accessori"),    (230, 230, 230)),
                ("ERRORE MISURE NEL RILIEVO",           gvb("errore_misure_nel_rilievo"),          (230, 230, 230)),
                ("DIFFICOLTA' TRASPORTO NON SEGNALATE", gvb("difficolta_trasporto_non_segnalate"), (230, 230, 230)),
                ("ERRORE CALCOLO TEMPO A DISPOSIZIONE", gvb("errore_calcolo_disposizione"),        (230, 230, 230)),
            ],
        },

        # --- Third block: UFFICIO ---
        {
            "header": "UFFICIO",
            "rows": [
                ("ERRORE MISURE",                       gvb("errore_progettazione"),            (230, 230, 230)),
                ("ERRORE CALCOLO TEMPO A DISPOSIZIONE", gvb("errore_scelta_profili_accessori"), (230, 230, 230)),
            ],
        },
        # COMMERCIALE
        {
            "header": "COMMERCIALE",
            "rows": [
                ("ERRORE MATERIALE/COLORE NEL CONTRATTO", gvb("errore_misure_nel_rilievo"), (230, 230, 230))
            ],
        },
        # POSATORI
        {
            "header": "POSATORI",
            "rows": [
                ("VETRO ROTTO DURANTE LA POSA",                   gvb("vetro_rotto"),                   (230, 230, 230)),
                ("MATERIALI-PROFILI DANNEGGIATI DURANTE LA POSA", gvb("materiali_profili_danneggiati"), (230, 230, 230)),
                ("MANCANZA ATTREZZATURE NON CARICATE",            gvb("mancanza_attrezzature"),         (230, 230, 230)),
                ("DANNEGGIAMENTO CASA DEL CLIENTE",               gvb("danneggiamento_casa_cliente"),   (230, 230, 230))
            ],
        },
        # MAGAZZINO
        {
            "header": "MAGAZZINO",
            "rows": [
                ("VETRO ROTTO DIFETTOSO DA SOTITUIRE",      gvb("errore_materiale_contratto"),  (230, 230, 230)),
                ("MATERIALE MANCANTE NON CARICATO",         gvb("mancanza_attrezzature"),       (230, 230, 230)),
                ("MATERIALI DI POSA MANCANTI NON CARICATI", gvb("errore_misure_ordine"),        (230, 230, 230))
            ],
        },
        # FORNITORE
        {
            "header": "FORNITORE",
            "rows": [
                ("VETRO ROTTO DIFETTOSO DA SOTITUIRE CAUSA FORNITORE",  gvb("errore_materiale_contratto"),  (230, 230, 230)),
                ("MATERIALE MANCANTE CAUSA FORNITORE",                  gvb("mancanza_attrezzature"),       (230, 230, 230)),
                ("ERRORE TIPOLOGIA MATERIALE CAUSA FORNITORE",          gvb("errore_misure_ordine"),        (230, 230, 230)),
                ("MATERIALE DIFETTOSO CAUSA FORNITORE",                 gvb("danneggiamento_casa_cliente"), (230, 230, 230))
            ],
        },
    ]

    pairs = [
        # (label1, value1, width1, widthVal1, label2, value2, width2, widthVal2)
        ("Cliente", gv("cliente"), 30, 60, "Ordine N°", gv("ordine_n"), 30, 70),
        ("Indirizzo", gv("indirizzo"), 30, 60, "Città", gv("citta"), 30, 70),
        ("Telefono fisso", gv("telefono_fisso"), 30, 60, "Cellulare", gv("cellulare"), 30, 70),
        ("Persona rif", gv("persona_rif"), 30, 60, "Cellulare", gv("cellulare"), 30, 70),
        ("Posatore", gv("posatore"), 30, 60, "SQUADRA", gv("squadra"), 30, 70),
    ]

    checkbox_groups = [
        (
            "STATO LAVORO",
            [
                ("Completato", gvb("stato_lavoro"), 60),
                ("Da Completare", not gvb("stato_lavoro"), 82),
            ],
        ),
        (
            "Informazioni",
            [
                ("Già Cliente", gvb("informazioni"), 60),
                ("E' STATO ESEGUITO IL SOPRALLUOGO", gvb("informazioni"), 82, 10),  # font_size override
            ],
        ),
        (
            "Tipo Riparazione",
            [
                ("Riparazione STD", gvb("tipo_riparazione"), 60),
                ("Riparazione in Garanzia", not gvb("tipo_riparazione"), 82),
            ],
        ),
    ]

    # region pdf Build Code
    
    # Ticket / Del / Data
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(30, 8, "Ticket N°", fill=True, bold=True)
    write_cell(60, 8, gv("ticket_n"))
    write_cell(30, 8, "Del", fill=True, bold=True)
    write_cell(70, 8, gv("del"))
    pdf.ln()
    green_rule(height=2)   

    # cliente indirizzo tel fisso persona rif popsatore
    for i, (lbl1, val1, w1, wval1, lbl2, val2, w2, wval2) in enumerate(pairs, start=1):
        ensure_space(pdf, 8)
        pdf.set_fill_color(230, 230, 230)
        write_cell(w1, 8, lbl1, fill=True, bold=True)
        write_cell(wval1, 8, val1)
        write_cell(w2, 8, lbl2, fill=True, bold=True)
        write_cell(wval2, 8, val2)
        pdf.ln()

        if i == 3:   # after the 3rd iteration
            green_rule(height=2)

    # Tempo prev. ore / Intervento pianificato / Data & Ora
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(50, 8, "Tempo PREVISTO ORE", fill=True, bold=True)
    write_cell(40, 8, gv("tempo_previsto_ore"))
    write_cell(50, 8, "Intervento pianificato x:", fill=True, bold=True)
    date_str, time_str = fmt_dt("int_pian_data_ora")
    pdf.set_fill_color(255, 255, 0)
    write_cell(30, 8, date_str, fill=True)  
    write_cell(20, 8, time_str, fill=True)  
    pdf.ln()
    green_rule(height=2)   
    
    # stato lavoro, informazioni, tipo riparazione
    for title, checkboxes in checkbox_groups:
        pdf.set_fill_color(204, 255, 204)
        ensure_space(pdf, 8)
        write_cell(50, 8, title, bold=True, fill=True)
        for cb in checkboxes:
            if len(cb) == 3:
                label, checked, width = cb
                checkbox_cell_split(pdf, width, 8, label, checked=checked)
            else:
                label, checked, width, font_size = cb
                checkbox_cell_split(pdf, width, 8, label, checked=checked, font_size=font_size)
        pdf.ln()
        green_rule(height=2)

    # Cose da fare
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(190, 8, "Cose da fare", bold=True, fill=True, align='C')
    pdf.ln()
    
    for item in gvl("cliente_lavori_eseguiti"):
        d = item if isinstance(item, dict) else getattr(item, "model_dump", lambda: {})()
        if callable(d):
            d = d()
        three_checkbox_cell_right_optional(
            pdf, 8,
            materiale=d.get("cliente"),
            ordinare="",
            magazzino="",
            verificare=d.get("switch1"),
        )
        
    #  Materiale mancante 
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(100, 8, "Materiale mancante", bold=True, fill=True)
    write_cell(30, 8, "Ordinare", bold=True, fill=True, align="C")
    write_cell(30, 8, "Magaz.", bold=True, fill=True, align="C")
    write_cell(30, 8, "Verificare", bold=True, fill=True, align="C")
    pdf.ln()
    
    for item in gvl("cliente_materiale_mancante"):
        d = item if isinstance(item, dict) else getattr(item, "model_dump", lambda: {})()
        if callable(d):
            d = d()
        ensure_space(pdf, 8)
        three_checkbox_cell_right(
            pdf, 8,
            materiale=d.get("materiale"),
            ordinare=bool(d.get("ordinare")),
            magazzino=bool(d.get("magazzino")),
            verificare=bool(d.get("verificare")),
        )
    
    # Materiale rientrato 
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(100, 8, "Materiale rientrato", bold=True, fill=True)
    write_cell(30, 8, "Riportare", bold=True, fill=True, align="C")
    write_cell(30, 8, "Reso", bold=True, fill=True, align="C")
    write_cell(30, 8, "Avanzo", bold=True, fill=True, align="C")
    pdf.ln()
    
    for item in gvl("cliente_materiale_rientrato"):
        d = item if isinstance(item, dict) else getattr(item, "model_dump", lambda: {})()
        if callable(d):
            d = d()
        ensure_space(pdf, 8)
        three_checkbox_cell_right(
            pdf, 8,
            materiale=d.get("materiale"),
            ordinare=bool(d.get("ordinare")),
            magazzino=bool(d.get("magazzino")),
            verificare=bool(d.get("verificare")),
        )

    # ---------- Ore previste ----------
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(60, 8, "Ore previste per finire rip", fill=True, bold=True)
    write_cell(40, 8, gv("ore_previste_riparazioni"))
    write_cell(50, 8, "Per quanti posatori", fill=True, bold=True)
    write_cell(40, 8, gv("per_numero_posatori"))
    pdf.ln()

    # FOTOGRAFIE TUTELA, TECNICO, UFFICIO, COMMERCIALE, POSATORI, MAGAZZINO, FORNITORE
    for section in sections:
        if section["header"]:
            pdf.set_fill_color(230, 230, 230)
            write_cell(190, 8, f" {section['header']}", bold=True, fill=True)
            pdf.ln()

        for label, check_value, bg_color in section["rows"]:
            ensure_space(pdf, 8)
            one_checkbox_cell_right(
                pdf, 8,
                materiale=label,
                checked=check_value,
                left_w=160,
                box_w=30,
                mat_fill_rgb=bg_color,
                empty_fill_rgb=None,
            )
        pdf.ln()
        
    # Firma del posatore
    ensure_space(pdf, 8)
    signature_block(
        pdf,
        text=(
            "FIRMA DEL POSATORE  Il tecnico dichiara, sotto la propria responsabilità, "
            "che tutto quanto sopra indicato corrisponde al vero ed è consapevole e "
            "informato di eventuali sanzioni disciplinari o addebiti nel caso quanto "
            "dichiarato non corrisponda a verità."
        ),
        sig_data=gv("signature"),
    )

    # ---------- Note ----------
    ensure_space(pdf, 8)
    note_box(
        pdf,
        title="NOTE descrivere eventuali difetti riscontrati o danni causati all'interno dell'abitazione:",
        body=gv("note"),
        height=85,       # your desired size
        end_gap=5       # leave ~12 pts before page bottom
    )

    content = pdf.output(dest='S')
    return content.encode('latin-1') if isinstance(content, str) else content

