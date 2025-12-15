# EvoSep_Data_Traces

Tool allowing you to review EvoSep Data traces like pressure and flow rate

## Overview

This is a web-based application for viewing and analyzing Evosep Eno system data traces. The application allows users to:

- Select one or multiple run folders
- Choose specific metrics (pressure, flow rate, pump speed, etc.) from different pumps
- Generate interactive plots with time on the x-axis and selected metrics on the y-axis
- Overlay multiple runs and/or multiple metrics on the same plot

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. Clone or download this repository

2. Install required Python packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the web application:
```bash
python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:8050
```

3. The application will automatically load available run folders from the `ExampleData` directory

**Note for Network Access**: The application runs on `0.0.0.0:8050`, making it accessible to other devices on your local network. To access from another computer, use:
```
http://YOUR_HOST_IP:8050
```
Replace `YOUR_HOST_IP` with the IP address of the machine running the application (e.g., `http://192.168.1.100:8050`).

**Production Deployment**: For production use, run with debug mode disabled:
```bash
python app.py --no-debug
```

## Usage

### Data Source

Choose between two data sources:
- **Example Data**: Uses the pre-loaded run folders from the `ExampleData` directory
- **Upload Data**: Allows you to upload your own run data from your local computer

To upload your own data:
1. Select the "Upload Data" radio button
2. Click "Browse Local Folders" to select ZIP archives containing your run folders
3. The ZIP file should contain folders with the run data structure (see Data Format below)

### Selecting Runs

- Use the checkboxes in the "Select Runs" section to choose one or more run folders
- Multiple runs can be selected to overlay their data on the same plot
- **Search and Filter**: Use the search box and filter inputs to quickly find specific runs:
  - Search by run name
  - Filter by procedure name (e.g., "200 SPD")
  - Filter by sample name
- Run labels display metadata including date/time and procedure name for easy identification

### Selecting Metrics

- The "Select Metrics" section displays available metrics organized by pump (Pump A, Pump B, Pump C, Pump D, Pump HP)
- Each pump has multiple metric types:
  - Pressure [bar]
  - Actual flow [µL/min]
  - Setpoint
  - Displacement [µL]
  - Pump speed [µL/min]
- Check the boxes next to the metrics you want to plot
- Use "Select All" to quickly select all available metrics
- Use "Unselect All" to clear all selections

### Generating Plots

- Click the "Generate Plot" button to create an interactive plot
- The plot shows:
  - Time (in seconds) on the x-axis
  - Selected metric values on the y-axis
  - Different colors for each metric/run combination
  - **Legend positioned below the plot** for unobstructed viewing
- Hover over data points to see detailed values
- Use the Plotly toolbar to zoom, pan, or save the plot as an image

### UI Features

- **Scrollable Lists**: When working with many runs (30+), the run and metric lists are scrollable to keep the interface manageable
- **Side-by-Side Layout**: The selection panel is on the left (30%) and the plot is on the right (69%) for efficient use of screen space
- **Metadata Display**: Each run shows its date/time and procedure information in the label

## Data Format

The application expects data files in the following format:

- Directory structure: `ExampleData/[run_name]/[metric_files].txt`
- File naming: `Pump-[PUMP]_[METRIC].txt` (e.g., `Pump-HP_Pressure.txt`)
- File content: Tab-separated values with:
  - First line: Header with column names
  - Subsequent lines: Time (HH:MM:SS.mmm) and value
- Optional metadata file: `journal.txt` in each run folder containing:
  - Procedure.Name: The procedure name
  - Procedure.Logname: Log name with date/time
  - Procedure.Samplename: Sample identifier
  - Procedure.Vialposition: Vial position information

Example data file:
```
time	Pump HP:Pressure [bar]
00:00:00.072	176.400
00:00:00.085	175.600
```

Example journal.txt excerpt:
```
Procedure.Name:200 SPD
Procedure.Logname:200-SPD_2025-12-11_12-27-48
Procedure.Samplename:
Procedure.Vialposition:Slot3:2 (S3-A2)
```

## Technology Stack

- **Python**: Backend programming language
- **Dash**: Python framework for building web applications
- **Plotly**: Interactive plotting library
- **Pandas**: Data manipulation and analysis
