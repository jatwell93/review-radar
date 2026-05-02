"use client";

import { useState } from "react";
import type { DragEvent, ChangeEvent } from "react";
import type { AnalysisResponse } from "@/types/analysis";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
if (!process.env.NEXT_PUBLIC_API_URL) {
  console.warn("NEXT_PUBLIC_API_URL not set, falling back to localhost:8000");
}

interface Props {
  onSuccess: (data: AnalysisResponse) => void;
}

export default function UploadZone({ onSuccess }: Props) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  async function handleFile(file: File) {
    setError(null);

    if (!file.name.endsWith(".csv")) {
      setError("Only CSV files are accepted.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("File exceeds 10 MB limit.");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/analyze/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let detail = "Request failed. Please try again.";
        try {
          const json = await response.json();
          if (json?.detail) detail = String(json.detail);
        } catch {
          // non-JSON error body — keep default message
        }
        setError(detail);
        return;
      }

      const data = (await response.json()) as AnalysisResponse;
      onSuccess(data);
    } catch {
      setError("Request failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleDragOver(e: DragEvent<HTMLDivElement>) {
    if (isLoading) return;
    e.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave() {
    setIsDragging(false);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    if (isLoading) return;
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset so same file can be re-uploaded after an error
    e.target.value = "";
  }

  return (
    <div className="w-full max-w-lg">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
          isDragging
            ? "border-indigo-500 bg-indigo-50"
            : "border-slate-300 hover:border-slate-400"
        } ${isLoading ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
      >
        {isLoading ? (
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-slate-500 text-sm">Analysing…</p>
          </div>
        ) : (
          <>
            <p className="text-slate-600 mb-3 font-medium">
              Drag &amp; drop your CSV file here
            </p>
            <p className="text-slate-400 text-sm mb-5">or click to browse</p>
            <label
              className={`bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors ${
                isLoading ? "cursor-not-allowed opacity-50" : "cursor-pointer"
              }`}
            >
              Choose File
              <input
                type="file"
                accept=".csv"
                className="hidden"
                disabled={isLoading}
                onChange={handleChange}
              />
            </label>
          </>
        )}
      </div>

      {error && (
        <p className="mt-4 text-sm text-red-600 text-center">{error}</p>
      )}
    </div>
  );
}
