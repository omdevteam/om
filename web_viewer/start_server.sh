#!/bin/bash
# Start the Bokeh server for CXI visualization

PYTHON_BIN="/sdf/home/v/valmar/Projects/OM/om/.pixi/envs/default/bin"

echo "Starting Bokeh server for CXI visualization..."
echo "Server will be accessible at: http://$(hostname):5006/visualize_cxi_server"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"

$PYTHON_BIN/bokeh serve visualize_cxi_server.py \
    --address 0.0.0.0 \
    --port 5006 \
    --allow-websocket-origin='*' \
    --show
