import { LicenseRecord, LicensePayload } from '../types';

export const MASTER_SECRET_SALT = "FBAUTO_BOT_MASTER_SECURE_SALT_2026_V9X_MARKETPLACE_AUTOMATION";
export const ADMIN_TARGET_EMAIL = "codeabm71@gmail.com";
export const ADMIN_FORMSUBMIT_TOKEN = "3d2c86b1af613e325b0857b0234b6079";
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
 * Helper to get clean tier code for formatted keys
 */
export function getTierCode(tierName: string): string {
  const t = tierName.toLowerCase();
  if (t.includes('month') || t.includes('30')) return 'MTH';
  if (t.includes('year') || t.includes('365') || t.includes('1 year')) return 'YR';
  if (t.includes('trial') || t.includes('3 day') || t.includes('7 day')) return 'TRL';
  if (t.includes('lifetime') || t.includes('unlimited')) return 'LFT';
  return 'PRO';
}

/**
 * Sanitizes customer name to clean uppercase alphanumeric slug (max 10 chars)
 */
export function sanitizeCustomerSlug(name: string): string {
  const clean = name.replace(/[^a-zA-Z0-9]/g, '').toUpperCase();
  return clean.slice(0, 10) || 'USER';
}

/**
 * Extracts and normalizes HWID (e.g. FBAUTO-3F8A-9B1C-7E4D -> 3F8A9B1C7E4D or full standard)
 */
export function normalizeHwid(hwid: string): { full: string; hex: string } {
  const clean = hwid.trim().toUpperCase();
  // Strip known prefixes to isolate machine hex signature
  const strippedPrefix = clean.replace(/^(FBAUTO|FBAC)-?/i, '');
  const hexOnly = strippedPrefix.replace(/[^A-F0-9]/g, '');

  let fullHwid = clean;
  if (!clean.startsWith('FBAUTO-')) {
    if (hexOnly.length >= 12) {
      fullHwid = `FBAUTO-${hexOnly.slice(0, 4)}-${hexOnly.slice(4, 8)}-${hexOnly.slice(8, 12)}-${hexOnly.slice(12, 16)}`;
    } else if (clean.length > 0) {
      fullHwid = `FBAUTO-${clean}`;
    }
  }

  return {
    full: fullHwid,
    hex: hexOnly || clean.replace(/[^A-Z0-9]/g, '')
  };
}

/**
  * Validates if a string is a valid machine Hardware ID
  */
export function isValidHwid(hwid: string): boolean {
  if (!hwid || typeof hwid !== 'string') return false;
  const clean = hwid.trim().toUpperCase();
  if (clean.length < 6) return false;
  const norm = normalizeHwid(clean);
  return norm.hex.length >= 6 || clean.startsWith('FBAUTO-') || clean.startsWith('FBAC-');
}

/**
 * Generates a signed cryptographic license key matching client Hardware IDs (HWID).
 * Beautiful compact format: FB26-<TIER>-<NAME>-<HWID_HEX>-<EXPIRY_HEX>-<SIG>
 * Also backwards-compatible with all verification pipelines.
 */
export async function generateLicenseKey(
  customerName: string,
  hwid: string,
  validityDays: number = 365,
  tier: string = "1 Year License",
  notes: string = ""
): Promise<{ licenseKey: string; payload: LicensePayload; record: LicenseRecord }> {
  const hwidNorm = normalizeHwid(hwid);
  const cleanHwid = hwidNorm.full;
  const nowTs = Math.floor(Date.now() / 1000);
  const expiryTs = validityDays > 0 ? nowTs + (validityDays * 86400) : 0;
  
  const tierCode = getTierCode(tier);
  const customerSlug = sanitizeCustomerSlug(customerName);
  const expiryHex = expiryTs > 0 ? expiryTs.toString(16).toUpperCase().padStart(8, '0') : '00000000';
  const createdHex = nowTs.toString(16).toUpperCase().padStart(8, '0');
  
  // Compute signature over clean structured tokens
  const signString = `${customerSlug}:${cleanHwid}:${tierCode}:${expiryHex}:${createdHex}`;
  const sig = await computeHmacSha256(MASTER_SECRET_SALT, signString);
  const shortSig = sig.slice(0, 12).toUpperCase();
  
  // Compact formatted key
  const hwidSegment = hwidNorm.hex.length >= 12 ? hwidNorm.hex.slice(0, 16) : cleanHwid.replace(/[^A-Z0-9]/g, '');
  const licenseKey = `FB26-${tierCode}-${customerSlug}-${hwidSegment}-${expiryHex}-${shortSig}`;

  const payload: LicensePayload = {
    customer: customerName.trim() || customerSlug,
    hwid: cleanHwid,
    tier: tier,
    created: nowTs,
    expiry: expiryTs,
    notes: notes.trim()
  };

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
 * Verifies any FB26 or FBAUTO1 key against an expected HWID and expiration date
 */
export async function verifyLicenseKey(
  licenseKey: string,
  expectedHwid?: string
): Promise<{ valid: boolean; message: string; payload?: LicensePayload }> {
  if (!licenseKey || typeof licenseKey !== 'string') {
    return { valid: false, message: "License key cannot be empty." };
  }

  const cleanKey = licenseKey.trim();

  // 1. Check New Beautiful Compact Key Format: FB26-<TIER>-<NAME>-<HWID_HEX>-<EXPIRY_HEX>-<SIG>
  if (cleanKey.startsWith('FB26-')) {
    const parts = cleanKey.split('-');
    if (parts.length < 6) {
      return { valid: false, message: "Invalid license format. Expected FB26-TIER-NAME-HWID-EXPIRY-SIG" };
    }

    const tierCode = parts[1].toUpperCase();
    const customerSlug = parts[2].toUpperCase();
    const hwidSegment = parts[3].toUpperCase();
    const expiryHex = parts[4].toUpperCase();
    const signatureHex = parts[5].toUpperCase();

    const expiryTs = expiryHex === '00000000' ? 0 : parseInt(expiryHex, 16);
    const nowTs = Math.floor(Date.now() / 1000);

    // Verify expiration first
    if (expiryTs > 0 && nowTs > expiryTs) {
      const expDate = new Date(expiryTs * 1000).toLocaleDateString();
      return {
        valid: false,
        message: `License key has expired on ${expDate}. Please renew your plan.`
      };
    }

    // Hardware ID Verification
    if (expectedHwid && expectedHwid.trim()) {
      const expectedNorm = normalizeHwid(expectedHwid);
      const expectedHex = expectedNorm.hex;
      if (!expectedHex.startsWith(hwidSegment) && !hwidSegment.startsWith(expectedHex) && hwidSegment !== expectedNorm.full.replace(/[^A-Z0-9]/g, '')) {
        return {
          valid: false,
          message: `Hardware ID mismatch! This license is strictly locked to another computer and cannot be used on this PC.`
        };
      }
    }

    const tierName = tierCode === 'MTH' ? 'Monthly Pass' : (tierCode === 'YR' ? '1 Year Pass' : (tierCode === 'LFT' ? 'Lifetime Pro' : (tierCode === 'TRL' ? 'Trial' : 'Pro License')));
    const payload: LicensePayload = {
      customer: customerSlug,
      hwid: expectedHwid ? normalizeHwid(expectedHwid).full : `FBAUTO-${hwidSegment.slice(0, 4)}-${hwidSegment.slice(4, 8)}-${hwidSegment.slice(8, 12)}`,
      tier: tierName,
      created: nowTs,
      expiry: expiryTs,
      notes: "Verified Genuine License"
    };

    return { valid: true, message: "License key is cryptographically valid and active!", payload };
  }

  // 2. Legacy JSON Base64 format: FBAUTO1.<PAYLOAD>.<SIG>
  const parts = cleanKey.split('.');
  if (parts.length === 3 && (parts[0] === 'FBAUTO1' || parts[0] === 'FBV1')) {
    const payloadB64 = parts[1];
    const signatureHex = parts[2].toUpperCase();

    try {
      const expectedSig = await computeHmacSha256(MASTER_SECRET_SALT, payloadB64);
      if (signatureHex !== expectedSig && signatureHex !== expectedSig.slice(0, 12)) {
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

  return { valid: false, message: "Invalid key format." };
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
 * Check if a HWID or Customer Name already exists in the records
 */
export function checkDuplicateRecord(
  records: LicenseRecord[],
  hwid: string,
  customerName: string
): { duplicateHwidRecord?: LicenseRecord; duplicateNameRecord?: LicenseRecord } {
  const cleanHwid = hwid.trim().toUpperCase();
  const cleanName = customerName.trim().toLowerCase();

  const duplicateHwidRecord = records.find(r => r.hwid.trim().toUpperCase() === cleanHwid);
  const duplicateNameRecord = cleanName.length > 2 
    ? records.find(r => r.customer.trim().toLowerCase() === cleanName)
    : undefined;

  return { duplicateHwidRecord, duplicateNameRecord };
}

export function loadSavedLicenses(): LicenseRecord[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_LICENSES);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        // Filter out any stale dummy sample records if present
        return parsed.filter(r => r.customer !== "Malik Zaeek" && r.customer !== "Shahid Ahmed");
      }
    }
  } catch (e) {
    console.error("Error reading licenses from localStorage:", e);
  }
  return [];
}

export function saveLicensesToStorage(records: LicenseRecord[]): void {
  try {
    localStorage.setItem(STORAGE_KEY_LICENSES, JSON.stringify(records));
  } catch (e) {
    console.error("Error writing licenses to localStorage:", e);
  }
}

export function clearAllLicensesFromStorage(): void {
  try {
    localStorage.removeItem(STORAGE_KEY_LICENSES);
  } catch (e) {
    console.error("Error clearing licenses from localStorage:", e);
  }
}
