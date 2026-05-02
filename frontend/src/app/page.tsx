"use client";

import { useState } from "react";
import type { AnalysisResponse, NarrativeResponse } from "@/types/analysis";
import UploadZone from "@/components/UploadZone";
import ResultsDashboard from "@/components/ResultsDashboard";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [narrative, setNarrative] = useState<string | null>(null);
  const [narrativeLoading, setNarrativeLoading] = useState(false);

  async function handleAnalysisSuccess(data: AnalysisResponse) {
    setAnalysisResult(data);
    setNarrativeLoading(true);
    try {
      const narrativeRes = await fetch(`${API_URL}/narrative/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
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
  }

  if (analysisResult !== null) {
    return (
      <div className="min-h-screen bg-slate-50 w-full">
        <ResultsDashboard
          data={analysisResult}
          onReset={handleReset}
          narrative={narrative}
          narrativeLoading={narrativeLoading}
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
