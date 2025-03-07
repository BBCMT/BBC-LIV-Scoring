document.addEventListener("DOMContentLoaded", function () {
    fetch("https://bbc-liv-scoring.onrender.com/leaderboard")
        .then(response => response.json())
        .then(data => {
            console.log("Leaderboard Data:", data);
        })
        .catch(error => console.error("Error fetching leaderboard:", error));
});
