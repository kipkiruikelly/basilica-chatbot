// BASILICA — Enterprise Parish Governance & Approval Portal Client Controller (v6.0)
document.addEventListener("DOMContentLoaded", () => {
    let JWT_TOKEN = localStorage.getItem("basilica_admin_token") || "";
    let USER_ROLE = localStorage.getItem("basilica_admin_role") || "";
    let USERNAME = localStorage.getItem("basilica_admin_username") || "";

    const API_BASE = window.location.origin.includes("localhost") || window.location.origin.includes("127.0.0.1") || window.location.origin.includes("5001")
        ? "/api/v1"
        : (window.location.protocol === "file:" ? "http://127.0.0.1:5001/api/v1" : "/api/v1");

    // Charts references placeholders
    let trafficChart = null;
    let intentChart = null;

    // Check existing logins on boots
    if (JWT_TOKEN) {
        document.getElementById("auth-overlay").style.display = "none";
        setupDashboard();
    }

    // ----------------------------------------------------------------------
    // Authentication Logic & MFA Code simulators
    // ----------------------------------------------------------------------
    const loginBtn = document.getElementById("login-btn");
    const mfaBtn = document.getElementById("mfa-btn");
    const authError = document.getElementById("auth-error");
    const mfaError = document.getElementById("mfa-error");

    loginBtn.addEventListener("click", async () => {
        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value.trim();
        authError.style.display = "none";

        if (!username || !password) {
            authError.innerText = "Please specify username and password.";
            authError.style.display = "block";
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/admin/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();

            if (!res.ok) {
                authError.innerText = data.error || "Login credentials authentication failed.";
                authError.style.display = "block";
                return;
            }

            if (data.mfa_required) {
                localStorage.setItem("mfa_user_id", data.user_id);
                document.getElementById("login-fields").style.display = "none";
                document.getElementById("mfa-fields").style.display = "block";
            } else {
                saveAuth(data.token, data.role, data.username);
            }
        } catch (e) {
            authError.innerText = "Internal gateway connection failed.";
            authError.style.display = "block";
        }
    });

    mfaBtn.addEventListener("click", async () => {
        const code = document.getElementById("mfa-code").value.trim();
        const userId = localStorage.getItem("mfa_user_id");
        mfaError.style.display = "none";

        if (!code) {
            mfaError.innerText = "Please specify your 6-digit code.";
            mfaError.style.display = "block";
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/admin/auth/mfa/verify`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, code })
            });
            const data = await res.json();

            if (!res.ok) {
                mfaError.innerText = data.error || "MFA code verification failed.";
                mfaError.style.display = "block";
                return;
            }

            saveAuth(data.token, data.role, data.username);
        } catch (e) {
            mfaError.innerText = "MFA connection gateway error.";
            mfaError.style.display = "block";
        }
    });

    function saveAuth(token, role, username) {
        JWT_TOKEN = token;
        USER_ROLE = role;
        USERNAME = username;
        localStorage.setItem("basilica_admin_token", token);
        localStorage.setItem("basilica_admin_role", role);
        localStorage.setItem("basilica_admin_username", username);
        document.getElementById("auth-overlay").style.display = "none";
        setupDashboard();
    }

    document.getElementById("logout-btn").addEventListener("click", () => {
        localStorage.clear();
        location.reload();
    });

    // ----------------------------------------------------------------------
    // UI Navigation Router Controllers
    // ----------------------------------------------------------------------
    const navLinks = document.querySelectorAll(".nav-link");
    const viewPanels = document.querySelectorAll(".view-panel");

    navLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            navLinks.forEach(nl => nl.classList.remove("active"));
            link.classList.add("active");

            const targetView = link.getAttribute("data-view");
            viewPanels.forEach(panel => {
                panel.classList.remove("active");
                if (panel.id === targetView) {
                    panel.classList.add("active");
                }
            });

            // Set Breadcrumb
            document.getElementById("breadcrumb-focus").innerText = link.innerText.trim();
            document.getElementById("workspace-title").innerText = link.innerText.trim();

            if (targetView === "content-view") loadContentRegistry();
            if (targetView === "preview-view") loadPreviewSandbox();
            if (targetView === "audit-view") loadAuditLogs();
            if (targetView === "users-view") loadTeamMembers();
        });
    });

    // ----------------------------------------------------------------------
    // Main System Setup & Refreshers
    // ----------------------------------------------------------------------
    function setupDashboard() {
        document.getElementById("avatar-letters").innerText = USERNAME.slice(0, 2).toUpperCase();
        document.getElementById("user-display-name").innerText = USERNAME;
        document.getElementById("user-display-role").innerText = USER_ROLE;

        loadAnalyticsData();
        loadNotificationsFeed();
        
        // Hide edit/approval options according to privileges matrix
        if (USER_ROLE === "Read Only") {
            document.getElementById("new-content-btn").style.display = "none";
            document.getElementById("new-user-btn").style.display = "none";
        }
    }

    async function loadAnalyticsData() {
        try {
            const res = await fetch(`${API_BASE}/admin/analytics`, {
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            const data = await res.json();
            if (!res.ok) return;

            // Draw Charts dynamically using Chart.js
            const trafficCtx = document.getElementById("traffic-chart").getContext("2d");
            const intentCtx = document.getElementById("intent-chart").getContext("2d");

            if (trafficChart) trafficChart.destroy();
            if (intentChart) intentChart.destroy();

            trafficChart = new Chart(trafficCtx, {
                type: "line",
                data: {
                    labels: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    datasets: [{
                        label: "Weekly Chats Received",
                        data: [120, 150, 180, 140, 210, 290, 310],
                        borderColor: "#D4AF37",
                        backgroundColor: "rgba(212, 175, 55, 0.1)",
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });

            // Group intents data from API
            const labels = Object.keys(data.intents || { "mass_times": 10, "greeting": 8, "location": 5 });
            const counts = Object.values(data.intents || { "mass_times": 10, "greeting": 8, "location": 5 });

            intentChart = new Chart(intentCtx, {
                type: "doughnut",
                data: {
                    labels: labels,
                    datasets: [{
                        data: counts,
                        backgroundColor: ["#D4AF37", "#17A2B8", "#28A745", "#FFC107", "#EF4444", "#A855F7"]
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        } catch (e) {
            console.error(e);
        }
    }

    // ----------------------------------------------------------------------
    // Unified Content Registry Loader & CRUD
    // ----------------------------------------------------------------------
    const filterCat = document.getElementById("content-filter-category");
    filterCat.addEventListener("change", () => loadContentRegistry());

    async function loadContentRegistry() {
        try {
            const cat = filterCat.value;
            const res = await fetch(`${API_BASE}/admin/content?category=${cat}`, {
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            const data = await res.json();
            if (!res.ok) return;

            const tableBody = document.getElementById("content-table-body");
            tableBody.innerHTML = "";

            // Update stats widgets on-the-fly
            let pendingCount = 0;
            let scheduledCount = 0;

            data.items.forEach(item => {
                if (item.status === "Pending Review") pendingCount++;
                if (item.status === "Scheduled") scheduledCount++;

                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${item.title}</strong></td>
                    <td><span style="font-family: monospace;">${item.category}</span></td>
                    <td>v${item.version}</td>
                    <td><span class="badge badge-${item.status.toLowerCase().replace(" ", "-")}">${item.status}</span></td>
                    <td>${item.created_by || "system"}</td>
                    <td>
                        <button class="btn-gold" style="padding: 4px 10px; font-size: 0.8rem; display: inline-flex;" onclick="openEditModal('${item.id}')"><i class="fa-solid fa-pen-to-square"></i> Open</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });

            document.getElementById("widget-awaiting-review").innerText = pendingCount;
            document.getElementById("widget-scheduled-count").innerText = scheduledCount;

        } catch (e) {
            console.error(e);
        }
    }

    // ----------------------------------------------------------------------
    // Reactive Form Fields Renderers by Category
    // ----------------------------------------------------------------------
    const categorySelector = document.getElementById("editor-category");
    const fieldsContainer = document.getElementById("dynamic-fields-container");

    categorySelector.addEventListener("change", () => {
        renderCategoryFields(categorySelector.value);
    });

    function renderCategoryFields(category, existingData = {}) {
        fieldsContainer.innerHTML = "";
        let html = "";

        if (category === "mass_schedule") {
            html = `
                <div class="form-grid">
                    <div class="input-group"><label>Church Branch</label><input type="text" id="field-church" class="input-field" value="${existingData.church || "St. Joseph Ruiru"}"></div>
                    <div class="input-group"><label>Day of Mass</label><input type="text" id="field-day" class="input-field" value="${existingData.day || "Sunday"}"></div>
                </div>
                <div class="form-grid">
                    <div class="input-group"><label>Time</label><input type="text" id="field-time" class="input-field" value="${existingData.time || "07:00 AM"}"></div>
                    <div class="input-group"><label>Language</label><input type="text" id="field-language" class="input-field" value="${existingData.language || "English"}"></div>
                    <div class="input-group"><label>Presiding Priest</label><input type="text" id="field-priest" class="input-field" value="${existingData.priest || "Father Jude"}"></div>
                </div>
            `;
        } else if (category === "confessions") {
            html = `
                <div class="input-group"><label>Location / Confessional Box</label><input type="text" id="field-location" class="input-field" value="${existingData.location || "Chapel of Mercy"}"></div>
                <div class="input-group"><label>Weekly Schedule</label><input type="text" id="field-schedule" class="input-field" value="${existingData.schedule || "Saturdays after morning Mass"}"></div>
                <div class="input-group"><label>Preparation Guide Instruction</label><input type="text" id="field-preparation" class="input-field" value="${existingData.preparation || "Examine your conscience prior to arriving"}"></div>
            `;
        } else if (category === "sacraments") {
            html = `
                <div class="input-group"><label>Sacramental Coordinator Staff</label><input type="text" id="field-coordinator" class="input-field" value="${existingData.coordinator || ""}" required></div>
                <div class="input-group"><label>Mandatory Requirements Checklist</label><input type="text" id="field-requirements" class="input-field" value="${existingData.requirements || ""}" required></div>
                <div class="input-group"><label>Regular Schedule / Timetable</label><input type="text" id="field-schedule" class="input-field" value="${existingData.schedule || ""}" required></div>
            `;
        } else if (category === "events") {
            html = `
                <div class="form-grid">
                    <div class="input-group"><label>Venue</label><input type="text" id="field-venue" class="input-field" value="${existingData.venue || ""}"></div>
                    <div class="input-group"><label>Date & Time</label><input type="text" id="field-date" class="input-field" value="${existingData.date || ""}"></div>
                </div>
                <div class="input-group"><label>Registration Link / Sign-Up URL (Optional)</label><input type="text" id="field-registration_link" class="input-field" value="${existingData.registration_link || ""}"></div>
                <div class="input-group"><label>Event Description</label><textarea id="field-description" class="input-field" style="height: 100px;">${existingData.description || ""}</textarea></div>
            `;
        } else if (category === "announcements") {
            html = `
                <div class="input-group"><label>Announcement Content Body</label><textarea id="field-body" class="input-field" style="height: 120px;" required>${existingData.body || ""}</textarea></div>
            `;
        } else if (category === "donations") {
            html = `
                <div class="form-grid">
                    <div class="input-group"><label>M-Pesa Paybill Number</label><input type="text" id="field-paybill" class="input-field" value="${existingData.paybill || "400200"}"></div>
                    <div class="input-group"><label>Cooperative Bank Account Name</label><input type="text" id="field-account_name" class="input-field" value="${existingData.account_name || "St. Joseph Cathedral"}"></div>
                </div>
                <div class="input-group"><label>Generosity Instructions</label><textarea id="field-instructions" class="input-field" style="height: 100px;">${existingData.instructions || ""}</textarea></div>
            `;
        } else if (category === "faqs") {
            html = `
                <div class="input-group"><label>Question / Query Matching Phrase</label><input type="text" id="field-question" class="input-field" value="${existingData.question || ""}" required></div>
                <div class="input-group"><label>Approved Answer Copy</label><textarea id="field-answer" class="input-field" style="height: 120px;" required>${existingData.answer || ""}</textarea></div>
            `;
        } else if (category === "emergency_notices") {
            html = `
                <div class="form-grid">
                    <div class="input-group"><label>Urgency Level</label><select id="field-urgency" class="input-field"><option value="Critical" ${existingData.urgency==='Critical'?'selected':''}>Critical Alert</option><option value="Warning" ${existingData.urgency==='Warning'?'selected':''}>Warning</option></select></div>
                    <div class="input-group"><label>Banner Title</label><input type="text" id="field-banner_title" class="input-field" value="${existingData.banner_title || ""}"></div>
                </div>
                <div class="input-group"><label>Detailed notice</label><textarea id="field-description_copy" class="input-field" style="height: 100px;">${existingData.description_copy || ""}</textarea></div>
            `;
        } else {
            // Static Pages and general templates
            html = `
                <div class="input-group"><label>Relative Path / Route Endpoint</label><input type="text" id="field-path" class="input-field" value="${existingData.path || "/parish-news"}"></div>
                <div class="input-group"><label>Page HTML Content Payload</label><textarea id="field-html_content" class="input-field" style="height: 150px;">${existingData.html_content || "<div></div>"}</textarea></div>
                <div class="input-group"><label>SEO Search Keywords (Comma separated)</label><input type="text" id="field-seo_keywords" class="input-field" value="${existingData.seo_keywords || ""}"></div>
            `;
        }

        fieldsContainer.innerHTML = html;
    }

    // ----------------------------------------------------------------------
    // Modal Governors
    // ----------------------------------------------------------------------
    const contentModal = document.getElementById("content-modal");
    
    document.getElementById("new-content-btn").addEventListener("click", () => {
        document.getElementById("modal-content-title").innerText = "Create New Parish Content Draft";
        document.getElementById("editor-id").value = "";
        document.getElementById("editor-title").value = "";
        document.getElementById("editor-category").value = "mass_schedule";
        document.getElementById("editor-status").value = "Draft";
        document.getElementById("editor-scheduled").value = "";
        document.getElementById("editor-expiry").value = "";
        
        // Hide review buttons for fresh creations
        document.getElementById("editor-submit-review-btn").style.display = "none";
        document.getElementById("editor-approve-btn").style.display = "none";
        document.getElementById("editor-reject-btn").style.display = "none";
        document.getElementById("editor-commentary-root").style.display = "none";

        renderCategoryFields("mass_schedule");
        contentModal.style.display = "flex";
    });

    window.closeContentModal = () => {
        contentModal.style.display = "none";
    };

    window.openEditModal = async (itemId) => {
        try {
            const res = await fetch(`${API_BASE}/admin/content`, {
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            const data = await res.json();
            const item = data.items.find(i => i.id === itemId);
            if (!item) return;

            document.getElementById("modal-content-title").innerText = "Review & Manage Content Details";
            document.getElementById("editor-id").value = item.id;
            document.getElementById("editor-title").value = item.title;
            document.getElementById("editor-category").value = item.category;
            document.getElementById("editor-status").value = item.status;
            
            // Populate dates
            document.getElementById("editor-scheduled").value = item.scheduled_for ? new Date(item.scheduled_for * 1000).toISOString().slice(0, 16) : "";
            document.getElementById("editor-expiry").value = item.expiry_date ? new Date(item.expiry_date * 1000).toISOString().slice(0, 16) : "";

            renderCategoryFields(item.category, item.content_data);

            // Control display of Submit / Approve / Reject based on state and role privileges
            document.getElementById("editor-commentary-root").style.display = "block";
            renderCommentsList(item.comments || []);

            const submitBtn = document.getElementById("editor-submit-review-btn");
            const approveBtn = document.getElementById("editor-approve-btn");
            const rejectBtn = document.getElementById("editor-reject-btn");

            submitBtn.style.display = "none";
            approveBtn.style.display = "none";
            rejectBtn.style.display = "none";

            if (item.status === "Draft" && USER_ROLE !== "Read Only") {
                submitBtn.style.display = "inline-flex";
            }
            if (item.status === "Pending Review" && (USER_ROLE === "Super Administrator" || USER_ROLE === "Parish Administrator" || USER_ROLE === "Priest")) {
                approveBtn.style.display = "inline-flex";
                rejectBtn.style.display = "inline-flex";
            }

            contentModal.style.display = "flex";
        } catch (e) {
            console.error(e);
        }
    };

    function renderCommentsList(comments) {
        const list = document.getElementById("editor-comments-list");
        list.innerHTML = "";
        if (comments.length === 0) {
            list.innerHTML = `<p style="font-size: 0.85rem; opacity: 0.5; font-style: italic;">No commentary attached to this item yet.</p>`;
            return;
        }
        comments.forEach(c => {
            const div = document.createElement("div");
            div.className = "comment-bubble";
            div.innerHTML = `
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--brushed-gold); margin-bottom: 5px;">
                    <strong>${c.user}</strong>
                    <span>${new Date(c.timestamp * 1000).toLocaleTimeString()}</span>
                </div>
                <p style="font-size: 0.85rem; opacity: 0.95;">${c.text}</p>
            `;
            list.appendChild(div);
        });
    }

    // Add general comments
    document.getElementById("editor-add-comment-btn").addEventListener("click", async () => {
        const itemId = document.getElementById("editor-id").value;
        const text = document.getElementById("editor-add-comment-input").value.trim();
        if (!itemId || !text) return;

        try {
            const res = await fetch(`${API_BASE}/admin/content/${itemId}/comment`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${JWT_TOKEN}`
                },
                body: JSON.stringify({ text })
            });
            if (res.ok) {
                const item = await res.json();
                renderCommentsList(item.comments);
                document.getElementById("editor-add-comment-input").value = "";
            }
        } catch (e) {
            console.error(e);
        }
    });

    // ----------------------------------------------------------------------
    // Submissions, Approvals, Rejections, Validations Actions
    // ----------------------------------------------------------------------
    document.getElementById("editor-submit-review-btn").addEventListener("click", async () => {
        const itemId = document.getElementById("editor-id").value;
        if (!itemId) return;
        try {
            const res = await fetch(`${API_BASE}/admin/content/${itemId}/submit`, {
                method: "POST",
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            if (res.ok) {
                closeContentModal();
                loadContentRegistry();
            }
        } catch (e) {
            console.error(e);
        }
    });

    document.getElementById("editor-approve-btn").addEventListener("click", async () => {
        const itemId = document.getElementById("editor-id").value;
        if (!itemId) return;
        try {
            const res = await fetch(`${API_BASE}/admin/content/${itemId}/review`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${JWT_TOKEN}`
                },
                body: JSON.stringify({ action: "Approve" })
            });
            if (res.ok) {
                closeContentModal();
                loadContentRegistry();
            }
        } catch (e) {
            console.error(e);
        }
    });

    document.getElementById("editor-reject-btn").addEventListener("click", async () => {
        const itemId = document.getElementById("editor-id").value;
        const comment = prompt("Please provide a brief reason for returning this item to Draft status:");
        if (!itemId || comment === null) return;
        try {
            const res = await fetch(`${API_BASE}/admin/content/${itemId}/review`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${JWT_TOKEN}`
                },
                body: JSON.stringify({ action: "Reject", comment })
            });
            if (res.ok) {
                closeContentModal();
                loadContentRegistry();
            }
        } catch (e) {
            console.error(e);
        }
    });

    // Save and validate form
    const form = document.getElementById("content-form");
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const itemId = document.getElementById("editor-id").value;
        const title = document.getElementById("editor-title").value.trim();
        const category = document.getElementById("editor-category").value;
        const status = document.getElementById("editor-status").value;

        // Build content data from input inputs
        const content_data = {};
        const inputs = fieldsContainer.querySelectorAll("input, textarea, select");
        inputs.forEach(i => {
            const fieldKey = i.id.replace("field-", "");
            content_data[fieldKey] = i.value;
        });

        // Validation rules checker
        const warnPanel = document.getElementById("validation-warning-panel");
        const warnList = document.getElementById("validation-warning-list");
        warnPanel.style.display = "none";
        warnList.innerHTML = "";

        const errors = [];
        // 1. Broken URL validation rules
        if (content_data.registration_link && !content_data.registration_link.startsWith("http://") && !content_data.registration_link.startsWith("https://")) {
            errors.push("Invalid URL: Registration Sign-up link must start with http:// or https://");
        }

        // 2. Dates chronological validations
        const schedVal = document.getElementById("editor-scheduled").value;
        const expVal = document.getElementById("editor-expiry").value;

        const scheduled_for = schedVal ? new Date(schedVal).getTime() / 1000 : null;
        const expiry_date = expVal ? new Date(expVal).getTime() / 1000 : null;

        if (scheduled_for && scheduled_for <= (Date.now() / 1000)) {
            errors.push("Illogical scheduling: Publication start date must be in the future.");
        }
        if (expiry_date && scheduled_for && expiry_date <= scheduled_for) {
            errors.push("Illogical chronology: Auto-archiving expiration must occur after publication start date.");
        }

        if (errors.length > 0) {
            errors.forEach(err => {
                const li = document.createElement("li");
                li.innerText = err;
                warnList.appendChild(li);
            });
            warnPanel.style.display = "block";
            return;
        }

        const payload = {
            title,
            category,
            status,
            content_data,
            scheduled_for,
            expiry_date,
            change_notes: `Admin update by ${USERNAME}`,
            change_summary: `Editorial updates to fields`
        };

        try {
            let res;
            if (itemId) {
                res = await fetch(`${API_BASE}/admin/content/${itemId}`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${JWT_TOKEN}`
                    },
                    body: JSON.stringify(payload)
                });
            } else {
                res = await fetch(`${API_BASE}/admin/content`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${JWT_TOKEN}`
                    },
                    body: JSON.stringify(payload)
                });
            }

            if (res.ok) {
                closeContentModal();
                loadContentRegistry();
            } else {
                const errData = await res.json();
                errors.push(errData.error || "Save error occurred.");
                errors.forEach(err => {
                    const li = document.createElement("li");
                    li.innerText = err;
                    warnList.appendChild(li);
                });
                warnPanel.style.display = "block";
            }
        } catch (err) {
            console.error(err);
        }
    });

    // Simulated Auto-Saving Drafts Indicator Loop
    setInterval(() => {
        if (contentModal.style.display === "flex") {
            const ind = document.getElementById("editor-autosave-indicator");
            const timeStr = new Date().toLocaleTimeString();
            ind.innerText = `Draft auto-saved locally at ${timeStr}`;
        }
    }, 15000);

    // AI Writing Assistant suggestions trigger
    document.getElementById("ai-assist-btn").addEventListener("click", async () => {
        const title = document.getElementById("editor-title").value;
        if (!title) {
            alert("Please specify an item title first so AI knows what to draft.");
            return;
        }
        try {
            const res = await fetch(`${API_BASE}/admin/ai/draft`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${JWT_TOKEN}`
                },
                body: JSON.stringify({ prompt: `Draft high fidelity announcement info context about: ${title}` })
            });
            const data = await res.json();
            if (res.ok && data.draft) {
                alert(`✨ AI Suggestion suggestion:\n\n${data.draft}`);
            }
        } catch (e) {
            console.error(e);
        }
    });

    // ----------------------------------------------------------------------
    // Integrated Live Chat Preview Sandbox Controls
    // ----------------------------------------------------------------------
    async function loadPreviewSandbox() {
        try {
            const res = await fetch(`${API_BASE}/admin/content`, {
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            const data = await res.json();
            const list = document.getElementById("sandbox-draft-availables");
            list.innerHTML = "";

            data.items.forEach(i => {
                const li = document.createElement("li");
                li.style.display = "flex";
                li.style.justify = "space-between";
                li.style.fontSize = "0.85rem";
                li.innerHTML = `<span>📂 ${i.title}</span><span style="font-weight: 600; color: var(--brushed-gold);">${i.status}</span>`;
                list.appendChild(li);
            });
        } catch (e) {
            console.error(e);
        }
    }

    const chatSendBtn = document.getElementById("sandbox-send-btn");
    const chatInput = document.getElementById("sandbox-chat-input");
    const chatBody = document.getElementById("sandbox-chat-body");

    chatSendBtn.addEventListener("click", triggerSandboxAsk);
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") triggerSandboxAsk();
    });

    async function triggerSandboxAsk() {
        const q = chatInput.value.trim();
        if (!q) return;

        appendSandboxBubble(q, "bubble-user");
        chatInput.value = "";

        try {
            const res = await fetch(`${API_BASE}/ask?preview_drafts=true`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question: q, session_id: "preview-sandbox-session" })
            });
            const data = await res.json();
            appendSandboxBubble(data.answer || "No response received.", "bubble-bot");
        } catch (e) {
            appendSandboxBubble("Gateway connection timeout error.", "bubble-bot");
        }
    }

    function appendSandboxBubble(text, className) {
        const div = document.createElement("div");
        div.className = `chat-bubble ${className}`;
        div.innerText = text;
        chatBody.appendChild(div);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    // ----------------------------------------------------------------------
    // Audit log timelines extraction
    // ----------------------------------------------------------------------
    async function loadAuditLogs() {
        try {
            const res = await fetch(`${API_BASE}/admin/audit-logs`, {
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            const data = await res.json();
            if (!res.ok) return;

            const tbody = document.getElementById("audit-table-body");
            tbody.innerHTML = "";

            data.slice(-25).reverse().forEach(log => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${new Date(log.timestamp * 1000).toLocaleString()}</td>
                    <td><span style="font-family: monospace;">${log.session_id || "guest"}</span></td>
                    <td><strong>${log.intent || "unknown"}</strong></td>
                    <td>${Math.round(log.confidence * 100)}%</td>
                    <td>${log.latency_seconds ? log.latency_seconds.toFixed(3) : "0.012"}s</td>
                    <td><span class="badge" style="background: rgba(255,255,255,0.05);">${log.cache_hit ? 'Cache' : 'Gemini'}</span></td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error(e);
        }
    }

    // ----------------------------------------------------------------------
    // Team Members Loader
    // ----------------------------------------------------------------------
    async function loadTeamMembers() {
        try {
            const res = await fetch(`${API_BASE}/admin/users`, {
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            const data = await res.json();
            if (!res.ok) return;

            const tbody = document.getElementById("users-table-body");
            tbody.innerHTML = "";

            data.forEach(user => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><strong>${user.username}</strong></td>
                    <td>${user.role}</td>
                    <td><span class="badge badge-published">${user.status}</span></td>
                    <td><span style="color: #28A745;"><i class="fa-solid fa-square-check"></i> Enabled</span></td>
                    <td>${user.created_at ? new Date(user.created_at * 1000).toLocaleDateString() : "2026-07-27"}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error(e);
        }
    }

    document.getElementById("new-user-btn").addEventListener("click", () => {
        document.getElementById("user-modal").style.display = "flex";
    });

    const userForm = document.getElementById("user-form");
    userForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const username = document.getElementById("user-username").value.trim();
        const password = document.getElementById("user-password").value.trim();
        const role = document.getElementById("user-role").value;

        try {
            const res = await fetch(`${API_BASE}/admin/users`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${JWT_TOKEN}`
                },
                body: JSON.stringify({ username, password, role })
            });
            if (res.ok) {
                document.getElementById("user-modal").style.display = "none";
                userForm.reset();
                loadTeamMembers();
            } else {
                const data = await res.json();
                alert(data.error || "Failed to invite member.");
            }
        } catch (err) {
            console.error(err);
        }
    });

    // ----------------------------------------------------------------------
    // Notifications Center Controls
    // ----------------------------------------------------------------------
    const notifModal = document.getElementById("notif-modal");
    window.toggleNotificationsModal = () => {
        if (notifModal.style.display === "flex") {
            notifModal.style.display = "none";
        } else {
            notifModal.style.display = "flex";
        }
    };

    async function loadNotificationsFeed() {
        try {
            const res = await fetch(`${API_BASE}/admin/notifications`, {
                headers: { "Authorization": `Bearer ${JWT_TOKEN}` }
            });
            const data = await res.json();
            if (!res.ok) return;

            document.getElementById("notif-badge").innerText = data.filter(n => !n.read).length;

            const list = document.getElementById("notifications-modal-list");
            list.innerHTML = "";
            if (data.length === 0) {
                list.innerHTML = `<li style="font-size: 0.9rem; opacity: 0.5; text-align: center;">No notifications currently.</li>`;
                return;
            }

            data.reverse().forEach(n => {
                const li = document.createElement("li");
                li.style.background = "rgba(255,255,255,0.02)";
                li.style.padding = "10px 15px";
                li.style.borderRadius = "10px";
                li.style.borderLeft = "3px solid var(--brushed-gold)";
                li.innerHTML = `
                    <p style="font-size: 0.85rem; opacity: 0.95;">${n.text}</p>
                    <span style="font-size: 0.7rem; color: var(--brushed-gold); margin-top: 5px; display: block;">${new Date(n.timestamp * 1000).toLocaleTimeString()}</span>
                `;
                list.appendChild(li);
            });
        } catch (e) {
            console.error(e);
        }
    }
});
