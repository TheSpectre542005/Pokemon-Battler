"""
app.py — Pokémon Battler Win Rate Intelligence Dashboard

Nostalgic Pokémon-themed Streamlit app with 5 pages:
  1. Leaderboard — Adjusted win rate rankings
  2. The Truth Gap — Overrated vs. underrated analysis
  3. Type Matrix — 18×18 effectiveness heatmap
  4. Battle Center — Head-to-head Pokémon comparison with win probability
  5. Pokédex Lookup — Individual deep-dive with radar chart

Design: Retro Game Boy aesthetic, Pokédex red/cream palette,
        pixel fonts, CRT scan-lines, animated VS badge.
"""

import os
import sqlite3
import logging
import math

import streamlit as st
import pandas as pd
import requests

from queries import (
    QUERY_ADJUSTED_WIN_RATE,
    QUERY_OVERRATED_INDEX,
    QUERY_TYPE_DOMINANCE,
    QUERY_TYPE_CHART,
    QUERY_POKEMON_DETAIL,
    QUERY_POKEMON_BATTLES,
    QUERY_POKEMON_COUNT,
    QUERY_BATTLE_COUNT,
    QUERY_ALL_POKEMON_NAMES,
    QUERY_HEAD_TO_HEAD,
    QUERY_TYPE_EFFECTIVENESS,
    QUERY_BATTLE_HISTORY,
)
from charts import (
    build_leaderboard_chart,
    build_inflation_gap_chart,
    build_type_heatmap,
    build_type_dominance_chart,
    build_pokemon_radar,
    build_stat_comparison_chart,
    build_dual_radar,
    TYPE_COLORS,
)

# ─── Logging ────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ─── Page Configuration ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pokémon Battler — Antigravity",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─── Load Custom CSS ───────────────────────────────────────────────────────
def load_css() -> None:
    """Inject the retro Pokémon theme from styles.css."""
    css_path = os.path.join(os.path.dirname(__file__), "styles.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        logger.warning("styles.css not found — using default theme.")

load_css()


# ─── Database Connection ──────────────────────────────────────────────────
@st.cache_resource
def get_db_connection() -> sqlite3.Connection:
    """Open a cached SQLite connection to the project database."""
    db_path = os.path.join(os.path.dirname(__file__), "..", "pokemon_battler.db")
    db_path = os.path.abspath(db_path)
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    return sqlite3.connect(db_path, check_same_thread=False)


def run_query(query: str, params: tuple = ()) -> pd.DataFrame:
    """Execute a SQL query and return results as a DataFrame."""
    try:
        conn = get_db_connection()
        return pd.read_sql_query(query, conn, params=params)
    except FileNotFoundError:
        st.error(
            "🚨 **Database not found.** Run the data pipeline first:\n\n"
            "```\npython data/fetch_pokemon.py\n"
            "python data/fetch_type_chart.py\n"
            "python data/generate_battles.py\n"
            "python data/load_database.py\n```"
        )
        st.stop()
    except Exception as exc:
        st.error(f"Query failed: {exc}")
        logger.error("Query error: %s", exc, exc_info=True)
        return pd.DataFrame()


# ─── Helpers ───────────────────────────────────────────────────────────────
def type_badge(type_name: str) -> str:
    """Generate HTML for a coloured type pill badge with glow effect."""
    color = TYPE_COLORS.get(type_name, "#9E9E9E")
    return (
        f'<span class="type-badge" style="background-color:{color};'
        f'box-shadow:0 0 8px {color}40;">'
        f'{type_name.upper()}</span>'
    )


def effectiveness_label(mult: float) -> str:
    """Convert multiplier to a human-readable label with color."""
    if mult == 0.0:
        return '<span style="color:#666;font-weight:700;">IMMUNE (0×)</span>'
    elif mult == 0.5:
        return '<span style="color:#E57373;font-weight:600;">Not Very Effective (½×)</span>'
    elif mult == 1.0:
        return '<span style="color:#9E9E9E;">Normal (1×)</span>'
    elif mult == 2.0:
        return '<span style="color:#4CAF50;font-weight:700;">SUPER EFFECTIVE! (2×)</span>'
    return f'<span style="color:#FFD600;">{mult}×</span>'


@st.cache_data(ttl=3600)
def fetch_pokemon_moves(pokemon_name: str) -> list[dict]:
    """
    Fetch learnable moves from PokéAPI (cached for 1 hour).

    Returns top 8 level-up moves sorted by level learned.
    """
    try:
        resp = requests.get(
            f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}/",
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        moves = []
        for move_entry in data.get("moves", []):
            for version_detail in move_entry.get("version_group_details", []):
                if version_detail.get("move_learn_method", {}).get("name") == "level-up":
                    level = version_detail.get("level_learned_at", 0)
                    if level > 0:
                        moves.append({
                            "name": move_entry["move"]["name"].replace("-", " ").title(),
                            "level": level,
                        })
                    break

        # Deduplicate and sort by level, take top 8
        seen = set()
        unique_moves = []
        for m in sorted(moves, key=lambda x: x["level"]):
            if m["name"] not in seen:
                seen.add(m["name"])
                unique_moves.append(m)
            if len(unique_moves) >= 8:
                break

        return unique_moves
    except Exception as exc:
        logger.warning("Failed to fetch moves for %s: %s", pokemon_name, exc)
        return []


# ─── Sidebar: Pokédex Navigation ──────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="text-align:center;padding:0.5rem 0;">'
        '<span style="font-family:Press Start 2P;font-size:0.7rem;color:#FFDE00;'
        'text-shadow:1px 1px 0 #8B0000;">⚡ POKÉMON</span><br>'
        '<span style="font-family:Press Start 2P;font-size:0.55rem;color:#F8F0E0;'
        'letter-spacing:2px;">BATTLER  SQL</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "🏆 Leaderboard",
            "⚖️ The Truth Gap",
            "🗺️ Type Matrix",
            "⚔️ Battle Center",
            "📖 Pokédex Lookup",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    min_battles = st.slider(
        "Min battles required",
        min_value=10, max_value=100, value=30, step=10,
        help="Exclude Pokémon with fewer battles than this.",
    )

    with st.expander("📜 How it works"):
        st.markdown(
            """
            **Adjusted Win Rate** corrects for opponent difficulty.

            A Pokémon with 80% wins against Grass types (easy matchups)
            is not truly elite. We divide win counts by the average
            type multiplier to reveal who wins on **merit**, not luck.

            *Same logic used in sports analytics and finance.*
            """
        )

    st.markdown(
        '<div style="text-align:center;margin-top:2rem;">'
        '<span style="font-family:VT323;color:#555;font-size:0.9rem;">'
        'Built on Antigravity · 2026</span></div>',
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 1: LEADERBOARD
# ═══════════════════════════════════════════════════════════════════════════
if page == "🏆 Leaderboard":
    st.markdown("# 🏆 TRAINER RANKINGS")
    st.markdown(
        '<p style="font-family:VT323;font-size:1.3rem;color:#A0A0B0;">'
        '"Raw win rate is a lie. Here\'s the truth."</p>',
        unsafe_allow_html=True,
    )

    # Metric cards
    c1, c2, c3 = st.columns(3)
    with c1:
        cnt = run_query(QUERY_POKEMON_COUNT)
        st.metric("Pokémon Analysed", cnt.iloc[0]["cnt"] if not cnt.empty else "—")
    with c2:
        bat = run_query(QUERY_BATTLE_COUNT)
        st.metric("Battles Simulated", f"{bat.iloc[0]['cnt']:,}" if not bat.empty else "—")
    with c3:
        st.metric("Type Matchups", "324")

    st.markdown("---")

    query = QUERY_ADJUSTED_WIN_RATE.format(min_battles=min_battles)
    df = run_query(query)

    if not df.empty:
        st.plotly_chart(build_leaderboard_chart(df), use_container_width=True)
        st.markdown("---")

        st.markdown("### 📊 Full Results")
        display_cols = [
            "pokemon_name", "primary_type", "total_battles",
            "raw_win_pct", "adjusted_win_pct", "inflation_gap", "analyst_tag",
        ]
        st.dataframe(
            df[display_cols], use_container_width=True, hide_index=True,
            column_config={
                "pokemon_name": st.column_config.TextColumn("Pokémon", width="medium"),
                "primary_type": st.column_config.TextColumn("Type"),
                "total_battles": st.column_config.NumberColumn("Battles", format="%d"),
                "raw_win_pct": st.column_config.NumberColumn("Raw %", format="%.1f%%"),
                "adjusted_win_pct": st.column_config.NumberColumn("Adj %", format="%.1f%%"),
                "inflation_gap": st.column_config.NumberColumn("Gap", format="%+.1f"),
                "analyst_tag": st.column_config.TextColumn("Tag"),
            },
        )

        with st.expander("📜 What is Adjusted Win Rate?"):
            st.markdown(
                """
                Raw win rate treats all victories equally — but a win against a
                type-disadvantaged opponent is "free." Adjusted win rate divides
                by the average type multiplier to normalize for schedule difficulty.

                **Inflation gap** = raw − adjusted. Positive = overrated. Negative = underrated.
                Same technique used for risk-adjusted returns in finance and
                strength-of-schedule in sports analytics.
                """
            )
    else:
        st.warning("No data returned. Check the database or adjust filters.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 2: THE TRUTH GAP
# ═══════════════════════════════════════════════════════════════════════════
elif page == "⚖️ The Truth Gap":
    st.markdown("# ⚖️ THE TRUTH GAP")
    st.markdown(
        '<p style="font-family:VT323;font-size:1.3rem;color:#A0A0B0;">'
        'Whose reputation doesn\'t match reality?</p>',
        unsafe_allow_html=True,
    )

    query = QUERY_OVERRATED_INDEX.format(min_battles=min_battles)
    df = run_query(query)

    if not df.empty:
        overrated = df[df["category"] == "MOST OVERRATED"]
        underrated = df[df["category"] == "MOST UNDERRATED"]

        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🔻 Most Overrated")
            for _, row in overrated.iterrows():
                badge = type_badge(row["primary_type"])
                delta = round(row["raw_win_pct"] - row["adjusted_win_pct"], 1)
                sprite = row.get("sprite_url", "")
                st.markdown(
                    f'<div class="glass-card" style="display:flex;align-items:center;gap:1rem;">'
                    f'<img src="{sprite}" width="48" style="image-rendering:pixelated;">'
                    f'<div>'
                    f'<strong style="font-size:1.1rem;">{row["pokemon_name"].title()}</strong> '
                    f'{badge}<br>'
                    f'<span style="color:#888;font-size:0.9rem;">Raw: {row["raw_win_pct"]}% → '
                    f'Adj: {row["adjusted_win_pct"]}%</span> '
                    f'<span style="color:#E63946;font-weight:700;"> ▼ {delta}pp</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

        with col_r:
            st.markdown("### 🔺 Most Underrated")
            for _, row in underrated.iterrows():
                badge = type_badge(row["primary_type"])
                delta = round(row["adjusted_win_pct"] - row["raw_win_pct"], 1)
                sprite = row.get("sprite_url", "")
                st.markdown(
                    f'<div class="glass-card" style="display:flex;align-items:center;gap:1rem;">'
                    f'<img src="{sprite}" width="48" style="image-rendering:pixelated;">'
                    f'<div>'
                    f'<strong style="font-size:1.1rem;">{row["pokemon_name"].title()}</strong> '
                    f'{badge}<br>'
                    f'<span style="color:#888;font-size:0.9rem;">Raw: {row["raw_win_pct"]}% → '
                    f'Adj: {row["adjusted_win_pct"]}%</span> '
                    f'<span style="color:#4CAF50;font-weight:700;"> ▲ {delta}pp</span>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        full_df = run_query(QUERY_ADJUSTED_WIN_RATE.format(min_battles=min_battles))
        if not full_df.empty:
            st.plotly_chart(build_inflation_gap_chart(full_df), use_container_width=True)

        st.info(
            "**🔬 Analyst Note:** Positive inflation gap = record inflated by easy matchups. "
            "Negative = won despite tough opponents. The truth only emerges after type adjustment."
        )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 3: TYPE MATRIX
# ═══════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Type Matrix":
    st.markdown("# 🗺️ TYPE EFFECTIVENESS")
    st.markdown(
        '<p style="font-family:VT323;font-size:1.3rem;color:#A0A0B0;">'
        'The rock-paper-scissors that defines every battle.</p>',
        unsafe_allow_html=True,
    )

    chart_df = run_query(QUERY_TYPE_CHART)
    if not chart_df.empty:
        st.plotly_chart(build_type_heatmap(chart_df), use_container_width=True)

    st.markdown("---")

    st.markdown("### 🏅 Type Dominance Rankings")
    dom_df = run_query(QUERY_TYPE_DOMINANCE)
    if not dom_df.empty:
        st.plotly_chart(build_type_dominance_chart(dom_df), use_container_width=True)

        with st.expander("📊 Top 3 dominant types in Gen 1"):
            top3 = dom_df.nsmallest(3, "type_rank")
            for _, row in top3.iterrows():
                badge = type_badge(row["primary_type"])
                st.markdown(
                    f"**{badge} — Adjusted: {row['avg_type_adjusted_win_pct']}%** "
                    f"(Raw: {row['raw_type_win_pct']}%) · "
                    f"{row['pokemon_count']} Pokémon · "
                    f"{row['total_battles_as_attacker']:,} battles · "
                    f"**{row['type_verdict']}**",
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 4: BATTLE CENTER ⚔️
# ═══════════════════════════════════════════════════════════════════════════
elif page == "⚔️ Battle Center":
    st.markdown("# ⚔️ BATTLE CENTER")
    st.markdown(
        '<p style="font-family:VT323;font-size:1.3rem;color:#A0A0B0;">'
        'Choose two Pokémon. See who really wins.</p>',
        unsafe_allow_html=True,
    )

    # Get all Pokémon names
    names_df = run_query(QUERY_ALL_POKEMON_NAMES)
    if names_df.empty:
        st.warning("No Pokémon in database.")
        st.stop()

    all_names = names_df["name"].tolist()

    # ── Pokémon Selection ──
    st.markdown("---")
    col_p1, col_vs, col_p2 = st.columns([5, 2, 5])

    with col_p1:
        st.markdown("### 🔴 Player 1")
        p1_name = st.selectbox(
            "Choose your Pokémon",
            options=all_names, index=0,
            format_func=lambda n: n.title(),
            key="p1_select",
        )

    with col_vs:
        st.markdown("")
        st.markdown("")
        st.markdown(
            '<div style="text-align:center;padding-top:1rem;">'
            '<div class="vs-badge">VS</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with col_p2:
        st.markdown("### 🔵 Player 2")
        p2_name = st.selectbox(
            "Choose opponent",
            options=all_names, index=min(5, len(all_names) - 1),
            format_func=lambda n: n.title(),
            key="p2_select",
        )

    # Prevent same Pokémon
    if p1_name == p2_name:
        st.warning("⚠️ A Pokémon can't battle itself! Choose a different opponent.")
        st.stop()

    # ── Fetch both Pokémon details ──
    p1_df = run_query(QUERY_POKEMON_DETAIL, params=(p1_name,))
    p2_df = run_query(QUERY_POKEMON_DETAIL, params=(p2_name,))

    if p1_df.empty or p2_df.empty:
        st.error("Could not load Pokémon data.")
        st.stop()

    p1 = p1_df.iloc[0]
    p2 = p2_df.iloc[0]

    # ── Display Pokémon Cards ──
    st.markdown("---")
    col_card1, col_card2 = st.columns(2)

    with col_card1:
        p1_color = TYPE_COLORS.get(p1["primary_type"], "#9E9E9E")
        badges1 = type_badge(p1["primary_type"])
        if pd.notna(p1.get("secondary_type")):
            badges1 += " " + type_badge(p1["secondary_type"])

        st.markdown(
            f'<div class="pokemon-card-battle" style="border-top:3px solid {p1_color};">'
            f'<img src="{p1.get("sprite_url", "")}" width="120" '
            f'style="image-rendering:pixelated;filter:drop-shadow(0 0 10px {p1_color}40);"><br>'
            f'<span style="font-family:Press Start 2P;font-size:0.8rem;color:#F8F0E0;">'
            f'{p1["name"].title()}</span><br>'
            f'{badges1}<br>'
            f'<span style="font-family:Press Start 2P;font-size:1.2rem;color:#FFDE00;'
            f'text-shadow:0 0 10px rgba(255,222,0,0.3);">{int(p1["bst"])}</span> '
            f'<span style="font-family:VT323;color:#888;font-size:1rem;">BST</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_card2:
        p2_color = TYPE_COLORS.get(p2["primary_type"], "#9E9E9E")
        badges2 = type_badge(p2["primary_type"])
        if pd.notna(p2.get("secondary_type")):
            badges2 += " " + type_badge(p2["secondary_type"])

        st.markdown(
            f'<div class="pokemon-card-battle" style="border-top:3px solid {p2_color};">'
            f'<img src="{p2.get("sprite_url", "")}" width="120" '
            f'style="image-rendering:pixelated;filter:drop-shadow(0 0 10px {p2_color}40);"><br>'
            f'<span style="font-family:Press Start 2P;font-size:0.8rem;color:#F8F0E0;">'
            f'{p2["name"].title()}</span><br>'
            f'{badges2}<br>'
            f'<span style="font-family:Press Start 2P;font-size:1.2rem;color:#FFDE00;'
            f'text-shadow:0 0 10px rgba(255,222,0,0.3);">{int(p2["bst"])}</span> '
            f'<span style="font-family:VT323;color:#888;font-size:1rem;">BST</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── BATTLE BUTTON ──
    st.markdown("")
    _, btn_col, _ = st.columns([3, 2, 3])
    with btn_col:
        battle_pressed = st.button("⚔️  BATTLE!", use_container_width=True)

    if battle_pressed:
        st.markdown("---")

        # ── 1. Win Probability Calculation ──
        # Get type effectiveness both ways
        eff_1v2 = run_query(QUERY_TYPE_EFFECTIVENESS, params=(p1["primary_type"], p2["primary_type"]))
        eff_2v1 = run_query(QUERY_TYPE_EFFECTIVENESS, params=(p2["primary_type"], p1["primary_type"]))

        mult_1v2 = float(eff_1v2.iloc[0]["multiplier"]) if not eff_1v2.empty else 1.0
        mult_2v1 = float(eff_2v1.iloc[0]["multiplier"]) if not eff_2v1.empty else 1.0

        # Win probability using BST × type multiplier
        adj_bst_1 = int(p1["bst"]) * mult_1v2
        adj_bst_2 = int(p2["bst"]) * mult_2v1
        p1_win_prob = adj_bst_1 / (adj_bst_1 + adj_bst_2) if (adj_bst_1 + adj_bst_2) > 0 else 0.5
        p2_win_prob = 1 - p1_win_prob

        predicted_winner = p1_name if p1_win_prob >= p2_win_prob else p2_name
        winner_prob = max(p1_win_prob, p2_win_prob)

        # ── Results Header ──
        st.markdown(
            f'<div class="result-card">'
            f'<span style="font-family:Press Start 2P;font-size:0.6rem;color:#A0A0B0;'
            f'letter-spacing:2px;">PREDICTED WINNER</span><br>'
            f'<span style="font-family:Press Start 2P;font-size:1.2rem;color:#FFDE00;'
            f'text-shadow:0 0 15px rgba(255,222,0,0.4);">'
            f'🏆 {predicted_winner.title()}</span><br>'
            f'<span style="font-family:VT323;font-size:1.3rem;color:#F8F0E0;">'
            f'Win Probability: {winner_prob * 100:.1f}%</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown("")

        # ── 2. Win Probability Bars ──
        col_prob1, col_prob2 = st.columns(2)

        with col_prob1:
            hp_class = "high" if p1_win_prob >= 0.5 else ("mid" if p1_win_prob >= 0.3 else "low")
            st.markdown(
                f'<div style="text-align:center;font-family:VT323;font-size:1.1rem;color:#F8F0E0;">'
                f'{p1_name.title()} — {p1_win_prob * 100:.1f}%</div>'
                f'<div class="hp-bar-container">'
                f'<div class="hp-bar-fill {hp_class}" style="width:{p1_win_prob * 100:.1f}%;"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col_prob2:
            hp_class = "high" if p2_win_prob >= 0.5 else ("mid" if p2_win_prob >= 0.3 else "low")
            st.markdown(
                f'<div style="text-align:center;font-family:VT323;font-size:1.1rem;color:#F8F0E0;">'
                f'{p2_name.title()} — {p2_win_prob * 100:.1f}%</div>'
                f'<div class="hp-bar-container">'
                f'<div class="hp-bar-fill {hp_class}" style="width:{p2_win_prob * 100:.1f}%;"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # ── 3. Type Matchup ──
        st.markdown("### 🎯 Type Matchup")
        col_tm1, col_tm2 = st.columns(2)

        with col_tm1:
            eff_label = eff_1v2.iloc[0]["effectiveness_label"] if not eff_1v2.empty else "normal"
            st.markdown(
                f'<div class="glass-card">'
                f'<span style="font-family:VT323;font-size:1.1rem;color:#A0A0B0;">'
                f'{p1_name.title()} → {p2_name.title()}</span><br>'
                f'{effectiveness_label(mult_1v2)}'
                f'</div>',
                unsafe_allow_html=True,
            )

        with col_tm2:
            eff_label2 = eff_2v1.iloc[0]["effectiveness_label"] if not eff_2v1.empty else "normal"
            st.markdown(
                f'<div class="glass-card">'
                f'<span style="font-family:VT323;font-size:1.1rem;color:#A0A0B0;">'
                f'{p2_name.title()} → {p1_name.title()}</span><br>'
                f'{effectiveness_label(mult_2v1)}'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── 4. Stat Comparison Charts ──
        st.markdown("### 📊 Stat Comparison")
        tab_bars, tab_radar = st.tabs(["📊 Bar Comparison", "🕸️ Radar Overlay"])

        with tab_bars:
            fig_bars = build_stat_comparison_chart(p1, p2, p1_name, p2_name)
            st.plotly_chart(fig_bars, use_container_width=True)

        with tab_radar:
            fig_radar = build_dual_radar(p1, p2, p1_name, p2_name)
            st.plotly_chart(fig_radar, use_container_width=True)

        # ── 5. Moves ──
        st.markdown("### ⚡ Learnable Moves")
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown(f"**{p1_name.title()}**")
            moves1 = fetch_pokemon_moves(p1_name)
            if moves1:
                for mv in moves1:
                    st.markdown(
                        f'<div class="move-item">'
                        f'<span>{mv["name"]}</span>'
                        f'<span class="move-power">Lv.{mv["level"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Could not fetch moves.")

        with col_m2:
            st.markdown(f"**{p2_name.title()}**")
            moves2 = fetch_pokemon_moves(p2_name)
            if moves2:
                for mv in moves2:
                    st.markdown(
                        f'<div class="move-item">'
                        f'<span>{mv["name"]}</span>'
                        f'<span class="move-power">Lv.{mv["level"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info("Could not fetch moves.")

        # ── 6. Battle History ──
        st.markdown("### 📜 Battle History")
        history = run_query(
            QUERY_BATTLE_HISTORY,
            params=(p1_name, p2_name, p2_name, p1_name),
        )
        if not history.empty:
            # Count wins
            p1_hist_wins = ((history["winner_name"] == p1_name)).sum()
            p2_hist_wins = ((history["winner_name"] == p2_name)).sum()
            st.markdown(
                f'<div class="glass-card" style="text-align:center;">'
                f'<span style="font-family:VT323;font-size:1.2rem;color:#F8F0E0;">'
                f'Historical Record: '
                f'<span style="color:{p1_color};font-weight:700;">{p1_name.title()} {p1_hist_wins}W</span>'
                f' — '
                f'<span style="color:{p2_color};font-weight:700;">{p2_hist_wins}W {p2_name.title()}</span>'
                f'</span></div>',
                unsafe_allow_html=True,
            )
            st.dataframe(history, use_container_width=True, hide_index=True)
        else:
            st.info("No direct battles found between these two Pokémon in our simulation data.")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 5: POKÉDEX LOOKUP
# ═══════════════════════════════════════════════════════════════════════════
elif page == "📖 Pokédex Lookup":
    st.markdown("# 📖 POKÉDEX")
    st.markdown(
        '<p style="font-family:VT323;font-size:1.3rem;color:#A0A0B0;">'
        'Tap a Pokémon to view its Pokédex entry.</p>',
        unsafe_allow_html=True,
    )

    names_df = run_query(QUERY_ALL_POKEMON_NAMES)
    if names_df.empty:
        st.warning("No Pokémon found.")
        st.stop()

    all_names = names_df["name"].tolist()
    selected = st.selectbox(
        "Select a Pokémon",
        options=all_names, index=0,
        format_func=lambda n: f"#{all_names.index(n)+1:03d} {n.title()}",
    )

    if selected:
        detail_df = run_query(QUERY_POKEMON_DETAIL, params=(selected,))

        if not detail_df.empty:
            row = detail_df.iloc[0]
            ptype_color = TYPE_COLORS.get(row["primary_type"], "#9E9E9E")

            col_info, col_radar = st.columns([1, 2])

            with col_info:
                sprite_url = row.get("sprite_url", "")
                if sprite_url:
                    st.markdown(
                        f'<div style="text-align:center;padding:1rem;">'
                        f'<img src="{sprite_url}" width="160" '
                        f'style="image-rendering:pixelated;'
                        f'filter:drop-shadow(0 0 15px {ptype_color}50);">'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    f'<div style="text-align:center;">'
                    f'<span style="font-family:VT323;color:#888;font-size:1.2rem;">'
                    f'#{int(row["id"]):03d}</span><br>'
                    f'<span style="font-family:Press Start 2P;font-size:0.9rem;color:#F8F0E0;">'
                    f'{row["name"].title()}</span></div>',
                    unsafe_allow_html=True,
                )

                badges = type_badge(row["primary_type"])
                if pd.notna(row.get("secondary_type")):
                    badges += " " + type_badge(row["secondary_type"])
                st.markdown(
                    f'<div style="text-align:center;margin:0.5rem 0;">{badges}</div>',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f'<div style="text-align:center;">'
                    f'<span style="font-family:Press Start 2P;font-size:1.5rem;color:#FFDE00;'
                    f'text-shadow:0 0 12px rgba(255,222,0,0.3);">{int(row["bst"])}</span><br>'
                    f'<span style="font-family:VT323;color:#888;font-size:1rem;'
                    f'text-transform:uppercase;letter-spacing:2px;">Base Stat Total</span></div>',
                    unsafe_allow_html=True,
                )

            with col_radar:
                fig = build_pokemon_radar(detail_df, selected)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")

            # Battle performance
            adj_df = run_query(QUERY_ADJUSTED_WIN_RATE.format(min_battles=min_battles))
            poke_stats = adj_df[adj_df["pokemon_name"] == selected]

            if not poke_stats.empty:
                ps = poke_stats.iloc[0]
                st.markdown("### ⚔️ Battle Performance")

                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Raw Win %", f"{ps['raw_win_pct']}%")
                    st.metric("Adjusted Win %", f"{ps['adjusted_win_pct']}%",
                              delta=f"{-ps['inflation_gap']:+.1f}pp" if ps['inflation_gap'] != 0 else "0")
                with m2:
                    st.metric("Rank in Type", int(ps["rank_in_type"]))
                    st.metric("Percentile", f"{ps['overall_percentile']}%")
                with m3:
                    st.metric("Total Battles", int(ps["total_battles"]))
                    st.metric("Analyst Tag", ps["analyst_tag"])
            else:
                st.info(
                    f"{selected.title()} has too few battles (min: {min_battles}) "
                    f"to compute adjusted statistics."
                )

            # Moves
            st.markdown("### ⚡ Learnable Moves")
            moves = fetch_pokemon_moves(selected)
            if moves:
                mcols = st.columns(2)
                for i, mv in enumerate(moves):
                    with mcols[i % 2]:
                        st.markdown(
                            f'<div class="move-item">'
                            f'<span>{mv["name"]}</span>'
                            f'<span class="move-power">Lv.{mv["level"]}</span>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            # Recent battles
            with st.expander(f"📋 Recent battles ({selected.title()})"):
                battles_df = run_query(QUERY_POKEMON_BATTLES, params=(selected, selected))
                if not battles_df.empty:
                    st.dataframe(battles_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No battle records found.")
