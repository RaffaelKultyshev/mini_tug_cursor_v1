import { API_URL } from "../../lib/api";

export async function getKPI() {
  const res = await fetch(`${API_URL}/kpi`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch KPI");
  return res.json();
}

