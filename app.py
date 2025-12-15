"""
Dash web application for viewing Evosep Eno system data traces.
Allows users to select runs, metrics, and generate interactive plots.
"""
import os
from pathlib import Path
import dash
from dash import dcc, html, Input, Output, State, ALL, callback_context
import plotly.graph_objs as go
import pandas as pd

# Base directory for example data
DATA_DIR = Path(__file__).parent / "ExampleData"


def parse_time_to_seconds(time_str):
    """
    Convert time string to seconds.
    
    Args:
        time_str: Time string in format 'HH:MM:SS.mmm' (e.g., '00:00:01.455')
        
    Returns:
        float: Total seconds, or None if parsing fails
    """
    try:
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        return None


def parse_data_file(filepath):
    """Parse a data file and return a DataFrame with time and value columns."""
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
            # Skip header and get metric info
            if len(lines) < 2:
                return None, None
            
            header = lines[0].strip().split('\t')
            metric_info = header[1] if len(header) > 1 else "Unknown"
            
            # Parse data
            times = []
            values = []
            
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split('\t')
                if len(parts) >= 2:
                    time_seconds = parse_time_to_seconds(parts[0])
                    if time_seconds is not None:
                        try:
                            value = float(parts[1])
                            times.append(time_seconds)
                            values.append(value)
                        except ValueError:
                            continue
            
            if times and values:
                df = pd.DataFrame({'time': times, 'value': values})
                return df, metric_info
            return None, None
    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None, None


def get_available_runs():
    """Get list of available run folders."""
    runs = []
    if DATA_DIR.exists():
        for item in sorted(DATA_DIR.iterdir()):
            if item.is_dir():
                runs.append(item.name)
    return runs


def get_metrics_for_run(run_name):
    """Get available metrics grouped by pump for a specific run."""
    run_path = DATA_DIR / run_name
    if not run_path.exists() or not run_path.is_dir():
        return {}
    
    metrics = {}
    
    for file in sorted(run_path.glob("Pump-*.txt")):
        filename = file.stem
        parts = filename.split('_')
        
        if len(parts) >= 2:
            pump = parts[0]  # e.g., "Pump-HP"
            metric = '_'.join(parts[1:])  # e.g., "Pressure" or "Actual-flow"
            
            if pump not in metrics:
                metrics[pump] = []
            
            metrics[pump].append({
                "name": metric,
                "filename": file.name
            })
    
    return metrics


# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Evosep Eno Data Viewer"

# App layout
app.layout = html.Div([
    html.H1("Evosep Eno System Data Viewer", style={'textAlign': 'center', 'marginBottom': 20}),
    
    html.Div([
        # Left panel - Run and metric selection
        html.Div([
            html.H3("Select Runs"),
            dcc.Checklist(
                id='run-checklist',
                options=[],
                value=[],
                style={'marginBottom': 20}
            ),
            
            html.Hr(),
            
            html.H3("Select Metrics"),
            html.Div([
                html.Button("Select All", id='select-all-btn', n_clicks=0, 
                           style={'marginRight': 10}),
                html.Button("Unselect All", id='unselect-all-btn', n_clicks=0),
            ], style={'marginBottom': 10}),
            
            html.Div(id='metric-checklist-container'),
            
            html.Hr(),
            
            html.Button("Generate Plot", id='plot-btn', n_clicks=0, 
                       style={'width': '100%', 'padding': 10, 'fontSize': 16}),
        ], style={
            'width': '25%', 
            'display': 'inline-block', 
            'verticalAlign': 'top',
            'padding': 20,
            'borderRight': '1px solid #ccc'
        }),
        
        # Right panel - Plot display
        html.Div([
            dcc.Graph(id='data-plot', style={'height': '80vh'})
        ], style={
            'width': '74%', 
            'display': 'inline-block', 
            'padding': 20
        })
    ])
])


@app.callback(
    Output('run-checklist', 'options'),
    Output('run-checklist', 'value'),
    Input('run-checklist', 'id')
)
def populate_runs(_):
    """Populate the run checklist with available runs."""
    runs = get_available_runs()
    options = [{'label': run, 'value': run} for run in runs]
    # Select the first run by default
    value = [runs[0]] if runs else []
    return options, value


@app.callback(
    Output('metric-checklist-container', 'children'),
    Input('run-checklist', 'value')
)
def update_metric_checklist(selected_runs):
    """
    Update metric checklist based on selected runs.
    
    Note: Uses metrics from the first selected run. Assumes all runs have
    similar structure. If runs have different metrics, only those from the
    first run will be displayed, though plots will work for matching files.
    """
    if not selected_runs:
        return html.Div("Please select at least one run", style={'color': 'gray'})
    
    # Get metrics from the first selected run
    metrics = get_metrics_for_run(selected_runs[0])
    
    if not metrics:
        return html.Div("No metrics found", style={'color': 'gray'})
    
    # Create nested checklist structure
    children = []
    
    for pump in sorted(metrics.keys()):
        pump_metrics = metrics[pump]
        
        # Pump header
        children.append(html.H4(pump, style={'marginTop': 15, 'marginBottom': 5}))
        
        # Metrics for this pump
        metric_options = []
        for metric in pump_metrics:
            metric_id = f"{pump}_{metric['name']}"
            metric_options.append({
                'label': metric['name'].replace('-', ' ').replace('_', ' '),
                'value': metric['filename']
            })
        
        children.append(
            dcc.Checklist(
                id={'type': 'metric-checkbox', 'pump': pump},
                options=metric_options,
                value=[],
                style={'marginLeft': 20, 'marginBottom': 10}
            )
        )
    
    return children


@app.callback(
    Output({'type': 'metric-checkbox', 'pump': ALL}, 'value'),
    Input('select-all-btn', 'n_clicks'),
    Input('unselect-all-btn', 'n_clicks'),
    State({'type': 'metric-checkbox', 'pump': ALL}, 'options'),
    State({'type': 'metric-checkbox', 'pump': ALL}, 'value'),
    prevent_initial_call=True
)
def select_unselect_all(select_clicks, unselect_clicks, all_options, current_values):
    """Handle select all and unselect all buttons."""
    ctx = callback_context
    
    if not ctx.triggered:
        return current_values
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'select-all-btn':
        # Select all metrics
        return [[opt['value'] for opt in options] for options in all_options]
    elif button_id == 'unselect-all-btn':
        # Unselect all metrics
        return [[] for _ in all_options]
    
    return current_values


@app.callback(
    Output('data-plot', 'figure'),
    Input('plot-btn', 'n_clicks'),
    State('run-checklist', 'value'),
    State({'type': 'metric-checkbox', 'pump': ALL}, 'value'),
    prevent_initial_call=True
)
def update_plot(n_clicks, selected_runs, selected_metrics_lists):
    """Generate plot based on selected runs and metrics."""
    if not selected_runs:
        return go.Figure().add_annotation(
            text="Please select at least one run",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Flatten the selected metrics from all pumps
    selected_metrics = []
    for metrics_list in selected_metrics_lists:
        if metrics_list:
            selected_metrics.extend(metrics_list)
    
    if not selected_metrics:
        return go.Figure().add_annotation(
            text="Please select at least one metric",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    # Create traces for each run and metric combination
    fig = go.Figure()
    
    for run_name in selected_runs:
        run_path = DATA_DIR / run_name
        
        for metric_file in selected_metrics:
            filepath = run_path / metric_file
            
            if filepath.exists():
                df, metric_info = parse_data_file(filepath)
                
                if df is not None and not df.empty:
                    # Create label
                    metric_name = metric_file.replace('.txt', '').replace('_', ' ')
                    if len(selected_runs) > 1:
                        label = f"{run_name} - {metric_name}"
                    else:
                        label = metric_name
                    
                    # Add trace
                    fig.add_trace(go.Scatter(
                        x=df['time'],
                        y=df['value'],
                        mode='lines',
                        name=label,
                        hovertemplate='<b>' + label + '</b><br>' +
                                    'Time: %{x:.2f}s<br>' +
                                    'Value: %{y:.3f}<br>' +
                                    '<extra></extra>'
                    ))
    
    # Update layout
    fig.update_layout(
        title="Evosep Data Traces",
        xaxis_title="Time (seconds)",
        yaxis_title="Value",
        hovermode='closest',
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        template="plotly_white"
    )
    
    return fig


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
