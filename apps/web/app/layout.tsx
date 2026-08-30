import type { Metadata } from "next";
import Link from "next/link";
import "./styles.css";

export const metadata: Metadata = { title: "Civic Intel", description: "Evidence-grounded public-official intelligence" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><header><Link href="/">Civic Intel</Link><span>Evidence first</span></header><main>{children}</main><footer>V0 · Every published fact is source-traceable.</footer></body></html>;
}
