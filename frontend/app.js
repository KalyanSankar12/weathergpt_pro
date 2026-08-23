// ---------------------------------------------------------
// WeatherGPT frontend logic.
// Talks to the FastAPI backend running on the same origin
// (since main.py serves this frontend directly), so all API
// calls use relative paths like "/api/weather/current".
// ---------------------------------------------------------

const API = ""; // same-origin; change to "http://localhost:8000" if serving frontend separately

let currentLocation = "Indore";
let currentLanguage = "en";
let hourlyChartInstance = null;
let climateChartInstance = null;

// ---------------- Tabs ----------------
document.querySelectorAll(".tab").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");

    if (btn.dataset.tab === "alerts") loadAlerts();
  });
});

// ---------------- Location & language controls ----------------
document.getElementById("locationGo").addEventListener("click", () => {
  currentLocation = document.getElementById("locationInput").value.trim() || "Indore";
  loadDashboard();
});
document.getElementById("locationInput").addEventListener("keydown", e => {
  if (e.key === "Enter") document.getElementById("locationGo").click();
});
document.getElementById("langSelect").addEventListener("change", e => {
  currentLanguage = e.target.value;
});

// ---------------- Health / demo mode badge ----------------
async function loadHealth() {
  try {
    const res = await fetch(`${API}/api/health`);
    const data = await res.json();
    const badge = document.getElementById("demoModeBadge");
    badge.textContent = data.demo_mode ? "DEMO MODE" : "LIVE MODE";
  } catch (e) {
    console.error("health check failed", e);
  }
}

// ---------------- Dashboard: current weather ----------------
async function loadCurrentWeather() {
  document.getElementById("currentLoading").classList.remove("hidden");
  document.getElementById("currentContent").classList.add("hidden");
  try {
    const res = await fetch(`${API}/api/weather/current?location=${encodeURIComponent(currentLocation)}`);
    const d = await res.json();

    document.getElementById("curTemp").textContent = `${Math.round(d.temperature)}°`;
    document.getElementById("curCondition").textContent = d.condition;
    document.getElementById("curFeels").textContent = `${Math.round(d.feels_like)}°`;
    document.getElementById("curHumidity").textContent = `${d.humidity}%`;
    document.getElementById("curWind").textContent = `${d.wind_speed} km/h`;
    document.getElementById("curPressure").textContent = `${d.pressure} hPa`;
    document.getElementById("curVisibility").textContent = `${d.visibility} km`;
    document.getElementById("curRain").textContent = `${d.rain_probability}%`;
    document.getElementById("curSource").textContent = `source: ${d.data_source}`;

    document.getElementById("currentLoading").classList.add("hidden");
    document.getElementById("currentContent").classList.remove("hidden");
  } catch (e) {
    document.getElementById("currentLoading").textContent = "Could not load weather. Is the backend running?";
  }
}

// ---------------- Dashboard: hourly chart ----------------
async function loadHourly() {
  try {
    const res = await fetch(`${API}/api/weather/hourly?location=${encodeURIComponent(currentLocation)}&hours=12`);
    const d = await res.json();
    const labels = d.hourly.map(h => h.time);
    const temps = d.hourly.map(h => h.temperature);

    const ctx = document.getElementById("hourlyChart");
    if (hourlyChartInstance) hourlyChartInstance.destroy();
    hourlyChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Temp (°C)",
          data: temps,
          borderColor: "#4da3ff",
          backgroundColor: "rgba(77,163,255,0.15)",
          tension: 0.35,
          fill: true,
        }],
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#8a97b3" }, grid: { color: "#24324f" } },
          y: { ticks: { color: "#8a97b3" }, grid: { color: "#24324f" } },
        },
      },
    });
  } catch (e) {
    console.error("hourly load failed", e);
  }
}

// ---------------- Dashboard: 7-day forecast row ----------------
async function loadForecast() {
  try {
    const res = await fetch(`${API}/api/weather/forecast?location=${encodeURIComponent(currentLocation)}&days=7`);
    const d = await res.json();
    const row = document.getElementById("forecastRow");
    row.innerHTML = "";
    d.forecast.forEach(day => {
      const el = document.createElement("div");
      el.className = "forecast-day";
      el.innerHTML = `
        <div class="fd-name">${day.day_name.slice(0, 3)}</div>
        <div class="fd-cond">${conditionEmoji(day.condition)}</div>
        <div class="fd-temp">${Math.round(day.temp_max)}° / ${Math.round(day.temp_min)}°</div>
        <div class="fd-rain">${day.rain_probability}% rain</div>
      `;
      row.appendChild(el);
    });
  } catch (e) {
    console.error("forecast load failed", e);
  }
}

function conditionEmoji(condition) {
  const c = condition.toLowerCase();
  if (c.includes("thunder")) return "⛈️";
  if (c.includes("rain")) return "🌧️";
  if (c.includes("cloud")) return "☁️";
  if (c.includes("haze") || c.includes("fog")) return "🌫️";
  return "☀️";
}

// ---------------- Dashboard: climate trends chart ----------------
async function loadClimate() {
  try {
    const res = await fetch(`${API}/api/climate/trends?location=${encodeURIComponent(currentLocation)}`);
    const d = await res.json();
    const ctx = document.getElementById("climateChart");
    if (climateChartInstance) climateChartInstance.destroy();
    climateChartInstance = new Chart(ctx, {
      type: "bar",
      data: {
        labels: d.months,
        datasets: [
          { label: "Rainfall (mm)", data: d.monthly_rainfall_mm, backgroundColor: "#4da3ff", yAxisID: "y" },
          { label: "Avg Temp (°C)", data: d.monthly_avg_temp_c, type: "line", borderColor: "#f5a524", yAxisID: "y1" },
        ],
      },
      options: {
        plugins: { legend: { labels: { color: "#e7ecf5" } } },
        scales: {
          x: { ticks: { color: "#8a97b3" }, grid: { display: false } },
          y: { position: "left", ticks: { color: "#8a97b3" }, grid: { color: "#24324f" } },
          y1: { position: "right", ticks: { color: "#8a97b3" }, grid: { display: false } },
        },
      },
    });
  } catch (e) {
    console.error("climate load failed", e);
  }
}

function loadDashboard() {
  loadCurrentWeather();
  loadHourly();
  loadForecast();
  loadClimate();
}

// ---------------- Chat ----------------
const chatWindow = document.getElementById("chatWindow");

function addChatBubble(text, sender, meta) {
  const wrap = document.createElement("div");
  wrap.className = `chat-msg ${sender}`;
  const bubble = document.createElement("div");
  bubble.className = "chat-bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);
  if (meta) {
    const metaEl = document.createElement("div");
    metaEl.className = "chat-meta";
    metaEl.textContent = meta;
    wrap.appendChild(metaEl);
  }
  chatWindow.appendChild(wrap);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendChat() {
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;
  addChatBubble(message, "user");
  input.value = "";

  addChatBubble("Thinking…", "bot");
  const thinkingBubble = chatWindow.lastChild;

  try {
    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, language: currentLanguage }),
    });
    const d = await res.json();
    thinkingBubble.remove();
    addChatBubble(d.reply, "bot", `${d.location || ""} · ${d.intent} · data: ${d.data_source}`);
    speak(d.reply);
  } catch (e) {
    thinkingBubble.remove();
    addChatBubble("Sorry, I couldn't reach the WeatherGPT backend. Is it running?", "bot");
  }
}

document.getElementById("chatSend").addEventListener("click", sendChat);
document.getElementById("chatInput").addEventListener("keydown", e => {
  if (e.key === "Enter") sendChat();
});

// ---------------- Voice (browser Speech Recognition + Synthesis) ----------------
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const micBtn = document.getElementById("micBtn");

if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;

  micBtn.addEventListener("click", () => {
    recognition.lang = currentLanguage === "hi" ? "hi-IN" : "en-IN";
    recognition.start();
    micBtn.classList.add("recording");
  });

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById("chatInput").value = transcript;
    sendChat();
  };
  recognition.onend = () => micBtn.classList.remove("recording");
  recognition.onerror = () => micBtn.classList.remove("recording");
} else {
  micBtn.title = "Voice input not supported in this browser";
  micBtn.style.opacity = 0.4;
}

function speak(text) {
  if (!window.speechSynthesis) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = currentLanguage === "hi" ? "hi-IN" : "en-IN";
  window.speechSynthesis.speak(utter);
}

// ---------------- Alerts tab ----------------
async function loadAlerts() {
  const list = document.getElementById("alertsList");
  list.innerHTML = '<div class="loading">Checking alerts…</div>';
  try {
    const res = await fetch(`${API}/api/alerts?location=${encodeURIComponent(currentLocation)}`);
    const d = await res.json();
    if (d.alert_count === 0) {
      list.innerHTML = '<div class="no-alerts">✓ No active alerts. Conditions look normal.</div>';
      return;
    }
    list.innerHTML = "";
    d.alerts.forEach(a => {
      const el = document.createElement("div");
      el.className = `alert-item sev-${a.severity}`;
      el.innerHTML = `
        <div class="alert-top">
          <span class="alert-type">${a.type}</span>
          <span class="alert-severity">${a.severity}</span>
        </div>
        <div class="alert-msg">${a.message}</div>
        <div class="alert-rec">➜ ${a.recommendation}</div>
      `;
      list.appendChild(el);
    });
  } catch (e) {
    list.innerHTML = '<div class="loading">Could not load alerts.</div>';
  }
}

// ---------------- Agriculture tab ----------------
document.getElementById("cropGo").addEventListener("click", async () => {
  const crop = document.getElementById("cropSelect").value;
  const result = document.getElementById("cropResult");
  result.innerHTML = '<div class="loading">Generating advisory…</div>';
  try {
    const res = await fetch(`${API}/api/agriculture/advisory`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ crop, location: currentLocation, language: currentLanguage }),
    });
    const d = await res.json();
    result.innerHTML = "";
    d.advisories.forEach(a => {
      const el = document.createElement("div");
      el.className = "crop-advisory-item";
      el.textContent = a;
      result.appendChild(el);
    });
    const disclaimer = document.createElement("div");
    disclaimer.className = "crop-disclaimer";
    disclaimer.textContent = d.disclaimer;
    result.appendChild(disclaimer);
  } catch (e) {
    result.innerHTML = '<div class="loading">Could not load advisory.</div>';
  }
});

// ---------------- Init ----------------
loadHealth();
loadDashboard();
