/**
 * Map management for HydroFlow - Water Distribution Modeling
 */

// Map manager object
const mapManager = {
  map: null,
  networkLayers: {
    junctions: null,
    pipes: null,
    reservoirs: null,
    tanks: null,
  },
  currentView: "map",

  /**
   * Initialize the map
   */
  initMap: function () {
    // Create Leaflet map
    this.map = L.map("network-map").setView([43.0731, -89.4012], 12); // Madison, WI coordinates

    // Add basemap layer
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(this.map);

    // Add empty layer groups for network components
    this.networkLayers.junctions = L.layerGroup().addTo(this.map);
    this.networkLayers.pipes = L.layerGroup().addTo(this.map);
    this.networkLayers.reservoirs = L.layerGroup().addTo(this.map);
    this.networkLayers.tanks = L.layerGroup().addTo(this.map);

    // Add map legend
    this.addLegend();

    // Invalidate size to ensure proper rendering
    setTimeout(() => {
      this.map.invalidateSize();
    }, 100);
  },

  /**
   * Add legend to the map
   */
  addLegend: function () {
    const legend = L.control({ position: "bottomright" });

    legend.onAdd = function (map) {
      const div = L.DomUtil.create("div", "network-legend");
      div.innerHTML = `
                <h6>Network Components</h6>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #0d6efd;"></div>
                    <span>Junction</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #6c757d;"></div>
                    <span>Pipe</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #198754;"></div>
                    <span>Reservoir</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background-color: #ffc107;"></div>
                    <span>Tank</span>
                </div>
            `;
      return div;
    };

    legend.addTo(this.map);
  },

  /**
   * Render network on the map
   */
  renderNetwork: function (data) {
    if (!data || !data.nodes || !data.links) {
      console.error("Invalid network data");
      return;
    }

    // Clear existing layers
    this.clearLayers();

    // Add nodes (junctions, reservoirs, tanks)
    this.addNodes(data.nodes.features);

    // Add links (pipes, pumps, valves)
    this.addLinks(data.links.features);

    // Fit map to network bounds
    this.fitMapToNetwork();
  },

  /**
   * Clear all network layers
   */
  clearLayers: function () {
    this.networkLayers.junctions.clearLayers();
    this.networkLayers.pipes.clearLayers();
    this.networkLayers.reservoirs.clearLayers();
    this.networkLayers.tanks.clearLayers();
  },

  /**
   * Add nodes to the map
   */
  addNodes: function (nodes) {
    nodes.forEach((node) => {
      const coords = [
        node.geometry.coordinates[1],
        node.geometry.coordinates[0],
      ];
      const props = node.properties;

      let marker;

      switch (props.type) {
        case "junction":
          marker = L.circleMarker(coords, {
            radius: 4,
            fillColor: "#0d6efd",
            color: "#0d6efd",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8,
          });

          marker.bindPopup(this.createJunctionPopup(props));
          this.networkLayers.junctions.addLayer(marker);
          break;

        case "reservoir":
          marker = L.circleMarker(coords, {
            radius: 8,
            fillColor: "#198754",
            color: "#198754",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8,
          });

          marker.bindPopup(this.createReservoirPopup(props));
          this.networkLayers.reservoirs.addLayer(marker);
          break;

        case "tank":
          marker = L.circleMarker(coords, {
            radius: 6,
            fillColor: "#ffc107",
            color: "#ffc107",
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8,
          });

          marker.bindPopup(this.createTankPopup(props));
          this.networkLayers.tanks.addLayer(marker);
          break;
      }

      // Store node ID for later lookup
      if (marker) {
        marker.nodeId = props.id;
      }
    });
  },

  /**
   * Add links to the map
   */
  addLinks: function (links) {
    links.forEach((link) => {
      const coords = link.geometry.coordinates.map((coord) => [
        coord[1],
        coord[0],
      ]);
      const props = link.properties;

      let polyline;

      switch (props.type) {
        case "pipe":
          polyline = L.polyline(coords, {
            color: "#6c757d",
            weight: props.diameter * 50, // Scale based on diameter
            opacity: 0.7,
          });

          polyline.bindPopup(this.createPipePopup(props));
          this.networkLayers.pipes.addLayer(polyline);
          break;

        case "pump":
          polyline = L.polyline(coords, {
            color: "#dc3545",
            weight: 3,
            opacity: 0.7,
            dashArray: "5, 5",
          });

          polyline.bindPopup(this.createPumpPopup(props));
          this.networkLayers.pipes.addLayer(polyline);
          break;

        case "valve":
          polyline = L.polyline(coords, {
            color: "#fd7e14",
            weight: 3,
            opacity: 0.7,
            dashArray: "10, 5",
          });

          polyline.bindPopup(this.createValvePopup(props));
          this.networkLayers.pipes.addLayer(polyline);
          break;
      }

      // Store link ID for later lookup
      if (polyline) {
        polyline.linkId = props.id;
      }
    });
  },

  /**
   * Create popup content for junction
   */
  createJunctionPopup: function (props) {
    return `
            <div class="popup-content">
                <div class="popup-title">${props.name || props.id}</div>
                <div class="popup-property">
                    <span class="popup-key">Type:</span>
                    <span class="popup-value">Junction</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Elevation:</span>
                    <span class="popup-value">${props.elevation.toFixed(
                      2
                    )} m</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Demand:</span>
                    <span class="popup-value">${props.base_demand.toFixed(
                      4
                    )} m³/s</span>
                </div>
            </div>
        `;
  },

  /**
   * Create popup content for reservoir
   */
  createReservoirPopup: function (props) {
    return `
            <div class="popup-content">
                <div class="popup-title">${props.name || props.id}</div>
                <div class="popup-property">
                    <span class="popup-key">Type:</span>
                    <span class="popup-value">Reservoir</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Head:</span>
                    <span class="popup-value">${props.base_head.toFixed(
                      2
                    )} m</span>
                </div>
            </div>
        `;
  },

  /**
   * Create popup content for tank
   */
  createTankPopup: function (props) {
    return `
            <div class="popup-content">
                <div class="popup-title">${props.name || props.id}</div>
                <div class="popup-property">
                    <span class="popup-key">Type:</span>
                    <span class="popup-value">Tank</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Elevation:</span>
                    <span class="popup-value">${props.elevation.toFixed(
                      2
                    )} m</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Initial Level:</span>
                    <span class="popup-value">${props.init_level.toFixed(
                      2
                    )} m</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Min Level:</span>
                    <span class="popup-value">${props.min_level.toFixed(
                      2
                    )} m</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Max Level:</span>
                    <span class="popup-value">${props.max_level.toFixed(
                      2
                    )} m</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Diameter:</span>
                    <span class="popup-value">${props.diameter.toFixed(
                      2
                    )} m</span>
                </div>
            </div>
        `;
  },

  /**
   * Create popup content for pipe
   */
  createPipePopup: function (props) {
    return `
            <div class="popup-content">
                <div class="popup-title">${props.name || props.id}</div>
                <div class="popup-property">
                    <span class="popup-key">Type:</span>
                    <span class="popup-value">Pipe</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Length:</span>
                    <span class="popup-value">${props.length.toFixed(
                      2
                    )} m</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Diameter:</span>
                    <span class="popup-value">${(props.diameter * 1000).toFixed(
                      2
                    )} mm</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Roughness:</span>
                    <span class="popup-value">${props.roughness.toFixed(
                      2
                    )}</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">From:</span>
                    <span class="popup-value">${props.start_node}</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">To:</span>
                    <span class="popup-value">${props.end_node}</span>
                </div>
            </div>
        `;
  },

  /**
   * Create popup content for pump
   */
  createPumpPopup: function (props) {
    return `
            <div class="popup-content">
                <div class="popup-title">${props.name || props.id}</div>
                <div class="popup-property">
                    <span class="popup-key">Type:</span>
                    <span class="popup-value">Pump</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">From:</span>
                    <span class="popup-value">${props.start_node}</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">To:</span>
                    <span class="popup-value">${props.end_node}</span>
                </div>
            </div>
        `;
  },

  /**
   * Create popup content for valve
   */
  createValvePopup: function (props) {
    return `
            <div class="popup-content">
                <div class="popup-title">${props.name || props.id}</div>
                <div class="popup-property">
                    <span class="popup-key">Type:</span>
                    <span class="popup-value">Valve (${props.valve_type})</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Status:</span>
                    <span class="popup-value">${props.status}</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">From:</span>
                    <span class="popup-value">${props.start_node}</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">To:</span>
                    <span class="popup-value">${props.end_node}</span>
                </div>
            </div>
        `;
  },

  /**
   * Fit map to network bounds
   */
  fitMapToNetwork: function () {
    const bounds = L.featureGroup([
      this.networkLayers.junctions,
      this.networkLayers.pipes,
      this.networkLayers.reservoirs,
      this.networkLayers.tanks,
    ]).getBounds();

    if (bounds.isValid()) {
      this.map.fitBounds(bounds, { padding: [20, 20] });
    }
  },

  /**
   * Switch between map and schematic views
   */
  switchToMapView: function () {
    this.currentView = "map";
    this.map.setView([43.0731, -89.4012], 12); // Madison, WI coordinates

    // Show basemap
    this.map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer) {
        layer.setOpacity(1);
      }
    });
  },

  switchToSchematicView: function () {
    this.currentView = "schematic";
    this.fitMapToNetwork();

    // Hide basemap
    this.map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer) {
        layer.setOpacity(0);
      }
    });
  },

  /**
   * Update network visualization with simulation results
   */
  updateNetworkWithResults: function (results, timeStep) {
    if (!results || !results.nodes || !results.links) {
      return;
    }

    // Update junctions with pressure data
    this.networkLayers.junctions.eachLayer((layer) => {
      const junctionId = layer.nodeId;

      if (junctionId && results.nodes.pressure[junctionId]) {
        const pressure = results.nodes.pressure[junctionId][timeStep];

        // Update marker style based on pressure
        const color = this.getPressureColor(pressure);
        layer.setStyle({
          fillColor: color,
          color: color,
        });

        // Update popup content
        const popup = layer.getPopup();
        if (popup) {
          const content = popup.getContent();
          const updatedContent = this.updateJunctionPopupWithResults(
            content,
            pressure
          );
          popup.setContent(updatedContent);
        }
      }
    });

    // Update pipes with flow data
    this.networkLayers.pipes.eachLayer((layer) => {
      const pipeId = layer.linkId;

      if (pipeId && results.links.flow[pipeId]) {
        const flow = results.links.flow[pipeId][timeStep];
        const velocity = results.links.velocity[pipeId][timeStep];

        // Update pipe style based on velocity
        const color = this.getVelocityColor(velocity);
        layer.setStyle({
          color: color,
        });

        // Update popup content
        const popup = layer.getPopup();
        if (popup) {
          const content = popup.getContent();
          const updatedContent = this.updatePipePopupWithResults(
            content,
            flow,
            velocity
          );
          popup.setContent(updatedContent);
        }
      }
    });
  },

  /**
   * Get color based on pressure value
   */
  getPressureColor: function (pressure) {
    // Color scale from low (red) to high (blue) pressure
    if (pressure < 20) {
      return "#dc3545"; // Red - low pressure
    } else if (pressure < 35) {
      return "#fd7e14"; // Orange - medium-low pressure
    } else if (pressure < 50) {
      return "#20c997"; // Teal - medium pressure
    } else if (pressure < 65) {
      return "#0d6efd"; // Blue - high pressure
    } else {
      return "#6610f2"; // Purple - very high pressure
    }
  },

  /**
   * Get color based on velocity value
   */
  getVelocityColor: function (velocity) {
    // Color scale from low (blue) to high (red) velocity
    if (velocity < 0.5) {
      return "#0d6efd"; // Blue - low velocity
    } else if (velocity < 1.0) {
      return "#20c997"; // Teal - medium-low velocity
    } else if (velocity < 1.5) {
      return "#ffc107"; // Yellow - medium velocity
    } else if (velocity < 2.0) {
      return "#fd7e14"; // Orange - medium-high velocity
    } else {
      return "#dc3545"; // Red - high velocity
    }
  },

  /**
   * Update junction popup with simulation results
   */
  updateJunctionPopupWithResults: function (content, pressure) {
    // Check if results already added
    if (content.includes("Current Pressure")) {
      // Replace existing values
      return content.replace(
        /<span class="popup-value">\d+\.\d+ m<\/span>/g,
        `<span class="popup-value">${pressure.toFixed(2)} m</span>`
      );
    } else {
      // Add result to popup
      return content.replace(
        "</div>",
        `</div>
                <div class="popup-property">
                    <span class="popup-key">Current Pressure:</span>
                    <span class="popup-value">${pressure.toFixed(2)} m</span>
                </div>`
      );
    }
  },

  /**
   * Update pipe popup with simulation results
   */
  updatePipePopupWithResults: function (content, flow, velocity) {
    // Check if results already added
    if (content.includes("Current Flow")) {
      // Replace existing values
      return content
        .replace(
          /<span class="popup-value">\-?\d+\.\d+ m³\/s<\/span>/g,
          `<span class="popup-value">${flow.toFixed(4)} m³/s</span>`
        )
        .replace(
          /<span class="popup-value">\d+\.\d+ m\/s<\/span>/g,
          `<span class="popup-value">${velocity.toFixed(2)} m/s</span>`
        );
    } else {
      // Add results to popup
      return content.replace(
        "</div>",
        `</div>
                <div class="popup-property">
                    <span class="popup-key">Current Flow:</span>
                    <span class="popup-value">${flow.toFixed(4)} m³/s</span>
                </div>
                <div class="popup-property">
                    <span class="popup-key">Current Velocity:</span>
                    <span class="popup-value">${velocity.toFixed(2)} m/s</span>
                </div>`
      );
    }
  },
};

// Initialize map when page loads
function initMap() {
  mapManager.initMap();
}
