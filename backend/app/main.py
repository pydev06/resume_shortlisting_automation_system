import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from .api import jobs, resumes, evaluations, ai

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("resume_shortlisting")

app = FastAPI(
    title="Resume Shortlisting Automation API",
    description="Internal HR tool for managing jobs, resumes, and candidate evaluations",
    version="1.0.0"
)

# CORS middleware for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(resumes.router, prefix="/api/v1")
app.include_router(evaluations.router, prefix="/api/v1")
app.include_router(ai.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "Resume Shortlisting API"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "services": {
            "api": "up"
        }
    }


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """OAuth callback endpoint to handle authorization code"""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    scope = request.query_params.get("scope")

    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OAuth Authorization Complete</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .code {{ background: #f0f0f0; padding: 10px; border-radius: 5px; font-family: monospace; }}
        </style>
    </head>
    <body>
        <h1>OAuth Authorization Complete</h1>
        <p>Copy the full URL from your browser's address bar and paste it into the terminal where the server is running.</p>
        
        <div class="code">
            Full URL: {request.url}
        </div>
        
        <p><strong>Code:</strong> {code}</p>
        <p><strong>State:</strong> {state}</p>
        <p><strong>Scope:</strong> {scope}</p>
    </body>
    </html>
    """)
