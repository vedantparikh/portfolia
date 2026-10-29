export function fetchSummary(report) {
  if (!report) return null;
  if (report.error) return report.error;
  const created = (report.portfolios || []).reduce((n, p) => n + p.created, 0);
  const taxes = (report.portfolios || []).reduce((n, p) => n + p.tax_entries_created, 0);
  const parts = [`${created} new transaction${created === 1 ? "" : "s"}`];
  if (taxes) parts.push(`${taxes} tax entr${taxes === 1 ? "y" : "ies"}`);
  if (report.documents) parts.push(`${report.documents} new document${report.documents === 1 ? "" : "s"}`);
  return parts.join(" · ");
}
