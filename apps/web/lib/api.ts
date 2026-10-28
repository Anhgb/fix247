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

// ── P3 Types ────────────────────────────────────────────────────────────────

export interface InvoiceLineItem {
  item_type: "labor" | "part";
  name: string;
  qty: number;
  unit_price: number;
  line_total: number;
  photo_url?: string | null;
}

export interface InvoiceResponse {
  order_id: string;
  labor_subtotal: number;
  parts_subtotal: number;
  night_surcharge: number;
  total: number;
  commission_amount: number;
  commission_rate: number;
  warranty_days: number;
  items: InvoiceLineItem[];
}

export interface PaymentCreateResponse {
  payment_id: string;
  method: string;
  amount: number;
  status: string;
  qr_url?: string | null;
  instructions?: string | null;
}

export interface WalletInfoResponse {
  technician_id: string;
  total_earned: number;
  total_commission: number;
  debt_amount: number;
  debt_overdue_at: string | null;
  is_blocked: boolean;
}

export interface ReviewCreate {
  stars: number;
  tags: string[];
  comment?: string;
}

export interface WarrantyClaimCreate {
  reason: string;
  media_urls?: string[];
}

export interface WarrantyClaimResponse {
  id: string;
  order_id: string;
  status: string;
  reason: string;
  media_urls: string[];
  created_at: string;
  resolved_at?: string | null;
  resolution_note?: string | null;
}

export interface TechCompleteOrderRequest {
  photo_after_urls?: string[];
  summary?: string;
}

// ── P3 API helpers ───────────────────────────────────────────────────────────

export const ordersApi = {
  getInvoice: (id: string) => apiRequest<InvoiceResponse>(`/orders/${id}/invoice`),

  createPayment: (id: string, method: string) =>
    apiRequest<PaymentCreateResponse>(`/orders/${id}/pay`, {
      method: "POST",
      body: JSON.stringify({ method }),
    }),

  confirmCashPayment: (id: string, paymentId: string, role: "customer" | "technician") =>
    apiRequest(`/orders/${id}/payments/${paymentId}/cash-confirm`, {
      method: "POST",
      body: JSON.stringify({ confirmed_by: role }),
    }),

  submitReview: (id: string, data: ReviewCreate) =>
    apiRequest(`/orders/${id}/review`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  submitWarranty: (id: string, data: WarrantyClaimCreate) =>
    apiRequest<WarrantyClaimResponse>(`/orders/${id}/warranty`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getWarranty: (id: string) =>
    apiRequest<WarrantyClaimResponse>(`/orders/${id}/warranty`),

  submitDispute: (id: string, reason: string) =>
    apiRequest(`/orders/${id}/dispute`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  techComplete: (id: string, data: TechCompleteOrderRequest) =>
    apiRequest(`/orders/${id}/tech-complete`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

export const techApi = {
  getWallet: () => apiRequest<WalletInfoResponse>("/tech/wallet"),

  settleDebt: (amount: number) =>
    apiRequest(`/tech/wallet/settle-debt?amount=${amount}`, {
      method: "POST",
    }),

  getProfile: () => apiRequest<TechProfileResponse>("/tech/profile"),

  saveProfile: (data: TechProfileOnboardingRequest) =>
    apiRequest<TechProfileResponse>("/tech/profile", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getHistory: () => apiRequest<TechOrderHistoryResponse>("/tech/orders/history"),

  submitDiagnosisFeedback: (orderId: string, data: TechDiagnosisLabelRequest) =>
    apiRequest<{ ok: boolean; message: string }>(`/orders/${orderId}/diagnosis-feedback`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ── P4 Asset & Health Log Types ──────────────────────────────────────────────

export interface AssetCreate {
  asset_type: "vehicle" | "appliance";
  brand: string;
  model: string;
  year?: number | null;
  plate_or_serial?: string | null;
  location_label?: string | null;
  notes?: string | null;
}

export interface MaintenanceLogResponse {
  id: string;
  asset_id: string;
  order_id?: string | null;
  summary: string;
  parts_replaced?: Array<{ name: string; qty: number; unit_price: number }> | null;
  labor_cost: number;
  parts_cost: number;
  total_cost: number;
  technician_id?: string | null;
  technician_name?: string | null;
  performed_at: string;
  created_at: string;
}

export interface MaintenanceReminderResponse {
  reminder_type: string;
  title: string;
  message: string;
  due_date?: string | null;
  is_overdue: boolean;
}

export interface AssetResponse {
  id: string;
  owner_id: string;
  asset_type: "vehicle" | "appliance";
  brand?: string | null;
  model?: string | null;
  year?: number | null;
  plate_or_serial?: string | null;
  location_label?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  maintenance_count: number;
  last_maintained_at?: string | null;
  health_status: "good" | "needs_maintenance" | "due_soon";
  recent_logs: MaintenanceLogResponse[];
  reminders: MaintenanceReminderResponse[];
}

export interface AssetListResponse {
  total: number;
  items: AssetResponse[];
}

export const assetsApi = {
  list: () => apiRequest<AssetListResponse>("/assets"),
  get: (id: string) => apiRequest<AssetResponse>(`/assets/${id}`),
  create: (data: AssetCreate) =>
    apiRequest<AssetResponse>("/assets", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<AssetCreate>) =>
    apiRequest<AssetResponse>(`/assets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/assets/${id}`, {
      method: "DELETE",
    }),
  getReminders: (id: string) =>
    apiRequest<MaintenanceReminderResponse[]>(`/assets/${id}/reminders`),
};

// ── P4 Tech Onboarding & History Types ───────────────────────────────────────

export interface TechProfileOnboardingRequest {
  id_number: string;
  portrait_url: string;
  certificate_urls: string[];
  specialties: string[];
  service_areas: string[];
}

export interface TechBadge {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface TechProfileResponse {
  id: string;
  user_id: string;
  id_number_masked: string;
  portrait_url?: string | null;
  certificate_urls: string[];
  specialties: string[];
  service_areas: string[];
  approval_status: "pending" | "approved" | "rejected" | "suspended";
  approval_note?: string | null;
  approved_at?: string | null;
  is_online: boolean;
  rating_avg: number;
  rating_count: number;
  total_earned: number;
  debt_amount: number;
  badges: TechBadge[];
  created_at: string;
  updated_at: string;
}

export interface TechOrderHistoryItem {
  order_id: string;
  code: string;
  service_name: string;
  status: string;
  customer_name: string;
  address: string;
  completed_at?: string | null;
  total_amount: number;
  tech_earnings: number;
  customer_rating?: number | null;
  customer_comment?: string | null;
}

export interface TechOrderHistoryResponse {
  total: number;
  items: TechOrderHistoryItem[];
  total_earnings: number;
}

export interface TechDiagnosisLabelRequest {
  verified_label: "correct" | "partial" | "incorrect";
  notes?: string;
}

// ── P5 Admin Panel & QR Types (UC-10, UC-11, UC-12, FR-ADM, FR-QR) ──────────

export interface AdminDashboardStats {
  orders_total: number;
  orders_today: number;
  gmv_total: number;
  gmv_today: number;
  commission_total: number;
  median_time_to_accept_sec?: number | null;
  completion_rate_pct: number;
  dispute_rate_pct: number;
  ai_top3_accuracy_pct: number;
  ai_calls_total: number;
  ai_cost_per_call_vnd: number;
  ai_daily_spend_vnd: number;
  ai_monthly_spend_vnd: number;
  ai_monthly_budget_vnd: number;
  ai_budget_alert: boolean;
  maps_daily_spend_vnd: number;
  maps_monthly_spend_vnd: number;
  maps_monthly_budget_vnd: number;
  maps_budget_alert: boolean;
}

export interface AdminTechnicianItem {
  profile_id: string;
  user_id: string;
  phone: string;
  name: string;
  id_number_masked: string;
  portrait_url?: string | null;
  certificate_urls: string[];
  specialties: string[];
  service_areas: string[];
  approval_status: "pending" | "approved" | "rejected" | "suspended";
  approval_note?: string | null;
  is_online: boolean;
  rating_avg: number;
  rating_count: number;
  total_earned: number;
  debt_amount: number;
  badges: TechBadge[];
  created_at: string;
}

export interface FaultCatalogItem {
  id: string;
  category_id: string;
  category_name?: string | null;
  fault_code: string;
  name: string;
  description?: string | null;
  labor_min: number;
  labor_max: number;
  parts_min: number;
  parts_max: number;
  safety_notes?: string | null;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface FaultCatalogCreate {
  category_id: string;
  fault_code: string;
  name: string;
  description?: string;
  labor_min: number;
  labor_max: number;
  parts_min?: number;
  parts_max?: number;
  safety_notes?: string;
  is_active?: boolean;
}

export interface FaultCatalogUpdate {
  name?: string;
  description?: string;
  labor_min?: number;
  labor_max?: number;
  parts_min?: number;
  parts_max?: number;
  safety_notes?: string;
  is_active?: boolean;
}

export interface AdminOrderItem {
  id: string;
  mode: string;
  status: string;
  address: string;
  customer_id: string;
  customer_phone: string;
  customer_name: string;
  technician_id?: string | null;
  technician_phone?: string | null;
  technician_name?: string | null;
  final_quote?: number | null;
  total?: number | null;
  commission_amount?: number | null;
  created_at: string;
  scheduled_at?: string | null;
  completed_at?: string | null;
}

export interface AdminDisputeItem {
  id: string;
  order_id: string;
  opened_by_id: string;
  opened_by_phone?: string | null;
  opened_by_name?: string | null;
  reason: string;
  status: "open" | "resolved" | "closed";
  resolution?: string | null;
  resolved_by_id?: string | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
  order_total?: number | null;
  order_code?: string | null;
}

export interface PlatformSettings {
  commission_rate: number;
  night_surcharge: number;
  survey_fee: number;
  travel_fee: number;
  emergency_radius_km: number;
  ai_daily_quota_anon: number;
  ai_daily_quota_user: number;
  monthly_ai_budget_vnd: number;
  monthly_maps_budget_vnd: number;
}

export interface QRLocationItem {
  id: string;
  code: string;
  name: string;
  location_type?: string | null;
  address: string;
  lat?: number | null;
  lng?: number | null;
  owner_contact?: string | null;
  scan_count: number;
  order_count: number;
  conversion_rate_pct: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  landing_url: string;
}

export interface QRLocationCreate {
  name: string;
  location_type?: string;
  address: string;
  lat?: number;
  lng?: number;
  owner_contact?: string;
}

export interface QRLocationPublic {
  id: string;
  code: string;
  name: string;
  location_type?: string | null;
  address: string;
  lat?: number | null;
  lng?: number | null;
}

export interface AdminActionLogItem {
  id: string;
  admin_id: string;
  admin_phone?: string | null;
  action: string;
  entity_type?: string | null;
  entity_id?: string | null;
  detail?: Record<string, unknown> | null;
  created_at: string;
}

export const adminApi = {
  getDashboard: () => apiRequest<AdminDashboardStats>("/admin/dashboard"),

  getTechnicians: (status?: string) =>
    apiRequest<{ total: number; items: AdminTechnicianItem[] }>(
      status ? `/admin/technicians?status=${status}` : "/admin/technicians"
    ),

  approveTechnician: (techUserId: string, note?: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/admin/technicians/${techUserId}/approve`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),

  rejectTechnician: (techUserId: string, note?: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/admin/technicians/${techUserId}/reject`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),

  suspendTechnician: (techUserId: string, note?: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/admin/technicians/${techUserId}/suspend`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),

  getFaultCatalog: (search?: string, categoryId?: string) => {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (categoryId) params.append("category_id", categoryId);
    const qs = params.toString();
    return apiRequest<{ total: number; items: FaultCatalogItem[] }>(
      qs ? `/admin/fault-catalog?${qs}` : "/admin/fault-catalog"
    );
  },

  createFaultCatalog: (data: FaultCatalogCreate) =>
    apiRequest<FaultCatalogItem>("/admin/fault-catalog", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateFaultCatalog: (id: string, data: FaultCatalogUpdate) =>
    apiRequest<FaultCatalogItem>(`/admin/fault-catalog/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  importFaultCatalogCsv: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return apiUpload<{ ok: boolean; message: string; created_count: number; updated_count: number }>(
      "/admin/fault-catalog/import-csv",
      formData
    );
  },

  getOrders: (params?: { status?: string; mode?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.append("status", params.status);
    if (params?.mode) q.append("mode", params.mode);
    if (params?.search) q.append("search", params.search);
    const qs = q.toString();
    return apiRequest<{ total: number; items: AdminOrderItem[] }>(
      qs ? `/admin/orders?${qs}` : "/admin/orders"
    );
  },

  getOrderDetail: (orderId: string) => apiRequest<any>(`/admin/orders/${orderId}`),

  transitionOrder: (orderId: string, targetStatus: string, reason?: string) =>
    apiRequest<{ ok: boolean; message: string; status: string }>(`/admin/orders/${orderId}/transition`, {
      method: "POST",
      body: JSON.stringify({ target_status: targetStatus, reason }),
    }),

  reassignTechnician: (orderId: string, technicianId: string, reason?: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/admin/orders/${orderId}/reassign`, {
      method: "POST",
      body: JSON.stringify({ technician_id: technicianId, reason }),
    }),

  cancelOrder: (orderId: string, cancelReason: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/admin/orders/${orderId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ cancel_reason: cancelReason }),
    }),

  addOrderNote: (orderId: string, note: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/admin/orders/${orderId}/notes`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),

  getDisputes: (status?: string) =>
    apiRequest<{ total: number; items: AdminDisputeItem[] }>(
      status ? `/admin/disputes?status=${status}` : "/admin/disputes"
    ),

  resolveDispute: (disputeId: string, action: "refund" | "reject" | "close", resolutionNote: string) =>
    apiRequest<{ ok: boolean; message: string }>(`/admin/disputes/${disputeId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ action, resolution_note: resolutionNote }),
    }),

  getSettings: () => apiRequest<PlatformSettings>("/admin/settings"),

  updateSettings: (data: Partial<PlatformSettings>) =>
    apiRequest<PlatformSettings>("/admin/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  getQRLocations: () =>
    apiRequest<{ total: number; items: QRLocationItem[] }>("/admin/qr-locations"),

  createQRLocation: (data: QRLocationCreate) =>
    apiRequest<QRLocationItem>("/admin/qr-locations", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateQRLocation: (id: string, data: Partial<QRLocationCreate & { is_active: boolean }>) =>
    apiRequest<QRLocationItem>(`/admin/qr-locations/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getAuditLogs: (limit = 50, offset = 0) =>
    apiRequest<{ total: number; items: AdminActionLogItem[] }>(
      `/admin/audit-logs?limit=${limit}&offset=${offset}`
    ),
};

export const qrApi = {
  resolve: (code: string) => apiRequest<QRLocationPublic>(`/qr/${code}`),
};


