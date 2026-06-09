// All requests go to /api/... on the same origin. nginx (in the container)
// forwards those to the backend, so the browser never deals with CORS.
const API = "/api";

const MOODS = ["😄", "🙂", "😐", "😕", "😢", "😠", "😴"];

// Hebrew label shown when hovering / selecting each mood.
const MOOD_NAMES = {
  "😄": "שמח",
  "🙂": "טוב",
  "😐": "רגיל",
  "😕": "לא משהו",
  "😢": "עצוב",
  "😠": "כועס",
  "😴": "עייף",
};

// The single piece of state: which day are we looking at.
let currentDay = new Date();

// Which month the overview modal is currently showing (1st of the month).
let monthCursor = new Date();

// --- Helpers ----------------------------------------------------------------

function ymd(d) {
  // Format a Date as "YYYY-MM-DD" in local time.
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function prettyDate(d) {
  return d.toLocaleDateString("he-IL", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });
}

async function api(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.status === 200 ? res.json() : null;
}

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  Object.assign(node, props);
  for (const c of children) node.append(c);
  return node;
}

// --- Load + render one day --------------------------------------------------

async function loadDay() {
  const day = ymd(currentDay);
  document.getElementById("dateLabel").textContent = prettyDate(currentDay);

  const data = await api(`/day/${day}`);

  renderMood(data.mood);
  renderTodos(data.todos);
  renderEntries("positive", data.positive);
  renderEntries("negative", data.negative);
  renderEntries("improve", data.improve);
  renderHobbies(data.hobbies);
}

function renderMood(selected) {
  const row = document.getElementById("moodRow");
  row.innerHTML = "";
  for (const emoji of MOODS) {
    const btn = el("button", {
      className: "mood" + (emoji === selected ? " selected" : ""),
      textContent: emoji,
      title: MOOD_NAMES[emoji],
      onclick: () => setMood(emoji),
    });
    // data-name powers the hover tooltip (see .mood::after in the CSS).
    btn.dataset.name = MOOD_NAMES[emoji];
    row.append(btn);
  }
}

function renderTodos(todos) {
  const list = document.getElementById("todoList");
  list.innerHTML = "";
  if (todos.length === 0) {
    list.append(el("li", { className: "empty", textContent: "עדיין ריק" }));
    return;
  }
  for (const t of todos) {
    const checkbox = el("input", { type: "checkbox", checked: t.done });
    checkbox.onchange = () => updateTodo(t.id, { done: checkbox.checked });

    const text = el("span", { className: "text", textContent: t.text, dir: "auto" });
    const del = el("button", { className: "del", textContent: "×", title: "Delete" });
    del.onclick = () => deleteTodo(t.id);

    list.append(el("li", { className: "item" + (t.done ? " done" : "") }, [checkbox, text, del]));
  }
}

function renderEntries(kind, entries) {
  const list = document.getElementById(kind + "List");
  list.innerHTML = "";
  if (entries.length === 0) {
    list.append(el("li", { className: "empty", textContent: "עדיין ריק" }));
    return;
  }
  for (const e of entries) {
    const bullet = el("span", { className: "bullet", textContent: "•" });
    const text = el("span", { className: "text", textContent: e.text, dir: "auto" });
    const del = el("button", { className: "del", textContent: "×", title: "Delete" });
    del.onclick = () => deleteEntry(e.id);
    list.append(el("li", { className: "item" }, [bullet, text, del]));
  }
}

function renderHobbies(hobbies) {
  const list = document.getElementById("hobbyList");
  list.innerHTML = "";
  if (hobbies.length === 0) {
    list.append(el("li", { className: "empty", textContent: "עדיין אין תחביבים במעקב" }));
    return;
  }
  for (const h of hobbies) {
    const checkbox = el("input", { type: "checkbox", checked: h.done });
    checkbox.onchange = () => setHobbyLog(h.id, checkbox.checked);

    const text = el("span", { className: "text", textContent: h.name, dir: "auto" });
    const del = el("button", { className: "del", textContent: "×", title: "Remove hobby" });
    del.onclick = () => deleteHobby(h.id);

    list.append(el("li", { className: "item" }, [checkbox, text, del]));
  }
}

// --- Actions (each one writes, then reloads the day) ------------------------

async function setMood(emoji) {
  await api("/mood", { method: "PUT", body: JSON.stringify({ day: ymd(currentDay), emoji }) });
  loadDay();
}

async function addTodo(text) {
  await api("/todos", { method: "POST", body: JSON.stringify({ day: ymd(currentDay), text }) });
  loadDay();
}
async function updateTodo(id, patch) {
  await api(`/todos/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
  loadDay();
}
async function deleteTodo(id) {
  await api(`/todos/${id}`, { method: "DELETE" });
  loadDay();
}

async function addEntry(kind, text) {
  await api("/entries", { method: "POST", body: JSON.stringify({ day: ymd(currentDay), kind, text }) });
  loadDay();
}
async function deleteEntry(id) {
  await api(`/entries/${id}`, { method: "DELETE" });
  loadDay();
}

async function addHobby(name) {
  await api("/hobbies", { method: "POST", body: JSON.stringify({ name }) });
  loadDay();
}
async function deleteHobby(id) {
  await api(`/hobbies/${id}`, { method: "DELETE" });
  loadDay();
}
async function setHobbyLog(hobbyId, done) {
  await api("/hobby-logs", { method: "PUT", body: JSON.stringify({ day: ymd(currentDay), hobby_id: hobbyId, done }) });
  loadDay();
}

// --- Month mood overview ----------------------------------------------------
// The backend only exposes one endpoint (/api/day/{day}), so we build the
// monthly mood table on the client by fetching each day of the month at once.

const HE_WEEKDAYS = ["א", "ב", "ג", "ד", "ה", "ו", "ש"];

function openMonth() {
  monthCursor = new Date(currentDay.getFullYear(), currentDay.getMonth(), 1);
  document.getElementById("monthModal").hidden = false;
  renderMonth();
}

function closeMonth() {
  document.getElementById("monthModal").hidden = true;
}

async function renderMonth() {
  const year = monthCursor.getFullYear();
  const month = monthCursor.getMonth();

  document.getElementById("monthLabel").textContent =
    monthCursor.toLocaleDateString("he-IL", { month: "long", year: "numeric" });

  const grid = document.getElementById("monthGrid");
  grid.innerHTML = "";

  // Weekday header row (Sunday-first, the Hebrew convention).
  for (const w of HE_WEEKDAYS) {
    grid.append(el("div", { className: "cell head", textContent: w }));
  }

  const firstWeekday = new Date(year, month, 1).getDay(); // 0 = Sunday
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const todayStr = ymd(new Date());

  // Empty padding cells so day 1 lands under the right weekday.
  for (let i = 0; i < firstWeekday; i++) {
    grid.append(el("div", { className: "cell blank" }));
  }

  const slots = [];
  for (let d = 1; d <= daysInMonth; d++) {
    const dayStr = ymd(new Date(year, month, d));
    const num = el("span", { className: "num", textContent: String(d) });
    const moodSlot = el("span", { className: "cmood" });
    const cell = el("div", {
      className: "cell day" + (dayStr === todayStr ? " today" : ""),
    }, [num, moodSlot]);
    cell.onclick = () => {
      currentDay = new Date(year, month, d);
      closeMonth();
      loadDay();
    };
    grid.append(cell);
    slots.push({ dayStr, moodSlot });
  }

  // Pull every day's mood in parallel and drop the emoji into its cell.
  await Promise.all(slots.map(async ({ dayStr, moodSlot }) => {
    try {
      const data = await api(`/day/${dayStr}`);
      if (data && data.mood) {
        moodSlot.textContent = data.mood;
        moodSlot.title = MOOD_NAMES[data.mood] || "";
      }
    } catch (_) { /* a day with no data is just blank */ }
  }));
}

// --- Wire up inputs and navigation ------------------------------------------

function onEnter(inputId, handler) {
  const input = document.getElementById(inputId);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && input.value.trim()) {
      handler(input.value.trim());
      input.value = "";
    }
  });
}

onEnter("todoInput", addTodo);
onEnter("positiveInput", (t) => addEntry("positive", t));
onEnter("negativeInput", (t) => addEntry("negative", t));
onEnter("improveInput", (t) => addEntry("improve", t));
onEnter("hobbyInput", addHobby);

document.getElementById("prevDay").onclick = () => {
  currentDay.setDate(currentDay.getDate() - 1);
  loadDay();
};
document.getElementById("nextDay").onclick = () => {
  currentDay.setDate(currentDay.getDate() + 1);
  loadDay();
};
document.getElementById("todayBtn").onclick = () => {
  currentDay = new Date();
  loadDay();
};

// Month overview modal controls.
document.getElementById("monthBtn").onclick = openMonth;
document.getElementById("closeMonth").onclick = closeMonth;
document.getElementById("prevMonth").onclick = () => {
  monthCursor.setMonth(monthCursor.getMonth() - 1);
  renderMonth();
};
document.getElementById("nextMonth").onclick = () => {
  monthCursor.setMonth(monthCursor.getMonth() + 1);
  renderMonth();
};
// Close on backdrop click or Esc.
document.getElementById("monthModal").addEventListener("click", (e) => {
  if (e.target.id === "monthModal") closeMonth();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeMonth();
});

loadDay();
