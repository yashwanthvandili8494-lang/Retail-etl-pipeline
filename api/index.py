"""FastAPI application entrypoint for Vercel Serverless and Render Web Service."""

from pathlib import Path
import json
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Resolve paths
BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(
    title="Retail ETL Pipeline API",
    description="Live analytical API and dashboard for Retail Store Sales ETL assessment",
    version="1.0.0",
)

# Enable CORS for cross-origin frontend queries
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the interactive executive analytics dashboard."""
    html_file = BASE_DIR / "dashboard" / "index.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="Dashboard template not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.get("/health")
async def health_check():
    """Health check endpoint for Render / Vercel uptime monitoring."""
    return {
        "status": "healthy",
        "service": "Retail ETL Pipeline",
        "version": "1.0.0",
        "environment": "production",
    }


@app.get("/api/metrics")
async def get_metrics():
    """Return executive ETL metrics summary."""
    return {
        "source_rows": 25000,
        "staging_rows": 25000,
        "duplicate_rows": 345,
        "clean_rows": 24655,
        "fact_rows": 24655,
        "customers": 5000,
        "stores": 8,
        "products": 13,
        "reconciliation_errors": 555,
        "status": "SUCCESS",
    }


@app.get("/api/reconciliation")
async def get_reconciliation_errors():
    """Return financial reconciliation discrepancies (> INR 0.01 tolerance)."""
    csv_path = BASE_DIR / "output" / "reconciliation_errors.csv"
    if not csv_path.exists():
        return []
    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")


@app.get("/api/duplicates")
async def get_duplicate_records():
    """Return quarantined duplicate records."""
    csv_path = BASE_DIR / "output" / "duplicate_records.csv"
    if not csv_path.exists():
        return []
    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")


@app.get("/api/dq-report")
async def get_data_quality_report():
    """Return structured data quality audit evaluation."""
    csv_path = BASE_DIR / "output" / "data_quality_report.csv"
    if not csv_path.exists():
        return []
    df = pd.read_csv(csv_path)
    return df.to_dict(orient="records")


@app.get("/download/docx")
async def download_word_document():
    """Download the official Word (.docx) technical assessment report."""
    docx_path = BASE_DIR / "Retail_ETL_Pipeline_Technical_Assessment.docx"
    if not docx_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        path=str(docx_path),
        filename="Retail_ETL_Pipeline_Technical_Assessment.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api.index:app", host="0.0.0.0", port=port, reload=False)
