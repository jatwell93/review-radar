import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { getSubscriptionStatus } from "@/lib/supabase/subscription";

interface Analysis {
  id: string;
  overall_score: number;
  total_reviews: number;
  distribution: { positive: number; neutral: number; negative: number };
  created_at: string;
}

function UpgradePrompt() {
  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 max-w-md w-full text-center">
        <h2 className="text-2xl font-semibold text-slate-800 mb-3">
          Analysis History
        </h2>
        <p className="text-slate-500 mb-6">
          Upgrade to Premium to save and review your analysis history over time.
        </p>
        <a
          href="/dashboard"
          className="inline-block bg-slate-800 text-white px-6 py-3 rounded-lg font-medium hover:bg-slate-700 transition-colors"
        >
          View Upgrade Options
        </a>
      </div>
    </div>
  );
}

function ComparisonCard({ current, previous }: { current: Analysis; previous: Analysis }) {
  const scoreDelta = current.overall_score - previous.overall_score;
  const deltaSign = scoreDelta > 0 ? "+" : "";
  const deltaColor = scoreDelta > 0.02
    ? "text-emerald-600"
    : scoreDelta < -0.02
    ? "text-red-600"
    : "text-slate-500";
  const arrow = scoreDelta > 0.02 ? "↑" : scoreDelta < -0.02 ? "↓" : "→";

  const posDelta = current.distribution.positive - previous.distribution.positive;
  const negDelta = current.distribution.negative - previous.distribution.negative;
  const neuDelta = current.distribution.neutral - previous.distribution.neutral;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-6">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-4">
        Latest vs Previous
      </p>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-1">Previous</p>
          <p className="text-2xl font-bold text-slate-700">{previous.overall_score.toFixed(2)}</p>
          <p className="text-xs text-slate-400">{new Date(previous.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</p>
        </div>
        <div className="flex flex-col items-center justify-center">
          <span className={`text-3xl font-bold ${deltaColor}`}>{arrow}</span>
          <span className={`text-sm font-medium ${deltaColor}`}>{deltaSign}{scoreDelta.toFixed(2)}</span>
        </div>
        <div className="text-center">
          <p className="text-xs text-slate-400 mb-1">Latest</p>
          <p className="text-2xl font-bold text-slate-700">{current.overall_score.toFixed(2)}</p>
          <p className="text-xs text-slate-400">{new Date(current.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</p>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs border-t border-slate-100 pt-4">
        <div>
          <p className="text-slate-400 mb-1">Positive</p>
          <p className={`font-medium ${posDelta > 0 ? "text-emerald-600" : posDelta < 0 ? "text-red-600" : "text-slate-500"}`}>
            {posDelta >= 0 ? "+" : ""}{posDelta}
          </p>
        </div>
        <div>
          <p className="text-slate-400 mb-1">Neutral</p>
          <p className={`font-medium ${neuDelta > 0 ? "text-slate-700" : neuDelta < 0 ? "text-slate-400" : "text-slate-500"}`}>
            {neuDelta >= 0 ? "+" : ""}{neuDelta}
          </p>
        </div>
        <div>
          <p className="text-slate-400 mb-1">Negative</p>
          <p className={`font-medium ${negDelta < 0 ? "text-emerald-600" : negDelta > 0 ? "text-red-600" : "text-slate-500"}`}>
            {negDelta >= 0 ? "+" : ""}{negDelta}
          </p>
        </div>
      </div>
    </div>
  );
}

function HistoryList({ analyses }: { analyses: Analysis[] }) {
  if (analyses.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-10 max-w-md w-full text-center">
          <h2 className="text-2xl font-semibold text-slate-800 mb-3">
            Analysis History
          </h2>
          <p className="text-slate-500">
            No analyses saved yet. Upload a CSV to get started.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold text-slate-800 mb-6">
          Analysis History
        </h1>
        {analyses.length >= 2 && (
          <ComparisonCard current={analyses[0]} previous={analyses[1]} />
        )}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-6 py-4 font-medium text-slate-500">
                  Date
                </th>
                <th className="text-left px-6 py-4 font-medium text-slate-500">
                  Overall Score
                </th>
                <th className="text-left px-6 py-4 font-medium text-slate-500">
                  Reviews
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {analyses.map((analysis) => (
                <tr key={analysis.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4 text-slate-700">
                    {new Date(analysis.created_at).toLocaleDateString("en-US", {
                      month: "long",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </td>
                  <td className="px-6 py-4 text-slate-700 font-medium">
                    {analysis.overall_score.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-slate-500">
                    {analysis.total_reviews}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default async function HistoryPage() {
  const supabase = createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const subscriptionStatus = await getSubscriptionStatus();
  const isPremium = subscriptionStatus === "active";

  if (!isPremium) {
    return <UpgradePrompt />;
  }

  // Query user's analyses — RLS filters by auth.uid(), explicit .eq is defense-in-depth
  const { data: analyses } = await supabase
    .from("analyses")
    .select("id, overall_score, total_reviews, distribution, created_at")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(50);

  return <HistoryList analyses={analyses ?? []} />;
}
