"use client";

import { useState } from "react";
import Image from "next/image";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Loader2, Sparkles, User, Lock, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { useApp } from "@/lib/app-store";
import { cn } from "@/lib/utils";

const DEMO_ACCOUNTS = [
  { user: "admin", pass: "admin123", label: "Admin" },
  { user: "finance", pass: "finance123", label: "Finance" },
  { user: "logistics", pass: "logistics123", label: "Logistics" },
];

function IconInput({
  icon,
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  icon: React.ReactNode;
}) {
  return (
    <div className={cn("group relative", className)}>
      <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground/70 transition-colors group-focus-within:text-primary">
        {icon}
      </span>
      <input
        className={cn(
          "flex h-12 w-full rounded-xl border border-input bg-muted/40 pl-11 pr-4 text-[15px] shadow-sm outline-none transition-all",
          "placeholder:text-muted-foreground/70",
          "focus-visible:border-primary/60 focus-visible:bg-background focus-visible:ring-2 focus-visible:ring-primary/20",
          "disabled:cursor-not-allowed disabled:opacity-50"
        )}
        {...props}
      />
    </div>
  );
}

export default function LoginPage() {
  const { login } = useApp();
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (u = username, p = password) => {
    if (!u || !p) return;
    setLoading(true);
    setError("");
    try {
      await login(u, p);
      router.push("/chat");
    } catch (e) {
      setError((e as Error).message || "Đăng nhập thất bại");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-dvh flex-col bg-background lg:flex-row">
      <div className="absolute right-4 top-4 z-20">
        <ThemeSwitcher />
      </div>

      <div
        className="relative flex min-h-[40dvh] flex-1 items-center justify-center overflow-hidden border-b lg:min-h-0 lg:border-b-0 lg:h-dvh"
        style={{ backgroundColor: "#f5f5f6" }}
      >
        <Image
          src="/login_hero.png"
          alt="DataAtlas"
          fill
          priority
          sizes="(max-width: 1024px) 100vw, 50vw"
          className="object-contain"
        />
      </div>

      <div className="relative flex flex-1 items-center justify-center bg-background lg:h-dvh">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          className="w-full px-6 py-12 sm:px-10"
        >
          <div className="mx-auto flex w-full max-w-[520px] flex-col">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <Sparkles className="h-5 w-5" />
              </span>
              <div>
                <h1 className="text-[28px] font-semibold leading-tight tracking-tight">
                  DataAtlas
                </h1>
                <p className="text-sm font-medium text-muted-foreground">
                  AI Metadata Assistant for DataHub
                </p>
              </div>
            </div>

            <p className="mt-8 max-w-md text-[15px] leading-relaxed text-muted-foreground">
              Sign in to explore datasets, lineage, glossary, documentation, and
              metadata using natural language.
            </p>

            <div className="my-8 h-px w-full bg-border" />

            <form
              className="flex flex-col gap-5"
              onSubmit={(e) => {
                e.preventDefault();
                submit();
              }}
            >
              <div className="space-y-2">
                <Label htmlFor="username" className="text-sm font-medium">
                  Username
                </Label>
                <IconInput
                  id="username"
                  icon={<User className="h-[18px] w-[18px]" />}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  autoFocus
                  placeholder="e.g. admin"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium">
                  Password
                </Label>
                <IconInput
                  id="password"
                  icon={<Lock className="h-[18px] w-[18px]" />}
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="••••••••"
                />
              </div>

              {error && (
                <p className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                size="lg"
                className="h-12 w-full rounded-xl text-[15px] font-semibold transition-all hover:shadow-lg hover:shadow-primary/20 active:scale-[0.99]"
                disabled={loading}
              >
                {loading ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <>
                    Sign in
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </Button>
            </form>

            <div className="mt-8">
              <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                Quick Demo Access
              </p>
              <div className="flex flex-wrap items-center justify-center gap-2">
                {DEMO_ACCOUNTS.map((a) => (
                  <button
                    key={a.user}
                    type="button"
                    className="rounded-full border bg-background px-4 py-1.5 text-sm font-medium text-muted-foreground shadow-sm transition-all hover:border-primary/40 hover:bg-primary/5 hover:text-foreground active:scale-95"
                    onClick={() => {
                      setUsername(a.user);
                      setPassword(a.pass);
                    }}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        <p className="pointer-events-none absolute bottom-6 left-1/2 w-full -translate-x-1/2 px-6 text-center text-xs text-muted-foreground/70">
          Powered by DataHub • DataAtlas
        </p>
      </div>
    </div>
  );
}