# gosom/google-maps-scraper — Dockerised REST API service for Review Radar
#
# Runs gosom in web server mode (REST API available at :8080).
# API docs at http://localhost:8080/api/docs when running locally.
#
# Render deployment:
#   ACCESS CONTROL — REQUIRED before commercial launch:
#   Paid plan:  Configure this service as a Render Private Service (Render dashboard
#               → service settings → "Private" visibility) so it is not publicly
#               accessible. Set GOSOM_API_URL=http://review-radar-gosom:8080 in
#               the review-radar-api environment variables (internal Render DNS).
#   Free plan:  Service gets a public URL — known risk; any party can trigger
#               scraping via the public URL. Migrate to paid plan (Private Service)
#               before commercial launch to eliminate this abuse vector.

FROM gosom/google-maps-scraper:latest

# Create data directory for gosom's job queue and results storage.
# Data is ephemeral per container lifecycle (no Render persistent disk on free tier).
# This is acceptable: jobs are short-lived scrape tasks, not stored state.
RUN mkdir -p /data

EXPOSE 8080

# -data-folder enables REST API server mode on port 8080.
# API endpoint: POST /api/v1/jobs  GET /api/v1/jobs/{id}  GET /api/v1/jobs/{id}/download
# Full OpenAPI spec: GET /api/docs
CMD ["google-maps-scraper", "-data-folder", "/data"]
