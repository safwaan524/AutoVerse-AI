const API_BASE = "http://127.0.0.1:8000/api";
const RECENT_KEY = "autoverse.recentVehicles";
const MAX_RECENT = 4;
const FEATURED_BRANDS = ["Maruti Suzuki", "Hyundai", "Tata", "Mahindra", "Toyota", "Kia"];
const PAGE_ROUTES = {
  dashboard: { title: "Dashboard" },
  explore: { title: "Explore Cars" },
  compare: { title: "Vehicle Comparison" },
  assistant: { title: "AI Assistant" },
  garage: { title: "3D Garage" },
  analytics: { title: "Analytics" },
};

const elements = {
  apiLight: document.querySelector("#status-light"),
  apiStatusLabel: document.querySelector("#api-status-label"),
  apiStatusDetail: document.querySelector("#api-status-detail"),
  vehicleGrid: document.querySelector("#vehicle-grid"),
  resultNotice: document.querySelector("#result-notice"),
  searchForm: document.querySelector("#search-form"),
  searchInput: document.querySelector("#vehicle-search"),
  statRecords: document.querySelector("#stat-records"),
  statTables: document.querySelector("#stat-tables"),
  statEngine: document.querySelector("#stat-engine"),
  recommendationForm: document.querySelector("#recommendation-form"),
  recommendationResults: document.querySelector("#recommendation-results"),
  recommendButton: document.querySelector("#recommend-button"),
  recentList: document.querySelector("#recent-list"),
  dialog: document.querySelector("#vehicle-dialog"),
  dialogTitle: document.querySelector("#dialog-title"),
  dialogBody: document.querySelector("#dialog-body"),
  toast: document.querySelector("#toast"),
  sidebar: document.querySelector("#sidebar"),
  mobileMenu: document.querySelector("#mobile-menu"),
  breadcrumb: document.querySelector("#breadcrumb-current"),
};

let toastTimeout;

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[character]);
}

function formatPrice(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount) || amount <= 0) return "Price unavailable";
  if (amount >= 100000) {
    return `₹${(amount / 100000).toLocaleString("en-IN", {
      maximumFractionDigits: 1,
    })}L`;
  }
  return `₹${amount.toLocaleString("en-IN")}`;
}

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("en-IN") : "—";
}

function getErrorMessage(error) {
  if (error instanceof TypeError) {
    return "Could not reach AutoVerse API. Start the API server and try again.";
  }
  return error.message || "Something went wrong. Please try again.";
}

async function apiRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
  } catch {
    throw new TypeError("Unable to reach the AutoVerse API.");
  }

  const body = await response.json().catch(() => null);
  if (!response.ok || !body?.success) {
    throw new Error(body?.error?.message || `Request failed (${response.status}).`);
  }
  return body.data;
}

function carIllustration() {
  return `
    <svg class="vehicle-silhouette" viewBox="0 0 280 112" fill="none" aria-hidden="true">
      <defs><linearGradient id="miniBody" x1="30" y1="31" x2="243" y2="94" gradientUnits="userSpaceOnUse"><stop stop-color="#D1D3D3"/><stop offset=".48" stop-color="#73777B"/><stop offset="1" stop-color="#C3C5C6"/></linearGradient></defs>
      <ellipse cx="141" cy="93" rx="111" ry="5" fill="#F27B42" fill-opacity=".12"/>
      <path class="body" d="m31 72 8-24c2-7 7-12 14-15l37-14c5-2 10-3 15-3h49c12 0 23 5 31 14l22 24 24 7c7 2 11 8 11 15v7H28v-4c0-4 1-6 3-7Z"/>
      <path class="glass" d="m98 23-37 14c-5 2-8 6-10 11l-3 10h61V23H98Zm20 0v35h78l-18-20c-5-6-12-9-20-10h-40Z"/>
      <path d="M37 68h205" stroke="#F0F1F1" stroke-opacity=".38" stroke-width="1.5"/>
      <path d="M32 75h26m171-9 22 5" stroke="#FF9561" stroke-width="2.5" stroke-linecap="round"/>
      <circle class="wheel" cx="76" cy="81" r="15"/><circle class="wheel-center" cx="76" cy="81" r="7"/>
      <circle class="wheel" cx="207" cy="81" r="15"/><circle class="wheel-center" cx="207" cy="81" r="7"/>
    </svg>`;
}

function renderVehicleCard(vehicle, index) {
  const brand = escapeHTML(vehicle.brand || "—");
  const model = escapeHTML(vehicle.model || "—");
  const variant = escapeHTML(vehicle.variant || "Variant not listed");
  const type = escapeHTML(vehicle.vehicle_type || "Vehicle");
  const fuel = escapeHTML(vehicle.fuel_type || "—");
  const transmission = escapeHTML(vehicle.transmission || "—");
  const mileage = Number(vehicle.mileage_kmpl);
  const mileageText = Number.isFinite(mileage) && mileage > 0
    ? `${escapeHTML(mileage)} km/l`
    : null;
  const engine = Number(vehicle.engine_cc);
  const engineText = Number.isFinite(engine) && engine > 0
    ? `${formatNumber(engine)} cc`
    : null;
  const price = formatPrice(vehicle.ex_showroom_inr);
  const vehicleData = escapeHTML(JSON.stringify(vehicle));

  return `
    <article class="vehicle-card">
      <div class="vehicle-visual">
        <span class="vehicle-number">AV / ${String(index + 1).padStart(2, "0")}</span>
        ${carIllustration()}
        <span class="vehicle-condition ${type.toLowerCase() === "used" ? "is-used" : ""}">${type}</span>
      </div>
      <div class="vehicle-info">
        <div class="vehicle-brand">${brand}</div>
        <div class="vehicle-name-line"><h3>${model}</h3><span class="vehicle-price">${escapeHTML(price)}</span></div>
        <p class="vehicle-variant">${variant}</p>
        <div class="vehicle-specs">
          <span class="spec-chip"><b>Fuel</b> ${fuel}</span>
          <span class="spec-chip"><b>Gearbox</b> ${transmission}</span>
          ${mileageText ? `<span class="spec-chip"><b>Efficiency</b> ${mileageText}</span>` : ""}
          ${engineText ? `<span class="spec-chip"><b>Engine</b> ${engineText}</span>` : ""}
        </div>
      </div>
      <button class="vehicle-card-button" type="button" data-vehicle="${vehicleData}" aria-label="View ${brand} ${model} details"></button>
    </article>`;
}

function renderVehicles(vehicles, { query = "", initial = false } = {}) {
  if (!Array.isArray(vehicles) || vehicles.length === 0) {
    elements.vehicleGrid.innerHTML = `
      <div class="empty-results">
        <strong>No matching vehicles found</strong>
        <span>Try a broader make, model, or fuel type.</span>
      </div>`;
    elements.resultNotice.textContent = query ? `No results for “${query}”.` : "";
    return;
  }
  elements.vehicleGrid.innerHTML = vehicles
    .map((vehicle, index) => renderVehicleCard(vehicle, index))
    .join("");
  elements.resultNotice.textContent = initial
    ? "Live listings from the AutoVerse database"
    : `${vehicles.length} matching ${vehicles.length === 1 ? "vehicle" : "vehicles"} from the AutoVerse database${query ? ` for “${query}”` : ""}`;
}

async function loadVehicles(params, query = "") {
  elements.vehicleGrid.innerHTML = '<div class="loading-card"><span class="spinner"></span> Loading vehicles from AutoVerse...</div>';
  elements.resultNotice.textContent = "";
  try {
    const data = await apiRequest(`/vehicles?${params.toString()}`);
    renderVehicles(data.vehicles, { query });
  } catch (error) {
    elements.vehicleGrid.innerHTML = `
      <div class="empty-results">
        <strong>Vehicle data is temporarily unavailable</strong>
        <span>${escapeHTML(getErrorMessage(error))}</span>
      </div>`;
  }
}

async function loadFeaturedVehicles() {
  elements.vehicleGrid.innerHTML = '<div class="loading-card"><span class="spinner"></span> Loading vehicles from AutoVerse...</div>';
  elements.resultNotice.textContent = "";
  const requests = FEATURED_BRANDS.map(async (brand) => {
    const params = new URLSearchParams({ brand, vehicle_type: "New", limit: "30" });
    const data = await apiRequest(`/vehicles?${params.toString()}`);
    return data.vehicles?.[0] || null;
  });
  const results = await Promise.allSettled(requests);
  const vehicles = results
    .filter((result) => result.status === "fulfilled" && result.value)
    .map((result) => result.value);

  if (!vehicles.length) {
    const error = results.find((result) => result.status === "rejected");
    elements.vehicleGrid.innerHTML = `
      <div class="empty-results">
        <strong>Vehicle data is temporarily unavailable</strong>
        <span>${escapeHTML(getErrorMessage(error?.reason || new Error("No featured vehicle records were returned.")))}</span>
      </div>`;
    return;
  }
  renderVehicles(vehicles, { initial: true });
}

function updateApiStatus(health) {
  const database = health?.database;
  const ollama = health?.ollama;
  const databaseAvailable = Boolean(database?.available);

  elements.apiLight.classList.toggle("is-online", databaseAvailable);
  elements.apiLight.classList.toggle("is-offline", !databaseAvailable);
  elements.apiStatusLabel.textContent = databaseAvailable ? "AutoVerse data live" : "Data engine unavailable";
  elements.apiStatusDetail.textContent = databaseAvailable
    ? `${formatNumber(database.records)} records connected`
    : "Check the local API server";
  elements.statRecords.textContent = formatNumber(database?.records);
  elements.statTables.textContent = formatNumber(database?.tables);

  const modelOnline = Boolean(ollama?.online && ollama?.model_installed);
  elements.statEngine.textContent = modelOnline
    ? (ollama.configured_model || "Online")
    : "Offline";
}

async function loadHealth() {
  try {
    const health = await apiRequest("/health");
    updateApiStatus(health);
  } catch {
    elements.apiLight.classList.add("is-offline");
    elements.apiStatusLabel.textContent = "AutoVerse API offline";
    elements.apiStatusDetail.textContent = "Start the backend on port 8000";
    elements.statRecords.textContent = "—";
    elements.statTables.textContent = "—";
    elements.statEngine.textContent = "Offline";
  }
}

function readRecent() {
  try {
    const history = JSON.parse(localStorage.getItem(RECENT_KEY) || "[]");
    return Array.isArray(history) ? history.slice(0, MAX_RECENT) : [];
  } catch {
    return [];
  }
}

function rememberVehicle(vehicle) {
  const recent = readRecent().filter((item) => (
    item.model !== vehicle.model || item.brand !== vehicle.brand
  ));
  recent.unshift({
    brand: vehicle.brand,
    model: vehicle.model,
    variant: vehicle.variant,
    vehicle_type: vehicle.vehicle_type,
    ex_showroom_inr: vehicle.ex_showroom_inr,
    fuel_type: vehicle.fuel_type,
  });
  try {
    localStorage.setItem(RECENT_KEY, JSON.stringify(recent.slice(0, MAX_RECENT)));
  } catch {
    showToast("This browser could not save recent vehicles.");
  }
  renderRecent();
}

function renderRecent() {
  const recent = readRecent();
  if (!recent.length) {
    elements.recentList.innerHTML = `
      <div class="empty-recent"><span>◷</span><p>Your recently explored vehicles will appear here.</p><a href="#explore">Start exploring <span aria-hidden="true">↗</span></a></div>`;
    return;
  }
  elements.recentList.innerHTML = recent.map((vehicle) => `
    <article class="recent-card">
      <div class="recent-thumb">${carIllustration()}</div>
      <div class="recent-copy">
        <strong>${escapeHTML(vehicle.brand)} ${escapeHTML(vehicle.model)}</strong>
        <span>${escapeHTML(vehicle.variant || "Vehicle")}${vehicle.ex_showroom_inr ? ` · ${escapeHTML(formatPrice(vehicle.ex_showroom_inr))}` : ""}</span>
      </div>
      <button class="recent-open" type="button" data-model="${escapeHTML(vehicle.model)}">View</button>
    </article>`).join("");
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("is-visible");
  window.clearTimeout(toastTimeout);
  toastTimeout = window.setTimeout(() => elements.toast.classList.remove("is-visible"), 2800);
}

function renderRoute() {
  const requestedRoute = window.location.hash.slice(1).toLowerCase();
  const routeId = Object.hasOwn(PAGE_ROUTES, requestedRoute) ? requestedRoute : "dashboard";
  const route = PAGE_ROUTES[routeId];

  if (window.location.hash !== `#${routeId}`) {
    window.history.replaceState(null, "", `#${routeId}`);
  }

  document.querySelectorAll("[data-page-view]").forEach((view) => {
    view.hidden = view.dataset.pageView !== routeId;
  });
  document.querySelectorAll("[data-page-link]").forEach((link) => {
    const isCurrent = link.dataset.pageLink === routeId;
    link.classList.toggle("is-active", isCurrent);
    if (isCurrent) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });

  elements.breadcrumb.textContent = route.title;
  document.title = `AutoVerse AI — ${route.title}`;
  elements.sidebar.classList.remove("is-open");
  elements.mobileMenu.setAttribute("aria-expanded", "false");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function showVehicleDetails(details) {
  const model = details?.model || {};
  const variants = Array.isArray(details?.variants) ? details.variants : [];
  const title = [model.brand_name, model.model_name].filter(Boolean).join(" ");
  elements.dialogTitle.textContent = title || "Vehicle details";
  const variantRows = variants.slice(0, 6).map((variant) => {
    const variantName = escapeHTML(variant.variant_name || "Variant");
    const fuel = escapeHTML(variant.fuel_type || "—");
    const transmission = escapeHTML(variant.transmission || "—");
    const mileage = Number(variant.mileage_kmpl);
    const engine = Number(variant.engine_cc);
    const price = Number(variant.min_ex_showroom);
    const facts = [
      fuel,
      transmission,
      Number.isFinite(engine) && engine > 0 ? `${formatNumber(engine)} cc` : null,
      Number.isFinite(mileage) && mileage > 0 ? `${mileage} km/l` : null,
    ].filter(Boolean).map(escapeHTML).join(" · ");
    return `<div class="dialog-variant"><strong>${variantName}</strong><span>${facts || "Specifications not listed"}</span><b>${price > 0 ? escapeHTML(formatPrice(price)) : "Price unavailable"}</b></div>`;
  }).join("");

  elements.dialogBody.innerHTML = variants.length
    ? `<p class="dialog-subtitle">Database specifications · ${variants.length} ${variants.length === 1 ? "variant" : "variants"}</p><div class="dialog-variants">${variantRows}</div>`
    : '<p class="dialog-subtitle">No variant details are available for this model.</p>';
  elements.dialog.showModal();
}

async function openVehicle(modelName, fallbackVehicle = null) {
  if (fallbackVehicle) rememberVehicle(fallbackVehicle);
  try {
    const details = await apiRequest(`/vehicles/${encodeURIComponent(modelName)}`);
    showVehicleDetails(details);
  } catch (error) {
    showToast(getErrorMessage(error));
  }
}

elements.searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const query = elements.searchInput.value.trim();
  const params = new URLSearchParams({ limit: "9" });
  if (query) params.set("query", query);
  loadVehicles(params, query);
  document.querySelector("#featured-title").scrollIntoView({ behavior: "smooth", block: "start" });
});

document.querySelectorAll("[data-search-filter]").forEach((button) => {
  button.addEventListener("click", () => {
    const params = new URLSearchParams({ limit: "9" });
    params.set(button.dataset.searchFilter, button.dataset.searchValue);
    elements.searchInput.value = "";
    loadVehicles(params);
    document.querySelector("#featured-title").scrollIntoView({ behavior: "smooth", block: "start" });
  });
});

elements.vehicleGrid.addEventListener("click", (event) => {
  const button = event.target.closest("[data-vehicle]");
  if (!button) return;
  try {
    const vehicle = JSON.parse(button.dataset.vehicle);
    if (vehicle.model) openVehicle(vehicle.model, vehicle);
  } catch {
    showToast("Vehicle details could not be opened.");
  }
});

elements.recommendationForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const budget = Number(document.querySelector("#budget-input").value);
  if (!Number.isFinite(budget) || budget <= 0) {
    elements.recommendationResults.innerHTML = '<div class="recommendation-message is-error">Enter a valid budget to find a match.</div>';
    return;
  }

  elements.recommendButton.disabled = true;
  elements.recommendationResults.innerHTML = '<div class="recommendation-message"><span class="spinner"></span> Matching your brief with vehicle data...</div>';
  try {
    const data = await apiRequest("/recommendations", {
      method: "POST",
      body: JSON.stringify({
        budget,
        fuel_preference: document.querySelector("#fuel-select").value,
        seats: 5,
        transmission: "Any",
        usage: "Mixed",
        priority: "Fuel Efficiency",
        limit: 4,
      }),
    });
    const candidates = Array.isArray(data.candidates) ? data.candidates : [];
    const candidateCards = candidates.map((candidate) => `
      <div class="candidate">
        <strong>${escapeHTML(candidate.brand)} ${escapeHTML(candidate.model)}</strong>
        <span>${escapeHTML(candidate.variant || "Variant")} · ${escapeHTML(formatPrice(candidate.ex_showroom_inr))}</span>
      </div>`).join("");
    const rationale = data.ai_rationale
      ? `<details class="recommendation-analysis"><summary>Read the AI-generated analysis</summary><p>Candidate specifications above come from database records. AI-generated commentary may include unverified details.</p><div class="recommendation-rationale">${escapeHTML(data.ai_rationale)}</div></details>`
      : "";
    elements.recommendationResults.innerHTML = `
      ${candidates.length
        ? `<div class="recommendation-candidates">${candidateCards}</div>`
        : '<div class="recommendation-message">No matching vehicles were returned for those preferences.</div>'}
      ${rationale}`;
  } catch (error) {
    elements.recommendationResults.innerHTML = `<div class="recommendation-message is-error">${escapeHTML(getErrorMessage(error))}</div>`;
  } finally {
    elements.recommendButton.disabled = false;
  }
});

elements.recentList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-model]");
  if (button?.dataset.model) openVehicle(button.dataset.model);
});

document.querySelector("#clear-recent").addEventListener("click", () => {
  try {
    localStorage.removeItem(RECENT_KEY);
  } catch {
    showToast("This browser could not clear recent vehicles.");
  }
  renderRecent();
});

elements.mobileMenu.addEventListener("click", () => {
  const isOpen = elements.sidebar.classList.toggle("is-open");
  elements.mobileMenu.setAttribute("aria-expanded", String(isOpen));
});

window.addEventListener("hashchange", renderRoute);
document.addEventListener("click", (event) => {
  if (
    elements.sidebar.classList.contains("is-open")
    && !elements.sidebar.contains(event.target)
    && !elements.mobileMenu.contains(event.target)
  ) {
    elements.sidebar.classList.remove("is-open");
    elements.mobileMenu.setAttribute("aria-expanded", "false");
  }
});

renderRoute();
loadHealth();
loadFeaturedVehicles();
renderRecent();