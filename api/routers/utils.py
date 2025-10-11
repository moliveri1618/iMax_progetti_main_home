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
    
from models.iParametriDaInserire import ParametriDaInserire  
from schemas.iParametriDaInserire import TEMPLATE_ROWS, MONTHS, MONTH_ORDER, MONTHS_LIST, TRIM_STARTS, TRIM_WEIGHTS
from models.vendite import VenditeImax
from models.iBudgetVendutoCalcoli import BudgetVendutoCalcoli
from models.iConteggiCommessa import OrdiniPremi
logger = logging.getLogger(__name__)


###   REPORTDATA MODELS     ###
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
    

# --- REPORT POST VENDITA ---
class PosaCliente(BaseModel):
    cliente: str
    ordine: str
    squadra_posatori: str
    data: str
    stato_posa: str
    resta_da_fare: str
    pulizia_vetri: bool
    giro_cliente: bool
    consegna_documenti: bool
    giro_cliente_conformita: bool
    consegna_libretto: bool
    ddt_verbal_firmati: bool
    difetti_vetri: bool
    difetti_profili: bool
    difetti_muratura: bool
    danni_arrecati: bool
    signature: str

class Materiale(BaseModel):
    materiale: str
    ordinare: bool
    magazzino: bool
    verificare: bool

class ReportFotografico(BaseModel):
    foto_danni_inizio: bool
    danni_posa_cliente: bool
    foto_giunti_posa: bool
    foto_lavoro_ultimato: bool
    lavoro_non_completato_nostro: bool
    lavoro_non_completato_cliente: bool

class Errori(BaseModel):
    errore_progettazione: bool
    errore_scelta_profili_accessori: bool
    errore_misure_nel_rilievo: bool
    difficolta_trasporto_non_segnalate: bool
    errore_calcolo_tempo_disp: bool

class Posatori(BaseModel):
    vetro_rotto_durante_la_posa: bool
    materiali_danneggiati_durante_posa: bool
    mancanza_attr_non_caricate: bool
    danneggiamento_casa_cliente: bool
    errore_calcolo_tempo_disp: bool

class Ufficio(BaseModel):
    errore_misure_ordine: bool
    errore_calcolo_tempo: bool

class Coomerciale(BaseModel):
    errore_materiale_contratto: bool
    errore_scelta_profili_accessori_comm: bool

class Magazzino(BaseModel):
    vetro_rotto_difettoso: bool
    materiale_mancante_non_caricato: bool
    materiali_posa_mancanti_noncaricati: bool
    difficolta_trasporto_non_segnalate: bool
    errore_calcolo_tempo_disp: bool

class Fornitore(BaseModel):
    materiale_difettoso_causa_fornitore: bool
    errore_tipologia_materiale_causa_fornitore: bool
    vetro_rotto_diffettoso_causa_fornitore: bool
    materiale_mancante_causa_fornitore: bool

class PosaCommessa(BaseModel):
    cliente_cliente: str
    cliente_ordine: str
    cliente_squadra_posatori: str
    cliente_data: str
    cliente_stato_posa: str
    cliente_materiale_mancante: List[Materiale]
    cliente_materiale_rientrato: List[Materiale]
    ore_previste_finitura: str
    per_numero_posatori: str
    report_fotografico: ReportFotografico
    errori: Errori
    posatori: Posatori
    ufficio: Ufficio
    coomerciale: Coomerciale
    magazzino: Magazzino
    fornitore: Fornitore
    signature_cliente: str

class ReportPostVendita(BaseModel):
    posa_cliente: PosaCliente
    posa_commessa: PosaCommessa






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

def order_rows_by_month(rows: Iterable[Dict]) -> List[Dict]:
    """Return rows ordered Gen→Dic using MONTH_ORDER."""
    return sorted(rows, key=lambda r: MONTH_ORDER[str(r["mese"]).strip().lower()])

def json_to_dict(rows: Optional[Sequence[Any]]) -> Optional[List[Dict[str, Any]]]:
    if rows is None:
        return None
    out: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, str):
            try:
                r = json.loads(r)
            except Exception:
                # skip or raise depending on your needs
                continue
        if hasattr(r, "model_dump"):     # Pydantic v2 / SQLModel new
            out.append(r.model_dump())
        elif hasattr(r, "dict"):         # Pydantic v1 / SQLModel old
            out.append(r.dict())
        elif isinstance(r, dict):
            out.append(r)
        else:
            raise TypeError(f"Unexpected row type: {type(r)!r}")
    return out

def compute_progressivi_mensili(obiettivi: List[float]) -> List[float]:
    cumul = 0.0
    out: List[float] = []
    for v in obiettivi:
        cumul += v
        out.append(cumul)
    return out

def compute_progressivi_trimestrali(obiettivi: List[float]) -> List[Optional[float]]:
    
    out: List[Optional[float]] = []
    cumul_q = 0.0
    for i, v in enumerate(obiettivi):
        cumul_q += v
        end_of_quarter = (i % 3) == 2  # Mar, Jun, Sep, Dec (0-based)
        if end_of_quarter:
            out.append(cumul_q)
            cumul_q = 0.0
        else:
            out.append(None)
    return out

def _to_datetime(d):
    if isinstance(d, datetime):
        return d
    if isinstance(d, date):
        return datetime(d.year, d.month, d.day)
    if isinstance(d, str):
        # Try common formats + ISO
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(d, fmt)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(d)  # handles "YYYY-MM-DD HH:MM:SS"
        except Exception:
            return None
    return None

def compute_venduto_reale(db, year=None):
    if year is None:
        year = date.today().year

    sums = [0.0] * 12

    vendite = db.exec(select(VenditeImax)).all()

    for v in vendite:
        dt = _to_datetime(v.data)
        if not dt or dt.year != year:
            continue
        sums[dt.month - 1] += float(v.quantita or 0)

    return sums

def compute_consuntivo_venduto_trimestrale(venduto, fatturato_del_trimestre):
    out = []
    for i, _ in enumerate(venduto):
        # end of quarter months are indices 2, 5, 8, 11, ...
        if (i % 3) == 2:
            q_num = (i // 3) % 4 + 1  # 1..4 cycling
            key = f"{q_num}_trimestre"
            out.append(float(fatturato_del_trimestre.get(key)) if key in fatturato_del_trimestre else None)
        else:
            out.append(None)
    return out

def compute_pct_consuntivo_vs_prog_trimestrale(consuntivo_q, prog_trimestrale):
    """
    Percentage only on quarter ends, None elsewhere.
    """
    out = []
    for c, p in zip(consuntivo_q, prog_trimestrale):
        if c is None or not p:         # not a quarter end or p = 0/None
            out.append(None)
        else:
            out.append((float(c) / float(p)) * 100.0)
    return out

def compute_perc_ragg_fatturato_trimestrale(param_rows):
    """
    Returns a 12-length list: value only on quarter-end months,
    taken from 'perc_premio_trimestrale' in your param rows.
    """
    out = []
    for i, r in enumerate(param_rows):
        out.append(r.get("perc_premio_trimestrale") if (i % 3) == 2 else None)
    return out

def compute_premio_ragg_budget_trimestrale(consuntivo_q, prog_trimestrale, perc_ragg_tri):
    """
    consuntivo_q: quarter-to-date Venduto REALE (value only on Mar/Jun/Sep/Dec; None elsewhere)
    prog_trimestrale: budget quarter total (value only on Mar/Jun/Sep/Dec; None elsewhere)
    perc_ragg_tri: quarter % (value only on Mar/Jun/Sep/Dec; None elsewhere)
    """
    out = []
    for i, (c, p, perc) in enumerate(zip(consuntivo_q, prog_trimestrale, perc_ragg_tri)):
        if (i % 3) != 2:
            out.append(None)                # not a quarter end
            continue
        if c is None or p is None or perc is None:
            out.append(0.0)                 # quarter end but missing data -> 0
            continue
        out.append(c * perc if c >= p else 0.0)
    return out

def compute_premio_ragg_budget_trimestrale(obiettivi, venduto_reale, param_rows):
    """
    For EVERY month:
      IF (QTD consuntivo venduto) >= (quarter budget) THEN QTD * perc_ragg_trimestrale ELSE 0
    - QTD resets at each quarter end.
    - perc_ragg_trimestrale is taken from `perc_premio_trimestrale` on the quarter-end row and
      applied to all 3 months in that quarter.
    """
    # 1) Quarter % spread to all 3 months
    perc_spread = [0.0] * 12
    for q in range(4):
        end = q * 3 + 2  # quarter end index
        row = param_rows[end]
        perc = (row.get("perc_premio_trimestrale")
                if isinstance(row, dict)
                else getattr(row, "perc_premio_trimestrale", 0.0))
        perc_spread[q*3 : q*3 + 3] = [float(perc or 0.0)] * 3

    # 2) Quarter budget repeated across its 3 months
    quarter_budget = []
    for i in range(12):
        start = (i // 3) * 3
        quarter_budget.append(sum(float(x or 0) for x in obiettivi[start:start+3]))

    # 3) Quarter-to-date venduto for each month (reset each quarter)
    venduto_qtd, acc = [], 0.0
    for i, v in enumerate(venduto_reale):
        acc += float(v or 0.0)
        venduto_qtd.append(acc)
        if (i % 3) == 2:
            acc = 0.0

    # 4) Apply your formula per month
    return [(v * p) if (p and v >= b) else 0.0
            for v, b, p in zip(venduto_qtd, quarter_budget, perc_spread)]

def _quarter_progressivo(obiettivi, quarter_idx: int) -> float:
    """Sum of obiettivi for the quarter (equals progressivo trimestrale at Mar/Jun/Sep/Dec)."""
    start = TRIM_STARTS[quarter_idx]
    return float(obiettivi[start] or 0) + float(obiettivi[start+1] or 0) + float(obiettivi[start+2] or 0)

def compute_valori_trimestre(obiettivi, quarter_idx: int):
    """
    Produce a 12-length array for one quarter:
      valori_{quarter} [month] = (quarter progressivo) * weight
    applied over a 7-month window starting at the quarter's first month.
    Wraps around year end for Q4 (Oct..Dec, then Jan..Apr).
    """
    q_prog = _quarter_progressivo(obiettivi, quarter_idx)
    vals = [0.0] * 12
    start = TRIM_STARTS[quarter_idx]
    for k, w in enumerate(TRIM_WEIGHTS):
        i = (start + k) % 12
        vals[i] = q_prog * w
    return vals

def compute_valori_all_trimestri(obiettivi):
    """Returns 4 arrays: valori_1, valori_2, valori_3, valori_4."""
    return (
        compute_valori_trimestre(obiettivi, 0),  # Q1 uses March progressivo
        compute_valori_trimestre(obiettivi, 1),  # Q2 uses June progressivo
        compute_valori_trimestre(obiettivi, 2),  # Q3 uses September progressivo
        compute_valori_trimestre(obiettivi, 3),  # Q4 uses December progressivo
    )

def compute_perc_trim_arrays(perc_al_100, calcolo_percentuale_venduto):
    """
    Build 4 arrays:
      perc_trim_1 = Q * H[Mar], perc_trim_2 = Q * H[Jun],
      perc_trim_3 = Q * H[Sep], perc_trim_4 = Q * H[Dec].

    Notes:
    - We auto-normalize H values: if they look like 0–1 keep as-is, if 0–100 -> divide by 100.
    - Quarter-end month indices (0-based): Mar=2, Jun=5, Sep=8, Dec=11.
    """
    def nz(x):  # none→0 float
        return 0.0 if x is None else float(x)

    def normalize_h(x):
        x = nz(x)
        # If it's percentage like 83 (meaning 83%), scale to 0.83
        return x / 100.0 if x > 1 else x

    # Pick H at quarter ends
    h_mar = normalize_h(calcolo_percentuale_venduto[2])   # H5
    h_jun = normalize_h(calcolo_percentuale_venduto[5])   # H8
    h_sep = normalize_h(calcolo_percentuale_venduto[8])   # H11
    h_dec = normalize_h(calcolo_percentuale_venduto[11])  # H14

    p1 = [nz(q) * h_mar for q in perc_al_100]
    p2 = [nz(q) * h_jun for q in perc_al_100]
    p3 = [nz(q) * h_sep for q in perc_al_100]
    p4 = [nz(q) * h_dec for q in perc_al_100]
    return p1, p2, p3, p4

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

def calcola_percentuale_premio(margine, soglie_premi):
    """
    Calcola la percentuale_premio in base al margine e alle soglie.
    soglie_premi deve essere una lista di tuple (soglia, premio), ordinata in modo decrescente.
    """
    for soglia, premio in soglie_premi:
        if margine > soglia:
            return premio

    # fallback → ultimo premio (come R16 in Excel)
    if soglie_premi:
        return soglie_premi[-1][1]
    return None

def create_ordiniPremi_obj(vendite, parametri, user_id):
    
    # estrai coppie (limite, premio) ordinate per valore limite decrescente
    soglie_premi = sorted(
        [(p["valore_limite_perc"], p.get("premio_ragg_budget_annuale")) 
        for p in parametri if p["valore_limite_perc"] is not None],
        key=lambda x: x[0],
        reverse=True
    )


    result = []
    for v in vendite:
            data = parse_date(v["data"])
            venduto_a = v["subtotale"]
            costo_totale = v["costo_unitario"] * v["quantita"]
            margine = venduto_a - costo_totale
            percentuale_ricarico = (margine / costo_totale * 100) if costo_totale else None
            percentuale_premio = calcola_percentuale_premio(margine, soglie_premi)
            valore_premio_lordo = margine * percentuale_premio if percentuale_premio else None

            obj = {
                "user_id": user_id,
                "ordine_numero": v["ordine"],
                "cliente": v["cliente"],
                "prodotto": v["prodotto"],
                "mese": data.strftime("%d/%m/%y"),
                "venduto_a": venduto_a,
                "costo_totale_acquisto": costo_totale,
                "margine": margine,
                "percentuale_ricarico": percentuale_ricarico,
                "percentuale_premio": percentuale_premio,
                "valore_premio_lordo": valore_premio_lordo

            }
            result.append(obj)
            
            
    return result

def delete_replace_ordini_premi(session, user_id: str, rows: List[Dict]) -> int:
    """
    Cancella le righe esistenti in OrdiniPremi per lo user_id e inserisce le nuove.
    Ritorna il numero di righe inserite.
    """
    try:
        # 1) Cancella righe esistenti per questo user
        session.exec(delete(OrdiniPremi).where(OrdiniPremi.user_id == user_id))

        # 2) Inserisci nuove righe
        objs = [OrdiniPremi(user_id=user_id, **{k: v for k, v in row.items() if k != "user_id"}) for row in rows]
        session.add_all(objs)

        # 3) Commit
        session.commit()

        return len(objs)

    except Exception:
        session.rollback()
        raise



def replace_or_insert_parametriDaInserire(
    session: Session,
    user_id: str,
    rows: Optional[Iterable[Dict]] = None,
    *,
    treat_empty_list_as_template: bool = True,
)->int:
    """
    If `rows` is provided:
      - Expect 12 rows covering all months (same shape as TEMPLATE_ROWS).
      - Replace all existing rows for this user atomically.
    If `rows` is None or empty:
      - Seed from TEMPLATE_ROWS.
    """
    uid = str(user_id)

    # Decide source data
    if rows is None or (treat_empty_list_as_template and rows == []):
        source = TEMPLATE_ROWS
    else:
        incoming = [dict(r) for r in rows]  
        for r in incoming:
            r["mese"] = r["mese"].strip().lower()
        months = [r["mese"] for r in incoming]
        if len(incoming) != 12 or len(set(months)) != 12 or set(months) != MONTHS:
            raise HTTPException(
                status_code=422,
                detail="Payload must contain exactly one row for each month (gennaio..dicembre).",
            )
        source = incoming

    # Replace atomically: delete then insert
    try:
        session.exec(delete(ParametriDaInserire).where(ParametriDaInserire.user_id == uid))
        for r in source:
            session.add(ParametriDaInserire(
                user_id=uid,
                mese=r["mese"],
                obiettivo_mensile=r["obiettivo_mensile"],
                perc_premio_trimestrale=r.get("perc_premio_trimestrale"),
                perc_premio_annuale=r.get("perc_premio_annuale"),
                valore_limite=r.get("valore_limite"),
                perc_100_budget=r.get("perc_100_budget"),
            ))
        session.commit()
    except Exception:
        session.rollback()
        raise

    return len(source)

def replace_or_insert_budget_venduto_calcoli(session: Session, user_id: str, rows: List[Dict]) -> None:
    
    try:
        # 1) Delete old rows for the user
        session.exec(delete(BudgetVendutoCalcoli).where(BudgetVendutoCalcoli.user_id == user_id))

        # 2) Insert new rows
        session.add_all([BudgetVendutoCalcoli(**row) for row in rows])
        session.commit()
        return len(rows)
    except Exception:
        session.rollback()
        raise

def replace_or_insert_calcoli(parametriDaInserire, session: Session, user_id: str, fatturato_del_trimestre):
    """
    Calculate and save the parametri for the given user_id.
    This function should be called after replace_or_seed_parametri_for_user_core.
    """
    #print('parametriDaInserire', parametriDaInserire)
    
    # Force Gen→Dic order
    ordered = order_rows_by_month([dict(r) for r in parametriDaInserire])

    # Columns calculation
    obiettivi = [row["obiettivo_mensile"] for row in ordered]
    prog_mensili = compute_progressivi_mensili(obiettivi)
    prog_trimestrali = compute_progressivi_trimestrali(obiettivi) 
    venduto_reale = compute_venduto_reale(session, year=None)
    consuntivo_venduto = compute_consuntivo_venduto_trimestrale(venduto_reale, fatturato_del_trimestre)
    perc_rispetto_budget = compute_pct_consuntivo_vs_prog_trimestrale(consuntivo_venduto, prog_trimestrali)
    perc_ragg_fatturato_trimestrale = compute_perc_ragg_fatturato_trimestrale(parametriDaInserire)
    premio_ragg_budget_trimestrale = compute_premio_ragg_budget_trimestrale(obiettivi, venduto_reale, parametriDaInserire)
    valori1, valori2, valori3, valori4 = compute_valori_all_trimestri(obiettivi)
    perc_al_100 = [row["perc_100_budget"] for row in parametriDaInserire]
    perc_trim_1_arr, perc_trim_2_arr, perc_trim_3_arr, perc_trim_4_arr = compute_perc_trim_arrays(perc_al_100, perc_rispetto_budget)
    
    res = []
    totale_obiettivo_mensile = 0 
    totale_obiettivo_trimestrale = 0
    totale_venduto_reale = 0
    totale_consuntivo_venduto = 0
    totale_ragg_budget_trimestrale = 0
    for i, month in enumerate(MONTHS_LIST):
        
        ### Calc totali ###
        # obiettivo_mensile totale
        ob_mens = obiettivi[i] if obiettivi[i] is not None else 0
        totale_obiettivo_mensile += ob_mens
        
        # obiettivo_trimestrale totale
        trim_val = prog_trimestrali[i] if prog_trimestrali[i] is not None else 0
        totale_obiettivo_trimestrale += trim_val
        
        #Venduto reale totale
        venduto_val = venduto_reale[i] if venduto_reale[i] is not None else 0
        totale_venduto_reale += venduto_val
        
        #Totale consuntivo venduto
        consuntivo_val = consuntivo_venduto[i] if consuntivo_venduto[i] is not None else 0
        totale_consuntivo_venduto += consuntivo_val
        
        # TOtale ragg budget trimestrale
        ragg_budget_val = premio_ragg_budget_trimestrale[i] if premio_ragg_budget_trimestrale[i] is not None else 0
        totale_ragg_budget_trimestrale += ragg_budget_val

        
        res.append({
            "user_id": user_id,
            "mese": month,                              
            "obiettivo_mensile": obiettivi[i],
            "progressivo_mensile": prog_mensili[i],
            "progressivo_trimestrale": prog_trimestrali[i],        
            "venduto_reale": venduto_reale[i],
            "consuntivo_venduto": consuntivo_venduto[i], 
            "perc_rispetto_budget": perc_rispetto_budget[i],
            "calcolo_percentuale_venduto": perc_rispetto_budget[i],
            "valore_premio": None,
            "perc_ragg_fatturato_trimestrale": perc_ragg_fatturato_trimestrale[i],
            "premio_ragg_budget_trimestrale": premio_ragg_budget_trimestrale[i],
            "premio_ragg_budget_annuale": parametriDaInserire[i]["perc_premio_annuale"],
            "valori_1_trim": valori1[i],  
            "valori_2_trim": valori2[i],  
            "valori_3_trim": valori3[i],  
            "valori_4_trim": valori4[i],  
            "perc_al_100": perc_al_100[i],
            "perc_trim_1": perc_trim_1_arr[i],
            "perc_trim_2": perc_trim_2_arr[i],
            "perc_trim_3": perc_trim_3_arr[i],
            "perc_trim_4": perc_trim_4_arr[i],
            "valore_limite_perc": parametriDaInserire[i]["valore_limite"],
            
        })
        
    # Add extra "totali" row after the loop
    res.append({
        "user_id": user_id,
        "mese": "totali",
        "obiettivo_mensile": totale_obiettivo_mensile,
        "progressivo_mensile": None,
        "progressivo_trimestrale": totale_obiettivo_trimestrale,
        "venduto_reale": totale_venduto_reale,
        "consuntivo_venduto": totale_consuntivo_venduto,
        "valore_premio": None,
        "premio_ragg_budget_trimestrale": totale_ragg_budget_trimestrale,
        "premio_ragg_budget_annuale": parametriDaInserire[0]["perc_premio_annuale"]
    })
    # print("res")
    # pprint(res)
    
    
    result = replace_or_insert_budget_venduto_calcoli(session, user_id, res)
    return result, res

def replace_or_insert_conteggi_commessa(session: Session, user_id: str, parametri):
    
    # Get vendite for the user
    vendite = session.exec(select(VenditeImax).where(VenditeImax.venditore == "Diana Joita")).scalars().all() # to change!
    vendite = [v.dict() for v in vendite]
    #pprint(parametri)
    #pprint(vendite)
    
    # Create ordiniPremi object 
    res = create_ordiniPremi_obj(vendite, parametri, user_id)
    # print("res:")
    # pprint(res) 
    
    # delete_replace_ordini_premi
    result = delete_replace_ordini_premi(session, user_id, res)
   
    return result

def send_email(receiver_email, filename, pdf_bytes=None):
    print("Sending email...")
    
    sender_email = "lastiada1@gmail.com"
    password = "opqexobtkprukiyi"   # Use environment variable in production!

    subject = "Test Email"
    body = "Hello, this is a test email sent from Python!"

    try:
        
        # Create email message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
        
        # ✅ attach PDF if provided
        if pdf_bytes:
            pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_part.add_header("Content-Disposition", "attachment", filename=filename)
            message.attach(pdf_part)

        # Connect to SMTP and send
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)

        return {"status_code": 200, "result": f"Email sent to {receiver_email}"}


    except smtplib.SMTPAuthenticationError:
        return {"status_code": 401, "error": "Authentication failed. Check SMTP_USER/SMTP_PASS (app password)."}
    except smtplib.SMTPConnectError as e:
        # Connection-level SMTP failure
        err = getattr(e, "smtp_error", b"")
        err = err.decode(errors="ignore") if isinstance(err, bytes) else str(err or e)
        return {"status_code": 503, "error": f"SMTP connect error: {err}"}
    except smtplib.SMTPResponseException as e:
        # Generic 4xx/5xx SMTP response
        code = getattr(e, "smtp_code", 500)
        err = getattr(e, "smtp_error", b"")
        err = err.decode(errors="ignore") if isinstance(err, bytes) else str(err or e)
        return {"status_code": code, "error": err}
    except Exception as e:
        return {"status_code": 500, "error": str(e)}

def send_email_with_retry(
    to_email: str,
    pdf_bytes: bytes,
    filename: str,
    *,
    max_attempts: int = 3,
    backoff_seconds: float = 2.0,
):
    """Blocking send with simple retry/backoff. Safe to run in BackgroundTasks."""
    attempt = 0
    last_err: Optional[Exception] = None
    while attempt < max_attempts:
        attempt += 1
        try:
            logger.info("Email attempt %s to %s", attempt, to_email)
            send_email(to_email, filename, pdf_bytes)
            return
        except Exception as e:
            last_err = e
            logger.warning("Email attempt %s failed: %s", attempt, e)
            time.sleep(backoff_seconds * (2 ** (attempt - 1)))

    logger.error("Email failed after %s attempts: %s", max_attempts, last_err)




def build_pdf_report_tecnico(data):
    
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
        pdf.set_fill_color(0, 128, 85)
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
    add_pdf_header(pdf, title="Report Intervento Tecnico")
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
        pdf.set_fill_color(0, 128, 0)
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

        pdf.set_fill_color(0, 128, 0)
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
        #checkbox_cell_right(pdf, 190, 8, item.cliente or "", checked=bool(item.switch1))
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

    def ensure_block(pdf: FPDF, block_h: float):
        """If the next block wouldn't fit, start a new page first."""
        if pdf.get_y() + block_h > pdf.page_break_trigger:
            pdf.add_page()        # (optionally call your add_pdf_header(...) here)

    def write_cell(w, h, text='', fill=False, align='L', bold=False):
        family = pdf.font_family or "Arial"
        size = pdf.font_size_pt or 12
        style = "B" if bold else ""
        pdf.set_font(family, style=style, size=size)
        pdf.cell(w, h, text or "", border=1, fill=fill, align=align)

    def green_rule(height: float = 3, *, color=(127, 255, 212), x_start: float | None = None,
                border_rgb=(0, 0, 0), border_width: float = 0.2):
        """
        Draw a full-width mint bar and continue the table's vertical borders
        at the left/right extremes of the bar.
        - color: fill RGB for the bar
        - x_start: start X (defaults to left margin); bar goes to right margin
        - border_rgb: color for the vertical edge lines
        - border_width: thickness of the vertical edge lines
        """
        if x_start is None:
            x_start = pdf.l_margin

        y = pdf.get_y()
        w = pdf.w - x_start - pdf.r_margin

        # bar
        r, g, b = color
        pdf.set_fill_color(r, g, b)
        pdf.rect(x_start, y, w, height, style="F")

        # vertical continuations at both ends
        pdf.set_draw_color(*border_rgb)
        pdf.set_line_width(border_width)
        pdf.line(x_start,       y, x_start,       y + height)  # left edge
        pdf.line(x_start + w,   y, x_start + w,   y + height)  # right edge

        # move cursor below and restore defaults
        pdf.ln(height)
        pdf.set_line_width(0.2)          # or whatever you use elsewhere
        pdf.set_fill_color(255, 255, 0)  # your default cell fill

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
                ("FOTOGRAFIE PER TUTELA DANNI PRIMA DI INIZIARE I LAVORI",      gvb("fotografie_danni_prima_di_iniziare"), (255, 0, 0)),
                ("FOTOGRAFIE LAVORO ULTIMATO",                                  gvb("fotografie_lavoro_ultimato"),          (255, 255, 255)),
                ("GIRO CON IL CLIENTE, PRODOTTO PER PRODOTTO SU CORRETTA FUNZ", gvb("lavoro_non_completato_causa_nostra"),  (255, 255, 255)),
                ("DDT e Documenti FIRMATI",                                     gvb("lavoro_non_completato_causa_cliente"), (255, 255, 255)),
                ("DIFETTI SPIEGATI AL CLIENTE DOVUTI AD ALTRE CAUSE",           gvb("danni_vedi_rapporto_posa"),            (255, 255, 255)),
                ("LAVORO NON COMPLETATO CAUSA NOSTRA",                          gvb("lavoro_non_completato_causa_nostra"),  (255, 255, 255)),
                ("LAVORO NON COMPLETATO CAUSA CLIENTE",                         gvb("lavoro_non_completato_causa_cliente"), (255, 255, 255)),
                ("SONO STATI ARRECATI DANNI VEDI RAPPORTO POSA CLIENTE",        gvb("danni_vedi_rapporto_posa"),            (255, 255, 255)),
            ],
        }
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
        # (
        #     "Informazioni",
        #     [
        #         ("Già Cliente", gvb("informazioni"), 60),
        #         ("E' STATO ESEGUITO IL SOPRALLUOGO", gvb("informazioni"), 82, 10),  # font_size override
        #     ],
        # ),
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

    # Tempo prev. ore / Intervento pianificato Data & Ora
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
    
    # stato lavoro, tipo riparazione
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

    # Lavori Eseguiti
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(190, 8, "Lavori Eseguiti", bold=True, fill=True, align='C')
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
    green_rule(height=2)

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
    SIG_H = 42 
    ensure_block(pdf, SIG_H)
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
    
    # Firma del cliente
    SIG_H = 42 
    ensure_block(pdf, SIG_H)
    signature_block(
        pdf,
        text=(
            "FIRMA DEL CLIENTE  Il cliente o chi per esso ha verificato con il tecnico,"
            "se non specificato sopra e nelle note, che tutte le superfici di quanto"
            "consegnato non presentano danni o difetti visibili e dichiara che non sono"
            "stati causati danni all' interno dell' abitazione."
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




def build_pdf_report_posa_commessa(data):
    
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
        pdf.set_fill_color(110, 207, 246)    # your mint color
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
        pdf.set_fill_color(110, 207, 246)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 18)
        pdf.cell(right_w, h, title, border=0, fill=True, align="C")

        # move below header
        pdf.ln(h + 2)

        # restore defaults so later table borders don’t inherit colors
        pdf.set_draw_color(0, 0, 0)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(255, 255, 0)

    t = getattr(data, "posa_commessa", None) or type("Empty", (), {})()
    pdf = FPDF()
    pdf.add_page()
    add_pdf_header(pdf, title="Report Posa In Opera")
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

    def ensure_block(pdf: FPDF, block_h: float):
        """If the next block wouldn't fit, start a new page first."""
        if pdf.get_y() + block_h > pdf.page_break_trigger:
            pdf.add_page()        # (optionally call your add_pdf_header(...) here)

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
        pdf.set_fill_color(0, 128, 0)
        pdf.rect(x, y, w, height, style='F')
        pdf.ln(height)
        # restore your default fill color (yellow for cells, per your code)
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


    checkbox_groups = [
        (
            "STATO LAVORO",
            [
                ("Completato", gvb("cliente_stato_posa"), 60),
                ("Da Completare", not gvb("cliente_stato_posa"), 82),
            ],
        ),
    ]    

    sections = [

        # --- Second block: TECNICO ---
        {
            "header": "REPORT FOTOGRAFICO",
            "rows": [
                ("FOTOGRAFIE PER TUTELA DANNI PRIMA DI INIZIARE I LAVORI",   gvb("foto_danni_inizio"),               (230, 230, 230)),
                ("SONO STATI ARRECATI DANNI VEDI RAPPORTO POSA CLIENTE",     gvb("danni_posa_cliente"),            (230, 230, 230)),
                ("FOTOGRAFIE GIUNTI DI POSA PER OGNI INFISSO",               gvb("foto_giunti_posa"),          (230, 230, 230)),
                ("FOTOGRAFIE DEL LAVORO ULTIMATO",                           gvb("foto_lavoro_ultimato"),      (230, 230, 230)),
                ("LAVORO NON COMPLETATO CAUSA NOSTRA",                       gvb("lavoro_non_completato_nostro"),        (230, 230, 230)),
                ("LAVORO NON COMPLETATO CAUSA CLIENTE",                      gvb("lavoro_non_completato_cliente"),          (230, 230, 230)),
            ],
        },
        {
            "header": "ERRORI",
            "rows": [
                ("ERRORE PROGETTAZIONE",                         gvb("errore_progettazione"),               (230, 230, 230)),
                ("ERRORE SCELTA PROFILI E ACCESSORI",            gvb("errore_scelta_profili_accessori"),            (230, 230, 230)),
                ("GIRO CON IL CLIENTE SU CORRETTA CONFORMITA",   gvb("errore_misure_nel_rilievo"),          (230, 230, 230)),
                ("ERRORE MISURE NEL RILIEVO",                    gvb("errore_misure_nel_rilievo"),      (230, 230, 230)),
                ("DIFFICOLTÀ TRASPORTO NON SEGNALATE",           gvb("difficolta_trasporto_non_segnalate"),        (230, 230, 230)),
                ("ERRORE CALCOLO TEMPO A DISPOSIZIONE",          gvb("errore_calcolo_tempo_disp"),          (230, 230, 230)),
            ],
        },
        {
            "header": "POSATORI",
            "rows": [
                ("VETRO ROTTO DURANTE LA POSA",                    gvb("vetro_rotto_durante_la_posa"),           (230, 230, 230)),
                ("MATERIALI-PROFILI DANNEGGIATI DURANTE LA POSA",  gvb("materiali_danneggiati_durante_posa"),            (230, 230, 230)),
                ("MANCANZA ATTREZZATURE NON CARICATE",             gvb("danneggiamento_casa_cliente"), (230, 230, 230)),
                ("DANNEGGIAMENTO CASA DEL CLIENTE",                gvb("consegna_documenti"),      (230, 230, 230)),
            ],
        },
        {
            "header": "UFFICIO",
            "rows": [
                ("ERRORE MISURE/MATERIALE/COLORE NELL' ORDINE",   gvb("errore_misure_ordine"),               (230, 230, 230)),
                ("ERRORE CALCOLO TEMPO A DISPOSIZIONE",           gvb("errore_calcolo_tempo"),            (230, 230, 230)),
            ],
        },
        {
            "header": "COMMERCIALE",
            "rows": [
                ("PULIZIA DEI VETRI E/O FINESTRE",                gvb("errore_materiale_contratto"),               (230, 230, 230)),
                ("GIRO CON IL CLIENTE SU CORRETTA FUNZIONALITA",  gvb("errore_scelta_profili_accessori_comm"),            (230, 230, 230)),
            ],
        },
        {
            "header": "MAGAZZINO",
            "rows": [
                ("VETRO ROTTO/DIFETTOSO DA SOSTITUIRE",      gvb("vetro_rotto_difettoso"),               (230, 230, 230)),
                ("MATERIALE MANCANTE NON CARICATO",          gvb("materiale_mancante_non_caricato"),     (230, 230, 230)),
                ("MATERIALI DI POSA MANCANTI NON CARICATI",  gvb("materiali_posa_mancanti_noncaricati"),     (230, 230, 230)),
            ],
        },
        {
            "header": "FORNITORE",
            "rows": [
                ("MATERIALE DIFETTOSO CAUSA FORNITORE",                 gvb("materiale_difettoso_causa_fornitore"),               (230, 230, 230)),
                ("ERRORE TIPOLOGIA MATERIALE CAUSA FORNITORE",          gvb("errore_tipologia_materiale_causa_fornitore"),     (230, 230, 230)),
                ("VETRO ROTTO/DIFETTOSO DA SOSTITUIRE CAUSA FORNITORE", gvb("vetro_rotto_diffettoso_causa_fornitore"),     (230, 230, 230)),
                ("MATERIALE MANCANTE CAUSA FORNITORE",                  gvb("materiale_mancante_causa_fornitore"),     (230, 230, 230)),
            ],
        },
    ]
    
    # Cliente, ordine, squadra postatori, data
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(30, 8, "Cliente°", fill=True, bold=True)
    write_cell(65, 8, gv("cliente_cliente"))
    write_cell(30, 8, "Ordine", fill=True, bold=True)
    write_cell(65, 8, gv("cliente_ordine"))
    pdf.ln()
    
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(40, 8, "Squadra Posatori", fill=True, bold=True)
    write_cell(55, 8, gv("cliente_squadra_posatori"))
    write_cell(30, 8, "Data", fill=True, bold=True)
    write_cell(65, 8, gv("cliente_data"))
    pdf.ln()
    green_rule(height=2)  
    
    # stato lavoro,
    for title, checkboxes in checkbox_groups:
        pdf.set_fill_color(110, 207, 246)
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
        
    # resta da fare
    ensure_space(pdf, 8)
    note_box(
        pdf,
        title="Resta da fare (descrivere brevemente cosa manca e perché):",
        body=gv("cliente_resta_da_fare"),
        height=55,       
        end_gap=5       
    )
    green_rule(height=2)
    
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
    
    
    #  Materiale rientrato 
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(100, 8, "Materiale rientrato", bold=True, fill=True)
    write_cell(30, 8, "Ordinare", bold=True, fill=True, align="C")
    write_cell(30, 8, "Magaz.", bold=True, fill=True, align="C")
    write_cell(30, 8, "Verificare", bold=True, fill=True, align="C")
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
    green_rule(height=2)
    
    # ---------- Ore previste ----------
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(60, 8, "Ore previste finitura", fill=True, bold=True)
    write_cell(40, 8, gv("ore_previste_finitura"))
    write_cell(50, 8, "Per quanti posatori", fill=True, bold=True)
    write_cell(40, 8, gv("per_numero_posatori"))
    pdf.ln()
    green_rule(height=2)
    
    # altri campi
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

def build_pdf_report_posa_cliente(data):
    
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
        pdf.set_fill_color(110, 207, 246)    # your mint color
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
        pdf.set_fill_color(110, 207, 246)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Arial", "B", 18)
        pdf.cell(right_w, h, title, border=0, fill=True, align="C")

        # move below header
        pdf.ln(h + 2)

        # restore defaults so later table borders don’t inherit colors
        pdf.set_draw_color(0, 0, 0)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(255, 255, 0)

    t = getattr(data, "posa_cliente", None) or type("Empty", (), {})()
    pdf = FPDF()
    pdf.add_page()
    add_pdf_header(pdf, title="Report Posa Cliente")
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

    def ensure_block(pdf: FPDF, block_h: float):
        """If the next block wouldn't fit, start a new page first."""
        if pdf.get_y() + block_h > pdf.page_break_trigger:
            pdf.add_page()        # (optionally call your add_pdf_header(...) here)

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
        pdf.set_fill_color(0, 128, 0)
        pdf.rect(x, y, w, height, style='F')
        pdf.ln(height)
        # restore your default fill color (yellow for cells, per your code)
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

    
    checkbox_groups = [
        (
            "STATO POSA",
            [
                ("Completato", gvb("stato_posa"), 60),
                ("Da Completare", not gvb("stato_posa"), 82),
            ],
        ),
    ]    

    sections = [

        # --- Second block: TECNICO ---
        {
            "header": "ALTRI CAMPI",
            "rows": [
                ("PULIZIA DEI VETRI E/O FINESTRE",                                            gvb("pulizia_vetri"),               (230, 230, 230)),
                ("GIRO CON IL CLIENTE SU CORRETTA FUNZIONALITA",                              gvb("giro_cliente"),            (230, 230, 230)),
                ("GIRO CON IL CLIENTE SU CORRETTA CONFORMITA",                                gvb("giro_cliente_conformita"),          (230, 230, 230)),
                ("CONSEGNA DEI DOCUMENTI ES. ENEA",                                           gvb("consegna_documenti"),      (230, 230, 230)),
                ("CONSEGNA LIBRETTO USO E MANUTENZIONE",                                      gvb("consegna_libretto"),        (230, 230, 230)),
                ("DDT E VERBALE DI COLLAUDO FIRMATI",                                         gvb("ddt_verbal_firmati"),          (230, 230, 230)),
                ("DIFETTI PRESENTI SUI VETRI",                                                gvb("difetti_vetri"),             (230, 230, 230)),
                ("DIFETTI PRESENTI SUI PROFILI",                                              gvb("difetti_profili"),        (230, 230, 230)),
                ("DIFETTI SPIEGATI AL CLIENTE DOVUTI ALLA MURATURA NON DI NOSTRA COMPETENZA", gvb("difetti_muratura"),      (230, 230, 230)),
                ("SONO STATI ARRECATI DANNI SCRIVERE LE SPECIFICHE NELLE NOTE",               gvb("danni_arrecati"),        (230, 230, 230)),
            ],
        },
    ]
    
    # Cliente, ordine, squadra postatori, data
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(30, 8, "Cliente°", fill=True, bold=True)
    write_cell(65, 8, gv("cliente"))
    write_cell(30, 8, "Ordine", fill=True, bold=True)
    write_cell(65, 8, gv("ordine"))
    pdf.ln()
    
    pdf.set_fill_color(230, 230, 230)
    ensure_space(pdf, 8)
    write_cell(40, 8, "Squadra Posatori", fill=True, bold=True)
    write_cell(55, 8, gv("squadra_posatori"))
    write_cell(30, 8, "Data", fill=True, bold=True)
    write_cell(65, 8, gv("data"))
    pdf.ln()
    green_rule(height=2)  
    
    # stato lavoro,
    for title, checkboxes in checkbox_groups:
        pdf.set_fill_color(110, 207, 246)
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
        
    # resta da fare
    ensure_space(pdf, 8)
    note_box(
        pdf,
        title="Resta da fare (descrivere brevemente cosa manca e perché):",
        body=gv("resta_da_fare"),
        height=55,       
        end_gap=5       
    )
    green_rule(height=2)
    
    
    # altri campi
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
    SIG_H = 42 
    ensure_block(pdf, SIG_H)
    signature_block(
        pdf,
        text=(
            "FIRMA DEL POSATORE  Il tecnico dichiara, sotto la propria responsabilità, "
            "che tutto quanto sopra indicato corrisponde al vero ed è consapevole e "
            "informato di eventuali sanzioni disciplinari o addebiti nel caso quanto "
            "dichiarato non corrisponda a verità."
        ),
        sig_data=gv("cellulare_cliente_posatore"),
    )
    
    # Firma del cliente
    SIG_H = 42 
    ensure_block(pdf, SIG_H)
    signature_block(
        pdf,
        text=(
            "FIRMA DEL CLIENTE  Il cliente o chi per esso ha verificato con il tecnico,"
            "se non specificato sopra e nelle note, che tutte le superfici di quanto"
            "consegnato non presentano danni o difetti visibili e dichiara che non sono"
            "stati causati danni all' interno dell' abitazione."
        ),
        sig_data=gv("cellulare_cliente_cliente"),
    )
    
    # ---------- Note ----------
    ensure_space(pdf, 8)
    note_box(
        pdf,
        title="NOTE descrivere eventuali difetti riscontrati o danni causati all'interno dell'abitazione:",
        body=gv("note_cliente"),
        height=55,       # your desired size
        end_gap=5       # leave ~12 pts before page bottom
    )
    
    
    content = pdf.output(dest='S')
    return content.encode('latin-1') if isinstance(content, str) else content