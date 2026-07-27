import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from backend.config import settings
from backend.presentation.routes import api_bp
from backend.presentation import routes as api_routes
from backend.presentation.middleware import register_middlewares

from backend.infrastructure.firebase import FirestoreService
from backend.infrastructure.ai_pipeline import AIService
from backend.infrastructure.session import InMemorySessionManager
from backend.infrastructure.redis_cache import RedisCacheService
from backend.infrastructure.telemetry import setup_telemetry
from backend.infrastructure.logging import log_event

def create_app() -> Flask:
    # Set up paths to serve the frontend directly from Flask if requested
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))
    
    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    CORS(app)

    # 1. Initialize Infrastructure Services (Dependency Injection)
    db_service = FirestoreService()
    ai_service = AIService()
    session_manager = InMemorySessionManager()
    
    # Enable enterprise distributed caching with automated fallback
    redis_url = os.environ.get("REDIS_URL")
    cache_service = RedisCacheService(redis_url)

    # 2. Bind Services to Presentation Layer (Wired Up Dependency Container)
    api_routes.database_service = db_service
    api_routes.ai_service = ai_service
    api_routes.session_manager = session_manager
    api_routes.cache_service = cache_service

    # 3. Register Middlewares
    register_middlewares(app)

    # 4. Activate Observability Tracing
    setup_telemetry(app)

    # 5. Register API Blueprints
    app.register_blueprint(api_bp, url_prefix="/api/v1")

    # 6. Serve Frontend assets directly for simple local development
    @app.route("/")
    def serve_index():
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/<path:path>")
    def serve_static(path):
        if os.path.exists(os.path.join(frontend_dir, path)):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, "index.html")

    @app.after_request
    def add_header(response):
        # Disable caching on assets to prevent browser-side cache locking
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response

    log_event("app_bootstrap_success", {"port": settings.PORT, "debug": settings.DEBUG})
    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=settings.PORT, debug=settings.DEBUG)

