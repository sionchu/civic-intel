import Link from "next/link";

export default function NotFound() {
  return (
    <div className="site-page not-found-page">
      <h1>Profile not found</h1>
      <p>No resolved, publishable profile exists for this identifier.</p>
      <Link href="/people">Return to People</Link>
    </div>
  );
}
