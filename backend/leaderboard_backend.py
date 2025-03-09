from flask import Flask, send_from_directory, jsonify
import pandas as pd
import os
import glob

# Absolute path to templates and static directories
TEMPLATE_DIR = os.path.abspath("frontend/templates")
STATIC_DIR = os.path.abspath("frontend/static")

print("Template Directory:", TEMPLATE_DIR)  # Debugging line

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

data_dir = "/backend/data/"

# File Paths
SCORES_FILE = os.path.join(data_dir, "scores.xlsx")
LEADERBOARD_FILE = os.path.join(data_dir, "leaderboard.xlsx")
BACKUP_DIR = os.path.join(data_dir, "MTbackup/")

def load_latest_backup():
    """Finds the most recent leaderboard backup in MTbackup."""
    backup_files = glob.glob(os.path.join(BACKUP_DIR, "leaderboard_*.xlsx"))
    if not backup_files:
        return None  # No backup found

    latest_file = max(backup_files, key=os.path.getctime)  # Get the most recent file
    return pd.ExcelFile(latest_file)

@app.route("/update_leaderboard", methods=["POST"])
def update_leaderboard():
    """Calculate rankings for event and season leaderboard and update leaderboard.xlsx."""
    try:
        if not os.path.exists(SCORES_FILE):
            return jsonify({"error": "Scores file not found"}), 404

        # 🔹 Read scores.xlsx
        df_scores = pd.read_excel(SCORES_FILE)
        if df_scores.empty:
            return jsonify({"error": "No scores available"}), 400

        # 🔹 Calculate Event Leaderboard Rankings
        df_group_a_gross = df_scores[df_scores["Group"] == "A"].copy()
        df_group_a_gross["Rank"] = df_group_a_gross["total_stroke"].rank(method="min", ascending=True)
        df_group_a_gross.sort_values(by="Rank", inplace=True)

        df_group_a_stableford = df_scores[df_scores["Group"] == "A"].copy()
        df_group_a_stableford["Rank"] = df_group_a_stableford["stableford point"].rank(method="min", ascending=False)
        df_group_a_stableford.sort_values(by="Rank", inplace=True)

        df_group_b_stableford = df_scores[df_scores["Group"] == "B"].copy()
        df_group_b_stableford["Rank"] = df_group_b_stableford["stableford point"].rank(method="min", ascending=False)
        df_group_b_stableford.sort_values(by="Rank", inplace=True)

        df_team = df_scores.groupby("Team").agg({"stableford point": "mean", "player": "count"}).reset_index()
        df_team.columns = ["Team", "Average Stableford", "Players Joined"]
        df_team["Rank"] = df_team["Average Stableford"].rank(method="min", ascending=False)
        df_team.sort_values(by="Rank", inplace=True)

        # 🔹 Process Season Leaderboard
        latest_backup = load_latest_backup()
        if latest_backup:
            df_season_prev = latest_backup.parse("Season Leaderboard")
            df_season_updated = pd.concat([df_season_prev, df_scores]).groupby("player").agg({"stableford point": "sum"}).reset_index()
        else:
            df_season_updated = df_scores.groupby("player").agg({"stableford point": "sum"}).reset_index()

        # 🔹 Save Event and Season Leaderboard to leaderboard.xlsx
        with pd.ExcelWriter(LEADERBOARD_FILE, engine="openpyxl") as writer:
            df_group_a_gross.to_excel(writer, sheet_name="Event Leaderboard", startrow=1, index=False)
            df_group_a_stableford.to_excel(writer, sheet_name="Event Leaderboard", startrow=len(df_group_a_gross) + 5, index=False)
            df_group_b_stableford.to_excel(writer, sheet_name="Event Leaderboard", startrow=len(df_group_a_gross) + len(df_group_a_stableford) + 10, index=False)
            df_team.to_excel(writer, sheet_name="Event Leaderboard", startrow=len(df_group_a_gross) + len(df_group_a_stableford) + len(df_group_b_stableford) + 15, index=False)
 
            df_season_updated.to_excel(writer, sheet_name="Season Leaderboard", startrow=1, index=False)

        return jsonify({"message": "Leaderboard updated successfully"})

# Serve Leaderboard Page
@app.route("/leaderboard.html")
def serve_leaderboard():
    return send_from_directory("frontend/templates", "leaderboard.html")  # ✅ Adjust path

@app.route("/api/get_scores")
def get_scores():
    return send_from_directory(data_dir, "scores.xlsx")

# API Route Example
@app.route("/api/leaderboard", methods=["GET"])
def leaderboard_api():
    return jsonify({"message": "Leaderboard API is working!", "status": "success"})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
