"use client";

import { useTheme } from "@/components/theme/theme-provider";
import { Check, Moon, Sun, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

const THEMES = [
  { id: "light", label: "Light", icon: Sun },
  { id: "dark", label: "Dark", icon: Moon },
  { id: "tokyo", label: "Tokyo Night", icon: Sparkles },
] as const;

export function ThemeSwitcher() {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Đổi giao diện">
          {mounted && resolvedTheme === "dark" ? (
            <Moon className="h-4 w-4" />
          ) : mounted && resolvedTheme === "tokyo" ? (
            <Sparkles className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuLabel>Giao diện</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {THEMES.map((t) => {
          const Icon = t.icon;
          const active = mounted && resolvedTheme === t.id;
          return (
            <DropdownMenuItem
              key={t.id}
              className={cn("flex items-center justify-between", active && "font-medium")}
              onSelect={() => setTheme(t.id)}
            >
              <span className="flex items-center gap-2">
                <Icon className="h-4 w-4" />
                {t.label}
              </span>
              {active && <Check className="h-4 w-4 text-primary" />}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}