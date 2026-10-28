"use client";

import * as React from "react";
import { FileText, ShieldCheck, Clock, User, ArrowRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { adminApi, AdminActionLogItem } from "@/lib/api";

export default function AdminAuditLogsPage() {
  const { showToast } = useToast();

  const [logs, setLogs] = React.useState<AdminActionLogItem[]>([]);
  const [totalCount, setTotalCount] = React.useState(0);
  const [isLoading, setIsLoading] = React.useState(true);

  const loadLogs = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getAuditLogs(50, 0);
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setLogs(data.items);
      setTotalCount(data.total);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "--";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const getActionBadge = (action: string) => {
    if (action.includes("approved")) return <Badge variant="brand">{action}</Badge>;
    if (action.includes("rejected") || action.includes("suspended") || action.includes("cancelled")) {
      return <Badge variant="emergency">{action}</Badge>;
    }
    return <Badge variant="neutral">{action}</Badge>;
  };

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-white">Nhật Ký Thao Tác Quản Trị</h2>
          <p className="text-xs text-slate-400">Kiểm toán bất biến mọi can thiệp hệ thống (FR-ADM-01)</p>
        </div>

        <Button variant="secondary" size="default" onClick={loadLogs} isLoading={isLoading} className="text-xs">
          <RefreshCw className="w-3.5 h-3.5 mr-1" />
          <span>Làm mới</span>
        </Button>
      </div>

      {/* Logs Table / List */}
      {isLoading ? (
        <div className="py-16 text-center text-xs text-slate-400">Đang tải nhật ký kiểm toán...</div>
      ) : logs.length === 0 ? (
        <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl text-xs text-slate-400">
          Chưa có nhật ký thao tác nào được ghi nhận.
        </div>
      ) : (
        <div className="space-y-3">
          {logs.map((log) => (
            <Card key={log.id} className="bg-surface-card border-surface-border">
              <CardContent className="p-3.5 space-y-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {getActionBadge(log.action)}
                    {log.entity_type && (
                      <span className="text-[11px] font-mono text-slate-400">
                        [{log.entity_type}]
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(log.created_at)}
                  </span>
                </div>

                <div className="text-xs text-slate-300">
                  <span>Thực hiện bởi: </span>
                  <strong className="text-white">{log.admin_phone || log.admin_id.slice(0, 8)}</strong>
                  {log.entity_id && (
                    <span className="text-slate-400 ml-2">
                      (Đối tượng: #{log.entity_id.slice(0, 8)})
                    </span>
                  )}
                </div>

                {log.detail && Object.keys(log.detail).length > 0 && (
                  <pre className="p-2.5 bg-surface-elevated rounded-xl text-[11px] text-slate-300 font-mono overflow-x-auto">
                    {JSON.stringify(log.detail, null, 2)}
                  </pre>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

