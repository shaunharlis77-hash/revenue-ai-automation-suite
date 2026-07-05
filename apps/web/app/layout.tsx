import type { Metadata } from "next";
import Link from "next/link";

import { navigationItems } from "@/lib/navigation";
import "./globals.css";

export const metadata: Metadata = {
  title: "Revenue AI Automation Suite",
  description: "Internal sales operations dashboard foundation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="appShell">
          <aside className="sidebar" aria-label="Main navigation">
            <div className="brandBlock">
              <span className="brandMark">RA</span>
              <div>
                <p className="brandName">Revenue AI</p>
                <p className="brandSubtle">Sales Ops Suite</p>
              </div>
            </div>
            <nav className="navList">
              {navigationItems.map((item) => (
                <Link key={item.href} className="navLink" href={item.href}>
                  {item.label}
                </Link>
              ))}
            </nav>
          </aside>
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  );
}

