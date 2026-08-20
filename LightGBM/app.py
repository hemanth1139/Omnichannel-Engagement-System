from flask import Flask, jsonify, request, render_template_string
import os
import pandas as pd
from score_hcp import predict_hcp

app = Flask(__name__)
OUTPUT_DIR = "output"

# HTML + CSS + JavaScript Frontend Template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Omnichannel HCP Engagement Scoring System</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border-color: rgba(255, 255, 255, 0.1);
            --primary-accent: #38bdf8;
            --primary-gradient: linear-gradient(135deg, #38bdf8 0%, #818cf8 100%);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success-color: #4ade80;
            --warning-color: #facc15;
            --danger-color: #fb923c;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(129, 140, 248, 0.12) 0px, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 2rem 1rem;
        }

        .container {
            max-width: 1100px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            text-align: center;
            margin-bottom: 2.5rem;
        }

        .header h1 {
            font-size: 2.25rem;
            font-weight: 800;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }

        .header p {
            color: var(--text-muted);
            font-size: 1rem;
        }

        /* Search Section */
        .search-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
        }

        .search-box {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .search-input {
            flex: 1;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 0.85rem 1.2rem;
            color: #fff;
            font-size: 1rem;
            outline: none;
            transition: all 0.2s ease;
        }

        .search-input:focus {
            border-color: var(--primary-accent);
            box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2);
        }

        .search-btn {
            background: var(--primary-gradient);
            color: #0f172a;
            font-weight: 700;
            font-size: 1rem;
            padding: 0.85rem 1.75rem;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: transform 0.15s ease, opacity 0.2s ease;
        }

        .search-btn:hover {
            opacity: 0.92;
            transform: translateY(-1px);
        }

        .quick-samples {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-muted);
            flex-wrap: wrap;
        }

        .sample-badge {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            color: var(--primary-accent);
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s ease;
        }

        .sample-badge:hover {
            background: rgba(56, 189, 248, 0.15);
            border-color: var(--primary-accent);
        }

        /* Results Grid */
        .results-container {
            display: none;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .scores-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }

        .score-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 1.25rem;
            text-align: center;
        }

        .score-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .score-val {
            font-size: 2.25rem;
            font-weight: 800;
            color: #fff;
            margin-bottom: 0.5rem;
        }

        .progress-bar-bg {
            background: rgba(255, 255, 255, 0.1);
            height: 6px;
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-bar-fill {
            height: 100%;
            background: var(--primary-gradient);
            border-radius: 3px;
            width: 0%;
            transition: width 0.6s ease;
        }

        /* Level Badge */
        .level-badge {
            display: inline-block;
            padding: 0.35rem 1rem;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.9rem;
            text-transform: uppercase;
        }

        .level-high { background: rgba(74, 222, 128, 0.15); color: var(--success-color); border: 1px solid var(--success-color); }
        .level-medium { background: rgba(250, 204, 21, 0.15); color: var(--warning-color); border: 1px solid var(--warning-color); }
        .level-low { background: rgba(251, 146, 60, 0.15); color: var(--danger-color); border: 1px solid var(--danger-color); }

        /* Probabilities & Recommendation Grid */
        .details-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        @media (max-width: 768px) {
            .details-grid { grid-template-columns: 1fr; }
        }

        .detail-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
        }

        .detail-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 1.25rem;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .channel-row {
            margin-bottom: 1rem;
        }

        .channel-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            margin-bottom: 0.35rem;
            font-weight: 500;
        }

        .nbc-highlight {
            background: rgba(56, 189, 248, 0.15);
            border: 1px solid var(--primary-accent);
            color: var(--primary-accent);
            padding: 0.3rem 0.8rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 700;
        }

        .reason-box {
            background: rgba(15, 23, 42, 0.6);
            border-left: 4px solid var(--primary-accent);
            border-radius: 8px;
            padding: 1.25rem;
            font-size: 0.95rem;
            line-height: 1.6;
            color: #e2e8f0;
        }

        /* Loading & Error */
        .loading-spinner {
            display: none;
            text-align: center;
            padding: 2rem;
            font-size: 1.1rem;
            color: var(--primary-accent);
        }

        .error-box {
            display: none;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid #ef4444;
            color: #fca5a5;
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>Omnichannel HCP Engagement Dashboard</h1>
            <p>Real-time predictive scoring, channel probabilities, and AI recommendations for Healthcare Professionals</p>
        </div>

        <!-- Search Card -->
        <div class="search-card">
            <div class="search-box">
                <input type="text" id="hcpInput" class="search-input" placeholder="Enter HCP ID (e.g. HCP0001, HCP0523, 42)..." value="HCP0001">
                <button class="search-btn" onclick="searchHCP()">Search HCP</button>
            </div>
            <div class="quick-samples">
                <span>Quick Samples:</span>
                <span class="sample-badge" onclick="quickSearch('HCP0001')">HCP0001</span>
                <span class="sample-badge" onclick="quickSearch('HCP0100')">HCP0100</span>
                <span class="sample-badge" onclick="quickSearch('HCP0500')">HCP0500</span>
                <span class="sample-badge" onclick="quickSearch('HCP1000')">HCP1000</span>
                <span class="sample-badge" onclick="quickSearch('HCP1500')">HCP1500</span>
            </div>
        </div>

        <!-- Error Alert -->
        <div id="errorBox" class="error-box"></div>

        <!-- Loading Spinner -->
        <div id="loading" class="loading-spinner">
            ⚡ Analyzing HCP historical behavior & predicting future engagement...
        </div>

        <!-- Results View -->
        <div id="results" class="results-container">
            <!-- Top Score Cards -->
            <div class="scores-grid">
                <div class="score-card">
                    <div class="score-label">Historical Score</div>
                    <div class="score-val" id="histScore">0.0</div>
                    <div class="progress-bar-bg"><div class="progress-bar-fill" id="histBar"></div></div>
                </div>

                <div class="score-card">
                    <div class="score-label">Predicted Score</div>
                    <div class="score-val" id="predScore">0.0</div>
                    <div class="progress-bar-bg"><div class="progress-bar-fill" id="predBar"></div></div>
                </div>

                <div class="score-card">
                    <div class="score-label">Hybrid Score</div>
                    <div class="score-val" id="hybridScore">0.0</div>
                    <div class="progress-bar-bg"><div class="progress-bar-fill" id="hybridBar"></div></div>
                </div>

                <div class="score-card" style="display:flex; flex-direction:column; justify-content:center; align-items:center;">
                    <div class="score-label">Engagement Tier</div>
                    <div id="levelBadge" class="level-badge level-medium">MEDIUM</div>
                </div>
            </div>

            <!-- Channel Probabilities & Recommendation -->
            <div class="details-grid">
                <!-- Channel Probabilities -->
                <div class="detail-card">
                    <div class="detail-title">
                        <span>Channel Engagement Probabilities</span>
                        <span id="nbcBadge" class="nbc-highlight">NEXT BEST: EMAIL</span>
                    </div>

                    <div class="channel-row">
                        <div class="channel-info">
                            <span>📧 Email Channel</span>
                            <span id="probEmail">0.0%</span>
                        </div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" id="barEmail"></div></div>
                    </div>

                    <div class="channel-row">
                        <div class="channel-info">
                            <span>🌐 Website Portal</span>
                            <span id="probWeb">0.0%</span>
                        </div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" id="barWeb"></div></div>
                    </div>

                    <div class="channel-row">
                        <div class="channel-info">
                            <span>🎓 Webinar / Event</span>
                            <span id="probWebinar">0.0%</span>
                        </div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" id="barWebinar"></div></div>
                    </div>

                    <div class="channel-row">
                        <div class="channel-info">
                            <span>🤝 Veeva Representative</span>
                            <span id="probVeeva">0.0%</span>
                        </div>
                        <div class="progress-bar-bg"><div class="progress-bar-fill" id="barVeeva"></div></div>
                    </div>
                </div>

                <!-- Recommendation Reason -->
                <div class="detail-card">
                    <div class="detail-title">
                        <span>AI Recommended Outreach Strategy</span>
                    </div>
                    <div class="reason-box" id="reasonText">
                        Select or search an HCP to generate AI recommendations...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function searchHCP() {
            const input = document.getElementById('hcpInput').value.trim();
            if (!input) return;

            const errorBox = document.getElementById('errorBox');
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');

            errorBox.style.display = 'none';
            loading.style.display = 'block';
            results.style.display = 'none';

            try {
                const response = await fetch(`/api/score/${encodeURIComponent(input)}`);
                const data = await response.json();

                if (!response.ok || data.error) {
                    throw new Error(data.error || 'Failed to fetch HCP score');
                }

                renderResults(data);
                loading.style.display = 'none';
                results.style.display = 'block';
            } catch (err) {
                loading.style.display = 'none';
                errorBox.innerText = `Error: ${err.message}`;
                errorBox.style.display = 'block';
            }
        }

        function quickSearch(id) {
            document.getElementById('hcpInput').value = id;
            searchHCP();
        }

        function renderResults(data) {
            // Scores
            document.getElementById('histScore').innerText = data.Historical_Engagement_Score.toFixed(1);
            document.getElementById('predScore').innerText = data.Predicted_Engagement_Score.toFixed(1);
            document.getElementById('hybridScore').innerText = data.Hybrid_Engagement_Score.toFixed(1);

            document.getElementById('histBar').style.width = `${Math.min(data.Historical_Engagement_Score, 100)}%`;
            document.getElementById('predBar').style.width = `${Math.min(data.Predicted_Engagement_Score, 100)}%`;
            document.getElementById('hybridBar').style.width = `${Math.min(data.Hybrid_Engagement_Score, 100)}%`;

            // Badge
            const badge = document.getElementById('levelBadge');
            badge.innerText = data.Engagement_Level;
            badge.className = `level-badge level-${data.Engagement_Level.toLowerCase()}`;

            // Probabilities
            const p = data.Channel_Probabilities;
            document.getElementById('probEmail').innerText = `${(p.Email * 100).toFixed(1)}%`;
            document.getElementById('probWeb').innerText = `${(p.Website * 100).toFixed(1)}%`;
            document.getElementById('probWebinar').innerText = `${(p.Webinar * 100).toFixed(1)}%`;
            document.getElementById('probVeeva').innerText = `${(p.Veeva * 100).toFixed(1)}%`;

            document.getElementById('barEmail').style.width = `${p.Email * 100}%`;
            document.getElementById('barWeb').style.width = `${p.Website * 100}%`;
            document.getElementById('barWebinar').style.width = `${p.Webinar * 100}%`;
            document.getElementById('barVeeva').style.width = `${p.Veeva * 100}%`;

            // NBC & Reason
            document.getElementById('nbcBadge').innerText = `NEXT BEST: ${data.Next_Best_Channel.toUpperCase()}`;
            document.getElementById('reasonText').innerText = `"${data.Recommended_Reason}"`;
        }

        // Search HCP0001 on page load
        window.addEventListener('DOMContentLoaded', () => {
            searchHCP();
        });
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    """Root route: Renders the web frontend dashboard for searching HCP engagement scores."""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/score/<hcp_id>", methods=["GET"])
def get_hcp_score(hcp_id):
    """GET endpoint: Returns real-time score JSON for requested HCP ID."""
    try:
        res = predict_hcp(hcp_id)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/score", methods=["POST"])
def post_hcp_score():
    """POST endpoint: Accepts JSON payload {'hcp_id': 'HCP0001'} from frontend."""
    try:
        data = request.get_json(force=True)
        hcp_id = data.get("hcp_id", "HCP0001")
        res = predict_hcp(hcp_id)
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/predictions", methods=["GET"])
def get_all_predictions():
    """GET endpoint: Returns batch predictions from output/hcp_engagement_predictions.csv."""
    pred_path = os.path.join(OUTPUT_DIR, "hcp_engagement_predictions.csv")
    if os.path.exists(pred_path):
        df = pd.read_csv(pred_path)
        limit = request.args.get("limit", default=100, type=int)
        return jsonify(df.head(limit).to_dict(orient="records")), 200
    else:
        return jsonify({"error": "Predictions file not found"}), 404


if __name__ == "__main__":
    print(
        "Starting Omnichannel HCP Scoring REST API & Web Dashboard on http://127.0.0.1:5000..."
    )
    app.run(host="0.0.0.0", port=5000, debug=False)
