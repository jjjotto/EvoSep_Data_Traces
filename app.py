"""
Dash web application for viewing Evosep Eno system data traces.
Allows users to select runs, metrics, and generate interactive plots.
"""
import os
from pathlib import Path
from datetime import datetime
import dash
from dash import dcc, html, Input, Output, State, ALL, callback_context, no_update, dash_table
import plotly.graph_objs as go
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

def resolve_data_root(path_str):
    """Resolve and validate a data root path string."""
    if not path_str:
        return None
    try:
        path = Path(path_str).expanduser()
        if path.exists() and path.is_dir():
            return path
    except Exception:
        return None
    return None


DEFAULT_DATA_PATH = os.environ.get('EVOSEP_DEFAULT_DATA_PATH', '').strip()
RESOLVED_DEFAULT_PATH = resolve_data_root(DEFAULT_DATA_PATH)
INITIAL_DATA_ROOT = str(RESOLVED_DEFAULT_PATH) if RESOLVED_DEFAULT_PATH else ''
if DEFAULT_DATA_PATH and not RESOLVED_DEFAULT_PATH:
    INITIAL_STATUS_MESSAGE = html.Span(
        f"Configured default path not found: {DEFAULT_DATA_PATH}",
        style={'color': '#dc3545'}
    )
elif RESOLVED_DEFAULT_PATH:
    INITIAL_STATUS_MESSAGE = html.Span(
        f"Using data folder: {RESOLVED_DEFAULT_PATH}",
        style={'color': '#28a745'}
    )
else:
    INITIAL_STATUS_MESSAGE = html.Span(
        "Please enter the parent folder path that contains your run subdirectories.",
        style={'color': '#6c757d'}
    )


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


def parse_journal_file(run_path):
    """Parse journal.txt file to extract metadata."""
    journal_path = run_path / "journal.txt"
    metadata = {
        'procedure_name': '',
        'log_name': '',
        'sample_name': '',
        'vial_position': '',
        'date_time': ''
    }
    
    if journal_path.exists():
        try:
            with open(journal_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('Procedure.Name:'):
                        metadata['procedure_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Procedure.Logname:'):
                        metadata['log_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Procedure.Samplename:'):
                        metadata['sample_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('Procedure.Vialposition:'):
                        metadata['vial_position'] = line.split(':', 1)[1].strip()
        except Exception as e:
            print(f"Error parsing journal file {journal_path}: {e}")
    
    # Try to extract date/time from folder name if not in journal
    if not metadata['date_time']:
        folder_name = run_path.name
        # Format: 200-SPD_2025-12-11_12-27-48
        parts = folder_name.split('_')
        if len(parts) >= 3:
            date_part = parts[-2]
            time_part = parts[-1]
            try:
                metadata['date_time'] = f"{date_part} {time_part.replace('-', ':')}"
            except Exception:
                pass
    
    return metadata


def get_available_runs(base_dir):
    """Get list of available run folders with metadata."""
    runs = []

    if base_dir and base_dir.exists():
        for item in sorted(base_dir.iterdir()):
            if item.is_dir():
                metadata = parse_journal_file(item)
                runs.append({
                    'name': item.name,
                    'procedure': metadata['procedure_name'],
                    'sample': metadata['sample_name'],
                    'vial': metadata['vial_position'],
                    'datetime': metadata['date_time']
                })
    return runs


def get_metrics_for_run(base_dir, run_name):
    """Get available metrics grouped by pump for a specific run."""
    if not base_dir:
        return {}
    run_path = base_dir / run_name
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


FLOW_AXIS_KEYWORDS = ('flow', 'speed', 'setpoint', 'displacement')


def classify_metric_axis(metric_filename):
    lower_name = metric_filename.lower()
    if any(keyword in lower_name for keyword in FLOW_AXIS_KEYWORDS):
        return 'flow'
    return 'pressure'


def extract_selected_runs(run_table_data, selected_rows):
    """Return list of run names based on selected table rows."""
    if not run_table_data:
        return []
    selected_rows = selected_rows or []
    selected_names = []
    for idx in selected_rows:
        if isinstance(idx, int) and 0 <= idx < len(run_table_data):
            selected_names.append(run_table_data[idx]['folder'])
    if selected_names:
        return selected_names
    return [run_table_data[0]['folder']]


# Initialize the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Evosep Eno Data Viewer"

# App layout
app.layout = html.Div([
    html.H1("Evosep Eno System Data Viewer", style={'textAlign': 'center', 'marginBottom': 20}),
    
    # Data folder selection controls
    html.Div([
        html.Div([
            html.Label("Data folder:", style={'fontWeight': 'bold', 'marginRight': 10}),
            dcc.Input(
                id='data-root-input',
                type='text',
                placeholder='Enter parent folder path (e.g., \\network\\share\\S10782)',
                value=INITIAL_DATA_ROOT or DEFAULT_DATA_PATH,
                style={'width': '50%', 'padding': 8, 'marginRight': 10}
            ),
            html.Button('Set Data Folder', id='set-data-root-btn', n_clicks=0, style={
                'padding': '8px 16px',
                'backgroundColor': '#007bff',
                'color': 'white',
                'border': 'none',
                'borderRadius': '4px',
                'cursor': 'pointer',
                'marginRight': 10
            }),
            html.Button('Refresh Runs', id='refresh-runs-btn', n_clicks=0, style={
                'padding': '8px 16px',
                'border': '1px solid #6c757d',
                'backgroundColor': 'white',
                'color': '#6c757d',
                'borderRadius': '4px',
                'cursor': 'pointer'
            })
        ], style={'marginBottom': 5}),
        html.Div(INITIAL_STATUS_MESSAGE, id='data-root-status', style={'fontSize': 12})
    ], style={'padding': '10px 20px', 'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #dee2e6'}),
    
    html.Div([
        html.H3("Select Runs", style={'marginBottom': 15}),
        html.Div([
            dcc.Input(
                id='run-search',
                type='text',
                placeholder='Search runs...',
                style={'flex': 1, 'minWidth': '200px', 'padding': 8, 'marginRight': 10}
            ),
            dcc.Input(
                id='procedure-filter',
                type='text',
                placeholder='Procedure name...',
                style={'flex': 1, 'minWidth': '160px', 'padding': 8, 'marginRight': 10}
            ),
            dcc.Input(
                id='sample-filter',
                type='text',
                placeholder='Sample name...',
                style={'flex': 1, 'minWidth': '160px', 'padding': 8, 'marginRight': 10}
            ),
            dcc.Input(
                id='vial-filter',
                type='text',
                placeholder='Vial position...',
                style={'flex': 1, 'minWidth': '140px', 'padding': 8}
            )
        ], style={'display': 'flex', 'flexWrap': 'wrap', 'marginBottom': 10}),
        dash_table.DataTable(
            id='run-table',
            columns=[
                {'name': 'Folder', 'id': 'folder'},
                {'name': 'Date & Time', 'id': 'datetime'},
                {'name': 'Procedure', 'id': 'procedure'},
                {'name': 'Sample', 'id': 'sample'},
                {'name': 'Vial', 'id': 'vial'}
            ],
            data=[],
            sort_action='native',
            row_selectable='multi',
            style_table={'maxHeight': '320px', 'overflowY': 'auto', 'border': '1px solid #ddd'},
            style_header={'backgroundColor': '#f1f3f5', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'left', 'padding': '6px 8px', 'fontSize': 13},
            selected_rows=[],
            page_action='none'
        ),
        html.Div([
            html.Button("Select All (Filtered)", id='select-all-runs-btn', n_clicks=0,
                        style={'marginRight': 10, 'padding': '6px 12px'}),
            html.Button("Clear Selection", id='clear-runs-btn', n_clicks=0,
                        style={'padding': '6px 12px'})
        ], style={'marginTop': 10})
    ], style={'padding': 20, 'borderBottom': '1px solid #e0e0e0', 'backgroundColor': '#fff'}),
    
    html.Div([
        html.H3("Select Metrics", style={'marginBottom': 10}),
        html.Div([
            html.Button("Select All", id='select-all-btn', n_clicks=0, 
                       style={'marginRight': 10, 'padding': '6px 12px'}),
            html.Button("Unselect All", id='unselect-all-btn', n_clicks=0,
                       style={'padding': '6px 12px'})
        ], style={'marginBottom': 10}),
        html.Div(
            id='metric-checklist-container',
            style={'border': '1px solid #ddd', 'padding': 10, 'backgroundColor': '#fafafa',
                   'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'center', 'gap': '16px'}
        )
    ], style={'padding': 20, 'borderBottom': '1px solid #e0e0e0', 'backgroundColor': '#fefefe'}),
    
    html.Div([
        html.H3("Plot Options", style={'marginBottom': 10}),
        dcc.Checklist(
            id='dual-axis-toggle',
            options=[{'label': ' Use dual Y axes (Pressure vs Flow)', 'value': 'dual'}],
            value=['dual'],
            style={'marginBottom': 10}
        ),
        html.Div([
            html.Div([
                html.Label("Pressure axis max", style={'display': 'block', 'fontSize': 12}),
                dcc.Input(
                    id='pressure-axis-max',
                    type='number',
                    placeholder='e.g., 400',
                    debounce=True,
                    style={'width': '150px', 'padding': 6}
                )
            ], style={'marginRight': 20}),
            html.Div([
                html.Label("Flow axis max", style={'display': 'block', 'fontSize': 12}),
                dcc.Input(
                    id='flow-axis-max',
                    type='number',
                    placeholder='e.g., 6',
                    debounce=True,
                    style={'width': '150px', 'padding': 6}
                )
            ])
        ], style={'display': 'flex', 'alignItems': 'flex-end', 'flexWrap': 'wrap'}),
        html.Small("Leave axis values blank to auto-scale.", style={'color': '#6c757d'})
    ], style={'padding': 20, 'borderBottom': '1px solid #e0e0e0', 'backgroundColor': '#fffdf7'}),

    html.Div([
        html.Button("Generate Plot", id='plot-btn', n_clicks=0, 
                   style={'width': '100%', 'padding': 12, 'fontSize': 16,
                          'backgroundColor': '#28a745', 'color': 'white',
                          'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer',
                          'marginBottom': 15}),
        dcc.Graph(id='data-plot', style={'height': '80vh'})
    ], style={'padding': 20}),
    
    # Store selected data folder path
    dcc.Store(id='data-root-store', data=INITIAL_DATA_ROOT)
])


@app.callback(
    Output('data-root-store', 'data'),
    Output('data-root-status', 'children'),
    Input('set-data-root-btn', 'n_clicks'),
    State('data-root-input', 'value'),
    prevent_initial_call=True
)
def set_data_root(n_clicks, path_value):
    """Update the active data root when the user submits a folder path."""
    del n_clicks
    cleaned_value = (path_value or '').strip()
    if not cleaned_value:
        return no_update, html.Span("Please enter a folder path before applying.", style={'color': '#dc3545'})
    resolved = resolve_data_root(cleaned_value)
    if not resolved:
        return no_update, html.Span(f"Folder not found or inaccessible: {cleaned_value}", style={'color': '#dc3545'})
    return str(resolved), html.Span(f"Using data folder: {resolved}", style={'color': '#28a745'})


@app.callback(
    Output('run-table', 'data'),
    Output('run-table', 'selected_rows'),
    Input('data-root-store', 'data'),
    Input('refresh-runs-btn', 'n_clicks'),
    Input('run-search', 'value'),
    Input('procedure-filter', 'value'),
    Input('sample-filter', 'value'),
    Input('vial-filter', 'value'),
    Input('select-all-runs-btn', 'n_clicks'),
    Input('clear-runs-btn', 'n_clicks')
)
def populate_runs(data_root, refresh_clicks, search_term, procedure_filter, sample_filter, vial_filter,
                  select_all_clicks, clear_clicks):
    """Populate the run table with available runs and apply filters."""
    del refresh_clicks, select_all_clicks, clear_clicks
    base_dir = Path(data_root) if data_root else None
    runs = get_available_runs(base_dir)
    
    filtered_runs = runs
    
    if search_term:
        search_lower = search_term.lower()
        filtered_runs = [r for r in filtered_runs if search_lower in r['name'].lower()]
    
    if procedure_filter:
        proc_lower = procedure_filter.lower()
        filtered_runs = [r for r in filtered_runs if proc_lower in r['procedure'].lower()]
    
    if sample_filter:
        sample_lower = sample_filter.lower()
        filtered_runs = [r for r in filtered_runs if sample_lower in r['sample'].lower()]
    
    if vial_filter:
        vial_lower = vial_filter.lower()
        filtered_runs = [r for r in filtered_runs if vial_lower in r['vial'].lower()]
    
    table_data = [{
        'folder': run['name'],
        'datetime': run['datetime'],
        'procedure': run['procedure'],
        'sample': run['sample'],
        'vial': run['vial']
    } for run in filtered_runs]
    trigger = callback_context.triggered[0]['prop_id'].split('.')[0] if callback_context.triggered else None
    if trigger == 'select-all-runs-btn':
        selected_rows = list(range(len(table_data)))
    elif trigger == 'clear-runs-btn':
        selected_rows = []
    else:
        selected_rows = [0] if table_data else []
    return table_data, selected_rows


@app.callback(
    Output('metric-checklist-container', 'children'),
    Input('run-table', 'data'),
    Input('run-table', 'selected_rows'),
    Input('data-root-store', 'data')
)
def update_metric_checklist(run_table_data, selected_rows, data_root):
    """
    Update metric checklist based on selected runs.
    
    Note: Uses metrics from the first selected run. Assumes all runs have
    similar structure. If runs have different metrics, only those from the
    first run will be displayed, though plots will work for matching files.
    """
    base_dir = Path(data_root) if data_root else None
    if not base_dir:
        return html.Div("Set a data folder to browse metrics", style={'color': 'gray'})
    if not run_table_data:
        return html.Div("No runs available", style={'color': 'gray'})
    selected_runs = extract_selected_runs(run_table_data, selected_rows)
    if not selected_runs:
        return html.Div("Please select at least one run", style={'color': 'gray'})
    
    metrics = get_metrics_for_run(base_dir, selected_runs[0])
    
    if not metrics:
        return html.Div("No metrics found", style={'color': 'gray'})
    
    pump_blocks = []
    for pump in sorted(metrics.keys()):
        pump_metrics = metrics[pump]
        metric_options = []
        default_values = []
        for metric in pump_metrics:
            label = metric['name'].replace('-', ' ').replace('_', ' ')
            metric_options.append({'label': label, 'value': metric['filename']})
            metric_key = metric['name'].lower().replace(' ', '')
            if pump.lower() == 'pump-hp' and metric_key in {'actual-flow', 'actualflow', 'pressure'}:
                default_values.append(metric['filename'])
        pump_blocks.append(html.Div([
            html.H4(pump, style={'marginBottom': 8}),
            dcc.Checklist(
                id={'type': 'metric-checkbox', 'pump': pump},
                options=metric_options,
                value=default_values,
                labelStyle={'display': 'block', 'marginBottom': 3}
            )
        ], style={'backgroundColor': '#fff', 'border': '1px solid #e3e3e3', 'borderRadius': '8px',
                  'padding': '12px 16px', 'minWidth': '180px', 'boxShadow': '0 1px 2px rgba(0,0,0,0.05)' }))
    
    return pump_blocks


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
    State('run-table', 'data'),
    State('run-table', 'selected_rows'),
    State({'type': 'metric-checkbox', 'pump': ALL}, 'value'),
    State('data-root-store', 'data'),
    State('dual-axis-toggle', 'value'),
    State('pressure-axis-max', 'value'),
    State('flow-axis-max', 'value'),
    prevent_initial_call=True
)
def update_plot(n_clicks, run_table_data, selected_rows, selected_metrics_lists, data_root,
                dual_axis_toggle, pressure_axis_max, flow_axis_max):
    """Generate plot based on selected runs and metrics."""
    base_dir = Path(data_root) if data_root else None
    if not base_dir:
        return go.Figure().add_annotation(
            text="Set a data folder before plotting",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    if not run_table_data:
        return go.Figure().add_annotation(
            text="No runs available to plot",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    selected_runs = extract_selected_runs(run_table_data, selected_rows)
    if not selected_runs:
        return go.Figure().add_annotation(
            text="Please select at least one run",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    dual_axis_enabled = bool(dual_axis_toggle and 'dual' in dual_axis_toggle)
    pressure_axis_limit = float(pressure_axis_max) if isinstance(pressure_axis_max, (int, float)) else None
    flow_axis_limit = float(flow_axis_max) if isinstance(flow_axis_max, (int, float)) else None
    
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
    has_pressure = False
    has_flow = False
    
    for run_name in selected_runs:
        run_path = base_dir / run_name
        
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
                    
                    axis_type = classify_metric_axis(metric_file)
                    if axis_type == 'flow':
                        has_flow = True
                    else:
                        has_pressure = True
                    yaxis_name = 'y2' if dual_axis_enabled and axis_type == 'flow' else 'y'
                    # Add trace
                    fig.add_trace(go.Scatter(
                        x=df['time'],
                        y=df['value'],
                        mode='lines',
                        name=label,
                        yaxis=yaxis_name,
                        hovertemplate='<b>' + label + '</b><br>' +
                                    'Time: %{x:.2f}s<br>' +
                                    'Value: %{y:.3f}<br>' +
                                    '<extra></extra>'
                    ))
    
    # Update layout with legend positioned below the plot
    layout_kwargs = {
        'title': "Evosep Data Traces",
        'xaxis_title': "Time (seconds)",
        'hovermode': 'closest',
        'showlegend': True,
        'legend': dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        'template': "plotly_white",
        'margin': dict(b=150)  # Add bottom margin for legend
    }
    if dual_axis_enabled:
        yaxis_cfg = {'title': 'Pressure', 'rangemode': 'tozero'}
        if pressure_axis_limit is not None:
            yaxis_cfg['range'] = [0, pressure_axis_limit]
        yaxis2_cfg = {'title': 'Flow / Related', 'overlaying': 'y', 'side': 'right', 'rangemode': 'tozero'}
        if flow_axis_limit is not None:
            yaxis2_cfg['range'] = [0, flow_axis_limit]
        layout_kwargs['yaxis'] = yaxis_cfg
        layout_kwargs['yaxis2'] = yaxis2_cfg
        if not has_flow:
            layout_kwargs.pop('yaxis2', None)
    else:
        yaxis_cfg = {'title': 'Value', 'rangemode': 'tozero'}
        if pressure_axis_limit is not None:
            yaxis_cfg['range'] = [0, pressure_axis_limit]
        layout_kwargs['yaxis'] = yaxis_cfg
    fig.update_layout(**layout_kwargs)
    
    return fig


if __name__ == '__main__':
    # Note: For production deployment, set debug=False to avoid exposing debug information
    # on the network. Debug mode is enabled here for development convenience.
    import sys
    debug_mode = '--debug' in sys.argv or len(sys.argv) == 1
    app.run_server(debug=debug_mode, host='0.0.0.0', port=8050)
