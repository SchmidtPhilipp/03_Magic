#!/usr/bin/env python3
"""
Flask Web Application for Magic Deck Optimizer
"""

import json
import logging
import logging.handlers
import os
import queue
import sys
import threading
import time
import uuid
from datetime import datetime
from io import StringIO
import shutil

import pandas as pd
import requests
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
    session,
)
from werkzeug.utils import secure_filename

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config
from magic_optimizer.deck_builder import EnhancedDeckBuilder
from magic_optimizer.collection.routes import collection_bp
from magic_optimizer.deck_picker.api import deck_picker_bp


# Setup logging
def setup_logging():
    """Setup comprehensive logging system"""
    # Create logs directory
    os.makedirs("logs", exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler (INFO level for user-friendly output)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (DEBUG level for all details)
    file_handler = logging.handlers.RotatingFileHandler(
        "logs/web_app.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Create specific loggers
    user_logger = logging.getLogger("user")
    user_logger.setLevel(logging.INFO)

    optimization_logger = logging.getLogger("optimization")
    optimization_logger.setLevel(logging.DEBUG)

    api_logger = logging.getLogger("api")
    api_logger.setLevel(logging.DEBUG)

    return user_logger, optimization_logger, api_logger


# Initialize logging
user_logger, optimization_logger, api_logger = setup_logging()

app = Flask(__name__)
app.register_blueprint(collection_bp)
app.register_blueprint(deck_picker_bp)
app.config["SECRET_KEY"] = config.APP_CONFIG["secret_key"]
app.config["UPLOAD_FOLDER"] = config.PATHS["upload_folder"]
app.config["CACHE_FOLDER"] = config.PATHS[
    "cache_folder"
]  # Folder for cached card images
app.config["MAX_CONTENT_LENGTH"] = (
    config.NUMBERS["max_file_size_mb"] * 1024 * 1024
)  # Convert MB to bytes

# Create upload and cache folders if they don't exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["CACHE_FOLDER"], exist_ok=True)

# Initialize the deck builder once to be shared across requests
deck_builder = EnhancedDeckBuilder()

from magic_optimizer.collection.db import init_db

init_db()

user_logger.info("Logging system initialized")
user_logger.info(f"Log files: logs/")

# Concurrent optimization management
class OptimizationManager:
    """Manages multiple concurrent optimization processes"""
    
    def __init__(self):
        self.active_optimizations = {}  # optimization_id -> optimization_info
        self.lock = threading.Lock()
    
    def start_optimization(self, optimization_id, params):
        """Start a new optimization process"""
        with self.lock:
            if optimization_id in self.active_optimizations:
                return False, "Optimization already exists"
            
            # Create queue for this optimization
            output_queue = queue.Queue()
            
            # Create output capture for this optimization
            output_capture = OutputCapture(output_queue)
            
            # Store optimization info
            self.active_optimizations[optimization_id] = {
                'params': params,
                'queue': output_queue,
                'output_capture': output_capture,
                'thread': None,
                'running': False,
                'result': None,
                'start_time': time.time()
            }
            
            # Start optimization thread
            thread = threading.Thread(
                target=self._run_optimization,
                args=(optimization_id, params, output_capture)
            )
            thread.daemon = True
            thread.start()
            
            self.active_optimizations[optimization_id]['thread'] = thread
            self.active_optimizations[optimization_id]['running'] = True
            
            return True, "Optimization started"
    
    def stop_optimization(self, optimization_id):
        """Stop a specific optimization"""
        with self.lock:
            if optimization_id in self.active_optimizations:
                self.active_optimizations[optimization_id]['running'] = False
                return True, "Optimization stopped"
            return False, "Optimization not found"
    
    def get_optimization_status(self, optimization_id):
        """Get status of a specific optimization"""
        with self.lock:
            if optimization_id not in self.active_optimizations:
                return None
            
            opt_info = self.active_optimizations[optimization_id]
            
            # Get messages from queue
            messages = []
            while not opt_info['queue'].empty():
                try:
                    msg = opt_info['queue'].get_nowait()
                    messages.append(msg)
                except queue.Empty:
                    break
            
            return {
                'running': opt_info['running'],
                'result': opt_info['result'],
                'messages': messages,
                'start_time': opt_info['start_time']
            }
    
    def cleanup_optimization(self, optimization_id):
        """Clean up completed optimization"""
        with self.lock:
            if optimization_id in self.active_optimizations:
                del self.active_optimizations[optimization_id]
    
    def _run_optimization(self, optimization_id, params, output_capture):
        """Run optimization in a separate thread"""
        try:
            # Set up output capture for this thread
            original_stdout = sys.stdout
            sys.stdout = output_capture
            
            # Send starting message
            output_capture.queue.put({"type": "status", "status": "starting"})
            
            # Load collection file
            filepath = params['filepath']
            print(f"Loading collection file: {filepath}")
            collection_df = deck_builder.load_collection(filepath)
            print(f"Loaded {len(collection_df)} cards from collection")
            
            # Check if optimization was stopped
            if not self.active_optimizations[optimization_id]['running']:
                print("Optimization stopped by user")
                return
            
            # Run optimization
            algorithm = params['algorithm']
            print(f"Starting optimization with {algorithm} algorithm...")
            print(f"Target Colors: {params['num_colors']}, Deck Size: {params['deck_size']}, Lands: {params['num_lands']}, Lambda: {params['lambda_penalty']}")
            print(f"Optimization Criterion: {params['optimization_criterion']}")
            if params['fixed_colors']:
                print(f"Fixed Colors: {', '.join(params['fixed_colors'])}")
            
            print(f"DEBUG: Received fixed_colors: {params['fixed_colors']}")
            sys.stdout.flush()
            
            # Check if optimization was stopped
            if not self.active_optimizations[optimization_id]['running']:
                print("Optimization stopped by user")
                return
            
            # Prepare parameters for build_optimal_deck_advanced
            build_params = {
                "collection_df": collection_df,
                "num_colors": params['num_colors'],
                "total_deck_size": params['deck_size'],
                "num_lands": params['num_lands'],
                "algorithm": params['algorithm'],
                "optimization_criterion": params['optimization_criterion'],
                "lambda_penalty": params['lambda_penalty'],
                "fixed_colors": params['fixed_colors'],
            }
            
            # Add runtime limit if provided
            if 'max_runtime_seconds' in params:
                build_params['max_runtime_seconds'] = params['max_runtime_seconds']
            
            result = deck_builder.build_optimal_deck_advanced(**build_params)
            
            sys.stdout.flush()
            
            # Check if optimization was stopped
            if not self.active_optimizations[optimization_id]['running']:
                print("Optimization stopped by user")
                return
            
            # Store result
            self.active_optimizations[optimization_id]['result'] = result
            output_capture.queue.put({
                "type": "result",
                "result": {
                    "deck": result["deck"],
                    "score": result["score"],
                    "target_colors": result["target_colors"],
                    "algorithm": result["algorithm"],
                    "optimization_criterion": result.get("optimization_criterion", "manual"),
                    "exported_files": result.get("exported_files", []),
                },
            })
            
            print("Optimization completed successfully!")
            sys.stdout.flush()
            
        except Exception as e:
            print(f"Error during optimization: {e}")
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            output_capture.queue.put({"type": "error", "error": str(e)})
        
        finally:
            # Restore original stdout
            sys.stdout = original_stdout
            # Mark as not running
            self.active_optimizations[optimization_id]['running'] = False
            output_capture.queue.put({"type": "status", "status": "completed"})


# Global optimization manager
optimization_manager = OptimizationManager()

EVALUATION_CRITERIA = [
    {"value": "empirical_mit", "label": "Empirical: MIT DraftBot Regression"},
    {"value": "manual", "label": "Manual Ratings"},
    {"value": "empirical_vanilla", "label": "Empirical: Vanilla-Test + Keywords (LSV-Style)"},
    {"value": "empirical_cube", "label": "Empirical: CubeTutor Value System"},
    {"value": "empirical_average", "label": "Empirical: Average of All Models"},
]


class OutputCapture:
    """Capture print output and send to web interface"""

    def __init__(self, queue):
        self.queue = queue
        self.buffer = []

    def write(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.buffer.append(f"[{timestamp}] {text}")
        if len(self.buffer) > config.NUMBERS["max_output_lines"]:
            self.buffer.pop(0)
        
        # Send output immediately to web interface
        try:
            self.queue.put_nowait(
                {
                    "type": "output",
                    "timestamp": timestamp,
                    "text": text,
                    "full_buffer": self.buffer[
                        -config.NUMBERS["output_buffer_size"] :
                    ],
                }
            )
        except queue.Full:
            # If queue is full, just skip this message to prevent blocking
            pass

    def flush(self):
        # Ensure any buffered output is sent
        pass


# Note: Output capture is now handled per-optimization in OptimizationManager





@app.route("/")
def index():
    """Main page"""
    return render_template("index.html", config=config)


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload"""
    if "file" not in request.files:
        return jsonify({"error": config.VALIDATION_MESSAGES["no_file"]}), 400

    file = request.files["file"]
    
    if not file or not file.filename:
        return jsonify({"error": config.VALIDATION_MESSAGES["no_file_selected"]}), 400

    if file.filename.endswith(".csv"):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        session["uploaded_file"] = filename
        
        # Try to load and validate the CSV for immediate feedback
        try:
            df = pd.read_csv(filepath)
            card_count = len(df)
            return jsonify(
                {
                    "success": True,
                    "filename": filename,
                    "filepath": filepath,
                    "card_count": card_count,
                }
            )
        except Exception as e:
            return (
                jsonify(
                    {
                        "error": f"Invalid CSV file: {str(e)}",
                    }
                ),
                400,
            )
    elif file.filename.endswith(".txt"):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        session["uploaded_file"] = filename
        
        # Try to load and validate the text file for immediate feedback
        try:
            from src.magic_optimizer.utils.text_parser import TextFileParser
            text_parser = TextFileParser()
            df = text_parser.parse_text_file(filepath)
            card_count = len(df)
            return jsonify(
                {
                    "success": True,
                    "filename": filename,
                    "filepath": filepath,
                    "card_count": card_count,
                }
            )
        except Exception as e:
            return (
                jsonify(
                    {
                        "error": f"Invalid text file: {str(e)}",
                    }
                ),
                400,
            )

    return jsonify({"error": "Invalid file format. Please upload a CSV or TXT file."}), 400


@app.route("/optimize", methods=["POST"])
def optimize():
    """Start the deck optimization process"""
    # Generate unique optimization ID
    optimization_id = str(uuid.uuid4())

    # Check for uploaded file
    uploaded_file = session.get("uploaded_file")
    if not uploaded_file:
        # If no file is in session, use the default collection
        print("No file uploaded. Using default FinalFantasy.csv collection.")
        filepath = os.path.join("data", "collections", "FinalFantasy.csv")
        # To be safe, place its name in the session for other parts of the app
        session["uploaded_file"] = "FinalFantasy.csv"
    else:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], uploaded_file)

    if not os.path.exists(filepath):
        return (
            jsonify({"error": f"File not found: {os.path.basename(filepath)}"}),
            404,
        )
        
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    num_colors = data.get("num_colors")
    deck_size = data.get("deck_size")
    num_lands = data.get("num_lands")
    algorithm = data.get("algorithm")
    optimization_criterion = data.get("optimization_criterion")
    lambda_penalty = data.get("lambda_penalty")
    fixed_colors = data.get("fixed_colors", [])

    if not all(
        [filepath, num_colors, deck_size, num_lands, algorithm, optimization_criterion]
    ):
        return jsonify({"error": "Missing required parameters"}), 400

    # Prepare optimization parameters
    params = {
        'filepath': filepath,
        'num_colors': num_colors,
        'deck_size': deck_size,
        'num_lands': num_lands,
        'algorithm': algorithm,
        'optimization_criterion': optimization_criterion,
        'lambda_penalty': lambda_penalty,
        'fixed_colors': fixed_colors,
    }
    
    # Start optimization
    success, message = optimization_manager.start_optimization(optimization_id, params)
    
    if success:
        return jsonify({
            "success": True, 
            "message": "Optimization started",
            "optimization_id": optimization_id
        })
    else:
        return jsonify({"error": message}), 400


def convert_sets_to_lists(obj):
    if isinstance(obj, dict):
        return {k: convert_sets_to_lists(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_sets_to_lists(x) for x in obj]
    elif isinstance(obj, set):
        return list(obj)
    else:
        return obj


@app.route("/status")
def get_status():
    """Get current optimization status and output"""
    optimization_id = request.args.get('optimization_id')
    
    if not optimization_id:
        return jsonify({"error": "Missing optimization_id parameter"}), 400
    
    status = optimization_manager.get_optimization_status(optimization_id)
    
    if status is None:
        return jsonify({"error": "Optimization not found"}), 404
    
            # Convert sets to lists in result messages
    if status['result']:
        status['result'] = convert_sets_to_lists(status['result'])
    
    for msg in status['messages']:
            if msg.get("type") == "result" and "result" in msg:
                msg["result"] = convert_sets_to_lists(msg["result"])
    
    return jsonify(status)


@app.route("/download/<format>")
def download_deck(format):
    """Download deck in specified format"""
    # Find the most recent completed optimization
    latest_result = None
    latest_time = 0
    
    for opt_id, opt_info in optimization_manager.active_optimizations.items():
        if opt_info['result'] and opt_info['start_time'] > latest_time:
            latest_result = opt_info['result']
            latest_time = opt_info['start_time']
    
    if not latest_result or "deck" not in latest_result:
        return jsonify({"error": "No deck available for download"}), 400

    try:
        exported_files = deck_builder.exporter.export_deck(
            deck=latest_result["deck"],
            algorithm=latest_result["algorithm"],
            target_colors=latest_result["target_colors"],
            score=latest_result["score"],
            formats=[format],
        )

        if exported_files and format in exported_files:
            file_path = exported_files[format]
            return send_file(
                file_path, as_attachment=True, download_name=f"deck_{format}.txt"
            )
        else:
            return jsonify({"error": f"Export format {format} not available"}), 400

    except Exception as e:
        return jsonify({"error": f"Export failed: {str(e)}"}), 500


@app.route("/deck_info")
def get_deck_info():
    """Get current deck information"""
    # Find the most recent completed optimization
    latest_result = None
    latest_time = 0
    
    for opt_id, opt_info in optimization_manager.active_optimizations.items():
        if opt_info['result'] and opt_info['start_time'] > latest_time:
            latest_result = opt_info['result']
            latest_time = opt_info['start_time']
    
    if not latest_result:
        return jsonify({"error": "No deck available"}), 400

    deck = latest_result["deck"]
    optimization_criterion = latest_result.get("optimization_criterion", "manual")

    # Analyze deck
    color_counts = {}
    colorless_count = 0
    mana_curve = {i: 0 for i in range(8)}
    card_types = {}
    ratings = []

    for card in deck:
        # Color counts
        colors = card.get("colors", set())
        if not colors:
            colorless_count += 1
        else:
            for color in colors:
                color_counts[color] = color_counts.get(color, 0) + 1

        # Mana curve
        cmc = card.get("cmc", 0)
        if cmc >= 7:
            mana_curve[7] += 1
        else:
            mana_curve[cmc] += 1

        # Card types
        card_type = card.get("type", "Unknown")
        card_types[card_type] = card_types.get(card_type, 0) + 1

        # Ratings
        rating = card.get("rating", 0)
        if rating > 0:
            ratings.append(rating)

    # Add colorless count to color_counts if there are colorless cards
    if colorless_count > 0:
        color_counts["Colorless"] = colorless_count

    # Get optimization criterion details
    criterion_info = {
        "criterion": optimization_criterion,
        "description": (
            "Manual evaluation + synergy values from local dictionary."
            if optimization_criterion == "manual"
            else "Data-based evaluation from 17Lands – combines GIH Winrate and IWD."
        ),
        "is_17lands": optimization_criterion == "17lands",
    }

    return jsonify(
        convert_sets_to_lists(
            {
                "deck": deck,
                "score": latest_result["score"],
                "colors": latest_result["target_colors"],
                "algorithm": latest_result["algorithm"],
                "optimization": criterion_info,
                "analysis": {
                    "color_counts": color_counts,
                    "mana_curve": mana_curve,
                    "card_types": card_types,
                    "avg_rating": sum(ratings) / len(ratings) if ratings else 0,
                    "total_cards": len(deck),
                },
            }
        )
    )


@app.route("/evaluation_methods")
def get_evaluation_methods():
    """Get available evaluation methods for UI dropdown"""
    try:
        methods = deck_builder.optimizer.get_evaluation_methods()
        return jsonify({"methods": methods})
    except Exception as e:
        return jsonify({"error": f"Failed to get evaluation methods: {str(e)}"}), 500


@app.route("/load_default_csv")
def load_default_csv():
    """Load default CSV file for debugging"""
    try:
        # Try default CSV from config
        default_paths = [
            config.PATHS["default_csv"],
            "static/FinalFantasy.csv",
            "data/collections/FinalFantasy.csv",
            "uploads/FinalFantasy.csv",
        ]

        for path in default_paths:
            if os.path.exists(path):
                # Copy to uploads folder if not already there
                if not path.startswith("uploads/"):
                    import shutil

                    upload_path = os.path.join(
                        app.config["UPLOAD_FOLDER"], "FinalFantasy.csv"
                    )
                    shutil.copy2(path, upload_path)
                    path = upload_path

                # Load and validate the CSV
                df = pd.read_csv(path)
                card_count = len(df)
                return jsonify(
                    {
                        "success": True,
                        "filename": "FinalFantasy.csv",
                        "card_count": card_count,
                        "filepath": path,
                    }
                )

        return jsonify({"error": "Default CSV file not found"}), 404

    except Exception as e:
        return jsonify({"error": f"Error loading default CSV: {str(e)}"}), 500


@app.route("/cache_card_image/<card_name>")
def cache_card_image(card_name):
    """Cache a single card image"""
    try:
        # Check if already cached
        cache_filename = f"{card_name}.jpg"
        cache_path = os.path.join(app.config["CACHE_FOLDER"], cache_filename)

        if os.path.exists(cache_path):
            return jsonify(
                {"success": True, "cached": True, "filename": cache_filename}
            )

        # Fetch from Scryfall
        response = requests.get(
            f"{config.LINKS['scryfall_api']}?fuzzy={card_name}&format=image&version=normal",
            timeout=10,
        )

        if response.status_code == 200:
            # Save to cache
            with open(cache_path, "wb") as f:
                f.write(response.content)
            return jsonify(
                {"success": True, "cached": False, "filename": cache_filename}
            )
        else:
            return jsonify({"error": f"Failed to fetch image for {card_name}"}), 404

    except Exception as e:
        return jsonify({"error": f"Error caching image: {str(e)}"}), 500


@app.route("/cache_deck_images", methods=["POST"])
def cache_deck_images():
    """Cache images for all cards in the current deck"""
    # Find the most recent completed optimization
    latest_result = None
    latest_time = 0
    
    for opt_id, opt_info in optimization_manager.active_optimizations.items():
        if opt_info['result'] and opt_info['start_time'] > latest_time:
            latest_result = opt_info['result']
            latest_time = opt_info['start_time']
    
    if not latest_result or "deck" not in latest_result:
        return jsonify({"error": "No deck available"}), 400

    try:
        deck = latest_result["deck"]
        cached_images = []
        failed_images = []

        for card in deck:
            card_name = card.get("name", "")
            if card_name:
                try:
                    # Check if already cached
                    cache_filename = f"{card_name}.jpg"
                    cache_path = os.path.join(
                        app.config["CACHE_FOLDER"], cache_filename
                    )

                    if not os.path.exists(cache_path):
                        # Fetch from Scryfall
                        response = requests.get(
                            f"{config.LINKS['scryfall_api']}?fuzzy={card_name}&format=image&version=normal",
                            timeout=10,
                        )

                        if response.status_code == 200:
                            # Save to cache
                            with open(cache_path, "wb") as f:
                                f.write(response.content)
                            cached_images.append(card_name)
                        else:
                            failed_images.append(card_name)
                    else:
                        cached_images.append(card_name)

                except Exception as e:
                    failed_images.append(f"{card_name} ({str(e)})")

        return jsonify(
            {
                "success": True,
                "cached": len(cached_images),
                "failed": len(failed_images),
                "cached_images": cached_images,
                "failed_images": failed_images,
            }
        )

    except Exception as e:
        return jsonify({"error": f"Error caching deck images: {str(e)}"}), 500


@app.route("/static/card_cache/<filename>")
def serve_cached_image(filename):
    """Serve cached card images"""
    return send_from_directory(app.config["CACHE_FOLDER"], filename)


@app.route("/export_html_with_artwork", methods=["POST"])
def export_html_with_artwork():
    """Render a new page with the decklist and card images (artwork)"""
    if request.content_type and "application/json" in request.content_type:
        data = request.get_json()
        deck = data.get("deck", [])
        deck_name = data.get("deck_name", "Deck Export")
    else:
        # Handle form data from fallback
        try:
            deck = json.loads(request.form.get("deck", "[]"))
            deck_name = request.form.get("deck_name", "Deck Export")
        except (json.JSONDecodeError, KeyError):
            deck = []
            deck_name = "Deck Export"

    # Each card should have at least 'name' and 'quantity'
    return render_template(
        "deck_export_artwork.html",
        deck=deck,
        deck_name=deck_name,
    )


@app.route("/stop_optimization", methods=["POST"])
def stop_optimization():
    """Stop a specific optimization process"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    optimization_id = data.get("optimization_id")
    if not optimization_id:
        return jsonify({"error": "Missing optimization_id parameter"}), 400
    
    success, message = optimization_manager.stop_optimization(optimization_id)
    
    if success:
        return jsonify({"success": True, "message": "Optimization stopped"})
    else:
        return jsonify({"error": message}), 400


if __name__ == "__main__":
    app.run(
        host=config.APP_CONFIG["host"],
        port=config.APP_CONFIG["port"],
        debug=config.APP_CONFIG["debug"],
        threaded=config.APP_CONFIG["threaded"],
    )
