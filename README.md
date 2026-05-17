```
██████╗  ██████╗ ██╗  ██╗███████╗███╗   ███╗ ██████╗ ███╗   ██╗
██╔══██╗██╔═══██╗██║ ██╔╝██╔════╝████╗ ████║██╔═══██╗████╗  ██║
██████╔╝██║   ██║█████╔╝ █████╗  ██╔████╔██║██║   ██║██╔██╗ ██║
██╔═══╝ ██║   ██║██╔═██╗ ██╔══╝  ██║╚██╔╝██║██║   ██║██║╚██╗██║
██║     ╚██████╔╝██║  ██╗███████╗██║ ╚═╝ ██║╚██████╔╝██║ ╚████║
╚═╝      ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═══╝

██████╗  █████╗ ████████╗████████╗██╗     ███████╗██████╗
██╔══██╗██╔══██╗╚══██╔══╝╚══██╔══╝██║     ██╔════╝██╔══██╗
██████╔╝███████║   ██║      ██║   ██║     █████╗  ██████╔╝
██╔══██╗██╔══██║   ██║      ██║   ██║     ██╔══╝  ██╔══██╗
██████╔╝██║  ██║   ██║      ██║   ███████╗███████╗██║  ██║
╚═════╝ ╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚══════╝╚═╝  ╚═╝

        WIN   RATE   INTELLIGENCE
```

**Built on Antigravity · SQL Analytics Portfolio Project**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)](https://plotly.com)

---

## The Business Question

**Which Pokémon has the highest win rate in competitive battles — and does that answer change when we control for type matchup advantages?**

Consider Charizard. If Charizard has a 78% win rate, that sounds dominant. But what if 60% of its battles were against Grass, Bug, and Ice-type opponents — all of which Charizard has a 2× type advantage against? That 78% isn't skill; it's schedule. A salesperson who only closes deals in the richest zip code isn't necessarily the best closer on the team.

To find the *truly* dominant Pokémon, we compute an **adjusted win rate** that deflates performance achieved against type-advantaged opponents and inflates performance achieved against type-disadvantaged opponents. The resulting metric strips away structural unfairness and reveals which Pokémon win on merit, not matchup luck. This is the same analytical technique used in sports (strength-of-schedule adjustment), finance (risk-adjusted returns), and sales analytics (territory-adjusted quota attainment).

---

## Data Architecture

```
pokemon ──(name)──► battles ◄──(name)── pokemon
   │                                       │
   └──(primary_type)──► type_chart ◄──(primary_type)──┘
```

| Table | Rows | Description |
|-------|------|-------------|
| `pokemon` | 151 | Gen 1 Pokémon with base stats, types, BST, and sprite URLs |
| `type_chart` | 324 | 18×18 type effectiveness matrix (multipliers: 0, 0.5, 1, 2) |
| `battles` | 10,000 | Simulated battle records with BST-weighted, type-adjusted outcomes |

The `battles` table joins to `pokemon` **twice** (once for attacker, once for defender), and both sides join to `type_chart` on their primary types. This multi-table JOIN pattern is the foundation of every analytical query in the project.

---

## SQL Skills Demonstrated

| Skill | Where Used | Business Equivalent |
|-------|-----------|---------------------|
| Multi-table JOIN | Query 3, 4, 5 | Joining sales transactions to product catalog |
| CASE WHEN scoring | Query 2, 4 | Flagging accounts by risk tier |
| Common Table Expressions (CTEs) | All queries | Breaking complex logic into readable stages |
| RANK() OVER (PARTITION BY) | Query 4 | Ranking sales reps within their region |
| PERCENT_RANK() OVER () | Query 4 | Scoring customers by lifetime value percentile |
| NULLIF() safe division | All % calculations | Preventing divide-by-zero in KPI calculations |
| COALESCE() null handling | Query 3, 4 | Filling missing values in reporting tables |
| HAVING clause filtering | Query 2, 3, 4 | Filtering segments with insufficient data |
| Aggregated window functions | Query 4 | Running totals, moving averages |
| UNION ALL | Query 5 | Combining top/bottom rankings in one query |

---

## Key Finding

The headline insight emerges from Query 04. Pokémon that appear dominant by raw win rate often owe their record to favourable type matchups. The **inflation gap** (raw win % − adjusted win %) quantifies exactly how much of a Pokémon's reputation is earned vs. inherited.

The most **overrated** Pokémon are those with the largest positive inflation gap — their records collapse when you strip away the type advantage subsidy. The most **underrated** Pokémon show the opposite: they were winning despite facing structurally harder opponents, and their adjusted rates rise above their raw numbers.

This finding is only visible through the type adjustment. Raw leaderboards will never surface it.

---

## The Business Parallel

### Sales Analytics
A sales team has 50 reps across regions with vastly different average deal sizes and competition levels. Rep A closes $2M in revenue in a territory where the average deal is $500K, while Rep B closes $1.5M where the average deal is $50K. Raw revenue says Rep A is better. Territory-adjusted revenue tells a completely different story. The SQL pattern used in this project — computing a contextual multiplier (type advantage → territory difficulty), then dividing raw performance by that multiplier — is the exact technique needed to produce fair sales leaderboards.

### Marketing Analytics
Two campaigns both achieve 4× ROAS. But Campaign A targeted high-intent audiences (equivalent to fighting type-disadvantaged opponents), while Campaign B targeted cold prospects (fighting at a type disadvantage). Adjusting ROAS by audience quality multiplier reveals which campaign strategy actually drove incremental value. The CTE-driven, window-function-ranked query structure demonstrated here scales directly to this use case — swap Pokémon names for campaign IDs, type multipliers for audience quality scores, and the SQL is transferable line-for-line.

---

## How to Run

```bash
# 1. Clone and install
git clone <repo-url>
cd pokemon-battler
pip install -r requirements.txt

# 2. Fetch data from PokéAPI (~3 minutes due to rate limiting)
python data/fetch_pokemon.py
python data/fetch_type_chart.py

# 3. Generate battle simulation
python data/generate_battles.py

# 4. Load everything into SQLite
python data/load_database.py

# 5. Launch the dashboard
cd app && streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Project Structure

```
pokemon-battler/
│
├── README.md                    ← This file
├── requirements.txt             ← Pinned Python dependencies
│
├── data/
│   ├── fetch_pokemon.py         ← Script 1: Pull Pokémon data from PokéAPI
│   ├── fetch_type_chart.py      ← Script 2: Pull type effectiveness matrix
│   ├── generate_battles.py      ← Script 3: Simulate 10,000 battle records
│   ├── load_database.py         ← Script 4: Load all CSVs into SQLite
│   ├── pokemon.csv              ← OUTPUT of Script 1 (151 rows)
│   ├── type_chart.csv           ← OUTPUT of Script 2 (324 rows)
│   └── battles.csv              ← OUTPUT of Script 3 (10,000 rows)
│
├── sql/
│   ├── 00_schema.sql            ← CREATE TABLE statements
│   ├── 01_sanity_check.sql      ← Warm-up validation query
│   ├── 02_raw_win_rate.sql      ← Baseline: naive win %
│   ├── 03_type_matchup_join.sql ← Intermediate: join to type chart
│   ├── 04_adjusted_win_rate.sql ← Advanced: full portfolio query
│   ├── 05_overrated_index.sql   ← Bonus: inflation gap analysis
│   └── 06_type_dominance.sql    ← Bonus: which TYPE wins most
│
├── app/
│   ├── app.py                   ← Main Streamlit application
│   ├── queries.py               ← All SQL queries as Python constants
│   ├── charts.py                ← All Plotly chart builder functions
│   └── styles.css               ← Custom dark-theme CSS
│
└── notebooks/
    └── exploration.ipynb        ← Jupyter notebook walkthrough (optional)
```

---

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Data Acquisition | Python + Requests | PokéAPI data fetch |
| Simulation | Python + Pandas | Battle generation with probability model |
| Database | SQLite | Local analytical data store |
| Analysis | SQL (7 query files) | All metrics, rankings, and classifications |
| Visualisation | Plotly Express + Graph Objects | Interactive charts |
| Dashboard | Streamlit | Web-based UI layer |

---

*Built with precision by a data scientist who understands that the most important metric is never the obvious one.*
