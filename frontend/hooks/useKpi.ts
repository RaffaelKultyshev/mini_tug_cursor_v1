"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../lib/api";

export interface KPIResponse {
  invoices_count: number;
  bank_count: number;
  total_revenue: number;
  collection_rate: number;
}

export function useKpi() {
  const [data, setData] = useState<KPIResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKpi = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiGet<KPIResponse>("/kpi");
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKpi();
  }, [fetchKpi]);

  return { data, loading, error, refetch: fetchKpi };
}
