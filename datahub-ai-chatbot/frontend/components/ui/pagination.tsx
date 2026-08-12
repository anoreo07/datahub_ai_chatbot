"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PaginationProps {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
  showTotal?: boolean;
  total?: number;
}

export function Pagination({ page, pageCount, onPageChange, showTotal, total }: PaginationProps) {
  if (pageCount <= 1) return null;
  return (
    <div className="flex items-center justify-between border-t pt-3">
      <Button
        variant="ghost"
        size="sm"
        disabled={page === 0}
        onClick={() => onPageChange(page - 1)}
      >
        <ChevronLeft /> Trước
      </Button>
      <span className="text-sm text-muted-foreground">
        {showTotal && total != null ? `${total} mục · ` : ""}
        {page + 1} / {pageCount}
      </span>
      <Button
        variant="ghost"
        size="sm"
        disabled={page >= pageCount - 1}
        onClick={() => onPageChange(page + 1)}
      >
        Sau <ChevronRight />
      </Button>
    </div>
  );
}