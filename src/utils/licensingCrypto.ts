import { LicenseRecord, LicensePayload } from '../types';

export const MASTER_SECRET_SALT = "FBAUTO_BOT_MASTER_SECURE_SALT_2026_V9X_MARKETPLACE_AUTOMATION";
export const ADMIN_TARGET_EMAIL = "spain78666@gmail.com";
export const STORAGE_KEY_LICENSES = "fb_admin_keys_db";
export const STORAGE_KEY_SESSION = "fb_admin_auth_session";

/**
 * Base64 URL-safe encoding without padding
 */
function base64UrlEncode(str: string): string {
  const bytes = new TextEncoder().encode(str);
  let binary = '';
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Base64 URL-safe decoding
 */
function base64UrlDecode(b64url: string): string {
  let base64 = b64url.replace(/-/g, '+').replace(/_/g, '/');
  while (base64.length % 4) {
    base64 += '=';
  }
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new TextDecoder().decode(bytes);
}

/**
 * Computes HMAC-SHA256 signature using browser Web Crypto API
 */
async function computeHmacSha256(secret: string, data: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(secret);
  const msgData = encoder.encode(data);

  if (window.crypto && window.crypto.subtle) {
    const cryptoKey = await window.crypto.subtle.importKey(
      "raw",
      keyData,
      { name: "HMAC", hash: { name: "SHA-256" } },
      false,
      ["sign"]
    );
    const signatureBuffer = await window.crypto.subtle.sign("HMAC", cryptoKey, msgData);
    const hashArray = Array.from(new Uint8Array(signatureBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('').slice(0, 16).toUpperCase();
  }

  throw new Error("Web Crypto API is not available on this device.");
}

/**
 * Generates a signed cryptographic license key matching client Hardware IDs (HWID).
 * Key format: FBAUTO1.<BASE64_PAYLOAD>.<HEX_SIGNATURE>
 */
export async function generateLicenseKey(
  customerName: string,
  hwid: string,
  validityDays: number = 365,
  tier: string = "1 Year License",
  notes: string = ""
): Promise<{ licenseKey: string; payload: LicensePayload; record: LicenseRecord }> {
  const cleanHwid = hwid.trim().toUpperCase();
  const nowTs = Math.floor(Date.now() / 1000);
  const expiryTs = validityDays > 0 ? nowTs + (validityDays * 86400) : 0;

  const payload: LicensePayload = {
    customer: customerName.trim() || "Valued Customer",
    hwid: cleanHwid,
    tier: tier,
    created: nowTs,
    expiry: expiryTs,
    notes: notes.trim()
  };

  const payloadJson = JSON.stringify(payload);
  const payloadB64 = base64UrlEncode(payloadJson);
  const sig = await computeHmacSha256(MASTER_SECRET_SALT, payloadB64);
  const licenseKey = `FBAUTO1.${payloadB64}.${sig}`;

  const createdDate = new Date(nowTs * 1000).toISOString().replace('T', ' ').substring(0, 19);
  const expiryDate = expiryTs > 0 
    ? new Date(expiryTs * 1000).toISOString().replace('T', ' ').substring(0, 19)
    : "LIFETIME";

  const record: LicenseRecord = {
    key: licenseKey,
    customer: payload.customer,
    hwid: payload.hwid,
    tier: payload.tier,
    created_date: createdDate,
    expiry_date: expiryDate,
    notes: payload.notes,
    status: "ACTIVE",
    created_ts: nowTs,
    expiry_ts: expiryTs
  };

  return { licenseKey, payload, record };
}

/**
 * Verifies any FBAUTO1 key against an expected HWID and expiration date
 */
export async function verifyLicenseKey(
  licenseKey: string,
  expectedHwid?: string
): Promise<{ valid: boolean; message: string; payload?: LicensePayload }> {
  if (!licenseKey || typeof licenseKey !== 'string') {
    return { valid: false, message: "License key cannot be empty." };
  }

  const cleanKey = licenseKey.trim();
  const parts = cleanKey.split('.');
  if (parts.length !== 3 || (parts[0] !== 'FBAUTO1' && parts[0] !== 'FBV1')) {
    return { valid: false, message: "Invalid key format. Expected FBAUTO1.<PAYLOAD>.<SIG>" };
  }

  const payloadB64 = parts[1];
  const signatureHex = parts[2].toUpperCase();

  try {
    const expectedSig = await computeHmacSha256(MASTER_SECRET_SALT, payloadB64);
    if (signatureHex !== expectedSig) {
      return { valid: false, message: "Cryptographic signature validation failed. Key is forged or modified." };
    }

    const payloadJson = base64UrlDecode(payloadB64);
    const payload: LicensePayload = JSON.parse(payloadJson);

    if (expectedHwid && expectedHwid.trim()) {
      const cleanExpected = expectedHwid.trim().toUpperCase();
      if (payload.hwid.toUpperCase() !== cleanExpected) {
        return {
          valid: false,
          message: `Hardware ID mismatch. Key locked to ${payload.hwid}, your machine is ${cleanExpected}.`,
          payload
        };
      }
    }

    const nowTs = Math.floor(Date.now() / 1000);
    if (payload.expiry > 0 && nowTs > payload.expiry) {
      const expDate = new Date(payload.expiry * 1000).toLocaleDateString();
      return {
        valid: false,
        message: `License key has expired on ${expDate}. Please renew to continue.`,
        payload
      };
    }

    return { valid: true, message: "License key is cryptographically valid and active!", payload };
  } catch (err: any) {
    return { valid: false, message: `Key verification error: ${err.message || String(err)}` };
  }
}

/**
 * Prepares preformatted WhatsApp delivery message
 */
export function formatWhatsAppDeliveryText(
  customerName: string,
  hwid: string,
  key: string,
  tier: string,
  expiryDate: string
): string {
  return (
    `🎉 *FB Auto Bot Activation Key Ready!*\n\n` +
    `Hi *${customerName}*, thank you for choosing FB Auto Bot.\n\n` +
    `📋 *License Details:*\n` +
    `• *Plan:* ${tier}\n` +
    `• *Hardware ID:* \`${hwid}\`\n` +
    `• *Validity:* ${expiryDate}\n\n` +
    `🔑 *Your Activation Key:*\n` +
    `\`\`\`${key}\`\`\`\n\n` +
    `🚀 *How to Activate:*\n` +
    `1. Launch \`FBAutoBot.exe\` on your PC.\n` +
    `2. Paste the key above into the activation box.\n` +
    `3. Click *Unlock & Activate Software* to start automating!`
  );
}

/**
 * Default sample records to populate initial view if empty
 */
const DEFAULT_RECORDS: LicenseRecord[] = [
  {
    key: "FBAUTO1.eyJjdXN0b21lciI6Ik1hbGlrIFphZWVrIiwiY2hhbiI6InBybyIsImh3aWQiOiJGQkFVVE8tODQ5MS0yOTA0LTY2MTktMzk0OCIsInRpZXIiOiIxIFllYXIgTGljZW5zZSIsImNyZWF0ZWQiOjE3NzM2MDAwMDAsImV4cGlyeSI6MTgwNTEzNjAwMCwibm90ZXMiOiJPcmRlciAjMTA0MiAtIFdoYXRzQXBwIn0.7A8B9C0D1E2F3A4B",
    customer: "Malik Zaeek",
    hwid: "FBAUTO-8491-2904-6619-3948",
    tier: "1 Year License",
    created_date: "2026-03-15 14:20:00",
    expiry_date: "2027-03-15 14:20:00",
    notes: "Order #1042 - WhatsApp client",
    status: "ACTIVE",
    created_ts: 1773600000,
    expiry_ts: 1805136000
  },
  {
    key: "FBAUTO1.eyJjdXN0b21lciI6IlNoYWhpZCBBaG1lZCIsImh3aWQiOiJGQkFVVE8tMTEyMi0zMzQ0LTU1NjYtNzc4OCIsInRpZXIiOiJMaWZldGltZSBBY2Nlc3MiLCJjcmVhdGVkIjoxNzczNTEwMDAwLCJleHBpcnkiOjAsIm5vdGVzIjoiVklQIExpZmV0aW1lIFBhY2thZ2UifQ.9C8D7E6F5A4B3C2D",
    customer: "Shahid Ahmed",
    hwid: "FBAUTO-1122-3344-5566-7788",
    tier: "Lifetime Access",
    created_date: "2026-03-14 10:15:00",
    expiry_date: "LIFETIME",
    notes: "VIP Lifetime Package",
    status: "ACTIVE",
    created_ts: 1773510000,
    expiry_ts: 0
  }
];

export function loadSavedLicenses(): LicenseRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_LICENSES);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (e) {
    console.error("Error reading licenses from localStorage:", e);
  }
  return DEFAULT_RECORDS;
}

export function saveLicensesToStorage(records: LicenseRecord[]): void {
  try {
    localStorage.setItem(STORAGE_KEY_LICENSES, JSON.stringify(records));
  } catch (e) {
    console.error("Error writing licenses to localStorage:", e);
  }
}
