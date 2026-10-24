/**
 * Fix 24/7 – Shared TypeScript Domain Models & Types
 * Source of truth: SRS §6, §7, §8 & PRD
 */

export type UserRole = "CUSTOMER" | "TECHNICIAN" | "ADMIN";

export type TechnicianStatus = "PENDING" | "APPROVED" | "REJECTED" | "SUSPENDED";

export type ServiceGroup = "MOTORBIKE" | "HOME_APPLIANCE";

export type BookingType = "EMERGENCY" | "SCHEDULED";

/**
 * 14-state Order State Machine per SRS §6
 */
export type OrderStatus =
  | "CREATED"
  | "DIAGNOSED"
  | "DISPATCHING"
  | "ACCEPTED"
  | "ON_THE_WAY"
  | "ARRIVED"
  | "INSPECTING"
  | "QUOTED"
  | "APPROVED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "REJECTED"
  | "DISPUTED";

export type PaymentMethod = "CASH" | "VIETQR" | "WALLET";

export type PaymentStatus = "PENDING" | "PAID" | "FAILED" | "REFUNDED";

export type SeverityLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface GeoLocation {
  latitude: number;
  longitude: number;
  address?: string;
}

export interface UserProfile {
  id: string;
  phone: string;
  full_name: string | null;
  role: UserRole;
  avatar_url: string | null;
  terms_accepted_at: string | null;
  created_at: string;
}

export interface FaultCatalogItem {
  id: string;
  category_id: string;
  fault_code: string;
  name: string;
  name_vi: string;
  description_vi: string;
  labor_cost_min: number;
  labor_cost_max: number;
  parts_cost_min: number;
  parts_cost_max: number;
  typical_duration_minutes: number;
  severity: SeverityLevel;
  safety_warning: string | null;
  is_emergency_eligible: boolean;
}

export interface DiagnosisResult {
  id: string;
  suggested_faults: Array<{
    fault_code: string;
    confidence: number;
    name_vi: string;
    description: string;
    price_range: {
      min: number;
      max: number;
      currency: "VND";
    };
    safety_warning?: string;
  }>;
  clarifying_questions?: string[];
  requires_manual_inspection: boolean;
  audio_beta_notice?: boolean;
}

export interface OrderItem {
  id: string;
  order_id: string;
  item_type: "LABOR" | "PART" | "FEE";
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface OrderEvent {
  id: string;
  order_id: string;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  actor_id: string;
  actor_role: UserRole;
  notes?: string;
  created_at: string;
}

export interface OrderDetail {
  id: string;
  order_code: string;
  customer_id: string;
  technician_id: string | null;
  asset_id: string | null;
  category_id: string;
  status: OrderStatus;
  booking_type: BookingType;
  scheduled_at: string | null;
  customer_location: GeoLocation;
  estimated_cost_min: number;
  estimated_cost_max: number;
  final_amount: number | null;
  night_surcharge: number;
  survey_fee: number;
  notes?: string;
  items: OrderItem[];
  events: OrderEvent[];
  created_at: string;
  updated_at: string;
}

/**
 * Standard API Envelope per SRS §7.4
 */
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown> | Array<unknown>;
  };
  meta?: {
    page?: number;
    limit?: number;
    total?: number;
    trace_id?: string;
  };
}
