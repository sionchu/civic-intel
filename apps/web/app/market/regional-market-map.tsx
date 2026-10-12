"use client";

import { useState } from "react";

import { PROVINCE_SHAPES } from "./province-shapes";

type MarketScope = "housing" | "apartment" | "land";

// Shapes and labels are navigation only. Do not join a R-ONE CLS_ID to a polygon.
const displayProvince = (name: string) => name;

const MARKET_SOURCES = {
  housing: {
    label: "주택 거래",
    sourceLabel: "한국부동산원 주택거래현황",
    url: "https://www.reb.or.kr/r-one/portal/stat/easyStatPage/A_2024_00546.do",
    basis: "신고일 기준 공식 통계 · 지역별 수치 미연결",
    note: "주택 유형 전체를 포함합니다. 아파트 전용 통계나 개별 매매가격으로 해석할 수 없습니다.",
  },
  apartment: {
    label: "아파트 매매",
    sourceLabel: "한국부동산원 아파트매매거래현황",
    url: "https://www.reb.or.kr/r-one/portal/stat/easyStatPage/A_2024_00554.do",
    basis: "신고일 기준 공식 통계 · 지역별 수치 미연결",
    note: "아파트 매매 호수(호)를 나타내는 통계이며 개별 거래가격이 아닙니다.",
  },
  land: {
    label: "토지 매매",
    sourceLabel: "한국부동산원 토지매매거래현황",
    url: "https://www.reb.or.kr/r-one/portal/stat/easyStatPage/A_2024_00536.do",
    basis: "신고일 기준 공식 통계 · 지역별 수치 미연결",
    note: "토지 매매 필지수(필지)를 나타내는 통계이며 개별 매매가격이 아닙니다.",
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
            {(["housing", "apartment", "land"] as const).map((kind) => (
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
            행정구역 경계: 2026년 7월 1일 기준 16개 시·도. 통계청 SGIS 기반
            가공자료(CC BY 4.0). R-ONE 통계의 기간별 분류코드와 자동으로 연결하지 않습니다.
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
