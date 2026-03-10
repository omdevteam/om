#!/usr/bin/env python
"""
Bokeh server application to visualize CXI detector data with CrystFEL geometry.
Interactive controls for frame selection, colormap, and scaling.

Usage:
    bokeh serve visualize_cxi_server.py --address 0.0.0.0 --allow-websocket-origin='*'

Then access at: http://<your-ip>:5006/visualize_cxi_server
"""

import sys
import os

# Add OM source to path
om_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, om_src_path)

import h5py
import numpy as np
from bokeh.plotting import figure
from bokeh.models import (
    ColorBar,
    LinearColorMapper,
    Select,
    Slider,
    Div,
    RadioButtonGroup,
    CheckboxGroup,
    Button,
)
from bokeh.layouts import column, row
from bokeh.palettes import (
    Viridis256,
    Plasma256,
    Inferno256,
    Magma256,
    Cividis256,
    Turbo256,
)
from bokeh.io import curdoc

from om.lib.geometry import GeometryInformation, DataVisualizer

# File paths
CXI_FILE = "cxi101235425-r0121_16.cxi"
GEOM_FILE = "jungfrau4M.geom"

# Available colormaps
COLORMAPS = {
    "Viridis": Viridis256,
    "Plasma": Plasma256,
    "Inferno": Inferno256,
    "Magma": Magma256,
    "Cividis": Cividis256,
    "Turbo": Turbo256,
}


# Scaling functions
def scale_linear(data):
    """Linear scaling"""
    return data


def scale_log(data):
    """Log10 scaling (shifts negative values)"""
    shifted = data - data.min() + 1
    return np.log10(shifted)


def scale_arcsinh(data):
    """Arcsinh scaling (handles negative values well)"""
    return np.arcsinh(data / 100.0)


def scale_sqrt(data):
    """Square root scaling (shifts negative values)"""
    shifted = data - data.min()
    return np.sqrt(shifted)


SCALING_FUNCTIONS = {
    "Linear": scale_linear,
    "Log10": scale_log,
    "Arcsinh": scale_arcsinh,
    "Sqrt": scale_sqrt,
}

SCALING_NAMES = list(SCALING_FUNCTIONS.keys())

# Global variables for data and geometry
print("Loading CXI data...")
h5_file = h5py.File(CXI_FILE, "r")
detector_data = h5_file["/entry_1/data_1/data"]
num_frames = detector_data.shape[0]
print(f"Loaded {num_frames} frames of shape {detector_data.shape[1:]}")

# Load peak data
print("Loading peak data...")
peak_x_raw = h5_file["/entry_1/result_1/peakXPosRaw"][:]
peak_y_raw = h5_file["/entry_1/result_1/peakYPosRaw"][:]
print(f"Loaded peak data: {peak_x_raw.shape}")

print("Loading geometry...")
geometry_info = GeometryInformation.from_file(
    geometry_filename=GEOM_FILE, geometry_format="crystfel"
)
pixel_maps = geometry_info.get_pixel_maps()
visualizer = DataVisualizer(pixel_maps=pixel_maps)
print("Geometry loaded successfully")

# Get the assembled image shape
test_assembled = visualizer.visualize_data(data=detector_data[0])
img_height, img_width = test_assembled.shape
print(f"Assembled image shape: {img_height} x {img_width}")

# Get visualization pixel maps for transforming peak coordinates
vis_pixel_maps = visualizer.get_visualization_pixel_maps()
print("Visualization pixel maps retrieved")


# Create the Bokeh document
def create_app(doc):
    """Create the Bokeh application"""

    # Initial state
    current_frame = 0
    current_colormap = "Viridis"
    current_scaling = "Arcsinh"
    auto_scale = True
    manual_vmin = 0.0
    manual_vmax = 1.0
    show_peaks = True
    auto_play = False
    auto_callback = None

    # Load and process initial frame
    def get_processed_frame(frame_idx, scaling_name):
        """Load a frame, apply geometry, and scale it"""
        raw_data = detector_data[frame_idx]
        assembled = visualizer.visualize_data(data=raw_data)
        scaled = SCALING_FUNCTIONS[scaling_name](assembled)
        # Replace any infinities or NaNs
        scaled = np.nan_to_num(scaled, nan=0.0, posinf=0.0, neginf=0.0)
        return scaled

    def transform_peaks_to_assembled(frame_idx):
        """Transform peak coordinates from raw detector to assembled image space"""
        # Get raw peak coordinates for this frame
        x_raw = peak_x_raw[frame_idx]
        y_raw = peak_y_raw[frame_idx]

        # Filter out invalid peaks (0, 0)
        valid_mask = (x_raw != 0) | (y_raw != 0)
        x_valid = x_raw[valid_mask]
        y_valid = y_raw[valid_mask]

        # Transform coordinates using visualization pixel maps
        # The raw coordinates are in (fs, ss) = (x, y) format
        # We need to convert to integer indices for lookup
        x_indices = np.clip(x_valid.astype(int), 0, vis_pixel_maps.x.shape[1] - 1)
        y_indices = np.clip(y_valid.astype(int), 0, vis_pixel_maps.x.shape[0] - 1)

        # Look up the assembled positions
        x_assembled = vis_pixel_maps.x[y_indices, x_indices]
        y_assembled = vis_pixel_maps.y[y_indices, x_indices]

        return x_assembled, y_assembled

    # Get initial frame
    img_data = get_processed_frame(current_frame, current_scaling)

    # Create color mapper
    if auto_scale:
        vmin = np.percentile(img_data[img_data != 0], 1)
        vmax = np.percentile(img_data[img_data != 0], 99)
    else:
        vmin = manual_vmin
        vmax = manual_vmax

    color_mapper = LinearColorMapper(
        palette=COLORMAPS[current_colormap], low=vmin, high=vmax
    )

    # Create figure
    p = figure(
        width=900,
        height=900,
        title=f"Jungfrau 4M - Frame {current_frame}/{num_frames - 1} - {current_scaling} scaling",
        x_range=(0, img_width),
        y_range=(0, img_height),
        tools="pan,wheel_zoom,box_zoom,reset,save",
        active_scroll="wheel_zoom",
    )

    # Add image
    image_renderer = p.image(
        image=[img_data],
        x=0,
        y=0,
        dw=img_width,
        dh=img_height,
        color_mapper=color_mapper,
    )

    # Add colorbar
    color_bar = ColorBar(
        color_mapper=color_mapper, width=15, location=(0, 0), title="Intensity"
    )
    p.add_layout(color_bar, "right")

    # Add peak overlay
    peak_x_assembled, peak_y_assembled = transform_peaks_to_assembled(current_frame)
    peak_circles = p.circle(
        x=peak_x_assembled,
        y=peak_y_assembled,
        size=8,
        fill_color=None,
        line_color="red",
        line_width=2,
        alpha=0.8,
        legend_label=f"Peaks ({len(peak_x_assembled)})",
    )

    # Make legend interactive
    p.legend.click_policy = "hide"
    p.legend.location = "top_right"

    # Info display
    info_div = Div(
        text=f"""
        <b>Data Info:</b><br>
        Shape: {detector_data.shape}<br>
        Current frame range: [{detector_data[current_frame].min():.2f}, {detector_data[current_frame].max():.2f}]<br>
        Assembled shape: {img_height} x {img_width}<br>
        Peaks: {len(peak_x_assembled)}<br>
        Color range: [{vmin:.2f}, {vmax:.2f}]
        """,
        width=400,
        height=140,
    )

    # Frame selector
    frame_slider = Slider(
        start=0,
        end=num_frames - 1,
        value=current_frame,
        step=1,
        title="Frame Index",
        width=400,
    )

    # Colormap selector
    colormap_select = Select(
        title="Colormap",
        value=current_colormap,
        options=list(COLORMAPS.keys()),
        width=200,
    )

    # Scaling selector
    scaling_buttons = RadioButtonGroup(
        labels=SCALING_NAMES, active=SCALING_NAMES.index(current_scaling), width=400
    )

    # Auto-scale toggle
    autoscale_buttons = RadioButtonGroup(
        labels=["Auto Scale", "Manual Scale"], active=0 if auto_scale else 1, width=400
    )

    # Manual scale sliders (initially disabled)
    vmin_slider = Slider(
        start=-10,
        end=10,
        value=vmin,
        step=0.1,
        title="Min Value",
        width=400,
        disabled=auto_scale,
    )

    vmax_slider = Slider(
        start=-10,
        end=10,
        value=vmax,
        step=0.1,
        title="Max Value",
        width=400,
        disabled=auto_scale,
    )

    # Peak visibility toggle
    peak_checkbox = CheckboxGroup(
        labels=["Show Peaks"], active=[0] if show_peaks else [], width=400
    )

    # Auto-play button
    auto_button = Button(label="▶ Start Auto Play", button_type="success", width=400)

    # Auto-advance function
    def auto_advance():
        """Advance to the next frame"""
        nonlocal current_frame
        # Advance frame
        current_frame = (current_frame + 1) % num_frames
        frame_slider.value = current_frame

    # Toggle auto-play
    def toggle_auto_play():
        """Start or stop auto-play mode"""
        nonlocal auto_play, auto_callback
        auto_play = not auto_play

        if auto_play:
            # Start auto-play
            auto_button.label = "⏸ Stop Auto Play"
            auto_button.button_type = "danger"
            # Add periodic callback (2000ms = 2 seconds)
            auto_callback = doc.add_periodic_callback(auto_advance, 2000)
        else:
            # Stop auto-play
            auto_button.label = "▶ Start Auto Play"
            auto_button.button_type = "success"
            # Remove periodic callback
            if auto_callback is not None:
                doc.remove_periodic_callback(auto_callback)
                auto_callback = None

    # Update function
    def update():
        """Update the visualization"""
        nonlocal \
            current_frame, \
            current_colormap, \
            current_scaling, \
            auto_scale, \
            manual_vmin, \
            manual_vmax, \
            show_peaks

        # Get current values
        current_frame = frame_slider.value
        current_colormap = colormap_select.value
        current_scaling = SCALING_NAMES[scaling_buttons.active]
        auto_scale = autoscale_buttons.active == 0
        show_peaks = 0 in peak_checkbox.active

        # Process frame
        img_data = get_processed_frame(current_frame, current_scaling)

        # Update color range
        if auto_scale:
            vmin = np.percentile(img_data[img_data != 0], 1)
            vmax = np.percentile(img_data[img_data != 0], 99)
            vmin_slider.value = vmin
            vmax_slider.value = vmax
            vmin_slider.disabled = True
            vmax_slider.disabled = True
        else:
            vmin = vmin_slider.value
            vmax = vmax_slider.value
            vmin_slider.disabled = False
            vmax_slider.disabled = False

        manual_vmin = vmin
        manual_vmax = vmax

        # Update color mapper
        color_mapper.palette = COLORMAPS[current_colormap]
        color_mapper.low = vmin
        color_mapper.high = vmax

        # Update image
        image_renderer.data_source.data["image"] = [img_data]

        # Update peaks
        peak_x_new, peak_y_new = transform_peaks_to_assembled(current_frame)
        peak_circles.data_source.data = {"x": peak_x_new, "y": peak_y_new}
        # Update legend label through the legend items
        if p.legend and len(p.legend) > 0:
            for legend in p.legend:
                for item in legend.items:
                    if peak_circles in item.renderers:
                        item.label = {"value": f"Peaks ({len(peak_x_new)})"}
        peak_circles.visible = show_peaks

        # Update title
        p.title.text = f"Jungfrau 4M - Frame {current_frame}/{num_frames - 1} - {current_scaling} scaling"

        # Update info
        raw_frame = detector_data[current_frame]
        info_div.text = f"""
        <b>Data Info:</b><br>
        Shape: {detector_data.shape}<br>
        Current frame range: [{raw_frame.min():.2f}, {raw_frame.max():.2f}]<br>
        Assembled shape: {img_height} x {img_width}<br>
        Peaks: {len(peak_x_new)}<br>
        Color range: [{vmin:.2f}, {vmax:.2f}]
        """

    # Attach callbacks
    frame_slider.on_change("value", lambda attr, old, new: update())
    colormap_select.on_change("value", lambda attr, old, new: update())
    scaling_buttons.on_change("active", lambda attr, old, new: update())
    autoscale_buttons.on_change("active", lambda attr, old, new: update())
    vmin_slider.on_change("value", lambda attr, old, new: update())
    vmax_slider.on_change("value", lambda attr, old, new: update())
    peak_checkbox.on_change("active", lambda attr, old, new: update())
    auto_button.on_click(toggle_auto_play)

    # Layout
    controls = column(
        Div(text="<h2>Jungfrau 4M Detector Visualization</h2>", width=400),
        info_div,
        Div(text="<b>Frame Selection:</b>", width=400),
        frame_slider,
        auto_button,
        Div(text="<b>Scaling:</b>", width=400),
        scaling_buttons,
        Div(text="<b>Color Settings:</b>", width=400),
        colormap_select,
        autoscale_buttons,
        vmin_slider,
        vmax_slider,
        Div(text="<b>Peak Display:</b>", width=400),
        peak_checkbox,
    )

    layout = row(controls, p)

    doc.add_root(layout)
    doc.title = "CXI Detector Viewer"


# Create the application
create_app(curdoc())
