import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { getSubscriptionStatus } from '@/lib/supabase/subscription'
import CompetitorAnalyser from '@/components/CompetitorAnalyser'

function UpgradePrompt() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 max-w-md w-full text-center">
        <h2 className="text-2xl font-semibold text-slate-800 mb-3">
          Competitor Analysis
        </h2>
        <p className="text-slate-500 mb-6">
          Upgrade to Premium to analyse competitor Google Maps reviews.
        </p>
        <a
          href="/dashboard"
          className="inline-block bg-slate-800 text-white px-6 py-3 rounded-lg font-medium hover:bg-slate-700 transition-colors"
        >
          View Upgrade Options
        </a>
      </div>
    </div>
  )
}

export default async function CompetitorPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const subscriptionStatus = await getSubscriptionStatus()
  const isPremium = subscriptionStatus === 'active'

  if (!isPremium) {
    return <UpgradePrompt />
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-800 mb-6">Competitor Analysis</h1>
        <CompetitorAnalyser />
      </div>
    </div>
  )
}
