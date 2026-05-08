export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <div className="text-center mb-8">
          <span className="text-2xl font-bold text-slate-800">Review Radar</span>
          <p className="text-sm text-slate-500 mt-1">Part of Pharm IQ</p>
        </div>
        {children}
      </div>
    </div>
  )
}
