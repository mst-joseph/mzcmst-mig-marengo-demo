/* ==============================================================================================================================
 *      File     : web/components/ResultGrid.tsx
 *      Project  : MZCMST AI Migration PoC
 *      Description: 검색 결과 그리드 — 데스크탑 4열 / 태블릿 2열 / 모바일 1열. 로딩/빈상태 처리.
 *      Author   : Joseph Kim <josephkim@mz.co.kr>
 *      Date     : 2026-05-11
 *      Branch   : feature/ai-mig-poc-web
 *      Usage    : <ResultGrid results={results} loading={loading} skeletonCount={12} />
 *      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
 *
 *      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
 *      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
 * ============================================================================================================================== */
"use client";

import type { SearchResult } from "@/lib/types";
import { ResultCard } from "./ResultCard";

interface ResultGridProps {
  results: SearchResult[];
  loading: boolean;
  skeletonCount?: number;
  emptyHint?: string;
}

function SkeletonCard() {
  return (
    <div className="flex animate-pulse flex-col overflow-hidden rounded-xl border border-border bg-card">
      <div className="aspect-video w-full bg-muted" />
      <div className="flex flex-col gap-2 p-4">
        <div className="h-4 w-3/4 rounded bg-muted" />
        <div className="h-3 w-1/2 rounded bg-muted" />
        <div className="mt-2 flex justify-between">
          <div className="h-3 w-12 rounded bg-muted" />
          <div className="h-3 w-12 rounded bg-muted" />
        </div>
      </div>
    </div>
  );
}

export function ResultGrid({
  results,
  loading,
  skeletonCount = 12,
  emptyHint = "검색어를 입력하거나 예시 쿼리를 클릭하세요.",
}: ResultGridProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: skeletonCount }).map((_, idx) => (
          <SkeletonCard key={idx} />
        ))}
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card/40 py-16 text-center">
        <p className="text-sm text-muted-foreground">{emptyHint}</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {results.map((r) => (
        <ResultCard key={r.key} result={r} />
      ))}
    </div>
  );
}
