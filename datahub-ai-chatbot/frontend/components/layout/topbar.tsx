"use client";

import { Menu, Bell, LogOut, User, ArrowLeft } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { useApp } from "@/lib/app-store";

const ADMIN_ROUTES = ["/glossary", "/entities", "/admin", "/status", "/search", "/profile"];

export function Topbar({ title }: { title?: string }) {
  const { user, logout, setMobileSidebarOpen } = useApp();
  const router = useRouter();
  const pathname = usePathname();
  const displayName = user?.display_name || user?.username || "Anonymous";
  const initials = displayName
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const showBack = ADMIN_ROUTES.includes(pathname) || ADMIN_ROUTES.some((r) => pathname.startsWith(`${r}/`));

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 bg-background px-4">
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={() => setMobileSidebarOpen(true)}
        aria-label="Mở menu"
      >
        <Menu className="h-5 w-5" />
      </Button>

      {showBack && (
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.back()}
          aria-label="Trở về"
          title="Trở về"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
      )}

      <h1 className="min-w-0 truncate text-sm font-semibold sm:text-base">{title ?? "DataAtlas"}</h1>

      <div className="flex-1" />

      <ThemeSwitcher />

      <Button variant="ghost" size="icon" aria-label="Thông báo" className="relative">
        <Bell className="h-4 w-4" />
        <Badge variant="warning" className="absolute right-1 top-1 h-2 w-2 rounded-full p-0" />
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Menu người dùng"
          >
            <Avatar className="h-8 w-8">
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel>
            <span className="block text-sm font-medium">{displayName}</span>
            <span className="block text-xs text-muted-foreground">
              {user?.is_admin ? "Administrator" : "Data Engineer"}
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => router.push("/profile")}>
            <User className="h-4 w-4" /> Hồ sơ
          </DropdownMenuItem>
          <DropdownMenuItem
            className="text-destructive focus:text-destructive"
            onClick={() => {
              logout();
              router.push("/login");
            }}
          >
            <LogOut className="h-4 w-4" /> Đăng xuất
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}