"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import Sidebar from "../components/Sidebar";
import KpiCard from "../components/KpiCard";
import { useKpi } from "../hooks/useKpi";
import {
  BOARD_PACK_URL,
  fetchExceptions,
  fetchJournal,
  fetchOverview,
  loadSampleData,
  resetDatabase,
  runReconciliation,
  scanInvoices,
  uploadCsv,
} from "../lib/api";

type ChartPoint = {
  month: string;
  metric: string;
  amount: number;
};

type OverviewResponse = {
  kpis: {
    matched_count: number;
    matched_amount: number;
    unmatched_amount: number;
    runway_months: number | null;
    vat_total: number;
    currencies: string[];
    gross_profit: number;
    cash_balance: number;
    collection_rate: number;
  };
  rev_vs_collected: ChartPoint[];
  net_vat: ChartPoint[];
  revenue_table: {
    entity: string;
    month: string;
    revenue: number;
    expense: number;
  }[];
  cash_table: {
    entity: string;
    month: string;
    inflow: number;
    outflow: number;
    net_cash: number;
  }[];
  top_ar: {
    date: string;
    partner: string;
    amount: number;
    invoice_no: string;
  }[];
};

type InvoiceException = {
  date?: string;
  partner?: string;
  amount?: number;
  invoice_no?: string;
};

type BankException = {
  date?: string;
  partner?: string;
  memo?: string;
  description?: string;
  amount?: number;
};

type ExceptionsResponse = {
  unmatched_invoices: InvoiceException[];
  unmatched_bank: BankException[];
  psp_batch: BankException[];
};

type ReconSummary = {
  total_rule1: number;
  total_rule2: number;
  total_rule3: number;
  recent: {
    rule: string;
    match_id: string;
    inv_id?: number;
    bank_id?: number;
    inv_ids?: string;
  }[];
};

type ReconSettingsState = {
  date_window_days: number;
  amount_tolerance: number;
  psp_fee_abs: number;
  psp_fee_pct: number;
  only_psp_names: boolean;
  persist: boolean;
};

const defaultRecon: ReconSettingsState = {
  date_window_days: 3,
  amount_tolerance: 0.5,
  psp_fee_abs: 50,
  psp_fee_pct: 4,
  only_psp_names: true,
  persist: false,
};

type JournalRow = {
  date?: string;
  entity?: string;
  account?: string;
  debit?: number;
  credit?: number;
  ref?: string;
};

export default function Home() {
  const { data: kpi, loading: kpiLoading, error: kpiError, refetch: refetchKpi } =
    useKpi();
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [exceptions, setExceptions] = useState<ExceptionsResponse | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [message, setMessage] = useState<string | null>(null);
  const [messageType, setMessageType] = useState<"success" | "error">("success");
  const [entity, setEntity] = useState("ALL");
  const [reconSettings, setReconSettings] = useState<ReconSettingsState>(defaultRecon);
  const [reconSummary, setReconSummary] = useState<ReconSummary | null>(null);
  const [journalRows, setJournalRows] = useState<JournalRow[]>([]);
  const [journalLoading, setJournalLoading] = useState(false);

  const notify = (type: "success" | "error", text: string) => {
    setMessageType(type);
    setMessage(text);
    setTimeout(() => setMessage(null), 4000);
  };

  const loadOverview = useCallback(async (ent: string) => {
    try {
      setOverviewLoading(true);
      const data = (await fetchOverview(ent)) as OverviewResponse;
      setOverview(data);
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "Kon overview niet laden");
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  const loadExceptions = useCallback(async () => {
    try {
      const data = (await fetchExceptions()) as ExceptionsResponse;
      setExceptions(data);
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "Kon uitzonderingen niet laden");
    }
  }, []);

  useEffect(() => {
    loadOverview(entity);
    loadExceptions();
  }, [entity, loadOverview, loadExceptions]);

  const handleLoadSample = async () => {
    try {
      await loadSampleData();
      notify("success", "Sample data geladen");
      await Promise.all([refetchKpi(), loadOverview(entity), loadExceptions()]);
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "Sample laden faalde");
    }
  };

  const handleReset = async () => {
    try {
      await resetDatabase();
      notify("success", "Database gereset");
      setOverview(null);
      setExceptions(null);
      await refetchKpi();
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "Reset mislukt");
    }
  };

  const handleCsvUpload =
    (dataset: "invoices" | "bank_tx") =>
    async (event: ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      event.target.value = "";
      if (!file) return;
      try {
        await uploadCsv(dataset, file);
        notify("success", `${dataset} geüpload`);
        await Promise.all([refetchKpi(), loadOverview(entity), loadExceptions()]);
      } catch (err) {
        notify("error", err instanceof Error ? err.message : "Upload faalde");
      }
    };

  const handleOcrUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files ? Array.from(event.target.files) : [];
    event.target.value = "";
    if (!files.length) return;
    try {
      await scanInvoices(files);
      notify("success", "OCR-run succesvol");
      await Promise.all([refetchKpi(), loadOverview(entity), loadExceptions()]);
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "OCR faalde");
    }
  };

  const handleRecon = async () => {
    try {
      const result = (await runReconciliation(reconSettings)) as {
        summary: ReconSummary;
      };
      setReconSummary(result.summary);
      notify("success", "Reconciliatie uitgevoerd");
      await Promise.all([refetchKpi(), loadOverview(entity), loadExceptions()]);
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "Reconciliatie faalde");
    }
  };

  const handleFetchJournal = async () => {
    try {
      setJournalLoading(true);
      const data = (await fetchJournal()) as { rows: JournalRow[] };
      setJournalRows(data.rows || []);
    } catch (err) {
      notify("error", err instanceof Error ? err.message : "Kon journaal niet laden");
    } finally {
      setJournalLoading(false);
    }
  };

  const reconInput = (
    key: keyof ReconSettingsState,
    value: string | number | boolean
  ) => {
    setReconSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="flex">
      <Sidebar />
      <main className="flex-1 p-8 bg-gray-50 min-h-screen space-y-8">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold">Mini-TUG Control Center</h1>
            <p className="text-gray-500">Webversie van de eerdere Streamlit flow</p>
          </div>
          <div className="flex gap-3">
            <button
              className="px-4 py-2 bg-gray-900 text-white rounded"
              onClick={handleLoadSample}
            >
              Load sample data
            </button>
            <button
              className="px-4 py-2 bg-red-500 text-white rounded"
              onClick={handleReset}
            >
              Reset DB
            </button>
          </div>
        </header>

        {message && (
          <div
            className={`p-3 rounded ${
              messageType === "success" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-700"
            }`}
          >
            {message}
          </div>
        )}

        <section>
          <h2 className="text-2xl font-semibold mb-4">KPI Snapshot</h2>
          {kpiLoading && <p>Laden...</p>}
          {kpiError && <p className="text-red-500">{kpiError}</p>}
          {!kpiLoading && kpi && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <KpiCard label="Invoices" value={kpi.invoices_count} />
              <KpiCard label="Bank TX" value={kpi.bank_count} />
              <KpiCard
                label="Total revenue"
                value={`€${kpi.total_revenue.toFixed(0)}`}
              />
              <KpiCard
                label="Collection rate"
                value={`${(kpi.collection_rate * 100).toFixed(1)}%`}
              />
            </div>
          )}
        </section>

        <section className="bg-white rounded shadow p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Insight overview</h2>
            <select
              value={entity}
              onChange={(e) => setEntity(e.target.value)}
              className="border rounded px-3 py-2"
            >
              <option value="ALL">ALL entities</option>
              <option value="TUG_NL">TUG_NL</option>
            </select>
          </div>

          {overviewLoading && <p>Data ophalen...</p>}
          {!overviewLoading && overview && (
            <>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KpiCard label="Matched #" value={overview.kpis.matched_count} />
                <KpiCard
                  label="Matched €"
                  value={`€${overview.kpis.matched_amount.toFixed(0)}`}
                />
                <KpiCard
                  label="Unmatched €"
                  value={`€${overview.kpis.unmatched_amount.toFixed(0)}`}
                />
                <KpiCard
                  label="Runway (m)"
                  value={
                    overview.kpis.runway_months
                      ? overview.kpis.runway_months.toFixed(1)
                      : "-"
                  }
                />
              </div>

              <div>
                <h3 className="font-semibold mb-2">Accrued vs collected</h3>
                <div className="overflow-x-auto text-sm">
                  <table className="w-full text-left">
                    <thead>
                      <tr>
                        <th className="py-2">Month</th>
                        <th>Metric</th>
                        <th>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.rev_vs_collected.map((row, idx) => (
                        <tr key={`${row.metric}-${idx}`}>
                          <td className="py-1">{row.month?.slice(0, 10)}</td>
                          <td>{row.metric}</td>
                          <td>€{row.amount.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Net revenue & VAT</h3>
                <div className="overflow-x-auto text-sm">
                  <table className="w-full text-left">
                    <thead>
                      <tr>
                        <th className="py-2">Month</th>
                        <th>Metric</th>
                        <th>Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.net_vat.map((row, idx) => (
                        <tr key={`${row.metric}-${idx}`}>
                          <td className="py-1">{row.month?.slice(0, 10)}</td>
                          <td>{row.metric}</td>
                          <td>€{row.amount.toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-2">Top open AR</h3>
                <div className="overflow-x-auto text-sm">
                  <table className="w-full text-left">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>Partner</th>
                        <th>Amount</th>
                        <th>Invoice #</th>
                      </tr>
                    </thead>
                    <tbody>
                      {overview.top_ar.map((row, idx) => (
                        <tr key={`${row.invoice_no}-${idx}`}>
                          <td>{row.date?.slice(0, 10)}</td>
                          <td>{row.partner}</td>
                          <td>€{row.amount?.toLocaleString()}</td>
                          <td>{row.invoice_no}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </section>

        <section className="bg-white rounded shadow p-6 space-y-4">
          <h2 className="text-xl font-semibold">Data management</h2>
          <div className="grid md:grid-cols-3 gap-4">
            <label className="flex flex-col gap-2">
              <span className="font-medium">Upload invoices CSV</span>
              <input
                type="file"
                accept=".csv"
                onChange={handleCsvUpload("invoices")}
                className="border rounded px-3 py-2"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-medium">Upload bank CSV</span>
              <input
                type="file"
                accept=".csv"
                onChange={handleCsvUpload("bank_tx")}
                className="border rounded px-3 py-2"
              />
            </label>
            <label className="flex flex-col gap-2">
              <span className="font-medium">OCR PDF/JPG/PNG</span>
              <input
                type="file"
                accept=".pdf,.png,.jpg,.jpeg"
                multiple
                onChange={handleOcrUpload}
                className="border rounded px-3 py-2"
              />
            </label>
          </div>
        </section>

        <section className="bg-white rounded shadow p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Reconciliation rules</h2>
            <button
              className="px-4 py-2 bg-blue-600 text-white rounded"
              onClick={handleRecon}
            >
              Run reconciliation
            </button>
          </div>
          <div className="grid md:grid-cols-3 gap-4">
            <label className="flex flex-col text-sm">
              Date window (± days)
              <input
                type="number"
                min={0}
                className="border rounded px-3 py-2"
                value={reconSettings.date_window_days}
                onChange={(e) => reconInput("date_window_days", Number(e.target.value))}
              />
            </label>
            <label className="flex flex-col text-sm">
              Amount tolerance (€)
              <input
                type="number"
                step="0.1"
                className="border rounded px-3 py-2"
                value={reconSettings.amount_tolerance}
                onChange={(e) => reconInput("amount_tolerance", Number(e.target.value))}
              />
            </label>
            <label className="flex flex-col text-sm">
              Max PSP fee (€)
              <input
                type="number"
                className="border rounded px-3 py-2"
                value={reconSettings.psp_fee_abs}
                onChange={(e) => reconInput("psp_fee_abs", Number(e.target.value))}
              />
            </label>
            <label className="flex flex-col text-sm">
              Max PSP fee (%)
              <input
                type="number"
                step="0.1"
                className="border rounded px-3 py-2"
                value={reconSettings.psp_fee_pct}
                onChange={(e) => reconInput("psp_fee_pct", Number(e.target.value))}
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={reconSettings.only_psp_names}
                onChange={(e) => reconInput("only_psp_names", e.target.checked)}
              />
              Alleen PSP namen filteren
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={reconSettings.persist}
                onChange={(e) => reconInput("persist", e.target.checked)}
              />
              Schrijf matches terug naar DB
            </label>
          </div>
          {reconSummary && (
            <div className="text-sm bg-gray-50 border rounded p-3">
              <p>
                Rule1: {reconSummary.total_rule1} · Rule2: {reconSummary.total_rule2} ·
                Rule3: {reconSummary.total_rule3}
              </p>
              <div className="mt-2 space-y-1 max-h-40 overflow-auto">
                {reconSummary.recent.map((row, idx) => (
                  <p key={`${row.match_id}-${idx}`}>
                    {row.rule} – {row.match_id}
                  </p>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="bg-white rounded shadow p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Exceptions</h2>
            <button
              className="text-sm underline"
              onClick={() => loadExceptions()}
            >
              Refresh
            </button>
          </div>
          {!exceptions && <p>Geen data</p>}
          {exceptions && (
            <div className="grid md:grid-cols-3 gap-4 text-sm">
              <div>
                <h3 className="font-semibold mb-1">
                  Unmatched invoices ({exceptions.unmatched_invoices.length})
                </h3>
                <div className="max-h-48 overflow-auto border rounded p-2">
                  {exceptions.unmatched_invoices.map((row, idx) => (
                    <p key={idx}>
                      {row.date?.slice(0, 10)} · {row.partner} · €{row.amount}
                    </p>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-semibold mb-1">
                  Unmatched bank ({exceptions.unmatched_bank.length})
                </h3>
                <div className="max-h-48 overflow-auto border rounded p-2">
                  {exceptions.unmatched_bank.map((row, idx) => (
                    <p key={idx}>
                      {row.date?.slice(0, 10)} · {row.description || row.partner} · €
                      {row.amount}
                    </p>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="font-semibold mb-1">
                  PSP / batch ({exceptions.psp_batch.length})
                </h3>
                <div className="max-h-48 overflow-auto border rounded p-2">
                  {exceptions.psp_batch.map((row, idx) => (
                    <p key={idx}>
                      {row.date?.slice(0, 10)} · {row.partner || row.memo} · €
                      {row.amount}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}
        </section>

        <section className="bg-white rounded shadow p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Journal & Board Pack</h2>
            <div className="flex gap-3">
              <button
                className="px-4 py-2 border rounded"
                onClick={handleFetchJournal}
              >
                {journalLoading ? "Laden..." : "Bekijk journal"}
              </button>
              <a
                className="px-4 py-2 bg-gray-900 text-white rounded"
                href={BOARD_PACK_URL}
                target="_blank"
                rel="noreferrer"
              >
                Download board pack
              </a>
            </div>
          </div>
          {journalRows.length > 0 && (
            <div className="overflow-x-auto text-sm max-h-64 overflow-y-auto border rounded">
              <table className="w-full text-left">
                <thead>
                  <tr>
                    <th className="py-2 px-2">Date</th>
                    <th>Entity</th>
                    <th>Account</th>
                    <th>Debit</th>
                    <th>Credit</th>
                    <th>Ref</th>
                  </tr>
                </thead>
                <tbody>
                  {journalRows.slice(0, 80).map((row, idx) => (
                    <tr key={idx}>
                      <td className="py-1 px-2">{row.date?.slice(0, 10)}</td>
                      <td>{row.entity}</td>
                      <td>{row.account}</td>
                      <td>{row.debit}</td>
                      <td>{row.credit}</td>
                      <td>{row.ref}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {journalRows.length > 80 && (
                <p className="p-2 text-xs text-gray-500">
                  Toon eerste 80 regels — download board pack voor volledige set.
                </p>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
