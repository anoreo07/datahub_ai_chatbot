import { Menu, Bell, LogOut, User, ArrowLeft, Clock } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";

import { cn } from "@/lib/utils";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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
import { getRoleAvatar } from "@/lib/avatar";
import { useNotificationStore } from "@/lib/notification-store";

const ADMIN_ROUTES = ["/glossary", "/entities", "/admin", "/status", "/search", "/profile"];

interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  status: "pending" | "running" | "success" | "failed";
  is_read: boolean;
  created_at: string;
  read_at: string | null;
  metadata: any;
}

interface NotificationState {
  notifications: Notification[];
  unreadCount: number;
  hasActiveJobs: boolean;
  activeJobs: Notification[];
  isPolling: boolean;
  pollInterval: NodeJS.Timeout | null;
}

export function Topbar({ title }: { title?: string }) {
  const { user, logout, setMobileSidebarOpen, showResponseTime, toggleShowResponseTime } = useApp();
  const router = useRouter();
  const pathname = usePathname();
  const avatar = getRoleAvatar(user);
  const displayName = user?.display_name || user?.username || "Anonymous";
  const initials = displayName
    .split(/\s+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const showBack = ADMIN_ROUTES.includes(pathname) || ADMIN_ROUTES.some((r) => pathname.startsWith(`${r}/`));
  const store = useNotificationStore();

  const unreadCount = store.unreadCount;
  const hasActiveJobs = store.hasActiveJobs;
  const notifications = store.notifications;
  const markAllRead = store.markAllRead;

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

      <h1 className="min-w-0 truncate text-sm font-semibold sm:text-base">{title ?? "V-DataAtlas"}</h1>

      <div className="flex-1" />

      <div className="flex items-center gap-1.5 sm:gap-2">
        <ThemeSwitcher />

        <button
          type="button"
          onClick={toggleShowResponseTime}
          aria-label="Toggle Response Time"
          title="Bật/Tắt hiển thị thời gian phản hồi"
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-all border shadow-sm",
            showResponseTime
              ? "border-primary/40 bg-primary/10 text-primary hover:bg-primary/20"
              : "border-border/60 bg-muted/50 text-muted-foreground hover:bg-muted"
          )}
        >
          <Clock className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Response Time</span>
          <span
            className={cn(
              "h-2 w-2 rounded-full shrink-0",
              showResponseTime ? "bg-primary animate-pulse" : "bg-muted-foreground/40"
            )}
          />
        </button>
      </div>



      <Button variant="ghost" size="icon" aria-label="Thông báo" className="relative">
        <Bell className="h-4 w-4" />
        <Badge
          variant="warning"
          className={cn("absolute right-1 top-1 h-2 w-2 rounded-full p-0", {
            hidden: unreadCount === 0,
          })}
        />
        {unreadCount > 0 && (
          <span className="absolute -bottom-1 -right-1 bg-primary text-primary-foreground text-xs rounded-pulse">
            {unreadCount}
          </span>
        )}
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="flex items-center gap-2 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Menu người dùng"
          >
            <Avatar className="h-8 w-8">
              {avatar && <AvatarImage src={avatar} alt={displayName} />}
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
            {hasActiveJobs && (
              <Badge variant="warning" className="ml-2 h-4 w-4 rounded-full p-0 animate-pulse">
                running
              </Badge>
            )}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-80">
          <DropdownMenuLabel>
            <span className="block text-sm font-medium">Thông báo</span>
            <span className="block text-xs text-muted-foreground">
              {unreadCount} chưa đọc
            </span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />

          {hasActiveJobs && (
            <div className="px-2 py-2 text-sm text-muted-foreground">
              🔵 Đang có task đang chạy
            </div>
          )}

          <ul className="space-y-1 px-2 max-h-80 overflow-y-auto text-sm">
            {notifications.length > 0 && (
              <li className="px-2 py-2">
                <div className="text-primary font-medium">{notifications[0]?.title}</div>
                <div className="text-xs text-muted-foreground">{notifications[0]?.message}</div>
              </li>
            )}
          </ul>

          {unreadCount > 0 && (
            <DropdownMenuItem onClick={markAllRead}>
              <span className="flex items-center gap-2">
                <i className="check-circle h-4 w-4" /> Mark all as read
              </span>
            </DropdownMenuItem>
          )}

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
