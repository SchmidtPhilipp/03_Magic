/** Collection manager UI */
(function () {
  let activeId = null;
  let scanSessionId = null;
  let scanDetections = [];
  let selectedDetectionId = null;
  let scanOriginalUrl = null;

  const STATUS_COLORS = {
    pending: "rgba(230, 170, 40, 0.95)",
    accepted: "rgba(40, 200, 80, 0.95)",
    rejected: "rgba(220, 50, 50, 0.95)",
  };

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { Accept: "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  function setupTabs() {
    document.querySelectorAll("#detailTabs .nav-link").forEach((btn) => {
      btn.onclick = () => {
        document.querySelectorAll("#detailTabs .nav-link").forEach((b) =>
          b.classList.remove("active")
        );
        btn.classList.add("active");
        const tab = btn.dataset.tab;
        document.getElementById("tabCards").style.display =
          tab === "cards" ? "block" : "none";
        document.getElementById("tabScan").style.display =
          tab === "scan" ? "block" : "none";
      };
    });
  }

  async function loadCollections() {
    const data = await api("/collections/api");
    const list = document.getElementById("collectionList");
    list.innerHTML = "";
    data.collections.forEach((c) => {
      const li = document.createElement("li");
      li.className =
        "list-group-item list-group-item-action d-flex justify-content-between";
      if (c.id === activeId) li.classList.add("active");
      li.innerHTML = `<span>${c.name}</span><span class="badge bg-light text-dark">${c.card_count || 0}</span>`;
      li.onclick = () => selectCollection(c.id);
      list.appendChild(li);
    });
  }

  async function selectCollection(id) {
    activeId = id;
    scanSessionId = null;
    scanDetections = [];
    selectedDetectionId = null;
    document.getElementById("scanPanel").style.display = "none";
    document.getElementById("emptyDetail").style.display = "none";
    document.getElementById("detailPanel").style.display = "block";
    await refreshDetail();
    await loadCollections();
  }

  async function refreshDetail() {
    if (!activeId) return;
    const data = await api(`/collections/api/${activeId}`);
    document.getElementById("detailTitle").textContent = data.collection.name;
    document.getElementById("detailCount").textContent = data.cards.length;

    const setFilter = document.getElementById("setFilter");
    const current = setFilter.value;
    setFilter.innerHTML = '<option value="">Alle Sets</option>';
    data.sets.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      setFilter.appendChild(opt);
    });
    setFilter.value = current;

    const filterSet = setFilter.value;
    const tbody = document.getElementById("cardTable");
    tbody.innerHTML = "";
    data.cards
      .filter((c) => !filterSet || (c.set_code || "").toUpperCase() === filterSet)
      .forEach((c) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${c.card_name}</td>
          <td>${c.set_code || "—"}</td>
          <td>${c.collector_number || "—"}</td>
          <td>${c.amount}</td>
          <td><button class="btn btn-sm btn-link text-danger p-0" data-id="${c.id}">×</button></td>`;
        tr.querySelector("button").onclick = () => removeCard(c.id);
        tbody.appendChild(tr);
      });
  }

  function escapeAttr(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function renderScanBoxes() {
    const layer = document.getElementById("scanBoxes");
    layer.innerHTML = "";
    scanDetections.forEach((d) => {
      const box = document.createElement("button");
      box.type = "button";
      box.className = "scan-box";
      box.dataset.id = d.id;
      const color = STATUS_COLORS[d.status] || STATUS_COLORS.pending;
      const selected = d.id === selectedDetectionId;
      Object.assign(box.style, {
        position: "absolute",
        left: `${(d.bbox_x || 0) * 100}%`,
        top: `${(d.bbox_y || 0) * 100}%`,
        width: `${(d.bbox_w || 0) * 100}%`,
        height: `${(d.bbox_h || 0) * 100}%`,
        border: `3px solid ${color}`,
        background: selected ? "rgba(255,255,255,0.12)" : "transparent",
        boxShadow: selected ? `0 0 0 2px ${color}` : "none",
        cursor: "pointer",
        padding: 0,
        margin: 0,
      });
      box.title = d.detected_name || "?";
      box.onclick = (e) => {
        e.preventDefault();
        openScanDetail(d.id);
      };
      layer.appendChild(box);
    });
  }

  function openScanDetail(id) {
    const d = scanDetections.find((x) => x.id === id);
    if (!d) return;
    selectedDetectionId = id;
    document.getElementById("scanDetailPanel").style.display = "block";
    document.getElementById("scanDetailEmpty").style.display = "none";
    document.getElementById("scanDetailName").value = d.detected_name || "";
    document.getElementById("scanDetailSet").value = d.set_code || "";
    document.getElementById("scanDetailMeta").textContent = d.collector_number
      ? `Collector #${d.collector_number}`
      : "";
    const img = document.getElementById("scanDetailImg");
    if (d.image_uri) {
      img.src = d.image_uri;
      img.style.display = "block";
    } else {
      img.removeAttribute("src");
      img.style.display = "none";
    }
    renderScanBoxes();
    renderScanDetections();
  }

  function renderScanDetections() {
    const tbody = document.getElementById("scanDetections");
    tbody.innerHTML = "";
    scanDetections.forEach((d, idx) => {
      const tr = document.createElement("tr");
      if (d.id === selectedDetectionId) tr.classList.add("table-active");
      const statusBadge =
        d.status === "accepted"
          ? '<span class="badge bg-success">OK</span>'
          : d.status === "rejected"
            ? '<span class="badge bg-danger">Nein</span>'
            : '<span class="badge bg-warning text-dark">?</span>';
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td><input class="form-control form-control-sm det-name" value="${escapeAttr(d.detected_name)}"></td>
        <td><input class="form-control form-control-sm det-set" value="${escapeAttr(d.set_code)}"></td>
        <td class="small">${escapeAttr(d.collector_number) || "—"}</td>
        <td>${statusBadge}</td>
        <td>
          <button class="btn btn-sm btn-outline-success btn-acc" title="Annehmen">✓</button>
          <button class="btn btn-sm btn-outline-danger btn-rej" title="Ablehnen">×</button>
        </td>`;
      tr.onclick = (e) => {
        if (e.target.closest("button, input")) return;
        openScanDetail(d.id);
      };
      tr.querySelector(".btn-acc").onclick = (e) => {
        e.stopPropagation();
        patchDetection(d.id, { status: "accepted", detected_name: tr.querySelector(".det-name").value });
      };
      tr.querySelector(".btn-rej").onclick = (e) => {
        e.stopPropagation();
        patchDetection(d.id, { status: "rejected" });
      };
      tr.querySelector(".det-name").onchange = (e) =>
        patchDetection(d.id, { detected_name: e.target.value });
      tbody.appendChild(tr);
    });
  }

  async function patchDetection(id, body) {
    await api(`/collections/api/scan/${scanSessionId}/detections/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    await reloadScanSession();
    if (selectedDetectionId === id) openScanDetail(id);
  }

  function applyScanPayload(data) {
    scanDetections = data.detections || [];
    scanOriginalUrl = data.original_url || scanOriginalUrl;
    const img = document.getElementById("scanOriginal");
    if (scanOriginalUrl) {
      img.src = `${scanOriginalUrl}?t=${Date.now()}`;
    }
    renderScanBoxes();
    renderScanDetections();
    if (selectedDetectionId) {
      const still = scanDetections.find((d) => d.id === selectedDetectionId);
      if (still) openScanDetail(selectedDetectionId);
    }
  }

  async function reloadScanSession() {
    if (!scanSessionId) return;
    const data = await api(`/collections/api/scan/${scanSessionId}`);
    applyScanPayload(data);
  }

  async function removeCard(cardId) {
    await api(`/collections/api/${activeId}/cards/${cardId}`, { method: "DELETE" });
    await refreshDetail();
    await loadCollections();
  }

  document.getElementById("btnNewCollection").onclick = async () => {
    const name = prompt("Name der Sammlung:");
    if (!name) return;
    const coll = await api("/collections/api", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    await loadCollections();
    selectCollection(coll.id);
  };

  document.getElementById("btnDeleteCollection").onclick = async () => {
    if (!activeId || !confirm("Sammlung wirklich löschen?")) return;
    await api(`/collections/api/${activeId}`, { method: "DELETE" });
    activeId = null;
    document.getElementById("detailPanel").style.display = "none";
    document.getElementById("emptyDetail").style.display = "block";
    await loadCollections();
  };

  document.getElementById("addCardForm").onsubmit = async (e) => {
    e.preventDefault();
    await api(`/collections/api/${activeId}/cards`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        card_name: document.getElementById("cardName").value,
        set_code: document.getElementById("setCode").value || null,
        amount: parseInt(document.getElementById("cardAmount").value, 10) || 1,
      }),
    });
    document.getElementById("cardName").value = "";
    document.getElementById("setCode").value = "";
    await refreshDetail();
    await loadCollections();
  };

  document.getElementById("csvImport").onchange = async (e) => {
    const file = e.target.files[0];
    if (!file || !activeId) return;
    const fd = new FormData();
    fd.append("file", file);
    await fetch(`/collections/api/${activeId}/import`, { method: "POST", body: fd }).then(
      async (res) => {
        if (!res.ok) {
          const d = await res.json();
          throw new Error(d.error || "Import failed");
        }
        return res.json();
      }
    );
    e.target.value = "";
    await refreshDetail();
    await loadCollections();
  };

  document.getElementById("scanUpload").onchange = async (e) => {
    const file = e.target.files[0];
    if (!file || !activeId) return;
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`/collections/api/${activeId}/scan`, { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Scan failed");
    scanSessionId = data.session_id;
    selectedDetectionId = null;
    document.getElementById("scanPanel").style.display = "block";
    document.getElementById("scanDetailPanel").style.display = "none";
    document.getElementById("scanDetailEmpty").style.display = "block";
    applyScanPayload(data);
    if (!data.detection_count) {
      alert("Keine Karten erkannt — Foto/Licht prüfen oder Karten näher ran.");
    }
    e.target.value = "";
  };

  document.getElementById("scanDetailAccept").onclick = async () => {
    if (!selectedDetectionId) return;
    await patchDetection(selectedDetectionId, {
      status: "accepted",
      detected_name: document.getElementById("scanDetailName").value,
      set_code: document.getElementById("scanDetailSet").value || null,
    });
  };

  document.getElementById("scanDetailReject").onclick = async () => {
    if (!selectedDetectionId) return;
    await patchDetection(selectedDetectionId, { status: "rejected" });
  };

  document.getElementById("scanDetailName").onchange = async () => {
    if (!selectedDetectionId) return;
    await patchDetection(selectedDetectionId, {
      detected_name: document.getElementById("scanDetailName").value,
    });
  };

  document.getElementById("btnCommitScan").onclick = async () => {
    if (!scanSessionId) return;
    const data = await api(`/collections/api/scan/${scanSessionId}/commit`, {
      method: "POST",
    });
    alert(`${data.added} Karte(n) übernommen.`);
    scanSessionId = null;
    scanDetections = [];
    selectedDetectionId = null;
    document.getElementById("scanPanel").style.display = "none";
    await refreshDetail();
    await loadCollections();
  };

  document.getElementById("setFilter").onchange = refreshDetail;

  document.getElementById("btnOptimize").onclick = async () => {
    const setCode = document.getElementById("setFilter").value;
    const body = setCode ? { set_codes: [setCode] } : {};
    const data = await api(`/collections/api/${activeId}/use-for-optimize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    alert(`${data.card_count} Karten geladen — weiter zum Optimizer.`);
    window.location.href = "/";
  };

  setupTabs();
  loadCollections().catch((err) => alert(err.message));
})();
