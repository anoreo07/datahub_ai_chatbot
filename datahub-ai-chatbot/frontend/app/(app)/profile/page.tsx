"use client";

import Link from "next/link";
import { Activity, BookOpen, LayoutGrid, ShieldCheck } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useApp } from "@/lib/app-store";
import { cn } from "@/lib/utils";
import { getRoleAvatar } from "@/lib/avatar";

const ADMIN_TOOLS = [
  {
    href: "/status",
    label: "System Status",
    desc: "Sức khỏe hệ thống, metrics và logs",
    icon: Activity,
  },
  {
    href: "/admin",
    label: "Administration",
    desc: "Sync, index và quản lý tài liệu",
    icon: ShieldCheck,
  },
  {
    href: "/entities",
    label: "Browse Entities",
    desc: "Danh sách datasets, dashboards và documents",
    icon: LayoutGrid,
  },
  {
    href: "/glossary",
    label: "Glossary Terms",
    desc: "Tra cứu thuật ngữ kinh doanh",
    icon: BookOpen,
  },
];

export default function ProfilePage() {
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
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-5 p-6">
        <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
          <Card>
            <CardContent className="flex flex-col items-center pt-8 text-center">
              <Avatar className="h-20 w-20">
                {avatar && <AvatarImage src={avatar} alt={displayName} />}
                <AvatarFallback className="text-2xl">{initials}</AvatarFallback>
              </Avatar>
              <h2 className="mt-4 text-xl font-semibold">{displayName}</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {user?.is_admin ? "Administrator" : "Data Engineer"}
              </p>
              <div className="mt-3 flex flex-wrap justify-center gap-1.5">
                {(user?.roles?.length ? user.roles : [user?.is_admin ? "admin" : "member"]).map((r) => (
                  <Badge key={r} variant="secondary">{r}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Thông tin tài khoản</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Username</span>
                <span className="font-medium">{user?.username}</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Tên hiển thị</span>
                <span className="font-medium">{user?.display_name || "—"}</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span className="text-muted-foreground">Quyền admin</span>
                <span className="font-medium">{user?.is_admin ? "Có" : "Không"}</span>
              </div>
              <div className="flex justify-between pb-1">
                <span className="text-muted-foreground">Tên đăng nhập</span>
                <span className="text-xs text-muted-foreground">{user?.username}</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {user?.is_admin && (
          <Card>
            <CardHeader>
              <CardTitle>Quản trị hệ thống</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {ADMIN_TOOLS.map((tool) => (
                <Link
                  key={tool.href}
                  href={tool.href}
                  className={cn(
                    "group flex items-start gap-3 rounded-lg border p-3 transition-colors",
                    "hover:border-primary/40 hover:bg-accent"
                  )}
                >
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <tool.icon className="h-4 w-4" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-medium">{tool.label}</span>
                    <span className="block text-xs text-muted-foreground">{tool.desc}</span>
                  </span>
                </Link>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}