from flask import Flask, jsonify
from flask_cors import CORS
from db import get_conn

app = Flask(__name__)
CORS(app)

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