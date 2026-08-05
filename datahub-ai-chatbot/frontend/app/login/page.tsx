"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { Loader2, Database } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { useApp } from "@/lib/app-store";

const DEMO_ACCOUNTS = [
  { user: "admin", pass: "admin123", label: "Admin" },
  { user: "finance", pass: "finance123", label: "Finance" },
  { user: "logistics", pass: "logistics123", label: "Logistics" },
];

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
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4">
      <div className="absolute right-4 top-4">
        <ThemeSwitcher />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="w-full max-w-sm"
      >
        <div className="rounded-2xl border bg-card p-8 shadow-xl">
          <div className="mb-6 flex flex-col items-center text-center">
            <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/15 text-primary">
              <Database className="h-6 w-6" />
            </div>
            <h1 className="text-xl font-semibold tracking-tight">DataAtlas</h1>
            <p className="mt-1 text-sm text-muted-foreground">AI Metadata Assistant cho DataHub</p>
          </div>

          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                onKeyDown={(e) => e.key === "Enter" && submit()}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                onKeyDown={(e) => e.key === "Enter" && submit()}
              />
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <Button className="w-full" onClick={() => submit()} disabled={loading}>
              {loading && <Loader2 className="animate-spin" />}
              Đăng nhập
            </Button>
          </div>

          <div className="mt-6 rounded-xl border bg-muted/40 p-3">
            <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              Tài khoản demo
            </p>
            <div className="flex flex-wrap gap-1.5">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.user}
                  className="rounded-full border bg-background px-2.5 py-1 text-xs transition-colors hover:bg-accent"
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
    </div>
  );
}