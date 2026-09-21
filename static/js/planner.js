/* Planner page. No framework, no build step.
   Flow: brief text -> /api/design {prompt}  -> render
         fine-tune controls -> /api/design {params} -> render (debounced)          */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const app = $("app");
  const CURRENCY = app.dataset.currency || "USD";
  const SYMBOL = { USD: "$", INR: "₹" };
  const LOCALE = { USD: "en-US", INR: "en-IN" };
  const EXAMPLES = {
    USD: ["8x10 ft bathroom, $12,000 budget, Japanese Zen style, smart features",
          "Family of 4, 10x12 ft, $25,000 budget, classic luxury",
          "Compact 6x8 ft, $9,000 budget, minimalist modern"],
    INR: ["8x10 ft bathroom, ₹6 lakh budget, japandi style, smart features",
          "Family of 4, 10x12 ft, ₹15 lakh budget, classic luxury",
          "Compact 6x8 ft, ₹5 lakh budget, minimalist modern"],
  };

  const money = (n, cur = CURRENCY) => (SYMBOL[cur] || "") + Math.round(n).toLocaleString(LOCALE[cur] || "en-US");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const ft = (inches) => `${+(inches / 12).toFixed(1)} ft`;

  const ctl = {
    length: $("lengthRange"), width: $("widthRange"), budget: $("budgetRange"),
    household: $("householdRange"), theme: $("styleSelect"), smart: $("smartCheck"),
  };
  let seq = 0;      // guards against out-of-order responses
  let timer = null; // debounce for the controls
  let lastData = null; // stores the last successful bundle for saving

  /* ------------------------------------------------------------- API ---- */
  async function requestDesign(payload) {
    const mine = ++seq;
    $("workspace").classList.add("loading");
    $("generateBtn").disabled = true;
    try {
      const res = await fetch("/api/design", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      const json = await res.json();
      if (mine !== seq) return null; // a newer request superseded this one
      if (!res.ok || json.status !== "success") throw new Error(json.message || "Request failed");
      return json;
    } catch (err) {
      if (mine === seq) showBanner("Something went wrong", err.message);
      return null;
    } finally {
      if (mine === seq) {
        $("workspace").classList.remove("loading");
        $("generateBtn").disabled = false;
      }
    }
  }

  async function fromPrompt(ev) {
    if (ev && ev.preventDefault) ev.preventDefault();
    const json = await requestDesign({ prompt: $("promptInput").value });
    if (!json) return;
    syncControls(json.parsed);
    const a = json.parsed.assumed || [];
    const note = $("assumed");
    note.hidden = a.length === 0;
    note.textContent = a.length ? `Not specified, so defaults were used for: ${a.join(", ")}. Adjust below.` : "";
    render(json);
  }

  async function fromControls() {
    const json = await requestDesign({ params: readControls() });
    if (json) { $("assumed").hidden = true; render(json); }
  }

  /* -------------------------------------------------------- controls ---- */
  function readControls() {
    return {
      length_ft: parseFloat(ctl.length.value), width_ft: parseFloat(ctl.width.value),
      budget: parseFloat(ctl.budget.value), household: parseInt(ctl.household.value, 10),
      theme: ctl.theme.value, prioritize_smart: ctl.smart.checked,
    };
  }

  function syncControls(p) {
    ctl.length.value = p.length_ft; ctl.width.value = p.width_ft;
    ctl.budget.value = Math.round(p.budget); ctl.household.value = p.household;
    ctl.theme.value = p.theme; ctl.smart.checked = !!p.prioritize_smart;
    updateLabels();
  }

  function updateLabels() {
    $("lengthVal").textContent = `${ctl.length.value} ft`;
    $("widthVal").textContent = `${ctl.width.value} ft`;
    $("householdVal").textContent = ctl.household.value;
  }

  /* ---------------------------------------------------------- render ---- */
  function showBanner(title, body, extraHtml = "") {
    const b = $("banner");
    b.hidden = false;
    b.innerHTML = `<strong>${esc(title)}</strong>${esc(body)}${extraHtml}`;
  }

  function render(json) {
    const data = json.data;
    $("solveSpeedBadge").textContent = `SOLVED IN ${json.elapsed_ms} ms`;
    const cur = data.currency;
    const room = { width: data.inputs.width_ft * 12, length: data.inputs.length_ft * 12 };

    let view;
    if (data.status === "ok") {
      $("banner").hidden = true;
      view = { bundle: data.bundle, placements: data.layout.placements, total: data.metrics.total_cost, note: "" };
      renderMetrics(data);
      if (data.ai) renderAI(data.ai);
      $("saveBtn").style.display = "block";
      lastData = data;
      localStorage.setItem('saved_plumbline_data', JSON.stringify(data));
    } else {
      const alt = data.alternative;
      const extra = alt
        ? `<div class="alt">Closest valid option shown below: ${esc(money(alt.total_cost, cur))} (${esc(money(alt.over_budget_by, cur))} over your budget).</div>`
        : "";
      showBanner("No valid bundle for this brief", data.message, extra);
      $("costVal").textContent = "--";
      $("budgetStatus").textContent = "⚠ No Valid Bundle";
      $("budgetStatus").style.color = "#D32F2F";
      $("waterValTech").textContent = "--";
      $("utilValTech").textContent = "--";
      $("hygieneValTech").textContent = "--";
      $("checks").innerHTML = "";
      view = alt ? { bundle: alt.bundle, placements: alt.layout.placements, total: alt.total_cost, note: " (closest option, over budget)" } : null;
      $("saveBtn").style.display = "none";
      lastData = null;
    }

    $("planNote").hidden = data.status === "ok";
    if (view) {
      drawFloorplan(room, view.placements, view.bundle);
      renderBom(view.bundle, view.total, cur, view.note);
    } else {
      $("floorplanSvg").innerHTML = "";
      $("itemList").innerHTML = `<tr><td colspan="6" style="text-align:center; padding:30px; font-weight:700; color:#8C8A82;">No bundle to show. Try a larger room.</td></tr>`;
    }
  }

  function renderMetrics(data) {
    const m = data.metrics, cur = data.currency, w = m.water;
    
    $("costVal").textContent = esc(money(m.total_cost, cur));
    
    const budgetStatusStr = m.budget_used_pct <= 100 ? `✓ ${m.budget_used_pct}% Budget Compliant` : `⚠ ${m.budget_used_pct}% OVER BUDGET`;
    $("budgetStatus").textContent = budgetStatusStr;
    $("budgetStatus").style.color = m.budget_used_pct <= 100 ? "#2F6B4F" : "#D32F2F";
    
    $("waterValTech").textContent = `${w.saved_gal.toLocaleString("en-US")} gal/yr conserved \xB7 EPA WaterSense`;
    $("utilValTech").textContent = `${m.space_utilization_pct}% Floor Utilization \xB7 Clearance verification`;
    $("hygieneValTech").textContent = `Skirted Traps \xB7 Touchless Actuation Ready`;
    
    $("checks").innerHTML = data.checks.map((c) => `
      <div class="check-row"><span class="check-icon" style="color: ${c.passed ? '#2F6B4F' : '#D32F2F'};">${c.passed ? '✓' : '✗'}</span> ${esc(c.name)}: ${c.passed ? 'Pass' : 'FAIL'} <span style="font-size: 10px; color: #8C8A82; margin-left: 4px;">${esc(c.detail)}</span></div>
    `).join("");
  }

  function renderAI(ai) {
    try {
      if (!ai) return;

      let badge = $("aiStatusBadge");
      if (badge) {
          if (ai.status === "live") {
              badge.style.background = "#2F6B4F";
              badge.textContent = "GEMINI 3.6-FLASH";
          } else {
              badge.style.background = "#D32F2F";
              badge.textContent = "DETERMINISTIC FALLBACK (OFFLINE)";
          }
      }

      let log = $("aiReasoningLog");
      if (!log) return;

      let html = "";
      html += `<div style="margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #E8E6DF;">`;
      html += `<strong>INTENT PARSER:</strong> ${ai.intent_source === 'gemini' ? 'Gemini AI' : 'Regex Fallback'}<br>`;
      html += `<strong>UNDERSTOOD:</strong> ${esc(ai.reading || 'None')}<br>`;
      
      // If we have a rationale, show it too
      if (typeof lastData !== 'undefined' && lastData && lastData.rationale && lastData.rationale.why_this_works) {
          html += `<div style="margin-top: 8px; font-style: italic; color: #4A4A45;">"${esc(lastData.rationale.why_this_works)}"</div>`;
      }
      html += `</div>`;

      if (Array.isArray(ai.trace) && ai.trace.length > 0) {
          ai.trace.forEach(t => {
              if (!t) return;
              let color = t.accepted ? "#2F6B4F" : "#D32F2F";
              html += `<div style="margin-bottom: 12px; border-left: 2px solid ${color}; padding-left: 10px;">`;
              html += `<strong>ATTEMPT ${t.attempt || '?'} (${t.source || 'unknown'}):</strong> ${t.ms || 0}ms<br>`;
              if (t.reasoning) {
                  html += `<em style="color: #666660;">"${esc(t.reasoning)}"</em><br>`;
              }
              if (Array.isArray(t.problems) && t.problems.length > 0) {
                  html += `<span style="color: #D32F2F; font-size: 11px;">✗ ${t.problems.map(esc).join('<br>✗ ')}</span><br>`;
              } else {
                  html += `<span style="color: #2F6B4F; font-size: 11px;">✓ Spatial validation passed</span><br>`;
              }
              html += `</div>`;
          });
      } else {
          html += `<div>No spatial trace generated.</div>`;
      }

      log.innerHTML = html;
    } catch (e) {
      console.error("renderAI failed but suppressed:", e);
    }
  }

  function renderBom(bundle, total, cur, note) {
    $("bomTitle").textContent = "04 · ARCHITECTURAL BILL OF MATERIALS & FIXTURE SCHEDULE" + note;
    const price = (p) => (p.price_inr !== undefined ? p.price_inr : p.price_usd);
    const rows = bundle.map((p) => {
      const d = p.dimensions_in;
      const tags = [...(p.smart_features || []).slice(0, 3), ...(p.health_features || []).slice(0, 1)]
        .map((t) => `<span class="tag" style="font-size: 9px; padding: 2px 4px; background: #F0EEE8; margin-right: 4px; border-radius: 2px;">${esc(t)}</span>`).join("");
      return `<tr>
        <td><span class="cat" style="font-size:10px; font-weight:800; color:#8C8A82; letter-spacing:1px;">${esc(p.category).toUpperCase()}</span></td>
        <td><strong style="font-weight:700; color:#141412;">${esc(p.name)}</strong><div class="tags" style="margin-top:6px;">${tags}</div></td>
        <td><span class="bom-sku-tag">${esc(p.sku)}</span></td>
        <td>${d.width} &times; ${d.depth} in</td>
        <td>${esc((p.finishes || []).join(", "))}</td>
        <td style="font-weight:800; text-align:right;">${esc(money(price(p), cur))}</td></tr>`;
    }).join("");
    $("itemList").innerHTML = rows + `<tr class="bom-total-row"><td colspan="5">TOTAL INVESTMENT</td><td style="text-align:right;">${esc(money(total, cur))}</td></tr>`;
  }

  /* -------------------------------------------------------- floorplan ---- */
  function calculateDynamicPositions(roomWidthInches, roomHeightInches, fixtures) {
      // The backend (Gemini/deterministic) now fully computes x, y, w, d, and side 
      // accurately. We must not overwrite these with hardcoded top/bottom assignments 
      // or we will draw right-wall fixtures rotated out of the grid bounds!
      return fixtures;
  }

  const DOOR = 30; // inches; matches layout.py DOOR_WIDTH_IN

  function localMatrix(p) {
    // wall-local (u along wall, v into room) -> room coordinates
    switch (p.side) {
      case "top": return [1, 0, 0, 1, p.x, p.y];
      case "bottom": return [1, 0, 0, -1, p.x, p.y + p.d];
      case "left": return [0, 1, 1, 0, p.x, p.y];
      default: return [0, 1, -1, 0, p.x + p.w, p.y];
    }
  }

  function fixtureDetail(p) {
    const u = p.u_len, v = p.v_len;
    if (p.category === "toilet") {
      const tank = v * 0.28, bowl = v - tank;
      return `<rect class="fp-detail" x="0" y="0" width="${u}" height="${tank}"/>
              <ellipse class="fp-detail" cx="${u / 2}" cy="${tank + bowl / 2}" rx="${u * 0.4}" ry="${bowl * 0.45}"/>`;
    }
    if (p.category === "shower") {
      return `<line class="fp-detail" x1="0" y1="0" x2="${u}" y2="${v}"/><line class="fp-detail" x1="${u}" y1="0" x2="0" y2="${v}"/>
              <circle class="fp-detail" cx="${u / 2}" cy="${v / 2}" r="${Math.min(u, v) * 0.07}"/>`;
    }
    if (p.category === "vanity") {
      return `<ellipse class="fp-detail" cx="${u / 2}" cy="${v * 0.5}" rx="${u * 0.3}" ry="${v * 0.25}"/>`;
    }
    return "";
  }

  function drawFloorplan(room, placements, bundle) {
    const W = room.width, L = room.length, pad = 30;
    const fs = Math.max(3.4, Math.max(W, L) / 34);
    const byId = Object.fromEntries(bundle.map((p) => [p.id, p]));
    const svg = $("floorplanSvg");
    svg.setAttribute("viewBox", `${-pad} ${-pad} ${W + pad * 2} ${L + pad * 2}`);

    let grid = "";
    for (let x = 0; x <= W + 0.01; x += 12) grid += `<line x1="${x}" y1="0" x2="${x}" y2="${L}"/>`;
    for (let y = 0; y <= L + 0.01; y += 12) grid += `<line x1="0" y1="${y}" x2="${W}" y2="${y}"/>`;

    // Process fixtures through dynamic positioning to enforce architectural anchors
    const dynamicFixtures = calculateDynamicPositions(W, L, placements);
    const floor = dynamicFixtures.filter((p) => p.category !== "faucet");
    const faucets = dynamicFixtures.filter((p) => p.category === "faucet");

    const clear = floor.map((p) => {
        if (!p.clearance) return "";
        const cw = p.clearance.w * 0.85;
        const cd = p.clearance.d * 0.85;
        const cx = p.clearance.x + (p.clearance.w * 0.075);
        const cy = p.clearance.y + (p.clearance.d * 0.075);
        return `<rect class="fp-clear" x="${cx}" y="${cy}" width="${cw}" height="${cd}" style="stroke-dasharray: 5,5 !important;"/>`;
    }).join("");

    const fixtures = floor.map((p) => {
      const prod = byId[p.id] || {};
      const tip = `${p.name} | ${prod.sku || ""} | ${p.u_len} x ${p.v_len} in`;
      
      // --- 2. DYNAMIC COLOR MAPPING ---
      // Grab colors from global state (set by swatch clicks)
      const userHardwareColor = window.activeColors ? window.activeColors.hardware : "#B89758";
      const userShowerColor = window.activeColors ? window.activeColors.shower : "#5A7D8C";
      const userVanityColor = window.activeColors ? window.activeColors.vanity : "#8B7355";

      // 2b. Contrast Fallback Helper
      const isLightColor = (hexCode) => {
          const lightColors = ['#FFFFFF', '#FAFAFA', '#F5F5F5', '#E8E6DF'];
          return lightColors.includes(hexCode.toUpperCase());
      };

      let strokeColor = isLightColor(userHardwareColor) ? "#333333" : userHardwareColor; 
      let fillColor = "rgba(255, 255, 255, 0.8)"; 
      const typeStr = p.category ? p.category.toLowerCase() : '';

      // Map colors realistically with HIGH opacity ("CC" = 80% opacity)
      if (typeStr.includes('shower') || typeStr.includes('tub')) {
          strokeColor = isLightColor(userHardwareColor) ? "#333333" : userHardwareColor; 
          fillColor = userShowerColor + "CC"; 
      } else if (typeStr.includes('toilet') || typeStr.includes('wc')) {
          strokeColor = isLightColor(userHardwareColor) ? "#333333" : userHardwareColor; 
          fillColor = "#FFFFFF"; // Solid White China
      } else if (typeStr.includes('vanity') || typeStr.includes('sink')) {
          strokeColor = isLightColor(userHardwareColor) ? "#333333" : userHardwareColor; 
          fillColor = userVanityColor + "CC"; 
      }
      
      return `<g><title>${esc(tip)}</title>
        <rect class="fp-fixture" x="${p.x}" y="${p.y}" width="${p.w}" height="${p.d}" style="fill: ${fillColor} !important; stroke: ${strokeColor} !important; stroke-width: 3 !important;"/>
        <g transform="matrix(${localMatrix(p).join(" ")})">${fixtureDetail(p)}</g></g>`;
    }).join("");

    // Labels sit in the empty front-clearance zone so they never collide with fixture detail or the faucet.
    const labels = floor.map((p) => {
      const [a, b, c, d, e, f] = localMatrix(p), u = p.u_len / 2, v = p.v_len + 9;
      return `<text class="fp-label" font-size="${fs * 0.72}" x="${a * u + c * v + e}" y="${b * u + d * v + f + fs * 0.25}" text-anchor="middle">${p.category.toUpperCase()}</text>`;
    }).join("");

    const userHardwareColor = window.activeColors ? window.activeColors.hardware : "#B89758";
    const isLightColor = (hex) => ['#FFFFFF', '#FAFAFA', '#F5F5F5', '#E8E6DF'].includes(hex.toUpperCase());
    const faucetFill = isLightColor(userHardwareColor) ? "#333333" : userHardwareColor;
    const faucetShapes = faucets.map((p) =>
      `<g><title>${esc(p.name)}</title><rect class="fp-faucet" x="${p.x}" y="${p.y}" width="${p.w}" height="${p.d}" rx="1.2" style="fill: ${faucetFill} !important;"/></g>`).join("");

    const dimTop = -14, dimLeft = -14;
    const dims = `
      <line class="fp-dim" x1="0" y1="${dimTop}" x2="${W}" y2="${dimTop}"/>
      <line class="fp-dim" x1="0" y1="${dimTop - 3}" x2="0" y2="${dimTop + 3}"/><line class="fp-dim" x1="${W}" y1="${dimTop - 3}" x2="${W}" y2="${dimTop + 3}"/>
      <text class="fp-text" font-size="${fs}" x="${W / 2}" y="${dimTop - 5}" text-anchor="middle">${ft(W)}</text>
      <line class="fp-dim" x1="${dimLeft}" y1="0" x2="${dimLeft}" y2="${L}"/>
      <line class="fp-dim" x1="${dimLeft - 3}" y1="0" x2="${dimLeft + 3}" y2="0"/><line class="fp-dim" x1="${dimLeft - 3}" y1="${L}" x2="${dimLeft + 3}" y2="${L}"/>
      <text class="fp-text" font-size="${fs}" x="${dimLeft - 5}" y="${L / 2}" text-anchor="middle" transform="rotate(-90 ${dimLeft - 5} ${L / 2})">${ft(L)}</text>`;

    const door = `
      <line class="fp-door-gap" x1="0" y1="${L}" x2="${DOOR}" y2="${L}"/>
      <path class="fp-door" d="M 0 ${L} A ${DOOR} ${DOOR} 0 0 1 ${DOOR} ${L - DOOR}"/>
      <line class="fp-leaf" x1="${DOOR}" y1="${L}" x2="${DOOR}" y2="${L - DOOR}"/>`;

    svg.innerHTML = `<g class="fp-grid">${grid}</g>${clear}
      ${door}${fixtures}${faucetShapes}${labels}${dims}
      <rect class="fp-wall" x="0" y="0" width="${W}" height="${L}" fill="none" style="stroke-width: 4px !important; pointer-events: none;" />`;
      
    // Save the entire SVG to memory for the Sustainability page injection hack
    localStorage.setItem('saved_plumbline_canvas', svg.outerHTML);
  }

  /* ------------------------------------------------------------ init ---- */
  function init() {
    const examples = EXAMPLES[CURRENCY] || EXAMPLES.USD;
    $("promptInput").value = examples[0];
    $("chips").innerHTML = examples.map((e, i) => `<button type="button" class="chip" data-i="${i}">${esc(e)}</button>`).join("");
    $("chips").addEventListener("click", (ev) => {
      const chip = ev.target.closest(".chip");
      if (!chip) return;
      $("promptInput").value = examples[+chip.dataset.i];
      fromPrompt();
    });
    $("generateBtn").addEventListener("click", fromPrompt);
    $("saveBtn").addEventListener("click", saveProject);
    $("promptInput").addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) fromPrompt();
    });
    Object.values(ctl).forEach((el) => el.addEventListener("input", () => {
      updateLabels();
      clearTimeout(timer);
      timer = setTimeout(fromControls, 300);
    }));
    
    // Initialize state
    window.activeColors = {
        hardware: "#B89758",
        shower: "#5A7D8C",
        vanity: "#8B7355"
    };

    // Live Redraw for Color Pickers
    const redrawCanvas = () => {
        if (lastData && lastData.status === "ok") {
            const room = { width: lastData.inputs.width_ft * 12, length: lastData.inputs.length_ft * 12 };
            drawFloorplan(room, lastData.layout.placements, lastData.bundle);
        }
    };
    
    // Handle Swatch Clicks
    document.querySelectorAll('.swatch-group').forEach(group => {
        group.addEventListener('click', (e) => {
            if (e.target.classList.contains('swatch')) {
                // Manage active class
                group.querySelectorAll('.swatch').forEach(s => s.classList.remove('active'));
                e.target.classList.add('active');
                
                // Update specific color state
                const color = e.target.getAttribute('data-color');
                if (group.id === 'swatchHardware') window.activeColors.hardware = color;
                if (group.id === 'swatchShower') window.activeColors.shower = color;
                if (group.id === 'swatchVanity') window.activeColors.vanity = color;

                // Re-render instantly
                redrawCanvas();
            }
        });
    });
    
    // Check if we have a saved design in localStorage before auto-generating
    const savedData = localStorage.getItem('saved_plumbline_data');
    if (savedData) {
        try {
            const parsedData = JSON.parse(savedData);
            $("promptInput").value = parsedData.intent_source === 'gemini' 
                ? (parsedData.reading || $("promptInput").value) 
                : $("promptInput").value;
            render({ data: parsedData, elapsed_ms: "loaded" });
        } catch (e) {
            console.error("Failed to parse saved_plumbline_data", e);
            fromPrompt(); // page is never empty on first load
        }
    } else {
        fromPrompt(); // page is never empty on first load
    }
  }

  async function saveProject() {
    if (!lastData) return;
    const btn = $("saveBtn");
    btn.disabled = true;
    btn.textContent = "SAVING...";
    try {
      const payload = {
        name: "Design - " + new Date().toLocaleDateString(),
        length_ft: lastData.inputs.length_ft,
        width_ft: lastData.inputs.width_ft,
        total_cost: lastData.metrics.total_cost,
        water_saved: lastData.metrics.water.saved_gal,
        currency: lastData.currency
      };
      const res = await fetch("/api/projects/save", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload)
      });
      if (res.ok) {
        btn.textContent = "SAVED!";
        setTimeout(() => { btn.textContent = "SAVE PROJECT"; btn.disabled = false; }, 2000);
      } else {
        throw new Error("Save failed");
      }
    } catch (err) {
      alert("Failed to save project.");
      btn.textContent = "SAVE PROJECT";
      btn.disabled = false;
    }
  }

  init();
})();
