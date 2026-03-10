#!/usr/bin/env python
"""
Visualize CXI detector data with CrystFEL geometry applied using HoloViews/Bokeh.
"""

import sys
import os

# Add OM source to path
om_src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
sys.path.insert(0, om_src_path)

import h5py
import numpy as np
import holoviews as hv
from holoviews import opts

from om.lib.geometry import GeometryInformation, DataVisualizer

# Enable Bokeh backend for HoloViews
hv.extension("bokeh")


def main():
    # File paths
    cxi_file = "cxi101235425-r0121_16.cxi"
    geom_file = "jungfrau4M.geom"

    print(f"Loading CXI data from {cxi_file}...")
    # Read the first frame of detector data
    with h5py.File(cxi_file, "r") as f:
        data = f["/entry_1/data_1/data"][0]  # Shape: (4096, 1024)
        print(f"Data shape: {data.shape}")
        print(f"Data dtype: {data.dtype}")
        print(f"Data range: [{data.min():.2f}, {data.max():.2f}]")

    print(f"\nLoading geometry from {geom_file}...")
    # Load CrystFEL geometry
    geometry_info = GeometryInformation.from_file(
        geometry_filename=geom_file, geometry_format="crystfel"
    )

    # Get pixel maps for visualization
    pixel_maps = geometry_info.get_pixel_maps()
    print(f"Pixel maps generated:")
    print(f"  X map shape: {pixel_maps.x.shape}")
    print(f"  Y map shape: {pixel_maps.y.shape}")
    print(f"  Z map shape: {pixel_maps.z.shape}")

    print(f"\nApplying geometry to data...")
    # Create visualizer and apply geometry
    visualizer = DataVisualizer(pixel_maps=pixel_maps)

    # Get the assembled image with geometry applied
    assembled_image = visualizer.visualize_data(data=data)
    print(f"Assembled image shape: {assembled_image.shape}")
    print(
        f"Assembled image range: [{assembled_image.min():.2f}, {assembled_image.max():.2f}]"
    )

    print(f"\nCreating HoloViews visualization...")
    # Create HoloViews Image object
    # Use asinh scaling for better visibility with negative values
    # asinh is better than log for data with negative values
    img_data = np.arcsinh(assembled_image / 100.0)  # Scale factor for better contrast

    # Create the image with proper aspect ratio
    image = hv.Image(img_data, kdims=["x", "y"])

    # Configure plot options
    vmin = np.percentile(img_data[np.isfinite(img_data)], 1)
    vmax = np.percentile(img_data[np.isfinite(img_data)], 99)

    image.opts(
        opts.Image(
            cmap="viridis",
            width=800,
            height=800,
            colorbar=True,
            tools=["hover", "pan", "wheel_zoom", "box_zoom", "reset", "save"],
            title="Jungfrau 4M Detector - Frame 0 (arcsinh scale)",
            xlabel="X (pixels)",
            ylabel="Y (pixels)",
            clim=(vmin, vmax),
            aspect="equal",
        )
    )

    print("Displaying visualization...")
    print("Close the browser window to exit.")

    # Show the plot (opens in browser)
    hv.save(image, "detector_visualization.html", backend="bokeh")
    print("\nVisualization saved to: detector_visualization.html")
    print("Open this file in a web browser to view the interactive plot.")

    # Also display directly if running interactively
    return image


if __name__ == "__main__":
    img = main()
    # Display the image
    hv.output(img, backend="bokeh")
