/* ==============================================================================================================================
 *      File     : web/lib/types.ts
 *      Project  : MZCMST AI Migration PoC
 *      Description: 데모 페이지와 /search API 간 데이터 계약 — Request/Response/Result 타입 정의
 *      Author   : Joseph Kim <josephkim@mz.co.kr>
 *      Date     : 2026-05-11
 *      Branch   : feature/ai-mig-poc-web
 *      Usage    : import { SearchRequest, SearchResponse, SearchResult } from "@/lib/types"
 *      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
 *
 *      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
 *      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
 * ============================================================================================================================== */

export type MediaType = "video" | "image";

export interface SearchRequest {
  query: string;
  topK?: number;
}

export interface SearchResult {
  key: string;
  file_path: string;
  media_type: MediaType;
  segment_start: number;
  segment_end: number;
  duration_sec?: number;
  resolution?: string;
  score: number;
  thumbnail_url: string;
  playback_url: string;
}

export interface SearchResponse {
  query: string;
  took_ms: number;
  results: SearchResult[];
}

export interface SearchError {
  code: string;
  message: string;
}
