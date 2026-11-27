export type Money = string; // DRF sends decimals as strings

export interface LocationInfo {
  id: number;
  name: string;
  address: string;
  is_primary: boolean;
  tax_rate: string;
  service_charge_rate: string;
  inventory_policy: "ALLOW" | "WARN" | "BLOCK";
  role: "OWNER" | "MANAGER" | "POS_OPERATOR" | null;
}

export interface Me {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "PLATFORM" | "OWNER";
  organization: { id: number; name: string; currency: string; timezone: string; is_active: boolean; branding?: Branding; loyalty?: LoyaltyRules } | null;
  membership_role: "OWNER" | "STAFF" | null;
  is_owner: boolean;
  can_manage_menu: boolean;
  can_manage_inventory: boolean;
  can_operate_pos: boolean;
  can_view_reports: boolean;
  locations: LocationInfo[];
  subscription: SubscriptionInfo | null;
}

export interface Paginated<T> { count: number; next: string | null; previous: string | null; results: T[] }

export interface Category { id: number; name: string; slug: string; is_active: boolean; image?: string | null }
export interface Variant { id: number; name: string; base_price: Money; is_active: boolean; product_name: string }
export interface Product { id: number; name: string; category: number; category_name: string; is_active: boolean; image?: string | null; variants: Variant[]; modifier_groups?: ModGroup[] }
export interface ModOption { id: number; name: string; price: Money }
export interface ModGroup { id: number; link_id?: number; name: string; min: number; max: number; required: boolean; options: ModOption[] }
export interface DealItemT { id: number; product_variant: number; variant_name: string; product_name: string; quantity: number }
export interface Deal {
  id: number; name: string; slug: string; description: string; image: string | null; discount_type: "PERCENTAGE" | "FIXED"; discount_value: Money;
  start_at: string; end_at: string; is_active: boolean; items: DealItemT[]; locations: { id: number; location: number; is_enabled: boolean }[];
}

export interface Floor { id: number; location: number; name: string; level: number; table_count: number }
export type TableShape = "SQUARE" | "ROUND" | "LONG" | "WALL";
export interface TableT { pos_x?: number | null; pos_y?: number | null; id: number; location: number; floor: number | null; floor_name: string | null; table_number: string; capacity: number; shape: TableShape; status: string; is_active: boolean }
export interface Branding { logo: string | null; logo_bw: string; qr_bw: string; qr_text: string; accounts: { label: string; title: string; number: string }[]; footer: string; show_logo: boolean; show_accounts: boolean; show_qr: boolean }

export type OrderStatus = "PENDING" | "CONFIRMED" | "PREPARING" | "READY" | "OUT_FOR_DELIVERY" | "COMPLETED" | "CANCELLED";
export type OrderType = "DINE_IN" | "TAKEAWAY" | "DELIVERY";
export interface OrderItem { id: number; product_name: string; variant_name: string; quantity: number; unit_price: Money; total_price: Money; deal_name?: string; notes?: string; modifiers?: { id?: number; group?: string; name: string; price?: string }[] }
export interface LoyaltyRules { enabled: boolean; spend_per_point?: Money; point_value?: Money; min_redeem?: number }
export interface OrderLoyalty { customer: string; balance: number; earned: number; redeemed: number; redeemed_value: Money; can_redeem: boolean; min_redeem: number; point_value: Money }
export interface Order {
  loyalty?: OrderLoyalty | null;
  id: number; order_number: string; location: number; location_name: string; order_type: OrderType; order_type_display: string;
  table: number | null; customer_name: string; customer_phone: string; delivery_address: string;
  waiter: number | null; waiter_name: string | null; rider: number | null; rider_name: string | null; dispatched_at: string | null; delivered_at: string | null;
  subtotal: Money; tax: Money; service_charge: Money; discount: Money; total_amount: Money;
  status: OrderStatus; status_display: string; payment_status: "PENDING" | "PARTIAL" | "PAID" | "REFUNDED" | "FAILED"; notes: string; items: OrderItem[]; created_at: string;
}

export type BaseUnit = "G" | "ML" | "PCS";
export interface Ingredient { id: number; name: string; base_unit: BaseUnit; cost_per_unit: Money; reorder_level: Money; is_prepared: boolean; is_active: boolean }
export interface StockRow {
  location: number; location_name: string; ingredient: number; ingredient_name: string; base_unit: BaseUnit;
  quantity: Money; reorder_level: Money; cost_per_unit: Money; stock_value: Money; is_low: boolean;
}
export interface Movement {
  id: number; ingredient_name: string; base_unit: BaseUnit; location_name: string; movement_type: string;
  movement_type_display: string; quantity_change: Money; balance_after: Money; note: string; created_by_name: string | null; created_at: string;
}
export interface RecipeLine { ingredient: number; ingredient_name: string; base_unit: BaseUnit; quantity: Money; line_cost: Money }
export interface Recipe { id: number; output_quantity: Money; lines: RecipeLine[]; cost: Money; price?: Money; profit?: Money; margin_percent?: string | null }

export type PayMethod = "CASH" | "CARD" | "WALLET" | "BANK";
export interface MethodTotals { sales: Money; refunds: Money; net: Money }
export interface ShiftSummary {
  id: number; status: "OPEN" | "CLOSED"; location: number; location_name: string; cashier: string;
  opened_at: string; closed_at: string | null; note: string; opening_cash: Money;
  methods: Record<PayMethod, MethodTotals>;
  sales_total: Money; refunds_total: Money; net_total: Money; orders_paid: number;
  discounts: Money; tax: Money; service_charge: Money;
  cash_in: Money; cash_out: Money; expenses: Money; safe_drops: Money;
  expected_cash: Money; counted_cash: Money | null; difference: Money | null;
  cancelled: { count: number; total: Money; orders: { order_number: string; total: Money; reason: string }[] };
  movements: { id: number; kind: string; amount: Money; category: string; reason: string; created_at: string }[];
}
export interface ShiftRow {
  id: number; status: "OPEN" | "CLOSED"; location_name: string; cashier: string; opened_at: string; closed_at: string | null;
  opening_cash: Money; expected_cash: Money | null; counted_cash: Money | null; difference: Money | null;
}
export interface PaymentRow { id: number; kind: "PAYMENT" | "REFUND"; method: PayMethod; amount: Money; tendered: Money | null; change: Money | null; reference: string; reason: string; by: string; created_at: string }
export interface OrderMoney { total: Money; paid: Money; refunded: Money; due: Money; payment_status: Order["payment_status"] }

export interface SalesReport {
  from: string; to: string;
  summary: { gross_sales: Money; refunds: Money; net_sales: Money; orders: number; average_order: Money; tax: Money; service_charge: Money; discounts: Money; food_cost: Money; food_profit: Money };
  by_method: Record<PayMethod, Money>;
  by_day: { date: string; net: Money }[];
  by_hour: { hour: number; orders: number }[];
  top_items: { name: string; variant: string; quantity: number; revenue: Money; cost: Money | null; profit: Money | null }[];
  items_without_recipe: string[];
  exceptions: {
    cancelled: { count: number; total: Money; orders: { order_number: string; total: Money; reason: string; by: string | null; at: string }[] };
    refunds: { count: number; total: Money; list: { order_number: string; amount: Money; method: PayMethod; reason: string; by: string; at: string }[] };
    discounts: Money;
  };
  cashiers: { username: string; net_sales: Money; refunds: number; cancellations: number }[];
  shift_differences: { id: number; cashier: string; closed_at: string; expected: Money; counted: Money; difference: Money; location: string }[];
}
export interface AuditRow { id: number; action: string; user: string | null; location: string | null; object_type: string; object_id: number | null; details: Record<string, unknown>; created_at: string }

export type SubStatus = "TRIAL" | "ACTIVE" | "PAST_DUE" | "SUSPENDED" | "CANCELLED";
export interface SubscriptionInfo {
  status: SubStatus; plan: { code: string; name: string; max_locations: number; max_users: number };
  price: Money; trial_ends_at: string | null; days_left: number | null; current_period_end: string | null;
  blocked: boolean; message: string; invoices_due: number; amount_due: Money; next_due_date?: string | null;
}
export interface PlanRow { id: number; code: string; name: string; description: string; price_monthly: Money; max_locations: number; max_users: number; features: string[]; is_active: boolean; sort_order: number; restaurants: number }
export interface InvoiceRow { id: number; number: string; organization: number; organization_name: string; period_start: string; period_end: string; amount: Money; status: "DUE" | "PAID" | "VOID"; issued_at: string; due_date: string; paid_at: string | null; method: string; reference: string; note: string; overdue: boolean }
export interface RestaurantRow {
  id: number; name: string; currency: string; is_active: boolean; created_at: string;
  owner: { id: number; name: string; username: string; email: string } | null;
  subscription: { status: SubStatus; plan: string; plan_name: string; price: Money; trial_ends_at: string | null; current_period_end: string | null; suspended_reason: string } | null;
  usage: { locations: number; users: number; orders_30d: number; sales_30d: Money; last_order_at: string | null };
  invoices_due: number;
}
export interface RestaurantDetail extends RestaurantRow {
  subscription_detail: { notes: string; price_override: Money | null; plan_price: Money; current_period_start: string | null } | null;
  locations: { id: number; name: string; address: string; is_active: boolean }[];
  users: { id: number; username: string; name: string; email: string; role: string; is_active: boolean; last_login: string | null }[];
  invoices: InvoiceRow[];
  activity: { action: string; user: string | null; details: Record<string, unknown>; created_at: string }[];
  status_info: SubscriptionInfo | null;
}
export interface PlatformOverview {
  restaurants: number; by_status: Record<SubStatus, number>; mrr: Money; new_this_month: number; orders_30d: number;
  sales_processed_30d: Money; collected_this_month: Money; pending_payments: number; overdue: { count: number; amount: Money };
  trials_ending: { id: number; name: string; ends: string }[]; recent: RestaurantRow[]; overdue_list: InvoiceRow[];
}

export type EmpRole = "MANAGER" | "CASHIER" | "WAITER" | "RIDER" | "CHEF" | "HELPER" | "OTHER";
export interface Employee {
  id: number; code: string; name: string; role: EmpRole; role_display: string; location: number; location_name: string;
  phone: string; cnic: string; address: string; emergency_contact: string; joining_date: string | null; is_active: boolean;
  vehicle: string; delivery_commission: Money; username: string | null; has_pin: boolean; created_at: string;
}
export interface RiderSummary { on_road: number; on_road_value: Money; to_settle_orders: number; to_settle: Money; delivered_today: number; delivered_30d: number; avg_delivery_minutes: number | null }
export interface RiderRow extends Employee { summary: RiderSummary }
export interface RiderLedger {
  rider: Employee; summary: RiderSummary;
  orders: { id: number; order_number: string; customer_name: string; address: string; total: Money; due: Money; delivered_at: string }[];
  settlements: { id: number; expected: Money; handed: Money; shortage: Money; orders: number; received_by: string; note: string; created_at: string }[];
}
export interface EmployeeDetail extends Employee { schedule: Schedule | null; today: { state: DayState; record: AttRecord | null }; stats: { kind: "waiter"; orders_30d: number; sales_30d: Money; average_bill: Money } | ({ kind: "rider" } & RiderSummary) }

export interface Schedule { start_time: string; end_time: string; weekly_off: number[]; grace_minutes: number; min_overtime_minutes: number; overtime_multiplier: number; overnight: boolean }
export interface AttRecord {
  id: number; date: string; status: "PRESENT" | "ABSENT" | "LEAVE"; paid_leave: boolean; check_in: string | null; check_out: string | null; source: string;
  worked_minutes: number; late_minutes: number; early_leave_minutes: number; overtime_minutes: number; on_off_day: boolean; auto_closed: boolean; note: string;
}
export type DayState = "ON_DUTY" | "DONE" | "ABSENT" | "ABSENT_DERIVED" | "LEAVE" | "OFF" | "NO_SCHEDULE" | "UPCOMING" | "NOT_JOINED" | "NOT_IN";
export interface BoardRow { employee: { id: number; code: string; name: string; role: EmpRole; role_display: string; has_pin: boolean }; schedule: Schedule | null; state: DayState; record: AttRecord | null }
export interface Board { date: string; location: number; counts: Record<string, number>; rows: BoardRow[] }
export interface AttReportRow {
  employee: { id: number; code: string; name: string; role: EmpRole; role_display: string; is_active: boolean }; schedule: Schedule | null;
  scheduled_days: number; present_days: number; late_days: number; late_minutes: number; early_leave_days: number; absent_days: number; leave_paid: number;
  leave_unpaid: number; worked_minutes: number; overtime_minutes: number; off_days_worked: number; missing_checkouts: number; records: AttRecord[] | null;
}
export interface AttReport { from: string; to: string; location: number; rows: AttReportRow[] }

export type PayType = "MONTHLY" | "DAILY" | "HOURLY";
export interface PayProfile {
  pay_type: PayType; base_amount: Money; month_basis: "30" | "26" | "CALENDAR"; standard_hours: Money | null; fixed_allowance: Money; fixed_deduction: Money;
  overtime_enabled: boolean; absent_penalty_days: Money; pay_paid_leave: boolean; pay_weekly_off: boolean; late_rule: "NONE" | "MINUTES" | "COUNT";
  late_every: number; late_deduct_days: Money; notes: string;
}
export interface PayEmp { id: number; code: string; name: string; role: EmpRole; role_display: string; location: number; location_name: string; is_active: boolean }
export interface PayProfileRow { employee: PayEmp; profile: PayProfile | null; hours_per_day: Money | null; advance_balance: Money }
export interface PayrollRunRow { id: number; month: string; location: number; location_name: string; status: "DRAFT" | "FINALIZED"; employees: number; gross: Money; deductions: Money; net: Money; paid: number; unpaid: number; unmarked: number; finalized_at: string | null }
export interface PaySlipRow { id: number; employee: PayEmp; pay_type: PayType; status: "DRAFT" | "UNPAID" | "PAID"; gross: Money; deductions: Money; net: Money; overtime_minutes: number; unmarked_days: number; warnings: string[]; paid_at: string | null; paid_method: string }
export interface PayrollRunDetail extends PayrollRunRow { blockers: string[]; can_finalize: boolean; slips: PaySlipRow[] }
export interface PaySlipFull extends PaySlipRow {
  base_amount: Money; daily_rate: Money; hourly_rate: Money; scheduled_days: number; present_days: number; absent_days: number; leave_paid: number; leave_unpaid: number;
  weekly_off_days: number; late_days: number; late_minutes: number; worked_minutes: number; deliveries: number;
  basic_pay: Money; overtime_pay: Money; allowance: Money; commission: Money; bonus: Money; absent_deduction: Money; leave_deduction: Money; late_deduction: Money;
  fixed_deduction: Money; other_deduction: Money; advance_deduction: Money;
  lines: { kind: "earning" | "deduction"; label: string; amount: number; note: string }[]; adjustments: { id: number; kind: "BONUS" | "DEDUCTION"; label: string; amount: Money }[];
  paid_reference: string; paid_by: string | null; month: string; run: number; run_status: "DRAFT" | "FINALIZED"; location_name: string;
}
export interface AdvanceRow {
  id: number; employee: PayEmp; amount: Money; installment: Money; given_on: string; reason: string; status: "ACTIVE" | "CLEARED" | "VOID"; repaid: Money; balance: Money;
  repayments?: { id: number; amount: Money; date: string; note: string; source: "PAYROLL" | "MANUAL" }[];
}

export interface PublicPlan { code: string; name: string; description: string; price_monthly: Money; max_locations: number; max_users: number; features: string[] }
export interface PaymentAccountT { id: number; method: "JAZZCASH" | "EASYPAISA" | "BANK" | "OTHER"; method_label: string; account_title: string; account_number: string; bank_name: string; instructions: string; is_active: boolean; sort_order: number }
export interface PaymentSubmissionT {
  id: number; status: "PENDING" | "APPROVED" | "REJECTED"; status_label: string; amount: Money; method: string; reference: string;
  sender_name: string; sender_number: string; note: string; proof: string | null; reject_reason: string;
  created_at: string; reviewed_at: string | null; invoice: number | null; invoice_number: string | null; invoice_amount: Money | null; amount_matches: boolean;
  organization?: number; organization_name?: string; submitted_by?: string | null;
}

export interface Reservation { id: number; location: number; table: number | null; table_number: string | null; guest_name: string; phone: string; party_size: number; starts_at: string; ends_at: string; duration_minutes: number; status: "BOOKED" | "SEATED" | "COMPLETED" | "CANCELLED" | "NO_SHOW"; notes: string }
export interface Supplier { id: number; name: string; phone: string; address: string; notes: string; is_active: boolean; balance: string }
export interface PurchaseT { id: number; location: number; location_name: string; date: string; invoice_no: string; supplier: number | null; supplier_name: string; total: string; paid: string; due: string; note: string; lines: { ingredient: number; name: string; quantity: string; unit: string; unit_cost: string; line_total: string }[] }
export interface ExpenseT { id: number; location: number; location_name: string; date: string; category: string; description: string; amount: string; source: "DRAWER" | "OTHER" }
export interface DayReport {
  date: string; locations: string[];
  sales: { gross_sales: string; refunds: string; net_sales: string; orders: number; average_order: string; tax: string; service_charge: string; discounts: string };
  by_method: Record<string, string>;
  exceptions: { cancelled: { count: number; total: string }; refunds: { count: number; total: string } };
  top_items: { name: string; variant: string; quantity: number; revenue: string }[];
  expenses: { total: string; by_category: { category: string; amount: string }[] };
  purchases: { count: number; total: string; paid: string; unpaid: string };
  drawer: { cash_in: string; cash_out: string; safe_drops: string };
  shifts: { id: number; cashier: string; location: string; opened_at: string; closed_at: string | null; still_open: boolean; opening_cash: string; expected_cash: string; counted_cash: string | null; difference: string | null }[];
  open_shifts: number; cash_short_over: string;
  reservations: { total: number; seated: number; no_show: number; cancelled: number };
  net_after_costs: string;
}
