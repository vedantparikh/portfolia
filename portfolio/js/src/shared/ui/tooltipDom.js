import {
  formatCurrency,
  formatPercentage,
  formatRatio,
} from "../../utils/formatters.jsx";

export function chartMoney(value, currency) {
  return formatCurrency(value, { currency, defaultValue: "N/A" });
}

export function barChange(open, close) {
  return open && close
    ? formatPercentage(((close - open) / open) * 100, { showSign: false })
    : "N/A";
}

export const indicatorValue = (value) => formatRatio(value);

function addRows(parent, rows) {
  const body = document.createElement("div");
  body.className = "space-y-1 text-xs";
  for (const row of rows) {
    const line = document.createElement("div");
    line.className = "flex justify-between items-center";
    const label = document.createElement("span");
    label.className = "text-gray-400";
    label.textContent = row.label;
    const value = document.createElement("span");
    value.className = row.className || "text-gray-200";
    if (row.color) {
      value.style.color = row.color;
    }
    value.textContent = row.value;
    line.append(label, value);
    body.append(line);
  }
  parent.append(body);
}

export function renderTooltip(tooltip, { title, rows, sections = [] }) {
  tooltip.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "text-gray-100 font-semibold mb-2";
  heading.textContent = title;
  tooltip.append(heading);
  addRows(tooltip, rows);
  for (const section of sections) {
    const block = document.createElement("div");
    block.className = "border-t border-gray-600 mt-2 pt-2";
    if (section.title) {
      const sectionTitle = document.createElement("div");
      sectionTitle.className = "text-gray-300 font-medium mb-1";
      sectionTitle.textContent = section.title;
      block.append(sectionTitle);
    }
    addRows(block, section.rows);
    tooltip.append(block);
  }
}
