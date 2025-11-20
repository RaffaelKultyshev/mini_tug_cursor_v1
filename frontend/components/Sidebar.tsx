import Link from "next/link";

export default function Sidebar() {
  return (
    <div className="w-56 h-screen bg-gray-900 text-white px-4 py-6 flex flex-col gap-4">
      <h1 className="text-xl font-bold">Mini-TUG</h1>
      <nav className="flex flex-col gap-2 text-gray-300">
        <Link className="hover:text-white" href="/">
          Dashboard
        </Link>
      </nav>
    </div>
  );
}
