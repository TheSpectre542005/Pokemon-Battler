"""
charts.py — Plotly Chart Builder Functions

Every function takes a Pandas DataFrame (or subset) and returns a fully
configured Plotly figure styled for the dark-themed Streamlit dashboard.

Design contract:
- Background: #0F0F1A (dark navy)
- Font colour: white
- All axes labelled; all charts titled
- No default Plotly watermarks
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# Canonical colour mapping for all 18 Pokémon types.
# Colours chosen for readability on dark backgrounds and WCAG contrast.
TYPE_COLORS: dict[str, str] = {
    "fire": "#FF4500",
    "water": "#2196F3",
    "grass": "#4CAF50",
    "electric": "#FFD600",
    "psychic": "#E91E63",
    "dragon": "#7B1FA2",
    "normal": "#9E9E9E",
    "ice": "#00BCD4",
    "fighting": "#B71C1C",
    "poison": "#9C27B0",
    "ground": "#795548",
    "flying": "#03A9F4",
    "bug": "#8BC34A",
    "rock": "#607D8B",
    "ghost": "#311B92",
    "dark": "#212121",
    "steel": "#78909C",
    "fairy": "#F48FB1",
}

# Shared layout defaults applied to every chart
_LAYOUT_DEFAULTS = dict(
    paper_bgcolor="#0F0F1A",
    plot_bgcolor="#0F0F1A",
    font=dict(color="white", family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=60, b=20),
)


def _apply_defaults(fig: go.Figure) -> go.Figure:
    """Apply shared dark-theme styling to any Plotly figure."""
    fig.update_layout(**_LAYOUT_DEFAULTS)
    return fig


# ───────────────────────────────────────────────────────────────────────────
# Function 1: Adjusted Win Rate Leaderboard
# ───────────────────────────────────────────────────────────────────────────
def build_leaderboard_chart(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart of adjusted win rates with raw win rate overlay.

    Args:
        df: DataFrame with columns [pokemon_name, primary_type,
            adjusted_win_pct, raw_win_pct].

    Returns:
        Plotly Figure with dual-encoding: bars (adjusted) + dots (raw).
    """
    # Sort and limit to top 30
    df = df.nlargest(30, "adjusted_win_pct").sort_values("adjusted_win_pct")

    # Map each Pokémon's type to its colour
    bar_colors = [TYPE_COLORS.get(t, "#9E9E9E") for t in df["primary_type"]]

    fig = go.Figure()

    # Primary bars — adjusted win rate
    fig.add_trace(go.Bar(
        x=df["adjusted_win_pct"],
        y=df["pokemon_name"],
        orientation="h",
        marker=dict(color=bar_colors, line=dict(width=0)),
        name="Adjusted Win %",
        text=df["adjusted_win_pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        textfont=dict(size=10),
    ))

    # Overlay dots — raw win rate (grey) to show the adjustment gap
    fig.add_trace(go.Scatter(
        x=df["raw_win_pct"],
        y=df["pokemon_name"],
        mode="markers",
        marker=dict(color="#888888", size=8, symbol="circle"),
        name="● Raw Win %",
    ))

    fig.update_layout(
        title="Adjusted Win Rate Leaderboard (Top 30)",
        xaxis_title="Win Rate (%)",
        yaxis_title="",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=max(500, len(df) * 22),
        bargap=0.15,
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")

    return _apply_defaults(fig)


# ───────────────────────────────────────────────────────────────────────────
# Function 2: Inflation Gap (Diverging Bar Chart)
# ───────────────────────────────────────────────────────────────────────────
def build_inflation_gap_chart(df: pd.DataFrame) -> go.Figure:
    """
    Diverging horizontal bar chart showing raw-vs-adjusted gap.

    Positive gap = overrated (red), negative = underrated (green).

    Args:
        df: DataFrame with columns [pokemon_name, inflation_gap].

    Returns:
        Plotly Figure with colour-coded diverging bars.
    """
    # Filter to Pokémon with meaningful gap only
    df = df[df["inflation_gap"].abs() > 2].copy()
    df = df.sort_values("inflation_gap", ascending=True)

    colors = ["#E63946" if g > 0 else "#4CAF50" for g in df["inflation_gap"]]

    fig = go.Figure(go.Bar(
        x=df["inflation_gap"],
        y=df["pokemon_name"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=df["inflation_gap"].apply(lambda v: f"{v:+.1f}"),
        textposition="outside",
        textfont=dict(size=10),
    ))

    fig.update_layout(
        title="The Truth Gap — Raw vs. Adjusted Win Rate",
        xaxis_title="Inflation Gap (pp)",
        yaxis_title="",
        height=max(400, len(df) * 22),
    )

    # Subtitle annotation
    fig.add_annotation(
        text="Positive = overrated by type advantage | Negative = underrated despite type disadvantage",
        xref="paper", yref="paper", x=0.5, y=1.06,
        showarrow=False, font=dict(size=11, color="#AAAAAA"),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=True, zerolinecolor="#555")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")

    return _apply_defaults(fig)


# ───────────────────────────────────────────────────────────────────────────
# Function 3: Type Effectiveness Heatmap
# ───────────────────────────────────────────────────────────────────────────
def build_type_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    18×18 heatmap of type effectiveness multipliers.

    Args:
        df: DataFrame with columns [attacking_type, defending_type, multiplier].

    Returns:
        Plotly Figure with annotated heatmap cells (0, 0.5, 1, 2).
    """
    # Pivot into matrix form
    pivot = df.pivot(index="attacking_type", columns="defending_type", values="multiplier")

    # Canonical type ordering
    types_order = [
        "normal", "fire", "water", "electric", "grass", "ice",
        "fighting", "poison", "ground", "flying", "psychic", "bug",
        "rock", "ghost", "dragon", "dark", "steel", "fairy",
    ]
    # Reindex to canonical order (if all types present)
    available = [t for t in types_order if t in pivot.index]
    pivot = pivot.reindex(index=available, columns=available)

    z_vals = pivot.values.tolist()

    # Build annotation text matrix
    annotations = []
    for i, row_type in enumerate(available):
        for j, col_type in enumerate(available):
            val = pivot.iloc[i, j]
            annotations.append(dict(
                x=col_type, y=row_type,
                text=str(val) if val != 1.0 else "",
                showarrow=False,
                font=dict(color="white" if val != 1.0 else "rgba(255,255,255,0.2)", size=9),
            ))

    fig = go.Figure(go.Heatmap(
        z=z_vals,
        x=available,
        y=available,
        colorscale=[[0, "#212121"], [0.25, "#555555"], [0.5, "#F5F5F5"], [1, "#E63946"]],
        zmin=0, zmax=2,
        colorbar=dict(title="Multiplier", tickvals=[0, 0.5, 1, 2]),
        hovertemplate="Atk: %{y}<br>Def: %{x}<br>Mult: %{z}<extra></extra>",
    ))

    fig.update_layout(
        title="Type Effectiveness Matrix",
        xaxis_title="Defender Type",
        yaxis_title="Attacker Type",
        height=600,
        annotations=annotations,
    )
    fig.update_xaxes(side="top", tickangle=-45)

    return _apply_defaults(fig)


# ───────────────────────────────────────────────────────────────────────────
# Function 4: Type Dominance (Grouped Bar Chart)
# ───────────────────────────────────────────────────────────────────────────
def build_type_dominance_chart(df: pd.DataFrame) -> go.Figure:
    """
    Grouped bar chart: raw vs. adjusted win rate per type with 50% reference.

    Args:
        df: DataFrame with columns [primary_type, raw_type_win_pct,
            avg_type_adjusted_win_pct, type_verdict].

    Returns:
        Plotly Figure with grouped bars and coin-flip reference line.
    """
    df = df.sort_values("avg_type_adjusted_win_pct", ascending=False)

    verdict_colors = {
        "DOMINANT": "#E63946",
        "STRONG": "#FFD600",
        "BALANCED": "#4CAF50",
        "WEAK": "#607D8B",
    }
    adj_colors = [verdict_colors.get(v, "#9E9E9E") for v in df["type_verdict"]]

    fig = go.Figure()

    # Raw win rate bars (grey baseline)
    fig.add_trace(go.Bar(
        x=df["primary_type"],
        y=df["raw_type_win_pct"],
        name="Raw Win %",
        marker=dict(color="#555555"),
    ))

    # Adjusted win rate bars (coloured by verdict)
    fig.add_trace(go.Bar(
        x=df["primary_type"],
        y=df["avg_type_adjusted_win_pct"],
        name="Adjusted Win %",
        marker=dict(color=adj_colors),
    ))

    # 50% coin-flip reference line
    fig.add_hline(
        y=50, line_dash="dash", line_color="#AAAAAA",
        annotation_text="50% = coin flip",
        annotation_position="top right",
        annotation_font=dict(color="#AAAAAA", size=10),
    )

    fig.update_layout(
        title="Type Dominance — Raw vs. Adjusted",
        xaxis_title="Type",
        yaxis_title="Win Rate (%)",
        barmode="group",
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(tickangle=-45, gridcolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)")

    return _apply_defaults(fig)


# ───────────────────────────────────────────────────────────────────────────
# Function 5: Pokémon Radar / Spider Chart
# ───────────────────────────────────────────────────────────────────────────
def build_pokemon_radar(df: pd.DataFrame, pokemon_name: str) -> go.Figure:
    """
    Radar chart for a single Pokémon's base stats (HP through Speed).

    Stats are normalised to 0–100 scale where 255 (Gen 1 HP cap) = 100.

    Args:
        df: Single-row DataFrame with columns [hp, attack, defense,
            sp_atk, sp_def, speed, primary_type].
        pokemon_name: Display name for the chart title.

    Returns:
        Plotly Figure with filled radar polygon.
    """
    row = df.iloc[0]
    max_stat = 255  # Theoretical Gen 1 maximum (Chansey HP)

    categories = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
    raw_values = [row["hp"], row["attack"], row["defense"],
                  row["sp_atk"], row["sp_def"], row["speed"]]
    normalised = [round(v / max_stat * 100, 1) for v in raw_values]

    # Close the polygon by repeating the first value
    normalised.append(normalised[0])
    categories.append(categories[0])

    ptype = row.get("primary_type", "normal")
    fill_color = TYPE_COLORS.get(ptype, "#9E9E9E")

    # Convert hex to rgba with 40% opacity for the fill
    hex_color = fill_color.lstrip("#")
    rc, gc, bc = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    fill_rgba = f"rgba({rc},{gc},{bc},0.4)"

    fig = go.Figure(go.Scatterpolar(
        r=normalised,
        theta=categories,
        fill="toself",
        fillcolor=fill_rgba,
        line=dict(color=fill_color, width=2),
        name=pokemon_name.title(),
    ))

    fig.update_layout(
        title=f"Base Stats — {pokemon_name.title()}",
        polar=dict(
            bgcolor="#0F0F1A",
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor="rgba(255,255,255,0.1)",
                tickfont=dict(size=9),
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.1)",
                tickfont=dict(size=11),
            ),
        ),
        height=400,
        showlegend=False,
    )

    return _apply_defaults(fig)


# ───────────────────────────────────────────────────────────────────────────
# Function 6: Stat Comparison (Battle Center)
# ───────────────────────────────────────────────────────────────────────────
def build_stat_comparison_chart(
    p1: pd.Series, p2: pd.Series, name1: str, name2: str
) -> go.Figure:
    """
    Horizontal diverging bar chart comparing two Pokémon's stats.

    Left bars = Player 1, Right bars = Player 2.

    Args:
        p1: Series with stat columns for Pokémon 1.
        p2: Series with stat columns for Pokémon 2.
        name1: Display name for Pokémon 1.
        name2: Display name for Pokémon 2.

    Returns:
        Plotly Figure with mirrored horizontal bars.
    """
    stats = ["hp", "attack", "defense", "sp_atk", "sp_def", "speed"]
    labels = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]

    vals1 = [int(p1[s]) for s in stats]
    vals2 = [int(p2[s]) for s in stats]

    type1 = p1.get("primary_type", "normal")
    type2 = p2.get("primary_type", "normal")
    color1 = TYPE_COLORS.get(type1, "#9E9E9E")
    color2 = TYPE_COLORS.get(type2, "#9E9E9E")

    fig = go.Figure()

    # Pokémon 1 bars (negative direction for mirror effect)
    fig.add_trace(go.Bar(
        y=labels,
        x=[-v for v in vals1],
        orientation="h",
        name=name1.title(),
        marker=dict(color=color1),
        text=[str(v) for v in vals1],
        textposition="inside",
        textfont=dict(size=12, family="Press Start 2P"),
        insidetextanchor="end",
    ))

    # Pokémon 2 bars (positive direction)
    fig.add_trace(go.Bar(
        y=labels,
        x=vals2,
        orientation="h",
        name=name2.title(),
        marker=dict(color=color2),
        text=[str(v) for v in vals2],
        textposition="inside",
        textfont=dict(size=12, family="Press Start 2P"),
        insidetextanchor="start",
    ))

    fig.update_layout(
        title=f"{name1.title()} vs {name2.title()} — Stat Comparison",
        barmode="overlay",
        bargap=0.25,
        height=350,
        xaxis=dict(
            zeroline=True,
            zerolinecolor="rgba(255,222,0,0.3)",
            zerolinewidth=2,
            showticklabels=False,
            gridcolor="rgba(255,255,255,0.03)",
        ),
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.05)",
            tickfont=dict(size=12, family="VT323"),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="center", x=0.5, font=dict(family="VT323", size=14),
        ),
    )

    return _apply_defaults(fig)


# ───────────────────────────────────────────────────────────────────────────
# Function 7: Dual Radar Chart (Battle Center)
# ───────────────────────────────────────────────────────────────────────────
def build_dual_radar(
    p1: pd.Series, p2: pd.Series, name1: str, name2: str
) -> go.Figure:
    """
    Overlaid radar chart comparing two Pokémon's base stats.

    Args:
        p1: Series with stat columns for Pokémon 1.
        p2: Series with stat columns for Pokémon 2.
        name1: Display name for Pokémon 1.
        name2: Display name for Pokémon 2.

    Returns:
        Plotly Figure with two overlapping radar polygons.
    """
    max_stat = 255
    categories = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
    stats_keys = ["hp", "attack", "defense", "sp_atk", "sp_def", "speed"]

    vals1 = [round(int(p1[s]) / max_stat * 100, 1) for s in stats_keys]
    vals2 = [round(int(p2[s]) / max_stat * 100, 1) for s in stats_keys]

    # Close polygons
    vals1.append(vals1[0])
    vals2.append(vals2[0])
    cats = categories + [categories[0]]

    type1 = p1.get("primary_type", "normal")
    type2 = p2.get("primary_type", "normal")
    color1 = TYPE_COLORS.get(type1, "#9E9E9E")
    color2 = TYPE_COLORS.get(type2, "#9E9E9E")

    hex1 = color1.lstrip("#")
    r1, g1, b1 = int(hex1[:2], 16), int(hex1[2:4], 16), int(hex1[4:6], 16)
    hex2 = color2.lstrip("#")
    r2, g2, b2 = int(hex2[:2], 16), int(hex2[2:4], 16), int(hex2[4:6], 16)

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=vals1, theta=cats, fill="toself",
        fillcolor=f"rgba({r1},{g1},{b1},0.3)",
        line=dict(color=color1, width=2),
        name=name1.title(),
    ))

    fig.add_trace(go.Scatterpolar(
        r=vals2, theta=cats, fill="toself",
        fillcolor=f"rgba({r2},{g2},{b2},0.3)",
        line=dict(color=color2, width=2),
        name=name2.title(),
    ))

    fig.update_layout(
        title="Stat Overlay Comparison",
        polar=dict(
            bgcolor="#0F0F1A",
            radialaxis=dict(
                visible=True, range=[0, 100],
                gridcolor="rgba(255,255,255,0.08)",
                tickfont=dict(size=9),
            ),
            angularaxis=dict(
                gridcolor="rgba(255,255,255,0.08)",
                tickfont=dict(size=11, family="VT323"),
            ),
        ),
        height=400,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="center", x=0.5, font=dict(family="VT323", size=14),
        ),
    )

    return _apply_defaults(fig)

