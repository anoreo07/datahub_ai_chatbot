"use client";

import Image from "next/image";
import Link from "next/link";
import { Search, PanelLeftClose, PanelLeftOpen } from "lucide-react";

import { Button } from "@/components/ui/button";

interface SidebarHeaderProps {
  collapsed: boolean;
  onToggle: () => void;
  onSearch: () => void;
}

export function SidebarHeader({ collapsed, onToggle, onSearch }: SidebarHeaderProps) {
  const toggleButton = (
    <Button
      variant="ghost"
      size="icon"
      onClick={onToggle}
      aria-label={collapsed ? "Mở rộng sidebar" : "Thu gọn sidebar"}
      className="shrink-0"
    >
      {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
    </Button>
  );

  const searchButton = (
    <Button
      variant="ghost"
      size="icon"
      onClick={onSearch}
      aria-label="Tìm kiếm cuộc trò chuyện"
      className="shrink-0"
    >
      <Search className="h-4 w-4" />
    </Button>
  );

  const searchDataHubButton = (
    <Button variant="ghost" size="icon" asChild aria-label="Search DataHub" className="shrink-0">
      <Link href="/search">
        <Search className="h-4 w-4" />
      </Link>
    </Button>
  );

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 border-b py-3">
        <Image
          src="/logo.png"
          alt="V-DataAtlas"
          width={40}
          height={40}
          className="h-10 w-10 shrink-0 rounded-lg object-contain"
        />
        <div className="flex flex-col items-center gap-1">
          {searchButton}
          {searchDataHubButton}
          {toggleButton}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3 border-b px-4 py-4">
      <div className="flex min-w-0 flex-1 items-center gap-2.5 overflow-hidden">
        <Image
          src="/logo.png"
          alt="V-DataAtlas"
          width={40}
          height={40}
          className="h-10 w-10 shrink-0 rounded-lg object-contain"
        />
        <span className="truncate font-display text-lg tracking-tight">V-DataAtlas</span>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        {searchButton}
        {toggleButton}
      </div>
    </div>
  );
}
