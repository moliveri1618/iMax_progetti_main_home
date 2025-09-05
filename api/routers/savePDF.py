from fastapi import APIRouter
import sys
import os
import io
import os
from fastapi.responses import StreamingResponse
from typing import Optional
from fastapi import BackgroundTasks, status
from fastapi.responses import JSONResponse

if os.getenv("GITHUB_ACTIONS"):
    sys.path.append(os.path.dirname(__file__))
from routers.utils import send_email_with_retry, ReportData, ReportPostVendita, build_pdf_report_tecnico, build_pdf_report_cliente, build_pdf_report_posa_cliente, build_pdf_report_posa_commessa


router = APIRouter()


@router.post("/generate-report-lista-tickets")
async def generate_from_json(
    data: ReportData,
    background_tasks: BackgroundTasks,
    email:  Optional[str] = "mauro.oliveri16@gmail.com"
):
    
    try:
        # Generate PDF TECNICO & CLIENTE
        pdf_tecnico = build_pdf_report_tecnico(data)
        pdf_cliente = build_pdf_report_cliente(data)

        # SEND EMAIL
        background_tasks.add_task(send_email_with_retry, email, pdf_tecnico, "report_intervento_tecnico.pdf")
        background_tasks.add_task(send_email_with_retry, email, pdf_cliente, "report_intervento_cliente.pdf")

        return JSONResponse(
            {
                "ok": True,
                "message": "Reports generated successfully.",
            },
            status_code=status.HTTP_200_OK,
        )
        
        # # INSPECT PDF FILE
        # buffer = io.BytesIO(pdf_tecnico)
        # #buffer = io.BytesIO(pdf_cliente)
        # return StreamingResponse(buffer, media_type="application/pdf", headers={
        #     "Content-Disposition": "attachment; filename=posa_layout.pdf"
        # })

    except Exception as e:
        return JSONResponse(
            {
                "ok": False,
                "message": f"An error occurred while generating/sending reports: {str(e)}",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    


@router.post("/generate-report-post-vendita")
async def generate_reports(
    data: ReportPostVendita,
    background_tasks: BackgroundTasks,
    email:  Optional[str] = "mauro.oliveri16@gmail.com"
):
    
    try:
        # Generate PDF TECNICO & CLIENTE
        pdf_posa_commessa = build_pdf_report_posa_commessa(data)
        pdf_posa_cliente = build_pdf_report_posa_cliente(data)

        #SEND EMAIL
        background_tasks.add_task(send_email_with_retry, email, pdf_posa_commessa, "report_posa_commessa.pdf")
        background_tasks.add_task(send_email_with_retry, email, pdf_posa_cliente, "report_posa_cliente.pdf")

        return JSONResponse(
            {
                "ok": True,
                "message": "Reports generated successfully.",
            },
            status_code=status.HTTP_200_OK,
        )
        
        # # INSPECT PDF FILE
        # buffer = io.BytesIO(pdf_posa_commessa)
        # #buffer = io.BytesIO(pdf_posa_cliente)
        # return StreamingResponse(buffer, media_type="application/pdf", headers={
        #     "Content-Disposition": "attachment; filename=posa_layout.pdf"
        # })
    

    except Exception as e:
        return JSONResponse(
            {
                "ok": False,
                "message": f"An error occurred while generating/sending reports: {str(e)}",
            },
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )