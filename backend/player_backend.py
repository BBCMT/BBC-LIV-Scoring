import pandas as pd
import os, shutil
import glob
from flask import Flask, jsonify, request, render_template
from datetime import datetime
from filelock import FileLock
from flask_cors import CORS
import traceback

# Get the absolute path of the backend directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Get the absolute path of the frontend directory
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

UPLOAD_FOLDER = "/backend/data"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure the folder exists

# Absolute path to templates and static directories
TEMPLATE_DIR = os.path.abspath("frontend/templates")
STATIC_DIR = os.path.abspath("frontend/static")

app = Flask(__name__,
            template_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), "../frontend/templates"),
            static_folder=os.path.join(os.path.abspath(os.path.dirname(__file__)), "../frontend/static")
            )
CORS(app, resources={r"/*": {"origins": "*"}})  # ✅ Allow all origins

#print("🛠 DEBUG: Files in backend ->", os.listdir("backend"))

#conver to LF
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SCORES_FILE = os.path.join(BASE_DIR, "backend/data/scores.xlsx")
LEADERBOARD_FILE = os.path.join(BASE_DIR, "backend/data/leaderboard.xlsx")  # ✅ Define missing variable
COURSE_FILE = os.path.join(BASE_DIR, "backend/data/course_scorecard.xlsx")
TEAM_FILE = os.path.join(BASE_DIR, "backend/data/team_list.xlsx")
PIN_CODE = "BBCforever!"
FILE_LOCK = os.path.join(BASE_DIR, "backend/data/scores.lock")
BACKUP_DIR = os.path.join(BASE_DIR, "backend/data/MTbackup/")

@app.route("/")
def home():
    return render_template("index.html")  # Serve index.html/


@app.route("/upload_xlsx", methods=["POST"])
def upload_xlsx():
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400
    file.save(os.path.join(UPLOAD_FOLDER, file.filename))
    return f"File {file.filename} uploaded successfully", 200

@app.route("/get_teams_and_players", methods=["GET"])
def get_teams_and_players():
    try:
        df = pd.read_excel(TEAM_FILE, header=0)
        teams = df.iloc[:, 0].dropna().unique().tolist()
        team_players = {}
        for _, row in df.iterrows():
            team_name = row.iloc[0]
            if team_name not in team_players:
                team_players[team_name] = []
            for i in range(4):
                name_col = 1 + (i * 4)
                group_col = 2 + (i * 4)
                gender_col = 3 + (i * 4)
                handicap_col = 4 + (i * 4)
                if pd.notna(row.iloc[name_col]):
                    player_data = {
                        "name": row.iloc[name_col],
                        "group": row.iloc[group_col],
                        "gender": row.iloc[gender_col],
                        "handicap": row.iloc[handicap_col]
                    }
                    team_players[team_name].append(player_data)
        return jsonify({"teams": teams, "team_players": team_players})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/get_course_par", methods=["GET"])
def get_course_par():
    try:
        df_course = pd.read_excel(COURSE_FILE, header=0, names=["Hole", "Handicap", "PAR"])

        # ✅ Pre-load all holes correctly
        par_values = {f"hole{i+1}": int(df_course.loc[i, "PAR"]) for i in range(18)}
        handicap_values = {f"hole{i+1}": int(df_course.loc[i, "Handicap"]) for i in range(18)}

        return jsonify({"par": par_values, "handicap": handicap_values})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_playing_handicap', methods=['POST'])
def get_playing_handicap():
    try:
        data = request.json
        exact_handicap = float(data["exact_handicap"])
        gender = data["gender"]

        # Load golf course data to get Slope Rating (SR) and Course Rating (CR)
        course_file = "data/course_info.xlsx"  # Ensure this file exists
        df_course = pd.read_excel(course_file)

        # Extract SR and CR based on gender
        if gender == "M":
            sr = float(df_course.loc[0, "Men_SR"])
            cr = float(df_course.loc[0, "Men_CR"])
        else:
            sr = float(df_course.loc[0, "Women_SR"])
            cr = float(df_course.loc[0, "Women_CR"])

        # ✅ Playing Handicap Formula (Rounded Correctly)
        playing_handicap = round(exact_handicap * (sr / 113) + (cr - 72), 0) 

        return jsonify({"playing_handicap": playing_handicap}) # ✅ Ensure JSON response is correct

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
#flask_submit score
@app.route("/submit_score", methods=["POST"])
def submit_score():
    try:
        data = request.json

        # ✅ Convert incoming data to correct types
        exact_hcp = float(data["exactHandicap"])
        playing_hcp = int(float(data["playingHandicap"]))  # Ensure it's an integer
        total_stroke = int(data["totalStroke"])
        hole_scores = [int(score) for score in data["holeScores"]]  # ✅ Ensure scores are integers

        df_existing = pd.read_excel(SCORES_FILE) if os.path.exists(SCORES_FILE) else pd.DataFrame(columns=[
            "player", "exact_hcp", "Group", "playing_hcp", "total_stroke", "stableford point"
        ] + [f"hole {i}" for i in range(1, 19)] + ["Par Count", "Birdie Count", "timestamp"])

        # ✅ Load course info for Par and Handicap
        df_course = pd.read_excel(COURSE_FILE, usecols=["PAR", "Handicap"])
        course_par = df_course["PAR"].tolist()
        hole_handicap = df_course["Handicap"].tolist()

        # ✅ Compute Par and Birdie Count
        par_count = sum(1 for i in range(18) if hole_scores[i] == course_par[i])
        birdie_count = sum(1 for i in range(18) if hole_scores[i] == course_par[i] - 1)

        # ✅ Compute Stableford Points
        stableford_total = 0
        for i in range(18):
            strokes = hole_scores[i]
            par = course_par[i]
            strokes_received = 1 if playing_hcp >= hole_handicap[i] else 0
            if playing_hcp - 18 >= hole_handicap[i]:
                strokes_received += 1
            net_par = par + strokes_received

            if strokes <= net_par - 3:
                points = 5  # Albatross
            elif strokes == net_par - 2:
                points = 4  # Eagle
            elif strokes == net_par - 1:
                points = 3  # Birdie
            elif strokes == net_par:
                points = 2  # Par
            elif strokes == net_par + 1:
                points = 1  # Bogey
            else:
                points = 0  # Double bogey or worse

            stableford_total += points  # ✅ Now calculating Stableford correctly

        # ✅ Store scores in `scores.xlsx`, including scores per hole
        new_row = {
            "player": data["player"],
            "exact_hcp": float(exact_hcp),  # Ensure exact handicap is a float
            "Group": data.get("group", "Unknown"),  # ✅ Corrected placement inside dictionary
            "playing_hcp": int(playing_hcp),  # Ensure playing handicap is an integer
            "total_stroke": int(total_stroke),  # Convert to integer
            "stableford point": int(stableford_total),  # ✅ Stableford correctly calculated now
            "Par Count": int(par_count),  # Convert to integer
            "Birdie Count": int(birdie_count),  # Convert to integer
            "timestamp": datetime.now().isoformat()
        }

        # ✅ Add per-hole scores (holes 1-18)
        for i in range(1, 19):
            new_row[f"hole {i}"] = hole_scores[i - 1]  # Assign per-hole scores

        # ✅ Remove old score entry for this player and update the DataFrame
        df_existing = df_existing[df_existing["player"] != data["player"]]
        df_existing = pd.concat([df_existing, pd.DataFrame([new_row])], ignore_index=True)

        # ✅ Save the updated scores
        df_existing.to_excel(SCORES_FILE, index=False)

        return jsonify({"message": "Score stored successfully!"})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/mt_competition_prep", methods=["POST"])
def mt_competition_prep():
    try:
        data = request.json
        pin = data.get("pin", "").strip()  # ✅ Trim spaces before checking

        if pin != "BBCforever!":
            return jsonify({"error": "Please contact BBC-MT"}), 403

        # ✅ Clear `scores.xlsx` but keep headers
        if os.path.exists(SCORES_FILE):
            df_scores = pd.read_excel(SCORES_FILE)
            df_scores.iloc[0:0].to_excel(SCORES_FILE, index=False)  # ✅ Keeps headers, clears data

        # ✅ Clear leaderboard files but keep headers
        leaderboard_files = [
            "D:/BBC_LIV/leaderboard/data/event_leaderboard.xlsx",
            "D:/BBC_LIV/leaderboard/data/season_leaderboard.xlsx",
            "D:/BBC_LIV/leaderboard/data/season_score_leaderboard.xlsx",
            "D:/BBC_LIV/leaderboard/data/event_scores_leaderboard.xlsx"
        ]

        for file in leaderboard_files:
            if os.path.exists(file):
                df_leaderboard = pd.read_excel(file)
                df_leaderboard.iloc[0:0].to_excel(file, index=False)  # ✅ Keeps headers, clears data

        return jsonify({"message": "Competition Prep Complete!"})  # ✅ Correct PIN now shows success message

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/mt_scores_backup", methods=["POST"])
def mt_scores_backup():
    try:
        data = request.json
        pin = data.get("pin", "").strip()  

        if pin != PIN_CODE:
            return jsonify({"error": "Please contact BBC-MT"}), 403

        timestamp = datetime.now().strftime("%y%m%d")
        scores_backup_path = os.path.join(BACKUP_DIR, f"score_{timestamp}.xlsx")
        leaderboard_backup_path = os.path.join(BACKUP_DIR, f"leaderboard_{timestamp}.xlsx")

        if os.path.exists(SCORES_FILE):
            shutil.copy(SCORES_FILE, scores_backup_path)

        if os.path.exists(LEADERBOARD_FILE):
            shutil.copy(LEADERBOARD_FILE, leaderboard_backup_path)

        return jsonify({"message": "Backup Successful!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html")  # Serve leaderboard.html

# Serve static files (optional, if needed)
@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "../frontend/static"), filename)

@app.errorhandler(Exception)
def handle_exception(e):
    """Log full errors for debugging."""
    print("🛠 ERROR: ", str(e))
    print(traceback.format_exc())  # Print full error details
    return "Internal Server Error", 500

print("Registered Routes:")
with app.test_request_context():
    print(app.url_map)  # 👈 This will print all registered routes

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)  # Render auto-assigns a port, so this is only for local testing




