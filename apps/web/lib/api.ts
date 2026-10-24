/**
 * Fix 24/7 API Client
 * Follows SRS §7.4 response format and error handling.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown> | Array<unknown>;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<{ data?: T; error?: ApiError }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("fix247_access_token") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    const body = await res.json().catch(() => null);

    if (!res.ok) {
      return {
        error: body?.error || {
          code: body?.detail?.code || "REQUEST_FAILED",
          message: body?.detail?.message || body?.detail || "Đã có lỗi xảy ra. Vui lòng thử lại.",
        },
      };
    }

    return { data: body?.data !== undefined ? body.data : body };
  } catch (err: unknown) {
    return {
      error: {
        code: "NETWORK_ERROR",
        message: "Không thể kết nối đến máy chủ. Vui lòng kiểm tra mạng.",
      },
    };
  }
}

export async function apiUpload<T>(
  endpoint: string,
  formData: FormData
): Promise<{ data?: T; error?: ApiError }> {
  const token = typeof window !== "undefined" ? localStorage.getItem("fix247_access_token") : null;

  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers,
      body: formData,
    });

    const body = await res.json().catch(() => null);

    if (!res.ok) {
      return {
        error: body?.error || {
          code: body?.detail?.code || "UPLOAD_FAILED",
          message: body?.detail?.message || body?.detail || "Tải lên phương tiện thất bại.",
        },
      };
    }

    return { data: body?.data !== undefined ? body.data : body };
  } catch (err: unknown) {
    return {
      error: {
        code: "NETWORK_ERROR",
        message: "Lỗi kết nối khi tải tệp lên máy chủ.",
      },
    };
  }
}

export const authApi = {
  requestOtp: (phone: string) =>
    apiRequest<{ message: string }>("/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ phone }),
    }),

  verifyOtp: (phone: string, otp: string) =>
    apiRequest<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      user: {
        id: string;
        phone: string;
        role: string;
        terms_accepted_at: string | null;
      };
    }>("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ phone, otp }),
    }),

  acceptTerms: () =>
    apiRequest<{ message: string; accepted_at: string }>("/auth/terms/accept", {
      method: "POST",
      body: JSON.stringify({ accept: true }),
    }),

  getMe: () => apiRequest<{ id: string; phone: string; role: string }>("/auth/me"),
};

export interface CandidateResult {
  fault_code: string;
  name: string;
  confidence: number;
  confidence_label: "Thấp" | "Vừa" | "Cao";
  severity: "low" | "medium" | "high" | "critical";
  severity_vi: string;
  price_range: { min: number; max: number; currency: string } | null;
  price_display: string;
  safety_warning?: string | null;
}

export interface DiagnosisData {
  id: string;
  user_id?: string | null;
  asset_id?: string | null;
  category_id?: string | null;
  category_group: "motorbike" | "home";
  description?: string | null;
  media_urls: string[];
  candidates: CandidateResult[];
  safety_warnings: string[];
  self_checks: string[];
  followup_questions: string[];
  needs_technician: boolean;
  can_book_without_diagnosis: boolean;
  is_cached: boolean;
  has_audio_beta: boolean;
  disclaimer: string;
  created_at: string;
}

export const diagnosisApi = {
  createDiagnosis: (formData: FormData) =>
    apiUpload<DiagnosisData>("/diagnoses", formData),

  getDiagnosis: (id: string) =>
    apiRequest<DiagnosisData>(`/diagnoses/${id}`),

  submitFeedback: (id: string, verifiedLabel?: string, feedbackText?: string, rating?: number) =>
    apiRequest<{ ok: boolean; message: string }>(`/diagnoses/${id}/feedback`, {
      method: "POST",
      body: JSON.stringify({
        verified_label: verifiedLabel,
        feedback_text: feedbackText,
        rating,
      }),
    }),

  getCategories: () =>
    apiRequest<Array<{ id: string; name: string; group: string; icon: string; sort_order: number }>>(
      "/categories"
    ),
};
