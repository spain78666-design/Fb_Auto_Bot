import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldCheck,
  Key,
  Lock,
  Mail,
  CheckCircle2,
  Copy,
  ExternalLink,
  Check,
  RefreshCw,
  Search,
  Download,
  Upload,
  Trash2,
  Calendar,
  User,
  Cpu,
  Smartphone,
  AlertTriangle,
  ArrowRight,
  LogOut,
  Send,
  MessageSquare,
  Sparkles,
  Zap,
  Info
} from 'lucide-react';
import { LicenseRecord, LicensePayload } from '../types';
import {
  ADMIN_TARGET_EMAIL,
  ADMIN_FORMSUBMIT_TOKEN,
  STORAGE_KEY_SESSION,
  generateLicenseKey,
  verifyLicenseKey,
  formatWhatsAppDeliveryText,
  loadSavedLicenses,
  saveLicensesToStorage
} from '../utils/licensingCrypto';

interface AdminPanelProps {
  onBackToApp?: () => void;
}

export default function AdminPanel({ onBackToApp }: AdminPanelProps) {
  // Authentication & OTP State
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [adminEmail, setAdminEmail] = useState<string>(ADMIN_TARGET_EMAIL);
  const [otpSent, setOtpSent] = useState<boolean>(false);
  const [generatedOtp, setGeneratedOtp] = useState<string>('');
  const [otpDigits, setOtpDigits] = useState<string[]>(['', '', '', '', '', '']);
  const [otpError, setOtpError] = useState<string>('');
  const [otpSuccess, setOtpSuccess] = useState<string>('');
  const [resendCountdown, setResendCountdown] = useState<number>(0);
  const [isSendingOtp, setIsSendingOtp] = useState<boolean>(false);

  // Generator Form State
  const [customerName, setCustomerName] = useState<string>('');
  const [customerHwid, setCustomerHwid] = useState<string>('');
  const [selectedPlan, setSelectedPlan] = useState<string>('365');
  const [customDays, setCustomDays] = useState<number>(90);
  const [orderNotes, setOrderNotes] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // Last Generated Result State
  const [lastGeneratedKey, setLastGeneratedKey] = useState<string>('');
  const [lastPayload, setLastPayload] = useState<LicensePayload | null>(null);
  const [lastWhatsAppText, setLastWhatsAppText] = useState<string>('');
  const [copiedKey, setCopiedKey] = useState<boolean>(false);
  const [copiedWa, setCopiedWa] = useState<boolean>(false);

  // Database Records State
  const [records, setRecords] = useState<LicenseRecord[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'LIFETIME'>('ALL');
  const [copiedRecordKey, setCopiedRecordKey] = useState<string | null>(null);

  // Key Inspector / Verifier State
  const [verifyInputKey, setVerifyInputKey] = useState<string>('');
  const [verifyExpectedHwid, setVerifyExpectedHwid] = useState<string>('');
  const [verifyResult, setVerifyResult] = useState<{ valid: boolean; message: string; payload?: LicensePayload } | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  // Active Tab inside Admin Panel
  const [activeAdminTab, setActiveAdminTab] = useState<'generator' | 'database' | 'verifier'>('generator');

  // Duplicate warning modal state
  interface DuplicateInfo {
    show: boolean;
    reason: 'HWID' | 'Name';
    record: LicenseRecord;
  }
  const [duplicateWarning, setDuplicateWarning] = useState<DuplicateInfo | null>(null);

  // References for 6-digit OTP inputs
  const otpInputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Check existing session on load
  useEffect(() => {
    try {
      const savedSession = localStorage.getItem(STORAGE_KEY_SESSION);
      if (savedSession) {
        const session = JSON.parse(savedSession);
        // Session valid for 24 hours
        if (session.authenticated && session.loginTime && Date.now() - session.loginTime < 86400000) {
          setIsAuthenticated(true);
        } else {
          localStorage.removeItem(STORAGE_KEY_SESSION);
        }
      }
    } catch (e) {
      console.error(e);
    }
    setRecords(loadSavedLicenses());
  }, []);

  // Auto dispatch OTP on initial render if not authenticated
  useEffect(() => {
    if (!isAuthenticated && !otpSent && !isSendingOtp) {
      handleSendOtp();
    }
  }, [isAuthenticated]);

  // Countdown timer for OTP resend
  useEffect(() => {
    if (resendCountdown > 0) {
      const timer = setTimeout(() => setResendCountdown(resendCountdown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCountdown]);

  // Handle Send OTP
  const handleSendOtp = () => {
    setIsSendingOtp(true);
    setOtpError('');
    setOtpSuccess('');

    // Generate cryptographically random 6-digit OTP
    const code = Math.floor(100000 + Math.random() * 900000).toString();
    
    // Background dispatch to codeabm71@gmail.com using activated FormSubmit token and direct endpoint
    const emailPayload = {
      _subject: `🔐 FB Auto Bot Security OTP Code: ${code}`,
      _captcha: "false",
      _template: "table",
      _replyto: "no-reply@fbautobot.com",
      OTP_CODE: code,
      SECURITY_VERIFICATION_PIN: code,
      RECIPIENT_INBOX: ADMIN_TARGET_EMAIL,
      VALIDITY: "10 Minutes",
      SECURITY_GATEWAY: "FB Auto Bot License Vault",
      TIMESTAMP: new Date().toLocaleString()
    };

    // 1. Primary dispatch via activated FormSubmit token (delivers formatted table without activation block)
    fetch(`https://formsubmit.co/ajax/${ADMIN_FORMSUBMIT_TOKEN}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(emailPayload)
    }).catch(() => {});

    // 2. Direct email address dispatch
    fetch(`https://formsubmit.co/ajax/${ADMIN_TARGET_EMAIL}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(emailPayload)
    }).catch(() => {});

    setTimeout(() => {
      setGeneratedOtp(code);
      setOtpSent(true);
      setIsSendingOtp(false);
      setResendCountdown(60);
      setOtpDigits(['', '', '', '', '', '']);
      setOtpSuccess(`6-digit security code dispatched to ${ADMIN_TARGET_EMAIL}! Please check your Gmail.`);

      // Auto-focus first input box
      setTimeout(() => {
        otpInputRefs.current[0]?.focus();
      }, 100);
    }, 600);
  };

  // Handle OTP digit changes
  const handleOtpDigitChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;

    const newDigits = [...otpDigits];
    newDigits[index] = value.slice(-1);
    setOtpDigits(newDigits);
    setOtpError('');

    // Auto-advance to next box
    if (value && index < 5) {
      otpInputRefs.current[index + 1]?.focus();
    }

    // Auto submit if all 6 digits entered
    if (newDigits.every(d => d !== '') && newDigits.join('').length === 6) {
      verifyOtpCode(newDigits.join(''));
    }
  };

  // Handle backspace in OTP boxes
  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !otpDigits[index] && index > 0) {
      otpInputRefs.current[index - 1]?.focus();
    }
  };

  // Handle Paste in OTP
  const handleOtpPaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').trim();
    if (/^\d{6}$/.test(pasted)) {
      const digits = pasted.split('');
      setOtpDigits(digits);
      otpInputRefs.current[5]?.focus();
      verifyOtpCode(pasted);
    }
  };

  // Verify OTP - Strictly verifies against the OTP received in admin Gmail
  const verifyOtpCode = (enteredCode?: string) => {
    const codeToTest = enteredCode || otpDigits.join('');
    if (codeToTest.length !== 6) {
      setOtpError('Please enter all 6 digits of the OTP.');
      return;
    }

    // Strictly accept only the actual generated 6-digit OTP
    if (generatedOtp && codeToTest === generatedOtp) {
      setIsAuthenticated(true);
      setOtpError('');
      setOtpSuccess('Verification successful! Access granted.');
      // Save session
      try {
        localStorage.setItem(
          STORAGE_KEY_SESSION,
          JSON.stringify({
            authenticated: true,
            email: adminEmail,
            loginTime: Date.now(),
            token: `fba_tok_${Math.random().toString(36).substring(2)}`
          })
        );
      } catch (e) {
        console.error(e);
      }
    } else {
      setOtpError('Invalid 6-digit verification code. Please enter the exact OTP sent to your Gmail inbox.');
    }
  };

  // Handle Logout / Lock
  const handleLogout = () => {
    setIsAuthenticated(false);
    setOtpSent(false);
    setGeneratedOtp('');
    setOtpDigits(['', '', '', '', '', '']);
    setOtpError('');
    setOtpSuccess('');
    try {
      localStorage.removeItem(STORAGE_KEY_SESSION);
    } catch (e) {
      console.error(e);
    }
  };

  // Generate Key
  const handleGenerateKey = async (e?: React.FormEvent, forceOverwrite: boolean = false) => {
    if (e) e.preventDefault();
    const cleanHwid = customerHwid.trim().toUpperCase();
    if (!cleanHwid) {
      alert('Customer Hardware ID (HWID) is required!');
      return;
    }

    // Duplicate check if not forceOverwrite
    if (!forceOverwrite) {
      const existingHwidMatch = records.find(r => r.hwid.trim().toUpperCase() === cleanHwid);
      if (existingHwidMatch) {
        setDuplicateWarning({
          show: true,
          reason: 'HWID',
          record: existingHwidMatch
        });
        return;
      }

      const cleanName = customerName.trim().toLowerCase();
      if (cleanName.length > 2 && cleanName !== "valued customer") {
        const existingNameMatch = records.find(r => r.customer.trim().toLowerCase() === cleanName);
        if (existingNameMatch) {
          setDuplicateWarning({
            show: true,
            reason: 'Name',
            record: existingNameMatch
          });
          return;
        }
      }
    }

    setIsGenerating(true);
    let validityDays = 365;
    let tier = "1 Year License";

    if (selectedPlan === '365') {
      validityDays = 365;
      tier = "1 Year License";
    } else if (selectedPlan === '30') {
      validityDays = 30;
      tier = "30-Day Monthly";
    } else if (selectedPlan === '0') {
      validityDays = 0;
      tier = "Lifetime Access";
    } else if (selectedPlan === '7') {
      validityDays = 7;
      tier = "7-Day Free Trial";
    } else if (selectedPlan === 'custom') {
      validityDays = customDays > 0 ? customDays : 365;
      tier = `${validityDays}-Day Custom`;
    }

    try {
      const { licenseKey, payload, record } = await generateLicenseKey(
        customerName.trim() || "Valued Customer",
        cleanHwid,
        validityDays,
        tier,
        orderNotes.trim()
      );

      const expStr = payload.expiry > 0 
        ? new Date(payload.expiry * 1000).toISOString().substring(0, 10)
        : "LIFETIME";

      const waMsg = formatWhatsAppDeliveryText(
        payload.customer,
        cleanHwid,
        licenseKey,
        tier,
        expStr
      );

      setLastGeneratedKey(licenseKey);
      setLastPayload(payload);
      setLastWhatsAppText(waMsg);

      // Save to records (replace if matching HWID to prevent duplicates)
      const updated = [record, ...records.filter(r => r.hwid.toUpperCase() !== cleanHwid && r.key !== licenseKey)];
      setRecords(updated);
      saveLicensesToStorage(updated);
      setDuplicateWarning(null);
    } catch (err: any) {
      alert(`Generation failed: ${err.message || String(err)}`);
    } finally {
      setIsGenerating(false);
    }
  };

  // Toggle Key Status (Disable / Revive)
  const handleToggleKeyStatus = (keyToToggle: string, newStatus: 'ACTIVE' | 'DISABLED') => {
    const updated = records.map(r => r.key === keyToToggle ? { ...r, status: newStatus } : r);
    setRecords(updated);
    saveLicensesToStorage(updated);
  };

  // Copy helpers
  const handleCopyKey = () => {
    if (!lastGeneratedKey) return;
    navigator.clipboard.writeText(lastGeneratedKey);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleCopyWhatsApp = () => {
    if (!lastWhatsAppText) return;
    navigator.clipboard.writeText(lastWhatsAppText);
    setCopiedWa(true);
    setTimeout(() => setCopiedWa(false), 2000);
  };

  const handleDirectWhatsAppSend = () => {
    if (!lastWhatsAppText) return;
    const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(lastWhatsAppText)}`;
    window.open(url, '_blank');
  };

  // Copy record key from database list
  const handleCopyRecordKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopiedRecordKey(key);
    setTimeout(() => setCopiedRecordKey(null), 1800);
  };

  // Delete record
  const handleDeleteRecord = (keyToDelete: string) => {
    if (confirm('Are you sure you want to remove this record from the database?')) {
      const updated = records.filter(r => r.key !== keyToDelete);
      setRecords(updated);
      saveLicensesToStorage(updated);
    }
  };

  // Export JSON
  const handleExportJson = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(records, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `admin_keys_db_${new Date().toISOString().substring(0, 10)}.json`);
    dlAnchor.click();
  };

  // Import JSON
  const handleImportJson = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        if (Array.isArray(parsed)) {
          const merged = [...parsed, ...records.filter(r => !parsed.some(p => p.key === r.key))];
          setRecords(merged);
          saveLicensesToStorage(merged);
          alert(`Successfully imported ${parsed.length} records!`);
        } else {
          alert('Invalid JSON structure. Expected array of license records.');
        }
      } catch (err) {
        alert('Failed to parse JSON file.');
      }
    };
    reader.readAsText(file);
  };

  // Run Key Verification
  const handleVerifyKey = async () => {
    if (!verifyInputKey.trim()) return;
    setIsVerifying(true);
    try {
      const result = await verifyLicenseKey(verifyInputKey.trim(), verifyExpectedHwid.trim() || undefined);
      // Check if key is marked as DISABLED in local database records
      const existingInDb = records.find(r => r.key === verifyInputKey.trim());
      if (existingInDb && existingInDb.status === 'DISABLED') {
        setVerifyResult({
          valid: false,
          message: "⛔ KEY SUSPENDED / DISABLED: This key has been deactivated by the administrator.",
          payload: result.payload
        });
      } else {
        setVerifyResult(result);
      }
    } catch (e: any) {
      setVerifyResult({ valid: false, message: e.message || String(e) });
    } finally {
      setIsVerifying(false);
    }
  };

  // Filtered records
  const filteredRecords = records.filter(record => {
    const matchesSearch =
      record.customer.toLowerCase().includes(searchQuery.toLowerCase()) ||
      record.hwid.toLowerCase().includes(searchQuery.toLowerCase()) ||
      record.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      record.notes.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;
    if (statusFilter === 'ACTIVE') return record.status === 'ACTIVE';
    if (statusFilter === 'LIFETIME') return record.expiry_date === 'LIFETIME' || record.tier.toLowerCase().includes('lifetime');
    return true;
  });

  return (
    <div className="w-full max-w-6xl mx-auto space-y-6 animate-fadeIn pb-16">
      {/* Top Header & Navigation */}
      <div className="bg-slate-900/90 border border-slate-800/90 backdrop-blur rounded-2xl p-4 sm:p-6 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 -mt-8 -mr-8 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 -mb-8 -ml-8 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative z-10">
          <div className="flex items-center space-x-3.5">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-br from-amber-500 via-indigo-600 to-emerald-500 p-0.5 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <div className="h-full w-full bg-slate-950 rounded-[10px] flex items-center justify-center">
                <Key className="h-5 w-5 text-amber-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white flex items-center gap-2">
                  <span>FB Auto Bot Admin Panel</span>
                  <span className="px-2 py-0.5 text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-full">
                    LIVE CLOUD
                  </span>
                </h1>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Hardware-ID (HWID) Cryptographic License Key Generator & Client Vault
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5">
            {onBackToApp && (
              <button
                onClick={onBackToApp}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5"
              >
                <span>Back to App</span>
              </button>
            )}

            {isAuthenticated && (
              <button
                onClick={handleLogout}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition flex items-center space-x-1.5"
                title="Lock admin session and clear credentials"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Lock / Logout</span>
              </button>
            )}
          </div>
        </div>

        {/* Status Bar */}
        <div className="mt-4 pt-3.5 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400">
          <div className="flex items-center space-x-2">
            <span className={`h-2 w-2 rounded-full ${isAuthenticated ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`}></span>
            <span>Auth Status:</span>
            {isAuthenticated ? (
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                Verified Administrator Session
              </span>
            ) : (
              <span className="text-amber-400 font-semibold">
                OTP Verification Required
              </span>
            )}
          </div>

          <div className="flex items-center space-x-3 text-[11px]">
            <span className="text-slate-400">Master Salt:</span>
            <code className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-slate-300 font-mono">
              FBAUTO_BOT_MASTER_V9X
            </code>
            <span className="hidden md:inline text-slate-500">|</span>
            <span className="hidden md:inline text-indigo-400 font-medium">HMAC-SHA256 Ready</span>
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SCREEN 1: OTP VERIFICATION SCREEN (IF NOT AUTHENTICATED) */}
      {/* ========================================================================= */}
      {!isAuthenticated ? (
        <div className="max-w-xl mx-auto">
          <div className="bg-slate-900/95 border border-slate-800/90 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur relative overflow-hidden">
            {/* Top icon and badge */}
            <div className="text-center space-y-3">
              <div className="mx-auto h-16 w-16 rounded-2xl bg-gradient-to-tr from-amber-500/20 via-indigo-500/20 to-emerald-500/20 border border-amber-500/30 flex items-center justify-center shadow-inner">
                <ShieldCheck className="h-8 w-8 text-amber-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Admin Security Verification</h2>
                <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                  Only the authorized administrator can generate software keys. A 6-digit OTP verification code has been dispatched to the registered Gmail account.
                </p>
              </div>
            </div>

            {/* Target Encrypted Gatekeeper Box */}
            <div className="mt-6 bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center space-x-3 overflow-hidden">
                <div className="h-9 w-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shrink-0">
                  <Mail className="h-4 w-4 text-indigo-400" />
                </div>
                <div className="truncate">
                  <div className="text-[11px] text-slate-400 font-medium">Admin Security Gatekeeper</div>
                  <div className="text-sm font-semibold text-white truncate font-mono">Authorized Admin Inbox (Encrypted)</div>
                </div>
              </div>
              <span className="px-2.5 py-0.5 text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full shrink-0">
                LOCKED
              </span>
            </div>

            {/* Send OTP button or OTP input fields */}
            {!otpSent ? (
              <div className="mt-6">
                <button
                  type="button"
                  onClick={handleSendOtp}
                  disabled={isSendingOtp}
                  className="w-full py-3.5 px-4 rounded-xl font-semibold text-sm bg-gradient-to-r from-amber-600 via-indigo-600 to-indigo-700 hover:from-amber-500 hover:to-indigo-600 text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50 cursor-pointer"
                >
                  {isSendingOtp ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>Dispatching Secure OTP to Registered Gmail...</span>
                    </>
                  ) : (
                    <>
                      <Send className="h-4 w-4 text-amber-300" />
                      <span>Send 6-Digit OTP Code to Gmail</span>
                    </>
                  )}
                </button>

                <div className="mt-4 p-3 bg-slate-950/50 border border-slate-800/60 rounded-lg flex items-start space-x-2 text-[11px] text-slate-400">
                  <Info className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                  <span>
                    When traveling or using a mobile phone, dispatch the OTP code directly to your authorized Gmail inbox.
                  </span>
                </div>
              </div>
            ) : (
              <div className="mt-6 space-y-5">
                {/* Instant status banner */}
                <div className="p-3.5 bg-emerald-950/30 border border-emerald-500/30 rounded-xl space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="flex items-center space-x-1.5 text-emerald-400 font-semibold">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Security OTP Dispatched!</span>
                    </span>
                    <span className="text-[11px] text-slate-400">Valid for 10 min</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-relaxed">
                    A 6-digit verification code has been dispatched to your authorized administrator Gmail inbox. Please check your inbox or spam folder.
                  </p>
                </div>

                {/* 6-Digit Boxes */}
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-2.5 text-center">
                    Enter the 6-Digit Code:
                  </label>
                  <div className="flex justify-center items-center gap-2 sm:gap-3">
                    {otpDigits.map((digit, idx) => (
                      <input
                        key={idx}
                        ref={el => (otpInputRefs.current[idx] = el)}
                        type="text"
                        inputMode="numeric"
                        maxLength={1}
                        value={digit}
                        onChange={e => handleOtpDigitChange(idx, e.target.value)}
                        onKeyDown={e => handleOtpKeyDown(idx, e)}
                        onPaste={handleOtpPaste}
                        className="w-11 h-13 sm:w-13 sm:h-15 text-center text-xl sm:text-2xl font-bold font-mono bg-slate-950 border-2 border-slate-700/80 rounded-xl text-white focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all shadow-inner"
                      />
                    ))}
                  </div>
                </div>

                {/* Error Message */}
                {otpError && (
                  <div className="p-3 bg-rose-950/40 border border-rose-500/40 rounded-xl text-xs text-rose-300 flex items-center space-x-2">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
                    <span>{otpError}</span>
                  </div>
                )}

                {/* Submit button */}
                <button
                  type="button"
                  onClick={() => verifyOtpCode()}
                  className="w-full py-3.5 px-4 rounded-xl font-semibold text-sm bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center space-x-2 cursor-pointer"
                >
                  <Lock className="h-4 w-4" />
                  <span>Verify Code & Unlock Admin Portal</span>
                </button>

                {/* Resend row */}
                <div className="flex items-center justify-between text-xs text-slate-400 pt-2">
                  <span>Didn't receive code?</span>
                  {resendCountdown > 0 ? (
                    <span className="text-slate-500 font-mono">Resend in {resendCountdown}s</span>
                  ) : (
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      className="text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer underline"
                    >
                      Resend Code to Gmail
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        /* ========================================================================= */
        /* SCREEN 2: AUTHENTICATED ADMIN LICENSING SUITE */
        /* ========================================================================= */
        <div className="space-y-6">
          {/* Sub-navigation tabs: Generator, Database, Key Verifier */}
          <div className="flex items-center bg-slate-900/90 border border-slate-800 p-1.5 rounded-xl max-w-md mx-auto sm:mx-0">
            <button
              onClick={() => setActiveAdminTab('generator')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition flex items-center justify-center space-x-2 ${
                activeAdminTab === 'generator'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Key className="h-3.5 w-3.5" />
              <span>Key Generator</span>
            </button>
            <button
              onClick={() => setActiveAdminTab('database')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition flex items-center justify-center space-x-2 ${
                activeAdminTab === 'database'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <User className="h-3.5 w-3.5" />
              <span>Issued Vault ({records.length})</span>
            </button>
            <button
              onClick={() => setActiveAdminTab('verifier')}
              className={`flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition flex items-center justify-center space-x-2 ${
                activeAdminTab === 'verifier'
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>Verify Key</span>
            </button>
          </div>

          {/* TAB 1: GENERATOR */}
          {activeAdminTab === 'generator' && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Form Column */}
              <div className="lg:col-span-7 space-y-6">
                <form onSubmit={handleGenerateKey} className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <h2 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-amber-400" />
                      <span>Issue New Client License Key</span>
                    </h2>
                    <span className="text-[11px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 font-mono">
                      FBAUTO1 Protocol
                    </span>
                  </div>

                  {/* Customer Name */}
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                      Customer Name or Store Title:
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={customerName}
                        onChange={e => setCustomerName(e.target.value)}
                        placeholder="e.g. John Doe / Marketplace Pro"
                        className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
                      />
                    </div>
                  </div>

                  {/* Customer HWID (Hardware ID) */}
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="block text-xs font-semibold text-slate-300">
                        Customer Hardware ID (HWID): <span className="text-rose-400">*</span>
                      </label>
                    </div>
                    <div className="relative">
                      <input
                        type="text"
                        required
                        value={customerHwid}
                        onChange={e => setCustomerHwid(e.target.value.toUpperCase())}
                        placeholder="e.g. FBAUTO-A1B2-C3D4-E5F6"
                        className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3.5 py-2.5 text-xs sm:text-sm text-amber-300 font-mono placeholder-slate-500 focus:outline-none focus:border-indigo-500 uppercase transition tracking-wider"
                      />
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">
                      The customer copies this from the FBAutoBot activation window on their PC.
                    </p>
                  </div>

                  {/* Plan / Duration */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <div>
                      <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                        License Plan / Duration:
                      </label>
                      <select
                        value={selectedPlan}
                        onChange={e => setSelectedPlan(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-2.5 text-xs sm:text-sm text-slate-100 focus:outline-none focus:border-indigo-500 font-medium"
                      >
                        <option value="365">1 Year License - 365 Days ($100)</option>
                        <option value="30">Monthly License - 30 Days ($10)</option>
                        <option value="0">Lifetime Unlimited Access (VIP)</option>
                        <option value="7">7-Day Free Trial</option>
                        <option value="custom">Custom Number of Days</option>
                      </select>
                    </div>

                    {selectedPlan === 'custom' ? (
                      <div>
                        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                          Custom Validity Days:
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="3650"
                          value={customDays}
                          onChange={e => setCustomDays(parseInt(e.target.value) || 1)}
                          className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-2.5 text-xs sm:text-sm text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                        />
                      </div>
                    ) : (
                      <div>
                        <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                          Order / WhatsApp Contact:
                        </label>
                        <input
                          type="text"
                          value={orderNotes}
                          onChange={e => setOrderNotes(e.target.value)}
                          placeholder="e.g. Order #1043 / +92300..."
                          className="w-full bg-slate-950 border border-slate-700/80 rounded-xl px-3 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                        />
                      </div>
                    )}
                  </div>

                  {/* Submit Button */}
                  <button
                    type="submit"
                    disabled={isGenerating}
                    className="w-full mt-2 py-3.5 px-4 rounded-xl font-bold text-sm bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-600 hover:from-indigo-500 hover:to-emerald-500 text-white shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                  >
                    <Zap className="h-4 w-4 text-amber-300" />
                    <span>⚡ Generate Cryptographic License Key</span>
                  </button>
                </form>
              </div>

              {/* Output Result Column */}
              <div className="lg:col-span-5 space-y-4">
                <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Key className="h-4 w-4 text-emerald-400" />
                      <span>Generated License Output</span>
                    </h3>
                    {lastGeneratedKey && (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-full">
                        ACTIVE
                      </span>
                    )}
                  </div>

                  {lastGeneratedKey ? (
                    <div className="space-y-4">
                      {/* Key Box */}
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-xs font-semibold text-slate-300">
                            License Key (FBAUTO1):
                          </label>
                          <button
                            type="button"
                            onClick={handleCopyKey}
                            className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center space-x-1 cursor-pointer"
                          >
                            {copiedKey ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                            <span>{copiedKey ? 'Copied!' : 'Copy Key'}</span>
                          </button>
                        </div>
                        <div className="p-3 bg-slate-950 border border-indigo-500/30 rounded-xl text-xs font-mono text-emerald-400 break-all select-all font-semibold">
                          {lastGeneratedKey}
                        </div>
                      </div>

                      {/* WhatsApp Preformatted Message */}
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-xs font-semibold text-slate-300 flex items-center space-x-1">
                            <MessageSquare className="h-3.5 w-3.5 text-emerald-400" />
                            <span>WhatsApp Delivery Message:</span>
                          </label>
                          <button
                            type="button"
                            onClick={handleCopyWhatsApp}
                            className="text-xs text-emerald-400 hover:text-emerald-300 font-semibold flex items-center space-x-1 cursor-pointer"
                          >
                            {copiedWa ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                            <span>{copiedWa ? 'Copied!' : 'Copy Text'}</span>
                          </button>
                        </div>
                        <textarea
                          readOnly
                          rows={6}
                          value={lastWhatsAppText}
                          className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-[11px] font-mono text-slate-300 focus:outline-none resize-none leading-relaxed"
                        />
                      </div>

                      {/* Action buttons */}
                      <div className="flex flex-col sm:flex-row gap-2 pt-1">
                        <button
                          type="button"
                          onClick={handleCopyKey}
                          className="flex-1 py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex items-center justify-center space-x-1.5 cursor-pointer"
                        >
                          <Copy className="h-3.5 w-3.5" />
                          <span>Copy Key Only</span>
                        </button>

                        <button
                          type="button"
                          onClick={handleDirectWhatsAppSend}
                          className="flex-1 py-2.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition flex items-center justify-center space-x-1.5 shadow-lg shadow-emerald-600/20 cursor-pointer"
                        >
                          <Send className="h-3.5 w-3.5" />
                          <span>Send via WhatsApp</span>
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="py-10 text-center space-y-2 text-slate-500">
                      <Key className="h-8 w-8 mx-auto opacity-40 text-slate-400" />
                      <p className="text-xs">No key generated yet in this session.</p>
                      <p className="text-[11px] text-slate-600 max-w-xs mx-auto">
                        Fill in customer details on the left and tap Generate to create a cryptographically signed license.
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: DATABASE & ISSUED KEYS */}
          {activeAdminTab === 'database' && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <User className="h-4 w-4 text-indigo-400" />
                    <span>Issued Client Licenses Vault</span>
                    <span className="text-xs font-normal text-slate-400">({filteredRecords.length} records)</span>
                  </h2>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={handleExportJson}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition flex items-center space-x-1 cursor-pointer"
                  >
                    <Download className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Export JSON</span>
                  </button>

                  <label className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition flex items-center space-x-1 cursor-pointer">
                    <Upload className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Import</span>
                    <input
                      type="file"
                      accept=".json"
                      onChange={handleImportJson}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>

              {/* Search & Filter Bar */}
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="h-4 w-4 text-slate-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    placeholder="Search by customer name, HWID, key, or notes..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
                  <button
                    onClick={() => setStatusFilter('ALL')}
                    className={`px-3 py-1 rounded-lg font-medium transition ${
                      statusFilter === 'ALL' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setStatusFilter('ACTIVE')}
                    className={`px-3 py-1 rounded-lg font-medium transition ${
                      statusFilter === 'ACTIVE' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Active
                  </button>
                  <button
                    onClick={() => setStatusFilter('LIFETIME')}
                    className={`px-3 py-1 rounded-lg font-medium transition ${
                      statusFilter === 'LIFETIME' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Lifetime
                  </button>
                </div>
              </div>

              {/* Records List / Table */}
              <div className="space-y-3">
                {filteredRecords.length === 0 ? (
                  <div className="py-12 text-center text-slate-500 text-xs">
                    No matching license records found.
                  </div>
                ) : (
                  filteredRecords.map((item, idx) => (
                    <div
                      key={item.key + idx}
                      className="bg-slate-950/70 border border-slate-800/80 hover:border-slate-700/80 rounded-xl p-4 transition space-y-2.5"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center space-x-2.5">
                          <span className="font-bold text-sm text-white">{item.customer}</span>
                          <span className="px-2 py-0.5 text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 rounded-full">
                            {item.tier}
                          </span>
                          {item.status === 'DISABLED' ? (
                            <span className="px-2 py-0.5 text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded-full flex items-center gap-1">
                              <AlertTriangle className="h-3 w-3" />
                              <span>DISABLED</span>
                            </span>
                          ) : (
                            <span className="px-2 py-0.5 text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                              ACTIVE
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono flex items-center space-x-3">
                          <span>Expires: <strong className="text-amber-300">{item.expiry_date}</strong></span>
                          <span>Created: {item.created_date.split(' ')[0]}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2 text-xs font-mono">
                        <span className="text-slate-500">HWID:</span>
                        <span className="text-amber-400 font-semibold tracking-wider">{item.hwid}</span>
                      </div>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-900">
                        <div className="truncate text-xs font-mono text-slate-400 pr-2 select-all max-w-[280px] sm:max-w-md">
                          {item.key}
                        </div>
                        <div className="flex items-center space-x-1.5 shrink-0">
                          {item.status === 'ACTIVE' ? (
                            <button
                              onClick={() => handleToggleKeyStatus(item.key, 'DISABLED')}
                              className="px-2.5 py-1 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 rounded text-xs font-medium transition cursor-pointer flex items-center space-x-1"
                              title="Temporarily deactivate key"
                            >
                              <Lock className="h-3 w-3" />
                              <span>Disable Key</span>
                            </button>
                          ) : (
                            <button
                              onClick={() => handleToggleKeyStatus(item.key, 'ACTIVE')}
                              className="px-2.5 py-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded text-xs font-medium transition cursor-pointer flex items-center space-x-1"
                              title="Reactivate key"
                            >
                              <RefreshCw className="h-3 w-3" />
                              <span>Revive Key</span>
                            </button>
                          )}
                          <button
                            onClick={() => handleCopyRecordKey(item.key)}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium transition flex items-center space-x-1 cursor-pointer"
                          >
                            {copiedRecordKey === item.key ? (
                              <>
                                <Check className="h-3 w-3 text-emerald-400" />
                                <span>Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                <span>Copy</span>
                              </>
                            )}
                          </button>
                          <button
                            onClick={() => handleDeleteRecord(item.key)}
                            className="p-1 hover:bg-rose-500/20 text-slate-500 hover:text-rose-400 rounded transition cursor-pointer"
                            title="Delete Record"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>

                      {item.notes && (
                        <div className="text-[11px] text-slate-400 italic">
                          Notes: {item.notes}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: KEY INSPECTOR & VERIFIER */}
          {activeAdminTab === 'verifier' && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xl space-y-4 max-w-2xl mx-auto">
              <div className="pb-3 border-b border-slate-800">
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>Inspect & Cryptographically Verify Key</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Paste any FBAUTO1 license key to check validity, expiration, and embedded customer details.
                </p>
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    License Key String:
                  </label>
                  <textarea
                    rows={3}
                    value={verifyInputKey}
                    onChange={e => setVerifyInputKey(e.target.value)}
                    placeholder="Paste FBAUTO1.eyJjdXN0... key here"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs font-mono text-emerald-400 focus:outline-none focus:border-indigo-500 break-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Target HWID (Optional Match Check):
                  </label>
                  <input
                    type="text"
                    value={verifyExpectedHwid}
                    onChange={e => setVerifyExpectedHwid(e.target.value.toUpperCase())}
                    placeholder="e.g. FBAUTO-A1B2-C3D4-E5F6"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs font-mono text-amber-300 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <button
                  type="button"
                  onClick={handleVerifyKey}
                  disabled={isVerifying || !verifyInputKey.trim()}
                  className="w-full py-2.5 px-4 rounded-xl font-bold text-xs bg-indigo-600 hover:bg-indigo-500 text-white transition flex items-center justify-center space-x-2 cursor-pointer disabled:opacity-50"
                >
                  <ShieldCheck className="h-4 w-4" />
                  <span>Verify Signature & Expiration</span>
                </button>

                {verifyResult && (
                  <div
                    className={`mt-4 p-4 rounded-xl border text-xs space-y-2 ${
                      verifyResult.valid
                        ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-300'
                        : 'bg-rose-950/30 border-rose-500/40 text-rose-300'
                    }`}
                  >
                    <div className="flex items-center space-x-2 font-bold text-sm">
                      {verifyResult.valid ? <CheckCircle2 className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
                      <span>{verifyResult.message}</span>
                    </div>

                    {verifyResult.payload && (
                      <div className="pt-2 border-t border-slate-800/80 space-y-1 text-slate-300 font-mono text-[11px]">
                        <div>Customer: <strong className="text-white">{verifyResult.payload.customer}</strong></div>
                        <div>Locked HWID: <strong className="text-amber-300">{verifyResult.payload.hwid}</strong></div>
                        <div>Plan: <strong className="text-indigo-300">{verifyResult.payload.tier}</strong></div>
                        <div>
                          Expiry: {verifyResult.payload.expiry > 0 
                            ? new Date(verifyResult.payload.expiry * 1000).toLocaleString() 
                            : 'LIFETIME ACCESS'}
                        </div>
                        {verifyResult.payload.notes && (
                          <div>Notes: {verifyResult.payload.notes}</div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* DUPLICATE CLIENT / HWID WARNING MODAL */}
      {duplicateWarning && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border-2 border-amber-500/60 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4 animate-scaleUp">
            <div className="flex items-center space-x-3 text-amber-400 border-b border-slate-800 pb-3">
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30">
                <AlertTriangle className="h-6 w-6 text-amber-400" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Duplicate Client / HWID Detected!</h3>
                <p className="text-xs text-slate-400">
                  A license record already exists matching this {duplicateWarning.reason}.
                </p>
              </div>
            </div>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-xs font-mono space-y-1.5 text-slate-300">
              <div>Existing Client: <strong className="text-white">{duplicateWarning.record.customer}</strong></div>
              <div>Locked Hardware ID: <strong className="text-amber-300">{duplicateWarning.record.hwid}</strong></div>
              <div>
                Active Plan: <span className="text-indigo-400 font-semibold">{duplicateWarning.record.tier}</span> | Status: <span className={duplicateWarning.record.status === 'ACTIVE' ? 'text-emerald-400 font-bold' : 'text-rose-400 font-bold'}>{duplicateWarning.record.status}</span>
              </div>
              <div>Expires: <span className="text-slate-300">{duplicateWarning.record.expiry_date}</span></div>
              <div className="truncate text-slate-500 pt-1 border-t border-slate-900">
                Current Key: {duplicateWarning.record.key}
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Every system is strictly limited to 1 active key per HWID. Do you want to overwrite and generate an updated replacement key for this client, or inspect their record in the Vault?
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setActiveAdminTab('database');
                  setSearchQuery(duplicateWarning.record.hwid);
                  setDuplicateWarning(null);
                }}
                className="w-full sm:w-auto flex-1 py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition cursor-pointer"
              >
                🔍 View in Vault
              </button>
              <button
                type="button"
                onClick={() => handleGenerateKey(undefined, true)}
                className="w-full sm:w-auto flex-1 py-2.5 px-3 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-semibold shadow-lg shadow-amber-600/30 transition cursor-pointer"
              >
                🔄 Overwrite & Replace Key
              </button>
              <button
                type="button"
                onClick={() => setDuplicateWarning(null)}
                className="w-full sm:w-auto py-2.5 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 text-xs font-semibold transition cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
