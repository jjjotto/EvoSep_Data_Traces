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

## Usage

### Selecting Runs

- Use the checkboxes in the "Select Runs" section to choose one or more run folders
- Multiple runs can be selected to overlay their data on the same plot

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
- Hover over data points to see detailed values
- Use the Plotly toolbar to zoom, pan, or save the plot as an image

## Data Format

The application expects data files in the following format:

- Directory structure: `ExampleData/[run_name]/[metric_files].txt`
- File naming: `Pump-[PUMP]_[METRIC].txt` (e.g., `Pump-HP_Pressure.txt`)
- File content: Tab-separated values with:
  - First line: Header with column names
  - Subsequent lines: Time (HH:MM:SS.mmm) and value

Example:
```
time	Pump HP:Pressure [bar]
00:00:00.072	176.400
00:00:00.085	175.600
```

## Technology Stack

- **Python**: Backend programming language
- **Dash**: Python framework for building web applications
- **Plotly**: Interactive plotting library
- **Pandas**: Data manipulation and analysis
