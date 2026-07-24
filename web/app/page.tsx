/* ==============================================================================================================================
 *      File     : web/app/page.tsx
 *      Project  : MZCMST AI Migration PoC
 *      Description: 데모 메인 페이지 — SearchBar + ResultGrid 합성, 검색 상태 관리, AbortController 로 이전 요청 취소
 *      Author   : Joseph Kim <josephkim@mz.co.kr>
 *      Date     : 2026-05-11
 *      Branch   : feature/ai-mig-poc-web
 *      Usage    : pnpm dev | pnpm build
 *      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
 *
 *      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
 *      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
 * ============================================================================================================================== */
"use client";

import { useRef, useState } from "react";
import { ResultGrid } from "@/components/ResultGrid";
import { SearchBar } from "@/components/SearchBar";
import { isMockMode, searchVideos } from "@/lib/api";
import type { SearchResult } from "@/lib/types";

const TOP_K = 12;
// score(=1-cosine_distance) 가 이 값 이상이면 의미 매칭으로 간주. 이하는 노이즈로 보고 숨김.
const MATCH_THRESHOLD = 0.1;

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [tookMs, setTookMs] = useState<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function runSearch(text: string) {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      const response = await searchVideos(
        { query: text, topK: TOP_K },
        controller.signal,
      );
      setResults(response.results.filter((r) => r.score >= MATCH_THRESHOLD));
      setTookMs(response.took_ms);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        return;
      }
      setResults([]);
      setTookMs(null);
      const message =
        err instanceof Error ? err.message : "검색 중 오류가 발생했습니다.";
      setError(message);
    } finally {
      if (abortRef.current === controller) {
        setLoading(false);
      }
    }
  }

  const emptyHint = hasSearched
    ? "결과 없음. 다른 자연어 쿼리를 시도해 보세요."
    : "검색어를 입력하거나 예시 쿼리를 클릭하세요.";

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col px-4 py-6 sm:px-6 lg:px-8">
      <header className="flex flex-col gap-2 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
            AI Migration · Semantic Video Search
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            자연어 쿼리로 영상 segment 를 즉시 검색합니다.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="rounded-md border border-border bg-card px-2 py-1">
            Seoul · ap-northeast-2
          </span>
          {isMockMode() && (
            <span className="rounded-md border border-secondary/40 bg-secondary/10 px-2 py-1 text-secondary">
              MOCK MODE
            </span>
          )}
        </div>
      </header>

      <section className="py-8 sm:py-10">
        <SearchBar
          value={query}
          onChange={setQuery}
          onSubmit={runSearch}
          disabled={loading}
        />
      </section>

      <section className="flex flex-col gap-4 pb-10">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {hasSearched && !loading && results.length > 0
              ? `${results.length}건 결과`
              : ""}
          </span>
          <span>
            {tookMs !== null && !loading ? `응답 ${tookMs} ms` : ""}
          </span>
        </div>

        {error && (
          <div className="flex items-center justify-between rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => runSearch(query)}
              className="rounded-md border border-destructive/50 px-3 py-1 text-xs font-medium hover:bg-destructive/20"
            >
              다시 시도
            </button>
          </div>
        )}

        <ResultGrid
          results={results}
          loading={loading}
          skeletonCount={TOP_K}
          emptyHint={emptyHint}
        />
      </section>
    </main>
  );
}
