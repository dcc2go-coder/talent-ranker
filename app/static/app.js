const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");
const jobDescription = document.getElementById("jobDescription");
const analyzeBtn = document.getElementById("analyzeBtn");
const clearBtn = document.getElementById("clearBtn");
const resultsSection = document.getElementById("resultsSection");
const resultBody = document.getElementById("resultBody");
const resultMeta = document.getElementById("resultMeta");
const chatSection = document.getElementById("chatSection");
const chatMessages = document.getElementById("chatMessages");
const chatInput = document.getElementById("chatInput");
const chatSendBtn = document.getElementById("chatSendBtn");
const setupAlert = document.getElementById("setupAlert");
const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const apiKeyInput = document.getElementById("apiKeyInput");
const modelInput = document.getElementById("modelInput");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const closeSettingsBtn = document.getElementById("closeSettingsBtn");

let selectedFiles = [];
let sessionId = null;
let isConfigured = false;

async function checkStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();
  isConfigured = data.configured;
  setupAlert.classList.toggle("hidden", isConfigured);
  if (data.model) modelInput.placeholder = data.model;
}

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  addFiles([...e.dataTransfer.files]);
});

fileInput.addEventListener("change", () => {
  addFiles([...fileInput.files]);
  fileInput.value = "";
});

function addFiles(files) {
  const allowed = [".pdf", ".docx", ".doc", ".txt"];
  for (const f of files) {
    const ext = "." + f.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) continue;
    if (!selectedFiles.some((s) => s.name === f.name && s.size === f.size)) {
      selectedFiles.push(f);
    }
  }
  renderFileList();
}

function renderFileList() {
  fileList.innerHTML = "";
  selectedFiles.forEach((f, i) => {
    const div = document.createElement("div");
    div.className = "file-item";
    div.innerHTML = `<span>📄 ${f.name}</span>`;
    const btn = document.createElement("button");
    btn.textContent = "Remove";
    btn.addEventListener("click", () => {
      selectedFiles.splice(i, 1);
      renderFileList();
    });
    div.appendChild(btn);
    fileList.appendChild(div);
  });
  analyzeBtn.disabled = selectedFiles.length === 0;
}

clearBtn.addEventListener("click", () => {
  selectedFiles = [];
  jobDescription.value = "";
  sessionId = null;
  renderFileList();
  resultsSection.classList.add("hidden");
  chatSection.classList.add("hidden");
  chatMessages.innerHTML = "";
  resultBody.textContent = "";
});

analyzeBtn.addEventListener("click", async () => {
  if (!isConfigured) {
    settingsModal.classList.remove("hidden");
    return;
  }

  const form = new FormData();
  selectedFiles.forEach((f) => form.append("resumes", f));
  form.append("job_description", jobDescription.value);

  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = '<span class="spinner"></span> Analyzing…';

  try {
    const res = await fetch("/api/analyze", { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Analysis failed");

    sessionId = data.session_id;
    resultBody.textContent = data.result;
    resultMeta.textContent = `Analyzed ${data.resume_count} resume${data.resume_count !== 1 ? "s" : ""}`;
    resultsSection.classList.remove("hidden");
    chatSection.classList.remove("hidden");
    chatMessages.innerHTML = "";
    resultsSection.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    alert(err.message);
  } finally {
    analyzeBtn.disabled = selectedFiles.length === 0;
    analyzeBtn.textContent = "Rank Candidates";
  }
});

async function sendChat(message) {
  if (!sessionId || !message.trim()) return;

  appendBubble("user", message);
  chatInput.value = "";
  chatSendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Chat failed");
    appendBubble("assistant", data.reply);
  } catch (err) {
    appendBubble("assistant", `Error: ${err.message}`);
  } finally {
    chatSendBtn.disabled = false;
  }
}

function appendBubble(role, text) {
  const div = document.createElement("div");
  div.className = `chat-bubble ${role}`;
  div.textContent = text;
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

chatSendBtn.addEventListener("click", () => sendChat(chatInput.value));
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendChat(chatInput.value);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    chatInput.value = chip.dataset.prompt;
    sendChat(chip.dataset.prompt);
  });
});

settingsBtn.addEventListener("click", () => settingsModal.classList.remove("hidden"));
closeSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) settingsModal.classList.add("hidden");
});

saveSettingsBtn.addEventListener("click", async () => {
  const api_key = apiKeyInput.value.trim();
  if (!api_key) {
    alert("Please enter an API key.");
    return;
  }
  const body = { api_key };
  if (modelInput.value.trim()) body.model = modelInput.value.trim();

  const res = await fetch("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    alert("Failed to save settings.");
    return;
  }
  isConfigured = true;
  setupAlert.classList.add("hidden");
  settingsModal.classList.add("hidden");
  apiKeyInput.value = "";
});

checkStatus();