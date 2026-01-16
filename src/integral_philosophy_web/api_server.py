#!/usr/bin/env python3
"""
REST API for Integral Philosophy Publishing System
Provides programmatic access to all pipeline components
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import sys
import json
import uuid
import threading
import queue
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max file size

# Global job management
job_queue = queue.Queue()
job_status = {}
api_key = os.environ.get("INTEGRAL_API_KEY", "dev-key-2025")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import system components
try:
    from format_converter import FormatConverter
    from tei_generator import TEIGenerator
    from ast_to_uml import UMLGenerator
    from web_scraper import WebScraper
    from content_pipeline import ContentPipeline

    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Components not available: {e}")
    COMPONENTS_AVAILABLE = False


def require_api_key(f):
    """Decorator to require API key authentication"""

    def decorated_function(*args, **kwargs):
        if request.headers.get("X-API-Key") != api_key:
            return jsonify({"error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)

    return decorated_function


class APIJob:
    """Background job for API requests"""

    def __init__(self, job_id: str, job_type: str, params: Dict[str, Any]):
        self.job_id = job_id
        self.job_type = job_type
        self.params = params
        self.status = "pending"
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = datetime.now()
        self.work_dir = Path(f"api_jobs/{job_id}")
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Execute job in background"""
        try:
            self.status = "running"
            self._update_status()

            if self.job_type == "convert":
                self._run_conversion()
            elif self.job_type == "scrape":
                self._run_scraping()
            elif self.job_type == "tei":
                self._run_tei_generation()
            elif self.job_type == "uml":
                self._run_uml_generation()
            elif self.job_type == "pipeline":
                self._run_full_pipeline()
            else:
                raise ValueError(f"Unknown job type: {self.job_type}")

            self.status = "completed"

        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            logger.error(f"Job {self.job_id} failed: {e}")

        finally:
            self._update_status()

    def _update_status(self):
        """Update global job status"""
        job_status[self.job_id] = {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "error": self.error,
            "result": self.result,
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat()
            if self.status in ["completed", "failed"]
            else None,
        }

    def _run_conversion(self):
        """Run format conversion"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Pipeline components not available")

        input_content = self.params.get("input_content")
        input_format = self.params.get("input_format", "markdown")
        output_format = self.params.get("output_format", "html")

        if not input_content:
            raise ValueError("Input content is required")

        # Save input file
        input_file = self.work_dir / f"input.{self._get_file_extension(input_format)}"
        input_file.write_text(input_content, encoding="utf-8")

        self.progress = 20
        self._update_status()

        # Convert
        converter = FormatConverter(self.work_dir)
        success, output_file = converter.convert(input_file, output_format)

        self.progress = 80
        self._update_status()

        if success and output_file.exists():
            self.result = {
                "output_content": output_file.read_text(encoding="utf-8"),
                "output_format": output_format,
                "file_size": output_file.stat().st_size,
            }
        else:
            raise Exception("Conversion failed")

        self.progress = 100

    def _run_scraping(self):
        """Run web scraping"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Pipeline components not available")

        url = self.params.get("url")
        max_pages = self.params.get("max_pages", 10)
        depth = self.params.get("depth", 2)

        if not url:
            raise ValueError("URL is required")

        self.progress = 20
        self._update_status()

        # Scrape
        scraper = WebScraper(
            {
                "max_pages": max_pages,
                "timeout": 30,
                "rate_limit": 1.0,
                "respect_robots": True,
            }
        )

        result = scraper.scrape_url(url, depth)

        self.progress = 80
        self._update_status()

        if result and "pages" in result:
            self.result = {
                "url": url,
                "pages_scraped": len(result["pages"]),
                "scraping_data": result,
            }
        else:
            raise Exception("Scraping failed")

        self.progress = 100

    def _run_tei_generation(self):
        """Run TEI generation"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Pipeline components not available")

        input_content = self.params.get("input_content")
        metadata = self.params.get("metadata", {})

        if not input_content:
            raise ValueError("Input content is required")

        # Save input file
        input_file = self.work_dir / "input.md"
        input_file.write_text(input_content, encoding="utf-8")

        self.progress = 20
        self._update_status()

        # Convert to AST
        converter = FormatConverter(self.work_dir)
        ast_data = converter.convert_to_ast(input_file)

        self.progress = 60
        self._update_status()

        # Generate TEI
        generator = TEIGenerator()
        tei_xml = generator.generate_tei(
            ast_data,
            {
                "title": metadata.get("title", "API Generated Document"),
                "author": metadata.get("author", "API User"),
                "language": metadata.get("language", "en"),
                "date": metadata.get("date", datetime.now().isoformat()),
            },
        )

        self.progress = 80
        self._update_status()

        # Save TEI file
        tei_file = self.work_dir / "output.xml"
        tei_file.write_text(tei_xml, encoding="utf-8")

        self.result = {
            "tei_xml": tei_xml,
            "tei_size": len(tei_xml.encode("utf-8")),
            "metadata": metadata,
        }

        self.progress = 100

    def _run_uml_generation(self):
        """Run UML generation"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Pipeline components not available")

        input_content = self.params.get("input_content")
        uml_format = self.params.get("format", "plantuml")

        if not input_content:
            raise ValueError("Input content is required")

        # Save input file
        input_file = self.work_dir / "input.md"
        input_file.write_text(input_content, encoding="utf-8")

        self.progress = 20
        self._update_status()

        # Convert to AST
        converter = FormatConverter(self.work_dir)
        ast_data = converter.convert_to_ast(input_file)

        self.progress = 60
        self._update_status()

        # Generate UML
        generator = UMLGenerator()
        if uml_format == "plantuml":
            uml_output = generator.generate_plantuml(ast_data)
        elif uml_format == "mermaid":
            uml_output = generator.generate_mermaid(ast_data)
        elif uml_format == "graphviz":
            uml_output = generator.generate_dot(ast_data)
        else:
            uml_output = generator.generate_plantuml(ast_data)

        self.progress = 80
        self._update_status()

        # Save UML file
        uml_file = self.work_dir / f"diagram.{uml_format}"
        uml_file.write_text(uml_output, encoding="utf-8")

        self.result = {
            "uml_content": uml_output,
            "uml_format": uml_format,
            "uml_size": len(uml_output.encode("utf-8")),
        }

        self.progress = 100

    def _run_full_pipeline(self):
        """Run full pipeline"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Pipeline components not available")

        source = self.params.get("source")
        options = self.params.get("options", {})

        if not source:
            raise ValueError("Source is required")

        self.progress = 20
        self._update_status()

        # Create pipeline
        pipeline = ContentPipeline(
            {
                "scraping": options.get("scraping", {"depth": 2, "js_render": True}),
                "processing": options.get(
                    "processing", {"generate_tei": True, "generate_uml": True}
                ),
                "output": options.get("output", {"formats": ["html", "tei"]}),
            }
        )

        self.progress = 40
        self._update_status()

        # Run pipeline
        if source.startswith("http"):
            result = pipeline.process_website(
                source, {"output_dir": str(self.work_dir)}
            )
        else:
            result = pipeline.process_files(source, {"output_dir": str(self.work_dir)})

        self.progress = 80
        self._update_status()

        self.result = {
            "source": source,
            "pipeline_result": result,
            "output_directory": str(self.work_dir),
        }

        self.progress = 100

    def _get_file_extension(self, format_name: str) -> str:
        """Get file extension for format"""
        extensions = {
            "markdown": "md",
            "html": "html",
            "latex": "tex",
            "org": "org",
            "asciidoc": "adoc",
            "rst": "rst",
            "typst": "typ",
            "tei": "xml",
        }
        return extensions.get(format_name, "txt")


# API Routes


@app.route("/api/v1/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components_available": COMPONENTS_AVAILABLE,
            "version": "1.0.0",
        }
    )


@app.route("/api/v1/info", methods=["GET"])
def api_info():
    """API information"""
    return jsonify(
        {
            "name": "Integral Philosophy Publishing System API",
            "version": "1.0.0",
            "description": "REST API for academic content processing pipeline",
            "endpoints": {
                "health": "/api/v1/health",
                "convert": "/api/v1/convert",
                "scrape": "/api/v1/scrape",
                "tei": "/api/v1/tei",
                "uml": "/api/v1/uml",
                "pipeline": "/api/v1/pipeline",
                "jobs": "/api/v1/jobs",
                "job_status": "/api/v1/jobs/<job_id>",
            },
            "formats": {
                "input": [
                    "markdown",
                    "html",
                    "latex",
                    "org",
                    "asciidoc",
                    "rst",
                    "typst",
                ],
                "output": [
                    "html",
                    "latex",
                    "org",
                    "asciidoc",
                    "rst",
                    "typst",
                    "tei",
                    "pdf",
                    "epub",
                    "docx",
                ],
            },
            "authentication": "API Key (X-API-Key header)",
        }
    )


@app.route("/api/v1/convert", methods=["POST"])
@require_api_key
def api_convert():
    """Format conversion endpoint"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("input_content"):
            return jsonify({"error": "input_content is required"}), 400

        # Create job
        job_id = str(uuid.uuid4())
        job = APIJob(job_id, "convert", data)

        # Start job in background
        thread = threading.Thread(target=job.run)
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "job_id": job_id,
                "status": "submitted",
                "message": "Conversion job submitted successfully",
            }
        ), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/scrape", methods=["POST"])
@require_api_key
def api_scrape():
    """Web scraping endpoint"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("url"):
            return jsonify({"error": "url is required"}), 400

        # Create job
        job_id = str(uuid.uuid4())
        job = APIJob(job_id, "scrape", data)

        # Start job in background
        thread = threading.Thread(target=job.run)
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "job_id": job_id,
                "status": "submitted",
                "message": "Scraping job submitted successfully",
            }
        ), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/tei", methods=["POST"])
@require_api_key
def api_tei():
    """TEI generation endpoint"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("input_content"):
            return jsonify({"error": "input_content is required"}), 400

        # Create job
        job_id = str(uuid.uuid4())
        job = APIJob(job_id, "tei", data)

        # Start job in background
        thread = threading.Thread(target=job.run)
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "job_id": job_id,
                "status": "submitted",
                "message": "TEI generation job submitted successfully",
            }
        ), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/uml", methods=["POST"])
@require_api_key
def api_uml():
    """UML generation endpoint"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("input_content"):
            return jsonify({"error": "input_content is required"}), 400

        # Create job
        job_id = str(uuid.uuid4())
        job = APIJob(job_id, "uml", data)

        # Start job in background
        thread = threading.Thread(target=job.run)
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "job_id": job_id,
                "status": "submitted",
                "message": "UML generation job submitted successfully",
            }
        ), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/pipeline", methods=["POST"])
@require_api_key
def api_pipeline():
    """Full pipeline endpoint"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get("source"):
            return jsonify({"error": "source is required"}), 400

        # Create job
        job_id = str(uuid.uuid4())
        job = APIJob(job_id, "pipeline", data)

        # Start job in background
        thread = threading.Thread(target=job.run)
        thread.daemon = True
        thread.start()

        return jsonify(
            {
                "job_id": job_id,
                "status": "submitted",
                "message": "Pipeline job submitted successfully",
            }
        ), 202

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/jobs", methods=["GET"])
@require_api_key
def api_list_jobs():
    """List all jobs"""
    try:
        limit = request.args.get("limit", 50, type=int)
        status_filter = request.args.get("status")

        # Filter jobs
        jobs = []
        for job_id, status_data in job_status.items():
            if status_filter and status_data.get("status") != status_filter:
                continue
            jobs.append(status_data)

        # Sort by start time (newest first)
        jobs.sort(key=lambda x: x.get("start_time", ""), reverse=True)

        # Limit results
        jobs = jobs[:limit]

        return jsonify(
            {"jobs": jobs, "total": len(jobs), "filtered": bool(status_filter)}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/jobs/<job_id>", methods=["GET"])
@require_api_key
def api_get_job(job_id):
    """Get specific job status"""
    try:
        if job_id not in job_status:
            return jsonify({"error": "Job not found"}), 404

        return jsonify(job_status[job_id])

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/jobs/<job_id>", methods=["DELETE"])
@require_api_key
def api_delete_job(job_id):
    """Delete job and cleanup files"""
    try:
        if job_id not in job_status:
            return jsonify({"error": "Job not found"}), 404

        # Remove from status
        del job_status[job_id]

        # Cleanup job directory
        job_dir = Path(f"api_jobs/{job_id}")
        if job_dir.exists():
            shutil.rmtree(job_dir)

        return jsonify({"message": f"Job {job_id} deleted successfully"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Plugin System
@app.route("/api/v1/plugins", methods=["GET"])
@require_api_key
def api_list_plugins():
    """List available plugins"""
    try:
        # This is a placeholder for future plugin system
        plugins = {
            "converters": [
                {
                    "name": "FormatConverter",
                    "description": "Convert between multiple markup formats",
                    "version": "1.0.0",
                }
            ],
            "scrapers": [
                {
                    "name": "WebScraper",
                    "description": "Extract content from websites",
                    "version": "1.0.0",
                }
            ],
            "generators": [
                {
                    "name": "TEIGenerator",
                    "description": "Generate TEI XML for academic use",
                    "version": "1.0.0",
                },
                {
                    "name": "UMLGenerator",
                    "description": "Generate UML diagrams from content",
                    "version": "1.0.0",
                },
            ],
        }

        return jsonify(plugins)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Create necessary directories
    Path("api_jobs").mkdir(exist_ok=True)

    # Start API server
    app.run(host="0.0.0.0", port=5001, debug=False)
