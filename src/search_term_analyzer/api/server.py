from typing import Optional, Dict, Any
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import structlog
from datetime import datetime, timezone
from prometheus_client import make_asgi_app

from .endpoints import router as api_router
from ..core.config import PipelineConfig
from ..core.exceptions import SearchTermAnalyzerError
from ..utils.monitoring import MetricsCollector
from ..core.constants import (
    ALLOWED_ORIGINS,
    DEFAULT_LOG_FORMAT,
    HTTPStatus
)

logger = structlog.get_logger(__name__)

class SearchTermAnalyzerServer:
    """Main server class for Search Term Analyzer"""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.metrics_collector = MetricsCollector()
        self._initialize_server()

    def _initialize_server(self) -> None:
        """Initialize FastAPI server and components"""
        self.app = FastAPI(
            title="Search Term Analyzer API",
            description="API for analyzing and optimizing search terms",
            version="1.0.0",
            docs_url="/api/docs",
            redoc_url="/api/redoc",
            openapi_url="/api/openapi.json"
        )

        self._setup_middleware()
        self._setup_routes()
        self._setup_exception_handlers()
        self._setup_events()

    def _setup_middleware(self) -> None:
        """Configure middleware stack"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=list(ALLOWED_ORIGINS),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Gzip compression
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Request ID middleware
        @self.app.middleware("http")
        async def add_request_id(request: Request, call_next):
            request_id = f"req_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
            request.state.request_id = request_id
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Logging middleware
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = datetime.now(timezone.utc)
            response = await call_next(request)
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            logger.info(
                "request_processed",
                request_id=getattr(request.state, "request_id", None),
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration=duration
            )
            return response

    def _setup_routes(self) -> None:
        """Configure API routes"""
        # Mount metrics endpoint
        metrics_app = make_asgi_app()
        self.app.mount("/metrics", metrics_app)

        # Include API router
        self.app.include_router(
            api_router,
            prefix="/api/v1",
            tags=["search_term_analyzer"]
        )

        # Health check endpoint
        @self.app.get("/health")
        async def health_check() -> Dict[str, Any]:
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0.0"
            }

    def _setup_exception_handlers(self) -> None:
        """Configure exception handlers"""
        @self.app.exception_handler(SearchTermAnalyzerError)
        async def analyzer_exception_handler(request: Request, exc: SearchTermAnalyzerError):
            return JSONResponse(
                status_code=HTTPStatus.BAD_REQUEST,
                content={
                    "error": str(exc),
                    "details": exc.details,
                    "request_id": getattr(request.state, "request_id", None),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.error(
                "unhandled_error",
                error=str(exc),
                request_id=getattr(request.state, "request_id", None)
            )
            return JSONResponse(
                status_code=HTTPStatus.INTERNAL_ERROR,
                content={
                    "error": "Internal server error",
                    "request_id": getattr(request.state, "request_id", None),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )

    def _setup_events(self) -> None:
        """Configure startup and shutdown events"""
        @self.app.on_event("startup")
        async def startup_event():
            logger.info("server_starting")
            self.metrics_collector.start()
            # Initialize other components as needed

        @self.app.on_event("shutdown")
        async def shutdown_event():
            logger.info("server_stopping")
            self.metrics_collector.stop()
            # Cleanup other components as needed

    async def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics"""
        return {
            "start_time": self.metrics_collector._start_time.isoformat(),
            "uptime": str(datetime.now(timezone.utc) - self.metrics_collector._start_time),
            "metrics": await self.metrics_collector.get_metrics_summary()
        }

def create_app(config: Optional[PipelineConfig] = None) -> FastAPI:
    """Create and configure FastAPI application"""
    if config is None:
        config = PipelineConfig.load("config.json")
    
    server = SearchTermAnalyzerServer(config)
    return server.app

def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    reload: bool = False,
    config: Optional[PipelineConfig] = None
) -> None:
    """Run the API server"""
    app = create_app(config)
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_config={
            "version": 1,
            "formatters": {
                "default": {
                    "fmt": DEFAULT_LOG_FORMAT,
                    "datefmt": "%Y-%m-%d %H:%M:%S"
                }
            }
        }
    )

if __name__ == "__main__":
    run_server()
    