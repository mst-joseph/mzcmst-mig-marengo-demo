/* ==============================================================================================================================
 *      File     : web/lib/api.ts
 *      Project  : MZCMST AI Migration PoC
 *      Description: /search API 클라이언트 — NEXT_PUBLIC_USE_MOCK=true 일 때 fixture 응답, 아니면 실 API 호출
 *      Author   : Joseph Kim <josephkim@mz.co.kr>
 *      Date     : 2026-05-11
 *      Branch   : feature/ai-mig-poc-web
 *      Usage    : import { searchVideos } from "@/lib/api"
 *      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
 *
 *      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
 *      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
 * ============================================================================================================================== */
import fixture from "@/fixtures/search-response.json";
import type { SearchRequest, SearchResponse, SearchResult } from "@/lib/types";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const MOCK_LATENCY_MS = 600;

export class SearchApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "SearchApiError";
  }
}

function pickMockResults(query: string, topK: number): SearchResult[] {
  const trimmed = query.trim();
  const allResults = (fixture.results as SearchResult[]) ?? [];
  if (trimmed.length === 0) return [];

  const seed = Array.from(trimmed).reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  const rotated = [...allResults.slice(seed % allResults.length), ...allResults.slice(0, seed % allResults.length)];
  return rotated.slice(0, topK).map((r, idx) => ({
    ...r,
    score: Math.max(0.3, r.score - idx * 0.015),
  }));
}

async function mockSearch(req: SearchRequest, signal?: AbortSignal): Promise<SearchResponse> {
  await new Promise<void>((resolve, reject) => {
    const timer = setTimeout(resolve, MOCK_LATENCY_MS);
    if (signal) {
      signal.addEventListener(
        "abort",
        () => {
          clearTimeout(timer);
          reject(new DOMException("Aborted", "AbortError"));
        },
        { once: true },
      );
    }
  });
  return {
    query: req.query,
    took_ms: MOCK_LATENCY_MS,
    results: pickMockResults(req.query, req.topK ?? 12),
  };
}

async function realSearch(req: SearchRequest, signal?: AbortSignal): Promise<SearchResponse> {
  if (!API_BASE) {
    throw new SearchApiError(500, "NEXT_PUBLIC_API_BASE is not configured.");
  }
  const url = `${API_BASE.replace(/\/$/, "")}/search`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal,
  });
  if (!res.ok) {
    const message = await res.text().catch(() => res.statusText);
    throw new SearchApiError(res.status, message || `Request failed: ${res.status}`);
  }
  return (await res.json()) as SearchResponse;
}

export async function searchVideos(
  req: SearchRequest,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  return USE_MOCK ? mockSearch(req, signal) : realSearch(req, signal);
}

export function isMockMode(): boolean {
  return USE_MOCK;
}
