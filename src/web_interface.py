#!/usr/bin/env python3
"""
Web Interface for Integral Philosophy Publishing System
Flask-based web UI for the content processing pipeline
"""

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    flash,
    redirect,
    url_for,
)
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import uuid
import threading
import queue

# Add scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "scripts"))

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "integral_philosophy_publishing_system_2025"

# Global job tracking
job_queue = queue.Queue()
job_status = {}

# Import system components
try:
    from format_converter import FormatConverter
    from tei_generator import TEIGenerator
    from ast_to_uml import UMLGenerator
    from web_scraper import WebScraper
    from content_pipeline import ContentPipeline

    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some components not available: {e}")
    COMPONENTS_AVAILABLE = False


class WebJob:
    """Background job for web processing"""

    def __init__(self, job_id, job_type, params):
        self.job_id = job_id
        self.job_type = job_type
        self.params = params
        self.status = "pending"
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = datetime.now()

    def run(self):
        """Execute the job"""
        try:
            self.status = "running"
            job_status[self.job_id] = {
                "status": self.status,
                "progress": self.progress,
                "start_time": self.start_time.isoformat(),
                "job_type": self.job_type,
            }

            if self.job_type == "convert":
                self.run_conversion()
            elif self.job_type == "scrape":
                self.run_scraping()
            elif self.job_type == "tei":
                self.run_tei_generation()
            elif self.job_type == "uml":
                self.run_uml_generation()
            elif self.job_type == "pipeline":
                self.run_full_pipeline()

            self.status = "completed"

        except Exception as e:
            self.status = "failed"
            self.error = str(e)

        finally:
            job_status[self.job_id] = {
                "status": self.status,
                "progress": 100 if self.status == "completed" else self.progress,
                "error": self.error,
                "result": self.result,
                "end_time": datetime.now().isoformat(),
            }

    def run_conversion(self):
        """Run format conversion"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Components not available")

        input_file = Path(self.params["input_file"])
        output_format = self.params["output_format"]

        # Create converter
        work_dir = Path(f"web_jobs/{self.job_id}")
        work_dir.mkdir(parents=True, exist_ok=True)

        converter = FormatConverter(work_dir)

        self.progress = 20
        job_status[self.job_id]["progress"] = self.progress

        # Perform conversion
        success, output_file = converter.convert(input_file, output_format)

        self.progress = 80
        job_status[self.job_id]["progress"] = self.progress

        if success:
            self.result = {
                "output_file": str(output_file),
                "file_size": output_file.stat().st_size if output_file.exists() else 0,
            }
        else:
            raise Exception("Conversion failed")

        self.progress = 100

    def run_scraping(self):
        """Run web scraping"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Components not available")

        url = self.params["url"]
        max_pages = self.params.get("max_pages", 10)

        # Create scraper
        scraper = WebScraper({"max_pages": max_pages, "timeout": 30, "rate_limit": 1.0})

        self.progress = 20
        job_status[self.job_id]["progress"] = self.progress

        # Perform scraping
        result = scraper.scrape_url(url, depth=2)

        self.progress = 80
        job_status[self.job_id]["progress"] = self.progress

        if result and "pages" in result:
            self.result = {
                "pages_scraped": len(result["pages"]),
                "scraping_data": result,
            }
        else:
            raise Exception("Scraping failed")

        self.progress = 100

    def run_tei_generation(self):
        """Run TEI generation"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Components not available")

        input_file = Path(self.params["input_file"])

        # Create converter and TEI generator
        work_dir = Path(f"web_jobs/{self.job_id}")
        work_dir.mkdir(parents=True, exist_ok=True)

        converter = FormatConverter(work_dir)
        generator = TEIGenerator()

        self.progress = 20
        job_status[self.job_id]["progress"] = self.progress

        # Convert to AST first
        ast_data = converter.convert_to_ast(input_file)

        self.progress = 60
        job_status[self.job_id]["progress"] = self.progress

        # Generate TEI
        tei_xml = generator.generate_tei(
            ast_data,
            {
                "title": self.params.get("title", "Web Generated Document"),
                "author": self.params.get("author", "Web Interface User"),
                "language": "en",
            },
        )

        # Save TEI file
        output_file = work_dir / "output.xml"
        output_file.write_text(tei_xml, encoding="utf-8")

        self.progress = 80
        job_status[self.job_id]["progress"] = self.progress

        self.result = {
            "tei_file": str(output_file),
            "tei_size": len(tei_xml.encode("utf-8")),
        }

        self.progress = 100

    def run_uml_generation(self):
        """Run UML generation"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Components not available")

        input_file = Path(self.params["input_file"])
        uml_format = self.params.get("format", "plantuml")

        # Create converter and UML generator
        work_dir = Path(f"web_jobs/{self.job_id}")
        work_dir.mkdir(parents=True, exist_ok=True)

        converter = FormatConverter(work_dir)
        generator = UMLGenerator()

        self.progress = 20
        job_status[self.job_id]["progress"] = self.progress

        # Convert to AST first
        ast_data = converter.convert_to_ast(input_file)

        self.progress = 60
        job_status[self.job_id]["progress"] = self.progress

        # Generate UML
        if uml_format == "plantuml":
            uml_output = generator.generate_plantuml(ast_data)
        elif uml_format == "mermaid":
            uml_output = generator.generate_mermaid(ast_data)
        elif uml_format == "graphviz":
            uml_output = generator.generate_dot(ast_data)
        else:
            uml_output = generator.generate_plantuml(ast_data)

        # Save UML file
        output_file = work_dir / f"diagram.{uml_format}"
        output_file.write_text(uml_output, encoding="utf-8")

        self.progress = 80
        job_status[self.job_id]["progress"] = self.progress

        self.result = {
            "uml_file": str(output_file),
            "uml_format": uml_format,
            "uml_size": len(uml_output.encode("utf-8")),
        }

        self.progress = 100

    def run_full_pipeline(self):
        """Run full content pipeline"""
        if not COMPONENTS_AVAILABLE:
            raise Exception("Components not available")

        source = self.params["source"]

        # Create pipeline
        work_dir = Path(f"web_jobs/{self.job_id}")
        work_dir.mkdir(parents=True, exist_ok=True)

        pipeline = ContentPipeline(
            {
                "scraping": {"depth": 2, "js_render": True},
                "processing": {"generate_tei": True, "generate_uml": True},
                "output": {"formats": ["html", "tei"]},
            }
        )

        self.progress = 20
        job_status[self.job_id]["progress"] = self.progress

        # Run pipeline
        if source.startswith("http"):
            result = pipeline.process_website(source, {"output_dir": str(work_dir)})
        else:
            result = pipeline.process_files(source, {"output_dir": str(work_dir)})

        self.progress = 80
        job_status[self.job_id]["progress"] = self.progress

        self.result = {"pipeline_result": result, "output_directory": str(work_dir)}

        self.progress = 100


@app.route("/")
def index():
    """Main page"""
    return render_template("index.html")


@app.route("/convert", methods=["GET", "POST"])
def convert():
    """Format conversion page"""
    if request.method == "GET":
        return render_template("convert.html")

    # Handle file upload
    if "file" not in request.files:
        flash("No file uploaded")
        return redirect(url_for("convert"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected")
        return redirect(url_for("convert"))

    # Save uploaded file
    job_id = str(uuid.uuid4())
    upload_dir = Path("web_jobs") / job_id / "upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    input_file = upload_dir / file.filename
    file.save(input_file)

    # Create job
    output_format = request.form.get("format", "html")
    job = WebJob(
        job_id,
        "convert",
        {"input_file": str(input_file), "output_format": output_format},
    )

    # Start job in background
    thread = threading.Thread(target=job.run)
    thread.daemon = True
    thread.start()

    return render_template("job_status.html", job_id=job_id, job_type="Conversion")


@app.route("/scrape", methods=["GET", "POST"])
def scrape():
    """Web scraping page"""
    if request.method == "GET":
        return render_template("scrape.html")

    # Create job
    job_id = str(uuid.uuid4())
    job = WebJob(
        job_id,
        "scrape",
        {
            "url": request.form.get("url"),
            "max_pages": int(request.form.get("max_pages", 10)),
        },
    )

    # Start job in background
    thread = threading.Thread(target=job.run)
    thread.daemon = True
    thread.start()

    return render_template("job_status.html", job_id=job_id, job_type="Web Scraping")


@app.route("/tei", methods=["GET", "POST"])
def tei():
    """TEI generation page"""
    if request.method == "GET":
        return render_template("tei.html")

    # Handle file upload
    if "file" not in request.files:
        flash("No file uploaded")
        return redirect(url_for("tei"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected")
        return redirect(url_for("tei"))

    # Save uploaded file
    job_id = str(uuid.uuid4())
    upload_dir = Path("web_jobs") / job_id / "upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    input_file = upload_dir / file.filename
    file.save(input_file)

    # Create job
    job = WebJob(
        job_id,
        "tei",
        {
            "input_file": str(input_file),
            "title": request.form.get("title", "Web Generated Document"),
            "author": request.form.get("author", "Web Interface User"),
        },
    )

    # Start job in background
    thread = threading.Thread(target=job.run)
    thread.daemon = True
    thread.start()

    return render_template("job_status.html", job_id=job_id, job_type="TEI Generation")


@app.route("/uml", methods=["GET", "POST"])
def uml():
    """UML generation page"""
    if request.method == "GET":
        return render_template("uml.html")

    # Handle file upload
    if "file" not in request.files:
        flash("No file uploaded")
        return redirect(url_for("uml"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected")
        return redirect(url_for("uml"))

    # Save uploaded file
    job_id = str(uuid.uuid4())
    upload_dir = Path("web_jobs") / job_id / "upload"
    upload_dir.mkdir(parents=True, exist_ok=True)

    input_file = upload_dir / file.filename
    file.save(input_file)

    # Create job
    job = WebJob(
        job_id,
        "uml",
        {
            "input_file": str(input_file),
            "format": request.form.get("format", "plantuml"),
        },
    )

    # Start job in background
    thread = threading.Thread(target=job.run)
    thread.daemon = True
    thread.start()

    return render_template("job_status.html", job_id=job_id, job_type="UML Generation")


@app.route("/pipeline", methods=["GET", "POST"])
def pipeline():
    """Full pipeline page"""
    if request.method == "GET":
        return render_template("pipeline.html")

    # Create job
    job_id = str(uuid.uuid4())
    job = WebJob(job_id, "pipeline", {"source": request.form.get("source")})

    # Start job in background
    thread = threading.Thread(target=job.run)
    thread.daemon = True
    thread.start()

    return render_template("job_status.html", job_id=job_id, job_type="Full Pipeline")


@app.route("/status/<job_id>")
def status(job_id):
    """Get job status"""
    status_data = job_status.get(job_id, {"status": "not_found"})
    return jsonify(status_data)


@app.route("/download/<job_id>/<filename>")
def download(job_id, filename):
    """Download job output file"""
    file_path = Path(f"web_jobs/{job_id}/{filename}")
    if file_path.exists():
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404


@app.route("/view/<job_id>/<filename>")
def view_file(job_id, filename):
    """View job output file"""
    file_path = Path(f"web_jobs/{job_id}/{filename}")
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        return render_template(
            "view_file.html", content=content, filename=filename, job_id=job_id
        )
    else:
        return "File not found", 404


# Template routes
@app.route("/templates/<template_name>")
def template_file(template_name):
    """Serve template files"""
    template_path = Path(f"web_templates/{template_name}")
    if template_path.exists():
        return send_file(template_path)
    else:
        return "Template not found", 404


if __name__ == "__main__":
    # Create necessary directories
    Path("web_jobs").mkdir(exist_ok=True)
    Path("web_templates").mkdir(exist_ok=True)

    # Start Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
