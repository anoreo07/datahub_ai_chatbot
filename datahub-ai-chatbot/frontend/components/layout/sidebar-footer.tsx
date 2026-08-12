"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { useApp } from "@/lib/app-store";
import { getRoleAvatar } from "@/lib/avatar";

interface SidebarFooterProps {
  collapsed: boolean;
}

export function SidebarFooter({ collapsed }: SidebarFooterProps) {
  const { user } = useApp();
  const avatar = getRoleAvatar(user);
  const displayName = user?.display_name || user?.username || "Anonymous";
  const initials = displayName
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="border-t p-2">
      <Link
        href="/profile"
        className={cn(
          "group flex items-center gap-3 rounded-lg p-2 transition-colors hover:bg-accent",
          collapsed && "justify-center"
        )}
        aria-label="Hồ sơ người dùng"
      >
        <Avatar className="h-8 w-8 shrink-0">
          {avatar && <AvatarImage src={avatar} alt={displayName} />}
          <AvatarFallback>{initials}</AvatarFallback>
        </Avatar>
        {!collapsed && (
          <>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium">{displayName}</span>
              <span className="block truncate text-xs text-muted-foreground">
                {user?.is_admin ? "Administrator" : "Data Engineer"}
              </span>
            </span>
            <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </>
        )}
      </Link>
    </div>
  );
}