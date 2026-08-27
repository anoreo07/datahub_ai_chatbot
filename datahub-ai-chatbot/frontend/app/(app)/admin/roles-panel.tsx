"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2, Plus, Shield, Trash2, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type Role = {
  id: number;
  name: string;
  description?: string | null;
  is_admin: boolean;
  group_names: string[];
  domains: string[];
  user_count: number;
};

type User = {
  id: number;
  user_id: string;
  username: string;
  email: string;
  display_name: string;
  is_active: boolean;
  is_admin: boolean;
  role_ids: number[];
};

const EMPTY_ROLE = {
  name: "",
  description: "",
  is_admin: false,
  group_names: "",
  domains: [] as string[],
};

export function RolesPanel() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [domains, setDomains] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [r, u, d] = await Promise.all([
        apiFetch<Role[]>("/api/v1/admin/roles"),
        apiFetch<User[]>("/api/v1/admin/users"),
        apiFetch<string[]>("/api/v1/admin/domains"),
      ]);
      setRoles(r);
      setUsers(u);
      setDomains(d);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground p-4">
        <Loader2 className="animate-spin h-4 w-4" /> Đang tải roles &amp; permissions...
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col md:flex-row gap-6 overflow-hidden">
      {error && (
        <div className="absolute top-4 right-4 bg-destructive/15 border border-destructive/20 text-destructive text-xs rounded-lg p-3 z-50 shadow-sm max-w-sm">
          {error}
        </div>
      )}

      {/* Left Column: Create Form & User Assignment */}
      <div className="w-full md:w-[380px] shrink-0 flex flex-col gap-6 overflow-y-auto pr-1 min-h-0">
        <CreateRoleForm domains={domains} onCreated={refresh} />
        <UsersSection roles={roles} users={users} onChanged={refresh} />
      </div>

      {/* Right Column: Roles Grid with Scroll Container */}
      <Card className="flex-1 flex flex-col overflow-hidden h-full">
        <CardHeader className="pb-3 border-b flex flex-row items-center justify-between space-y-0 shrink-0">
          <CardTitle className="text-base font-semibold flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" /> Configured Roles
          </CardTitle>
          <Badge variant="secondary" className="font-mono text-xs">{roles.length} roles</Badge>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto p-4 min-h-0 bg-muted/5">
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 pb-4">
            {roles.map((role) => (
              <RoleCard
                key={role.id}
                role={role}
                domains={domains}
                onChanged={refresh}
              />
            ))}
            {roles.length === 0 && (
              <div className="col-span-full py-16 text-center text-sm text-muted-foreground">
                No roles configured. Create a role from the left panel to begin.
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function CreateRoleForm({
  domains,
  onCreated,
}: {
  domains: string[];
  onCreated: () => void;
}) {
  const [form, setForm] = useState({ ...EMPTY_ROLE });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const create = async () => {
    if (!form.name.trim()) return;
    setBusy(true);
    setMsg("");
    try {
      await apiFetch("/api/v1/admin/roles", {
        method: "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description || null,
          is_admin: form.is_admin,
          group_names: form.group_names
            .split(",")
            .map((g) => g.trim())
            .filter(Boolean),
          domains: form.domains,
        }),
      });
      setForm({ ...EMPTY_ROLE });
      setMsg("Đã tạo role.");
      onCreated();
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="shrink-0">
      <CardHeader className="pb-3 border-b">
        <CardTitle className="text-sm font-semibold flex items-center gap-1.5">
          <Plus className="h-4 w-4 text-primary" /> Create New Role
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 pt-3">
        <div className="space-y-1.5">
          <Label className="text-xs">Role Name</Label>
          <Input
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="e.g. Finance Admin"
            className="h-8.5 text-xs"
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Group Fallbacks (comma separated)</Label>
          <Input
            value={form.group_names}
            onChange={(e) => setForm({ ...form, group_names: e.target.value })}
            placeholder="finance-team, analytics-grp"
            className="h-8.5 text-xs"
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Description</Label>
          <Textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={2}
            className="text-xs p-2 min-h-[50px] resize-none"
          />
        </div>
        <DomainCheckboxes
          domains={domains}
          selected={form.domains}
          onToggle={(d) =>
            setForm({
              ...form,
              domains: form.domains.includes(d)
                ? form.domains.filter((x) => x !== d)
                : [...form.domains, d],
            })
          }
        />
        <div className="flex items-center justify-between pt-2 border-t mt-2">
          <label className="flex items-center gap-1.5 text-xs cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.is_admin}
              onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
              className="h-3.5 w-3.5 rounded border-gray-300 text-primary focus:ring-primary"
            />
            <span>All Domains (Admin)</span>
          </label>
          <Button onClick={create} disabled={busy || !form.name.trim()} size="sm" className="h-8">
            {busy && <Loader2 className="mr-1 h-3 w-3 animate-spin" />} Create
          </Button>
        </div>
        {msg && <p className="text-[11px] text-muted-foreground mt-1 bg-muted p-1.5 rounded text-center">{msg}</p>}
      </CardContent>
    </Card>
  );
}

function RoleCard({
  role,
  domains,
  onChanged,
}: {
  role: Role;
  domains: string[];
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    name: role.name,
    description: role.description || "",
    is_admin: role.is_admin,
    group_names: (role.group_names || []).join(", "),
    domains: role.domains,
  });
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await apiFetch(`/api/v1/admin/roles/${role.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: form.name.trim(),
          description: form.description || null,
          is_admin: form.is_admin,
          group_names: form.group_names
            .split(",")
            .map((g) => g.trim())
            .filter(Boolean),
        }),
      });
      await apiFetch(`/api/v1/admin/roles/${role.id}/domains`, {
        method: "PUT",
        body: JSON.stringify({ domains: form.domains }),
      });
      setEditing(false);
      onChanged();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!confirm(`Xóa role "${role.name}"?`)) return;
    try {
      await apiFetch(`/api/v1/admin/roles/${role.id}`, { method: "DELETE" });
      onChanged();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  return (
    <Card className="h-fit">
      <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
        <div className="min-w-0">
          <CardTitle className="text-sm font-semibold flex items-center gap-1.5 flex-wrap">
            <Shield className="h-4 w-4 text-primary shrink-0" />
            <span className="truncate">{role.name}</span>
            {role.is_admin && <Badge variant="success" className="text-[10px] py-0 px-1 font-normal">Admin</Badge>}
          </CardTitle>
          {role.description && (
            <p className="mt-1 text-xs text-muted-foreground leading-normal line-clamp-2">{role.description}</p>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0 ml-2">
          <Button variant="outline" size="sm" className="h-7 px-2 text-xs" onClick={() => setEditing(!editing)}>
            {editing ? "Hủy" : "Sửa"}
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 hover:bg-destructive/10 text-destructive" onClick={remove}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 pt-1">
        <div className="flex flex-wrap items-center gap-1">
          <Badge variant="secondary" className="text-[10px] py-0">{role.user_count} users</Badge>
          {role.domains.map((d) => (
            <Badge key={d} variant="outline" className="text-[10px] py-0 font-normal">
              {d}
            </Badge>
          ))}
          {role.domains.length === 0 && !role.is_admin && (
            <span className="text-[10px] text-muted-foreground italic">No domains assigned</span>
          )}
        </div>

        {editing && (
          <div className="space-y-3 rounded-lg border p-3 bg-muted/20 mt-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <div className="space-y-1">
                <Label className="text-[10px]">Tên role</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-[10px]">Groups</Label>
                <Input
                  value={form.group_names}
                  onChange={(e) => setForm({ ...form, group_names: e.target.value })}
                  className="h-8 text-xs"
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label className="text-[10px]">Mô tả</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                className="text-xs p-2 min-h-[40px] resize-none"
              />
            </div>
            <DomainCheckboxes
              domains={domains}
              selected={form.domains}
              onToggle={(d) =>
                setForm({
                  ...form,
                  domains: form.domains.includes(d)
                    ? form.domains.filter((x) => x !== d)
                    : [...form.domains, d],
                })
              }
            />
            <div className="flex items-center justify-between border-t pt-2 mt-2">
              <label className="flex items-center gap-1.5 text-xs cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_admin}
                  onChange={(e) =>
                    setForm({ ...form, is_admin: e.target.checked })
                  }
                  className="h-3.5 w-3.5 rounded border-gray-300"
                />
                <span className="text-[11px]">All Domains (Admin)</span>
              </label>
              <Button onClick={save} disabled={busy || !form.name.trim()} size="sm" className="h-7 text-xs">
                {busy && <Loader2 className="mr-1 h-3 w-3 animate-spin" />} Lưu
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function DomainCheckboxes({
  domains,
  selected,
  onToggle,
}: {
  domains: string[];
  selected: string[];
  onToggle: (domain: string) => void;
}) {
  if (domains.length === 0) {
    return (
      <p className="text-[10px] text-muted-foreground italic">
        Chưa có domain nào trong hệ thống.
      </p>
    );
  }
  return (
    <div className="space-y-1">
      <Label className="text-[10px] text-muted-foreground">Allowed Domains</Label>
      <div className="flex flex-wrap gap-1">
        {domains.map((d) => (
          <label
            key={d}
            className={cn(
              "flex cursor-pointer items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] select-none transition-all",
              selected.includes(d) ? "bg-primary/5 border-primary/30 text-primary font-medium" : "bg-background text-muted-foreground"
            )}
          >
            <input
              type="checkbox"
              checked={selected.includes(d)}
              onChange={() => onToggle(d)}
              className="h-3 w-3 rounded text-primary focus:ring-0"
            />
            {d}
          </label>
        ))}
      </div>
    </div>
  );
}

function UsersSection({
  roles,
  users,
  onChanged,
}: {
  roles: Role[];
  users: User[];
  onChanged: () => void;
}) {
  const [assignments, setAssignments] = useState<Record<string, number[]>>({});
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    const initial: Record<string, number[]> = {};
    for (const u of users) initial[u.user_id] = [...u.role_ids];
    setAssignments(initial);
  }, [users]);

  const save = async (userId: string) => {
    setBusy(userId);
    try {
      await apiFetch(`/api/v1/admin/users/${userId}/roles`, {
        method: "PUT",
        body: JSON.stringify({ role_ids: assignments[userId] || [] }),
      });
      onChanged();
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  const toggle = (userId: string, roleId: number) => {
    setAssignments((prev) => {
      const cur = prev[userId] || [];
      return {
        ...prev,
        [userId]: cur.includes(roleId)
          ? cur.filter((r) => r !== roleId)
          : [...cur, roleId],
      };
    });
  };

  return (
    <Card className="flex-1 flex flex-col overflow-hidden min-h-[300px]">
      <CardHeader className="pb-3 border-b shrink-0">
        <CardTitle className="text-sm font-semibold flex items-center gap-1.5">
          <Users className="h-4 w-4 text-primary" /> Assign Roles to Users
        </CardTitle>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0 bg-muted/5">
        {users.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-6">Chưa có người dùng.</p>
        )}
        {users.map((u) => (
          <div
            key={u.user_id}
            className="flex flex-col gap-2 rounded-lg border bg-background p-2.5 transition-all hover:shadow-sm"
          >
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="font-semibold text-xs text-foreground">
                    {u.display_name || u.username}
                  </span>
                  {u.is_admin && <Badge variant="success" className="text-[9px] py-0 px-1 font-normal">Admin</Badge>}
                </div>
                <span className="block text-[10px] text-muted-foreground font-mono truncate max-w-[200px]">
                  ID: {u.user_id}
                </span>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => save(u.user_id)}
                disabled={busy === u.user_id}
                className="h-7 text-xs px-2.5"
              >
                {busy === u.user_id && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
                Save
              </Button>
            </div>
            
            <div className="flex flex-wrap gap-x-3 gap-y-1 pt-1.5 border-t border-border/40">
              {roles.map((role) => (
                <label
                  key={role.id}
                  className="flex cursor-pointer items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground select-none"
                >
                  <input
                    type="checkbox"
                    checked={(assignments[u.user_id] || []).includes(role.id)}
                    onChange={() => toggle(u.user_id, role.id)}
                    className="h-3.5 w-3.5 rounded border-gray-300 focus:ring-0"
                  />
                  <span>{role.name}</span>
                </label>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}