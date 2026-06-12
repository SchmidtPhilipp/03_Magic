/** Collection manager UI */
(function () {
  let activeId = null;
  let scanSessionId = null;

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
        document.querySelectorAll("#detailTabs .nav-link").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const tab = btn.dataset.tab;
        document.getElementById("tabCards").style.display = tab === "cards" ? "block" : "none";
        document.getElementById("tabScan").style.display = tab === "scan" ? "block" : "none";
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

  function renderScanDetections(detections) {
    const tbody = document.getElementById("scanDetections");
    tbody.innerHTML = "";
    detections.forEach((d, idx) => {
      const tr = document.createElement("tr");
      const statusBadge =
        d.status === "accepted"
          ? '<span class="badge bg-success">OK</span>'
          : d.status === "rejected"
            ? '<span class="badge bg-danger">Nein</span>'
            : '<span class="badge bg-secondary">?</span>';
      tr.innerHTML = `
        <td>${idx + 1}</td>
        <td><input class="form-control form-control-sm det-name" value="${d.detected_name || ""}"></td>
        <td><input class="form-control form-control-sm det-set" value="${d.set_code || ""}"></td>
        <td>${statusBadge}</td>
        <td>
          <button class="btn btn-sm btn-outline-success btn-acc" title="Annehmen">✓</button>
          <button class="btn btn-sm btn-outline-danger btn-rej" title="Ablehnen">×</button>
        </td>`;
      tr.querySelector(".btn-acc").onclick = () => updateDetection(d.id, tr, "accepted");
      tr.querySelector(".btn-rej").onclick = () => updateDetection(d.id, tr, "rejected");
      tr.querySelector(".det-name").onchange = (e) =>
        updateDetection(d.id, tr, null, e.target.value);
      tbody.appendChild(tr);
    });
  }

  async function updateDetection(id, row, status, nameOverride) {
    const body = {};
    if (status) body.status = status;
    const nameInput = row.querySelector(".det-name");
    if (nameOverride !== undefined) body.detected_name = nameOverride;
    else if (status) body.detected_name = nameInput.value;
    const setInput = row.querySelector(".det-set");
    if (setInput.value) body.set_code = setInput.value;

    await api(`/collections/api/scan/${scanSessionId}/detections/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    await reloadScanSession();
  }

  async function reloadScanSession() {
    if (!scanSessionId) return;
    const data = await api(`/collections/api/scan/${scanSessionId}`);
    document.getElementById("scanOverlay").src = `${data.overlay_url}?t=${Date.now()}`;
    renderScanDetections(data.detections || []);
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
    document.getElementById("scanPanel").style.display = "block";
    document.getElementById("scanOverlay").src = `${data.overlay_url}?t=${Date.now()}`;
    renderScanDetections(data.detections || []);
    if (!data.detection_count) {
      alert("Keine Karten erkannt — Foto/Licht prüfen oder Karten näher ran.");
    }
    e.target.value = "";
  };

  document.getElementById("btnCommitScan").onclick = async () => {
    if (!scanSessionId) return;
    const data = await api(`/collections/api/scan/${scanSessionId}/commit`, { method: "POST" });
    alert(`${data.added} Karte(n) übernommen.`);
    scanSessionId = null;
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
