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

3. When the page loads, enter the parent folder path that contains your Evosep run directories (for example, a serial-number folder such as `\\\server\share\S10782`) and click **Set Data Folder**

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

### Selecting the Data Folder

- Enter the parent folder path that contains all run subfolders at the top of the app and click **Set Data Folder**.
- The folder can be a UNC/network share (e.g., `\\proteomics-srv-04.swmed.edu\dfs\temporary_files\JO\evosep logs\S10782`) or any local directory.
- Use **Refresh Runs** if new runs are added to that folder while the app is open.
- (Optional) Define `EVOSEP_DEFAULT_DATA_PATH` in your environment or in a local `.env` file to pre-populate the path when the app starts. The included `.env` is set to the shared `S10782` folder for this deployment; remove or change it before publishing the project.

The parent directory is typically the instrument serial number and each subfolder represents a single run. Once a valid folder is set, every run appears in the sortable **Select Runs** table.

### Selecting Runs

- Use the table's multi-select checkboxes to choose one or more run folders
- Columns display Folder, Date & Time, Procedure, Sample, and Vial so you can compare metadata at a glance
- Click any column header to sort ascending/descending; multi-sort with Ctrl/Cmd-click
- Multiple runs can be selected at once to overlay their traces on a single plot
- Use the **Select All (Filtered)** button to grab every run currently visible after filtering, or **Clear Selection** to start over
- **Search and Filter**: Use the search box and filter inputs to quickly find specific runs:
  - Search by run name
  - Filter by procedure name (e.g., "200 SPD")
  - Filter by sample name
  - Filter by vial position
- Run metadata remains visible in the table while you filter and select

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
- Pump cards are displayed side-by-side for easy comparison, and Pump-HP automatically pre-selects **Actual flow** and **Pressure** for quick plotting

### Generating Plots

- Click the "Generate Plot" button to create an interactive plot
- The plot shows:
  - Time (in seconds) on the x-axis
  - Selected metric values on the y-axis
  - Different colors for each metric/run combination
  - **Legend positioned below the plot** for unobstructed viewing
- Hover over data points to see detailed values
- Use the Plotly toolbar to zoom, pan, or save the plot as an image

### Plot Options

- Toggle **Use dual Y axes (Pressure vs Flow)** to automatically separate high-pressure traces (left axis) from low-flow traces (right axis)
- Specify optional axis maximums (e.g., 400 bar and 6 µL/min) to quickly zoom each axis; leave blank to auto-scale
- Dual axes make it much easier to compare pressure and flow simultaneously without sacrificing detail

### UI Features

- **Sortable Run Table**: Column headers support native sorting and the table scrolls independently for large datasets
- **Vertical Layout**: Run selection, metric selection, and the plot now stack vertically for a full-width experience
- **Metadata Visibility**: Key run details (date/time, procedure, sample, vial) remain visible while filtering and selecting

## Data Format

The application expects data files in the following format:

- Directory structure: `[ParentFolder]/[run_name]/[metric_files].txt` (the parent folder is often the serial number such as `S10782`)
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
- **python-dotenv**: Loads environment variables (e.g., default data folder path)
