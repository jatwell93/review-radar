import Link from 'next/link'

export default function UpgradeCancelPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
        <h1 className="text-xl font-bold text-slate-800 mb-2">Upgrade cancelled</h1>
        <p className="text-slate-500 text-sm mb-6">
          No charge was made. You can upgrade any time from your dashboard.
        </p>
        <Link
          href="/dashboard"
          className="inline-block px-6 py-2.5 text-sm font-medium text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  )
}
