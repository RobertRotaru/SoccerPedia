# ⚽ Soccerpedia: Football AI Assistant

Soccerpedia is an AI-powered assistant specialized in **football (soccer)** 🏟️.  
It combines **LangChain**, **FastAPI**, and **Streamlit** to give you real-time access to match results, player stats, and historical data from multiple sources like ⚡ Transfermarkt and live score APIs.

---

## 🚀 Features
- 🔎 Ask about yesterday’s results or the latest fixtures  
- 👤 Get detailed player information (from Transfermarkt)  
- 📅 Retrieve results from **any matchweek in any season**  
- 🖥️ Web UI built with **Streamlit**  
- ⚡ Backend powered by **FastAPI + LangChain**  

---

## 📂 Project Structure
```
soccerpedia/
│── agent/              # LangChain agent setup & tools
│   ├── agent_factory.py
│   ├── tools.py
│   ├── cache_manager.py
│   ├── data_source.py
│   ├── optimized_tools.py
│── mcp-server/
│   ├── football_mcp.py
│── gui/                # Streamlit frontend
│   ├── app.py
│   ├── app_enhanced.py
│── README.md           # This file
│── requirements.txt    # Dependencies
```

---

## 🛠️ Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/RobertRotaru/soccerpedia.git
cd soccerpedia
```

### 2. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate   # On Linux/Mac
.venv\Scripts\activate    # On Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the FastAPI backend
```bash
uvicorn backend.main:app --reload
```

### 5. Run the Streamlit frontend
```bash
streamlit run gui/app.py
```

---

## 💡 Example Queries

Try asking Soccerpedia in the Streamlit UI:

- `What were yesterday’s Premier League results?`  
- `Show me Barcelona’s last 5 matches.`  
- `Get player info for Erling Haaland.`  
- `What were the results of matchweek 3 in the 2022/23 La Liga season?`  
- `Who scored the most goals in Serie A last season?`  

---

## 🤖 Agent Tools

- **get_matches** → fetch recent or upcoming match results  
- **get_player_info** → retrieve player stats & details  
- **resolve_matchweek** → fetch results from any season & matchweek  

---

## 📜 License
MIT License © 2025
