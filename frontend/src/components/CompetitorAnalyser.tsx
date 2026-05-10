'use client'

import { useState, useEffect } from 'react'
import { createClient } from '@/lib/supabase/client'

interface Review {
  text: string
  rating: number
}

interface ScrapeResult {
  name: string
  overall_rating: number
  reviews: Review[]
}

interface GapDistribution {
  positive: number
  neutral: number
  negative: number
}

interface GapCompetitor {
  name: string
  overall_rating: number
  vader_score: number
  distribution: GapDistribution
  topics: string[]
  review_count: number
}

interface GapOwn {
  overall_score: number
  distribution: GapDistribution
  total_reviews: number
  created_at: string
}

interface GapResult {
  competitor: GapCompetitor
  own: GapOwn | null
}

function DistributionBar({ dist, total }: { dist: GapDistribution; total: number }) {
  const pct = (n: number) => total > 0 ? Math.round((n / total) * 100) : 0
  return (
    <div className="space-y-1.5 text-xs mt-3">
      <div className="flex justify-between text-slate-500">
        <span>Positive</span>
        <span className="text-emerald-600 font-medium">{pct(dist.positive)}%</span>
      </div>
      <div className="flex justify-between text-slate-500">
        <span>Neutral</span>
        <span className="font-medium">{pct(dist.neutral)}%</span>
      </div>
      <div className="flex justify-between text-slate-500">
        <span>Negative</span>
        <span className="text-red-500 font-medium">{pct(dist.negative)}%</span>
      </div>
    </div>
  )
}

// audit-added: GapPanel extracts delta computation out of JSX (replaces IIFE anti-pattern).
// Same idiom as ComparisonCard in history/page.tsx — precompute variables, then return JSX.
function GapPanel({ gapResult }: { gapResult: GapResult }) {
  const delta = gapResult.own
    ? gapResult.own.overall_score - gapResult.competitor.vader_score
    : null
  const deltaColor = delta === null
    ? ''
    : delta > 0.02 ? 'text-emerald-600'
    : delta < -0.02 ? 'text-red-600'
    : 'text-slate-500'
  const deltaArrow = delta === null ? '' : delta > 0.02 ? '↑' : delta < -0.02 ? '↓' : '→'
  const deltaLabel = delta === null
    ? ''
    : delta > 0.02
    ? `You are ${Math.abs(delta).toFixed(2)} ahead of your competitor`
    : delta < -0.02
    ? `You are ${Math.abs(delta).toFixed(2)} behind your competitor`
    : 'You are tied with your competitor'

  return (
    <>
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Own pharmacy card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Your Pharmacy
          </p>
          {gapResult.own ? (
            <>
              <p className="text-3xl font-bold text-slate-800 mb-0.5">
                {gapResult.own.overall_score.toFixed(2)}
              </p>
              <p className="text-xs text-slate-400">
                VADER score · {gapResult.own.total_reviews} reviews
              </p>
              <DistributionBar
                dist={gapResult.own.distribution}
                total={gapResult.own.total_reviews}
              />
            </>
          ) : (
            <p className="text-sm text-slate-400">Upload your reviews to compare</p>
          )}
        </div>

        {/* Competitor card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
            Competitor
          </p>
          <p className="text-sm font-medium text-slate-700 mb-1 truncate">
            {gapResult.competitor.name || 'Unknown'}
          </p>
          <p className="text-3xl font-bold text-slate-800 mb-0.5">
            {gapResult.competitor.vader_score.toFixed(2)}
          </p>
          <p className="text-xs text-slate-400">
            VADER score · {gapResult.competitor.review_count} reviews
            {' · '}
            {gapResult.competitor.overall_rating.toFixed(1)} ★ Google
          </p>
          <DistributionBar
            dist={gapResult.competitor.distribution}
            total={gapResult.competitor.review_count}
          />
          {gapResult.competitor.topics.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {gapResult.competitor.topics.map((t, i) => (
                <span key={i} className="px-2 py-0.5 text-xs bg-slate-100 text-slate-600 rounded-full">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {delta !== null && (
        <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 text-center">
          <span className={`text-sm font-semibold ${deltaColor}`}>
            {deltaArrow} {deltaLabel}
          </span>
        </div>
      )}
    </>
  )
}

interface UsageData {
  count: number
  limit: number
  month: string
}

function formatMonth(yyyyMM: string): string {
  const [year, mon] = yyyyMM.split('-').map(Number)
  return new Date(year, mon - 1, 1).toLocaleDateString('en-AU', { month: 'long', year: 'numeric' })
}

function formatNextMonth(yyyyMM: string): string {
  const [year, mon] = yyyyMM.split('-').map(Number)
  // mon is 1-indexed; Date month is 0-indexed, so new Date(year, mon, 1) = first day of next month
  // Handles December: new Date(2026, 12, 1) → January 2027 (JS Date auto-wraps)
  return new Date(year, mon, 1).toLocaleDateString('en-AU', { month: 'long', year: 'numeric' })
}

export default function CompetitorAnalyser() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ScrapeResult | null>(null)
  const [gapResult, setGapResult] = useState<GapResult | null>(null)
  const [gapLoading, setGapLoading] = useState(false)
  const [gapError, setGapError] = useState<string | null>(null)
  const [usageData, setUsageData] = useState<UsageData | null>(null)

  useEffect(() => {
    async function fetchUsage() {
      try {
        const supabase = createClient()
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) return
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/competitor/usage`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        })
        if (!res.ok) return  // non-premium or network error — degrade silently; backend enforces limit
        const data = await res.json()
        setUsageData(data)
      } catch {
        // silent failure — leave button enabled; backend will enforce on submit
      }
    }
    void fetchUsage()
  }, [])

  async function runGapAnalysis(scrapeData: ScrapeResult, token: string) {
    setGapLoading(true)
    setGapError(null)
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 30_000)
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/competitor/gap`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
        body: JSON.stringify(scrapeData),
      })
      if (!res.ok) {
        setGapError('Gap analysis unavailable — showing raw results')
        return
      }
      try {
        const data = await res.json()
        setGapResult(data)
      } catch {
        setGapError('Gap analysis unavailable — showing raw results')
      }
    } catch {
      setGapError('Gap analysis unavailable — showing raw results')
    } finally {
      clearTimeout(timer)
      setGapLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    if (
      !url.startsWith('https://www.google.com/maps') &&
      !url.startsWith('https://maps.google.com')
    ) {
      setError('Please enter a valid Google Maps place URL')
      return
    }

    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) {
      setError('Your session has expired. Please log in again.')
      return
    }
    const token = session.access_token

    setLoading(true)
    setError(null)
    setResult(null)
    setGapResult(null)
    setGapError(null)

    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 240_000)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/competitor/scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        signal: controller.signal,
        body: JSON.stringify({ url }),
      })

      if (!res.ok) {
        if (res.status === 422) {
          setError('Please enter a valid Google Maps place URL')
          return
        }
        if (res.status === 429) {
          setError('Monthly scan limit reached. Your limit resets next month.')
          return
        }
        setError('Could not reach the scraper — please try again shortly')
        return
      }

      try {
        const data = await res.json()
        setResult(data)
        // Increment local count to reflect consumed quota without a re-fetch round-trip
        setUsageData(prev => prev ? { ...prev, count: prev.count + 1 } : prev)
        // Fire gap analysis without await — loading/error managed independently
        void runGapAnalysis(data, token)
      } catch {
        setError('Unexpected response from server — please try again')
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Scraper timed out — please try again')
      } else {
        setError('Could not reach the scraper — please try again shortly')
      }
    } finally {
      clearTimeout(timer)
      setLoading(false)
    }
  }

  const atLimit = usageData !== null && usageData.count >= usageData.limit

  return (
    <>
      <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-6">
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Competitor Google Maps URL
        </label>
        <input
          type="url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://www.google.com/maps/place/..."
          disabled={loading}
          className="w-full px-4 py-2.5 border border-slate-300 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 mb-4"
        />
        {usageData && (
          <div className="mb-4">
            {atLimit ? (
              <p className="text-sm text-amber-600 font-medium">
                Monthly limit reached. Resets {formatNextMonth(usageData.month)}.
              </p>
            ) : (
              <p className="text-sm text-slate-500">
                {usageData.count} / {usageData.limit} scans used in {formatMonth(usageData.month)}
              </p>
            )}
          </div>
        )}
        {error && (
          <p className="text-sm text-red-600 mb-4">{error}</p>
        )}
        <button
          type="submit"
          disabled={loading || !url.trim() || atLimit}
          className="px-6 py-2.5 text-sm font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Scraping reviews…' : 'Analyse Competitor'}
        </button>
      </form>

      {loading && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800 mb-6">
          Scraping reviews can take 1–3 minutes. Please keep this page open.
        </div>
      )}

      {result && (
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
          <h2 className="text-xl font-bold text-slate-800 mb-1">{result.name || 'Unknown'}</h2>
          <p className="text-slate-500 text-sm mb-4">
            Overall rating: <span className="font-semibold text-slate-700">{result.overall_rating.toFixed(1)} ★</span>
            {' · '}
            {result.reviews.length} review{result.reviews.length !== 1 ? 's' : ''} scraped
          </p>
          {result.reviews.length === 0 ? (
            <p className="text-slate-400 text-sm">No reviews were returned for this place.</p>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {result.reviews.map((r, i) => (
                <div key={i} className="border-b border-slate-100 pb-3 last:border-0">
                  <p className="text-xs text-slate-400 mb-0.5">{'★'.repeat(Math.round(r.rating))} ({r.rating.toFixed(1)})</p>
                  <p className="text-sm text-slate-700">{r.text || <em className="text-slate-400">No review text</em>}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {(gapLoading || gapResult || gapError) && (
        <div className="mt-2">
          <h2 className="text-xl font-bold text-slate-800 mb-4">Gap Analysis</h2>

          {gapLoading && (
            <div className="bg-slate-50 rounded-2xl border border-slate-200 p-6 text-sm text-slate-500 text-center">
              Running sentiment analysis…
            </div>
          )}

          {gapError && !gapLoading && (
            <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
              {gapError}
            </p>
          )}

          {/* audit-added: compute delta variables before return — no IIFE in JSX (non-idiomatic,
              re-creates function on every render, confuses React DevTools).
              Follow ComparisonCard pattern from history/page.tsx: precompute, then render. */}
          {gapResult && !gapLoading && <GapPanel gapResult={gapResult} />}
        </div>
      )}
    </>
  )
}
