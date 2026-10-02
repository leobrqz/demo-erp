// Leonardo Briquezi
// github: https://github.com/leobrqz
// linkedin: https://www.linkedin.com/in/leonardobri

const tokenKey = "erp_demo_access_token";
const usernameKey = "erp_demo_username";
const loginScreen = document.querySelector("#loginScreen");
const appScreen = document.querySelector("#appScreen");
const loginForm = document.querySelector("#loginForm");
const loginError = document.querySelector("#loginError");
const questionForm = document.querySelector("#questionForm");
const questionInput = document.querySelector("#questionInput");
const sendButton = document.querySelector("#sendButton");
const conversation = document.querySelector("#conversation");
const productRows = document.querySelector("#productRows");
const inventoryError = document.querySelector("#inventoryError");

let accessToken = sessionStorage.getItem(tokenKey);

function showLogin(message = "") {
  accessToken = null;
  sessionStorage.removeItem(tokenKey);
  sessionStorage.removeItem(usernameKey);
  loginScreen.hidden = false;
  appScreen.hidden = true;
  loginError.textContent = message;
  loginError.hidden = !message;
  document.querySelector("#password").value = "";
}

function showApp(username) {
  loginScreen.hidden = true;
  appScreen.hidden = false;
  document.querySelector("#signedInAs").textContent = username;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (accessToken) headers.set("Authorization", "Bearer " + accessToken);
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    showLogin("Sua sessão expirou. Entre novamente.");
    throw new Error("Sua sessão expirou.");
  }
  return response;
}

function setApiStatus(online) {
  const status = document.querySelector("#apiStatus");
  status.classList.toggle("offline", !online);
  status.innerHTML = '<span class="status-dot"></span>' + (online ? "Conectada" : "Sem conexão");
}

async function signIn(username, password) {
  const body = new URLSearchParams({ username, password });
  const response = await fetch("/api/v1/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Não foi possível autenticar.");
  }
  const payload = await response.json();
  accessToken = payload.access_token;
  sessionStorage.setItem(tokenKey, accessToken);
  sessionStorage.setItem(usernameKey, username);
  showApp(username);
  await loadDashboard();
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = loginForm.querySelector("button[type=submit]");
  button.disabled = true;
  button.textContent = "Entrando…";
  loginError.hidden = true;
  try {
    const values = new FormData(loginForm);
    await signIn(values.get("username").trim(), values.get("password"));
  } catch (error) {
    loginError.textContent = error.message || "Falha ao entrar.";
    loginError.hidden = false;
  } finally {
    button.disabled = false;
    button.textContent = "Entrar";
  }
});

document.querySelector("#logoutButton").addEventListener("click", () => showLogin());
document.querySelector("#refreshButton").addEventListener("click", loadDashboard);

function money(value) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value));
}

function createCell(text, className = "") {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) cell.className = className;
  return cell;
}

function renderProducts(products) {
  productRows.replaceChildren();
  if (!products.length) {
    const row = document.createElement("tr");
    const cell = createCell("Nenhum produto encontrado.");
    cell.colSpan = 3;
    cell.className = "empty-state";
    row.append(cell);
    productRows.append(row);
    return;
  }

  for (const product of products) {
    const row = document.createElement("tr");
    const name = createCell(product.name, "product-name");
    const price = createCell(money(product.price));
    const stock = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = "stock-tag" + (product.quantity_in_stock <= 10 ? " low" : "");
    badge.textContent = product.quantity_in_stock;
    stock.append(badge);
    row.append(name, price, stock);
    productRows.append(row);
  }
}

async function loadDashboard() {
  if (!accessToken) return;
  inventoryError.hidden = true;
  setApiStatus(false);
  try {
    const [productsResponse, readyResponse] = await Promise.all([
      request("/api/v1/products?page=1&page_size=100"),
      fetch("/health/ready"),
    ]);
    if (!productsResponse.ok) throw new Error("Não consegui carregar os produtos.");
    const page = await productsResponse.json();
    const products = page.items || [];
    const lowStock = products.filter((product) => product.quantity_in_stock <= 10);

    document.querySelector("#productCount").textContent = page.total ?? products.length;
    document.querySelector("#lowStockCount").textContent = lowStock.length;
    document.querySelector("#inventoryTotal").textContent = page.total ?? products.length;
    renderProducts(products);
    setApiStatus(readyResponse.ok);
  } catch (error) {
    if (error.message !== "Sua sessão expirou.") {
      inventoryError.textContent = error.message || "Falha ao carregar os dados.";
      inventoryError.hidden = false;
    }
    setApiStatus(false);
  }
}

function addUserMessage(question) {
  const message = document.createElement("div");
  message.className = "user-message";
  const content = document.createElement("div");
  content.className = "message-content";
  const text = document.createElement("p");
  text.textContent = question;
  content.append(text);
  message.append(content);
  conversation.append(message);
  conversation.scrollTop = conversation.scrollHeight;
}

function addAssistantMessage() {
  const message = document.createElement("div");
  message.className = "assistant-message";
  const content = document.createElement("div");
  content.className = "message-content";
  const loading = document.createElement("span");
  loading.className = "loading-indicator";
  loading.textContent = "Consultando os dados…";
  content.append(loading);
  message.append(content);
  conversation.append(message);
  conversation.scrollTop = conversation.scrollHeight;
  return { content, loading };
}

function flattenProducts(data) {
  const items = [];
  const values = Array.isArray(data) ? data : [data];
  for (const value of values) {
    if (Array.isArray(value)) {
      items.push(...value);
    } else if (value && Array.isArray(value.items)) {
      items.push(...value.items);
    } else if (value && value.name && value.quantity_in_stock !== undefined) {
      items.push(value);
    }
  }
  const seen = new Set();
  return items.filter((item) => {
    const key = item.id || item.name;
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function renderResultProducts(content, data) {
  const products = flattenProducts(data);
  if (!products.length) return;
  const list = document.createElement("div");
  list.className = "result-products";
  for (const product of products.slice(0, 10)) {
    const row = document.createElement("div");
    row.className = "result-product";
    const name = document.createElement("span");
    name.textContent = product.name;
    const details = document.createElement("span");
    details.textContent = product.quantity_in_stock + " un. · " + money(product.price);
    row.append(name, details);
    list.append(row);
  }
  content.append(list);
}

function applyStreamEvent(type, data, state) {
  if (type === "replace") {
    state.content.replaceChildren();
    state.loading = null;
    return;
  }
  if (type === "paragraph") {
    if (state.loading) {
      state.loading.remove();
      state.loading = null;
    }
    const paragraph = document.createElement("p");
    paragraph.textContent = data.text || "";
    state.content.append(paragraph);
    conversation.scrollTop = conversation.scrollHeight;
    return;
  }
  if (type === "done") {
    if (state.loading) {
      state.loading.remove();
      state.loading = null;
    }
    renderResultProducts(state.content, data.data);
    conversation.scrollTop = conversation.scrollHeight;
    return;
  }
  if (type === "error") {
    if (state.loading) state.loading.remove();
    const paragraph = document.createElement("p");
    paragraph.textContent = data.message || "Ocorreu um erro ao consultar o assistente.";
    state.content.append(paragraph);
  }
}

async function readEventStream(response, state) {
  if (!response.body) throw new Error("O navegador não disponibilizou o fluxo da resposta.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  function dispatch(frame) {
    let type = "message";
    const dataLines = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) type = line.slice(6).trim();
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (!dataLines.length) return;
    const data = JSON.parse(dataLines.join("\n"));
    applyStreamEvent(type, data, state);
  }

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done }).replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      dispatch(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  if (buffer.trim()) dispatch(buffer);
}

async function askQuestion(question) {
  const value = question.trim();
  if (!value || !accessToken) return;
  document.querySelector("#welcomeMessage")?.remove();
  addUserMessage(value);
  const state = addAssistantMessage();
  sendButton.disabled = true;
  questionInput.disabled = true;
  try {
    const response = await request("/api/v1/ai/ask/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({ question: value }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || "A consulta não foi concluída.");
    }
    await readEventStream(response, state);
  } catch (error) {
    applyStreamEvent("error", { message: error.message || "Falha na consulta." }, state);
  } finally {
    sendButton.disabled = false;
    questionInput.disabled = false;
    questionInput.focus();
  }
}

questionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = questionInput.value;
  questionInput.value = "";
  await askQuestion(question);
});

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => askQuestion(button.dataset.question));
});

questionInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    questionForm.requestSubmit();
  }
});

async function resumeSession() {
  if (!accessToken) {
    showLogin();
    return;
  }
  showApp(sessionStorage.getItem(usernameKey) || "admin");
  await loadDashboard();
}

resumeSession();
