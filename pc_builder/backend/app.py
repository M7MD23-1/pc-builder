from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from data_loader import load_components
from search import bfs, dfs, ucs, astar

app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"),
    static_url_path=""
)
CORS(app)

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data", "PC_Components_Dataset_small__2_.xlsx")
MIN_BUDGET_BY_PURPOSE = {
    "Gaming": 920,
    "Office": 300,
    "Content Creation": 740,
    "AI Workstation": 1040,
    "Budget Build": 390,
    "High-End Build": 1060,
}


def normalize_purpose_name(purpose):
    text = str(purpose or "").strip()
    aliases = {
        "AI / ML Workstation": "AI Workstation",
        "AI/ML Workstation": "AI Workstation",
    }
    return aliases.get(text, text)


def format_build(result):
    return {
        "algorithm": result.get("algorithm"),
        "explored_states": result.get("explored_states"),
        "total_price": result.get("total_price"),
        "components": {
            "cpu": {
                "name": result["cpu"]["name"],
                "socket": result["cpu"]["socket"],
                "cores": result["cpu"]["cores"],
                "price": result["cpu"]["price_usd"],
            },
            "motherboard": {
                "name": result["mb"]["name"],
                "socket": result["mb"]["socket"],
                "price": result["mb"]["price_usd"],
            },
            "ram": {
                "name": result["ram"]["name"],
                "capacity": result["ram"]["capacity_gb"],
                "price": result["ram"]["price_usd"],
            },
            "storage": {
                "name": result["storage"]["name"],
                "interface": result["storage"]["interface"],
                "price": result["storage"]["price_usd"],
            },
            "gpu": {
                "name": result["gpu"]["name"] if "gpu" in result else "Integrated",
                "vram": result["gpu"].get("vram_gb", 0) if "gpu" in result else 0,
                "price": result["gpu"]["price_usd"] if "gpu" in result else 0,
            },
            "psu": {
                "name": result["psu"]["name"],
                "wattage": result["psu"]["wattage"],
                "price": result["psu"]["price_usd"],
            },
        }
    }


def format_builds(results):
    if not results:
        return []
    return [format_build(result) for result in results]


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/build", methods=["POST"])
def build():
    try:
        data = request.get_json() or {}

        budget = float(data.get("budget", 0))
        purpose = normalize_purpose_name(data.get("purpose", ""))
        algorithm = str(data.get("algorithm", "")).strip().upper()

        if budget <= 0 or not purpose or not algorithm:
            return jsonify({"success": False, "error": "يرجى إدخال جميع الحقول بشكل صحيح"}), 400

        valid_purposes = [
            "Gaming",
            "Office",
            "Content Creation",
            "AI Workstation",
            "Budget Build",
            "High-End Build",
        ]
        if purpose not in valid_purposes:
            return jsonify({"success": False, "error": f"غرض غير معروف: {purpose}"}), 400

        components = load_components(DATA_PATH)

        if algorithm == "BFS":
            result = bfs(components, budget, purpose)
        elif algorithm == "DFS":
            result = dfs(components, budget, purpose)
        elif algorithm == "UCS":
            result = ucs(components, budget, purpose)
        elif algorithm == "A*":
            result = astar(components, budget, purpose)
        else:
            return jsonify({"success": False, "error": f"خوارزمية غير معروفة: {algorithm}"}), 400

        if not result:
            min_budget = MIN_BUDGET_BY_PURPOSE.get(purpose)
            return jsonify({
                "success": False,
                "min_budget": min_budget
            })

        return jsonify({
            "success": True,
            "builds": format_builds(result)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/components", methods=["GET"])
def get_components():
    components = load_components(DATA_PATH)
    return jsonify({
        "cpu": len(components["cpu"]),
        "mb": len(components["mb"]),
        "ram": len(components["ram"]),
        "storage": len(components["storage"]),
        "gpu": len(components["gpu"]),
        "psu": len(components["psu"]),
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)