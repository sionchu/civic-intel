"use client";

import { useState } from "react";

import { PROVINCE_SHAPES } from "./province-shapes";

type MarketScope = "housing" | "land";

// Visual labels only; never used as a statistical namespace crosswalk.
const HISTORICAL_NAME_LABELS: Readonly<Record<string, string>> = {
  "강원도": "강원특별자치도 (2020년 경계)",
  "전라북도": "전북특별자치도 (2020년 경계)",
};
const displayProvince = (name: string) => HISTORICAL_NAME_LABELS[name] ?? name;

const MARKET_SOURCES = {
  housing: {
    label: "주택 거래",
    sourceLabel: "한국부동산원 부동산거래현황",
    url: "https://www.data.go.kr/data/15068453/fileData.do",
    basis: "신고일 기준 공식 통계 · 시도별 수치 미연결",
    note: "주택 유형 전체를 포함합니다. 아파트 전용 통계나 개별 매매가격으로 해석할 수 없습니다.",
  },
  land: {
    label: "토지 매매",
    sourceLabel: "한국부동산원 토지매매 거래현황",
    url: "https://www.data.go.kr/data/15067925/fileData.do",
    basis: "신고일 기준 공식 통계 · 시도별 수치 미연결",
    note: "토지와 건축물이 함께 거래된 자료의 범위도 포함됩니다. 순수토지 거래만의 통계가 아닙니다.",
  },
} as const;

export default function RegionalMarketMap() {
  const [province, setProvince] = useState<string>("서울특별시");
  const [scope, setScope] = useState<MarketScope>("housing");
  const source = MARKET_SOURCES[scope];

  return (
    <section className="market-explorer" aria-labelledby="market-explorer-heading">
      <div className="market-explorer-controls">
        <div>
          <h2 id="market-explorer-heading">시·도 선택</h2>
          <p>지도를 누르거나 선택 상자를 사용해 지역을 확인하세요.</p>
        </div>
        <div className="market-explorer-fields">
          <label htmlFor="market-region-select">
            지역
            <select id="market-region-select" value={province} onChange={(event) => setProvince(event.target.value)}>
              {PROVINCE_SHAPES.map((shape) => (
                <option key={shape.id} value={shape.id}>{displayProvince(shape.id)}</option>
              ))}
            </select>
          </label>
          <fieldset>
            <legend>통계 종류</legend>
            {(["housing", "land"] as const).map((kind) => (
              <label key={kind}>
                <input type="radio" name="market-kind" value={kind} checked={scope === kind} onChange={() => setScope(kind)} />
                {MARKET_SOURCES[kind].label}
              </label>
            ))}
          </fieldset>
        </div>
      </div>

      <div className="market-explorer-grid">
        <div className="market-outline">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 759" aria-hidden="true" focusable="false">
            <g>
              {PROVINCE_SHAPES.map((shape) => (
                <path
                  key={shape.id}
                  d={shape.path}
                  fillRule={shape.fillRule}
                  className={shape.id === province ? "market-region-shape selected" : "market-region-shape"}
                  onClick={() => setProvince(shape.id)}
                >
                  <title>{displayProvince(shape.id)}</title>
                </path>
              ))}
            </g>
          </svg>
          <p className="market-boundary-note">
            경계 도형: StatGarten/SGIS 기반 2020년 참고자료. 현재 행정구역 및
            R-ONE 통계 지역코드와 연결된 지도가 아닙니다.
          </p>
        </div>

        <aside className="market-explorer-detail" aria-label="선택한 지역의 거래 자료 상태">
          <span className="market-section-kicker">지역별 거래 동향 · 자료 준비 단계</span>
          <h3 aria-live="polite">{displayProvince(province)}</h3>
          <p className="market-data-unavailable">공식 거래 수치 미게시</p>
          <p>이 지역의 {source.label} 수치는 현재 CVIC에 검증된 형태로 연결되어 있지 않습니다. 0건이나 거래 없음이라는 뜻이 아닙니다.</p>
          <dl>
            <div><dt>통계 기준</dt><dd>{source.basis}</dd></div>
            <div><dt>자료 출처</dt><dd>{source.sourceLabel}</dd></div>
            <div><dt>현황</dt><dd>공식 통계 자료·지역코드 대조 검증 전</dd></div>
          </dl>
          <p className="market-context-note">{source.note}</p>
          <p>
            <a href={source.url} target="_blank" rel="noopener noreferrer">
              제공기관의 공식 자료 확인 <span aria-hidden="true">↗</span>
            </a>
          </p>
        </aside>
      </div>
    </section>
  );
}
