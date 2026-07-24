/* ==============================================================================================================================
 *      File     : web/components/SearchBar.tsx
 *      Project  : MZCMST AI Migration PoC
 *      Description: 자연어 검색 입력창 + 예시 쿼리 칩 + Enter/버튼 핸들러
 *      Author   : Joseph Kim <josephkim@mz.co.kr>
 *      Date     : 2026-05-11
 *      Branch   : feature/ai-mig-poc-web
 *      Usage    : <SearchBar value={q} onChange={setQ} onSubmit={runSearch} disabled={loading} />
 *      Notes    : 문의 — Media Service Team(mzc_tm_mediaserv@megazone.com).
 *
 *      Copyright 2026. MEGAZONE CLOUD Corp. All rights reserved.
 *      This file is part of the Professional Offering Services of Megazone Cloud Media Services Team.
 * ============================================================================================================================== */
"use client";

import { useRef, type KeyboardEvent } from "react";

const EXAMPLE_QUERIES = [
  "비 오는 도시 야경",
  "스튜디오 인터뷰 장면",
  "야구 경기 홈런 순간",
  "해변 일몰",
  "강아지가 뛰어노는 장면",
] as const;

interface SearchBarProps {
  value: string;
  onChange: (next: string) => void;
  onSubmit: (query: string) => void;
  disabled?: boolean;
}

export function SearchBar({ value, onChange, onSubmit, disabled = false }: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  function submit(text: string) {
    const trimmed = text.trim();
    if (trimmed.length === 0 || disabled) return;
    onSubmit(trimmed);
  }

  function onKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      submit(value);
    }
  }

  function onChipClick(chipQuery: string) {
    onChange(chipQuery);
    inputRef.current?.focus();
    submit(chipQuery);
  }

  return (
    <div className="mx-auto w-full max-w-3xl">
      <div className="flex items-center gap-2 rounded-xl border border-border bg-card p-2 shadow-sm transition-shadow focus-within:ring-2 focus-within:ring-[var(--ring)]">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="예: 비 오는 도시 야경 / 인터뷰 중 웃는 장면"
          aria-label="검색 쿼리 입력"
          disabled={disabled}
          className="h-10 flex-1 bg-transparent px-3 text-base text-card-foreground placeholder:text-muted-foreground focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
        />
        <button
          type="button"
          onClick={() => submit(value)}
          disabled={disabled || value.trim().length === 0}
          className="h-10 rounded-lg bg-primary px-5 text-sm font-semibold text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label="검색 실행"
        >
          Search
        </button>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <span className="text-xs text-muted-foreground">예시 쿼리:</span>
        {EXAMPLE_QUERIES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => onChipClick(q)}
            disabled={disabled}
            className="rounded-full border border-border bg-muted/60 px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary hover:bg-card hover:text-card-foreground disabled:cursor-not-allowed disabled:opacity-50"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
