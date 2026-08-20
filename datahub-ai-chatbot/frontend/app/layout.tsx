import type { Metadata } from "next";
import { Geist_Mono, Inter, Russo_One } from "next/font/google";

import { AppProviders } from "@/components/providers/app-providers";
import { InlineScript } from "@/components/theme/inline-script";
import { STORAGE_KEY, THEMES } from "@/components/theme/theme-constants";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const russoOne = Russo_One({
  variable: "--font-russo-one",
  subsets: ["latin"],
  weight: "400",
});

export const metadata: Metadata = {
  title: {
    default: "V-DataAtlas",
    template: "%s · V-DataAtlas",
  },
  description:
    "AI Metadata Assistant cho DataHub — tra cứu datasets, glossary, owners, lineage và tạo SQL từ metadata.",
  icons: {
    icon: "/favicon.png",
  },
};

const FOUC_SCRIPT = `(function(){try{var t=localStorage.getItem(${JSON.stringify(
  STORAGE_KEY
)});if(t&&${JSON.stringify(THEMES)}.indexOf(t)!==-1){document.documentElement.setAttribute("data-theme",t)}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={`${inter.variable} ${geistMono.variable} ${russoOne.variable} h-full antialiased`}
    >
      <head>
        <InlineScript html={FOUC_SCRIPT} />
      </head>
      <body className="min-h-screen bg-background font-sans text-foreground">
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}