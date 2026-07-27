/* ==========================================
   BASILICA Modern Frontend Engine (JS)
   ========================================== */

// Use local path as fallback or point to production/relative paths
const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") || window.location.origin.includes("5001")
  ? "/api/v1"
  : (window.location.protocol === "file:" ? "http://127.0.0.1:5001/api/v1" : "https://basilica-chatbot.onrender.com/api/v1");

const chatArea = document.getElementById("chatArea");
const chatForm = document.getElementById("chatForm");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const statusBanner = document.getElementById("statusBanner");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const resetSessionBtn = document.getElementById("resetSessionBtn");
const toastContainer = document.getElementById("toastContainer");

const themeMoonIcon = document.getElementById("themeMoonIcon");
const themeSunIcon = document.getElementById("themeSunIcon");

// 1. Session Manager (Generate and persist session ID)
function getSessionId() {
  let sid = sessionStorage.getItem("basilica_session_id");
  if (!sid) {
    sid = "sess_" + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    sessionStorage.setItem("basilica_session_id", sid);
  }
  return sid;
}

// 2. Active Theme Manager
function initTheme() {
  const savedTheme = localStorage.getItem("basilica_theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcons(savedTheme);
}

function updateThemeIcons(theme) {
  if (theme === "dark") {
    themeMoonIcon.style.display = "none";
    themeSunIcon.style.display = "block";
  } else {
    themeMoonIcon.style.display = "block";
    themeSunIcon.style.display = "none";
  }
}

themeToggleBtn.addEventListener("click", () => {
  const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
  const newTheme = currentTheme === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("basilica_theme", newTheme);
  updateThemeIcons(newTheme);
  showToast(`Switched to ${newTheme} theme`);
});

// Reset Session Button
resetSessionBtn.addEventListener("click", async () => {
  const sessionId = getSessionId();
  try {
    const res = await fetch(`${API_BASE}/session/clear`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId })
    });
    if (res.ok) {
      chatArea.innerHTML = `
        <div class="message-bubble bot-message">
          <div class="bubble-content">
            <p>Peace be with you! I have reset our conversation history. How can I help you today?</p>
          </div>
        </div>
      `;
      showToast("Conversation history reset");
    } else {
      throw new Error("Failed to clear session on backend");
    }
  } catch (err) {
    showToast("Reset failed. Clearing local session.", "error");
    sessionStorage.removeItem("basilica_session_id");
    chatArea.innerHTML = `
      <div class="message-bubble bot-message">
        <div class="bubble-content">
          <p>Peace be with you! I'm BASILICA, your parish assistant. Ask me about Mass times, sacraments, or donations.</p>
        </div>
      </div>
    `;
  }
});

// 3. UI Helpers (Toasts and Message Rendering)
function showToast(message, type = "info") {
  const t = document.createElement("div");
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${message}</span>`;
  toastContainer.appendChild(t);
  setTimeout(() => t.remove(), 4000);
}

function createBubble(text, sender, meta = null, hasMpesa = false) {
  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${sender === "user" ? "user-message" : "bot-message"}`;
  
  let innerHTML = `
    <div class="bubble-content">
      <p>${text}</p>
  `;
  
  if (hasMpesa) {
    innerHTML += `
      <div class="mpesa-card">
        <div class="mpesa-title">M-Pesa Paybill</div>
        <div class="mpesa-details">Paybill: <strong>400200</strong><br>Account: <strong>St. Joseph</strong></div>
        <button class="mpesa-copy-btn" onclick="copyMpesaDetails()">
          <svg style="width:12px;height:12px;vertical-align:middle" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          Copy Paybill
        </button>
      </div>
    `;
  }
  
  innerHTML += `</div>`;
  
  if (meta) {
    innerHTML += `<span class="meta-info">${meta}</span>`;
  }
  
  bubble.innerHTML = innerHTML;
  chatArea.appendChild(bubble);
  chatArea.scrollTop = chatArea.scrollHeight;
  return bubble;
}

window.copyMpesaDetails = function() {
  navigator.clipboard.writeText("400200").then(() => {
    showToast("Paybill 400200 copied to clipboard!");
  }).catch(() => {
    showToast("Failed to copy details.", "error");
  });
};

// 4. Skeleton Typing Animation Handler
function showSkeletonLoader() {
  const l = document.createElement("div");
  l.className = "message-bubble bot-message";
  l.id = "skeletonLoaderBubble";
  l.innerHTML = `
    <div class="typing-bubble">
      <span></span>
      <span></span>
      <span></span>
    </div>
  `;
  chatArea.appendChild(l);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function removeSkeletonLoader() {
  const l = document.getElementById("skeletonLoaderBubble");
  if (l) l.remove();
}

// 5. Main Interaction Query Pipeline
async function askQuestion(question) {
  if (!question || !question.trim()) return;
  
  createBubble(question, "user");
  questionInput.value = "";
  sendBtn.disabled = true;
  showSkeletonLoader();
  
  const wakeTimer = setTimeout(() => { statusBanner.style.display = "flex"; }, 4000);
  const sessionId = getSessionId();

  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId }),
    });
    
    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }
    
    const data = await res.json();
    removeSkeletonLoader();
    clearTimeout(wakeTimer);
    statusBanner.style.display = "none";
    
    const hasMpesa = question.toLowerCase().includes("mpesa") || question.toLowerCase().includes("paybill") || (data.intent === "donations");
    
    const meta = null;
      
    createBubble(data.answer, "bot", meta, hasMpesa);
  } catch (err) {
    removeSkeletonLoader();
    clearTimeout(wakeTimer);
    statusBanner.style.display = "none";
    showToast("Connection to Server failed", "error");
    createBubble("I couldn't reach the server. Please check your connection and try again.", "bot");
  } finally {
    sendBtn.disabled = false;
    questionInput.focus();
  }
}

// Form Submission Listeners
chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  askQuestion(questionInput.value);
});

// Setup
window.askQuestion = askQuestion; // expose globally to suggestions chips
initTheme();
questionInput.focus();
