"use client";

import { useState } from "react";

export default function ReviewedPortraitImage({ src, width, height, alt }: {
  src: string;
  width: number;
  height: number;
  alt: string;
}) {
  const [failed, setFailed] = useState(false);
  const style = { aspectRatio: `${width} / ${height}` };
  if (failed) {
    return <div className="profile-portrait-image profile-portrait-unavailable" style={style} role="img" aria-label="사진을 표시할 수 없습니다" />;
  }
  return (
    // The reviewed local file is shown at its original aspect ratio, without a transform.
    // eslint-disable-next-line @next/next/no-img-element
    <img className="profile-portrait-image" src={src} width={width} height={height} style={style} alt={alt} onError={() => setFailed(true)} />
  );
}
