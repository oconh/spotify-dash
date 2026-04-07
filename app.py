import os
import dash
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from dotenv import load_dotenv
from spotify_client import (
    get_spotify_client, get_spotify_oauth,
    get_top_tracks, get_top_artists,
    get_audio_features, get_currently_playing,
    get_genres_from_artists,
)

load_dotenv()


# Auth
def ensure_authenticated():
    oauth = get_spotify_oauth()
    if not oauth.get_cached_token():
        auth_url = oauth.get_authorize_url()
        print("\n" + "="*60)
        print("SPOTIFY AUTH REQUIRED")
        print("="*60)
        print(f"\nOpen this URL in your browser:\n\n  {auth_url}\n")
        print("After authorising, paste the full redirect URL here:")
        code = oauth.parse_response_code(input("> ").strip())
        oauth.get_access_token(code)
        print("\nAuthenticated! Starting dashboard...\n")


ensure_authenticated()
sp = get_spotify_client()


# Colours & theme
COLORS = {
    "bg":      "#0a0a0f",
    "surface": "#12121a",
    "card":    "#1a1a26",
    "border":  "#2a2a3d",
    "accent":  "#1DB954",
    "accent2": "#9b5de5",
    "accent3": "#f15bb5",
    "text":    "#ffffff",
    "muted":   "#a0a0b8",
}

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=COLORS["text"], family="'DM Sans', sans-serif"),
    colorway=[COLORS["accent"], COLORS["accent2"], COLORS["accent3"]],
    margin=dict(l=20, r=20, t=40, b=20),
)

TIME_RANGES = {
    "short_term":  "Last 4 weeks",
    "medium_term": "Last 6 months",
    "long_term":   "All time",
}


# Reusable components
def card(children, style=None):
    base = {
        "background": COLORS["card"],
        "border": f"1px solid {COLORS['border']}",
        "borderRadius": "16px",
        "padding": "1.5rem",
    }
    if style:
        base.update(style)
    return html.Div(children, style=base)


def stat_card(label, value, colour=None):
    return card([
        html.P(label, style={
            "color": COLORS["muted"], "fontSize": "12px",
            "textTransform": "uppercase", "letterSpacing": "0.08em",
            "marginBottom": "0.4rem",
        }),
        html.P(str(value), style={
            "color": colour or COLORS["accent"],
            "fontSize": "2rem", "fontWeight": "700", "margin": 0,
        }),
    ])


# App init
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    title="Spotify Dashboard",
)


# Sidebar
SIDEBAR = html.Div([
    html.Div([
        html.Span("◆", style={"color": COLORS["accent"], "fontSize": "1.4rem"}),
        html.Span(" Spotify", style={"fontWeight": "700"}),
        html.Span(".dash", style={"color": COLORS["accent"], "fontWeight": "300"}),
    ], style={"marginBottom": "2.5rem"}),

    html.P("NAVIGATION", style={
        "color": COLORS["muted"], "fontSize": "10px",
        "letterSpacing": "0.12em", "marginBottom": "0.75rem",
    }),

    *[
        html.Div(
            dcc.Link(label, href=href, style={
                "color": COLORS["muted"], "textDecoration": "none", "fontSize": "14px",
            }),
            style={"padding": "0.6rem 1rem", "borderRadius": "10px", "marginBottom": "4px"},
        )
        for href, label in [
            ("/",            "🎵  Now Playing"),
            ("/top-tracks",  "📈  Top Tracks"),
            ("/top-artists", "🎤  Top Artists"),
            ("/audio-dna",   "🧬  Audio DNA"),
            ("/genres",      "🗺  Genres"),
        ]
    ],

    html.Hr(style={"borderColor": COLORS["border"], "margin": "1.5rem 0"}),

    html.P("TIME RANGE", style={
        "color": COLORS["muted"], "fontSize": "10px",
        "letterSpacing": "0.12em", "marginBottom": "0.75rem",
    }),
    dcc.RadioItems(
        id="time-range",
        options=[{"label": v, "value": k} for k, v in TIME_RANGES.items()],
        value="medium_term",
        labelStyle={
            "display": "block", "marginBottom": "8px",
            "fontSize": "13px", "color": COLORS["muted"], "cursor": "pointer",
        },
        inputStyle={"marginRight": "8px", "accentColor": COLORS["accent"]},
    ),
], style={
    "width": "220px",
    "minHeight": "100vh",
    "background": COLORS["surface"],
    "padding": "1.5rem 1rem",
    "borderRight": f"1px solid {COLORS['border']}",
    "position": "fixed",
    "top": 0,
    "left": 0,
    "fontFamily": "'DM Sans', sans-serif",
})


# Layout
app.layout = html.Div([
    dcc.Location(id="url"),
    dcc.Interval(id="now-playing-interval", interval=10_000, n_intervals=0),
    SIDEBAR,
    html.Div(id="page-content", style={
        "marginLeft": "220px",
        "padding": "2rem 2.5rem",
        "fontFamily": "'DM Sans', sans-serif",
        "color": COLORS["text"],
        "minHeight": "100vh",
    }),
], style={"background": COLORS["bg"], "minHeight": "100vh"})


# Pages
def page_now_playing(n):
    now = get_currently_playing(sp)

    if not now:
        return card([
            html.P("Nothing playing right now.", style={"color": COLORS["muted"]}),
            html.P("Start Spotify then this will auto-refresh.",
                   style={"color": COLORS["muted"], "fontSize": "13px"}),
        ])

    progress_pct = (now["progress_ms"] / now["duration_ms"]) * 100
    fmt = lambda ms: f"{ms // 60000}:{(ms // 1000) % 60:02d}"

    return html.Div([
        html.H2("Now Playing", style={"marginBottom": "1.5rem", "fontWeight": "700"}),
        card([
            html.Div([
                html.Img(src=now["image"], style={
                    "width": "140px", "height": "140px",
                    "borderRadius": "12px", "objectFit": "cover",
                }) if now["image"] else html.Div(style={
                    "width": "140px", "height": "140px",
                    "borderRadius": "12px", "background": COLORS["border"],
                }),
                html.Div([
                    html.P(
                        "▶  PLAYING" if now["is_playing"] else "⏸  PAUSED",
                        style={"color": COLORS["accent"], "fontSize": "11px",
                               "letterSpacing": "0.1em", "marginBottom": "0.5rem"},
                    ),
                    html.H3(now["name"], style={"fontWeight": "700", "fontSize": "1.5rem",
                                                "marginBottom": "0.3rem"}),
                    html.P(now["artist"], style={"color": COLORS["muted"],
                                                  "marginBottom": "0.2rem"}),
                    html.P(now["album"], style={"color": COLORS["muted"], "fontSize": "13px"}),
                    html.Div([
                        html.Div(
                            style={"height": "4px", "borderRadius": "2px",
                                   "background": COLORS["border"], "marginTop": "1.5rem"},
                            children=[html.Div(style={
                                "height": "4px", "borderRadius": "2px",
                                "background": COLORS["accent"],
                                "width": f"{progress_pct:.1f}%",
                            })],
                        ),
                        html.Div([
                            html.Span(fmt(now["progress_ms"]),
                                      style={"color": COLORS["muted"], "fontSize": "12px"}),
                            html.Span(fmt(now["duration_ms"]),
                                      style={"color": COLORS["muted"], "fontSize": "12px"}),
                        ], style={"display": "flex", "justifyContent": "space-between",
                                  "marginTop": "4px"}),
                    ]),
                ], style={"flex": 1}),
            ], style={"display": "flex", "gap": "2rem", "alignItems": "flex-start"}),
        ]),
    ])


def page_top_tracks(time_range):
    tracks = get_top_tracks(sp, time_range)
    df = pd.DataFrame(tracks)

    fig = go.Figure(go.Bar(
        x=df["popularity"],
        y=[f"{i+1}. {n}" for i, n in enumerate(df["name"])],
        orientation="h",
        marker_color=COLORS["accent"],
        marker_opacity=0.85,
        text=df["artist"],
        textposition="inside",
        textfont=dict(color="white", size=11),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Top Tracks by Popularity",
        yaxis=dict(autorange="reversed", gridcolor=COLORS["border"], tickfont=dict(size=11)),
        height=max(400, len(df) * 22),
        showlegend=False,
    )

    top3 = df.head(3)

    return html.Div([
        html.H2("Top Tracks", style={"marginBottom": "0.5rem", "fontWeight": "700"}),
        html.P(TIME_RANGES[time_range], style={"color": COLORS["muted"], "marginBottom": "1.5rem"}),
        html.Div([
            stat_card("Total tracks", len(df)),
            stat_card("Avg popularity", f"{df['popularity'].mean():.0f}"),
            stat_card("With preview", df["preview_url"].notna().sum(), COLORS["accent2"]),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)",
                  "gap": "1rem", "marginBottom": "1.5rem"}),
        card([dcc.Graph(figure=fig, config={"displayModeBar": False})]),
        html.H3("Top 3", style={"margin": "1.5rem 0 1rem", "fontWeight": "600"}),
        html.Div([
            card([
                html.Img(src=row["image"], style={
                    "width": "100%", "borderRadius": "10px", "marginBottom": "0.75rem",
                }) if row["image"] else None,
                html.P(f"#{i+1}", style={"color": COLORS["accent"], "fontSize": "12px",
                                          "fontWeight": "700", "marginBottom": "4px"}),
                html.P(row["name"], style={"fontWeight": "600", "marginBottom": "2px",
                                            "fontSize": "14px"}),
                html.P(row["artist"], style={"color": COLORS["muted"], "fontSize": "12px"}),
            ])
            for i, (_, row) in enumerate(top3.iterrows())
        ], style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)", "gap": "1rem"}),
    ])


def page_top_artists(time_range):
    artists = get_top_artists(sp, time_range)
    df = pd.DataFrame(artists)

    fig = px.scatter(
        df, x=df.index + 1, y="popularity",
        size="followers", hover_name="name",
        color="popularity",
        color_continuous_scale=["#1DB954", "#9b5de5", "#f15bb5"],
        size_max=50,
    )
    fig.update_traces(marker=dict(line=dict(width=0)))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title="Artist Popularity vs Your Ranking",
        xaxis_title="Your Rank",
        yaxis_title="Spotify Popularity",
        coloraxis_showscale=False,
        height=380,
    )

    return html.Div([
        html.H2("Top Artists", style={"marginBottom": "0.5rem", "fontWeight": "700"}),
        html.P(TIME_RANGES[time_range], style={"color": COLORS["muted"], "marginBottom": "1.5rem"}),
        html.Div([
            stat_card("Artists", len(df)),
            stat_card("Avg popularity", f"{df['popularity'].mean():.0f}"),
            stat_card("Total followers", f"{df['followers'].sum():,}", COLORS["accent3"]),
        ], style={"display": "grid", "gridTemplateColumns": "repeat(3,1fr)",
                  "gap": "1rem", "marginBottom": "1.5rem"}),
        card([dcc.Graph(figure=fig, config={"displayModeBar": False})]),
        html.H3("Top 10", style={"margin": "1.5rem 0 1rem", "fontWeight": "600"}),
        html.Div([
            card([
                html.Div([
                    html.Img(src=row["image"], style={
                        "width": "48px", "height": "48px",
                        "borderRadius": "50%", "objectFit": "cover",
                    }) if row["image"] else html.Div(style={
                        "width": "48px", "height": "48px",
                        "borderRadius": "50%", "background": COLORS["border"],
                    }),
                    html.Div([
                        html.P(f"#{i+1}  {row['name']}",
                               style={"fontWeight": "600", "fontSize": "13px", "margin": 0}),
                        html.P(f"Popularity {row['popularity']}",
                               style={"color": COLORS["muted"], "fontSize": "11px", "margin": 0}),
                    ]),
                ], style={"display": "flex", "gap": "12px", "alignItems": "center"}),
            ], style={"padding": "0.75rem 1rem"})
            for i, (_, row) in enumerate(df.head(10).iterrows())
        ], style={"display": "grid", "gridTemplateColumns": "1fr 1fr", "gap": "8px"}),
    ])

def page_genres(time_range):
    artists = get_top_artists(sp, time_range)
    genre_counts = get_genres_from_artists(artists)

    if not genre_counts:
        return html.P("No genre data available.", style={"color": COLORS["muted"]})

    df = pd.DataFrame(list(genre_counts.items()), columns=["genre", "count"]).head(25)

    fig_tree = go.Figure(go.Treemap(
        labels=df["genre"],
        parents=[""] * len(df),
        values=df["count"],
        marker=dict(
            colorscale=[[0, COLORS["accent2"]], [1, COLORS["accent"]]],
            colors=df["count"],
            showscale=False,
        ),
        textfont=dict(size=13),
    ))
    fig_tree.update_layout(**PLOTLY_LAYOUT, title="Genre Treemap", height=400)

    fig_bar = go.Figure(go.Bar(
        x=df["count"],
        y=df["genre"],
        orientation="h",
        marker=dict(
            color=df["count"],
            colorscale=[[0, COLORS["accent2"]], [1, COLORS["accent"]]],
        ),
    ))
    fig_bar.update_layout(
        **PLOTLY_LAYOUT,
        title="Top Genres",
        yaxis=dict(autorange="reversed"),
        height=max(400, len(df) * 26),
        showlegend=False,
    )

    return html.Div([
        html.H2("Genres", style={"marginBottom": "0.5rem", "fontWeight": "700"}),
        html.P(TIME_RANGES[time_range], style={"color": COLORS["muted"], "marginBottom": "1.5rem"}),
        stat_card("Unique genres", len(genre_counts)),
        html.Div(style={"marginBottom": "1rem"}),
        card([dcc.Graph(figure=fig_tree, config={"displayModeBar": False})]),
        html.Div(style={"marginBottom": "1rem"}),
        card([dcc.Graph(figure=fig_bar,  config={"displayModeBar": False})]),
    ])


# Routing callback
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("time-range", "value"),
    Input("now-playing-interval", "n_intervals"),
)
def render_page(pathname, time_range, n):
    routes = {
        "/":            lambda: page_now_playing(n),
        "/top-tracks":  lambda: page_top_tracks(time_range),
        "/top-artists": lambda: page_top_artists(time_range),
        "/genres":      lambda: page_genres(time_range),
    }
    return routes.get(pathname or "/", lambda: html.P("Page not found."))()


# Run
if __name__ == "__main__":
    print("\n Starting Spotify Dashboard...")
    print("   Visit http://127.0.0.1:8888\n")
    app.run(debug=True, port=8888)