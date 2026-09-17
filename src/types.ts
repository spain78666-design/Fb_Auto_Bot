export interface LicenseRecord {
  key: string;
  customer: string;
  hwid: string;
  tier: string;
  created_date: string;
  expiry_date: string;
  notes: string;
  status: 'ACTIVE' | 'DISABLED' | 'REVOKED' | 'EXPIRED';
  created_ts?: number;
  expiry_ts?: number;
}

export interface LicensePayload {
  customer: string;
  hwid: string;
  tier: string;
  created: number;
  expiry: number;
  notes: string;
}

export interface AdminSession {
  authenticated: boolean;
  email: string;
  loginTime: number;
  token: string;
}
