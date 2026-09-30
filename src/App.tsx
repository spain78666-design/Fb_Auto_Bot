import React, { useState, useEffect } from 'react';
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
  Cloud,
  Key,
  Smartphone,
  Monitor,
  RotateCw,
  ChevronDown,
  ChevronUp,
  Trash2,
  Plus,
  Download,
  Sun,
  Moon
} from 'lucide-react';
import { browserBotCodeSnippet, appPyCodeSnippet, imageProcessorSnippet, sessionManagerSnippet, aiSpinnerSnippet, requirementsSnippet, landingPageSnippet, installerSetupSnippet, buildInstallerSnippet } from './data/codeSnippets';
import AdminPanel from './components/AdminPanel';
import listingFormsPreview from './assets/images/listing_forms_preview_1789717279793.jpg';

export default function App() {
  const [activeTab, setActiveTab] = useState<'desktop-sim' | 'landing-page' | 'code-viewer' | 'roadmap' | 'admin-panel' | 'columns-preview'>('landing-page');
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [showCookiePopup, setShowCookiePopup] = useState(false);
  const [cookieNotificationData, setCookieNotificationData] = useState({
    title: 'Account(s) Imported Successfully',
    message: 'Facebook UID/Password & session cookies have been imported into the vault with HEALTHY status.',
    count: 3
  });

  const [landingPreviewMode, setLandingPreviewMode] = useState<'desktop' | 'mobile'>('desktop');
  const [iframeKey, setIframeKey] = useState(0);

  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname.toLowerCase();
      const hash = window.location.hash.toLowerCase();
      if (path.includes('admin') || hash.includes('admin')) {
        setActiveTab('admin-panel');
      }
    };
    window.addEventListener('popstate', handlePopState);
    window.addEventListener('hashchange', handlePopState);
    return () => {
      window.removeEventListener('popstate', handlePopState);
      window.removeEventListener('hashchange', handlePopState);
    };
  }, []);
  const [simActivePage, setSimActivePage] = useState<'dashboard' | 'accounts' | 'automation' | 'ai' | 'settings'>('ai');
  const [selectedFile, setSelectedFile] = useState<'installer_setup.iss' | 'build_installer.py' | 'landing_page/index.html' | 'ai_spinner.py' | 'session_manager.py' | 'browser_bot.py' | 'image_processor.py' | 'app.py' | 'requirements.txt'>('installer_setup.iss');
  const [copiedCode, setCopiedCode] = useState(false);

  // Simulated GUI State
  const [simTitle, setSimTitle] = useState('Household Living Room Set / Auto Parts Replacement Unit');
  const [simPrice, setSimPrice] = useState('150');
  const [simCategory, setSimCategory] = useState('Household');
  const [simTabsCount, setSimTabsCount] = useState<number>(10);
  const [simIdLocation, setSimIdLocation] = useState('New York, NY');
  const [simLocation, setSimLocation] = useState('Los Angeles, CA, New York, NY, Chicago, IL, Houston, TX, Miami, FL, Phoenix, AZ, Philadelphia, PA, San Antonio, TX, San Diego, CA, Dallas, TX');
  const [simDescription, setSimDescription] = useState('High quality item in excellent condition. Available for immediate pickup or same-day local dropoff. Cash or digital payment accepted.');
  const [simSpeed, setSimSpeed] = useState('Normal (15-30s)');
  const [antiDupShield, setAntiDupShield] = useState(true);
  const [antiDupRotate, setAntiDupRotate] = useState(true);
  const [wipeExif, setWipeExif] = useState(true);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simProgress, setSimProgress] = useState(0);

  // Interactive Demo State for Image Dropdown in Preview
  const [demoImages, setDemoImages] = useState<string[]>([
    'living_room_luxury_view.jpg',
    'bedroom_master_suite.jpg',
    'kitchen_island_interior.jpg'
  ]);
  const [isDemoDropdownOpen, setIsDemoDropdownOpen] = useState(true);

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
    addLog('INFO', `📑 Multi-Tab Engine: Spawning ${simTabsCount} parallel listing tabs for current Facebook ID...`);

    setTimeout(() => {
      setSimProgress(15);
      addLog('INFO', `Injected auth cookies (c_user=100084..., xs=29%3A...) into isolated Chrome context`);
      addLog('INFO', `Routing traffic through residential proxy: socks5://185.199.229.15:8080`);
    }, 600);

    setTimeout(() => {
      setSimProgress(30);
      addLog('SUCCESS', `Session Health Check passed: Facebook profile authenticated without checkpoints.`);
      addLog('INFO', `Initializing pool: 50+ Location Targets & 50+ Product Images Pool loaded.`);
    }, 1200);

    // Phase 3: Anti-Duplicate Image Engine processing
    setTimeout(() => {
      setSimProgress(45);
      if (antiDupShield) {
        addLog('INFO', '🛡️ Anti-Duplicate Image Shield ACTIVE: Processing randomized image pool...');
        addLog('SUCCESS', ' -> EXIF metadata stripped. Micro-rotation (±0.4°), subtle noise & MD5 hash mutated for all pool items.');
      }
    }, 1800);

    setTimeout(() => {
      setSimProgress(60);
      addLog('INFO', `🚀 Multi-Tab Workflow: Concurrently opening ${simTabsCount} tabs at https://www.facebook.com/marketplace/create/item`);
      addLog('INFO', `Tab #1: Selected random location "Los Angeles, CA" | Random image "item_pool_img_03.jpg"`);
      addLog('INFO', `Tab #2: Selected random location "Houston, TX" | Random image "item_pool_img_17.jpg"`);
      if (simTabsCount > 2) {
        addLog('INFO', `Tabs #3 to #${simTabsCount}: Allocated distinct randomized locations & image slices.`);
      }
    }, 2800);

    setTimeout(() => {
      setSimProgress(75);
      addLog('INFO', `Precise Field Injector: Typing Title ("${simTitle}") strictly into [aria-label="Title"] input.`);
      addLog('INFO', `Precise Field Injector: Typing Price ("$${simPrice}") strictly into [aria-label="Price"] input.`);
      addLog('INFO', `Precise Field Injector: Category mapped to "${simCategory}" -> Selected item.`);
      addLog('INFO', `Precise Field Injector: Typing Description strictly into textarea.`);
    }, 4000);

    setTimeout(() => {
      setSimProgress(90);
      addLog('INFO', `Configuring dynamic locations per tab: Typing location -> ArrowDown -> Enter.`);
      addLog('INFO', `Advancing Next -> Clicking Publish across ${simTabsCount} tabs simultaneously.`);
    }, 5200);

    setTimeout(() => {
      setSimProgress(100);
      addLog('SUCCESS', `🎉 Batch Completed: ${simTabsCount} ads published across ${simTabsCount} tabs with unique locations & images!`);
      addLog('INFO', `Closed Chrome instance cleanly. Ready for next Facebook ID in queue.`);
      setIsSimulating(false);
    }, 6200);
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
    <div className={`min-h-screen transition-colors duration-300 flex flex-col font-sans selection:bg-indigo-600 selection:text-white ${
      theme === 'dark' ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'
    }`}>
      {/* Top Application Header */}
      <header className={`border-b backdrop-blur sticky top-0 z-30 px-6 py-3.5 flex items-center justify-between transition-colors duration-300 ${
        theme === 'dark' ? 'border-slate-800/80 bg-slate-900/90' : 'border-slate-200 bg-white/95 shadow-sm'
      }`}>
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className={`text-base font-bold tracking-tight ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>FB Auto Bot</h1>
              <span className={`px-2 py-0.5 text-[11px] font-semibold rounded-full border ${
                theme === 'dark'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-emerald-50 text-emerald-700 border-emerald-300 font-bold'
              }`}>
                Phase 3: Anti-Duplicate Engine Active
              </span>
            </div>
            <p className={`text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>Enterprise Facebook Marketplace Automation Suite</p>
          </div>
        </div>

        {/* Right Header: 2027 Futuristic Theme Toggle Icon Button & View Switcher Tabs */}
        <div className="flex items-center space-x-3">
          {/* Futuristic 2027 Theme Toggle Button (Icon Only - Ultra Futuristic 2027 Holographic Design) */}
          <button
            id="btn-theme-toggle-header"
            onClick={() => setTheme(prev => prev === 'dark' ? 'light' : 'dark')}
            title={theme === 'dark' ? 'Switch to 2027 Futuristic Solar Light Mode' : 'Switch to 2027 Cyber Deep Dark Mode'}
            className={`relative p-2.5 rounded-full transition-all duration-300 transform active:scale-90 flex items-center justify-center cursor-pointer shadow-lg group ${
              theme === 'dark'
                ? 'bg-gradient-to-tr from-amber-500/15 via-orange-500/20 to-yellow-500/25 text-amber-400 border border-amber-500/40 shadow-amber-500/25 hover:shadow-amber-500/50 hover:border-amber-400 hover:bg-amber-500/30'
                : 'bg-gradient-to-tr from-indigo-500/15 via-blue-500/20 to-purple-500/25 text-indigo-600 border border-indigo-400/50 shadow-indigo-500/20 hover:shadow-indigo-500/40 hover:border-indigo-600 hover:bg-indigo-500/30'
            }`}
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4 transition-transform duration-500 group-hover:rotate-90 text-amber-400 drop-shadow-[0_0_8px_rgba(251,191,36,0.7)]" />
            ) : (
              <Moon className="h-4 w-4 transition-transform duration-500 group-hover:-rotate-45 text-indigo-600 drop-shadow-[0_0_8px_rgba(79,70,229,0.6)]" />
            )}
            <span className="sr-only">Toggle Theme</span>
          </button>

          {/* View Switcher Tabs */}
          <div className={`flex items-center p-1 rounded-lg border transition-colors ${
            theme === 'dark' ? 'bg-slate-950/80 border-slate-800' : 'bg-slate-100 border-slate-200'
          }`}>
            <button
              id="tab-columns-preview"
              onClick={() => setActiveTab('columns-preview')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'columns-preview'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <ImageIcon className="h-3.5 w-3.5 text-cyan-400" />
              <span>Listing Columns Preview</span>
              <span className="px-1.5 py-0.2 text-[9px] bg-cyan-500/20 text-cyan-300 rounded font-mono font-bold">New</span>
            </button>
            <button
              id="tab-landing-page"
              onClick={() => setActiveTab('landing-page')}
              className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                activeTab === 'landing-page'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
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
                  : theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
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
                  : theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
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
                  : theme === 'dark' ? 'text-slate-400 hover:text-slate-200' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Project Roadmap</span>
            </button>
            {activeTab === 'admin-panel' && (
              <div className="flex items-center space-x-2 px-3 py-1 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">
                <Key className="h-3.5 w-3.5 text-amber-400" />
                <span>Admin Key Vault (Private)</span>
              </div>
            )}
            <a
              href="https://drive.google.com/drive/folders/1H3BDvhZQkvrTizcP9K3GMVZyq_CzH7j-?usp=sharing"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden lg:flex items-center space-x-1.5 px-3 py-1 rounded-md text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-sm shadow-emerald-600/30 border border-emerald-400/30 transition-all ml-1"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download Setup (.exe)</span>
            </a>
          </div>
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
        {activeTab === 'desktop-sim' && (
          <div className="space-y-4">
            {/* Context bar */}
            <div className={`flex flex-wrap items-center justify-between border rounded-xl px-4 py-3 text-xs transition-colors ${
              theme === 'dark' ? 'bg-slate-900/60 border-slate-800/80 text-slate-300' : 'bg-white border-slate-200 text-slate-700 shadow-sm'
            }`}>
              <div className="flex items-center space-x-2">
                <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span className={`font-semibold ${theme === 'dark' ? 'text-slate-200' : 'text-slate-900'}`}>PyQt5 Window Preview:</span>
                <span className={theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}>
                  This interactive workbench reflects the layout, controls, and {theme === 'dark' ? '2027 Cyber Dark' : '2027 Futuristic Light'} theme of the PyQt5 desktop app (`desktop_app/app.py`).
                </span>
              </div>
              <div className="flex items-center space-x-3 mt-2 sm:mt-0">
                <span className={theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}>Run locally:</span>
                <code className={`px-2 py-0.5 rounded border font-mono text-[11px] ${
                  theme === 'dark' ? 'bg-slate-950 border-slate-800 text-indigo-300' : 'bg-slate-100 border-slate-300 text-indigo-700 font-bold'
                }`}>
                  python desktop_app/app.py
                </code>
              </div>
            </div>

            {/* Simulated Desktop Window Frame */}
            <div className={`rounded-2xl border overflow-hidden flex flex-col min-h-[680px] transition-all duration-300 shadow-2xl ${
              theme === 'dark' ? 'border-slate-700/80 bg-slate-900/90 shadow-black/80' : 'border-slate-300 bg-white shadow-slate-300/60'
            }`}>
              {/* Fake Window Titlebar */}
              <div className={`px-4 py-2.5 border-b flex items-center justify-between select-none transition-colors ${
                theme === 'dark' ? 'bg-slate-950 border-slate-800 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-700'
              }`}>
                <div className="flex items-center space-x-2">
                  <div className="h-3 w-3 rounded-full bg-red-500/80 border border-red-600/50"></div>
                  <div className="h-3 w-3 rounded-full bg-yellow-500/80 border border-yellow-600/50"></div>
                  <div className="h-3 w-3 rounded-full bg-green-500/80 border border-green-600/50"></div>
                  <span className={`ml-3 text-xs font-medium ${theme === 'dark' ? 'text-slate-400' : 'text-slate-700 font-semibold'}`}>
                    FB Auto Bot - Facebook Marketplace Automation Suite (PyQt5)
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-[11px]">
                  {/* Test Cookie Popup Button */}
                  <button
                    id="btn-test-cookie-popup"
                    onClick={() => {
                      setCookieNotificationData({
                        title: 'Bulk Accounts Imported Successfully',
                        message: 'Successfully added 3 Facebook accounts (UID/Pass & Cookies) with HEALTHY status into vault! Form reset for next account.',
                        count: 3
                      });
                      setShowCookiePopup(true);
                    }}
                    className="px-2.5 py-1 rounded-md text-[10px] font-bold text-white bg-emerald-600 hover:bg-emerald-500 border border-emerald-400/40 flex items-center gap-1.5 transition-all shadow-sm cursor-pointer active:scale-95"
                    title="Click to test the centered cookie import popup notification in active theme"
                  >
                    <span>🍪 Quick Add Cookie (Test Notification)</span>
                  </button>

                  <span className={`px-2 py-0.5 rounded font-mono border ${
                    theme === 'dark'
                      ? 'bg-slate-900 border-slate-800 text-emerald-400'
                      : 'bg-emerald-50 border-emerald-200 text-emerald-700 font-bold'
                  }`}>
                    ONLINE • STEALTH V2.4
                  </span>
                </div>
              </div>

              {/* Window Content (Sidebar + Main View + Console) */}
              <div className="flex flex-1 overflow-hidden">
                {/* 1. PyQt5 Sidebar */}
                <aside className={`w-60 border-r p-4 flex flex-col justify-between shrink-0 transition-colors ${
                  theme === 'dark' ? 'bg-slate-950/90 border-slate-800/80' : 'bg-slate-50 border-slate-200'
                }`}>
                  <div className="space-y-6">
                    <div className="flex items-center space-x-2.5 px-2">
                      <div className="p-1.5 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
                        <Bot className="h-5 w-5" />
                      </div>
                      <div>
                        <div className={`font-extrabold text-sm tracking-tight ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                          FB Auto Bot
                        </div>
                        <div className="text-[10px] text-indigo-500 font-semibold tracking-wider">ENTERPRISE EDITION</div>
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
                                : theme === 'dark'
                                  ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
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
                  <div className={`p-3 rounded-xl border space-y-1 transition-colors ${
                    theme === 'dark' ? 'bg-slate-900/90 border-slate-800/90' : 'bg-white border-slate-200 shadow-sm'
                  }`}>
                    <div className={`text-[10px] font-bold tracking-wider uppercase ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>
                      Stealth Status
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`h-2 w-2 rounded-full ${isSimulating ? 'bg-amber-400 animate-ping' : 'bg-emerald-400'}`}></span>
                      <span className={`text-xs font-bold ${isSimulating ? 'text-amber-500' : 'text-emerald-500'}`}>
                        {isSimulating ? 'POSTING IN PROGRESS' : 'READY FOR TASKS'}
                      </span>
                    </div>
                  </div>
                </aside>

                {/* 2. Main Tab View Area */}
                <div className={`flex-1 flex flex-col overflow-y-auto p-5 space-y-4 transition-colors ${
                  theme === 'dark' ? 'bg-slate-900/60' : 'bg-slate-100/60'
                }`}>
                  {/* TAB: AUTOMATION ENGINE */}
                  {simActivePage === 'automation' && (
                    <div className="space-y-4">
                      <div>
                        <h2 className={`text-lg font-bold tracking-tight ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                          Marketplace Automation Engine
                        </h2>
                        <p className={`text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                          Configure listing metadata, tune humanized delays, and trigger automated posting.
                        </p>
                      </div>

                      {/* Main Form Box */}
                      <div className={`border rounded-xl p-4 space-y-4 transition-colors ${
                        theme === 'dark' ? 'bg-slate-950/70 border-slate-800/90' : 'bg-white border-slate-200 shadow-sm'
                      }`}>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div>
                            <label className={`block text-xs font-semibold mb-1.5 ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>
                              Target Facebook Account Profile
                            </label>
                            <select
                              id="input-sim-account"
                              className={`w-full border rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 ${
                                theme === 'dark' ? 'bg-slate-900 border-slate-700/80 text-slate-100' : 'bg-white border-slate-300 text-slate-900'
                              }`}
                            >
                              <option>#1 🟢 ShopUSA_MainProfile [Healthy] (185.199.229.15:8080)</option>
                              <option>#2 🟢 Backup_Store_UK [Healthy] (Direct Residential)</option>
                              <option>⚡ All Healthy Accounts (Sequential Multi-Post Batch)</option>
                            </select>
                          </div>
                          <div>
                            <label className={`block text-xs font-semibold mb-1.5 ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>
                              Marketplace Category
                            </label>
                            <select
                              id="input-sim-category"
                              value={simCategory}
                              onChange={e => setSimCategory(e.target.value)}
                              className={`w-full border rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-indigo-500 font-medium ${
                                theme === 'dark'
                                  ? 'bg-slate-900 border-slate-700/80 text-emerald-400'
                                  : 'bg-white border-slate-300 text-emerald-700'
                              }`}
                            >
                              <option value="Household">🏠 Household</option>
                              <option value="Appliances">🔌 Appliances</option>
                              <option value="Auto Parts">🚗 Auto Parts</option>
                              <option value="Electronics & Computers">Electronics & Computers</option>
                              <option value="Home & Kitchen">Home & Kitchen</option>
                              <option value="Tools & Appliances">Tools & Appliances</option>
                              <option value="Vehicles & Parts">Vehicles & Parts</option>
                              <option value="Furniture & Decor">Furniture & Decor</option>
                              <option value="Apparel & Accessories">Apparel & Accessories</option>
                              <option value="Mobile Phones & Tablets">Mobile Phones & Tablets</option>
                            </select>
                          </div>
                          <div>
                            <label className={`block text-xs font-semibold mb-1.5 ${theme === 'dark' ? 'text-slate-300' : 'text-slate-700'}`}>
                              📑 Tabs / Posts per ID
                            </label>
                            <div className="flex items-center space-x-2">
                              <input
                                id="input-sim-tabs-count"
                                type="number"
                                min={1}
                                max={100}
                                value={simTabsCount}
                                onChange={e => setSimTabsCount(Math.max(1, parseInt(e.target.value) || 1))}
                                className={`w-full border rounded-lg px-3 py-2 text-xs font-bold focus:outline-none focus:border-indigo-500 font-mono ${
                                  theme === 'dark' ? 'bg-slate-900 border-slate-700/80 text-sky-400' : 'bg-white border-slate-300 text-sky-600'
                                }`}
                              />
                              <span className={`text-[11px] whitespace-nowrap ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>
                                Tabs/Post per ID
                              </span>
                            </div>
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

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5">ID Location (Marketplace Default)</label>
                            <input
                              id="input-sim-id-location"
                              type="text"
                              value={simIdLocation}
                              onChange={e => setSimIdLocation(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                              placeholder="e.g. New York, NY"
                            />
                          </div>
                          <div>
                            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Listing Location (Target Cities Pool)</label>
                            <input
                              id="input-sim-location"
                              type="text"
                              value={simLocation}
                              onChange={e => setSimLocation(e.target.value)}
                              className="w-full bg-slate-900 border border-slate-700/80 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                              placeholder="e.g. Los Angeles, CA, New York, NY, Chicago, IL, Miami, FL, Houston, TX"
                            />
                          </div>
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
                                  <th className="pb-2 font-semibold w-8 text-center">#</th>
                                  <th className="pb-2 font-semibold">Account / Profile Dir</th>
                                  <th className="pb-2 font-semibold">Assigned Proxy</th>
                                  <th className="pb-2 font-semibold">Status</th>
                                  <th className="pb-2 font-semibold text-right">Actions</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                                <tr>
                                  <td className="py-2.5 text-center font-bold text-sky-400">1</td>
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
                                  <td className="py-2.5 text-center font-bold text-sky-400">2</td>
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
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-blue-500/20 text-blue-300 border border-blue-500/30">Enterprise 2027</span>
                </div>
                <p className="text-xs text-slate-400">
                  Modern dark glassmorphic landing page designed for maximum conversion. Includes Hero, Multi-Account Vault, Multi-Tab Marketplace Lister, Group Auto Poster, Bulk Page Creator, Reels Uploader, Token Extractor, Pricing ($10/mo & $100/yr), FAQ Accordion, and WhatsApp ordering.
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

            {/* Live Interactive Iframe Frame with Device Switcher */}
            <div className="rounded-2xl border border-slate-700/80 bg-slate-950 overflow-hidden shadow-2xl">
              {/* Browser bar */}
              <div className="h-11 bg-slate-900/90 px-4 flex flex-wrap items-center justify-between border-b border-slate-800 gap-2">
                <div className="flex items-center space-x-2">
                  <span className="w-3 h-3 rounded-full bg-rose-500/80"></span>
                  <span className="w-3 h-3 rounded-full bg-amber-500/80"></span>
                  <span className="w-3 h-3 rounded-full bg-emerald-500/80"></span>
                  <div className="ml-3 flex items-center space-x-2 bg-slate-950 px-3 py-1 rounded-md border border-slate-800 text-[11px] font-mono text-slate-400 w-56 sm:w-72 truncate">
                    <Globe className="h-3 w-3 text-indigo-400 shrink-0" />
                    <span>https://fbverse.pages.dev</span>
                  </div>
                </div>

                {/* Viewport Mode Switcher (Desktop PC vs Real Mobile) */}
                <div className="flex items-center space-x-2">
                  <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800">
                    <button
                      onClick={() => setLandingPreviewMode('desktop')}
                      className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                        landingPreviewMode === 'desktop'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Monitor className="h-3.5 w-3.5" />
                      <span>PC Preview</span>
                    </button>
                    <button
                      onClick={() => setLandingPreviewMode('mobile')}
                      className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                        landingPreviewMode === 'mobile'
                          ? 'bg-indigo-600 text-white shadow-sm'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      <Smartphone className="h-3.5 w-3.5" />
                      <span>Mobile Preview (390px)</span>
                    </button>
                  </div>

                  <a
                    href="https://drive.google.com/drive/folders/1H3BDvhZQkvrTizcP9K3GMVZyq_CzH7j-?usp=sharing"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 shadow-md shadow-emerald-600/30 border border-emerald-400/30 transition-all"
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span>Download Setup (.exe)</span>
                  </a>

                  <button
                    onClick={() => setIframeKey(k => k + 1)}
                    title="Reload Preview Frame"
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-all"
                  >
                    <RotateCw className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Embedded Iframe - Adaptive Viewport */}
              <div className={`w-full bg-[#070b14] flex items-center justify-center transition-all ${
                landingPreviewMode === 'mobile' ? 'py-8 px-4 bg-slate-950/80' : ''
              }`}>
                {landingPreviewMode === 'mobile' ? (
                  <div className="w-[392px] max-w-full rounded-[44px] bg-slate-900 border-4 border-slate-700 shadow-2xl overflow-hidden p-2.5 relative">
                    {/* Simulated Smartphone Speaker Notch */}
                    <div className="w-28 h-4 bg-slate-800 rounded-full mx-auto mb-2 flex items-center justify-center">
                      <div className="w-3 h-3 rounded-full bg-slate-900"></div>
                    </div>
                    <div className="w-full h-[690px] rounded-[32px] overflow-hidden bg-[#060911] border border-slate-800">
                      <iframe
                        key={`mobile-${iframeKey}`}
                        src="/landing.html"
                        title="FB Auto Bot Mobile Viewport Preview"
                        className="w-full h-full border-0"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="w-full h-[720px] bg-[#060911]">
                    <iframe
                      key={`desktop-${iframeKey}`}
                      src="/landing.html"
                      title="FB Auto Bot Desktop Preview"
                      className="w-full h-full border-0"
                    />
                  </div>
                )}
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
                  const code = selectedFile === 'installer_setup.iss'
                    ? installerSetupSnippet
                    : selectedFile === 'build_installer.py'
                    ? buildInstallerSnippet
                    : selectedFile === 'landing_page/index.html'
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
                onClick={() => setSelectedFile('installer_setup.iss')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'installer_setup.iss'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <ShieldCheck className="h-3.5 w-3.5 text-amber-400" />
                <span>installer_setup.iss</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-amber-500/20 text-amber-300 rounded font-sans">Setup .EXE</span>
              </button>
              <button
                onClick={() => setSelectedFile('build_installer.py')}
                className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-mono font-medium transition-all ${
                  selectedFile === 'build_installer.py'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                }`}
              >
                <Zap className="h-3.5 w-3.5 text-yellow-300" />
                <span>build_installer.py</span>
                <span className="px-1.5 py-0.2 text-[10px] bg-yellow-500/20 text-yellow-300 rounded font-sans">Builder</span>
              </button>
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
                  <div className="pl-4 text-amber-400 font-bold">├── installer_setup.iss <span className="text-[10px] text-amber-300 font-normal">(Inno Setup)</span></div>
                  <div className="pl-4 text-yellow-400 font-bold">├── build_installer.py <span className="text-[10px] text-yellow-300 font-normal">(Auto Compiler)</span></div>
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
                  <span>Build Windows Setup Wizard (.exe)</span>
                </div>
                <div className="space-y-2">
                  <p className="text-slate-300">1. Run the one-click build script to generate Setup Wizard:</p>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] text-indigo-300 space-y-1">
                    <div>cd desktop_app</div>
                    <div className="text-yellow-300">python build_installer.py</div>
                    <div className="text-slate-500"># Or simply double click: build_installer.bat</div>
                  </div>
                  <p className="text-slate-300">2. Resulting professional setup files in <code className="text-amber-300">dist_installer/</code>:</p>
                  <div className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 font-mono text-[11px] text-emerald-400 space-y-1">
                    <div>FBAutoBot_Setup_v5.0.exe (Windows Setup Wizard with Desktop Shortcut)</div>
                    <div className="text-slate-400">FBAutoBot_v5.0_Windows_Portable.zip (Portable Zip)</div>
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
                    {selectedFile === 'installer_setup.iss' && 'desktop_app/installer_setup.iss (Inno Setup 6 Wizard Configuration)'}
                    {selectedFile === 'build_installer.py' && 'desktop_app/build_installer.py (PyInstaller + Inno Setup Automation)'}
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
                  {selectedFile === 'installer_setup.iss' ? 'Inno Setup Script • Windows Wizard • Uninstaller' : selectedFile === 'build_installer.py' ? 'PyInstaller --onedir • Inno ISCC Automation' : selectedFile === 'landing_page/index.html' ? 'HTML5 • Tailwind CDN • Vanilla JS • Glassmorphism' : selectedFile === 'ai_spinner.py' ? 'Google GenAI SDK • Prompt Engineering • Offline Regex Spintax' : selectedFile === 'session_manager.py' ? 'Isolated Profiles • Cookie Normalizer • Health Auditor' : selectedFile === 'image_processor.py' ? 'OpenCV • Pillow • Piexif' : selectedFile === 'browser_bot.py' ? 'Python AsyncIO • Playwright Stealth' : selectedFile === 'app.py' ? 'PyQt5 • QSS Dark Theme' : 'PIP Manifest'}
                </span>
              </div>
              <pre className="p-4 text-xs font-mono text-slate-300 overflow-x-auto max-h-[480px] leading-relaxed">
                <code>
                  {selectedFile === 'installer_setup.iss' && installerSetupSnippet}
                  {selectedFile === 'build_installer.py' && buildInstallerSnippet}
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
                  title: 'VIP High-Converting Landing Sales Page',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Redesigned landing page with VIP glassmorphism, mobile slide-out drawer, smart CTA conversions, comparison matrix, pricing tiers, and interactive FAQ accordion.'
                },
                {
                  phase: 'Phase 7 (Completed)',
                  title: 'Professional Windows Setup Wizard & Inno Packager',
                  status: 'Completed',
                  statusColor: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
                  desc: 'Built Inno Setup script (installer_setup.iss) and automated build_installer.py to compile FBAutoBot_Setup_v5.0.exe with desktop shortcuts, persistent license configs, and uninstaller.'
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

        {activeTab === 'columns-preview' && (
          <div className="space-y-6">
            {/* Header Box */}
            <div className={`border rounded-2xl p-6 shadow-xl relative overflow-hidden transition-colors ${
              theme === 'dark' ? 'bg-slate-900/90 border-slate-800/80 text-white' : 'bg-white border-slate-200 text-slate-900 shadow-md'
            }`}>
              <div className="absolute -top-12 -right-12 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2.5 mb-2">
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                      theme === 'dark' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' : 'bg-cyan-50 text-cyan-700 border-cyan-300'
                    }`}>
                      LIVE UI DESIGN & LAYOUT
                    </span>
                    <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
                      theme === 'dark' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-emerald-50 text-emerald-700 border-emerald-300'
                    }`}>
                      Standard & Project Tabs
                    </span>
                  </div>
                  <h2 className={`text-xl font-black tracking-tight ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                    Vehicle and Property Listing Column Specifications
                  </h2>
                  <p className={`text-xs mt-1 max-w-3xl leading-relaxed ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                    According to Facebook Marketplace guidelines, selecting <strong>"Vehicle for sale"</strong> dynamically loads all vehicle parameters, while selecting <strong>"Property for sale or rent"</strong> dynamically loads all property, rental, and structural parameters.
                  </p>
                </div>
                <div className="flex items-center space-x-3 shrink-0">
                  <a
                    href={listingFormsPreview}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-2 px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-lg shadow-indigo-500/25"
                  >
                    <ExternalLink className="h-4 w-4" />
                    <span>View Full Size Image</span>
                  </a>
                </div>
              </div>
            </div>

            {/* Visual Image Card */}
            <div className={`rounded-2xl border p-3.5 shadow-2xl overflow-hidden transition-colors ${
              theme === 'dark' ? 'border-slate-700/80 bg-slate-900/95 shadow-black/60' : 'border-slate-200 bg-white shadow-slate-200/80'
            }`}>
              <div className={`flex items-center justify-between px-3 py-2 border-b mb-3 text-xs ${
                theme === 'dark' ? 'border-slate-800/80 text-slate-400' : 'border-slate-200 text-slate-600'
              }`}>
                <span className={`font-semibold flex items-center gap-2 ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>
                  <ImageIcon className="h-4 w-4 text-cyan-500" />
                  UI Mockup: Vehicle for Sale vs Property for Sale/Rent Columns
                </span>
                <span className={`text-[11px] ${theme === 'dark' ? 'text-slate-500' : 'text-slate-400'}`}>16:9 High Resolution Preview</span>
              </div>
              <div className={`relative group rounded-xl overflow-hidden border flex items-center justify-center ${
                theme === 'dark' ? 'border-slate-800 bg-slate-950' : 'border-slate-200 bg-slate-100'
              }`}>
                <img
                  src={listingFormsPreview}
                  alt="Facebook Marketplace Vehicle and Property Listing Forms Columns"
                  className="w-full h-auto max-h-[640px] object-contain transition-transform duration-300 group-hover:scale-[1.01]"
                  referrerPolicy="no-referrer"
                />
              </div>
            </div>

            {/* Detailed Field-by-Field Breakdown Columns */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Card 1: Vehicle for Sale */}
              <div className={`border rounded-2xl p-5 shadow-xl space-y-4 transition-colors ${
                theme === 'dark' ? 'bg-slate-900/90 border-slate-800/80' : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className={`flex items-center space-x-3 pb-3 border-b ${theme === 'dark' ? 'border-slate-800' : 'border-slate-200'}`}>
                  <div className="h-9 w-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-500 flex items-center justify-center font-bold text-base">
                    🚗
                  </div>
                  <div>
                    <h3 className={`text-sm font-black ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                      Vehicle for Sale Fields
                    </h3>
                    <p className={`text-[11px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>
                      Facebook Marketplace vehicle specific parameters
                    </p>
                  </div>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>1. Vehicle Type:</span>
                    <span className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                      theme === 'dark' ? 'text-cyan-400 bg-cyan-950/50 border-cyan-800/50' : 'text-cyan-800 bg-cyan-100 border-cyan-300 font-bold'
                    }`}>
                      Car/Truck, Motorcycle, RV/Camper, Boat, etc.
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>2. Vehicle Year:</span>
                    <span className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                      theme === 'dark' ? 'text-cyan-400 bg-cyan-950/50 border-cyan-800/50' : 'text-cyan-800 bg-cyan-100 border-cyan-300 font-bold'
                    }`}>
                      2026 to 1980 Dropdown
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>3. Vehicle Make:</span>
                    <span className={`font-mono text-[11px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      e.g., Toyota, Honda, Ford, BMW, Hyundai
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>4. Vehicle Model:</span>
                    <span className={`font-mono text-[11px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      e.g., Camry, Civic, F-150, Corolla
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>5. Price ($ USD):</span>
                    <span className={`font-mono text-[11px] font-bold ${theme === 'dark' ? 'text-emerald-400' : 'text-emerald-700'}`}>
                      Vehicle price (e.g., $15,000)
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>6. ID Location (Account Radius):</span>
                    <span className={`font-mono text-[11px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      Facebook homepage account location switcher
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex flex-col gap-1 ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>7. Target Locations / Cities Pool:</span>
                    <span className={`text-[11px] leading-relaxed ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      Multi-location pool (each tab automatically receives a distinct location)
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex flex-col gap-1 ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>8. Vehicle Description:</span>
                    <span className={`text-[11px] leading-relaxed ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      Vehicle features, mileage, clean title, and condition details
                    </span>
                  </div>
                </div>
              </div>

              {/* Card 2: Property for Sale or Rent */}
              <div className={`border rounded-2xl p-5 shadow-xl space-y-4 transition-colors ${
                theme === 'dark' ? 'bg-slate-900/90 border-slate-800/80' : 'bg-white border-slate-200 shadow-sm'
              }`}>
                <div className={`flex items-center space-x-3 pb-3 border-b ${theme === 'dark' ? 'border-slate-800' : 'border-slate-200'}`}>
                  <div className="h-9 w-9 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-500 flex items-center justify-center font-bold text-base">
                    🏠
                  </div>
                  <div>
                    <h3 className={`text-sm font-black ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                      Property for Sale or Rent Fields
                    </h3>
                    <p className={`text-[11px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>
                      Facebook property and rental specific parameters & specs
                    </p>
                  </div>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>1. Rental / Sale Classification:</span>
                    <span className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                      theme === 'dark' ? 'text-purple-400 bg-purple-950/50 border-purple-800/50' : 'text-purple-800 bg-purple-100 border-purple-300 font-bold'
                    }`}>
                      Rent or Sale
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>2. Property Type:</span>
                    <span className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                      theme === 'dark' ? 'text-purple-400 bg-purple-950/50 border-purple-800/50' : 'text-purple-800 bg-purple-100 border-purple-300 font-bold'
                    }`}>
                      Apartment & Condo, House, Townhouse, Room only
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>3. Number of Bedrooms:</span>
                    <span className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                      theme === 'dark' ? 'text-purple-400 bg-purple-950/50 border-purple-800/50' : 'text-purple-800 bg-purple-100 border-purple-300 font-bold'
                    }`}>
                      1, 2, 3, 4, 5+
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>4. Number of Bathrooms:</span>
                    <span className={`font-mono text-[11px] px-2 py-0.5 rounded border ${
                      theme === 'dark' ? 'text-purple-400 bg-purple-950/50 border-purple-800/50' : 'text-purple-800 bg-purple-100 border-purple-300 font-bold'
                    }`}>
                      1, 1.5, 2, 2.5, 3, 3+
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>5. Price ($ USD / Monthly Rent or Sale Price):</span>
                    <span className={`font-mono text-[11px] font-bold ${theme === 'dark' ? 'text-emerald-400' : 'text-emerald-700'}`}>
                      e.g., $1,800 / month
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex items-center justify-between ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>6. ID Location (Account Radius):</span>
                    <span className={`font-mono text-[11px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      Facebook homepage account location switcher
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex flex-col gap-1 ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>7. Target Locations / Cities Pool:</span>
                    <span className={`text-[11px] leading-relaxed ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      Target area list (e.g., Brooklyn, NY / Queens, NY)
                    </span>
                  </div>
                  <div className={`p-2.5 rounded-lg border flex flex-col gap-1 ${
                    theme === 'dark' ? 'bg-slate-950/60 border-slate-800/60' : 'bg-slate-50 border-slate-200'
                  }`}>
                    <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>8. Property Description:</span>
                    <span className={`text-[11px] leading-relaxed ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      Utilities, deposit terms, furnished/unfurnished status, and amenities
                    </span>
                  </div>

                  {/* Advanced Property Fields */}
                  <div className={`pt-2 border-t ${theme === 'dark' ? 'border-slate-800/80' : 'border-slate-200'}`}>
                    <span className={`text-[11px] font-bold uppercase tracking-wider block mb-2 ${
                      theme === 'dark' ? 'text-amber-400' : 'text-amber-700'
                    }`}>
                      ⭐ Advanced Property Specifications
                    </span>
                    <div className="space-y-2">
                      <div className={`p-2 rounded-lg border flex items-center justify-between ${
                        theme === 'dark' ? 'bg-slate-950/80 border-amber-500/20 text-slate-300' : 'bg-amber-50/80 border-amber-200 text-slate-800'
                      }`}>
                        <span className={`font-semibold text-[11px] ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>9. Square Feet:</span>
                        <span className={`font-mono text-[11px] font-bold ${theme === 'dark' ? 'text-amber-300' : 'text-amber-800'}`}>e.g., 1250 sqft</span>
                      </div>
                      <div className={`p-2 rounded-lg border flex items-center justify-between ${
                        theme === 'dark' ? 'bg-slate-950/80 border-amber-500/20 text-slate-300' : 'bg-amber-50/80 border-amber-200 text-slate-800'
                      }`}>
                        <span className={`font-semibold text-[11px] ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>10. Laundry:</span>
                        <span className={`font-mono text-[10px] text-right font-medium ${theme === 'dark' ? 'text-amber-300' : 'text-amber-800'}`}>In-unit, In building, Available, None</span>
                      </div>
                      <div className={`p-2 rounded-lg border flex items-center justify-between ${
                        theme === 'dark' ? 'bg-slate-950/80 border-amber-500/20 text-slate-300' : 'bg-amber-50/80 border-amber-200 text-slate-800'
                      }`}>
                        <span className={`font-semibold text-[11px] ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>11. Parking Type:</span>
                        <span className={`font-mono text-[10px] text-right font-medium ${theme === 'dark' ? 'text-amber-300' : 'text-amber-800'}`}>Garage, Street, Off-street, Spot, None</span>
                      </div>
                      <div className={`p-2 rounded-lg border flex items-center justify-between ${
                        theme === 'dark' ? 'bg-slate-950/80 border-amber-500/20 text-slate-300' : 'bg-amber-50/80 border-amber-200 text-slate-800'
                      }`}>
                        <span className={`font-semibold text-[11px] ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>12. Air Conditioning:</span>
                        <span className={`font-mono text-[10px] text-right font-medium ${theme === 'dark' ? 'text-amber-300' : 'text-amber-800'}`}>Central AC, AC available, None</span>
                      </div>
                      <div className={`p-2 rounded-lg border flex items-center justify-between ${
                        theme === 'dark' ? 'bg-slate-950/80 border-amber-500/20 text-slate-300' : 'bg-amber-50/80 border-amber-200 text-slate-800'
                      }`}>
                        <span className={`font-semibold text-[11px] ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>13. Heating Type:</span>
                        <span className={`font-mono text-[10px] text-right font-medium ${theme === 'dark' ? 'text-amber-300' : 'text-amber-800'}`}>Central, Electric, Gas, Radiator, None</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Interactive Image Dropdown Showcase */}
            <div className={`border rounded-2xl p-6 shadow-2xl space-y-4 relative overflow-hidden transition-colors ${
              theme === 'dark' ? 'bg-slate-900/90 border-cyan-500/30' : 'bg-white border-cyan-500/40 shadow-slate-200/80'
            }`}>
              <div className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b ${
                theme === 'dark' ? 'border-slate-800' : 'border-slate-200'
              }`}>
                <div className="flex items-center space-x-3">
                  <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-500 flex items-center justify-center font-bold text-lg">
                    📸
                  </div>
                  <div>
                    <h3 className={`text-base font-black flex items-center gap-2 ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                      <span>Interactive Collapsible Image Dropdown System</span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        theme === 'dark' ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30' : 'bg-cyan-100 text-cyan-800 border-cyan-300'
                      }`}>
                        Live Interactive Demo
                      </span>
                    </h3>
                    <p className={`text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                      Standard Bulk Listing and Project Listing display attached photos in a clean collapsible dropdown menu
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => {
                      const newSamples = [
                        'exterior_balcony_view.jpg',
                        'luxury_master_bath.jpg',
                        'car_front_bumper_angle.jpg',
                        'engine_bay_overview.jpg',
                        'garage_double_parking.jpg'
                      ];
                      const pick = newSamples[Math.floor(Math.random() * newSamples.length)];
                      const numbered = `${Math.floor(Math.random() * 900 + 100)}_${pick}`;
                      setDemoImages(prev => [...prev, numbered]);
                      setIsDemoDropdownOpen(true);
                    }}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
                      theme === 'dark' ? 'bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-300 border-cyan-500/40' : 'bg-cyan-50 hover:bg-cyan-100 text-cyan-800 border-cyan-300 font-bold'
                    }`}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    <span>Add Sample Image</span>
                  </button>
                  <button
                    onClick={() => {
                      setDemoImages([]);
                    }}
                    className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
                      theme === 'dark' ? 'bg-red-600/20 hover:bg-red-600/30 text-red-300 border-red-500/40' : 'bg-red-50 hover:bg-red-100 text-red-700 border-red-300 font-bold'
                    }`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Clear All</span>
                  </button>
                </div>
              </div>

              {/* The Actual Dropdown UI Demonstration */}
              <div className={`max-w-2xl mx-auto border rounded-xl p-4 shadow-inner transition-colors ${
                theme === 'dark' ? 'bg-slate-950/90 border-slate-800' : 'bg-slate-50 border-slate-200'
              }`}>
                <div className={`mb-2 flex items-center justify-between text-xs ${theme === 'dark' ? 'text-slate-400' : 'text-slate-600'}`}>
                  <span className={`font-semibold ${theme === 'dark' ? 'text-slate-300' : 'text-slate-800'}`}>Selected Product / Property Images:</span>
                  <span className={`text-[11px] ${theme === 'dark' ? 'text-slate-500' : 'text-slate-500'}`}>Click button below to expand/collapse</span>
                </div>

                {/* Collapsible Dropdown Toggle Button */}
                <button
                  onClick={() => setIsDemoDropdownOpen(!isDemoDropdownOpen)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl border text-xs font-bold transition-all shadow-md ${
                    isDemoDropdownOpen
                      ? theme === 'dark' ? 'bg-slate-800 border-cyan-500/60 text-cyan-300 shadow-cyan-500/10' : 'bg-white border-cyan-500 text-cyan-800 shadow-cyan-500/15'
                      : theme === 'dark' ? 'bg-slate-900 hover:bg-slate-800/80 border-slate-700/80 text-slate-200' : 'bg-white hover:bg-slate-100 border-slate-300 text-slate-800'
                  }`}
                >
                  <div className="flex items-center space-x-2 truncate">
                    <span className="text-base">📁</span>
                    <span className="truncate">
                      {demoImages.length === 0
                        ? 'No images selected (0 files) - Click browse to add'
                        : `Uploaded Images (${demoImages.length} file${demoImages.length > 1 ? 's' : ''}) - Last: ${demoImages[demoImages.length - 1]}`}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1.5 shrink-0 ml-2">
                    <span className={`text-[11px] font-mono ${theme === 'dark' ? 'text-cyan-400' : 'text-cyan-700 font-bold'}`}>
                      {isDemoDropdownOpen ? 'Collapse' : 'Expand'}
                    </span>
                    {isDemoDropdownOpen ? (
                      <ChevronUp className={`h-4 w-4 ${theme === 'dark' ? 'text-cyan-400' : 'text-cyan-700'}`} />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-slate-400" />
                    )}
                  </div>
                </button>

                {/* Expandable Image List Panel */}
                {isDemoDropdownOpen && (
                  <div className={`mt-2.5 p-3 rounded-xl border space-y-2 max-h-64 overflow-y-auto ${
                    theme === 'dark' ? 'bg-slate-900/90 border-slate-800' : 'bg-white border-slate-200'
                  }`}>
                    {demoImages.length === 0 ? (
                      <div className="py-6 text-center text-xs text-slate-500">
                        No images selected yet. Click &quot;Add Sample Image&quot; above.
                      </div>
                    ) : (
                      demoImages.map((img, idx) => (
                        <div
                          key={idx}
                          className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs transition-colors ${
                            theme === 'dark'
                              ? 'bg-slate-800/80 hover:bg-slate-800 border-slate-700/70 text-slate-200'
                              : 'bg-slate-50 hover:bg-slate-100 border-slate-200 text-slate-800'
                          }`}
                        >
                          <div className="flex items-center space-x-2.5 truncate">
                            <span className={`font-extrabold text-[11px] min-w-[24px] ${theme === 'dark' ? 'text-cyan-400' : 'text-cyan-700'}`}>#{idx + 1}</span>
                            <span className="text-base">🖼️</span>
                            <span className={`font-medium truncate ${theme === 'dark' ? 'text-slate-200' : 'text-slate-800'}`}>{img}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded border ${
                              theme === 'dark' ? 'text-slate-400 bg-slate-900 border-slate-700/50' : 'text-slate-600 bg-slate-200 border-slate-300'
                            }`}>
                              {(2.1 + (idx * 0.4)).toFixed(1)} MB
                            </span>
                          </div>

                          <button
                            onClick={() => {
                              setDemoImages(demoImages.filter((_, i) => i !== idx));
                            }}
                            className="flex items-center space-x-1 px-2.5 py-1 rounded bg-red-500/20 hover:bg-red-500 text-red-300 hover:text-white border border-red-500/30 text-[11px] font-bold transition-all shrink-0 ml-2"
                          >
                            <Trash2 className="h-3 w-3" />
                            <span>Remove</span>
                          </button>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'admin-panel' && (
          <AdminPanel
            onBackToApp={() => {
              setActiveTab('landing-page');
              try {
                window.history.pushState(null, '', '/');
              } catch (e) {
                window.location.hash = '';
              }
            }}
          />
        )}

        {/* 2027 Futuristic Cookie / Account Import Notification Modal (Directly testable in both Dark & Light Themes) */}
        {showCookiePopup && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div
              className={`w-full max-w-lg rounded-2xl p-6 shadow-2xl transition-all border transform scale-100 relative ${
                theme === 'dark'
                  ? 'bg-slate-900/95 border-slate-700/80 text-white shadow-black/80'
                  : 'bg-white border-slate-200 text-slate-900 shadow-2xl'
              }`}
            >
              <div className="flex items-start space-x-4">
                <div className="h-11 w-11 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-500 shrink-0 shadow-sm">
                  <CheckCircle2 className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className={`text-base font-black tracking-tight ${theme === 'dark' ? 'text-white' : 'text-slate-900'}`}>
                      {cookieNotificationData.title}
                    </h3>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      theme === 'dark'
                        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                        : 'bg-emerald-100 text-emerald-800 border-emerald-300'
                    }`}>
                      ● LIVE POPUP AUDIT
                    </span>
                  </div>
                  <p className={`text-xs mt-1.5 leading-relaxed ${theme === 'dark' ? 'text-slate-300' : 'text-slate-600'}`}>
                    {cookieNotificationData.message}
                  </p>

                  <div className={`mt-3.5 p-3 rounded-xl text-xs font-mono border space-y-1.5 ${
                    theme === 'dark'
                      ? 'bg-slate-950/80 border-slate-800 text-emerald-400'
                      : 'bg-slate-50 border-slate-200 text-emerald-700'
                  }`}>
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-sky-500">ID 1: FB_61594735472478</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 font-bold">HEALTHY</span>
                    </div>
                    <div className="text-[11px] truncate opacity-90">
                      c_user=61594735472478; xs=29%3A9Z...; datr=x84_Z...;
                    </div>
                    <div className="flex items-center justify-between pt-1 border-t border-slate-800/40">
                      <span className="font-semibold text-sky-500">ID 2: FB_10008492019482</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 font-bold">HEALTHY</span>
                    </div>
                    <div className="text-[11px] truncate opacity-90">
                      c_user=10008492019482; xs=41%3Af3...; datr=w73_A...;
                    </div>
                  </div>

                  <div className="mt-5 flex items-center justify-between">
                    <span className={`text-[11px] ${theme === 'dark' ? 'text-slate-400' : 'text-slate-500'}`}>
                      Active Theme: <strong>{theme === 'dark' ? '2027 Cyber Dark' : '2027 Futuristic Light'}</strong>
                    </span>
                    <button
                      id="btn-close-cookie-popup"
                      onClick={() => setShowCookiePopup(false)}
                      className="px-6 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 shadow-md shadow-indigo-500/25 cursor-pointer transition-all active:scale-95"
                    >
                      OK (Done)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
