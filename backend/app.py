from flask import Flask, jsonify
from flask_cors import CORS

from auth import bp as auth_bp
from transactions import bp as transactions_bp
from expenses import bp as expenses_bp
from settings import bp as settings_bp
from inventory import bp as inventory_bp
from pos import bp as pos_bp
from dashboard import bp as dashboard_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(auth_bp)
app.register_blueprint(transactions_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(inventory_bp)
app.register_blueprint(pos_bp)
app.register_blueprint(dashboard_bp)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True, port=5001)