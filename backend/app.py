from flask import Flask, jsonify
from flask_cors import CORS
from db import get_conn
from transactions import bp as transactions_bp
from expenses import bp as expenses_bp
from settings import bp as settings_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(transactions_bp)
app.register_blueprint(expenses_bp)
app.register_blueprint(settings_bp)

@app.get("/api/inventory")
def list_inventory():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM inventory ORDER BY 1;")
        cols = [d[0] for d in cur.description]
        return jsonify([dict(zip(cols, row)) for row in cur.fetchall()])
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
