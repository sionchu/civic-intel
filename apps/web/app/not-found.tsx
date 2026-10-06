import Link from "next/link";

export default function NotFound() {
  return (
    <div className="site-page not-found-page">
      <h1>기록을 찾을 수 없습니다</h1>
      <p>이 주소에 해당하는, 공개 기준을 통과한 기록이 없습니다. 주소를 확인하거나 이름으로 다시 검색해 주세요.</p>
      <Link href="/people">인물 찾기로 돌아가기</Link>
    </div>
  );
}
