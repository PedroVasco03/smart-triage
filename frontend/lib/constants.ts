export const FACTORS = [
  { key: "G", weightKey: "w1", label: "Gravidade", color: "#B4412F", hint: "Sinais vitais e sintomas simulados" },
  { key: "E", weightKey: "w2", label: "Tempo de espera", color: "#3B6FB6", hint: "Cresce com a espera e satura" },
  { key: "R", weightKey: "w3", label: "Risco de agravamento", color: "#C28A1B", hint: "Idade, sinais críticos e sintomas" },
  { key: "A", weightKey: "w4", label: "Recursos", color: "#5B7F6A", hint: "Disponibilidade, protegida pelo risco" },
] as const;

export type FactorKey = (typeof FACTORS)[number]["key"];

export const BAND_COLORS: Record<string, string> = {
  "Muito alta": "#A32A2A",
  Alta: "#D2691E",
  Média: "#C28A1B",
  Baixa: "#6B7F8C",
};

export const STATUS_LABELS: Record<string, string> = {
  waiting: "Em espera",
  in_service: "Em atendimento",
  attended: "Atendido",
  left: "Saiu",
};

export const TRIGGER_LABELS: Record<string, string> = {
  patient_created: "Novo paciente",
  patient_updated: "Dados atualizados",
  status_changed: "Estado alterado",
  resources_changed: "Recursos",
  config_changed: "Pesos alterados",
  time_elapsed: "Tempo de espera",
  time_advanced: "Tempo avançado",
  patients_generated: "Pacientes gerados",
  manual: "Recálculo manual",
};

export const VITAL_FIELDS = [
  { key: "temperature", label: "Temperatura", unit: "°C", min: 30, max: 45, step: 0.1 },
  { key: "heart_rate", label: "Frequência cardíaca", unit: "bpm", min: 20, max: 250, step: 1 },
  { key: "oxygen_saturation", label: "Saturação de oxigénio", unit: "%", min: 50, max: 100, step: 1 },
  { key: "respiratory_rate", label: "Frequência respiratória", unit: "rpm", min: 4, max: 70, step: 1 },
  { key: "systolic_pressure", label: "Pressão sistólica", unit: "mmHg", min: 50, max: 260, step: 1 },
  { key: "diastolic_pressure", label: "Pressão diastólica", unit: "mmHg", min: 30, max: 160, step: 1 },
] as const;

export const DISCLAIMER =
  "Simulação académica com dados sintéticos. As pontuações são parâmetros experimentais e não constituem triagem clínica.";
