/* ==============================================================================================================================
 *      File     : web/components/MediaThumbnail.tsx
 *      Project  : MZCMST AI Migration PoC
 *      Description: 검색 결과 카드 썸네일 — 영상은 segment_start 로 seek 한 프레임, 이미지는 원본
 *      Author   : Joseph Kim <josephkim@mz.co.kr>
 *      Date     : 2026-05-11
 *      Branch   : feature/ai-mig-poc-web
 *      Usage    : <MediaThumbnail src={playbackUrl} mediaType="video" segmentStart={12.0} alt="..." />
 *      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
 *
 *      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
 *      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
 * ============================================================================================================================== */
"use client";

import { useEffect, useRef, useState } from "react";

import type { MediaType } from "@/lib/types";

interface MediaThumbnailProps {
  src: string;
  mediaType: MediaType;
  segmentStart: number;
  alt: string;
}

export function MediaThumbnail({ src, mediaType, segmentStart, alt }: MediaThumbnailProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (mediaType !== "video") return;
    const v = videoRef.current;
    if (!v) return;

    const handleLoadedMetadata = () => {
      // Browsers render the frame at the seeked time even when paused.
      v.currentTime = Math.max(0, segmentStart);
    };
    const handleSeeked = () => setReady(true);

    v.addEventListener("loadedmetadata", handleLoadedMetadata);
    v.addEventListener("seeked", handleSeeked);
    return () => {
      v.removeEventListener("loadedmetadata", handleLoadedMetadata);
      v.removeEventListener("seeked", handleSeeked);
    };
  }, [mediaType, segmentStart, src]);

  if (mediaType === "image") {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={alt}
        loading="lazy"
        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
      />
    );
  }

  return (
    <>
      {!ready && <div className="absolute inset-0 animate-pulse bg-muted" aria-hidden />}
      <video
        ref={videoRef}
        src={src}
        muted
        playsInline
        preload="metadata"
        aria-label={alt}
        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
      />
    </>
  );
}
