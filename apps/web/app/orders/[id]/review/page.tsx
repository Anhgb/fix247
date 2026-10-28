"use client";

/**
 * Review Form – FR-RATE-01, FR-RATE-02, FR-RATE-03
 * Customer leaves 1-5 stars + tags + comment for COMPLETED orders.
 */

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Star, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { ordersApi, ReviewCreate } from "@/lib/api";

const PRESET_TAGS = [
  "Đúng giờ",
  "Giá đúng báo",
  "Sạch sẽ",
  "Thân thiện",
  "Chuyên nghiệp",
  "Sửa chắc tay",
  "Nhiệt tình",
];

const STAR_LABELS: Record<number, string> = {
  1: "Rất tệ",
  2: "Tệ",
  3: "Bình thường",
  4: "Tốt",
  5: "Xuất sắc",
};

export default function ReviewPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params?.id as string;
  const { showToast } = useToast();

  const [stars, setStars] = React.useState(0);
  const [hovered, setHovered] = React.useState(0);
  const [tags, setTags] = React.useState<string[]>([]);
  const [comment, setComment] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [submitted, setSubmitted] = React.useState(false);

  const MAX_COMMENT = 500;

  const toggleTag = (tag: string) => {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  const handleSubmit = async () => {
    if (stars === 0) {
      showToast("Vui lòng chọn số sao đánh giá.", "error");
      return;
    }
    if (comment.length > MAX_COMMENT) {
      showToast(`Nhận xét không được vượt quá ${MAX_COMMENT} ký tự.`, "error");
      return;
    }

    setSubmitting(true);
    const payload: ReviewCreate = { stars, tags, comment: comment || undefined };
    const { error } = await ordersApi.submitReview(orderId, payload);
    setSubmitting(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    setSubmitted(true);
    showToast("Cảm ơn bạn đã đánh giá!", "success");
  };

  if (submitted) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 gap-5 text-center">
        <CheckCircle2 className="w-16 h-16 text-emerald-400" />
        <h2 className="text-2xl font-black text-white">Cảm ơn bạn!</h2>
        <p className="text-slate-300 text-sm leading-relaxed max-w-xs">
          Đánh giá của bạn giúp thợ cải thiện chất lượng dịch vụ và giúp khách hàng khác chọn
          được thợ phù hợp.
        </p>
        <Button
          variant="primary"
          size="lg"
          className="w-full max-w-xs"
          onClick={() => router.push("/orders")}
        >
          Về Danh Sách Đơn
        </Button>
      </div>
    );
  }

  const displayStar = hovered > 0 ? hovered : stars;

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.back()}
          className="h-10 w-10 p-0 rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-black text-white">Đánh Giá Dịch Vụ</h1>
          <p className="text-xs text-slate-400">Đơn #{orderId.slice(0, 8)}</p>
        </div>
      </div>

      {/* Star selector */}
      <div className="p-5 bg-surface-card border border-surface-border rounded-2xl space-y-4 text-center">
        <p className="text-slate-300 text-sm font-medium">Bạn hài lòng thế nào với dịch vụ?</p>

        <div className="flex justify-center gap-2">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              className="p-1 touch-target-lg transition-transform hover:scale-110"
              onClick={() => setStars(n)}
              onMouseEnter={() => setHovered(n)}
              onMouseLeave={() => setHovered(0)}
              aria-label={`${n} sao`}
              style={{ minWidth: 48, minHeight: 48 }}
            >
              <Star
                className={`w-10 h-10 transition-colors ${
                  n <= displayStar
                    ? "fill-amber-400 text-amber-400"
                    : "text-slate-600"
                }`}
              />
            </button>
          ))}
        </div>

        {displayStar > 0 && (
          <p className="text-amber-400 font-bold text-lg">
            {STAR_LABELS[displayStar]}
          </p>
        )}
      </div>

      {/* Tag chips */}
      <div className="space-y-3">
        <h3 className="text-white font-semibold text-sm">
          Điểm nổi bật <span className="text-slate-500 font-normal">(tùy chọn)</span>
        </h3>
        <div className="flex flex-wrap gap-2">
          {PRESET_TAGS.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => toggleTag(tag)}
              className={`px-4 py-2 rounded-full text-sm font-medium border transition-all min-h-[40px] ${
                tags.includes(tag)
                  ? "bg-brand-primary border-brand-primary text-white"
                  : "bg-surface-card border-surface-border text-slate-400 hover:border-slate-500"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Comment */}
      <div className="space-y-2">
        <label className="text-white font-semibold text-sm">
          Nhận xét <span className="text-slate-500 font-normal">(tùy chọn)</span>
        </label>
        <textarea
          className="w-full bg-surface-card border border-surface-border rounded-xl p-3 text-white text-sm resize-none focus:outline-none focus:border-brand-primary transition-colors placeholder:text-slate-500"
          rows={4}
          maxLength={MAX_COMMENT}
          placeholder="Chia sẻ trải nghiệm của bạn..."
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
        <p
          className={`text-xs text-right ${
            comment.length > MAX_COMMENT * 0.9 ? "text-amber-400" : "text-slate-500"
          }`}
        >
          {comment.length}/{MAX_COMMENT}
        </p>
      </div>

      {/* Submit */}
      <Button
        variant="primary"
        size="lg"
        className="w-full min-h-[52px] font-bold"
        onClick={handleSubmit}
        isLoading={submitting}
        disabled={stars === 0}
      >
        <Star className="w-5 h-5 mr-2" />
        Gửi Đánh Giá
      </Button>
    </div>
  );
}

