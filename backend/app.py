from flask import Flask, jsonify

app = Flask(__name__)

#conver to LF
@app.route("/")
def home():
    return "BBC LIV Backend is running!"

@app.route("/leaderboard")
def get_leaderboard():
    return jsonify({"message": "Leaderboard API is working!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
