#!/usr/bin/env python3
"""
Flask Web Application for Magic Deck Optimizer
"""

import json
import os
import queue
import sys
import threading
import time
from datetime import datetime
from io import StringIO

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
)
from werkzeug.utils import secure_filename

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import config
from magic_optimizer.deck_builder import EnhancedDeckBuilder

app = Flask(__name__)
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

# Global variables for communication between threads
output_queue = queue.Queue()
current_result = None
optimization_running = False


class OutputCapture:
    """Capture print output and send to web interface"""

    def __init__(self):
        self.buffer = []
        self.lock = threading.Lock()

    def write(self, text):
        with self.lock:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.buffer.append(f"[{timestamp}] {text}")
            if (
                len(self.buffer) > config.NUMBERS["max_output_lines"]
            ):  # Keep last 1000 lines
                self.buffer.pop(0)
            output_queue.put(
                {
                    "type": "output",
                    "timestamp": timestamp,
                    "text": text,
                    "full_buffer": self.buffer[
                        -config.NUMBERS["output_buffer_size"] :
                    ],  # Send last 50 lines
                }
            )

    def flush(self):
        pass


# Redirect stdout to our capture
output_capture = OutputCapture()
sys.stdout = output_capture


def run_optimization(
    csv_file_path,
    num_colors,
    total_deck_size,
    land_ratio,
    algorithm,
    lambda_penalty,
    export_formats,
    evaluation_method,
):
    """Run optimization in a separate thread"""
    global current_result, optimization_running

    try:
        optimization_running = True
        output_queue.put({"type": "status", "status": "starting"})

        # Load CSV file
        print(f"Loading CSV file: {csv_file_path}")
        collection_df = pd.read_csv(csv_file_path)
        print(f"Loaded {len(collection_df)} cards from collection")

        # Calculate land/non-land split
        num_lands = round(total_deck_size * land_ratio)
        num_nonlands = total_deck_size - num_lands
        print(
            f"Deck size: {total_deck_size}, Land ratio: {land_ratio}, Lands: {num_lands}, Non-lands: {num_nonlands}"
        )

        # Initialize deck builder
        deck_builder = EnhancedDeckBuilder()

        # Run optimization
        print(f"Starting optimization with {algorithm} algorithm...")
        print(
            f"Target Colors: {num_colors}, Non-Land Cards: {num_nonlands}, Lambda Penalty: {lambda_penalty}"
        )
        print(f"Evaluation Method: {evaluation_method}")

        result = deck_builder.build_optimal_deck_advanced(
            collection_df=collection_df,
            num_colors=num_colors,
            deck_size=num_nonlands,
            algorithm=algorithm,
            export_formats=export_formats,
            lambda_penalty=lambda_penalty,
            total_deck_size=total_deck_size,
            land_ratio=land_ratio,
            evaluation_method=evaluation_method,
        )

        current_result = result
        output_queue.put(
            {
                "type": "result",
                "result": {
                    "deck": result["deck"],
                    "score": result["score"],
                    "target_colors": result["target_colors"],
                    "algorithm": result["algorithm"],
                    "evaluation_method": result.get("evaluation_method", "manual"),
                    "exported_files": result.get("exported_files", []),
                },
            }
        )

        print("Optimization completed successfully!")

    except Exception as e:
        print(f"Error during optimization: {e}")
        import traceback

        traceback.print_exc()
        output_queue.put({"type": "error", "error": str(e)})

    finally:
        optimization_running = False
        output_queue.put({"type": "status", "status": "completed"})


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
    if file.filename == "":
        return jsonify({"error": config.VALIDATION_MESSAGES["no_file_selected"]}), 400

    if file and file.filename.endswith(".csv"):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Try to load and validate the CSV
        try:
            df = pd.read_csv(filepath)
            card_count = len(df)
            return jsonify(
                {
                    "success": True,
                    "filename": filename,
                    "card_count": card_count,
                    "filepath": filepath,
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

    return jsonify({"error": "Invalid file format. Please upload a CSV file."}), 400


@app.route("/optimize", methods=["POST"])
def optimize():
    """Start optimization"""
    global optimization_running

    if optimization_running:
        return (
            jsonify({"error": config.VALIDATION_MESSAGES["optimization_running"]}),
            400,
        )

    data = request.json
    csv_file_path = data.get("csv_file_path")
    num_colors = int(data.get("num_colors", 2))
    total_deck_size = int(data.get("deck_size", 40))
    land_count = int(data.get("land_ratio", 17))  # This is now the number of lands
    algorithm = data.get("algorithm", "genetic")
    lambda_penalty = float(data.get("lambda_penalty", 0.5))
    export_formats = data.get("export_formats", [])
    evaluation_method = data.get("evaluation_method", "manual")

    if not csv_file_path or not os.path.exists(csv_file_path):
        return jsonify({"error": "Invalid CSV file path"}), 400

    # Calculate land ratio as decimal
    land_ratio = land_count / total_deck_size

    # Start optimization in background thread
    thread = threading.Thread(
        target=run_optimization,
        args=(
            csv_file_path,
            num_colors,
            total_deck_size,
            land_ratio,
            algorithm,
            lambda_penalty,
            export_formats,
            evaluation_method,
        ),
    )
    thread.daemon = True
    thread.start()

    return jsonify({"success": True, "message": "Optimization started"})


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
    messages = []
    while not output_queue.empty():
        try:
            msg = output_queue.get_nowait()
            # Convert sets to lists in result messages
            if msg.get("type") == "result" and "result" in msg:
                msg["result"] = convert_sets_to_lists(msg["result"])
            messages.append(msg)
        except queue.Empty:
            break

    return jsonify(
        {
            "messages": messages,
            "running": optimization_running,
            "has_result": current_result is not None,
        }
    )


@app.route("/download/<format>")
def download_deck(format):
    """Download deck in specified format"""
    global current_result

    if not current_result or "deck" not in current_result:
        return jsonify({"error": "No deck available for download"}), 400

    try:
        deck_builder = EnhancedDeckBuilder()
        exported_files = deck_builder.exporter.export_deck(
            deck=current_result["deck"],
            algorithm=current_result["algorithm"],
            target_colors=current_result["target_colors"],
            score=current_result["score"],
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
    global current_result

    if not current_result:
        return jsonify({"error": "No deck available"}), 400

    deck = current_result["deck"]
    evaluation_method = current_result.get("evaluation_method", "manual")

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

    # Get evaluation method details
    evaluation_info = {
        "method": evaluation_method,
        "description": (
            "Manual evaluation + synergy values from local dictionary."
            if evaluation_method == "manual"
            else "Data-based evaluation from 17Lands – combines GIH Winrate and IWD."
        ),
        "is_17lands": evaluation_method == "17lands",
    }

    return jsonify(
        convert_sets_to_lists(
            {
                "deck": deck,
                "score": current_result["score"],
                "colors": current_result["target_colors"],
                "algorithm": current_result["algorithm"],
                "evaluation": evaluation_info,
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
        deck_builder = EnhancedDeckBuilder()
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
    global current_result

    if not current_result or "deck" not in current_result:
        return jsonify({"error": "No deck available"}), 400

    try:
        deck = current_result["deck"]
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


if __name__ == "__main__":
    app.run(
        host=config.APP_CONFIG["host"],
        port=config.APP_CONFIG["port"],
        debug=config.APP_CONFIG["debug"],
        threaded=config.APP_CONFIG["threaded"],
    )
