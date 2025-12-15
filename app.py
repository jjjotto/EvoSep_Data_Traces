"""
Dash web application for viewing Evosep Eno system data traces.
Allows users to select runs, metrics, and generate interactive plots.
"""
import os
from pathlib import Path
import base64
import io
import zipfile
import tempfile
import shutil
from datetime import datetime
import dash
from dash import dcc, html, Input, Output, State, ALL, callback_context
import plotly.graph_objs as go
import pandas as pd

# Base directory for example data
DATA_DIR = Path(__file__).parent / "ExampleData"
# Temporary directory for uploaded data
UPLOAD_DIR = Path(tempfile.gettempdir()) / "evosep_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


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


def get_available_runs(data_source='example'):
    """Get list of available run folders with metadata."""
    runs = []
    source_dir = DATA_DIR if data_source == 'example' else UPLOAD_DIR
    
    if source_dir.exists():
        for item in sorted(source_dir.iterdir()):
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


def get_metrics_for_run(run_name, data_source='example'):
    """Get available metrics grouped by pump for a specific run."""
    source_dir = DATA_DIR if data_source == 'example' else UPLOAD_DIR
    run_path = source_dir / run_name
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
    
    # Data source selection and upload
    html.Div([
        html.Div([
            html.Label("Data Source:", style={'fontWeight': 'bold', 'marginRight': 10}),
            dcc.RadioItems(
                id='data-source',
                options=[
                    {'label': ' Example Data', 'value': 'example'},
                    {'label': ' Upload Data', 'value': 'upload'}
                ],
                value='example',
                inline=True,
                style={'display': 'inline-block', 'marginRight': 20}
            ),
        ], style={'display': 'inline-block', 'marginRight': 20}),
        
        html.Div([
            dcc.Upload(
                id='upload-data',
                children=html.Button('Browse Local Files/Folders', style={
                    'padding': '8px 16px',
                    'backgroundColor': '#007bff',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer'
                }),
                multiple=True,
                accept='.txt,.zip'
            ),
            html.Div(id='upload-status', style={'marginTop': 5, 'fontSize': 12, 'color': 'green'}),
            html.Div([
                html.Small("Tip: You can select .zip files, individual .txt files, or use Chrome/Edge to select entire folders.", 
                          style={'color': '#666', 'fontSize': 11})
            ], style={'marginTop': 3})
        ], id='upload-container', style={'display': 'inline-block'})
    ], style={'padding': '10px 20px', 'backgroundColor': '#f8f9fa', 'borderBottom': '1px solid #dee2e6'}),
    
    html.Div([
        # Left panel - Run and metric selection
        html.Div([
            html.Div([
                html.H3("Select Runs", style={'marginBottom': 10}),
                html.Div([
                    dcc.Input(
                        id='run-search',
                        type='text',
                        placeholder='Search runs...',
                        style={'width': '100%', 'padding': 8, 'marginBottom': 10}
                    ),
                ]),
                html.Div([
                    html.Label("Filter by:", style={'fontWeight': 'bold', 'marginBottom': 5}),
                    dcc.Input(
                        id='procedure-filter',
                        type='text',
                        placeholder='Procedure name...',
                        style={'width': '100%', 'padding': 6, 'marginBottom': 5, 'fontSize': 12}
                    ),
                    dcc.Input(
                        id='sample-filter',
                        type='text',
                        placeholder='Sample name...',
                        style={'width': '100%', 'padding': 6, 'marginBottom': 5, 'fontSize': 12}
                    ),
                    dcc.Input(
                        id='vial-filter',
                        type='text',
                        placeholder='Vial position...',
                        style={'width': '100%', 'padding': 6, 'marginBottom': 5, 'fontSize': 12}
                    ),
                ], style={'marginBottom': 10}),
            ]),
            
            html.Div([
                dcc.Checklist(
                    id='run-checklist',
                    options=[],
                    value=[],
                    style={'marginBottom': 20},
                    labelStyle={'display': 'block', 'marginBottom': 5}
                ),
            ], style={
                'maxHeight': '300px', 
                'overflowY': 'auto', 
                'border': '1px solid #ddd',
                'padding': 10,
                'marginBottom': 20,
                'backgroundColor': '#fafafa'
            }),
            
            html.Hr(),
            
            html.H3("Select Metrics", style={'marginBottom': 10}),
            html.Div([
                html.Button("Select All", id='select-all-btn', n_clicks=0, 
                           style={'marginRight': 10, 'padding': '6px 12px'}),
                html.Button("Unselect All", id='unselect-all-btn', n_clicks=0,
                           style={'padding': '6px 12px'}),
            ], style={'marginBottom': 10}),
            
            html.Div(
                id='metric-checklist-container',
                style={'maxHeight': '300px', 'overflowY': 'auto', 'border': '1px solid #ddd',
                       'padding': 10, 'backgroundColor': '#fafafa'}
            ),
            
            html.Hr(),
            
            html.Button("Generate Plot", id='plot-btn', n_clicks=0, 
                       style={'width': '100%', 'padding': 10, 'fontSize': 16,
                              'backgroundColor': '#28a745', 'color': 'white',
                              'border': 'none', 'borderRadius': '4px', 'cursor': 'pointer'}),
        ], style={
            'width': '30%', 
            'display': 'inline-block', 
            'verticalAlign': 'top',
            'padding': 20,
            'borderRight': '1px solid #ccc'
        }),
        
        # Right panel - Plot display
        html.Div([
            dcc.Graph(id='data-plot', style={'height': '80vh'})
        ], style={
            'width': '69%', 
            'display': 'inline-block', 
            'verticalAlign': 'top',
            'padding': 20
        })
    ]),
    
    # Hidden div to store data source state
    dcc.Store(id='current-data-source', data='example')
])


@app.callback(
    Output('current-data-source', 'data'),
    Output('upload-status', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def handle_upload(list_of_contents, list_of_filenames):
    """Handle uploaded files (zip archives, individual txt files, or folder structures)."""
    if list_of_contents is None:
        return 'example', ''
    
    # Validate UPLOAD_DIR before cleanup
    if not UPLOAD_DIR.exists() or not str(UPLOAD_DIR).startswith(tempfile.gettempdir()):
        return 'example', 'Error: Invalid upload directory configuration'
    
    # Clear existing uploads
    try:
        for item in UPLOAD_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    except Exception as e:
        return 'example', f'Error cleaning upload directory: {str(e)}'
    
    uploaded_count = 0
    txt_files_count = 0
    MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB limit
    
    # Dictionary to organize files by their run folder
    run_folders = {}
    
    for content, filename in zip(list_of_contents, list_of_filenames):
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        
        try:
            if filename.endswith('.zip'):
                # Check file size
                if len(decoded) > MAX_ZIP_SIZE:
                    return 'example', f'Error: ZIP file {filename} exceeds 100MB limit'
                
                # Handle zip file with path traversal protection
                with zipfile.ZipFile(io.BytesIO(decoded)) as zip_ref:
                    # Validate all paths before extraction
                    for zip_info in zip_ref.infolist():
                        # Resolve path and check it's within UPLOAD_DIR
                        extract_path = (UPLOAD_DIR / zip_info.filename).resolve()
                        if not str(extract_path).startswith(str(UPLOAD_DIR.resolve())):
                            return 'example', f'Error: ZIP contains invalid paths (security risk)'
                    
                    # Extract if all paths are valid
                    zip_ref.extractall(UPLOAD_DIR)
                    uploaded_count += 1
            elif filename.endswith('.txt'):
                # Handle individual .txt files - organize by folder structure
                # Filenames from folder uploads contain path separators
                path_parts = filename.replace('\\', '/').split('/')
                
                if len(path_parts) >= 2:
                    # File is part of a folder structure (e.g., "ExampleData/200-SPD.../Pump-HP_Pressure.txt")
                    # Find the run folder name (second-to-last part typically)
                    if len(path_parts) >= 2:
                        # Get the parent folder name (run folder)
                        run_folder = path_parts[-2]
                        
                        if run_folder not in run_folders:
                            run_folders[run_folder] = []
                        
                        run_folders[run_folder].append({
                            'filename': path_parts[-1],
                            'content': decoded
                        })
                        txt_files_count += 1
                else:
                    # Single file without folder structure - skip
                    pass
        except zipfile.BadZipFile:
            return 'example', f'Error: {filename} is not a valid ZIP file'
        except Exception as e:
            return 'example', f'Error uploading files: {str(e)}'
    
    # Write organized txt files to appropriate run folders
    if run_folders:
        try:
            for run_folder, files in run_folders.items():
                run_path = UPLOAD_DIR / run_folder
                run_path.mkdir(parents=True, exist_ok=True)
                
                for file_info in files:
                    file_path = run_path / file_info['filename']
                    with open(file_path, 'wb') as f:
                        f.write(file_info['content'])
            
            uploaded_count += len(run_folders)
        except Exception as e:
            return 'example', f'Error writing uploaded files: {str(e)}'
    
    if uploaded_count > 0:
        msg = f'Successfully uploaded {uploaded_count} run folder(s)'
        if txt_files_count > 0:
            msg += f' ({txt_files_count} files)'
        return 'upload', msg
    return 'example', 'Please upload ZIP files or select folders containing run data'


@app.callback(
    Output('upload-container', 'style'),
    Input('data-source', 'value')
)
def toggle_upload_visibility(data_source):
    """Show/hide upload button based on data source selection."""
    if data_source == 'upload':
        return {'display': 'inline-block'}
    return {'display': 'none'}


@app.callback(
    Output('run-checklist', 'options'),
    Output('run-checklist', 'value'),
    Input('data-source', 'value'),
    Input('current-data-source', 'data'),
    Input('run-search', 'value'),
    Input('procedure-filter', 'value'),
    Input('sample-filter', 'value'),
    Input('vial-filter', 'value')
)
def populate_runs(data_source, uploaded_source, search_term, procedure_filter, sample_filter, vial_filter):
    """Populate the run checklist with available runs and apply filters."""
    # Use uploaded data source if files were uploaded
    source = uploaded_source if uploaded_source == 'upload' else data_source
    
    runs = get_available_runs(source)
    
    # Apply filters
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
    
    # Create options with metadata displayed in a more informative format
    options = []
    for run in filtered_runs:
        # Build a rich label with all available metadata
        label_parts = [run['name']]
        
        # Add datetime if available
        if run['datetime']:
            label_parts.append(f"[{run['datetime']}]")
        
        # Add procedure if available
        if run['procedure']:
            label_parts.append(f"Proc: {run['procedure']}")
        
        # Add sample name if available
        if run['sample']:
            label_parts.append(f"Sample: {run['sample']}")
        
        # Add vial position if available
        if run['vial']:
            label_parts.append(f"Vial: {run['vial']}")
        
        label = ' | '.join(label_parts)
        options.append({'label': label, 'value': run['name']})
    
    # Select the first run by default if nothing is selected
    value = [filtered_runs[0]['name']] if filtered_runs else []
    return options, value


@app.callback(
    Output('metric-checklist-container', 'children'),
    Input('run-checklist', 'value'),
    Input('current-data-source', 'data')
)
def update_metric_checklist(selected_runs, data_source):
    """
    Update metric checklist based on selected runs.
    
    Note: Uses metrics from the first selected run. Assumes all runs have
    similar structure. If runs have different metrics, only those from the
    first run will be displayed, though plots will work for matching files.
    """
    if not selected_runs:
        return html.Div("Please select at least one run", style={'color': 'gray'})
    
    # Get metrics from the first selected run
    metrics = get_metrics_for_run(selected_runs[0], data_source)
    
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
                style={'marginLeft': 20, 'marginBottom': 10},
                labelStyle={'display': 'block', 'marginBottom': 3}
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
    State('current-data-source', 'data'),
    prevent_initial_call=True
)
def update_plot(n_clicks, selected_runs, selected_metrics_lists, data_source):
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
    
    # Determine source directory
    source_dir = DATA_DIR if data_source == 'example' else UPLOAD_DIR
    
    # Create traces for each run and metric combination
    fig = go.Figure()
    
    for run_name in selected_runs:
        run_path = source_dir / run_name
        
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
    
    # Update layout with legend positioned below the plot
    fig.update_layout(
        title="Evosep Data Traces",
        xaxis_title="Time (seconds)",
        yaxis_title="Value",
        hovermode='closest',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="center",
            x=0.5
        ),
        template="plotly_white",
        margin=dict(b=150)  # Add bottom margin for legend
    )
    
    return fig


if __name__ == '__main__':
    # Note: For production deployment, set debug=False to avoid exposing debug information
    # on the network. Debug mode is enabled here for development convenience.
    import sys
    debug_mode = '--debug' in sys.argv or len(sys.argv) == 1
    app.run_server(debug=debug_mode, host='0.0.0.0', port=8050)
