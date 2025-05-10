/**
 * Chart management for HydroFlow - Water Distribution Modeling
 */

// Chart manager object
const chartManager = {
  charts: {
    networkComponents: null,
    pipeDiameter: null,
    pipeLength: null,
    junctionElevation: null,
    pressure: null,
    flow: null,
    velocity: null,
  },

  /**
   * Render network statistics charts
   */
  renderNetworkStats: function (data) {
    if (!data) return;

    // Create sample data if network stats aren't available yet
    const stats = data.stats || this.createSampleNetworkStats();

    // Render network components pie chart
    this.renderNetworkComponentsChart(stats);

    // Render pipe diameter distribution chart
    this.renderPipeDiameterChart(stats);

    // Render pipe length distribution chart
    this.renderPipeLengthChart(stats);

    // Render junction elevation distribution chart
    this.renderJunctionElevationChart(stats);
  },

  /**
   * Create sample network statistics (for demo)
   */
  createSampleNetworkStats: function () {
    return {
      networkComponents: {
        labels: [
          "Junctions",
          "Pipes",
          "Reservoirs",
          "Tanks",
          "Valves",
          "Pumps",
        ],
        data: [156, 178, 1, 3, 2, 0],
      },
      pipeDiameter: {
        labels: [
          "0-50",
          "50-100",
          "100-150",
          "150-200",
          "200-250",
          "250-300",
          "300+",
        ],
        data: [12, 24, 56, 42, 28, 14, 2],
      },
      pipeLength: {
        labels: ["0-10", "10-50", "50-100", "100-200", "200-500", "500+"],
        data: [8, 22, 45, 62, 34, 7],
      },
      junctionElevation: {
        labels: [
          "240-245",
          "245-250",
          "250-255",
          "255-260",
          "260-265",
          "265-270",
          "270+",
        ],
        data: [15, 28, 42, 36, 22, 10, 3],
      },
    };
  },

  /**
   * Render network components pie chart
   */
  renderNetworkComponentsChart: function (stats) {
    const ctx = document
      .getElementById("network-components-chart")
      .getContext("2d");

    // Destroy existing chart if it exists
    if (this.charts.networkComponents) {
      this.charts.networkComponents.destroy();
    }

    // Create new chart
    this.charts.networkComponents = new Chart(ctx, {
      type: "pie",
      data: {
        labels: stats.networkComponents.labels,
        datasets: [
          {
            data: stats.networkComponents.data,
            backgroundColor: [
              "#0d6efd", // Blue - Junctions
              "#6c757d", // Gray - Pipes
              "#198754", // Green - Reservoirs
              "#ffc107", // Yellow - Tanks
              "#fd7e14", // Orange - Valves
              "#dc3545", // Red - Pumps
            ],
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: "right",
          },
          title: {
            display: false,
            text: "Network Components",
          },
        },
      },
    });
  },

  /**
   * Render pipe diameter distribution chart
   */
  renderPipeDiameterChart: function (stats) {
    const ctx = document.getElementById("pipe-diameter-chart").getContext("2d");

    // Destroy existing chart if it exists
    if (this.charts.pipeDiameter) {
      this.charts.pipeDiameter.destroy();
    }

    // Create new chart
    this.charts.pipeDiameter = new Chart(ctx, {
      type: "bar",
      data: {
        labels: stats.pipeDiameter.labels,
        datasets: [
          {
            label: "Number of Pipes",
            data: stats.pipeDiameter.data,
            backgroundColor: "#0d6efd",
            borderColor: "#0a58ca",
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Count",
            },
          },
          x: {
            title: {
              display: true,
              text: "Diameter Range (mm)",
            },
          },
        },
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: false,
            text: "Pipe Diameter Distribution",
          },
        },
      },
    });
  },

  /**
   * Render pipe length distribution chart
   */
  renderPipeLengthChart: function (stats) {
    const ctx = document.getElementById("pipe-length-chart").getContext("2d");

    // Destroy existing chart if it exists
    if (this.charts.pipeLength) {
      this.charts.pipeLength.destroy();
    }

    // Create new chart
    this.charts.pipeLength = new Chart(ctx, {
      type: "bar",
      data: {
        labels: stats.pipeLength.labels,
        datasets: [
          {
            label: "Number of Pipes",
            data: stats.pipeLength.data,
            backgroundColor: "#20c997",
            borderColor: "#198754",
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Count",
            },
          },
          x: {
            title: {
              display: true,
              text: "Length Range (m)",
            },
          },
        },
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: false,
            text: "Pipe Length Distribution",
          },
        },
      },
    });
  },

  /**
   * Render junction elevation distribution chart
   */
  renderJunctionElevationChart: function (stats) {
    const ctx = document
      .getElementById("junction-elevation-chart")
      .getContext("2d");

    // Destroy existing chart if it exists
    if (this.charts.junctionElevation) {
      this.charts.junctionElevation.destroy();
    }

    // Create new chart
    this.charts.junctionElevation = new Chart(ctx, {
      type: "bar",
      data: {
        labels: stats.junctionElevation.labels,
        datasets: [
          {
            label: "Number of Junctions",
            data: stats.junctionElevation.data,
            backgroundColor: "#6610f2",
            borderColor: "#6f42c1",
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            beginAtZero: true,
            title: {
              display: true,
              text: "Count",
            },
          },
          x: {
            title: {
              display: true,
              text: "Elevation Range (m)",
            },
          },
        },
        plugins: {
          legend: {
            display: false,
          },
          title: {
            display: false,
            text: "Junction Elevation Distribution",
          },
        },
      },
    });
  },

  /**
   * Render simulation results charts
   */
  renderResultCharts: function (results) {
    if (!results || !results.time_steps) return;

    // Render pressure chart
    this.renderPressureChart(results);

    // Render flow chart
    this.renderFlowChart(results);

    // Render velocity chart
    this.renderVelocityChart(results);
  },

  /**
   * Render pressure time series chart
   */
  renderPressureChart: function (results) {
    const ctx = document.getElementById("pressure-chart").getContext("2d");

    // Destroy existing chart if it exists
    if (this.charts.pressure) {
      this.charts.pressure.destroy();
    }

    // Create datasets for selected junctions
    const datasets = [];
    const colors = [
      "#0d6efd",
      "#dc3545",
      "#fd7e14",
      "#ffc107",
      "#198754",
      "#6610f2",
    ];

    // Select a few junctions for display
    const pressureNodes = results.nodes.pressure;
    const nodeIds = Object.keys(pressureNodes);

    // Limit to 6 junctions for clarity
    const selectedNodes = nodeIds.slice(0, 6);

    selectedNodes.forEach((nodeId, index) => {
      datasets.push({
        label: nodeId,
        data: pressureNodes[nodeId],
        borderColor: colors[index % colors.length],
        backgroundColor: "transparent",
        tension: 0.1,
        pointRadius: 2,
      });
    });

    // Create new chart
    this.charts.pressure = new Chart(ctx, {
      type: "line",
      data: {
        labels: results.time_steps,
        datasets: datasets,
      },
      options: {
        responsive: true,
        scales: {
          y: {
            title: {
              display: true,
              text: "Pressure (m)",
            },
          },
          x: {
            title: {
              display: true,
              text: "Time (hours)",
            },
          },
        },
        plugins: {
          title: {
            display: false,
            text: "Junction Pressures Over Time",
          },
        },
      },
    });
  },

  /**
   * Render flow time series chart
   */
  renderFlowChart: function (results) {
    const ctx = document.getElementById("flow-chart").getContext("2d");

    // Destroy existing chart if it exists
    if (this.charts.flow) {
      this.charts.flow.destroy();
    }

    // Create datasets for selected pipes
    const datasets = [];
    const colors = [
      "#0d6efd",
      "#dc3545",
      "#fd7e14",
      "#ffc107",
      "#198754",
      "#6610f2",
    ];

    // Select a few pipes for display
    const flowLinks = results.links.flow;
    const linkIds = Object.keys(flowLinks);

    // Limit to 6 pipes for clarity
    const selectedLinks = linkIds.slice(0, 6);

    selectedLinks.forEach((linkId, index) => {
      // Take absolute value of flow for visualization
      const flowData = flowLinks[linkId].map((flow) => Math.abs(flow));

      datasets.push({
        label: linkId,
        data: flowData,
        borderColor: colors[index % colors.length],
        backgroundColor: "transparent",
        tension: 0.1,
        pointRadius: 2,
      });
    });

    // Create new chart
    this.charts.flow = new Chart(ctx, {
      type: "line",
      data: {
        labels: results.time_steps,
        datasets: datasets,
      },
      options: {
        responsive: true,
        scales: {
          y: {
            title: {
              display: true,
              text: "Flow Rate (m³/s)",
            },
          },
          x: {
            title: {
              display: true,
              text: "Time (hours)",
            },
          },
        },
        plugins: {
          title: {
            display: false,
            text: "Pipe Flow Rates Over Time",
          },
        },
      },
    });
  },

  /**
   * Render velocity time series chart
   */
  renderVelocityChart: function (results) {
    const ctx = document.getElementById("velocity-chart").getContext("2d");

    // Destroy existing chart if it exists
    if (this.charts.velocity) {
      this.charts.velocity.destroy();
    }

    // Create datasets for selected pipes
    const datasets = [];
    const colors = [
      "#0d6efd",
      "#dc3545",
      "#fd7e14",
      "#ffc107",
      "#198754",
      "#6610f2",
    ];

    // Select a few pipes for display
    const velocityLinks = results.links.velocity;
    const linkIds = Object.keys(velocityLinks);

    // Limit to 6 pipes for clarity
    const selectedLinks = linkIds.slice(0, 6);

    selectedLinks.forEach((linkId, index) => {
      datasets.push({
        label: linkId,
        data: velocityLinks[linkId],
        borderColor: colors[index % colors.length],
        backgroundColor: "transparent",
        tension: 0.1,
        pointRadius: 2,
      });
    });

    // Create new chart
    this.charts.velocity = new Chart(ctx, {
      type: "line",
      data: {
        labels: results.time_steps,
        datasets: datasets,
      },
      options: {
        responsive: true,
        scales: {
          y: {
            title: {
              display: true,
              text: "Velocity (m/s)",
            },
          },
          x: {
            title: {
              display: true,
              text: "Time (hours)",
            },
          },
        },
        plugins: {
          title: {
            display: false,
            text: "Pipe Velocities Over Time",
          },
        },
      },
    });
  },

  /**
   * Update chart based on current time step
   */
  updateChartsForTimeStep: function (timeStep) {
    // Add time step indicator on all charts
    if (this.charts.pressure) {
      this.addTimeMarker(this.charts.pressure, timeStep);
    }

    if (this.charts.flow) {
      this.addTimeMarker(this.charts.flow, timeStep);
    }

    if (this.charts.velocity) {
      this.addTimeMarker(this.charts.velocity, timeStep);
    }
  },

  /**
   * Add a vertical marker for the current time step
   */
  addTimeMarker: function (chart, timeStep) {
    // Remove existing time marker annotation
    chart.options.plugins.annotation = chart.options.plugins.annotation || {};
    chart.options.plugins.annotation.annotations =
      chart.options.plugins.annotation.annotations || {};

    // Add new time marker annotation
    chart.options.plugins.annotation.annotations.timeMarker = {
      type: "line",
      xMin: timeStep,
      xMax: timeStep,
      borderColor: "rgba(255, 0, 0, 0.7)",
      borderWidth: 2,
      label: {
        content: "Current Time",
        enabled: true,
        position: "top",
      },
    };

    chart.update();
  },
};
