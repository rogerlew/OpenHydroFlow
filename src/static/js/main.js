/**
 * Main JavaScript file for HydroFlow - Water Distribution Modeling
 */

// Global application state
const appState = {
  dataCollected: false,
  dataProcessed: false,
  networkBuilt: false,
  simulationRun: false,
  currentTimeStep: 0,
  simulationResults: null,
  networkData: null,
  isPlaying: false,
  playInterval: null,
};

// DOM elements
const elements = {
  // Workflow steps
  stepDataCollection: document.getElementById("step-data-collection"),
  stepDataProcessing: document.getElementById("step-data-processing"),
  stepNetworkModeling: document.getElementById("step-network-modeling"),
  stepSimulation: document.getElementById("step-simulation"),

  // Buttons
  btnCollectData: document.getElementById("btn-collect-data"),
  btnProcessData: document.getElementById("btn-process-data"),
  btnBuildNetwork: document.getElementById("btn-build-network"),
  btnRunSimulation: document.getElementById("btn-run-simulation"),
  btnViewMap: document.getElementById("btn-view-map"),
  btnViewSchematic: document.getElementById("btn-view-schematic"),

  // Loading
  loadingModal: new bootstrap.Modal(document.getElementById("loading-modal")),
  loadingMessage: document.getElementById("loading-message"),
  loadingProgress: document.getElementById("loading-progress"),

  // Toast
  appToast: new bootstrap.Toast(document.getElementById("app-toast")),
  toastTitle: document.getElementById("toast-title"),
  toastMessage: document.getElementById("toast-message"),

  // Time controls
  timeSlider: document.getElementById("time-slider"),
  currentTime: document.getElementById("current-time"),
  btnTimePrev: document.getElementById("btn-time-prev"),
  btnTimePlay: document.getElementById("btn-time-play"),
  btnTimeNext: document.getElementById("btn-time-next"),

  // Form elements
  durationInput: document.getElementById("duration"),
  timeStepSelect: document.getElementById("time-step"),
  demandPatternCheck: document.getElementById("demand-pattern"),
};

// Initialize the application
document.addEventListener("DOMContentLoaded", function () {
  initApp();
});

/**
 * Initialize the application
 */
function initApp() {
  // Set up event listeners
  setupEventListeners();

  // Check for existing data and update workflow status
  checkExistingData();

  // Initialize network map
  initMap();
}

/**
 * Set up event listeners for UI interaction
 */
function setupEventListeners() {
  // Workflow step buttons
  elements.btnCollectData.addEventListener("click", handleCollectData);
  elements.btnProcessData.addEventListener("click", handleProcessData);
  elements.btnBuildNetwork.addEventListener("click", handleBuildNetwork);
  elements.btnRunSimulation.addEventListener("click", handleRunSimulation);

  // View buttons
  elements.btnViewMap.addEventListener("click", () => switchMapView("map"));
  elements.btnViewSchematic.addEventListener("click", () =>
    switchMapView("schematic")
  );

  // Time controls
  elements.timeSlider.addEventListener("input", handleTimeSliderChange);
  elements.btnTimePrev.addEventListener("click", handlePrevTimeStep);
  elements.btnTimePlay.addEventListener("click", handlePlayPause);
  elements.btnTimeNext.addEventListener("click", handleNextTimeStep);
}

/**
 * Check for existing data and update workflow status
 */
function checkExistingData() {
  // Use the API to check for existing data files
  api
    .checkExistingData()
    .then((data) => {
      if (data.hasRawData) {
        updateWorkflowStatus("dataCollected", true);
      }

      if (data.hasProcessedData) {
        updateWorkflowStatus("dataProcessed", true);
      }

      if (data.hasNetworkModel) {
        updateWorkflowStatus("networkBuilt", true);
        loadNetworkData();
      }

      if (data.hasSimulationResults) {
        updateWorkflowStatus("simulationRun", true);
        loadSimulationResults();
      }
    })
    .catch((error) => {
      console.error("Error checking existing data:", error);
    });
}

// ---------- Workflow Handlers ----------

/**
 * Handle data collection step
 */
function handleCollectData() {
  showLoading("Collecting water infrastructure data from APIs...", 0);

  api
    .collectData()
    .then((response) => {
      hideLoading();

      if (response.status === "success") {
        showToast(
          "Data Collection",
          "Water infrastructure data collected successfully."
        );
        updateWorkflowStatus("dataCollected", true);
      } else {
        showToast(
          "Error",
          "Failed to collect data: " + response.message,
          "error"
        );
      }
    })
    .catch((error) => {
      hideLoading();
      showToast("Error", "Failed to collect data: " + error.message, "error");
    });
}

/**
 * Handle data processing step
 */
function handleProcessData() {
  showLoading("Processing water infrastructure data...", 25);

  api
    .processData()
    .then((response) => {
      hideLoading();

      if (response.status === "success") {
        showToast(
          "Data Processing",
          "Water infrastructure data processed successfully."
        );
        updateWorkflowStatus("dataProcessed", true);
      } else {
        showToast(
          "Error",
          "Failed to process data: " + response.message,
          "error"
        );
      }
    })
    .catch((error) => {
      hideLoading();
      showToast("Error", "Failed to process data: " + error.message, "error");
    });
}

/**
 * Handle network building step
 */
function handleBuildNetwork() {
  showLoading("Building EPANET network model...", 50);

  api
    .buildNetwork()
    .then((response) => {
      hideLoading();

      if (response.status === "success") {
        showToast(
          "Network Modeling",
          "EPANET network model built successfully."
        );
        updateWorkflowStatus("networkBuilt", true);
        loadNetworkData();
      } else {
        showToast(
          "Error",
          "Failed to build network: " + response.message,
          "error"
        );
      }
    })
    .catch((error) => {
      hideLoading();
      showToast("Error", "Failed to build network: " + error.message, "error");
    });
}

/**
 * Handle simulation step
 */
function handleRunSimulation() {
  const duration = parseInt(elements.durationInput.value);
  const timeStep = parseFloat(elements.timeStepSelect.value);
  const useDemandPattern = elements.demandPatternCheck.checked;

  showLoading("Running hydraulic simulation...", 75);

  api
    .runSimulation({
      duration: duration,
      time_step: timeStep,
      use_demand_pattern: useDemandPattern,
    })
    .then((response) => {
      hideLoading();

      if (response.status === "success") {
        showToast("Simulation", "Hydraulic simulation completed successfully.");
        updateWorkflowStatus("simulationRun", true);
        loadSimulationResults();
      } else {
        showToast(
          "Error",
          "Failed to run simulation: " + response.message,
          "error"
        );
      }
    })
    .catch((error) => {
      hideLoading();
      showToast("Error", "Failed to run simulation: " + error.message, "error");
    });
}

// ---------- UI Helper Functions ----------

/**
 * Update workflow status and UI
 */
function updateWorkflowStatus(step, completed) {
  appState[step] = completed;

  // Update UI based on workflow status
  if (appState.dataCollected) {
    elements.stepDataCollection.classList.add("completed");
    elements.stepDataProcessing.classList.remove("disabled");
    elements.btnProcessData.disabled = false;
  }

  if (appState.dataProcessed) {
    elements.stepDataProcessing.classList.add("completed");
    elements.stepNetworkModeling.classList.remove("disabled");
    elements.btnBuildNetwork.disabled = false;
  }

  if (appState.networkBuilt) {
    elements.stepNetworkModeling.classList.add("completed");
    elements.stepSimulation.classList.remove("disabled");
    elements.btnRunSimulation.disabled = false;
    elements.btnViewMap.disabled = false;
    elements.btnViewSchematic.disabled = false;
  }

  if (appState.simulationRun) {
    elements.stepSimulation.classList.add("completed");
    // Update time slider max value based on simulation duration
    if (appState.simulationResults) {
      const timeSteps = appState.simulationResults.time_steps.length;
      elements.timeSlider.max = timeSteps - 1;
    }
  }
}

/**
 * Show loading modal with message and progress
 */
function showLoading(message, progress) {
  elements.loadingMessage.textContent = message;
  elements.loadingProgress.style.width = `${progress}%`;
  elements.loadingModal.show();
}

/**
 * Hide loading modal
 */
function hideLoading() {
  elements.loadingModal.hide();
}

/**
 * Show toast notification
 */
function showToast(title, message, type = "info") {
  elements.toastTitle.textContent = title;
  elements.toastMessage.textContent = message;

  // Set toast color based on type
  const toast = document.getElementById("app-toast");
  toast.classList.remove("bg-danger", "bg-success", "bg-info");

  switch (type) {
    case "error":
      toast.classList.add("bg-danger", "text-white");
      break;
    case "success":
      toast.classList.add("bg-success", "text-white");
      break;
    default:
      toast.classList.add("bg-info", "text-white");
  }

  elements.appToast.show();
}

/**
 * Switch between map and schematic views
 */
function switchMapView(view) {
  if (view === "map") {
    elements.btnViewMap.classList.add("active");
    elements.btnViewSchematic.classList.remove("active");
    mapManager.switchToMapView();
  } else {
    elements.btnViewMap.classList.remove("active");
    elements.btnViewSchematic.classList.add("active");
    mapManager.switchToSchematicView();
  }
}

// ---------- Data Loading Functions ----------

/**
 * Load network data and update UI
 */
function loadNetworkData() {
  api
    .getNetworkData()
    .then((data) => {
      appState.networkData = data;
      mapManager.renderNetwork(data);
      chartManager.renderNetworkStats(data);
    })
    .catch((error) => {
      console.error("Error loading network data:", error);
      showToast("Error", "Failed to load network data", "error");
    });
}

/**
 * Load simulation results and update UI
 */
function loadSimulationResults() {
  api
    .getSimulationResults()
    .then((data) => {
      appState.simulationResults = data;

      // Update time slider
      const timeSteps = data.time_steps.length;
      elements.timeSlider.max = timeSteps - 1;

      // Update UI with results
      updateSimulationStats(data);
      chartManager.renderResultCharts(data);
      mapManager.updateNetworkWithResults(data, 0); // Show first time step

      // Update current time display
      updateTimeDisplay(0);
    })
    .catch((error) => {
      console.error("Error loading simulation results:", error);
      showToast("Error", "Failed to load simulation results", "error");
    });
}

/**
 * Update simulation statistics display
 */
function updateSimulationStats(results) {
  // Update pressure stats
  if (results.stats && results.stats.pressure) {
    document.getElementById("min-pressure").textContent =
      results.stats.pressure.min.toFixed(2);
    document.getElementById("avg-pressure").textContent =
      results.stats.pressure.avg.toFixed(2);
    document.getElementById("max-pressure").textContent =
      results.stats.pressure.max.toFixed(2);
  }

  // Update flow stats
  if (results.stats && results.stats.flow) {
    document.getElementById("min-flow").textContent =
      results.stats.flow.min.toFixed(4);
    document.getElementById("avg-flow").textContent =
      results.stats.flow.avg.toFixed(4);
    document.getElementById("max-flow").textContent =
      results.stats.flow.max.toFixed(4);
  }

  // Update velocity stats
  if (results.stats && results.stats.velocity) {
    document.getElementById("min-velocity").textContent =
      results.stats.velocity.min.toFixed(2);
    document.getElementById("avg-velocity").textContent =
      results.stats.velocity.avg.toFixed(2);
    document.getElementById("max-velocity").textContent =
      results.stats.velocity.max.toFixed(2);
  }

  // Update simulation summary
  document.getElementById("simulation-duration").textContent =
    results.stats.duration_hours;
  document.getElementById("simulation-timestep").textContent = results
    .time_steps[1]
    ? parseInt(results.time_steps[1].split(":")[0]) -
      parseInt(results.time_steps[0].split(":")[0])
    : 1;
  document.getElementById("total-demand").textContent = (
    results.stats.flow.avg * 0.01
  ).toFixed(4);
  document.getElementById("simulation-status").textContent = "Completed";
}

// ---------- Time Control Functions ----------

/**
 * Handle time slider change
 */
function handleTimeSliderChange() {
  const timeStep = parseInt(elements.timeSlider.value);
  appState.currentTimeStep = timeStep;

  // Update map with current time step
  if (appState.simulationResults) {
    mapManager.updateNetworkWithResults(appState.simulationResults, timeStep);
  }

  // Update time display
  updateTimeDisplay(timeStep);
}

/**
 * Handle previous time step button
 */
function handlePrevTimeStep() {
  if (appState.currentTimeStep > 0) {
    appState.currentTimeStep--;
    elements.timeSlider.value = appState.currentTimeStep;
    handleTimeSliderChange();
  }
}

/**
 * Handle next time step button
 */
function handleNextTimeStep() {
  const maxTimeStep = parseInt(elements.timeSlider.max);
  if (appState.currentTimeStep < maxTimeStep) {
    appState.currentTimeStep++;
    elements.timeSlider.value = appState.currentTimeStep;
    handleTimeSliderChange();
  }
}

/**
 * Handle play/pause button
 */
function handlePlayPause() {
  if (appState.isPlaying) {
    // Pause
    clearInterval(appState.playInterval);
    appState.isPlaying = false;
    elements.btnTimePlay.innerHTML = '<i class="fas fa-play"></i>';
  } else {
    // Play
    appState.isPlaying = true;
    elements.btnTimePlay.innerHTML = '<i class="fas fa-pause"></i>';

    appState.playInterval = setInterval(() => {
      const maxTimeStep = parseInt(elements.timeSlider.max);

      if (appState.currentTimeStep < maxTimeStep) {
        appState.currentTimeStep++;
      } else {
        appState.currentTimeStep = 0; // Loop back to start
      }

      elements.timeSlider.value = appState.currentTimeStep;
      handleTimeSliderChange();
    }, 1000); // Update every second
  }
}

/**
 * Update time display
 */
function updateTimeDisplay(timeStep) {
  if (appState.simulationResults && appState.simulationResults.time_steps) {
    elements.currentTime.textContent =
      appState.simulationResults.time_steps[timeStep];
  }
}
