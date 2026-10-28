"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Camera,
  Video,
  Mic,
  Square,
  Trash2,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Wrench,
  Clock,
  Layers,
  Bike,
  Tv,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { diagnosisApi, DiagnosisData, assetsApi, AssetResponse } from "@/lib/api";
import { compressImage } from "@/lib/compression";

function DiagnoseContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { showToast } = useToast();

  const initialGroup = (searchParams.get("group") as "motorbike" | "home") || "motorbike";
  const [categoryGroup, setCategoryGroup] = React.useState<"motorbike" | "home">(initialGroup);
  const [description, setDescription] = React.useState(searchParams.get("desc") || "");

  // Digital Health Log Asset Picker (P4, FR-HEALTH-01)
  const [userAssets, setUserAssets] = React.useState<AssetResponse[]>([]);
  const [selectedAssetId, setSelectedAssetId] = React.useState<string>("");

  React.useEffect(() => {
    assetsApi.list().then(({ data }) => {
      if (data) setUserAssets(data.items);
    });
  }, []);

  // Filter assets matching current category
  const filteredAssets = React.useMemo(() => {
    const targetType = categoryGroup === "motorbike" ? "vehicle" : "appliance";
    return userAssets.filter((a) => a.asset_type === targetType);
  }, [userAssets, categoryGroup]);

  // Media files
  const [images, setImages] = React.useState<File[]>([]);
  const [imagePreviews, setImagePreviews] = React.useState<string[]>([]);
  const [videoFile, setVideoFile] = React.useState<File | null>(null);
  const [audioFile, setAudioFile] = React.useState<File | null>(null);

  // Audio recording state
  const [isRecording, setIsRecording] = React.useState(false);
  const [recordingSeconds, setRecordingSeconds] = React.useState(0);
  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const audioChunksRef = React.useRef<Blob[]>([]);
  const timerRef = React.useRef<NodeJS.Timeout | null>(null);

  // Loading & Progress
  const [isDiagnosing, setIsDiagnosing] = React.useState(false);
  const [loadingStep, setLoadingStep] = React.useState(1);

  // Follow-up Questions State (when confidence < 50%)
  const [followupQuestions, setFollowupQuestions] = React.useState<string[]>([]);
  const [followupAnswers, setFollowupAnswers] = React.useState<Record<string, string>>({});

  // Clean previews on unmount
  React.useEffect(() => {
    return () => {
      imagePreviews.forEach((url) => URL.revokeObjectURL(url));
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [imagePreviews]);

  // Handle image upload with client compression <= 1.5MB
  const handleImageChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files) return;
    const files = Array.from(e.target.files);

    if (images.length + files.length > 5) {
      showToast("Chỉ được tải lên tối đa 5 ảnh.", "error");
      return;
    }

    showToast("Đang nén ảnh theo chuẩn di động (<= 1.5MB)...", "info");
    const compressedList: File[] = [];
    const previewList: string[] = [];

    for (const f of files) {
      if (f.size > 8 * 1024 * 1024) {
        showToast(`Ảnh ${f.name} vượt quá 8MB.`, "error");
        continue;
      }
      try {
        const compressed = await compressImage(f, 1.5 * 1024 * 1024);
        compressedList.push(compressed);
        previewList.push(URL.createObjectURL(compressed));
      } catch (err) {
        compressedList.push(f);
        previewList.push(URL.createObjectURL(f));
      }
    }

    setImages((prev) => [...prev, ...compressedList]);
    setImagePreviews((prev) => [...prev, ...previewList]);
  };

  const removeImage = (index: number) => {
    URL.revokeObjectURL(imagePreviews[index]);
    setImages((prev) => prev.filter((_, i) => i !== index));
    setImagePreviews((prev) => prev.filter((_, i) => i !== index));
  };

  // Handle video upload
  const handleVideoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !e.target.files[0]) return;
    const file = e.target.files[0];
    if (file.size > 50 * 1024 * 1024) {
      showToast("Video vượt quá dung lượng tối đa 50MB.", "error");
      return;
    }
    setVideoFile(file);
    showToast("Đã đính kèm video ngắn sự cố.", "success");
  };

  // Handle Audio recording (<= 20s per FR-DIAG-01)
  const startRecording = async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      showToast("Trình duyệt không hỗ trợ ghi âm trực tiếp.", "error");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const file = new File([blob], "tieng_keu_dong_co.webm", { type: "audio/webm" });
        setAudioFile(file);
        setIsRecording(false);
        stream.getTracks().forEach((track) => track.stop());
        showToast("Đã ghi âm tiếng máy thành công!", "success");
      };

      recorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => {
          if (prev >= 19) {
            stopRecording();
            return 20;
          }
          return prev + 1;
        });
      }, 1000);
    } catch (err) {
      showToast("Vui lòng cấp quyền micro để ghi âm tiếng máy.", "error");
    }
  };

  const stopRecording = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  };

  // Submit diagnosis form
  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!description.trim() && images.length === 0 && !audioFile && !videoFile) {
      showToast("Vui lòng nhập mô tả sự cố hoặc đính kèm ảnh/âm thanh.", "error");
      return;
    }

    setIsDiagnosing(true);
    setLoadingStep(1);

    const formData = new FormData();
    formData.append("category_group", categoryGroup);
    if (selectedAssetId) {
      formData.append("asset_id", selectedAssetId);
    }
    if (description.trim()) {
      formData.append("description", description.trim());
    }

    // Attach clarifying answers if any
    if (Object.keys(followupAnswers).length > 0) {
      formData.append("clarifying_answers", JSON.stringify(followupAnswers));
    }

    // Attach images
    images.forEach((img) => formData.append("images", img));

    // Attach video & audio
    if (videoFile) formData.append("video", videoFile);
    if (audioFile) formData.append("audio", audioFile);

    // Simulate animated progress steps for UX
    const stepInterval = setInterval(() => {
      setLoadingStep((s) => (s < 3 ? s + 1 : s));
    }, 1200);

    const { data, error } = await diagnosisApi.createDiagnosis(formData);
    clearInterval(stepInterval);
    setIsDiagnosing(false);

    if (error) {
      if (error.code === "QUOTA_EXCEEDED") {
        showToast(error.message, "error");
      } else if (error.code === "TERMS_NOT_ACCEPTED") {
        showToast(error.message, "error");
      } else {
        showToast(error.message || "Chẩn đoán thất bại. Vui lòng thử lại.", "error");
      }
      return;
    }

    if (data) {
      // Check if confidence is low (<50%) and has questions
      if (
        data.followup_questions &&
        data.followup_questions.length > 0 &&
        (!data.candidates || data.candidates.length === 0 || data.candidates[0].confidence < 0.5)
      ) {
        setFollowupQuestions(data.followup_questions);
        showToast("Độ tin cậy thấp (<50%). Vui lòng trả lời câu hỏi để AI xác định chính xác hơn.", "info");
      } else {
        // Navigate to result screen
        router.push(`/diagnose/${data.id}`);
      }
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 pt-2">
        <Link
          href="/"
          className="p-2 min-h-[44px] min-w-[44px] rounded-xl bg-surface-card border border-surface-border text-slate-300 hover:text-white flex items-center justify-center"
          aria-label="Quay lại trang chủ"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span>Chẩn Đoán Sự Cố AI</span>
            <Sparkles className="w-4 h-4 text-brand-400" />
          </h1>
          <p className="text-xs text-slate-400">TP. Huế – Chuẩn giá niêm yết, không chặt chém</p>
        </div>
      </div>

      {/* Category Group Toggle */}
      <div className="grid grid-cols-2 gap-2 p-1.5 bg-surface-card border border-surface-border rounded-2xl">
        <button
          type="button"
          onClick={() => setCategoryGroup("motorbike")}
          className={`min-h-[48px] rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all ${
            categoryGroup === "motorbike"
              ? "bg-brand-600 text-white shadow-md shadow-brand-900/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <span>🛵</span>
          <span>Xe Máy</span>
        </button>
        <button
          type="button"
          onClick={() => setCategoryGroup("home")}
          className={`min-h-[48px] rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all ${
            categoryGroup === "home"
              ? "bg-brand-600 text-white shadow-md shadow-brand-900/40"
              : "text-slate-400 hover:text-white"
          }`}
        >
          <span>❄️</span>
          <span>Điện Máy / Đồ Nhà</span>
        </button>
      </div>

      {/* Asset Picker from Digital Health Log (FR-HEALTH-01) */}
      {filteredAssets.length > 0 && (
        <div className="p-3.5 bg-surface-card border border-surface-border rounded-2xl space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              {categoryGroup === "motorbike" ? <Bike className="w-4 h-4 text-amber-400" /> : <Tv className="w-4 h-4 text-sky-400" />}
              <span>Gắn với thiết bị trong Sổ Sức Khỏe (Tùy chọn):</span>
            </label>
            <Link
              href="/assets"
              className="text-[11px] text-brand-primary hover:text-brand-400 font-medium"
            >
              Quản lý ({userAssets.length}/10)
            </Link>
          </div>

          <select
            value={selectedAssetId}
            onChange={(e) => {
              const val = e.target.value;
              setSelectedAssetId(val);
              if (val) {
                const found = userAssets.find((a) => a.id === val);
                if (found && !description) {
                  setDescription(`Sự cố trên ${found.brand} ${found.model}${found.plate_or_serial ? ` (${found.plate_or_serial})` : ""}: `);
                }
              }
            }}
            className="w-full p-2.5 bg-surface-elevated border border-surface-border rounded-xl text-xs text-white focus:outline-none focus:border-brand-500"
          >
            <option value="">-- Không chọn (Nhập thiết bị mới) --</option>
            {filteredAssets.map((asset) => (
              <option key={asset.id} value={asset.id}>
                {asset.brand} {asset.model} {asset.plate_or_serial ? `[${asset.plate_or_serial}]` : ""} {asset.location_label ? `(${asset.location_label})` : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Low-confidence Clarifying Questions Form */}
      {followupQuestions.length > 0 && (
        <Card className="border-amber-500/60 bg-amber-950/20">
          <CardHeader>
            <div className="flex items-center gap-2 text-amber-400">
              <HelpCircle className="w-5 h-5" />
              <CardTitle className="text-base text-amber-300">
                Câu Hỏi Làm Rõ (Độ Tin Cậy AI &lt; 50%)
              </CardTitle>
            </div>
            <p className="text-xs text-amber-200/80">
              AI chưa đủ thông tin để kết luận chắc chắn. Hãy trả lời câu hỏi dưới đây rồi bấm Chẩn đoán lại:
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {followupQuestions.map((q, idx) => (
              <div key={idx} className="space-y-1">
                <label className="text-xs font-semibold text-slate-200">
                  {idx + 1}. {q}
                </label>
                <input
                  type="text"
                  placeholder="Nhập câu trả lời của bạn..."
                  className="w-full min-h-[44px] px-3.5 py-2 rounded-xl bg-surface-card border border-surface-border text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
                  value={followupAnswers[q] || ""}
                  onChange={(e) =>
                    setFollowupAnswers((prev) => ({
                      ...prev,
                      [q]: e.target.value,
                    }))
                  }
                />
              </div>
            ))}
            <Button
              variant="primary"
              size="sm"
              className="w-full mt-2"
              onClick={() => handleSubmit()}
            >
              Chạy Lại Chẩn Đoán AI
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Description Textarea */}
      <div className="space-y-2">
        <label className="block text-sm font-semibold text-slate-200">
          Mô tả hiện tượng sự cố
        </label>
        <textarea
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder={
            categoryGroup === "motorbike"
              ? "Ví dụ: Xe Wave đang đi trên đường thì máy kêu to xú-páp, đề không nổ, xì lốp..."
              : "Ví dụ: Máy lạnh Daikin bật 1 tiếng không mát, dàn lạnh chảy nước nhỏ giọt..."
          }
          className="w-full p-3.5 bg-surface-card border border-surface-border rounded-xl text-base text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Media Upload Area */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-semibold text-slate-200">
            Hình ảnh / Video / Ghi âm tiếng kêu
          </label>
          <span className="text-xs text-slate-400">{images.length}/5 ảnh</span>
        </div>

        {/* Media Buttons */}
        <div className="grid grid-cols-3 gap-2">
          {/* Photos */}
          <label className="min-h-[52px] p-2.5 bg-surface-card border border-surface-border rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-brand-500/60 active:scale-[0.98] transition">
            <input
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={handleImageChange}
              disabled={images.length >= 5}
            />
            <Camera className="w-5 h-5 text-brand-400 mb-1" />
            <span className="text-xs font-medium text-slate-300">Chụp / Ảnh</span>
          </label>

          {/* Video */}
          <label className="min-h-[52px] p-2.5 bg-surface-card border border-surface-border rounded-xl flex flex-col items-center justify-center cursor-pointer hover:border-brand-500/60 active:scale-[0.98] transition">
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={handleVideoChange}
            />
            <Video className="w-5 h-5 text-sky-400 mb-1" />
            <span className="text-xs font-medium text-slate-300">
              {videoFile ? "Đã có video" : "Video ≤30s"}
            </span>
          </label>

          {/* Audio Recorder */}
          <button
            type="button"
            onClick={isRecording ? stopRecording : startRecording}
            className={`min-h-[52px] p-2.5 border rounded-xl flex flex-col items-center justify-center active:scale-[0.98] transition ${
              isRecording
                ? "bg-emergency-900/60 border-emergency-500 animate-pulse text-emergency-300"
                : audioFile
                ? "bg-emerald-950/40 border-emerald-500 text-emerald-300"
                : "bg-surface-card border-surface-border text-slate-300 hover:border-brand-500/60"
            }`}
          >
            {isRecording ? (
              <>
                <Square className="w-5 h-5 text-emergency-400 mb-1" />
                <span className="text-xs font-bold text-emergency-300">
                  Dừng ({recordingSeconds}s/20s)
                </span>
              </>
            ) : audioFile ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-emerald-400 mb-1" />
                <span className="text-xs font-bold text-emerald-300">Đã ghi âm</span>
              </>
            ) : (
              <>
                <Mic className="w-5 h-5 text-purple-400 mb-1" />
                <span className="text-xs font-medium">Ghi âm ≤20s</span>
              </>
            )}
          </button>
        </div>

        {/* Audio file badge with delete */}
        {audioFile && (
          <div className="flex items-center justify-between p-2.5 bg-purple-950/30 border border-purple-500/40 rounded-xl text-xs text-purple-200">
            <div className="flex items-center gap-2">
              <Badge variant="brand" className="text-[10px]">Beta</Badge>
              <span>File âm thanh tiếng máy ({audioFile.name})</span>
            </div>
            <button
              type="button"
              onClick={() => setAudioFile(null)}
              className="text-slate-400 hover:text-emergency-400"
              aria-label="Xóa âm thanh"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Video file badge with delete */}
        {videoFile && (
          <div className="flex items-center justify-between p-2.5 bg-sky-950/30 border border-sky-500/40 rounded-xl text-xs text-sky-200">
            <span>Video đính kèm: {videoFile.name} ({(videoFile.size / 1024 / 1024).toFixed(1)} MB)</span>
            <button
              type="button"
              onClick={() => setVideoFile(null)}
              className="text-slate-400 hover:text-emergency-400"
              aria-label="Xóa video"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Image Preview Grid */}
        {imagePreviews.length > 0 && (
          <div className="grid grid-cols-4 gap-2 pt-1">
            {imagePreviews.map((url, idx) => (
              <div key={idx} className="relative aspect-square rounded-xl overflow-hidden border border-surface-border group">
                <img src={url} alt={`Preview ${idx}`} className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => removeImage(idx)}
                  className="absolute top-1 right-1 p-1 bg-black/70 hover:bg-emergency-600 rounded-md text-white transition"
                  aria-label="Xóa ảnh"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Animated Loading Overlay */}
      {isDiagnosing && (
        <Card className="border-brand-500/50 bg-brand-950/30 animate-pulse">
          <CardContent className="p-4 space-y-3 text-center">
            <div className="mx-auto w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
            <h4 className="font-bold text-white text-base">Đang Chẩn Đoán Lỗi Bằng AI...</h4>
            <div className="space-y-1.5 text-xs text-slate-300">
              <p className={loadingStep >= 1 ? "text-brand-300 font-medium" : "text-slate-500"}>
                ✓ 1. Nén ảnh và tải phương tiện an toàn
              </p>
              <p className={loadingStep >= 2 ? "text-brand-300 font-medium" : "text-slate-500"}>
                {loadingStep >= 2 ? "✓" : "○"} 2. Trợ lý AI đang phân tích triệu chứng lỗi
              </p>
              <p className={loadingStep >= 3 ? "text-brand-300 font-medium" : "text-slate-500"}>
                {loadingStep >= 3 ? "✓" : "○"} 3. Khớp mã lỗi và tra cứu bảng giá TP. Huế
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Submit Button */}
      <Button
        variant="primary"
        size="lg"
        className="w-full text-base font-bold shadow-xl shadow-brand-900/40"
        onClick={handleSubmit}
        isLoading={isDiagnosing}
      >
        <Sparkles className="w-5 h-5 mr-2" />
        <span>BẮT ĐẦU CHẨN ĐOÁN AI</span>
      </Button>

      {/* Safety Notice */}
      <div className="p-3 bg-surface-card border border-surface-border rounded-xl text-xs text-slate-400 space-y-1">
        <p className="font-semibold text-slate-300">💡 Lưu ý quan trọng:</p>
        <p>• Bảng giá luôn được tra cứu từ danh mục chuẩn tại Huế, không sinh tự do.</p>
        <p>• Hạn mức: 10 lượt/ngày (đã đăng nhập) hoặc 2 lượt/ngày (khách vãng lai).</p>
      </div>
    </div>
  );
}

export default function DiagnosePage() {
  return (
    <React.Suspense fallback={<div className="p-8 text-center text-slate-400">Đang tải biểu mẫu...</div>}>
      <DiagnoseContent />
    </React.Suspense>
  );
}
