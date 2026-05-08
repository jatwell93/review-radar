"use client";

import { useState } from "react";
import type { AnalysisResponse, NarrativeResponse, TopicsResponse } from "@/types/analysis";
import UploadZone from "@/components/UploadZone";
import ResultsDashboard from "@/components/ResultsDashboard";
import { createClient } from "@/lib/supabase/client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [narrative, setNarrative] = useState<string | null>(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);
  const [topics, setTopics] = useState<TopicsResponse | null>(null);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [topicsDenied, setTopicsDenied] = useState(false);

  // Fire-and-forget save for premium users — failure must not interrupt the UI
  async function trySaveAnalysis(data: AnalysisResponse, narrative: string | null) {
    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) return; // Not logged in — skip
      await fetch(`${API_URL}/analyses/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ ...data, narrative }),
      });
      // Silently ignore non-ok responses (403 = not premium, 5xx = DB error)
    } catch {
      // Network failure — silent degradation, free-tier experience unaffected
    }
  }

  async function tryFetchTopics(data: AnalysisResponse) {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      setTopicsDenied(true);
      return;
    }
    setTopicsLoading(true);
    try {
      const res = await fetch(`${API_URL}/topics/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({
          top_reviews: data.top_reviews,
          bottom_reviews: data.bottom_reviews,
        }),
      });
      if (res.ok) {
        const topicsData: TopicsResponse = await res.json();
        setTopics(topicsData);
      } else {
        setTopicsDenied(true); // 401 or 403 — not logged in or not premium
      }
    } catch {
      // Network failure — degrade silently, show nothing (not upsell)
    } finally {
      setTopicsLoading(false);
    }
  }

  async function handleAnalysisSuccess(data: AnalysisResponse) {
    setAnalysisResult(data);
    setNarrativeLoading(true);

    // Snapshot previous score before saving current (avoids race condition)
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    let previousScore: number | null = null;
    let previousDistribution: { positive: number; neutral: number; negative: number } | null = null;
    if (session) {
      try {
        const { data: prev } = await supabase
          .from("analyses")
          .select("overall_score, distribution")
          .eq("user_id", session.user.id)
          .order("created_at", { ascending: false })
          .limit(1)
          .maybeSingle();
        if (prev) {
          previousScore = prev.overall_score;
          previousDistribution = prev.distribution as { positive: number; neutral: number; negative: number };
        }
      } catch {
        // Silent degradation — narrative still works without trend context
      }
    }

    trySaveAnalysis(data, null);
    tryFetchTopics(data); // no await — runs in parallel with narrative

    try {
      const narrativeRes = await fetch(`${API_URL}/narrative/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...data,
          previous_score: previousScore,
          previous_distribution: previousDistribution,
        }),
      });
      if (narrativeRes.ok) {
        const narrativeData: NarrativeResponse = await narrativeRes.json();
        setNarrative(narrativeData.narrative);
      }
      // Non-ok response: leave narrative null (graceful degradation)
    } catch {
      // Network failure: leave narrative null (graceful degradation)
    } finally {
      setNarrativeLoading(false);
    }
  }

  function handleReset() {
    setAnalysisResult(null);
    setNarrative(null);
    setNarrativeLoading(false);
    setTopics(null);
    setTopicsLoading(false);
    setTopicsDenied(false);
  }

  if (analysisResult !== null) {
    return (
      <div className="min-h-screen bg-slate-50 w-full">
        <ResultsDashboard
          data={analysisResult}
          onReset={handleReset}
          narrative={narrative}
          narrativeLoading={narrativeLoading}
          topics={topics}
          topicsLoading={topicsLoading}
          topicsDenied={topicsDenied}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center px-4">
      <h1 className="text-4xl font-bold text-slate-800 mb-4">Review Radar</h1>
      <p className="text-lg text-slate-500 mb-10 text-center max-w-md">
        Upload your Google reviews and get actionable insights in seconds.
      </p>
      <UploadZone onSuccess={handleAnalysisSuccess} />
    </div>
  );
}
