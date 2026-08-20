"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { AppLayout } from "@/components/layout/app-layout";
import { useApp } from "@/lib/app-store";

const TITLES: Record<string, string> = {
  "/chat": "Chat",
  "/search": "Search Metadata",
  "/storage": "Storage",
  "/glossary": "Glossary Terms",
  "/entities": "Browse Entities",
  "/admin": "Administration",
  "/status": "System Status",
  "/profile": "Profile",
};

const ADMIN_ROUTES = ["/glossary", "/entities", "/admin", "/status"];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loadingUser } = useApp();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loadingUser && !user) {
      router.replace("/login");
      return;
    }
    if (
      user &&
      !user.is_admin &&
      ADMIN_ROUTES.some((r) => pathname === r || pathname.startsWith(`${r}/`))
    ) {
      router.replace("/chat");
    }
  }, [loadingUser, user, router, pathname]);

  if (loadingUser) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    );
  }

  if (!user) return null;

  const title = TITLES[pathname] || "V-DataAtlas";
  return <AppLayout title={title}>{children}</AppLayout>;
}