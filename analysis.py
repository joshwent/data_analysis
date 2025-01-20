import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, callback, callback_context, no_update, dash, Dash
import pandas as pd
import dash_bootstrap_components as dbc

# Global variables
global data
data = pd.DataFrame()  # Start with empty DataFrame

# Initialize the Dash app
app = Dash(__name__, 
           external_stylesheets=[dbc.themes.DARKLY],
           meta_tags=[{'name': 'viewport',
                      'content': 'width=device-width, initial-scale=1.0'}],
           suppress_callback_exceptions=True)

from html_parser import parse_html_file
import base64
import io


# print(data.columns)

# Create filter widgets with checkboxes
def create_checkbox_group(id_prefix, name, options):
    return html.Div([
        html.Div([
            dbc.Button(
                "Select All",
                id=f"{id_prefix}-select-all",
                color="primary",
                size="sm",
                className="me-2 mb-2"
            ),
            dbc.Button(
                "Deselect All",
                id=f"{id_prefix}-deselect-all", 
                color="secondary",
                size="sm",
                className="mb-2"
            ),
        ]),
        dbc.Checklist(
            id=f"{id_prefix}-checklist",
            options=[{"label": opt, "value": opt} for opt in sorted(options)],
            value=[],
            className="filter-checklist"
        )
    ], className="filter-group")

operator_group = create_checkbox_group('operator', 'Select Operators', [])
game_type_group = create_checkbox_group('game-type', 'Select Game Types', [])
map_group = create_checkbox_group('map', 'Select Maps', [])

# Create filter accordion using Dash components
filter_accordion = dbc.Accordion([
    dbc.AccordionItem(operator_group, title="Operators", item_id="operators"),
    dbc.AccordionItem(game_type_group, title="Game Types", item_id="game-types"),
    dbc.AccordionItem(map_group, title="Maps", item_id="maps")
], active_item="operators", style={"width": "250px"})

# Create date range picker using Dash component
date_range = dcc.DatePickerRange(
    id='date-range-picker',
    min_date_allowed=None,
    max_date_allowed=None,
    initial_visible_month=datetime.datetime.now(),
    start_date=None,
    end_date=None,
    style={
        'background-color': 'rgb(30, 30, 30)',
        'padding': '10px',
        'border-radius': '4px',
        'margin-top': '20px',
    }
)

# Set default plot dimensions
PLOT_HEIGHT = 300
PLOT_WIDTH = 490
    
# Create plots using hvPlot
def get_filtered_data(operators, game_types, maps, date_range):
    # Return empty DataFrame if any filter category is empty
    if not operators or not game_types or not maps:
        return pd.DataFrame(columns=data.columns)
        
    filtered = data.copy()
    
    # Basic filters with checkbox lists
    if operators:
        filtered = filtered[filtered['Operator'].isin(operators)]
    if game_types:
        filtered = filtered[filtered['Game Type'].isin(game_types)]
    if maps:
        filtered = filtered[filtered['Map'].isin(maps)]
    
    # Date range filter with proper timezone handling
    local_tz = datetime.datetime.now().astimezone().tzinfo
    start_time = pd.Timestamp(date_range[0]).tz_localize(local_tz)
    end_time = pd.Timestamp(date_range[1]).tz_localize(local_tz)
    
    # Ensure timestamps are in the correct timezone before comparison
    filtered = filtered[
        (filtered['Local Time'] >= start_time) &
        (filtered['Local Time'] <= end_time)
    ]

    # Add debug print statements
    # print(f"Filtering stats:")
    # print(f"Total rows before filter: {len(data)}")
    # print(f"Operators filter: {operators}")
    # print(f"Game Types filter: {game_types}")
    # print(f"Maps filter: {maps}")
    # print(f"Date range: {start_time} to {end_time}")
    # print(f"Remaining rows after filter: {len(filtered)}")
    
    return filtered

@callback(
    Output('plots-container', 'children'),
    [Input('operator-checklist', 'value'),
     Input('game-type-checklist', 'value'),
     Input('map-checklist', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def create_plots(operator, game_type, map_name, start_date, end_date):
    date_range = (start_date, end_date)
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Return message if no data after filtering
    if filtered_data.empty:
        return html.Div("Select filters to display charts", 
                       style={'text-align': 'center', 
                             'padding': '20px',
                             'color': 'var(--text-secondary)'})
    
    # Calculate metrics with proper handling of edge cases
    filtered_data['Accuracy'] = (filtered_data['Hits'] / filtered_data['Shots']).round(3)
    filtered_data['Accuracy'] = filtered_data['Accuracy'].clip(0, 1)  # Limit to valid range
    filtered_data['KD_Ratio'] = filtered_data.apply(
        lambda row: row['Kills'] / row['Deaths'] if row['Deaths'] > 0 else row['Kills'],
        axis=1
    ).round(2)
    # Extract time-based features
    # Extract time-based features using local time
    filtered_data['Hour'] = filtered_data['Local Time'].dt.hour
    filtered_data['Day'] = filtered_data['Local Time'].dt.day_name()
    
    # Skill progression over time
    skill_plot = px.line(
        filtered_data,
        x='Local Time',
        y='Skill',
        title="Skill Progression Over Time",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color_discrete_sequence=['#5B9AFF']
    )
    skill_plot.update_traces(line_width=2)
    skill_plot.update_layout(
        template="plotly_dark",
        xaxis_title='Time',
        yaxis_title='Skill Rating'
    )
    
    # KD ratio by hour as a bar chart with 12-hour format
    hourly_data = filtered_data.groupby('Hour')['KD_Ratio'].mean().reset_index()
    hourly_data['Hour_12'] = hourly_data['Hour'].apply(
        lambda x: f"{x if 0 < x < 12 else 12 if x == 12 else x-12} {'AM' if x < 12 else 'PM'}"
    )
    kd_by_hour = px.bar(
        hourly_data,
        x='Hour_12',
        y='KD_Ratio',
        title="Average K/D Ratio by Hour",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color_discrete_sequence=['#00ff00']
    )
    kd_by_hour.update_layout(
        xaxis_title='Hour of Day',
        yaxis_title='Average K/D Ratio',
        template="plotly_dark",
        xaxis_tickangle=45
    )
    
    # Accuracy distribution
    valid_accuracy = filtered_data[
        (filtered_data['Accuracy'] >= 0) & 
        (filtered_data['Accuracy'] <= 1) & 
        (filtered_data['Shots'] > 0)
    ]
    accuracy_hist = px.histogram(
        valid_accuracy,
        x='Accuracy',
        nbins=30,
        title="Accuracy Distribution",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color_discrete_sequence=['orange']
    )
    accuracy_hist.update_layout(
        xaxis_title='Accuracy %',
        yaxis_title='Number of Matches',
        template="plotly_dark"
    )

    # K/D distribution
    kd_hist = px.histogram(
        filtered_data,
        x='KD_Ratio',
        nbins=30,
        title="K/D Ratio Distribution",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color_discrete_sequence=['red']
    )
    kd_hist.update_layout(
        xaxis_title='K/D Ratio',
        yaxis_title='Number of Matches',
        template="plotly_dark"
    )

    # Skill distribution
    skill_hist = px.histogram(
        filtered_data,
        x='Skill',
        nbins=30,
        title="Skill Distribution",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color_discrete_sequence=['cyan']
    )
    skill_hist.update_layout(
        xaxis_title='Skill Rating',
        yaxis_title='Number of Matches',
        template="plotly_dark"
    )
    
    # Performance metrics over time
    metrics_plot = px.line(
        filtered_data,
        x='Local Time',
        y=['KD_Ratio', 'Accuracy'],
        title="Performance Metrics Over Time",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH
    )
    metrics_plot.update_traces(line_width=2)
    metrics_plot.update_layout(template="plotly_dark")
    
    # Headshot ratio over time
    filtered_data['Headshot_Ratio'] = (filtered_data['Headshots'] / filtered_data['Kills']).fillna(0)
    headshot_plot = px.line(
        filtered_data,
        x='Local Time',
        y='Headshot_Ratio',
        title="Headshot Ratio Over Time",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH
    )
    headshot_plot.update_traces(line_color='#ff4d4d', line_width=2)
    headshot_plot.update_layout(
        yaxis_title='Headshot Ratio',
        template="plotly_dark"
    )

    # Damage efficiency (damage done vs taken)
    damage_plot = px.scatter(
        filtered_data,
        x='Damage Taken',
        y='Damage Done',
        title="Damage Efficiency",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color='Match Outcome',
        trendline="ols"
    )
    damage_plot.update_layout(
        template="plotly_dark",
        showlegend=True
    )

    # Match outcomes pie chart
    outcome_stats = filtered_data['Match Outcome'].value_counts()
    outcome_plot = px.pie(
        values=outcome_stats.values,
        names=outcome_stats.index,
        title="Match Outcomes Distribution",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    outcome_plot.update_layout(template="plotly_dark")

    # Map K/D performance
    map_stats = (filtered_data.groupby('Map')
                .agg({'Kills': 'sum', 'Deaths': 'sum'})
                .reset_index())
    
    # Calculate KD ratio safely, replacing 0 deaths with 1
    map_stats['KD'] = (map_stats['Kills'] / map_stats['Deaths'].replace(0, 1)).round(2)
    
    # Sort by KD ratio
    map_stats = map_stats.sort_values('KD', ascending=True)
    
    map_performance = px.bar(
        map_stats,
        x='Map',
        y='KD',
        title="K/D Ratio by Map",
        height=PLOT_HEIGHT,
        width=PLOT_WIDTH,
        color_discrete_sequence=['purple']
    )
    map_performance.update_layout(
        xaxis_title='Map',
        yaxis_title='K/D Ratio',
        template="plotly_dark",
        xaxis_tickangle=45
    )
    
    # Create Dash graph components
    plots = [
        dcc.Graph(figure=skill_plot, id='skill-plot'),
        dcc.Graph(figure=kd_by_hour, id='kd-by-hour-plot'),
        dcc.Graph(figure=accuracy_hist, id='accuracy-hist'),
        dcc.Graph(figure=kd_hist, id='kd-hist'),
        dcc.Graph(figure=skill_hist, id='skill-hist'),
        dcc.Graph(figure=metrics_plot, id='metrics-plot'),
        dcc.Graph(figure=map_performance, id='map-performance'),
        dcc.Graph(figure=headshot_plot, id='headshot-plot'),
        dcc.Graph(figure=damage_plot, id='damage-plot'),
        dcc.Graph(figure=outcome_plot, id='outcome-plot')
    ]
    
    # Create activity heatmap
    activity_df = filtered_data.groupby(['Day', 'Hour']).size().reset_index(name='Count')
    activity_pivot = activity_df.pivot(index='Day', columns='Hour', values='Count').fillna(0)
    
    # Reorder days to start with Monday
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    activity_pivot = activity_pivot.reindex(day_order)
    
    # Convert hour numbers to 12-hour format for heatmap
    hour_labels = [f"{h if 0 < h < 12 else 12 if h == 12 else h-12} {'AM' if h < 12 else 'PM'}" 
                  for h in activity_pivot.columns]
    
    activity_heatmap = go.Figure(data=go.Heatmap(
        z=activity_pivot.values,
        x=hour_labels,
        y=activity_pivot.index,
        colorscale='Viridis',
        hoverongaps=False
    ))
    
    activity_heatmap.update_layout(
        title='Gaming Activity Heatmap',
        xaxis_title='Hour of Day',
        yaxis_title='Day of Week',
        height=400,
        template="plotly_dark",
        xaxis_tickangle=45
    )
    
    # Add activity heatmap to plots list
    plots.append(dcc.Graph(figure=activity_heatmap, id='activity-heatmap'))
    
    # Create responsive grid layout using Dash
    layout = html.Div(
        plots,
        style={
            'display': 'grid',
            'grid-template-columns': 'repeat(2, 1fr)',
            'gap': '1rem',
            'padding': '1rem',
            'background': 'var(--bg-dark)',
            'margin': '0 auto',
            'max-width': '1150px'
        }
    )
    return layout

# Create stats cards
@callback(
    Output('stats-container', 'children'),
    [Input('operator-checklist', 'value'),
     Input('game-type-checklist', 'value'),
     Input('map-checklist', 'value'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')]
)
def create_stats(operator, game_type, map_name, start_date, end_date):
    date_range = (start_date, end_date)
    filtered_data = get_filtered_data(operator, game_type, map_name, date_range)
    
    # Return empty stats if no data is loaded
    if data.empty:
        return html.Div([
            dbc.Card([
                dbc.CardBody([
                    html.H3("No Data Loaded", 
                           className="text-center mb-4",
                           style={'color': 'var(--accent-color)', 'fontSize': '1.4rem'}),
                    html.Div("Please load data using the upload button or example data button above.",
                            className="text-center",
                            style={'color': 'var(--text-secondary)'})
                ])
            ], className="stats-card mb-4")
        ])

    # Calculate stats from filtered data
    total_kills = filtered_data['Kills'].sum() if not filtered_data.empty else 0
    total_deaths = filtered_data['Deaths'].sum() if not filtered_data.empty else 0
    kd_ratio = round(total_kills / (total_deaths or 1), 2)  # Use 1 if total_deaths is 0
    total_wins = filtered_data['Match Outcome'].str.lower().str.contains('win').sum() if not filtered_data.empty else 0
    total_games = len(filtered_data)
    win_rate = round((total_wins / (total_games or 1)) * 100, 1)  # Use 1 if total_games is 0
    total_shots = filtered_data['Shots'].sum() if not filtered_data.empty else 0
    total_hits = filtered_data['Hits'].sum() if not filtered_data.empty else 0
    accuracy = round((total_hits / (total_shots or 1)) * 100, 1)  # Use 1 if total_shots is 0
    avg_score = int(round(filtered_data['Score'].mean(), 0)) if not filtered_data.empty else 0
    
    # Calculate total time played from match timestamps
    if not filtered_data.empty:
        match_durations = (filtered_data['Match End Timestamp'] - filtered_data['Match Start Timestamp'])
        total_seconds = int(match_durations.dt.total_seconds().sum())
    else:
        total_seconds = 0
    
    # Format total time
    days = total_seconds // (24 * 60 * 60)
    remaining_seconds = total_seconds % (24 * 60 * 60)
    hours = remaining_seconds // (60 * 60)
    minutes = (remaining_seconds % (60 * 60)) // 60
    total_time = f"{days}d {hours}h {minutes}m"
    
    # Create two cards: one for lifetime stats and one for filtered stats
    lifetime_card = dbc.Card([
        dbc.CardBody([
            html.H3("Lifetime Statistics", 
                    className="text-center mb-4",
                    style={'color': 'var(--accent-color)', 'fontSize': '1.4rem'}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong("Total K/D"),
                        html.Div(f"{kd_ratio}")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Overall Win Rate"),
                        html.Div(f"{win_rate}%")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Lifetime Accuracy"),
                        html.Div(f"{accuracy}%")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Total Play Time"),
                        html.Div(f"{total_time}")
                    ], className="text-center mb-3")
                ]),
            ])
        ])
    ], className="stats-card mb-4")

    # Return message if no data after filtering
    if filtered_data.empty:
        empty_card = html.Div("Select filters to display statistics", 
                       style={'text-align': 'center', 
                             'padding': '20px',
                             'color': 'var(--text-secondary)'})
        return html.Div([lifetime_card, empty_card])

    # Calculate filtered-specific stats
    filtered_avg_skill = round(filtered_data['Skill'].mean(), 2)
    filtered_kills = filtered_data['Kills'].sum()
    filtered_deaths = filtered_data['Deaths'].sum()
    filtered_kd = round(filtered_kills / (filtered_deaths or 1), 2)
    filtered_wins = filtered_data['Match Outcome'].str.lower().str.contains('win').sum()
    filtered_total = len(filtered_data)
    filtered_winrate = round((filtered_wins / (filtered_total or 1)) * 100, 1)  # Use 1 if filtered_total is 0
    filtered_accuracy = round((filtered_data['Hits'].sum() / filtered_data['Shots'].sum()) * 100, 1)
    filtered_streak = int(filtered_data['Longest Streak'].max())
    
    filtered_card = dbc.Card([
        dbc.CardBody([
            html.H3("Filtered Performance", 
                    className="text-center mb-4",
                    style={'color': 'var(--accent-color)', 'fontSize': '1.4rem'}),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong("Avg Skill Rating"),
                        html.Div(f"{filtered_avg_skill}")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Filtered K/D"),
                        html.Div(f"{filtered_kd}")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Win Rate"),
                        html.Div(f"{filtered_winrate}%")
                    ], className="text-center mb-3")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Accuracy"),
                        html.Div(f"{filtered_accuracy}%")
                    ], className="text-center mb-3")
                ]),
            ]),
            
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong("Best Streak"),
                        html.Div(f"{filtered_streak}")
                    ], className="text-center")
                ]),
                dbc.Col([
                    html.Div([
                        html.Strong("Matches"),
                        html.Div(f"{filtered_total}")
                    ], className="text-center")
                ]),
            ])
        ])
    ], className="stats-card", style={
        'background': 'rgb(30, 30, 30)',
        'color': 'white',
        'border': '1px solid #444',
        'borderRadius': '8px',
        'boxShadow': '0 2px 4px rgba(0,0,0,0.2)'
    })
    
    # Return both cards in a container
    return html.Div([
        lifetime_card,
        filtered_card
    ])


# Define the app layout
app.layout = dbc.Container([
    dbc.Row([
        # File upload
        dbc.Col([
            html.H2("Data Import",
                   style={'color': 'var(--text-primary)', 
                         'marginBottom': '1rem'}),
            dbc.Button(
                "Load Example Data",
                id='load-example-data',
                color="secondary",
                className="mb-3",
                style={'width': '100%'}
            ),
            html.Div("- or -", 
                    className="text-center mb-3",
                    style={'color': 'var(--text-secondary)'}),
            dcc.Upload(
                id='upload-data',
                children=html.Div([
                    'Drag and Drop or ',
                    dbc.Button('Select HTML File', color="primary", size="sm", className="ms-2")
                ]),
                style={
                    'width': '100%',
                    'height': '60px',
                    'lineHeight': '60px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'margin': '10px 0'
                },
                multiple=False
            ),
            dcc.Loading(
                id="loading-upload",
                type="circle",
                children=[
                    html.Div(id='upload-status', style={'marginBottom': '10px'})
                ]
            )
        ], width=12, style={
            'background': 'var(--bg-card)',
            'padding': '20px',
            'borderRadius': '8px',
            'marginBottom': '20px'
        }),
    ]),
    dbc.Row([
        # Sidebar
        dbc.Col([
            html.H2("Filters", 
                   style={'color': 'var(--text-primary)', 
                         'marginBottom': '1rem'}),
            filter_accordion,
            date_range
        ], width=3, style={
            'background': 'var(--bg-card)',
            'padding': '20px',
            'borderRadius': '8px'
        }),
        
        # Main content
        dbc.Col([
            html.Div(id='stats-container'),
            html.Hr(style={'margin': '20px 0'}),
            html.Div(id='plots-container')
        ], width=9, style={
            'background': 'var(--bg-dark)',
            'padding': '20px'
        })
    ])
], fluid=True, style={'maxWidth': '1400px'})

# Callbacks for select/deselect all buttons
@callback(
    Output('operator-checklist', 'value'),
    [Input('operator-select-all', 'n_clicks'),
     Input('operator-deselect-all', 'n_clicks')],
    [State('operator-checklist', 'options')]
)
def operator_select_all(select_clicks, deselect_clicks, options):
    ctx = callback_context
    if not ctx.triggered:
        return [opt['value'] for opt in options]  # Select all by default
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'operator-select-all':
        return [opt['value'] for opt in options]
    elif button_id == 'operator-deselect-all':
        return []
    return []

@callback(
    Output('game-type-checklist', 'value'),
    [Input('game-type-select-all', 'n_clicks'),
     Input('game-type-deselect-all', 'n_clicks')],
    [State('game-type-checklist', 'options')]
)
def game_type_select_all(select_clicks, deselect_clicks, options):
    ctx = callback_context
    if not ctx.triggered:
        return [opt['value'] for opt in options]  # Select all by default
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'game-type-select-all':
        return [opt['value'] for opt in options]
    elif button_id == 'game-type-deselect-all':
        return []
    return []

@callback(
    Output('map-checklist', 'value'),
    [Input('map-select-all', 'n_clicks'),
     Input('map-deselect-all', 'n_clicks')],
    [State('map-checklist', 'options')]
)
def map_select_all(select_clicks, deselect_clicks, options):
    ctx = callback_context
    if not ctx.triggered:
        return [opt['value'] for opt in options]  # Select all by default
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == 'map-select-all':
        return [opt['value'] for opt in options]
    elif button_id == 'map-deselect-all':
        return []
    return []


# Combined callback for file upload, example data, and date picker
@callback(
    [Output('upload-status', 'children'),
     Output('operator-checklist', 'options'),
     Output('game-type-checklist', 'options'),
     Output('map-checklist', 'options'),
     Output('date-range-picker', 'min_date_allowed'),
     Output('date-range-picker', 'max_date_allowed'),
     Output('date-range-picker', 'start_date', allow_duplicate=True),
     Output('date-range-picker', 'end_date', allow_duplicate=True),
     Output('operator-checklist', 'value', allow_duplicate=True),
     Output('game-type-checklist', 'value', allow_duplicate=True),
     Output('map-checklist', 'value', allow_duplicate=True),
     Output('upload-data', 'contents')],
    [Input('upload-data', 'contents'),
     Input('load-example-data', 'n_clicks'),
     Input('date-range-picker', 'start_date'),
     Input('date-range-picker', 'end_date')],
    [State('upload-data', 'filename')],
    prevent_initial_call=True
)
def update_data(contents, example_clicks, start_date, end_date, filename):
    global data
    ctx = callback_context
    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
    
    # Handle date picker updates
    if triggered_id in ['date-range-picker']:
        if start_date is None:
            start_date = data['Local Time'].min().replace(tzinfo=None)
        if end_date is None:
            end_date = data['Local Time'].max().replace(tzinfo=None)
        return no_update, no_update, no_update, no_update, no_update, no_update, start_date, end_date, no_update, no_update, no_update, None

    # Reset data before processing new data
    data = pd.DataFrame()

    # Handle example data loading
    if triggered_id == 'load-example-data' and example_clicks is not None:
        try:
            data = pd.read_csv('data2.csv')
            success_message = 'Example data loaded successfully'
        except Exception as e:
            return (
                html.Div([
                    html.I(className="fas fa-exclamation-circle", style={'color': 'red', 'marginRight': '10px'}),
                    'Error loading example data: ',
                    html.Pre(str(e))
                ]),
                [], [], [], None, None, None, None, [], [], [], None
            )
    
    # Handle file upload
    elif triggered_id == 'upload-data':
        if contents is None:
            return html.Div(), [], [], [], None, None, None, None, [], [], []
            
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            
            if 'html' in filename.lower():
                data = parse_html_file(decoded.decode('utf-8'))
                success_message = f'Successfully loaded {filename}'
            else:
                raise ValueError("Please upload an HTML file")
        except Exception as e:
            return (
                html.Div([
                    html.I(className="fas fa-exclamation-circle", style={'color': 'red', 'marginRight': '10px'}),
                    'Error processing file: ',
                    html.Pre(str(e))
                ]),
                [], [], [], None, None, None, None, [], [], [], None
            )
    else:
        return html.Div(), [], [], [], None, None, None, None, [], [], [], None

    # Apply common data processing
    # Filter out unwanted game types
    data = data[data['Game Type'] != 'Pentathlon Hint (TDM Example: Eliminate the other team or be holding the flag when time runs out.)']
    data = data[data['Game Type'] != 'Training Course']
    data = data[data['Game Type'] != 'Ran-snack']
    data = data[data['Game Type'] != 'Stop and Go']
    data = data[data['Game Type'] != 'Red Light Green Light']
    data = data[data['Game Type'] != 'Prop Hunt']
    
    # Convert timestamps and timezone
    timestamp_columns = ['UTC Timestamp', 'Match Start Timestamp', 'Match End Timestamp']
    for col in timestamp_columns:
        if col in data.columns:
            data[col] = pd.to_datetime(data[col])
            data[col] = data[col].dt.tz_localize('UTC')
    
    local_tz = datetime.datetime.now().astimezone().tzinfo
    data['Local Time'] = data['UTC Timestamp'].dt.tz_convert(local_tz)
    
    # Update filter options
    operator_options = [{"label": opt, "value": opt} for opt in sorted(data['Operator'].unique())]
    game_type_options = [{"label": opt, "value": opt} for opt in sorted(data['Game Type'].unique())]
    map_options = [{"label": opt, "value": opt} for opt in sorted(data['Map'].unique())]
    
    # Update date range
    min_date = data['Local Time'].min().replace(tzinfo=None)
    max_date = data['Local Time'].max().replace(tzinfo=None)
    
    # Get all values for initial selection
    operator_values = sorted(data['Operator'].unique())
    game_type_values = sorted(data['Game Type'].unique())
    map_values = sorted(data['Map'].unique())

    return (
        html.Div([
            html.I(className="fas fa-check-circle", style={'color': 'green', 'marginRight': '10px'}),
            success_message
        ]),
        operator_options,
        game_type_options,
        map_options,
        min_date,
        max_date,
        min_date,
        max_date,
        operator_values,
        game_type_values,
        map_values,
        None
    )

# Mount the app to the container
app.clientside_callback(
    """
    function(n) {
        return document.getElementById('dash-container').innerHTML;
    }
    """,
    Output('dash-container', 'children'),
    Input('_', 'data')
)

if __name__ == '__main__':
    app.layout = app.layout  # This ensures the layout is properly initialized
