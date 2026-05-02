export interface ReviewItem {
  text: string;
  score: number;
}

export interface TimelineEntry {
  month: string;
  avg_score: number;
  count: number;
}

export interface Distribution {
  positive: number;
  neutral: number;
  negative: number;
}

export interface AnalysisResponse {
  total_reviews: number;
  overall_score: number;
  distribution: Distribution;
  timeline: TimelineEntry[];
  top_reviews: ReviewItem[];
  bottom_reviews: ReviewItem[];
}

export interface NarrativeResponse {
  narrative: string;
}
