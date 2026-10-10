import type { Metadata } from "next";
import Link from "next/link";

import RegionalMarketMap from "./regional-market-map";

export const metadata: Metadata = {
  title: "지역별 부동산 거래 동향 자료 | 모두의국감",
  description: "한국부동산원과 국토교통부 공식 출처를 구분해 지역별 거래통계의 검증 및 연결 현황을 살펴봅니다.",
};

export default function MarketPage() {
  return (
    <div className="site-page market-page">
      <header className="market-page-heading">
        <p className="domain-label">공공데이터 · 지역별 시장 동향</p>
        <h1>지역별 부동산 거래 동향</h1>
        <p className="lede">
          공직자 신고재산과 혼동하지 않고 지역별 부동산 시장의 공식
          통계 자료를 별도로 살펴봅니다.
        </p>
        <p className="market-page-notice">
          현재 CVIC에는 검증되어 공개 승인된 지역별 거래통계가 연결되지 않아,
          지도에 거래 건수나 가격을 표시하지 않습니다. 거래가 없다는 뜻은 아닙니다.
        </p>
      </header>

      <RegionalMarketMap />

      <section className="market-source-method" aria-labelledby="market-source-heading">
        <h2 id="market-source-heading">통계와 재산공개를 구분하는 이유</h2>
        <p>
          한국부동산원 R-ONE은 신고일 기준 공식 거래통계를,
          국토교통부는 계약월·지역코드에 따른 실거래 신고 원자료를 제공합니다.
          두 자료는 집계 기준과 지역코드 체계가 다르므로 직접 합산하거나
          같은 수치라고 단정할 수 없습니다.
        </p>
        <p>
          국회의원과 고위공직자가 신고한 재산총액도 시장 거래통계와 별도입니다.
          시장에 신고된 거래를 특정 인물의 매수·매도·소유 부동산으로 연결하지 않습니다.
        </p>
        <ul className="market-source-links">
          <li>
            <a href="https://www.reb.or.kr/r-one/portal/openapi/openApiDevPage.do" target="_blank" rel="noopener noreferrer">
              한국부동산원 R-ONE 공식 통계 API
            </a>
          </li>
          <li>
            <a href="https://www.data.go.kr/data/15126469/openapi.do" target="_blank" rel="noopener noreferrer">
              국토교통부 아파트 매매 실거래가
            </a>
          </li>
          <li>
            <a href="https://www.data.go.kr/data/15126466/openapi.do" target="_blank" rel="noopener noreferrer">
              국토교통부 토지 매매 실거래가
            </a>
          </li>
        </ul>
        <p><Link href="/people">공직자 공적 기록으로 돌아가기</Link></p>
      </section>
    </div>
  );
}
