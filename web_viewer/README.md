# CXI Data Visualization with CrystFEL Geometry

This folder contains a script to visualize CXI detector data with CrystFEL geometry applied.

## Files

- `cxi101235425-r0121_16.cxi` - CXI data file containing 113 frames of 4096×1024 detector data
- `jungfrau4M.geom` - CrystFEL geometry file for Jungfrau 4M detector (32 panels)
- `visualize_cxi.py` - Python script to generate standalone HTML visualization
- `visualize_cxi_server.py` - Bokeh server application with interactive controls
- `start_server.sh` - Shell script to start the Bokeh server
- `detector_visualization.html` - Output HTML file from static visualization (generated)
- `README.md` - This documentation file

## Usage

### Option 1: Static HTML Visualization

Generate a standalone HTML file:

```bash
/sdf/home/v/valmar/Projects/OM/om/.pixi/envs/default/bin/python visualize_cxi.py
```

This will:
1. Load the first frame from the CXI file
2. Read the CrystFEL geometry file
3. Apply the geometry transformation using OM's geometry module
4. Create an interactive visualization using HoloViews/Bokeh
5. Save the result to `detector_visualization.html`

### Option 2: Bokeh Server (Interactive Multi-Frame Viewer)

Start the Bokeh server for network access:

```bash
./start_server.sh
```

Or manually:

```bash
/sdf/home/v/valmar/Projects/OM/om/.pixi/envs/default/bin/bokeh serve visualize_cxi_server.py \
    --address 0.0.0.0 \
    --port 5006 \
    --allow-websocket-origin='*'
```

Then access at: `http://<your-ip>:5006/visualize_cxi_server`

The Bokeh server provides:
- **Frame selector**: Browse through all 113 frames with a slider
- **Scaling options**: Linear, Log10, Arcsinh, or Sqrt scaling
- **Colormap selection**: Choose from Viridis, Plasma, Inferno, Magma, Cividis, Turbo
- **Auto/Manual scaling**: Automatically scale to percentiles or manually set min/max
- **Peak overlay**: View detected Bragg peaks overlaid on the detector image
- **Real-time updates**: Changes apply instantly
- **Network access**: Multiple users can view simultaneously

## How It Works

### Data Loading
The script reads detector data from `/entry_1/data_1/data` in the CXI file. The data has shape (113, 4096, 1024) representing 113 frames of detector data.

### Geometry Application
The Jungfrau 4M detector consists of 32 panels (8 ASICs each 256×256 pixels) arranged in a 2×4 module layout:

- **Module 0 (p0)**: Upper right quadrant
- **Module 1 (p1)**: Upper center-right
- **Module 2 (p2)**: Upper center-left  
- **Module 3 (p3)**: Upper left
- **Module 4 (p4)**: Lower right
- **Module 5 (p5)**: Lower center-right
- **Module 6 (p6)**: Lower center-left
- **Module 7 (p7)**: Lower left

The geometry file specifies the physical position and orientation of each panel using:
- `corner_x`, `corner_y`: Panel corner position in detector reference frame
- `fs`, `ss`: Fast-scan and slow-scan direction vectors
- `min_fs`, `max_fs`, `min_ss`, `max_ss`: Pixel range for each panel

The OM `GeometryInformation` class parses this geometry and creates pixel maps that describe where each pixel should be placed in the assembled image. The `DataVisualizer` class then applies these maps to transform the raw 4096×1024 data into a 2312×2218 assembled image showing the physical detector layout.

### Peak Detection Data

The CXI file contains detected Bragg peak positions stored at:
- `/entry_1/result_1/peakXPosRaw`: X coordinates in raw detector space
- `/entry_1/result_1/peakYPosRaw`: Y coordinates in raw detector space

Each frame can have up to 2048 detected peaks with sub-pixel precision (float32). The visualization automatically transforms these raw coordinates to the assembled image space using the same geometry transformation applied to the detector data. Peaks at position (0, 0) are filtered out as they represent empty slots in the peak array.

**Peak Statistics:**
- Valid peaks per frame: 6 to 871 (average ~83 peaks/frame)
- Coordinates: Sub-pixel precision in raw detector space
- Visualization: Red circles overlay on assembled image

### Visualization
The assembled image is displayed using:
- **Scaling**: arcsinh scaling to handle both positive and negative pixel values
- **Colormap**: Viridis colormap
- **Interactivity**: Pan, zoom, hover tools via Bokeh
- **Auto-scaling**: Color limits set to 1st-99th percentile for better contrast

## Output

The assembled detector image has shape (2312, 2218) pixels, showing all 8 modules in their physical arrangement with gaps between panels visible.

### Static HTML Output
Open `detector_visualization.html` in a web browser to view the interactive plot with pan/zoom/hover tools.

### Bokeh Server Interface
The server interface provides:

**Controls:**
- **Frame slider** (0-112): Navigate through all detector frames
- **Scaling buttons**: 
  - Linear: No transformation
  - Log10: Logarithmic scaling (shifts data to positive range)
  - Arcsinh: Inverse hyperbolic sine (handles negative values)
  - Sqrt: Square root scaling (shifts data to positive range)
- **Colormap dropdown**: Choose color palette for visualization
- **Auto/Manual scale toggle**: 
  - Auto: Uses 1st-99th percentile for color limits
  - Manual: Use sliders to set custom min/max values
- **Min/Max sliders**: Adjust color range when in manual mode
- **Show Peaks checkbox**: Toggle visibility of detected Bragg peaks (red circles)

**Display:**
- Current frame statistics (min/max values)
- Peak count for current frame
- Color range information
- Interactive pan, zoom, and reset tools
- Hover tool to inspect pixel values
- Detected peaks shown as red circles (toggleable via legend or checkbox)

**Performance:**
- Data stays on server (not sent to browser)
- Real-time frame updates
- Multiple users can connect simultaneously
