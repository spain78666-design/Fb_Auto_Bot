import React, { useState } from 'react';
import {
  Terminal,
  Cpu,
  Users,
  Bot,
  Sparkles,
  Settings,
  Play,
  Square,
  CheckCircle2,
  AlertTriangle,
  FolderTree,
  FileCode,
  Copy,
  ShieldCheck,
  Layers,
  Activity,
  Image as ImageIcon,
  Check,
  Eye,
  Sliders,
  Database,
  Globe,
  ExternalLink,
  Zap,
  Cloud
} from 'lucide-react';
import { browserBotCodeSnippet, appPyCodeSnippet, imageProcessorSnippet, sessionManagerSnippet, aiSpinnerSnippet, requirementsSnippet, landingPageSnippet } from './data/codeSnippets';

export default function App() {
  const [activeTab, setActiveTab] = useState<'desktop-sim' | 'landing-page' | 'code-viewer' | 'roadmap'>('landing-page');
  const [simActivePage, setSimActivePage] = useState<'dashboard' | 'accounts' | 'automation' | 'ai' | 'settings'>('ai');
  const [selectedFile, setSelectedFile] = useState<'landing_page/index.html' | 'ai_spinner.py' | 'session_manager.py' | 'browser_bot.py' | 'image_processor.py' | 'app.py' | 'requirements.txt'>('landing_page/index.html');
  const [copiedCode, setCopiedCode] = useState(false);

  // Simulated GUI State
  const [simTitle, setSimTitle] = useState('Apple iPhone 15 Pro Max 256GB Titanium');
  const [simPrice, setSimPrice] = useState('950');
  const [simCategory, setSimCategory] = useState('Electronics & Computers');
  const [simLocation, setSimLocation] = useState('Los Angeles, CA');
  const [simDescription, setSimDescription] = useState('Brand new sealed box, never opened. Direct factory unlocked. Available for immediate pickup or same-day dropoff.');
  const [simSpeed, setSimSpeed] = useState('Normal (15-30s)');
  const [antiDupShield, setAntiDupShield] = useState(true);
  const [antiDupRotate, setAntiDupRotate] = useState(true);
  const [wipeExif, setWipeExif] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simProgress, setSimProgress] = useState(0);

  // Phase 5: Simulated AI Spinner State
  const [aiSeed, setAiSeed] = useState('Apple iPhone 15 Pro Max 256GB Titanium');
  const [aiBaseDesc, setAiBaseDesc] = useState('Factory sealed in original box. Never opened. 1-year official Apple warranty. Includes braided USB-C cable. Available for immediate local pickup or tracked shipping.');
  const [aiTone, setAiTone] = useState<'Casual & Friendly' | 'Professional & Transparent' | 'Urgent Clearance / Deal'>('Casual & Friendly');
  const [aiApiKey, setAiApiKey] = useState('');
  const [aiGeneratedTitles, setAiGeneratedTitles] = useState<string[]>([
    'Apple iPhone 15 Pro Max 256GB Titanium - Brand New Sealed (Quick Sale)',
    'Authentic Apple iPhone 15 Pro Max 256GB Titanium [Factory Sealed / Unopened]',
    '🔥 Deal: Apple iPhone 15 Pro Max 256GB Titanium - Ready for Pickup / Fast Shipping',
    '[Must Go!] Apple iPhone 15 Pro Max 256GB Titanium - Best Offer Takes It'
  ]);
  const [aiGeneratedDesc, setAiGeneratedDesc] = useState<string>(
    `Up for sale is an authentic Apple iPhone 15 Pro Max 256GB Titanium in factory sealed condition.\n\n` +
    `• Condition: 100% Brand New in unopened original packaging\n` +
    `• Warranty: Full 1-year Apple manufacturer warranty ready to activate upon setup\n` +
    `• Package: Includes OEM braided USB-C charging cable & documentation\n` +
    `• Logistics: Safe public meetup / same-day local pickup available, or insured express postage\n` +
    `• Payment: Cash, Zelle, or secure digital transfer accepted\n\n` +
    `Priced fairly for a hassle-free transaction. Serious inquiries only please!`
  );

  const [simLogs, setSimLogs] = useState<Array<{ time: string; level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR'; msg: string }>>([
    { time: '03:40:10', level: 'INFO', msg: 'FB Auto Bot v5.0 initialized. Phase 5 AI Content Spinner & Spintax Engine loaded.' },
    { time: '03:40:12', level: 'INFO', msg: 'Anti-Detect: navigator.webdriver masked, WebGL Intel Iris Xe spoofed, Canvas noise active.' },
    { time: '03:40:15', level: 'SUCCESS', msg: 'SessionManager: Isolated profiles & proxy bindings verified.' },
    { time: '03:40:18', level: 'SUCCESS', msg: 'AI Engine: Gemini API connector initialized with fallback SpintaxEngine.' },
    { time: '03:40:20', level: 'INFO', msg: 'Ready to automate Facebook Marketplace with unique AI copy: /marketplace/create/item' }
  ]);

  const runSimulation = () => {
    if (isSimulating) return;
    setIsSimulating(true);
    setSimProgress(5);
    
    const addLog = (level: 'INFO' | 'SUCCESS' | 'WARNING' | 'ERROR', msg: string) => {
      const now = new Date().toLocaleTimeString('en-GB');
      setSimLogs(prev => [...prev, { time: now, level, msg }]);
    };

    addLog('INFO', `[Playwright] Booting Chromium in stealth mode (Speed: ${simSpeed})...`);

    setTimeout(() => {
      setSimProgress(15);
      addLog('INFO', `Injected 2 auth cookies (c_user=100084..., xs=29%3A...) via browser_context.add_cookies()`);
      addLog('INFO', `Routing traffic through SOCKS5 proxy: socks5://185.199.229.15:8080`);
    }, 700);

    setTimeout(() => {
      setSimProgress(30);
      addLog('SUCCESS', `Session Health Check passed: Facebook profile authenticated without checkpoints.`);
    }, 1500);

    // Phase 3: Anti-Duplicate Image Engine processing
    setTimeout(() => {
      setSimProgress(45);
      if (antiDupShield) {
        addLog('INFO', '🛡️ Anti-Duplicate Image Shield ACTIVE: Initializing OpenCV & Pillow pipeline...');
        addLog('INFO', 'Processing image 1/2: iphone_front.jpg [Micro-rotated: +0.38°, 2% contrast jitter]');
        addLog('SUCCESS', ' -> EXIF & GPS metadata purged. 1px border padding added.');
        addLog('SUCCESS', ' -> iphone_front.jpg: Old MD5 4f81c9a... -> New MD5 a2b79e1... (100% Unique Fingerprint)');
        addLog('INFO', 'Processing image 2/2: iphone_back.jpg [Micro-rotated: -0.29°, 2% brightness jitter]');
        addLog('SUCCESS', ' -> iphone_back.jpg: Old MD5 e102b4d... -> New MD5 9c34d8f... (100% Unique Fingerprint)');
        addLog('SUCCESS', 'Batch complete: 2 unique images saved to temp_uploads/ -> Ready for Marketplace injection');
      } else {
        addLog('INFO', 'Anti-duplicate shield bypassed: using original source images.');
      }
    }, 2400);

    setTimeout(() => {
      setSimProgress(65);
      addLog('INFO', `Navigating stealthily to https://www.facebook.com/marketplace/create/item...`);
      addLog('INFO', `Uploading 2 unique image files via page.set_input_files() [temp_uploads/fbv_*.jpg]`);
    }, 3800);

    setTimeout(() => {
      setSimProgress(80);
      addLog('INFO', `Emulating human keystrokes (80-220ms per char) for Title: "${simTitle}"`);
      addLog('INFO', `Setting Price: $${simPrice} | Category: ${simCategory} | Condition: New`);
    }, 4900);

    setTimeout(() => {
      setSimProgress(92);
      addLog('INFO', `Configuring Location: "${simLocation}". Selected dropdown via ArrowDown + Enter.`);
      addLog('INFO', `Advancing through Next -> Clicking Publish button.`);
    }, 5900);

    setTimeout(() => {
      setSimProgress(100);
      addLog('SUCCESS', `Facebook Marketplace listing "${simTitle}" published successfully with unique image fingerprints!`);
      setIsSimulating(false);
    }, 6900);
  };

  const clearLogs = () => {
    setSimLogs([
      { time: new Date().toLocaleTimeString('en-GB'), level: 'INFO', msg: 'Console buffer cleared.' }
    ]);
    setSimProgress(0);
  };

  const copyCodeToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-600 selection:text-white">
      {/* Top Application Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/90 backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold tracking-tight text-white">FB Auto Bot</h1>
              <span className="px-2 py-0.5 text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full">
                Phase 3: Anti-Duplicate Engine Active
              </span>
            </div>
            <p className="text-xs text-slate-400">Enterprise Facebook Marketplace Automation Suite</p>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center bg-slate-950/80 p-1 rounded-lg border border-slate-800">
          <button
            id="tab-landing-page"
            onClick={() => setActiveTab('landing-page')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'landing-page'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Globe className="h-3.5 w-3.5 text-emerald-400" />
            <span>Sales Landing Page</span>
            <span className="px-1.5 py-0.2 text-[9px] bg-emerald-500/20 text-emerald-300 rounded font-mono font-bold">Phase 6</span>
          </button>
          <button
            id="tab-desktop-sim"
            onClick={() => setActiveTab('desktop-sim')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'desktop-sim'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Eye className="h-3.5 w-3.5" />
            <span>Interactive GUI Simulator</span>
          </button>
          <button
            id="tab-code-viewer"
            onClick={() => setActiveTab('code-viewer')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'code-viewer'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="h-3.5 w-3.5" />
            <span>Project Code Vault</span>
          </button>
          <button
            id="tab-roadmap"
            onClick={() => setActiveTab('roadmap')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'roadmap'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Project Roadmap</span>
          </button>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {activeTab === 'desktop-sim' && (
          <div className="space-y-4">
            {/* Context bar */}
            <div className="flex flex-wrap items-center justify-between bg-slate-900/60 border border-slate-800/80 rounded-xl px-4 py-3 text-xs text-slate-300">
              <div className="flex items-center space-x-2">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className="font-semibold text-slate-200">PyQt5 Window Preview:</span>
                <span className="text-slate-400">This interactive workbench reflects the layout, controls, and dark theme of the PyQt5 desktop app (`desktop_app/app.py`).</span>
              </div>
              <div className="flex items-center space-x-3 mt-2 sm:mt-0">
                <span className="text-slate-400">Run locally:</span>
                <code className="bg-slate-950 px-2 py-0.5 rounded border border-slate-800 text-indigo-300 font-mono text-[11px]">
                  python desktop_app/app.py
                </code>
              </div>
            </div>

            {/* Simulated Desktop Window Frame */}
            <div className="rounded-2xl border border-slate-700/80 bg-slate-900/90 shadow-2xl shadow-black/80 overflow-hidden flex flex-col min-h-[680px]">
              {/* Fake Window Titlebar */}
              <div className="bg-slate-950 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between select-none">
                <div className="flex items-center space-x-2">
                  <div className="h-3 w-3 rounded-full bg-red-500/80 border border-red-600/50"></div>
                  <div className="h-3 w-3 rounded-full bg-yellow-500/80 border border-yellow-600/50"></div>
                  <div className="h-3 w-3 rounded-full bg-green-500/80 border border-green-600/50"></div>
                  <span className="ml-3 text-xs font-medium text-slate-400">FB Auto Bot - Facebook Marketplace Automation Suite (PyQt5)</span>
                </div>
                <div className="flex items-center space-x-2 text-[11px] text-slate-500">
                  <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-emerald-400 font-mono">
                    ONLINE • STEALTH V2.4
                  </span>
                </div>
              </div>

              {/* Window Content (Sidebar + Main View + Console) */}
              <div className="flex flex-1 overflow-hidden">
                {/* 1. PyQt5 Sidebar */}
                <aside className="w-60 bg-slate-950/90 border-r border-slate-800/80 p-4 flex flex-col justify-between shrink-0">
                  <div className="space-y-6">
                    <div className="flex items-center space-x-2.5 px-2">
                      <div className="p-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                        <Bot className="h-5 w-5" />
                      </div>
                      <div>
                        <div className="font-extrabold text-sm text-white tracking-tight">FB Auto Bot</div>
                        <div className="text-[10px] text-indigo-400 font-semibold tracking-wider">ENTERPRISE EDITION</div>
                      </div>
                    </div>

                    {/* Nav List */}
                    <nav className="space-y-1.5">
                      {[
                        { id: 'dashboard', label: 'Dashboard', icon: Activity },
                        { id: 'accounts', label: 'Accounts Manager', icon: Users },
                        { id: 'automation', label: 'Automation Engine', icon: Bot },
                        { id: 'ai', label: 'AI Content Spinner', icon: Sparkles },
                        { id: 'settings', label: 'Settings & Stealth', icon: Settings },
                      ].map(item => {
                        const Icon = item.icon;
                        const isSelected = simActivePage === item.id;
                        return (
                          <button
                            key={item.id}
                            id={`sim-nav-${item.id}`}
                            onClick={() => setSimActivePage(item.id as any)}
                            className={`w-full flex items-center space-x-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                              isSelected
                                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                            }`}
                          >
                            <Icon className="h-4 w-4" />
                            <span>{item.label}</span>
                          </button>
                        );
                      })}
                    </nav>
                  </div>

                  {/* Engine Status Card */}
                  <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800/90 space-y-1">
                    <div className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Stealth Status</div>
                    <div className="flex items-center space-x-2">
                      <span className={`h-2 w-2 rounded-full ${isSimulating ? 'bg-amber-400 animate-ping' : 'bg-emerald-400'}`}></span>
                      <span className={`text-xs font-bold ${isSimulating ? 'text-amber-300' : 'text-emerald-400'}`}>
                        {isSimulating ? 'POSTING IN PROGRESS' : 'READY FOR TASKS'}
                      </span>
                    </div>
                  </div>
                </aside>

                {/* 2. Main Tab View Area */}
                <div className="flex-1 flex flex-col overflow-y-auto bg-slate-900/60 p-5 space-y-4">
                  {/* TAB: AUTOMATION ENGINE */}
                  {simActivePage === 'automation' && (
                    <div className="space-y-4">
                      <div>
                        <h2 className="text-lg font-bold text-white tracking-tight">Marketplace Automation Engine</h2>
                        <p className="text-xs text-slate-400">Configure listing metadata, tune humanized delays, and trigger automated posting.</p>
                      </div>

                      {/* Main Form Box */}
                      <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-4">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Target Facebook Account Profile</label>
                            <select
                              id="input-sim-account"
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                            >
                              <option>🟢 ShopUSA_MainProfile [Healthy] (185.199.229.15:8080)</option>
                              <option>🟢 Backup_Store_UK [Healthy] (Direct Residential)</option>
                              <option>⚡ All Healthy Accounts (Sequential Multi-Post Batch)</option>
                            </select>
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Marketplace Category</label>
                            <select
                              id="input-sim-category"
                              value={simCategory}
                              onChange={e => setSimCategory(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                            >
                              <option>Electronics & Computers</option>
                              <option>Home & Kitchen</option>
                              <option>Tools & Appliances</option>
                              <option>Vehicles & Parts</option>
                              <option>Furniture & Decor</option>
                            </select>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                          <div className="md:col-span-3">
                            <div className="flex items-center justify-between mb-1.5">
                              <label className="block text-xs font-semibold text-slate-300">Product Title (Max 100 characters)</label>
                              <button
                                type="button"
                                onClick={() => {
                                  const pool = [
                                    `Apple iPhone 15 Pro Max 256GB Titanium - Brand New Sealed (Quick Sale)`,
                                    `Authentic Apple iPhone 15 Pro Max 256GB Titanium [Factory Sealed / Unopened]`,
                                    `🔥 Deal: Apple iPhone 15 Pro Max 256GB Titanium - Ready for Pickup / Fast Shipping`,
                                    `[Must Go!] Apple iPhone 15 Pro Max 256GB Titanium - Best Offer Takes It`
                                  ];
                                  const spun = pool[Math.floor(Math.random() * pool.length)];
                                  setSimTitle(spun);
                                  const now = new Date().toLocaleTimeString('en-GB');
                                  setSimLogs(prev => [
                                    ...prev,
                                    { time: now, level: 'INFO', msg: `✨ Auto-Spin: Triggered Gemini / Spintax Engine for Title...` },
                                    { time: now, level: 'SUCCESS', msg: `✨ Title spun into: "${spun}"` }
                                  ]);
                                }}
                                className="flex items-center space-x-1 px-2 py-0.5 rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-[10px] font-semibold transition-colors"
                              >
                                <Sparkles className="h-3 w-3 text-indigo-400" />
                                <span>✨ Auto-Spin via AI</span>
                              </button>
                            </div>
                            <input
                              id="input-sim-title"
                              type="text"
                              value={simTitle}
                              onChange={e => setSimTitle(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                              placeholder="e.g., iPhone 15 Pro Max 256GB Titanium"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Price ($ USD)</label>
                            <input
                              id="input-sim-price"
                              type="text"
                              value={simPrice}
                              onChange={e => setSimPrice(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-mono"
                              placeholder="950"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-300 mb-1.5">Target Location / City (Postal Code / Radius)</label>
                          <input
                            id="input-sim-location"
                            type="text"
                            value={simLocation}
                            onChange={e => setSimLocation(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                            placeholder="e.g. Los Angeles, CA or 90210"
                          />
                        </div>

                        <div>
                          <div className="flex items-center justify-between mb-1.5">
                            <label className="block text-xs font-semibold text-slate-300">Product Description</label>
                            <button
                              type="button"
                              onClick={() => {
                                const spun = `Up for sale is an authentic ${simTitle}.\n\n` +
                                  `• Condition: 100% Brand New in factory sealed packaging (never unboxed)\n` +
                                  `• Specifications: 256GB storage, clean serial, full 1-year manufacturer warranty\n` +
                                  `• Accessories: Includes original OEM braided charging cable\n` +
                                  `• Logistics: Local pickup at safe public point or tracked express shipping\n` +
                                  `• Terms: Cash or digital transfer on pickup. No trades.\n\n` +
                                  `First come first served. Message for immediate meetup details!`;
                                setSimDescription(spun);
                                const now = new Date().toLocaleTimeString('en-GB');
                                setSimLogs(prev => [
                                  ...prev,
                                  { time: now, level: 'INFO', msg: `✨ Auto-Spin: Rewriting description with specs & bullet points...` },
                                  { time: now, level: 'SUCCESS', msg: `✨ Description rewritten (Structured format bypasses duplicate text filter)` }
                                ]);
                              }}
                              className="flex items-center space-x-1 px-2 py-0.5 rounded bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 text-[10px] font-semibold transition-colors"
                            >
                              <Sparkles className="h-3 w-3 text-indigo-400" />
                              <span>✨ Auto-Spin via AI</span>
                            </button>
                          </div>
                          <textarea
                            id="input-sim-desc"
                            rows={3}
                            value={simDescription}
                            onChange={e => setSimDescription(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 resize-none"
                            placeholder="Detailed product condition, specs, payment methods..."
                          />
                        </div>

                        {/* Image picker & flags */}
                        <div className="flex flex-wrap items-center justify-between pt-2 border-t border-slate-800/80 gap-3">
                          <div className="flex items-center space-x-3">
                            <button
                              id="btn-sim-browse-img"
                              onClick={() => alert("PyQt5 QFileDialog opened: In the native app, this opens the local file system image picker.")}
                              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700"
                            >
                              <ImageIcon className="h-3.5 w-3.5 text-indigo-400" />
                              <span>Select Product Images</span>
                            </button>
                            <span className="text-xs text-slate-400">2 images selected (iphone_front.jpg, iphone_back.jpg)</span>
                          </div>

                          <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300">
                            <label className="flex items-center space-x-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={antiDupShield}
                                onChange={e => setAntiDupShield(e.target.checked)}
                                className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0"
                              />
                              <span className="font-semibold text-indigo-300">🛡️ Anti-Duplicate Shield</span>
                            </label>
                            <label className="flex items-center space-x-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={antiDupRotate}
                                onChange={e => setAntiDupRotate(e.target.checked)}
                                disabled={!antiDupShield}
                                className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0 disabled:opacity-50"
                              />
                              <span>Micro-Rotation (±0.5°)</span>
                            </label>
                            <label className="flex items-center space-x-2 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={wipeExif}
                                onChange={e => setWipeExif(e.target.checked)}
                                disabled={!antiDupShield}
                                className="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0 disabled:opacity-50"
                              />
                              <span>Wipe EXIF Metadata</span>
                            </label>
                          </div>
                        </div>
                      </div>

                      {/* Execution bar */}
                      <div className="bg-slate-950/90 border border-slate-800/90 rounded-xl p-3.5 flex flex-wrap items-center justify-between gap-4">
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-semibold text-slate-300">Posting Speed:</span>
                          <select
                            id="select-sim-speed"
                            value={simSpeed}
                            onChange={e => setSimSpeed(e.target.value)}
                            className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                          >
                            <option>Normal (15-30s)</option>
                            <option>Slow (Ultra-Stealth 30-60s)</option>
                            <option>Fast (5-15s)</option>
                          </select>
                        </div>

                        <div className="flex items-center space-x-3">
                          <button
                            id="btn-sim-start"
                            disabled={isSimulating}
                            onClick={runSimulation}
                            className={`flex items-center space-x-2 px-5 py-2 rounded-lg text-xs font-bold text-white transition-all ${
                              isSimulating
                                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                                : 'bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-600/30'
                            }`}
                          >
                            <Play className="h-3.5 w-3.5 fill-current" />
                            <span>{isSimulating ? 'Posting...' : 'Start Auto-Posting'}</span>
                          </button>

                          <button
                            id="btn-sim-stop"
                            disabled={!isSimulating}
                            onClick={() => setIsSimulating(false)}
                            className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${
                              !isSimulating
                                ? 'bg-slate-800 text-slate-600 cursor-not-allowed'
                                : 'bg-red-600 hover:bg-red-500 text-white'
                            }`}
                          >
                            <Square className="h-3.5 w-3.5 fill-current" />
                            <span>Stop</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB: ACCOUNTS MANAGER */}
                  {simActivePage === 'accounts' && (
                    <div className="space-y-4">
                      <div>
                        <h2 className="text-lg font-bold text-white tracking-tight">Accounts & Session Manager</h2>
                        <p className="text-xs text-slate-400">Import Facebook authentication cookies and bind isolated residential proxies.</p>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {/* Import Form */}
                        <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-3">
                          <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Import Session</h3>
                          <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Account Alias</label>
                            <input
                              type="text"
                              placeholder="e.g., ShopUSA_MainProfile"
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-100"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-slate-400 mb-1">Cookie String or JSON</label>
                            <textarea
                              rows={3}
                              placeholder="Paste JSON cookies array or c_user=...; xs=...;"
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-100 resize-none font-mono text-[11px]"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="block text-xs font-medium text-slate-400 mb-1">Proxy Type</label>
                              <select className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-2 py-1.5 text-xs text-slate-100">
                                <option>SOCKS5</option>
                                <option>HTTP</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-slate-400 mb-1">Host:Port</label>
                              <input
                                type="text"
                                placeholder="185.199.229.15:8080"
                                className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-100"
                              />
                            </div>
                          </div>
                          <button className="w-full mt-2 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white shadow">
                            + Save Facebook Profile
                          </button>
                        </div>

                        {/* Accounts List Table */}
                        <div className="lg:col-span-2 bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 flex flex-col">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Configured Profiles (2)</h3>
                            <button
                              onClick={() => {
                                const now = new Date().toLocaleTimeString('en-GB');
                                setSimLogs(prev => [
                                  ...prev,
                                  { time: now, level: 'INFO', msg: 'Auditing all account sessions via SessionManager...' },
                                  { time: now, level: 'SUCCESS', msg: 'acc_shop_usa: Verified active session on .facebook.com (Healthy)' },
                                  { time: now, level: 'SUCCESS', msg: 'acc_backup_uk: Verified active session on .facebook.com (Healthy)' },
                                ]);
                              }}
                              className="px-2.5 py-1 rounded bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/30 text-[11px] font-semibold"
                            >
                              🔄 Audit All Profiles
                            </button>
                          </div>
                          <div className="overflow-x-auto flex-1">
                            <table className="w-full text-left text-xs">
                              <thead>
                                <tr className="border-b border-slate-800 text-slate-400">
                                  <th className="pb-2 font-semibold">Account / Profile Dir</th>
                                  <th className="pb-2 font-semibold">Assigned Proxy</th>
                                  <th className="pb-2 font-semibold">Status</th>
                                  <th className="pb-2 font-semibold text-right">Actions</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                                <tr>
                                  <td className="py-2.5">
                                    <div className="font-medium text-white">ShopUSA_MainProfile</div>
                                    <div className="text-[10px] text-slate-500 font-mono">profiles/acc_shop_usa/</div>
                                  </td>
                                  <td className="py-2.5 text-slate-300 font-mono text-[11px]">185.199.229.15:8080</td>
                                  <td className="py-2.5">
                                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold">
                                      Healthy
                                    </span>
                                  </td>
                                  <td className="py-2.5 text-right space-x-1.5">
                                    <button
                                      onClick={() => {
                                        const now = new Date().toLocaleTimeString('en-GB');
                                        setSimLogs(prev => [
                                          ...prev,
                                          { time: now, level: 'INFO', msg: '[SessionHealth] Verifying session for ShopUSA_MainProfile...' },
                                          { time: now, level: 'SUCCESS', msg: 'ShopUSA_MainProfile: Valid session authenticated! (Feed & Navigation verified)' }
                                        ]);
                                      }}
                                      className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-emerald-300 border border-emerald-500/30 font-medium"
                                    >
                                      ⚡ Test Health
                                    </button>
                                    <button
                                      onClick={() => {
                                        const now = new Date().toLocaleTimeString('en-GB');
                                        setSimLogs(prev => [
                                          ...prev,
                                          { time: now, level: 'INFO', msg: '[ManualLogin] Launching Chromium headful window for ShopUSA_MainProfile...' },
                                          { time: now, level: 'SUCCESS', msg: 'Cookies extracted & synced to profiles/acc_shop_usa/' }
                                        ]);
                                      }}
                                      className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-indigo-300 border border-indigo-500/30 font-medium"
                                    >
                                      🌐 Login
                                    </button>
                                  </td>
                                </tr>
                                <tr>
                                  <td className="py-2.5">
                                    <div className="font-medium text-white">Backup_Store_UK</div>
                                    <div className="text-[10px] text-slate-500 font-mono">profiles/acc_backup_uk/</div>
                                  </td>
                                  <td className="py-2.5 text-slate-400">Direct (No Proxy)</td>
                                  <td className="py-2.5">
                                    <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-semibold">
                                      Healthy
                                    </span>
                                  </td>
                                  <td className="py-2.5 text-right space-x-1.5">
                                    <button
                                      onClick={() => {
                                        const now = new Date().toLocaleTimeString('en-GB');
                                        setSimLogs(prev => [
                                          ...prev,
                                          { time: now, level: 'INFO', msg: '[SessionHealth] Verifying session for Backup_Store_UK...' },
                                          { time: now, level: 'SUCCESS', msg: 'Backup_Store_UK: Valid session confirmed!' }
                                        ]);
                                      }}
                                      className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-emerald-300 border border-emerald-500/30 font-medium"
                                    >
                                      ⚡ Test Health
                                    </button>
                                    <button
                                      onClick={() => {
                                        const now = new Date().toLocaleTimeString('en-GB');
                                        setSimLogs(prev => [
                                          ...prev,
                                          { time: now, level: 'INFO', msg: '[ManualLogin] Launching Chromium headful window for Backup_Store_UK...' },
                                          { time: now, level: 'SUCCESS', msg: 'Cookies extracted & synced to profiles/acc_backup_uk/' }
                                        ]);
                                      }}
                                      className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-[10px] text-indigo-300 border border-indigo-500/30 font-medium"
                                    >
                                      🌐 Login
                                    </button>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB: DASHBOARD */}
                  {simActivePage === 'dashboard' && (
                    <div className="space-y-4">
                      <div>
                        <h2 className="text-lg font-bold text-white tracking-tight">Operational Dashboard</h2>
                        <p className="text-xs text-slate-400">Real-time telemetry, session health, and automated posting metrics.</p>
                      </div>

                      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                        <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4">
                          <div className="text-xs text-slate-400 font-medium">Active Profiles</div>
                          <div className="text-2xl font-bold text-indigo-400 mt-1">12</div>
                          <div className="text-[11px] text-slate-500 mt-1">Ready for scheduled queue</div>
                        </div>
                        <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4">
                          <div className="text-xs text-slate-400 font-medium">Listings Published</div>
                          <div className="text-2xl font-bold text-emerald-400 mt-1">148</div>
                          <div className="text-[11px] text-slate-500 mt-1">99.2% success rate today</div>
                        </div>
                        <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4">
                          <div className="text-xs text-slate-400 font-medium">Duplicate Evasion</div>
                          <div className="text-2xl font-bold text-amber-400 mt-1">100%</div>
                          <div className="text-[11px] text-slate-500 mt-1">OpenCV micro-alterations</div>
                        </div>
                        <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4">
                          <div className="text-xs text-slate-400 font-medium">Avg Proxy Latency</div>
                          <div className="text-2xl font-bold text-cyan-400 mt-1">42ms</div>
                          <div className="text-[11px] text-slate-500 mt-1">US & EU residential pool</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB: AI CONTENT SPINNER (Phase 5) */}
                  {simActivePage === 'ai' && (
                    <div className="space-y-4">
                      <div>
                        <div className="flex items-center space-x-2">
                          <h2 className="text-lg font-bold text-white tracking-tight">AI Content Spinner & Intelligence</h2>
                          <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Phase 5 Verified</span>
                        </div>
                        <p className="text-xs text-slate-400">Generate high-converting titles, rewrite descriptions with structured specifications, and bypass duplicate text penalties.</p>
                      </div>

                      {/* Inputs Card */}
                      <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-3">
                        <div>
                          <label className="block text-xs font-semibold text-slate-300 mb-1">Product Name or Seed Keywords</label>
                          <input
                            type="text"
                            value={aiSeed}
                            onChange={e => setAiSeed(e.target.value)}
                            placeholder="e.g., Apple iPhone 15 Pro Max 256GB Titanium sealed"
                            className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-slate-300 mb-1">Base Product Notes / Original Description</label>
                          <textarea
                            rows={2}
                            value={aiBaseDesc}
                            onChange={e => setAiBaseDesc(e.target.value)}
                            placeholder="Paste raw description or specifications here..."
                            className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 resize-none text-[11px]"
                          />
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          <div>
                            <label className="block text-xs font-semibold text-slate-300 mb-1">Tone of Voice</label>
                            <select
                              value={aiTone}
                              onChange={e => setAiTone(e.target.value as any)}
                              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
                            >
                              <option>Casual & Friendly</option>
                              <option>Professional & Transparent</option>
                              <option>Urgent Clearance / Deal</option>
                            </select>
                          </div>

                          <div className="md:col-span-2">
                            <label className="block text-xs font-semibold text-slate-300 mb-1">Gemini API Key (Optional / Uses Offline Spintax if blank)</label>
                            <input
                              type="password"
                              value={aiApiKey}
                              onChange={e => setAiApiKey(e.target.value)}
                              placeholder="AIzaSy... (Leave empty for Offline Spintax Engine)"
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                            />
                          </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80">
                          <button
                            onClick={() => {
                              const now = new Date().toLocaleTimeString('en-GB');
                              const prefixes = ['Brand New', 'Factory Sealed', '🔥 Deal:', '[Must Go!]', 'Authentic'];
                              const suffixes = ['- Quick Sale', '(Sealed Box)', '- Fast Local Pickup', '[Under Warranty]'];
                              const newTitles = [
                                `${prefixes[0]} ${aiSeed} ${suffixes[0]}`,
                                `${prefixes[1]} ${aiSeed} ${suffixes[1]}`,
                                `${prefixes[2]} ${aiSeed} ${suffixes[2]}`,
                                `${prefixes[3]} ${aiSeed} ${suffixes[3]}`
                              ];
                              setAiGeneratedTitles(newTitles);
                              setSimLogs(prev => [
                                ...prev,
                                { time: now, level: 'INFO', msg: `🧠 AI Spinner: Generated ${newTitles.length} title variants for '${aiSeed}' (Tone: ${aiTone})` }
                              ]);
                            }}
                            className="px-3.5 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 border border-indigo-500/40 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
                          >
                            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
                            <span>✨ Generate Titles</span>
                          </button>

                          <button
                            onClick={() => {
                              const now = new Date().toLocaleTimeString('en-GB');
                              const desc = `Up for sale is an authentic ${aiSeed} in pristine condition.\n\n` +
                                `• Condition: 100% Brand New in original factory sealed box\n` +
                                `• Specifications: Authentic verified device, comes with all genuine pack-ins\n` +
                                `• Logistics: Same-day local pickup available or tracked postage with signature\n` +
                                `• Payment: Cash or instant bank transfer upon collection\n\n` +
                                `Tone: ${aiTone}. Clean smoke-free home. Message for rapid response!`;
                              setAiGeneratedDesc(desc);
                              setSimLogs(prev => [
                                ...prev,
                                { time: now, level: 'INFO', msg: `📝 AI Spinner: Generated structured description rewrite (Tone: ${aiTone})` }
                              ]);
                            }}
                            className="px-3.5 py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-200 border border-indigo-500/40 text-xs font-semibold flex items-center space-x-1.5 transition-colors"
                          >
                            <FileCode className="h-3.5 w-3.5 text-indigo-400" />
                            <span>📝 Rewrite Description</span>
                          </button>

                          <button
                            onClick={() => {
                              const now = new Date().toLocaleTimeString('en-GB');
                              const prefixes = ['Brand New', 'Factory Sealed', '🔥 Deal:', '[Must Go!]'];
                              const newTitles = prefixes.map(p => `${p} ${aiSeed} - Ready for Pickup`);
                              setAiGeneratedTitles(newTitles);
                              const desc = `Up for sale is ${aiSeed} in immaculate condition.\n\n` +
                                `• Condition: Factory sealed & verified authentic\n` +
                                `• Specifications: Full factory packaging, warranty ready\n` +
                                `• Pickup / Shipping: Available immediately for local meetup or express delivery\n\n` +
                                `First come, first served! Cash or digital transfer accepted.`;
                              setAiGeneratedDesc(desc);
                              setSimLogs(prev => [
                                ...prev,
                                { time: now, level: 'INFO', msg: `🚀 AI Full Spin: Generated titles and complete sales copy for '${aiSeed}'` },
                                { time: now, level: 'SUCCESS', msg: `Anti-duplicate evasion score: 100% (All text hashes distinct)` }
                              ]);
                            }}
                            className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 flex items-center space-x-1.5 transition-all"
                          >
                            <Sparkles className="h-3.5 w-3.5 fill-current" />
                            <span>🚀 Full Listing Generation</span>
                          </button>
                        </div>
                      </div>

                      {/* Results Card */}
                      <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Title Variants */}
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Title Variants</h3>
                              <span className="text-[10px] text-slate-500 font-mono">{aiGeneratedTitles.length} options</span>
                            </div>
                            <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                              {aiGeneratedTitles.map((t, idx) => (
                                <div
                                  key={idx}
                                  onClick={() => {
                                    setSimTitle(t);
                                    const now = new Date().toLocaleTimeString('en-GB');
                                    setSimLogs(prev => [
                                      ...prev,
                                      { time: now, level: 'SUCCESS', msg: `Transferred title variant ${idx + 1} to Automation Tab: "${t}"` }
                                    ]);
                                  }}
                                  className="p-2 rounded-lg bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-indigo-500/50 cursor-pointer flex items-center justify-between group transition-all"
                                >
                                  <span className="text-xs text-slate-200 font-medium leading-tight">{idx + 1}. {t}</span>
                                  <span className="text-[10px] opacity-0 group-hover:opacity-100 text-indigo-400 font-semibold transition-opacity whitespace-nowrap ml-2">Use Title ↙</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Description Variant */}
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Generated Description</h3>
                              <button
                                onClick={() => {
                                  setSimDescription(aiGeneratedDesc);
                                  const now = new Date().toLocaleTimeString('en-GB');
                                  setSimLogs(prev => [
                                    ...prev,
                                    { time: now, level: 'SUCCESS', msg: `Transferred generated description to Automation Tab.` }
                                  ]);
                                }}
                                className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold"
                              >
                                Use Description ↙
                              </button>
                            </div>
                            <textarea
                              rows={5}
                              readOnly
                              value={aiGeneratedDesc}
                              className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-300 font-sans resize-none leading-relaxed"
                            />
                          </div>
                        </div>

                        {/* Apply All */}
                        <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                          <span className="text-[11px] text-slate-500">Ready to inject directly into Facebook Marketplace posting engine</span>
                          <button
                            onClick={() => {
                              if (aiGeneratedTitles.length > 0) {
                                setSimTitle(aiGeneratedTitles[0]);
                              }
                              setSimDescription(aiGeneratedDesc);
                              setSimActivePage('automation');
                              const now = new Date().toLocaleTimeString('en-GB');
                              setSimLogs(prev => [
                                ...prev,
                                { time: now, level: 'SUCCESS', msg: `Applied AI generated copy & switched to Automation Tab!` }
                              ]);
                            }}
                            className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white flex items-center space-x-1.5 shadow-lg shadow-emerald-600/20 transition-all"
                          >
                            <span>🚀 Apply Title & Description to Automation Tab</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB: SETTINGS */}
                  {simActivePage === 'settings' && (
                    <div className="space-y-4">
                      <div>
                        <h2 className="text-lg font-bold text-white tracking-tight">Settings & Stealth Parameters</h2>
                        <p className="text-xs text-slate-400">Configure browser evasion flags, API credentials, and runtime parameters.</p>
                      </div>

                      <div className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-3 text-xs text-slate-300">
                        <div className="space-y-2">
                          <label className="flex items-center space-x-2">
                            <input type="checkbox" defaultChecked className="rounded bg-slate-900 border-slate-700 text-indigo-600" />
                            <span>Playwright Stealth Module (Mask navigator.webdriver & permissions)</span>
                          </label>
                          <label className="flex items-center space-x-2">
                            <input type="checkbox" defaultChecked className="rounded bg-slate-900 border-slate-700 text-indigo-600" />
                            <span>Randomize Canvas & WebGL Audio Context noise</span>
                          </label>
                          <label className="flex items-center space-x-2">
                            <input type="checkbox" defaultChecked className="rounded bg-slate-900 border-slate-700 text-indigo-600" />
                            <span>Emulate Human Micro-Mouse Jitter & Variable Scroll Velocity</span>
                          </label>
                          <label className="flex items-center space-x-2">
                            <input type="checkbox" className="rounded bg-slate-900 border-slate-700 text-indigo-600" />
                            <span>Headless Mode (Off = Show real browser window during automation)</span>
                          </label>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 3. Global Terminal / Console Box (Bottom) */}
                  <div className="bg-slate-950/95 border border-slate-800/90 rounded-xl p-3 flex flex-col font-mono text-xs">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-[11px]">
                      <div className="flex items-center space-x-2 text-slate-300 font-semibold">
                        <Terminal className="h-3.5 w-3.5 text-indigo-400" />
                        <span>Live Terminal & Real-Time Console Log</span>
                      </div>
                      <button
                        id="btn-clear-console"
                        onClick={clearLogs}
                        className="text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        Clear Console
                      </button>
                    </div>

                    <div className="h-36 overflow-y-auto py-2 space-y-1 text-[11px] leading-relaxed">
                      {simLogs.map((log, idx) => (
                        <div key={idx} className="flex items-start space-x-2">
                          <span className="text-slate-500 select-none">[{log.time}]</span>
                          <span
                            className={`font-bold select-none ${
                              log.level === 'SUCCESS'
                                ? 'text-emerald-400'
                                : log.level === 'WARNING'
                                ? 'text-amber-400'
                                : log.level === 'ERROR'
                                ? 'text-red-400'
                                : 'text-indigo-400'
                            }`}
                          >
                            [{log.level}]
                          </span>
                          <span className="text-slate-300">{log.msg}</span>
                        </div>
                      ))}
                    </div>

                    {/* Bottom Progress Indicator */}
                    <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden mt-1">
                      <div
                        className="bg-gradient-to-r from-indigo-500 to-emerald-400 h-full transition-all duration-300"
                        style={{ width: `${simProgress}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB: LANDING PAGE PREVIEW & DEPLOYMENT */}
        {activeTab === 'landing-page' && (
          <div className="space-y-6">
            {/* Header / Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-4 rounded-2xl shadow-xl">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <h2 className="text-lg font-bold text-white tracking-tight">FB Auto Bot - Live Sales Landing Page</h2>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Single-File HTML + Tailwind</span>
                </div>
                <p className="text-xs text-slate-400">
                  Modern dark glassmorphic landing page designed for maximum conversion. Includes Hero, Features, Architecture Comparison Table, Pricing ($10/mo & $100/yr), Interactive FAQ Accordion, and WhatsApp ordering.
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => {
                    const code = landingPageSnippet;
                    copyCodeToClipboard(code);
                  }}
                  className="flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 hover:text-white transition-all shadow-sm"
                >
                  {copiedCode ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                  <span>{copiedCode ? 'Copied HTML!' : 'Copy index.html'}</span>
                </button>
                <a
                  href="/landing.html"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 border border-indigo-500/40 transition-all"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>Open Fullscreen in New Tab</span>
                </a>
              </div>
            </div>

            {/* Live Interactive Iframe Frame */}
            <div className="rounded-2xl border border-slate-700/80 bg-slate-950 overflow-hidden shadow-2xl">
              {/* Browser bar */}
              <div className="h-10 bg-slate-900/90 px-4 flex items-center justify-between border-b border-slate-800">
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 rounded-full bg-rose-500/80"></span>
                  <span className="w-3 h-3 rounded-full bg-amber-500/80"></span>
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80"></span>
                  <div className="ml-3 flex items-center space-x-2 bg-slate-950 px-3 py-1 rounded-md border border-slate-800 text-[11px] font-mono text-slate-400 w-80 truncate">
                    <Globe className="h-3 w-3 text-indigo-400 shrink-0" />
                    <span>https://fbverse.pages.dev</span>
                  </div>
                </div>
                <div className="flex items-center space-x-3 text-[11px] font-mono text-emerald-400">
                  <span>HTML5 • TAILWIND CDN • ZERO DEPENDENCIES</span>
                </div>
              </div>

              {/* Embedded Iframe */}
              <div className="w-full h-[700px] bg-[#0b0f19]">
                <iframe
                  src="/landing.html"
                  title="FB Auto Bot Landing Page Preview"
                  className="w-full h-full border-0"
                />
              </div>
            </div>

            {/* Cloudflare Pages & Vercel Free Hosting Guide */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              
              {/* Cloudflare Pages Guide */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
                <div className="flex items-center space-x-3">
                  <div className="w-9 h-9 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <Cloud className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">How to Host on Cloudflare Pages (100% Free)</h3>
                    <p className="text-[11px] text-slate-400">Unlimited bandwidth & global edge CDN under your custom domain or .pages.dev</p>
                  </div>
                </div>

                <ol className="space-y-2.5 text-xs text-slate-300 list-decimal list-inside leading-relaxed">
                  <li>Log in to your free dashboard at <a href="https://dash.cloudflare.com" target="_blank" className="text-indigo-400 underline">dash.cloudflare.com</a>.</li>
                  <li>Click <span className="text-white font-medium">Workers & Pages</span> &rarr; <span className="text-white font-medium">Create Application</span> &rarr; Select <span className="text-white font-medium">Pages</span>.</li>
                  <li>Choose <span className="text-white font-medium">"Upload assets"</span> and drag & drop the <code className="text-indigo-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">landing_page/</code> folder containing <code className="text-emerald-300">index.html</code>.</li>
                  <li>Click <span className="text-white font-medium">Deploy Site</span>. Your site will instantly go live at <code className="text-emerald-400">https://fbverse.pages.dev</code>!</li>
                </ol>
              </div>

              {/* Vercel Guide */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
                <div className="flex items-center space-x-3">
                  <div className="w-9 h-9 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <Zap className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-white">How to Host on Vercel (100% Free)</h3>
                    <p className="text-[11px] text-slate-400">Instant SSL certificate, fast deploy, and custom domain routing</p>
                  </div>
                </div>

                <ol className="space-y-2.5 text-xs text-slate-300 list-decimal list-inside leading-relaxed">
                  <li>Log in to <a href="https://vercel.com" target="_blank" className="text-indigo-400 underline">vercel.com</a> with your GitHub or Email.</li>
                  <li>Click <span className="text-white font-medium">"Add New Project"</span> &rarr; Import your GitHub repo, or install Vercel CLI.</li>
                  <li>Alternatively run <code className="text-indigo-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">npx vercel ./landing_page</code> directly in your terminal.</li>
                  <li>Your landing page is live in seconds with global SSL and automatic CDN cache invalidation!</li>
                </ol>
              </div>

            </div>
          </div>
        )}

        {/* TAB: CODE & FILE VIEWER */}
        {activeTab === 'code-viewer' && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Desktop Project Code Vault</h2>
                <p className="text-xs text-slate-400">Production-grade automation scripts and GUI files generated in `desktop_app/`.</p>
              </div>
              <button
                id="btn-copy-code"
                onClick={() => {
                  const code = selectedFile === 'landing_page/index.html'
                    ? landingPageSnippet
                    : selectedFile === 'ai_spinner.py'
                    ? aiSpinnerSnippet
                    : selectedFile === 'session_manager.py'
                    ? sessionManagerSnippet
                    : selectedFile === 'image_processor.py'
                    ? imageProcessorSnippet
                    : selectedFile === 'browser_bot.py' 
                    ? browserBotCodeSnippet 
                    : selectedFile === 'app.py' 
                    ? appPyCodeSnippet 
                    : requirementsSnippet;
                  copyCodeToClipboard(code);
                }}
                className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md shadow-indigo-600/30 transition-all"
              >
                {copiedCode ? <Check className="h-4 w-4 text-emerald-300" /> : <Copy className="h-4 w-4" />}
                <span>{copiedCode ? `Copied ${selectedFile}!` : `Copy ${selectedFile} Code`}</span>
              </button>
            </div>

            {/* File Switcher Header */}
            <div className="flex flex-wrap items-center gap-2 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800">
              <button
                onClick={() => setSelectedFile('landing_page/index.html')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'landing_page/index.html'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Globe className="h-3.5 w-3.5 text-emerald-300" />
                <span>landing_page/index.html</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-emerald-500/20 text-emerald-300 rounded font-sans">Phase 6</span>
              </button>
              <button
                onClick={() => setSelectedFile('ai_spinner.py')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'ai_spinner.py'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Sparkles className="h-3.5 w-3.5 text-amber-300" />
                <span>utils/ai_spinner.py</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-amber-500/20 text-amber-300 rounded font-sans">Phase 5</span>
              </button>
              <button
                onClick={() => setSelectedFile('session_manager.py')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'session_manager.py'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <FileCode className="h-3.5 w-3.5 text-purple-400" />
                <span>automation/session_manager.py</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-purple-500/20 text-purple-300 rounded font-sans">Phase 4</span>
              </button>
              <button
                onClick={() => setSelectedFile('image_processor.py')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'image_processor.py'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <FileCode className="h-3.5 w-3.5 text-cyan-400" />
                <span>utils/image_processor.py</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-cyan-500/20 text-cyan-300 rounded font-sans">Phase 3</span>
              </button>
              <button
                onClick={() => setSelectedFile('browser_bot.py')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'browser_bot.py'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <FileCode className="h-3.5 w-3.5 text-emerald-400" />
                <span>automation/browser_bot.py</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-emerald-500/20 text-emerald-300 rounded font-sans">Phase 2</span>
              </button>
              <button
                onClick={() => setSelectedFile('app.py')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'app.py'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <FileCode className="h-3.5 w-3.5 text-indigo-400" />
                <span>desktop_app/app.py</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-indigo-500/20 text-indigo-300 rounded font-sans">GUI</span>
              </button>
              <button
                onClick={() => setSelectedFile('requirements.txt')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'requirements.txt'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <FileCode className="h-3.5 w-3.5 text-amber-400" />
                <span>requirements.txt</span>
              </button>
            </div>

            {/* Quick Directory tree visualization */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 font-mono text-xs">
                <div className="flex items-center space-x-2 text-indigo-400 font-bold mb-3 pb-2 border-b border-slate-800">
                  <FolderTree className="h-4 w-4" />
                  <span>Repository Layout</span>
                </div>
                <div className="space-y-1 text-slate-300">
                  <div className="text-slate-100 font-bold">desktop_app/</div>
                  <div className="pl-4 text-emerald-400">├── app.py <span className="text-[10px] text-slate-500">(PyQt5 + AI Workers)</span></div>
                  <div className="pl-4 text-indigo-300">├── automation/</div>
                  <div className="pl-8 text-purple-400 font-bold">├── session_manager.py <span className="text-[10px] text-purple-300 font-normal">(Phase 4)</span></div>
                  <div className="pl-8 text-emerald-400 font-bold">├── browser_bot.py <span className="text-[10px] text-emerald-400 font-normal">(Phase 2)</span></div>
                  <div className="pl-4 text-indigo-300">├── profiles/ <span className="text-[10px] text-slate-500">(Isolated User Data Dirs)</span></div>
                  <div className="pl-8 text-slate-400">├── acc_shop_usa/</div>
                  <div className="pl-8 text-slate-400">└── acc_backup_uk/</div>
                  <div className="pl-4 text-indigo-300">├── config/</div>
                  <div className="pl-8 text-slate-400">└── accounts_db.json</div>
                  <div className="pl-4 text-indigo-300">└── utils/</div>
                  <div className="pl-8 text-amber-400 font-bold">├── ai_spinner.py <span className="text-[10px] text-amber-300 font-normal">(Phase 5)</span></div>
                  <div className="pl-8 text-cyan-400 font-bold">└── image_processor.py <span className="text-[10px] text-cyan-300 font-normal">(Phase 3)</span></div>
                </div>
              </div>

              <div className="md:col-span-2 bg-slate-900/80 border border-slate-800 rounded-xl p-4 text-xs space-y-3">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold pb-2 border-b border-slate-800">
                  <Terminal className="h-4 w-4" />
                  <span>How to Run Locally</span>
                </div>
                <div className="space-y-2">
                  <p className="text-slate-300">1. Setup Python virtual environment & install dependencies:</p>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] text-indigo-300 space-y-1">
                    <div>python -m venv venv</div>
                    <div>source venv/bin/activate  # Or `venv\Scripts\activate` on Windows</div>
                    <div>pip install -r desktop_app/requirements.txt</div>
                    <div className="text-emerald-400">playwright install chromium</div>
                  </div>
                  <p className="text-slate-300">2. Launch the desktop GUI:</p>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] text-emerald-400">
                    python desktop_app/app.py
                  </div>
                </div>
              </div>
            </div>

            {/* Code Snippet Box */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden">
              <div className="px-4 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <FileCode className="h-4 w-4 text-indigo-400" />
                  <span className="text-xs font-mono font-medium text-slate-200">
                    {selectedFile === 'landing_page/index.html' && 'landing_page/index.html (Single-File Tailwind CDN & FAQ Accordion)'}
                    {selectedFile === 'ai_spinner.py' && 'desktop_app/utils/ai_spinner.py (Gemini 2.5 API & Spintax Engine)'}
                    {selectedFile === 'session_manager.py' && 'desktop_app/automation/session_manager.py (Isolated Profiles & Session Health)'}
                    {selectedFile === 'image_processor.py' && 'desktop_app/utils/image_processor.py (OpenCV & Pillow Anti-Duplicate)'}
                    {selectedFile === 'browser_bot.py' && 'desktop_app/automation/browser_bot.py (Playwright Stealth Async)'}
                    {selectedFile === 'app.py' && 'desktop_app/app.py (PyQt5 Modern Desktop GUI & Async Worker)'}
                    {selectedFile === 'requirements.txt' && 'desktop_app/requirements.txt'}
                  </span>
                </div>
                <span className="text-[11px] text-slate-500 font-mono">
                  {selectedFile === 'landing_page/index.html' ? 'HTML5 • Tailwind CDN • Vanilla JS • Glassmorphism' : selectedFile === 'ai_spinner.py' ? 'Google GenAI SDK • Prompt Engineering • Offline Regex Spintax' : selectedFile === 'session_manager.py' ? 'Isolated Profiles • Cookie Normalizer • Health Auditor' : selectedFile === 'image_processor.py' ? 'OpenCV • Pillow • Piexif' : selectedFile === 'browser_bot.py' ? 'Python AsyncIO • Playwright Stealth' : selectedFile === 'app.py' ? 'PyQt5 • QSS Dark Theme' : 'PIP Manifest'}
                </span>
              </div>
              <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto max-h-[480px] leading-relaxed">
                <code>
                  {selectedFile === 'landing_page/index.html' && landingPageSnippet}
                  {selectedFile === 'ai_spinner.py' && aiSpinnerSnippet}
                  {selectedFile === 'session_manager.py' && sessionManagerSnippet}
                  {selectedFile === 'image_processor.py' && imageProcessorSnippet}
                  {selectedFile === 'browser_bot.py' && browserBotCodeSnippet}
                  {selectedFile === 'app.py' && appPyCodeSnippet}
                  {selectedFile === 'requirements.txt' && requirementsSnippet}
                </code>
              </pre>
            </div>
          </div>
        )}

        {/* TAB: ROADMAP */}
        {activeTab === 'roadmap' && (
          <div className="space-y-6">
            <div>
              <h2 className="text-xl font-bold text-white tracking-tight">FB Auto Bot - Engineering Roadmap</h2>
              <p className="text-xs text-slate-400">Step-by-step master plan execution from desktop software to landing sales site.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[
                {
                  phase: 'Phase 1 (Completed)',
                  title: 'Project Architecture & Modern Desktop GUI',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Established clean folder structure, requirements.txt, dark glassmorphic PyQt5 interface, accounts manager, automation inputs, and real-time terminal output.'
                },
                {
                  phase: 'Phase 2 (Completed)',
                  title: 'Playwright Browser Automation & Anti-Detection System',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Built production-grade async Playwright bot, navigator.webdriver masking, WebGL/Canvas spoofing, session cookie injector, human typing jitter (80-240ms), and QThread async bridge.'
                },
                {
                  phase: 'Phase 3 (Completed)',
                  title: 'OpenCV / Pillow Anti-Duplicate Image Engine',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Implemented EXIF/GPS metadata stripping, micro-rotations (-0.5° to +0.5°), pixel noise injection, color/contrast jitter, and dynamic temp batch processing.'
                },
                {
                  phase: 'Phase 4 (Completed)',
                  title: 'Multi-Account & Session Cookie Manager',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Automating Facebook login injection via JSON and Semicolon format cookies, isolated Chrome user-data directories, proxy binding, and headless session health auditor.'
                },
                {
                  phase: 'Phase 5 (Completed)',
                  title: 'AI Content Spinner & Intelligence (Gemini API)',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Generating high-converting title variants, formatted descriptions with structured specs, and offline Spintax regex fallback with one-click direct transfer into the automation queue.'
                },
                {
                  phase: 'Phase 6 (Completed)',
                  title: 'Modern Glassmorphic Landing Sales Page',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Built modern dark-themed glassmorphic sales page with Hero, features grid, comparison table, pricing tiers ($10/mo & $100/yr), interactive FAQ accordion, and WhatsApp order CTAs.'
                }
              ].map((step, idx) => (
                <div key={idx} className="bg-slate-900/80 border border-slate-800/80 rounded-xl p-4 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] font-bold text-slate-400 font-mono">{step.phase}</span>
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${step.statusColor}`}>
                        {step.status}
                      </span>
                    </div>
                    <h3 className="text-sm font-bold text-white">{step.title}</h3>
                    <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
