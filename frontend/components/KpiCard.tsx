export default function KpiCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="p-4 rounded-xl border bg-white shadow-sm flex flex-col">
      <span className="text-gray-500 text-sm">{label}</span>
      <span className="text-2xl font-semibold mt-1">{value}</span>
    </div>
  );
}

