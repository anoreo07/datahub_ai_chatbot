"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export interface NavItem {
  label: string;
  href?: string;
  icon: LucideIcon;
  onClick?: () => void;
  soon?: boolean;
  external?: boolean;
}

interface NavigationMenuProps {
  items: NavItem[];
  collapsed: boolean;
  className?: string;
}

export function NavigationMenu({ items, collapsed, className }: NavigationMenuProps) {
  const pathname = usePathname();

  return (
    <nav className={cn("flex flex-col gap-0.5 px-2", className)} aria-label="Điều hướng">
      {items.map((item) => {
        const active = item.href ? pathname.startsWith(item.href) : false;
        const content = (
          <>
            <item.icon
              className={cn(
                "h-4 w-4 shrink-0 transition-colors",
                active ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
              )}
            />
            <span className="flex-1 text-left text-sm font-medium transition-colors">
              {item.label}
            </span>
            {item.soon && (
              <span className="rounded-full bg-secondary px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                soon
              </span>
            )}
          </>
        );
        const cls = cn(
          "group flex w-full items-center gap-3 rounded-lg px-3 py-2 transition-colors",
          active
            ? "bg-primary/10 text-foreground"
            : "text-muted-foreground hover:bg-accent hover:text-foreground",
          collapsed && "justify-center px-2",
          item.soon && "cursor-not-allowed opacity-60 hover:bg-transparent"
        );

        const inner = item.href ? (
          item.external ? (
            <a
              key={item.label}
              href={item.href}
              target="_blank"
              rel="noreferrer"
              className={cls}
            >
              {content}
            </a>
          ) : (
            <Link
              key={item.label}
              href={item.href}
              className={cls}
              aria-current={active ? "page" : undefined}
            >
              {content}
            </Link>
          )
        ) : (
          <button
            key={item.label}
            className={cls}
            onClick={item.onClick}
            disabled={item.soon}
            aria-label={collapsed ? item.label : undefined}
          >
            {content}
          </button>
        );

        if (!collapsed) return inner;
        return (
          <Tooltip key={item.label}>
            <TooltipTrigger asChild>{inner}</TooltipTrigger>
            <TooltipContent side="right">{item.label}</TooltipContent>
          </Tooltip>
        );
      })}
    </nav>
  );
}