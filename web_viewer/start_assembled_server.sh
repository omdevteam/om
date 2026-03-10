#!/bin/bash
# Start the Bokeh server for pre-assembled CXI visualization

PYTHON_BIN="/sdf/home/v/valmar/Projects/OM/om/.pixi/envs/default/bin"

# Default CXI file
DEFAULT_CXI="/sdf/data/lcls/ds/prj/prjcwang31/results/proj-stream-to-ml/demo/runs/2026-0309-1549-23039077/cxi_output/mfxl1038923-r0278_20260309_155436_652134_chunk0006.cxi"

# Use provided file or default
CXI_FILE="${1:-$DEFAULT_CXI}"

echo "Starting Bokeh server for pre-assembled CXI visualization..."
echo "CXI file: $CXI_FILE"
echo "Server will be accessible at: http://$(hostname):5006/visualize_assembled_cxi_server"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"

$PYTHON_BIN/bokeh serve visualize_assembled_cxi_server.py \
    --args "$CXI_FILE" \
    --address 0.0.0.0 \
    --port 5006 \
    --allow-websocket-origin='*' \
    --show
