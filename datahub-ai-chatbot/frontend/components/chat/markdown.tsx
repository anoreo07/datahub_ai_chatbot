"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { Check, Copy } from "lucide-react";

interface MarkdownProps {
  content: string;
}

function sanitizeUrnMarkdown(text: string): string {
  if (!text) return text;
  // Restore any Liechtenstein flag emoji (🇱🇮 or unicode \uD83C\uDDF1\uD83C\uDDEE)
  // that may have been converted from :li: in DataHub URNs
  let sanitized = text.replace(/urn(?::)?\s*(?:🇱🇮|\uD83C\uDDF1\uD83C\uDDEE)\s*(?::)?/gi, "urn:li:");
  sanitized = sanitized.replace(/(?:🇱🇮|\uD83C\uDDF1\uD83C\uDDEE)/g, (match, offset, str) => {
    const before = str.slice(Math.max(0, offset - 10), offset);
    if (/urn:?$/i.test(before) || /urn:li:[^ \n]*$/i.test(before)) {
      return ":li:";
    }
    return match;
  });
  return sanitized;
}

function CodeBlock({ children }: { children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);
  const text = String(children ?? "").replace(/\n$/, "");
  return (
    <div className="relative group/code">
      <button
        className="absolute right-2 top-2 rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-white/10 hover:text-white focus:opacity-100 group-hover/code:opacity-100"
        onClick={() => {
          navigator.clipboard?.writeText(text).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          });
        }}
        aria-label="Sao chép code"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
      <pre className="!mt-2">{children}</pre>
    </div>
  );
}

export function Markdown({ content }: MarkdownProps) {
  const sanitizedContent = sanitizeUrnMarkdown(content);

  return (
    <div className="markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const text = String(children ?? "");
            const isBlock = Boolean(match) || text.includes("\n");
            if (isBlock) {
              return (
                <CodeBlock>
                  <code className={className} {...props}>
                    {children}
                  </code>
                </CodeBlock>
              );
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          a({ children, href }) {
            return (
              <a href={href} target="_blank" rel="noopener noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  );
}