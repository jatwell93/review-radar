"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  Cell,
} from "recharts";
import type {
  AnalysisResponse,
  ReviewItem,
  TimelineEntry,
  Distribution,
  TopicsResponse,
} from "@/types/analysis";

interface Props {
  data: AnalysisResponse;
  onReset: () => void;
  narrative?: string | null;
  narrativeLoading?: boolean;
  topics?: TopicsResponse | null;
  topicsLoading?: boolean;
  topicsDenied?: boolean;
}

function sentimentTextColor(score: number): string {
  if (score >= 0.05) return "text-green-600";
  if (score <= -0.05) return "text-red-600";
  return "text-amber-500";
}

function sentimentBadge(score: number): string {
  if (score >= 0.05) return "bg-green-100 text-green-700";
  if (score <= -0.05) return "bg-red-100 text-red-700";
  return "bg-amber-100 text-amber-700";
}

function formatScore(score: number): string {
  return (score >= 0 ? "+" : "") + score.toFixed(2);
}

const DIST_COLORS = ["#16a34a", "#d97706", "#dc2626"];

// audit-added: sanitize cell content to prevent formula injection in Excel/LibreOffice.
// Cells beginning with =, +, -, @ are treated as formulas by spreadsheet apps.
function sanitizeCell(value: string): string {
  const escaped = value.replace(/"/g, '""');
  return /^[=+\-@\t\r]/.test(escaped) ? " " + escaped : escaped;
}

function handleDownloadCSV(data: AnalysisResponse, narrative: string | null) {
  const rows: string[][] = [
    ["Type", "Detail", "Sentiment Score"],
    ["Summary", "Overall Score", data.overall_score.toFixed(4)],
    ["Summary", "Total Reviews", String(data.total_reviews)],
    ["Summary", "Positive Reviews", String(data.distribution.positive)],
    ["Summary", "Neutral Reviews", String(data.distribution.neutral)],
    ["Summary", "Negative Reviews", String(data.distribution.negative)],
  ];
  if (narrative) {
    rows.push(["Narrative", sanitizeCell(narrative), ""]);
  }
  data.top_reviews.forEach((r) =>
    rows.push(["Positive Review", sanitizeCell(r.text), r.score.toFixed(4)])
  );
  data.bottom_reviews.forEach((r) =>
    rows.push(["Critical Review", sanitizeCell(r.text), r.score.toFixed(4)])
  );
  const csv = rows.map((row) => row.map((cell) => `"${cell}"`).join(",")).join("\n");
  // audit-added: prepend UTF-8 BOM (\uFEFF) so Windows Excel opens without
  // character corruption. Matches the BOM-handling requirement from plan 01-02.
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "review-radar-report.csv";
  // audit-added: append to DOM before click (required for Safari) and defer
  // revokeObjectURL to ensure blob URL is not expired before download queues.
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 100);
}

export default function ResultsDashboard({ data, onReset, narrative, narrativeLoading, topics, topicsLoading, topicsDenied }: Props) {
  const timeline: TimelineEntry[] = data.timeline;
  const distribution: Distribution = data.distribution;

  const distData = [
    { name: "Positive", value: distribution.positive },
    { name: "Neutral", value: distribution.neutral },
    { name: "Negative", value: distribution.negative },
  ];

  const noReviews =
    data.top_reviews.length === 0 && data.bottom_reviews.length === 0;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Score Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6 flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-500 mb-1">Overall Sentiment Score</p>
          <p
            className={`text-5xl font-bold ${sentimentTextColor(data.overall_score)}`}
          >
            {formatScore(data.overall_score)}
          </p>
          <p className="text-xs text-slate-400 mt-2">
            Scale: -1 (very negative) to +1 (very positive)
          </p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-semibold text-slate-700">
            {data.total_reviews}
          </p>
          <p className="text-sm text-slate-500">reviews analysed</p>
        </div>
      </div>

      {/* Distribution Row */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-green-50 rounded-xl p-4 text-center border border-green-100">
          <p className="text-2xl font-bold text-green-700">
            {distribution.positive}
          </p>
          <p className="text-sm text-green-600 mt-1">Positive</p>
        </div>
        <div className="bg-amber-50 rounded-xl p-4 text-center border border-amber-100">
          <p className="text-2xl font-bold text-amber-700">
            {distribution.neutral}
          </p>
          <p className="text-sm text-amber-600 mt-1">Neutral</p>
        </div>
        <div className="bg-red-50 rounded-xl p-4 text-center border border-red-100">
          <p className="text-2xl font-bold text-red-700">
            {distribution.negative}
          </p>
          <p className="text-sm text-red-600 mt-1">Negative</p>
        </div>
      </div>

      {/* Trend Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-slate-700 mb-4">
          Sentiment Over Time
        </h2>
        {timeline.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-8">
            No date data available in your CSV
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={timeline}>
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis domain={[-1, 1]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="avg_score"
                stroke="#6366f1"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Distribution Chart */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <h2 className="text-lg font-semibold text-slate-700 mb-4">
          Review Breakdown
        </h2>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={distData}>
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {distData.map((_, index) => (
                <Cell key={index} fill={DIST_COLORS[index]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Review Lists */}
      <div className="mb-6">
        {noReviews ? (
          <p className="text-slate-400 text-sm text-center py-8">
            No individual review data available
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h2 className="text-lg font-semibold text-slate-700 mb-3">
                Most Positive Reviews
              </h2>
              <div className="space-y-3">
                {data.top_reviews.map((review, i) => (
                  <ReviewCard key={i} review={review} />
                ))}
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-700 mb-3">
                Most Critical Reviews
              </h2>
              <div className="space-y-3">
                {data.bottom_reviews.map((review, i) => (
                  <ReviewCard key={i} review={review} />
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Claude Haiku Narrative Summary */}
      <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-6 mb-6">
        <p className="text-xs font-semibold text-indigo-500 uppercase tracking-wide mb-3">
          AI Business Summary
        </p>
        {narrativeLoading ? (
          <div className="space-y-2">
            <div className="h-4 bg-indigo-100 rounded animate-pulse w-full" />
            <div className="h-4 bg-indigo-100 rounded animate-pulse w-5/6" />
            <div className="h-4 bg-indigo-100 rounded animate-pulse w-4/6" />
          </div>
        ) : narrative ? (
          <p className="text-slate-700 text-sm leading-relaxed italic">{narrative}</p>
        ) : (
          <p className="text-slate-400 text-sm italic">Summary unavailable</p>
        )}
      </div>

      {/* Key Themes — KeyBERT topic extraction (premium) */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">
          Key Themes
        </p>
        {topicsLoading ? (
          <div className="space-y-2">
            <div className="h-4 bg-slate-100 rounded animate-pulse w-3/4" />
            <div className="h-4 bg-slate-100 rounded animate-pulse w-1/2" />
          </div>
        ) : topicsDenied ? (
          <p className="text-sm text-slate-400">
            <span className="font-medium text-slate-600">Upgrade to Premium</span> to unlock topic analysis — discover exactly what customers love and complain about.
          </p>
        ) : topics ? (
          <div className="space-y-4">
            {topics.positive_topics.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-2">What customers love</p>
                <div className="flex flex-wrap gap-2">
                  {topics.positive_topics.map((topic) => (
                    <span key={topic} className="px-3 py-1 bg-green-50 text-green-700 border border-green-200 rounded-full text-sm font-medium">
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {topics.negative_topics.length > 0 && (
              <div>
                <p className="text-xs text-slate-400 mb-2">What customers complain about</p>
                <div className="flex flex-wrap gap-2">
                  {topics.negative_topics.map((topic) => (
                    <span key={topic} className="px-3 py-1 bg-red-50 text-red-700 border border-red-200 rounded-full text-sm font-medium">
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {topics.positive_topics.length === 0 && topics.negative_topics.length === 0 && (
              <p className="text-sm text-slate-400 italic">No themes extracted — try a larger review set.</p>
            )}
          </div>
        ) : null /* network failure — show nothing */}
      </div>

      {/* Action Row: Export + Reset */}
      <div className="print:hidden flex flex-wrap justify-center gap-3">
        <button
          onClick={() => handleDownloadCSV(data, narrative ?? null)}
          className="border border-slate-400 text-slate-700 px-6 py-3 rounded-lg font-medium hover:bg-slate-100 transition-colors"
        >
          Download CSV
        </button>
        <button
          onClick={() => window.print()}
          className="border border-slate-400 text-slate-700 px-6 py-3 rounded-lg font-medium hover:bg-slate-100 transition-colors"
        >
          Print / Save PDF
        </button>
        <button
          onClick={onReset}
          className="bg-slate-700 text-white px-6 py-3 rounded-lg font-medium hover:bg-slate-800 transition-colors"
        >
          Analyse another file
        </button>
      </div>
    </div>
  );
}

function ReviewCard({ review }: { review: ReviewItem }) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 shadow-sm">
      <p
        className="text-slate-600 text-sm overflow-hidden"
        style={{
          display: "-webkit-box",
          WebkitLineClamp: 3,
          WebkitBoxOrient: "vertical",
        }}
      >
        {review.text}
      </p>
      <span
        className={`inline-block mt-2 text-xs font-medium px-2 py-0.5 rounded-full ${sentimentBadge(review.score)}`}
      >
        {formatScore(review.score)}
      </span>
    </div>
  );
}
