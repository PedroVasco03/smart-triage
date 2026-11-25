export type Status = "waiting" | "in_service" | "attended" | "left";

export interface VitalSigns {
  temperature?: number | null;
  heart_rate?: number | null;
  oxygen_saturation?: number | null;
  respiratory_rate?: number | null;
  systolic_pressure?: number | null;
  diastolic_pressure?: number | null;
  recorded_at?: string | null;
}

export interface Symptom { id: number; description: string; simulated_severity: number }
export interface ResourceNeed { resource_id: number; resource_name: string; quantity: number }

export interface Patient {
  id: number;
  patient_code: string;
  age: number;
  sex: string | null;
  status: Status;
  arrived_at: string;
  service_started_at: string | null;
  finished_at: string | null;
  is_simulated: boolean;
  session_id: number | null;
  waiting_minutes: number;
  service_minutes: number | null;
  service_remaining_minutes: number | null;
  vital_signs: VitalSigns | null;
  symptoms: Symptom[];
  required_resources: ResourceNeed[];
  queue_position: number | null;
  created_at: string;
  updated_at: string;
}

export interface PatientCreate {
  patient_code: string;
  age: number;
  sex?: "M" | "F" | null;
  vital_signs?: Partial<Omit<VitalSigns, "recorded_at">> | null;
  symptoms: { description: string; simulated_severity: number }[];
  required_resources: { resource_id: number; quantity: number }[];
  arrived_at?: string | null;
  service_minutes?: number | null;
}

export type Contributions = Record<"G" | "E" | "R" | "A", number>;

export interface QueueItem {
  position: number;
  patient_id: number;
  patient_code: string;
  age: number;
  symptoms: string[];
  waiting_minutes: number;
  utility_score: number;
  band: string;
  status: string;
  tie_break_applied: boolean;
  blocked_by_resources: boolean;
  last_evaluated_at: string;
  contributions: Contributions;
}

export interface Queue {
  evaluated_at: string;
  config_version: number;
  next_patient_id: number | null;
  items: QueueItem[];
}

export interface Factors {
  G: number; E: number; R: number; A: number;
  V: number | null; S: number; max_deviation: number; age_factor: number; A_raw: number;
  waiting_minutes: number;
  deviations: Record<string, number>;
  notes: string[];
}

export interface Evaluation {
  patient_id: number;
  patient_code: string;
  position: number;
  utility: number;
  band: string;
  factors: Factors;
  weights: Record<"w1" | "w2" | "w3" | "w4", number>;
  contributions: Contributions;
  explanation: string;
  tie_break_applied: boolean;
}

export interface QueueDetail {
  patient_id: number;
  patient_code: string;
  age: number;
  status: string;
  in_queue: boolean;
  live: boolean;
  evaluated_at: string;
  config_version: number | null;
  evaluation: Evaluation;
  symptoms: Symptom[];
  vital_signs: VitalSigns | null;
  blocked_by_resources: boolean;
  missing_resources: { resource_id: number; name: string; needed: number; free: number }[];
}

export interface HistoryItem {
  id: number;
  patient_id: number;
  patient_code: string | null;
  previous_position: number | null;
  new_position: number | null;
  previous_utility: number | null;
  new_utility: number | null;
  trigger: string;
  reason: string;
  config_id: number | null;
  changed_at: string;
}

export interface Weights { w1: number; w2: number; w3: number; w4: number }

export interface VitalRange { min: number; max: number; tol_low: number; tol_high: number; unit: string }

export interface AgentParams {
  tau_minutes: number;
  severity_vitals_share: number;
  vitals_max_share: number;
  risk_vitals_share: number;
  risk_age_share: number;
  risk_symptom_share: number;
  young_age: number;
  old_start: number;
  old_full: number;
  vital_ranges: Record<string, VitalRange>;
  priority_bands: [string, number][];
}

export interface AgentConfig {
  id: number;
  version: number;
  is_active: boolean;
  weights: Weights;
  normalized_weights: Weights;
  params: AgentParams;
  note: string | null;
  warnings: string[];
  created_at: string;
}

export interface AgentStatus {
  agent_type: string;
  config_version: number;
  queue_size: number;
  in_service: number;
  last_evaluation_at: string | null;
  total_evaluations: number;
  decision_cycle: string[];
}

export interface Resource {
  id: number;
  resource_name: string;
  quantity_available: number;
  quantity_in_use: number;
  quantity_free: number;
  updated_at: string;
}

export interface Dashboard {
  total_patients: number;
  in_queue: number;
  in_service: number;
  attended: number;
  average_utility: number | null;
  config_version: number;
  distribution: { band: string; count: number }[];
  recent_activity: { patient_code: string | null; trigger: string; reason: string; changed_at: string }[];
}

export interface EvolutionPoint {
  t: string;
  avg_utility?: number | null;
  max_utility?: number | null;
  n?: number | null;
  utility?: number | null;
  G?: number | null; E?: number | null; R?: number | null; A?: number | null;
}

export interface Scenario { key: string; name: string; description: string; default_capacity: Record<string, number> }

export interface SimMetrics {
  n_patients: number;
  served: number;
  unserved: number;
  unserved_high_severity: number;
  avg_wait_minutes: number | null;
  max_wait_minutes: number | null;
  p90_wait_minutes: number | null;
  avg_wait_high_severity: number | null;
  avg_wait_medium_severity: number | null;
  avg_wait_low_severity: number | null;
  avg_utility_at_service: number | null;
  resource_utilization: Record<string, number>;
}

export interface TimelinePoint { t: number; queue_length: number; in_service: number; avg_utility: number | null; max_wait: number }

export interface SimSession {
  id: number;
  session_name: string;
  description: string | null;
  status: string;
  configuration: Record<string, any>;
  summary: { metrics: SimMetrics; timeline: TimelinePoint[]; final_queue: unknown[] } | null;
  created_at: string;
}

export interface SimSessionItem {
  id: number;
  session_name: string;
  scenario: string | null;
  n_patients: number | null;
  seed: number | null;
  avg_wait_minutes: number | null;
  served: number | null;
  created_at: string;
}

export interface SimResult {
  id: number;
  session_id: number;
  patient_id: number;
  patient_code: string;
  utility_score: number;
  assigned_position: number | null;
  waiting_minutes: number | null;
  decision_explanation: string;
  details: Record<string, any> | null;
}

export interface CompareRun { session_id: number; name: string; weights: Weights; metrics: SimMetrics }
export interface CompareResponse { scenario: string; seed: number; runs: CompareRun[] }

export interface CallNext { called: boolean; message: string; patient_id?: number | null; patient_code?: string | null }

export interface ApiErrorBody { error: { code: string; message: string; details?: unknown } }
