/** Collection manager UI */
(function () {
  let activeId = null;

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { Accept: "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
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

  loadCollections().catch((err) => alert(err.message));
})();
