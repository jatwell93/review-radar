import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { getSubscriptionStatus } from '@/lib/supabase/subscription'

export default async function DashboardPage() {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  const subscriptionStatus = await getSubscriptionStatus()
  const isPremium = subscriptionStatus === 'active'

  async function logout() {
    'use server'
    const supabase = createClient()
    await supabase.auth.signOut()
    redirect('/login')
  }

  async function initiateUpgrade() {
    'use server'
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) redirect('/login')

    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/stripe/checkout-session`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${session.access_token}` },
      }
    )
    if (!res.ok) {
      if (res.status === 409) redirect('/dashboard')
      throw new Error('Failed to create checkout session')
    }
    const { url } = await res.json()
    redirect(url)
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-sm border border-slate-200 p-8 text-center">
        <h1 className="text-2xl font-bold text-slate-800 mb-2">Review Radar Premium</h1>
        <p className="text-sm text-slate-500 mb-1">Signed in as</p>
        <p className="text-slate-700 font-medium mb-6">{user.email}</p>

        {isPremium ? (
          <div className="mb-8">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
              ✓ Premium Active
            </span>
            <p className="text-slate-500 text-sm mt-4">
              Your premium features are coming soon.
            </p>
          </div>
        ) : (
          <div className="mb-8">
            <p className="text-slate-500 text-sm mb-4">
              Unlock KeyBERT topic extraction, analysis history, and multi-location support.
            </p>
            <form action={initiateUpgrade}>
              <button
                type="submit"
                className="w-full px-6 py-3 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
              >
                Upgrade to Premium — $20/yr
              </button>
            </form>
          </div>
        )}

        <form action={logout}>
          <button
            type="submit"
            className="px-4 py-2 text-sm font-medium text-slate-600 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
          >
            Log out
          </button>
        </form>
      </div>
    </div>
  )
}
