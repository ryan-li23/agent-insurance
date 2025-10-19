(function () {
    const body = document.body;
    const jobId = body.dataset.jobId;
    if (!jobId) {
        return;
    }

    const caseId = body.dataset.caseId;
    const refreshButton = document.getElementById("btn-refresh");
    const statusBadge = document.getElementById("job-status-badge");
    const messageEl = document.getElementById("job-message");
    const createdEl = document.getElementById("job-created");
    const updatedEl = document.getElementById("job-updated");
    const stepperEl = document.getElementById("stepper");
    const storyPanel = document.getElementById("story-panel");
    const storyCaption = document.getElementById("story-caption");
    const storyNext = document.getElementById("btn-story-next");
    const storyReset = document.getElementById("btn-story-reset");
    const kpiContainer = document.getElementById("kpi-cards");
    const clarificationCard = document.getElementById("clarification-card");
    const metricsCard = document.getElementById("metrics-card");
    const intakeSummary = document.getElementById("intake-summary");
    const intakeContent = document.getElementById("intake-content");
    const debateSummary = document.getElementById("debate-summary");
    const debateContent = document.getElementById("debate-content");
    const decisionSummary = document.getElementById("decision-summary");
    const decisionContent = document.getElementById("decision-content");
    const continueSection = document.getElementById("continue-section");
    const continueBody = document.getElementById("continue-body");
    const btnEmail = document.getElementById("btn-generate-email");
    const btnDownload = document.getElementById("btn-download-packet");
    const btnCloseCase = document.getElementById("btn-close-case");
    const btnReopenCase = document.getElementById("btn-reopen-case");
    const emailDraft = document.getElementById("email-draft");
    const followupContainer = document.getElementById("followup-content");

    const pollIntervalMs = 3000;
    let pollTimer = null;
    let checklistLock = false;
    const openDebateDetails = new Set();
    const openDebateInlineDetails = new Set();
    const openEvidenceDetails = new Set();

    const roleLabels = {
        curator: "Evidence Curator",
        interpreter: "Policy Interpreter",
        reviewer: "Compliance Reviewer",
        supervisor: "Supervisor",
    };

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatDate(value) {
        if (!value) return "—";
        try {
            return new Intl.DateTimeFormat("en", {
                year: "numeric",
                month: "short",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
            }).format(new Date(value));
        } catch (err) {
            return value;
        }
    }

    function createBadge(status) {
        const map = {
            queued: { text: "Queued", cls: "badge--upcoming" },
            running: { text: "Running", cls: "badge--current" },
            needs_user_uploads: { text: "Awaiting uploads", cls: "badge--alert" },
            completed: { text: "Completed", cls: "badge--complete" },
            error: { text: "Error", cls: "badge--alert" },
        };
        return map[status] || { text: status, cls: "badge--upcoming" };
    }

    function createJsonDetails(title, data, key, store) {
        const details = document.createElement("details");
        details.className = "json-details";
        if (key && store && store.has(key)) {
            details.setAttribute('open', 'open');
            details.open = true;
        }
        const summary = document.createElement("summary");
        summary.className = "json-summary";
        summary.textContent = title;
        details.appendChild(summary);
        const pre = document.createElement("pre");
        pre.className = "json-view";
        pre.textContent = JSON.stringify(data, null, 2);
        details.appendChild(pre);
        if (key && store) {
            details.dataset.key = key;
            details.addEventListener("toggle", () => {
                if (details.open) {
                    store.add(key);
                } else {
                    store.delete(key);
                }
            });
        }
        return details;
    }

    function persistHtmlDetails(container, prefix, store) {
        if (!store) {
            return;
        }
        const nodes = container.querySelectorAll("details");
        nodes.forEach((node, idx) => {
            const key = `${prefix}-${idx}`;
            if (store.has(key)) {
                node.setAttribute("open", "open");
                node.open = true;
            }
            node.dataset.key = key;
            node.addEventListener("toggle", () => {
                if (node.open) {
                    store.add(key);
                } else {
                    store.delete(key);
                }
            });
        });
    }

    function computeStepStatus(payload) {
        const uploads = payload.uploads || { photos: [], invoices: [], fnol: [] };
        const hasInputs =
            (uploads.photos && uploads.photos.length) ||
            (uploads.invoices && uploads.invoices.length) ||
            (uploads.fnol && uploads.fnol.length) ||
            (payload.inputs &&
                payload.inputs.fnol_text &&
                payload.inputs.fnol_text.trim().length);

        const turns = (payload.result && payload.result.turns) || [];
        const decision = payload.decision || {};
        const metadata = payload.metadata || {};
        const roundsCompleted =
            metadata.rounds_completed || (turns.length ? 1 : 0);
        const objections = (payload.result && payload.result.objections) || [];
        const blocking = objections.some((obj) =>
            (obj.status || "").toLowerCase().includes("blocking"),
        );

        const status = {
            intake: "upcoming",
            debate: "upcoming",
            decision: "upcoming",
        };

        if (!hasInputs) {
            status.intake = "current";
        } else if (!turns.length) {
            status.intake = "complete";
            status.debate = "current";
        } else {
            status.intake = "complete";
            status.debate = roundsCompleted >= 1 ? "complete" : "current";
            if (!decision.outcome) {
                status.decision = "current";
            } else if (metadata.paused_for_user) {
                status.decision = "current";
            } else if (payload.job.case_closed || metadata.approval === true || !blocking) {
                status.decision = "complete";
            } else {
                status.decision = "current";
            }
        }

        if (payload.job.case_closed) {
            status.decision = "complete";
        }
        return status;
    }

    function renderStepper(payload) {
        const statuses = computeStepStatus(payload);
        const steps = [
            {
                key: "intake",
                title: "Upload Evidence",
                subtitle: "Photos, invoices, FNOL text",
            },
            {
                key: "debate",
                title: "Agent Debate",
                subtitle: "Curator ↔ Interpreter ↔ Reviewer",
            },
            {
                key: "decision",
                title: "Decision Review",
                subtitle: "Outcome, citations, follow-ups",
            },
        ];

        stepperEl.innerHTML = "";
        steps.forEach((step, index) => {
            const wrapper = document.createElement("div");
            wrapper.className = "stepper__item";
            wrapper.classList.add(`stepper__item--${statuses[step.key] || "upcoming"}`);

            const badge = document.createElement("div");
            badge.className = "stepper__index";
            badge.textContent = index + 1;

            const text = document.createElement("div");
            text.innerHTML = `<div class="stepper__title">${escapeHtml(step.title)}</div>
                <div class="stepper__subtitle">${escapeHtml(step.subtitle)}</div>`;

            wrapper.appendChild(badge);
            wrapper.appendChild(text);
            stepperEl.appendChild(wrapper);
        });
    }

    function renderKPIs(payload) {
        kpiContainer.innerHTML = "";
        const kpis = payload.kpis || [];
        if (!kpis.length) {
            kpiContainer.innerHTML =
                '<p class="muted">Run the review to populate KPIs.</p>';
            return;
        }
        const icons = {
            camera: "📷",
            alert: "🚨",
            receipt: "📑",
            book: "📘",
        };
        kpis.forEach((kpi) => {
            const card = document.createElement("div");
            card.className = "kpi-card";
            card.style.borderTopColor = kpi.accent || "#6366f1";
            card.innerHTML = `<div class="kpi-card__icon">${icons[kpi.icon] || "📌"}</div>
                <div class="kpi-card__value">${escapeHtml(kpi.value ?? "0")}</div>
                <div class="kpi-card__label">${escapeHtml(kpi.label)}</div>
                <div class="kpi-card__caption">${escapeHtml(kpi.caption || "")}</div>`;
            kpiContainer.appendChild(card);
        });
    }

    function renderClarification(payload) {
        clarificationCard.innerHTML = "";
        const notes = payload.clarification_notes || [];
        const header = document.createElement("h3");
        header.textContent = "Top clarification insights";
        clarificationCard.appendChild(header);
        if (!notes.length) {
            const p = document.createElement("p");
            p.className = "muted";
            p.textContent =
                "Clarification insights will populate after the curator processes evidence.";
            clarificationCard.appendChild(p);
            return;
        }
        const list = document.createElement("ul");
        notes.forEach((note) => {
            const li = document.createElement("li");
            li.textContent = note;
            list.appendChild(li);
        });
        clarificationCard.appendChild(list);
    }

    function renderMetrics(payload) {
        metricsCard.innerHTML = "";
        const metrics = payload.metrics || {};
        const header = document.createElement("h3");
        header.textContent = "Progress metrics";
        metricsCard.appendChild(header);

        if (!Object.keys(metrics).length) {
            const p = document.createElement("p");
            p.className = "muted";
            p.textContent = "Metrics will appear after a decision is produced.";
            metricsCard.appendChild(p);
            return;
        }

        const grid = document.createElement("div");
        grid.className = "metric-grid";
        const entries = [
            {
                label: "Estimated time saved",
                value: `${metrics.time_saved || 0} min`,
            },
            {
                label: "Objections resolved",
                value: metrics.resolved_objections || 0,
            },
            {
                label: "Confidence uplift",
                value: `${metrics.confidence || 0}%`,
            },
        ];

        entries.forEach((entry) => {
            const wrapper = document.createElement("div");
            wrapper.innerHTML = `<div class="metric-value">${escapeHtml(entry.value)}</div>
                <div class="metric-label">${escapeHtml(entry.label)}</div>`;
            grid.appendChild(wrapper);
        });

        metricsCard.appendChild(grid);
    }

    function renderIntake(payload) {
        const uploads = payload.uploads || { photos: [], invoices: [], fnol: [] };
        const fnolText = (payload.inputs && payload.inputs.fnol_text) || "";
        intakeSummary.textContent = `Photos ${uploads.photos.length} · Invoices ${uploads.invoices.length} · FNOL docs ${uploads.fnol.length}`;

        intakeContent.innerHTML = "";
        const photoCard = document.createElement("div");
        photoCard.className = "intake-card";

        if (!uploads.photos.length) {
            const p = document.createElement("p");
            p.className = "muted";
            p.textContent = "Upload photos to help the Evidence Curator.";
            photoCard.appendChild(p);
        } else {
            const gallery = document.createElement("div");
            gallery.className = "intake-gallery";
            uploads.photos.slice(0, 6).forEach((photo) => {
                const figure = document.createElement("figure");
                const img = document.createElement("img");
                img.alt = photo.filename || "photo";
                if (photo.preview) {
                    img.src = photo.preview;
                }
                figure.appendChild(img);
                const caption = document.createElement("figcaption");
                caption.className = "muted";
                caption.textContent = photo.filename;
                figure.appendChild(caption);
                gallery.appendChild(figure);
            });
            photoCard.appendChild(gallery);
        }

        intakeContent.appendChild(photoCard);

        const narrativeCard = document.createElement("div");
        narrativeCard.className = "intake-card";
        narrativeCard.innerHTML = `<h3>FNOL narrative</h3>
            <p>${escapeHtml(fnolText.trim() || "(No narrative provided)")}</p>`;

        const attachmentSection = document.createElement("div");
        attachmentSection.className = "intake-attachments";

        const buildList = (title, items) => {
            const block = document.createElement("div");
            block.className = "intake-list";
            const heading = document.createElement("h4");
            heading.textContent = title;
            block.appendChild(heading);
            const ul = document.createElement("ul");
            if (!items.length) {
                const li = document.createElement("li");
                li.className = "muted";
                li.textContent = "No files uploaded.";
                ul.appendChild(li);
            } else {
                items.forEach((item) => {
                    const li = document.createElement("li");
                    li.textContent = item.filename || "uploaded file";
                    ul.appendChild(li);
                });
            }
            block.appendChild(ul);
            return block;
        };

        attachmentSection.appendChild(
            buildList("Invoices / receipts", uploads.invoices || []),
        );
        attachmentSection.appendChild(
            buildList("FNOL forms & attachments", uploads.fnol || []),
        );

        narrativeCard.appendChild(attachmentSection);
        intakeContent.appendChild(narrativeCard);
    }

    function renderDebate(payload) {
        debateContent.innerHTML = "";
        const turns = (payload.result && payload.result.turns) || [];
        if (!turns.length) {
            debateSummary.textContent = "Awaiting initial run";
            const p = document.createElement("p");
            p.className = "muted";
            p.textContent =
                "Start the review to see the multi-agent collaboration timeline.";
            debateContent.appendChild(p);
            return;
        }

        debateSummary.textContent = `${turns.length} conversation turn(s)`;
        turns.forEach((turn, index) => {
            const role = (turn.role || "assistant").toLowerCase();
            const entry = document.createElement("div");
            entry.className = `chat-entry role-${role}`;

            const header = document.createElement("div");
            header.className = "chat-entry__role";
            header.textContent = roleLabels[role] || role;

            const body = document.createElement("div");
            body.className = "chat-entry__body";
            const cleaned = (turn.content || "").trim();
            try {
                const parsed = JSON.parse(cleaned);
                const key = `debate-${index}`;
                body.appendChild(
                    createJsonDetails("Structured output", parsed, key, openDebateDetails)
                );
            } catch (err) {
                const hasDetails = cleaned.includes("<details");
                if (hasDetails) {
                body.innerHTML = cleaned.replace(/\n/g, "<br>");
                persistHtmlDetails(
                    body,
                    `debate-inline-${index}`,
                    openDebateInlineDetails
                );
                } else {
                    body.innerHTML = escapeHtml(cleaned).replace(/\n/g, "<br>");
                }
            }

            entry.appendChild(header);
            entry.appendChild(body);
            debateContent.appendChild(entry);
        });
    }

    function decisionColor(outcome) {
        const map = { Pay: "#16a34a", Partial: "#f59e0b", Deny: "#ef4444" };
        return map[outcome] || "#2563eb";
    }

    function renderEvidenceGallery(payload, container) {
        container.innerHTML = "";
        const evidence = (payload.result && payload.result.evidence) || [];
        const annotated = payload.annotated_evidence || {};

        if (!evidence.length) {
            const p = document.createElement("p");
            p.className = "muted";
            p.textContent = "No structured evidence captured yet.";
            container.appendChild(p);
            return;
        }

        evidence.forEach((entry) => {
            const wrapper = document.createElement("div");
            wrapper.className = "evidence-entry";

            const name = entry.image_name || "Photo";
            const obs = entry.observations || [];
            const heading = document.createElement("h4");
            heading.textContent = `${name} (${obs.length} observation${obs.length === 1 ? "" : "s"})`;
            wrapper.appendChild(heading);

            if (annotated[name]) {
                const img = document.createElement("img");
                img.className = "evidence-preview";
                img.src = annotated[name];
                img.alt = name;
                wrapper.appendChild(img);
            }

            if (obs.length) {
                const chips = document.createElement("div");
                chips.className = "chip-row";
                obs.slice(0, 6).forEach((item) => {
                    const chip = document.createElement("span");
                    chip.className = "chip";
                    const severity = item.severity || "Unknown";
                    chip.textContent = `${item.label || "Observation"} (${severity})`;
                    chips.appendChild(chip);
                });
                wrapper.appendChild(chips);

                const list = document.createElement("ul");
                obs.forEach((item) => {
                    const li = document.createElement("li");
                    const severity = item.severity || "Unknown";
                    const location = item.location_text || "Location not captured";
                    const notes = item.explanation || item.notes || "No narrative provided.";
                    li.innerHTML = `<strong>${escapeHtml(item.label || "Observation")}</strong> (${escapeHtml(severity)}) at ${escapeHtml(location)}<br><span class="muted">${escapeHtml(notes)}</span>`;
                    list.appendChild(li);
                });
                wrapper.appendChild(list);
            }

            if (entry.global_assessment) {
                wrapper.appendChild(
                    createJsonDetails(
                        "Global assessment",
                        entry.global_assessment,
                        `evidence-${name}-global`,
                        openEvidenceDetails
                    )
                );
            }

            if (entry.chronology) {
                wrapper.appendChild(
                    createJsonDetails(
                        "Chronology",
                        entry.chronology,
                        `evidence-${name}-chronology`,
                        openEvidenceDetails
                    )
                );
            }

            container.appendChild(wrapper);
        });
    }

function renderInvoice(payload, container) {
    container.innerHTML = "";
    const expense = (payload.result && payload.result.expense) || {};
    if (!Object.keys(expense).length) {
        const p = document.createElement("p");
        p.className = "muted";
        p.textContent = "No invoice reconciliation data yet.";
        container.appendChild(p);
        return;
    }

        const card = document.createElement("div");
        card.className = "invoice-card";
        card.innerHTML = `<div class="invoice-card__header">
                <div>
                    <div class="muted">Primary vendor</div>
                    <div class="invoice-card__vendor">${escapeHtml(expense.vendor || "Unknown vendor")}</div>
                </div>
                <div class="invoice-card__total">${escapeHtml(expense.total ?? "—")}</div>
            </div>`;

        const table = document.createElement("table");
        table.className = "invoice-table";
        table.innerHTML =
            "<thead><tr><th>Line item</th><th>Amount</th><th>Status</th></tr></thead>";
        const tbody = document.createElement("tbody");

        (expense.line_items || []).forEach((item) => {
            const tr = document.createElement("tr");
            const status = (item.status || "Pending").toLowerCase();
            let badgeClass = "badge--current";
            if (status.includes("match") || status.includes("approved")) {
                badgeClass = "badge--complete";
            } else if (status.includes("reject") || status.includes("exception")) {
                badgeClass = "badge--alert";
            }
            tr.innerHTML = `<td>${escapeHtml(item.description || "Line item")}</td>
                <td>${escapeHtml(item.amount ?? "—")}</td>
                <td><span class="badge ${badgeClass}">${escapeHtml(item.status || "Pending")}</span></td>`;
            tbody.appendChild(tr);
        });

    table.appendChild(tbody);
    card.appendChild(table);
    container.appendChild(card);
}

function renderObjections(payload, container) {
    container.innerHTML = "";
    const objections = (payload.result && payload.result.objections) || [];
    if (!objections.length) {
        const p = document.createElement("p");
        p.className = "muted";
        p.textContent = "No objections logged.";
        container.appendChild(p);
        return;
    }
    const list = document.createElement("ul");
    list.className = "objection-list";
    objections.forEach((obj) => {
        const li = document.createElement("li");
        const status = (obj.status || "").toLowerCase();
        let badgeClass = "badge--current";
        if (status.includes("blocking")) {
            badgeClass = "badge--alert";
        } else if (status.includes("resolved")) {
            badgeClass = "badge--complete";
        }
        li.innerHTML = `<strong>${escapeHtml(obj.type || "Objection")}</strong>
            <span class="badge ${badgeClass}">${escapeHtml(obj.status || "")}</span>
            <div class="muted">${escapeHtml((obj.message || "").replace(/\\n/g, "\n"))}</div>`;
        list.appendChild(li);
    });
    container.appendChild(list);
}

function renderCitations(payload, container) {
    container.innerHTML = "";
    const citations = (payload.result && payload.result.citations) || [];
    if (!citations.length) {
        const p = document.createElement("p");
        p.className = "muted";
        p.textContent = "No citations captured.";
        container.appendChild(p);
        return;
    }
    const list = document.createElement("ul");
    list.className = "citation-list";
    citations.forEach((cit) => {
        const li = document.createElement("li");
        li.textContent = `${cit.policy || "Policy"} — ${cit.section || "Section"} (p.${cit.page || "?"})`;
        list.appendChild(li);
    });
    container.appendChild(list);
}

function renderChecklist(payload, container) {
    container.innerHTML = "";
    const checklist = payload.checklist || {};
    const entries = Object.entries(checklist);
    if (!entries.length) {
        const p = document.createElement("p");
        p.className = "muted";
        p.textContent = "Reviewer called no follow-ups for this run.";
        container.appendChild(p);
        return;
    }
    const list = document.createElement("div");
    list.className = "checklist";
    entries.forEach(([item, done], index) => {
        const id = `check-${index}`;
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox";
        input.id = id;
        input.checked = Boolean(done);
        input.dataset.item = item;
        input.addEventListener("change", handleChecklistChange);
        label.appendChild(input);
        const span = document.createElement("span");
        span.textContent = item;
        label.appendChild(span);
        list.appendChild(label);
    });
    container.appendChild(list);
}

function renderDecision(payload) {
    decisionContent.innerHTML = "";
    const decision = payload.decision || {};
    const metadata = payload.metadata || {};
    const outcome = decision.outcome;

    if (!outcome) {
        decisionSummary.textContent = "Run the review to generate a decision.";
        if (followupContainer) {
            followupContainer.innerHTML = "";
        }
        const p = document.createElement("p");
        p.className = "muted";
        p.textContent =
            "Once the debate completes, the consolidated decision will appear here.";
        decisionContent.appendChild(p);
        return;
    }

    decisionSummary.textContent = metadata.paused_for_user
        ? "Reviewer pause awaiting clarifications"
        : `${outcome} outcome available`;

    const topRow = document.createElement("div");
    topRow.className = "decision-top";

    const decisionCard = document.createElement("div");
    decisionCard.className = "decision-card";
    decisionCard.innerHTML = `<div class="decision-card__label muted">Final outcome</div>
        <div class="decision-card__outcome" style="color:${decisionColor(outcome)}">${escapeHtml(outcome)}</div>
        <p>${escapeHtml(decision.rationale || "No rationale provided.")}</p>`;
    const interpreterRec = decision.interpreter_recommendation;
    if (interpreterRec) {
        const interp = document.createElement("div");
        const color = decisionColor(interpreterRec);
        interp.className = "muted";
        const safeRec = escapeHtml(interpreterRec);
        const pill = `<span class="decision-pill" style="color:${color}; border-color:${color}">${safeRec}</span>`;
        const label =
            interpreterRec === outcome
                ? `Interpreter confirmed ${pill}`
                : `Interpreter suggested ${pill}`;
        interp.innerHTML = label;
        decisionCard.appendChild(interp);
    }
    topRow.appendChild(decisionCard);
    decisionContent.appendChild(topRow);

    const columns = document.createElement("div");
    columns.className = "decision-columns";

    const evidenceColumn = document.createElement("div");
    renderEvidenceGallery(payload, evidenceColumn);
    columns.appendChild(evidenceColumn);

    const invoiceColumn = document.createElement("div");
    renderInvoice(payload, invoiceColumn);
    columns.appendChild(invoiceColumn);

    decisionContent.appendChild(columns);

    renderFollowups(payload);
}

function renderFollowups(payload) {
    if (!followupContainer) {
        return;
    }
    if (!payload.result) {
        followupContainer.innerHTML = "";
        return;
    }
    followupContainer.innerHTML = "";

    const sections = [
        { title: "Objection log", render: renderObjections },
        { title: "Policy citations", render: renderCitations },
        { title: "Reviewer checklist", render: renderChecklist },
    ];

    sections.forEach(({ title, render }) => {
        const card = document.createElement("div");
        card.className = "info-card followup-card";
        const heading = document.createElement("h3");
        heading.textContent = title;
        card.appendChild(heading);
        const body = document.createElement("div");
        render(payload, body);
        card.appendChild(body);
        followupContainer.appendChild(card);
    });
}

function renderContinuePanel(payload) {
    const paused = payload.metadata && payload.metadata.paused_for_user;
    if (!paused || payload.job.case_closed) {
        continueSection.classList.add("hidden");
        continueBody.innerHTML = "";
        return;
    }

    continueSection.classList.remove("hidden");
    continueBody.innerHTML = `<form id="continue-form" class="form" enctype="multipart/form-data">
            <div class="form__row">
                <div class="form__upload">
                    <label for="continue-photos">Additional photos</label>
                    <input id="continue-photos" name="photos" type="file" multiple accept="image/png,image/jpeg,image/webp" />
                </div>
                <div class="form__upload">
                    <label for="continue-invoices">Additional invoices / documents</label>
                    <input id="continue-invoices" name="invoices" type="file" multiple accept="application/pdf" />
                </div>
            </div>
            <div class="form__upload">
                <label for="continue-fnol">Additional FNOL PDFs</label>
                <input id="continue-fnol" name="fnol_files" type="file" multiple accept="application/pdf,text/plain" />
            </div>
            <div class="export-actions">
                <button class="btn btn--primary" type="submit">Continue review</button>
                <button id="btn-continue-skip" class="btn btn--ghost" type="button">Continue without uploads</button>
            </div>
        </form>`;

    const form = document.getElementById("continue-form");
    const skipButton = document.getElementById("btn-continue-skip");
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        submitResumeForm(form, true);
    });
    skipButton.addEventListener("click", () => submitResumeForm(form, false));
}

async function submitResumeForm(form, includeUploads) {
    const actionButton = form.querySelector("button[type='submit']");
    const skipButton = document.getElementById("btn-continue-skip");
    actionButton.disabled = true;
    skipButton.disabled = true;
    try {
        const formData = new FormData();
        if (includeUploads) {
            form.querySelectorAll("input[type='file']").forEach((input) => {
                Array.from(input.files || []).forEach((file) => {
                    formData.append(input.name, file);
                });
            });
        }
        const response = await fetch(`/api/claims/${jobId}/continue`, {
            method: "POST",
            body: formData,
        });
        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || "Failed to continue review");
        }
        showToast(
            includeUploads
                ? "Supplemental evidence submitted."
                : "Continuing without uploads.",
        );
        schedulePoll(true);
    } catch (error) {
        showToast(error.message || "Unable to continue review.", true);
    } finally {
        actionButton.disabled = false;
        skipButton.disabled = false;
    }
}

function renderStory(payload) {
    const highlights = payload.job.story_highlights || [];
    if (!payload.job.story_mode || !highlights.length) {
        storyPanel.classList.add("hidden");
        return;
    }
    storyPanel.classList.remove("hidden");
    const index = payload.job.story_index || 0;
    storyCaption.textContent = highlights[index % highlights.length];
}

function updateExportsState(payload) {
    const hasResults = payload.result && payload.result.turns;
    btnEmail.disabled = !hasResults;
    btnDownload.disabled = !hasResults;
    if (payload.job.case_closed) {
        btnCloseCase.classList.add("hidden");
        btnReopenCase.classList.remove("hidden");
    } else {
        btnCloseCase.classList.remove("hidden");
        btnReopenCase.classList.add("hidden");
    }
    if (followupContainer) {
        if (hasResults) {
            followupContainer.classList.remove("hidden");
        } else {
            followupContainer.classList.add("hidden");
            followupContainer.innerHTML = "";
        }
    }
}

async function handleChecklistChange() {
    if (checklistLock) return;
    try {
        checklistLock = true;
        const checked = Array.from(
            decisionContent.querySelectorAll(".checklist input[type='checkbox']"),
        )
            .filter((input) => input.checked)
            .map((input) => input.dataset.item);

        const params = new URLSearchParams();
        checked.forEach((item) => params.append("items", item));

        const response = await fetch(`/api/claims/${jobId}/checklist`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: params.toString(),
        });
        if (!response.ok) {
            throw new Error("Failed to update checklist");
        }
        await response.json();
    } catch (error) {
        showToast(error.message || "Checklist update failed.", true);
    } finally {
        checklistLock = false;
    }
}

async function generateEmail() {
    try {
        btnEmail.disabled = true;
        const response = await fetch(`/api/claims/${jobId}/email`, { method: "POST" });
        const payload = await response.json();
        if (!response.ok) {
            throw new Error(payload.detail || "Unable to generate email draft");
        }
        emailDraft.textContent = payload.email || "";
        emailDraft.classList.remove("hidden");
        showToast("RFI email draft ready.");
    } catch (error) {
        showToast(error.message || "Email generation failed.", true);
    } finally {
        btnEmail.disabled = false;
    }
}

async function downloadPacket() {
    try {
        btnDownload.disabled = true;
        const response = await fetch(`/api/claims/${jobId}/packet`);
        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || "Unable to download packet");
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${caseId || "claim"}_packet.zip`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);
    } catch (error) {
        showToast(error.message || "Download failed.", true);
    } finally {
        btnDownload.disabled = false;
    }
}

async function closeCase() {
    try {
        const response = await fetch(`/api/claims/${jobId}/close`, { method: "POST" });
        if (!response.ok) {
            throw new Error("Unable to close case.");
        }
        showToast("Case closed.");
        schedulePoll(true);
    } catch (error) {
        showToast(error.message || "Case action failed.", true);
    }
}

async function reopenCase() {
    try {
        const response = await fetch(`/api/claims/${jobId}/reopen`, {
            method: "POST",
        });
        if (!response.ok) {
            throw new Error("Unable to reopen case.");
        }
        showToast("Case reopened.");
        schedulePoll(true);
    } catch (error) {
        showToast(error.message || "Case action failed.", true);
    }
}

async function storyAdvance(endpoint) {
    try {
        const response = await fetch(`/api/story/${jobId}/${endpoint}`, {
            method: "POST",
        });
        if (!response.ok) {
            throw new Error("Story action failed");
        }
        schedulePoll(true);
    } catch (error) {
        showToast(error.message || "Story action failed.", true);
    }
}

function render(payload) {
    const badge = createBadge(payload.job.status);
    statusBadge.textContent = badge.text;
    statusBadge.className = `badge ${badge.cls}`;
    messageEl.textContent = payload.job.message || "";
    createdEl.textContent = formatDate(payload.job.created_at);
    updatedEl.textContent = formatDate(payload.job.updated_at);
    if (payload.job.error) {
        showToast(payload.job.error, true);
    }

    renderStepper(payload);
    renderStory(payload);
    renderKPIs(payload);
    renderClarification(payload);
    renderMetrics(payload);
    renderIntake(payload);
    renderDebate(payload);
    renderDecision(payload);
    renderContinuePanel(payload);
    updateExportsState(payload);
}

async function fetchStatus(silent) {
    try {
        const response = await fetch(`/api/claims/${jobId}`);
        if (!response.ok) {
            const detail = await response.json().catch(() => ({}));
            throw new Error(detail.detail || "Failed to load job status");
        }
        const payload = await response.json();
        render(payload);
        if (!silent) {
            showToast("Status updated");
        }
        if (payload.job.status === "completed" && !payload.metadata.paused_for_user) {
            stopPoll();
        } else if (payload.job.status === "error") {
            stopPoll();
        }
    } catch (error) {
        showToast(error.message || "Unable to fetch status.", true);
    }
}

function stopPoll() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

function schedulePoll(immediate) {
    stopPoll();
    if (immediate) {
        fetchStatus(true);
    }
    pollTimer = setInterval(() => fetchStatus(true), pollIntervalMs);
}

function showToast(message, isError) {
    if (!message) {
        return;
    }
    let toast = document.querySelector(".toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.className = "toast";
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.background = isError ? "#b91c1c" : "#1f2937";
    requestAnimationFrame(() => {
        toast.classList.add("toast--visible");
        setTimeout(() => toast.classList.remove("toast--visible"), 3200);
    });
}

refreshButton.addEventListener("click", () => fetchStatus(true));
btnEmail.addEventListener("click", generateEmail);
btnDownload.addEventListener("click", downloadPacket);
btnCloseCase.addEventListener("click", closeCase);
btnReopenCase.addEventListener("click", reopenCase);
if (storyNext) {
    storyNext.addEventListener("click", () => storyAdvance("next"));
}
if (storyReset) {
    storyReset.addEventListener("click", () => storyAdvance("reset"));
}

schedulePoll(true);
fetchStatus(true);

})();
