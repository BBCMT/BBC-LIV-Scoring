// ?Update with your actual Render backend URL
const BASE_URL = "https://bbc-liv-scoring.onrender.com";

// ? Ensure the script runs only when the page is fully loaded
document.addEventListener("DOMContentLoaded", function () {
    console.log("Script loaded successfully! Fetching data...");

    // Load course PAR data
    fetch(`${BASE_URL}/get_course_par`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log("PAR Data Loaded:", data);
            // Handle the course PAR data
        })
        .catch(error => console.error("Error pre-loading PAR data:", error));

    // Load teams and players data
    fetch(`${BASE_URL}/get_teams_and_players`)
        .then (response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log("Teams and Players Loaded:", data);
            populateDropdowns(data);  // Ensure dropdowns are updated
        })
        .catch(error => {
            console.error("Error loading teams/players:", error);
        });

    // Upload button event listener
    const uploadBtn = document.getElementById("uploadLeaderboard");
    if (uploadBtn) {
        uploadBtn.addEventListener("click", function () {
            console.log("Upload button clicked!");
            // Add your upload logic here
        });
    } else {
        console.warn("Warning: 'uploadLeaderboard' not found in the HTML.");
    }
});

function populateDropdowns(data) {
    if (!data.teams || !data.players) {
        console.error("Error: Missing teams or players data.");
        return;
    }
    const teamSelect = document.getElementById("teamSelect");
    const playerSelect = document.getElementById("playerSelect");

    if (!teamSelect || !playerSelect) {
        console.warn("Dropdown elements not found!");
        return;
    }

    // Clear existing options
    teamSelect.innerHTML = '<option value="">Select Team</option>';
    playerSelect.innerHTML = '<option value="">Select Player</option>';

    data.teams.forEach(team => {
        let option = document.createElement("option");
        option.value = team.name;
        option.textContent = team.name;
        teamSelect.appendChild(option);
    });

    data.players.forEach(player => {
        let option = document.createElement("option");
        option.value = player.name;
        option.textContent = player.name;
        playerSelect.appendChild(option);
    });

    console.log("Dropdowns populated successfully.");
}

