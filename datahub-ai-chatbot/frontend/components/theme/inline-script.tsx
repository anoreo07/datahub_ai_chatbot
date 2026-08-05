// Prevent-flash-before-hydration inline script helper.
// Rendered as a Client Component so it re-evaluates during hydration and flips
// the type to "text/plain" (React ignores the script, no warning, no mismatch),
// while the server still emits type="text/javascript" so the browser runs it
// synchronously during HTML parsing.
"use client";

export function InlineScript({ html }: { html: string }) {
  return (
    <script
      type={typeof window === "undefined" ? "text/javascript" : "text/plain"}
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
