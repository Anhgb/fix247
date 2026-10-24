"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  Wrench,
  Sparkles,
  PhoneCall,
  Clock,
  Info,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { diagnosisApi, DiagnosisData, CandidateResult } from "@/lib/api";

export default function DiagnosisResultPage() {
  const params = useParams();
  const router = useRouter();
  const { showToast } = useToast();
  const diagnosisId = params.id as string;

  const [diagnosis, setDiagnosis] = React.useState<DiagnosisData | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [feedbackSent, setFeedbackSent] = React.useState(false);

  React.useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      const { data, error } = await diagnosisApi.getDiagnosis(diagnosisId);
      setIsLoading(false);
      if (error) {
        showToast(error.message || "Không thể tải kết quả chẩn đoán.", "error");
        return;
      }
      if (data) {
        setDiagnosis(data);
      }
    }
    if (diagnosisId) {
      loadData();
    }
  }, [diagnosisId, showToast]);

  const handleFeedback = async (label: "correct" | "partial" | "wrong") => {
    const { error } = await diagnosisApi.submitFeedback(diagnosisId, label);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    setFeedbackSent(true);
    showToast("Cảm ơn bạn đã phản hồi độ chính xác của chẩn đoán!", "success");
  };

  const handleBookTechnician = () => {
    showToast("Đang kết nối thợ gần nhất theo kết quả chẩn đoán...", "info");
    // Navigate to order placement with diagnosis reference
    router.push(`/?diagnosis_id=${diagnosisId}&action=book`);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-4">
        <div className="w-12 h-12 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm font-semibold text-slate-300">Đang tải kết quả chẩn đoán...</p>
      </div>
    );
  }

  if (!diagnosis) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-emergency-500" />
        <h2 className="text-lg font-bold text-white">Không tìm thấy chẩn đoán</h2>
        <Link href="/diagnose">
          <Button variant="primary">Tạo Chẩn Đoán Mới</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-4 pb-16 space-y-5">
      {/* Top Bar */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-2">
          <Link
            href="/diagnose"
            className="p-2 min-h-[44px] min-w-[44px] rounded-xl bg-surface-card border border-surface-border text-slate-300 hover:text-white flex items-center justify-center"
            aria-label="Quay lại"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-1.5">
              <span>Kết Quả Chẩn Đoán</span>
              {diagnosis.is_cached && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-300">
                  Đã lưu cache
                </span>
              )}
            </h1>
            <p className="text-xs text-slate-400">
              Mã: {diagnosis.id.substring(0, 8)} • TP. Huế
            </p>
          </div>
        </div>

        <Link href="/diagnose">
          <Button variant="ghost" size="sm" className="text-xs gap-1">
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Làm lại</span>
          </Button>
        </Link>
      </div>

      {/* 1. SAFETY WARNINGS PROMINENTLY FIRST (FR-DIAG-04) */}
      {diagnosis.safety_warnings && diagnosis.safety_warnings.length > 0 && (
        <div className="p-4 bg-gradient-to-r from-emergency-950/90 to-red-950/60 border-2 border-emergency-600 rounded-2xl shadow-lg space-y-2">
          <div className="flex items-center gap-2 text-emergency-400 font-bold text-sm uppercase tracking-wide">
            <ShieldAlert className="w-5 h-5 animate-pulse shrink-0" />
            <span>Cảnh Báo An Toàn Khẩn Cấp (FR-DIAG-04)</span>
          </div>
          <ul className="space-y-1.5 text-sm text-emergency-100 pl-6 list-disc">
            {diagnosis.safety_warnings.map((warn, i) => (
              <li key={i} className="leading-snug font-medium">
                {warn}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Audio Beta Notice (FR-DIAG-06) */}
      {diagnosis.has_audio_beta && (
        <div className="p-2.5 bg-purple-950/30 border border-purple-500/40 rounded-xl flex items-center gap-2 text-xs text-purple-200">
          <Badge variant="brand" className="text-[10px] uppercase">
            Beta
          </Badge>
          <span>
            Tính năng nhận diện qua âm thanh đang thử nghiệm (Beta) – kết quả mang tính định hướng.
          </span>
        </div>
      )}

      {/* Graceful Fallback Notice if AI failed (AT-09) */}
      {diagnosis.can_book_without_diagnosis && (
        <Card className="border-brand-500/60 bg-brand-950/30">
          <CardContent className="p-4 space-y-2 text-center">
            <AlertTriangle className="w-8 h-8 text-brand-400 mx-auto" />
            <h3 className="font-bold text-white text-base">Hệ Thống AI Đang Bảo Trì</h3>
            <p className="text-sm text-slate-300">
              Bạn không cần chờ chẩn đoán AI mà vẫn có thể đặt thợ trực tiếp để khảo sát tận nơi.
            </p>
          </CardContent>
        </Card>
      )}

      {/* 2. TOP-3 CAUSES & PRICE MAPPING (SRS §7.2, FR-DIAG-05) */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <span>Khả Năng Xảy Ra Nhất</span>
            <Badge variant="neutral">Top {diagnosis.candidates.length}</Badge>
          </h2>
          <span className="text-xs text-slate-400">Giá chuẩn Huế</span>
        </div>

        <div className="space-y-3">
          {diagnosis.candidates.map((c, idx) => {
            const confBadgeVariant =
              c.confidence >= 0.8
                ? "success"
                : c.confidence >= 0.5
                ? "warning"
                : "neutral";

            return (
              <Card
                key={idx}
                className={`p-4 border transition ${
                  idx === 0
                    ? "border-brand-500/60 bg-gradient-to-br from-surface-card to-brand-950/20 shadow-md"
                    : "border-surface-border bg-surface-card"
                }`}
              >
                {/* Header: Rank + Name + Badges */}
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5">
                    <span className="w-6 h-6 rounded-full bg-surface-elevated text-brand-400 font-extrabold text-xs flex items-center justify-center shrink-0 mt-0.5">
                      #{idx + 1}
                    </span>
                    <div>
                      <h3 className="font-bold text-white text-base leading-snug">
                        {c.name}
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5 font-mono">
                        Mã lỗi: {c.fault_code}
                      </p>
                    </div>
                  </div>

                  {/* Confidence Badge (FR-DIAG-03) */}
                  <Badge variant={confBadgeVariant} className="shrink-0 text-xs font-semibold">
                    {c.confidence_label} ({(c.confidence * 100).toFixed(0)}%)
                  </Badge>
                </div>

                {/* Price Display (FR-DIAG-05 & AI Price Rule) */}
                <div className="mt-3.5 pt-3 border-t border-surface-border flex items-center justify-between">
                  <div>
                    <span className="text-xs text-slate-400 block">Khoảng giá tham khảo:</span>
                    <span className="text-base font-black text-brand-400">
                      {c.price_display}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Mức độ:</span>
                    <span className="text-xs font-bold text-slate-200">
                      {c.severity_vi}
                    </span>
                  </div>
                </div>

                {/* Candidate Specific Warning */}
                {c.safety_warning && (
                  <p className="mt-2 text-xs text-emergency-400 bg-emergency-950/30 p-2 rounded-lg flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                    <span>{c.safety_warning}</span>
                  </p>
                )}
              </Card>
            );
          })}
        </div>
      </section>

      {/* 3. SELF CHECKS (Khách tự kiểm tra) */}
      {diagnosis.self_checks && diagnosis.self_checks.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2 text-sky-400">
              <CheckCircle2 className="w-5 h-5" />
              <CardTitle className="text-sm">Kiểm Tra Sơ Bộ Trước Khi Gọi Thợ</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-300">
            {diagnosis.self_checks.map((check, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-sky-400 font-bold shrink-0">•</span>
                <span>{check}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* 4. DISCLAIMER (FR-DIAG-06) */}
      <div className="p-3 bg-surface-card border border-surface-border rounded-xl flex items-start gap-2 text-xs text-slate-400 leading-relaxed">
        <Info className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
        <p>
          <strong>Miễn trừ trách nhiệm:</strong> {diagnosis.disclaimer}
        </p>
      </div>

      {/* 5. PRIMARY ACTION: GỌI THỢ */}
      <div className="pt-2 space-y-2">
        <Button
          variant="emergency"
          size="lg"
          className="w-full text-lg font-bold shadow-2xl shadow-emergency-900/50"
          onClick={handleBookTechnician}
        >
          <Wrench className="w-6 h-6 mr-2" />
          <span>GỌI THỢ SỬA NGAY</span>
        </Button>

        <Link href="/diagnose" className="block">
          <Button variant="secondary" className="w-full text-sm">
            Chẩn đoán sự cố khác
          </Button>
        </Link>
      </div>

      {/* 6. FEEDBACK ON DIAGNOSIS ACCURACY (FR-DIAG-09) */}
      <div className="p-3 bg-surface-card border border-surface-border rounded-xl text-center space-y-2">
        <p className="text-xs text-slate-300 font-medium">
          Đánh giá độ chính xác của chẩn đoán (FR-DIAG-09):
        </p>
        {!feedbackSent ? (
          <div className="flex justify-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="text-xs min-h-[36px] py-1.5 px-3 border-emerald-500/50 text-emerald-300 hover:bg-emerald-500/10"
              onClick={() => handleFeedback("correct")}
            >
              <ThumbsUp className="w-3.5 h-3.5 mr-1 text-emerald-400" />
              <span>Chính xác</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs min-h-[36px] py-1.5 px-3 border-amber-500/50 text-amber-300 hover:bg-amber-500/10"
              onClick={() => handleFeedback("partial")}
            >
              <HelpCircle className="w-3.5 h-3.5 mr-1 text-amber-400" />
              <span>Một phần</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="text-xs min-h-[36px] py-1.5 px-3 border-slate-600 text-slate-300 hover:bg-slate-700/30"
              onClick={() => handleFeedback("wrong")}
            >
              <ThumbsDown className="w-3.5 h-3.5 mr-1 text-emergency-400" />
              <span>Sai</span>
            </Button>
          </div>
        ) : (
          <p className="text-xs text-emerald-400 font-semibold">
            ✓ Đã ghi nhận phản hồi của bạn. Cảm ơn bạn!
          </p>
        )}
      </div>
    </div>
  );
}
