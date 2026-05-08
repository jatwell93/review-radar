import { createClient } from '@/lib/supabase/server'

export type SubscriptionStatus = 'active' | 'past_due' | 'canceled' | 'inactive'

export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  // Wrap in try/catch — Supabase query failure must not crash the dashboard page
  try {
    const supabase = createClient()
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return 'inactive'

    const { data } = await supabase
      .from('subscriptions')
      .select('status')
      .eq('user_id', user.id)
      .single()

    if (!data) return 'inactive'
    return data.status as SubscriptionStatus
  } catch {
    // Degrade gracefully — treat DB errors as unsubscribed, not premium
    return 'inactive'
  }
}
