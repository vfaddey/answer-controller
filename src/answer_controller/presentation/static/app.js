class Dashboard {
  constructor() {
    this.elements = {
      tickets: document.querySelector("#tickets"),
      empty: document.querySelector("#empty"),
      error: document.querySelector("#error"),
      summary: document.querySelector("#summary"),
      direction: document.querySelector("#direction"),
      created: document.querySelector("#created"),
      answered: document.querySelector("#answered"),
      overdue: document.querySelector("#overdue"),
      median: document.querySelector("#median"),
    };
    this.labels = { normal: "В норме", warning: "Внимание", overdue: "Просрочено" };
    this.timer = null;
  }

  start() {
    this.elements.direction.addEventListener("input", this.debounce(() => this.refreshTickets(), 350));
    this.refresh();
    this.timer = window.setInterval(() => this.refresh(), 12000);
  }

  async refresh() {
    await Promise.all([this.refreshTickets(), this.refreshMetrics()]);
  }

  async refreshTickets() {
    const direction = this.elements.direction.value.trim();
    const query = direction ? `?direction=${encodeURIComponent(direction)}` : "";
    try {
      const response = await fetch(`/api/tickets${query}`);
      if (!response.ok) throw new Error(response.statusText);
      const tickets = await response.json();
      this.renderTickets(tickets);
      this.elements.error.hidden = true;
    } catch {
      this.elements.error.hidden = false;
    }
  }

  async refreshMetrics() {
    try {
      const response = await fetch("/api/metrics");
      if (!response.ok) throw new Error(response.statusText);
      const metrics = await response.json();
      this.elements.created.textContent = metrics.created;
      this.elements.answered.textContent = metrics.answered;
      this.elements.overdue.textContent = metrics.overdue;
      this.elements.median.textContent = metrics.median_first_response_seconds === null
        ? "—"
        : this.duration(metrics.median_first_response_seconds);
    } catch {
      this.elements.error.hidden = false;
    }
  }

  renderTickets(tickets) {
    this.elements.tickets.replaceChildren(...tickets.map((ticket) => this.ticketRow(ticket)));
    this.elements.empty.hidden = tickets.length !== 0;
    this.elements.summary.textContent = `${tickets.length} ${this.plural(tickets.length)}`;
  }

  ticketRow(ticket) {
    const row = document.createElement("tr");
    row.append(
      this.cell(ticket.client_id, ticket.channel),
      this.cell(ticket.direction),
      this.cell(ticket.text, null, "message"),
      this.cell(this.duration(ticket.waiting_seconds), null, "waiting"),
      this.statusCell(ticket.sla_status),
    );
    return row;
  }

  cell(text, detail = null, className = null) {
    const cell = document.createElement("td");
    if (className) cell.className = className;
    cell.textContent = text;
    if (detail) {
      const small = document.createElement("small");
      small.textContent = detail;
      cell.append(small);
    }
    return cell;
  }

  statusCell(status) {
    const cell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `badge ${status}`;
    badge.textContent = this.labels[status];
    cell.append(badge);
    return cell;
  }

  duration(value) {
    const seconds = Math.max(0, Math.round(value));
    const minutes = Math.floor(seconds / 60);
    return minutes ? `${minutes} мин ${seconds % 60} сек` : `${seconds} сек`;
  }

  plural(value) {
    if (value % 10 === 1 && value % 100 !== 11) return "обращение";
    if ([2, 3, 4].includes(value % 10) && ![12, 13, 14].includes(value % 100)) return "обращения";
    return "обращений";
  }

  debounce(action, delay) {
    let timeout = null;
    return (...args) => {
      window.clearTimeout(timeout);
      timeout = window.setTimeout(() => action(...args), delay);
    };
  }
}

new Dashboard().start();
