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

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="animate-spin" /> Đang tải roles &amp; permissions...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-destructive">{error}</p>}
      <CreateRoleForm domains={domains} onCreated={refresh} />
      <div className="grid gap-4 lg:grid-cols-2">
        {roles.map((role) => (
          <RoleCard
            key={role.id}
            role={role}
            domains={domains}
            onChanged={refresh}
          />
        ))}
      </div>
      <UsersSection roles={roles} users={users} onChanged={refresh} />
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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Plus className="h-4 w-4" /> Tạo role mới
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label>Tên role</Label>
            <Input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="VD: Tài chính"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Group fallback (phân cách bằng dấu phẩy)</Label>
            <Input
              value={form.group_names}
              onChange={(e) => setForm({ ...form, group_names: e.target.value })}
              placeholder="finance-team"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label>Mô tả</Label>
          <Textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            rows={2}
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
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_admin}
              onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
              className="h-4 w-4"
            />
            Truy cập mọi domain (admin)
          </label>
          <Button onClick={create} disabled={busy || !form.name.trim()}>
            {busy && <Loader2 className="animate-spin" />} Tạo role
          </Button>
        </div>
        {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
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
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-4 w-4" /> {role.name}
            {role.is_admin && <Badge variant="success">Admin</Badge>}
          </CardTitle>
          {role.description && (
            <p className="mt-1 text-sm text-muted-foreground">{role.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm" onClick={() => setEditing(!editing)}>
            {editing ? "Hủy" : "Sửa"}
          </Button>
          <Button variant="destructive" size="sm" onClick={remove}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="secondary">{role.user_count} người dùng</Badge>
          {role.domains.map((d) => (
            <Badge key={d} variant="outline">
              {d}
            </Badge>
          ))}
          {role.domains.length === 0 && (
            <span className="text-xs text-muted-foreground">Chưa có domain nào</span>
          )}
        </div>

        {editing && (
          <div className="space-y-3 rounded-lg border p-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Tên role</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Group</Label>
                <Input
                  value={form.group_names}
                  onChange={(e) => setForm({ ...form, group_names: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Mô tả</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
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
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_admin}
                  onChange={(e) =>
                    setForm({ ...form, is_admin: e.target.checked })
                  }
                  className="h-4 w-4"
                />
                Truy cập mọi domain (admin)
              </label>
              <Button onClick={save} disabled={busy || !form.name.trim()}>
                {busy && <Loader2 className="animate-spin" />} Lưu
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
      <p className="text-sm text-muted-foreground">
        Chưa có domain nào trong hệ thống.
      </p>
    );
  }
  return (
    <div>
      <Label>Domains được phép truy cập</Label>
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {domains.map((d) => (
          <label
            key={d}
            className="flex cursor-pointer items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs"
          >
            <input
              type="checkbox"
              checked={selected.includes(d)}
              onChange={() => onToggle(d)}
              className="h-3.5 w-3.5"
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
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="h-4 w-4" /> Gán role cho người dùng
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {users.length === 0 && (
          <p className="text-sm text-muted-foreground">Chưa có người dùng.</p>
        )}
        {users.map((u) => (
          <div
            key={u.user_id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border p-3"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium">
                  {u.display_name || u.username}
                </span>
                <span className="truncate text-xs text-muted-foreground">
                  {u.user_id}
                </span>
                {u.is_admin && <Badge variant="success">Admin</Badge>}
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1.5 pt-1.5">
                {roles.map((role) => (
                  <label
                    key={role.id}
                    className="flex cursor-pointer items-center gap-1.5 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={(assignments[u.user_id] || []).includes(role.id)}
                      onChange={() => toggle(u.user_id, role.id)}
                      className="h-4 w-4"
                    />
                    {role.name}
                  </label>
                ))}
              </div>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => save(u.user_id)}
              disabled={busy === u.user_id}
            >
              {busy === u.user_id && <Loader2 className="animate-spin" />}
              Lưu quyền
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}