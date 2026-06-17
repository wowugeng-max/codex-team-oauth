const form = document.getElementById("configForm");
const statusText = document.getElementById("statusText");
const statusPill = document.getElementById("statusPill");
const statusLabel = document.getElementById("statusLabel");
const startButton = document.getElementById("startButton");
const stopButton = document.getElementById("stopButton");
const saveButton = document.getElementById("saveButton");
const resetLogButton = document.getElementById("resetLogButton");
const logOutput = document.getElementById("logOutput");
const startedAt = document.getElementById("startedAt");
const stoppedAt = document.getElementById("stoppedAt");
const exitCode = document.getElementById("exitCode");

function fieldElements() {
  return Array.from(form.querySelectorAll("[data-field]"));
}

function collectConfig() {
  const config = {};
  for (const element of fieldElements()) {
    config[element.dataset.field] = element.value.trim();
  }
  return config;
}

function fillConfig(config) {
  for (const element of fieldElements()) {
    element.value = config[element.dataset.field] ?? "";
  }
}

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload;
}

function formatTime(value) {
  if (!value) {
    return "-";
  }
  return new Date(value * 1000).toLocaleString();
}

function setStatus(status) {
  const running = Boolean(status.running);
  statusPill.dataset.state = running ? "running" : "idle";
  statusLabel.textContent = running ? "Running" : "Idle";
  statusText.textContent = running ? "Process is running" : "Process is idle";
  startButton.disabled = running;
  stopButton.disabled = !running;
  startedAt.textContent = formatTime(status.started_at);
  stoppedAt.textContent = formatTime(status.stopped_at);
  exitCode.textContent = status.exit_code === null || status.exit_code === undefined ? "-" : String(status.exit_code);

  const shouldStickToBottom = logOutput.scrollTop + logOutput.clientHeight >= logOutput.scrollHeight - 20;
  logOutput.textContent = status.log || "";
  if (shouldStickToBottom) {
    logOutput.scrollTop = logOutput.scrollHeight;
  }
}

async function loadConfig() {
  const payload = await requestJson("/api/config");
  fillConfig(payload.config);
}

async function refreshStatus() {
  try {
    const status = await requestJson("/api/status");
    setStatus(status);
  } catch (error) {
    statusText.textContent = error.message;
  }
}

async function saveConfig() {
  saveButton.disabled = true;
  try {
    const payload = await requestJson("/api/config", {
      method: "POST",
      body: JSON.stringify({ config: collectConfig() }),
    });
    fillConfig(payload.config);
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
}

async function startRun() {
  const config = collectConfig();
  try {
    const runCount = Number.parseInt(config.RUN_COUNT || "1", 10);
    if (!Number.isInteger(runCount) || runCount < 1) {
      throw new Error("RUN_COUNT must be a positive integer");
    }
    const payload = await requestJson("/api/run", {
      method: "POST",
      body: JSON.stringify({ config, run_count: runCount }),
    });
    setStatus(payload.status);
  } catch (error) {
    statusText.textContent = error.message;
  }
}

async function stopRun() {
  try {
    const payload = await requestJson("/api/stop", {
      method: "POST",
      body: "{}",
    });
    setStatus(payload.status);
  } catch (error) {
    statusText.textContent = error.message;
  }
}

async function resetLog() {
  try {
    const payload = await requestJson("/api/log/reset", {
      method: "POST",
      body: "{}",
    });
    setStatus(payload.status);
  } catch (error) {
    statusText.textContent = error.message;
  }
}

saveButton.addEventListener("click", saveConfig);
startButton.addEventListener("click", startRun);
stopButton.addEventListener("click", stopRun);
resetLogButton.addEventListener("click", resetLog);

loadConfig().then(refreshStatus);
setInterval(refreshStatus, 1000);
