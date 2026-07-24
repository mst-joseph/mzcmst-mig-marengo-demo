/* ==============================================================================================================================
 *      File     : web/components/ResultCard.tsx
 *      Project  : MZCMST AI Migration PoC
 *      Description: 검색 결과 카드 — thumbnail, 파일명, segment 시간, score, 미디어 타입 chip
 *      Author   : Joseph Kim <josephkim@mz.co.kr>
 *      Date     : 2026-05-11
 *      Branch   : feature/ai-mig-poc-web
 *      Usage    : <ResultCard result={result} />
 *      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
 *
 *      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
 *      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
 * ============================================================================================================================== */
"use client";

import type { SearchResult } from "@/lib/types";
import { MediaThumbnail } from "./MediaThumbnail";

interface ResultCardProps {
  result: SearchResult;
}

function formatSegment(seconds: number): string {
  const totalSec = Math.max(0, Math.floor(seconds));
  const mm = Math.floor(totalSec / 60)
    .toString()
    .padStart(2, "0");
  const ss = (totalSec % 60).toString().padStart(2, "0");
  return `${mm}:${ss}`;
}

function fileNameOf(path: string): string {
  const parts = path.split("/");
  return parts[parts.length - 1] ?? path;
}

function buildPlaybackHref(playbackUrl: string, segmentStart: number): string {
  const fragment = `#t=${segmentStart}`;
  return `${playbackUrl}${playbackUrl.includes("#") ? "" : fragment}`;
}

export function ResultCard({ result }: ResultCardProps) {
  const href = buildPlaybackHref(result.playback_url, result.segment_start);
  const fileName = fileNameOf(result.file_path);
  const segmentLabel = `${formatSegment(result.segment_start)} – ${formatSegment(result.segment_end)}`;
  const scoreLabel = result.score.toFixed(3);

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${fileName} — segment ${segmentLabel} 새 탭에서 열기`}
      className="group flex flex-col overflow-hidden rounded-xl border border-border bg-card transition-all duration-200 hover:-translate-y-0.5 hover:shadow-card-hover"
    >
      <div className="relative aspect-video w-full overflow-hidden bg-muted">
        <MediaThumbnail
          src={result.playback_url}
          mediaType={result.media_type}
          segmentStart={result.segment_start}
          alt={fileName}
        />
        <span className="absolute right-2 top-2 rounded-md bg-background/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-foreground backdrop-blur-sm">
          {result.media_type}
        </span>
        <span className="absolute bottom-2 left-2 rounded-md bg-background/80 px-2 py-0.5 text-xs font-medium text-foreground backdrop-blur-sm">
          {segmentLabel}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-1 p-4">
        <h3 className="truncate text-sm font-semibold text-card-foreground" title={fileName}>
          {fileName}
        </h3>
        <p className="truncate text-xs text-muted-foreground" title={result.file_path}>
          {result.file_path}
        </p>
        <div className="mt-2 flex items-center justify-between text-xs">
          <div className="flex items-baseline gap-2">
            <span className="text-muted-foreground">유사도</span>
            <span className="font-mono font-semibold text-primary">{scoreLabel}</span>
          </div>
          <span className="rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-primary">
            Match
          </span>
        </div>
      </div>
    </a>
  );
}
