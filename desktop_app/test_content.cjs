const fs = require("fs");
const vm = require("vm");

let contentCode = fs.readFileSync("desktop_app/FewFeedV3.9.1/content.js", "utf8");

const sandbox = {
  document: {
    querySelector: (sel) => {
        console.log("querySelector:", sel);
        return null;
    },
    querySelectorAll: () => [],
    head: {},
    body: {},
    documentElement: {}
  },
  MutationObserver: class {
    observe() {}
    disconnect() {}
  },
  chrome: {
    runtime: {
      onMessage: { addListener: (fn) => console.log("Listener added") },
      sendMessage: (msg, cb) => {
          console.log("chrome.runtime.sendMessage:", msg);
          if (cb) cb({ status: true });
      },
      id: "fewfeed_ext_id"
    }
  },
  fetch: async (url) => {
      console.log("FETCH:", url);
      return { ok: true, json: async () => ({ status: true, user: { id: 1 } }) };
  },
  localStorage: {
    getItem: (k) => { console.log("getItem:", k); return null; },
    setItem: (k, v) => console.log("localStorage set:", k, v)
  },
  console: console
};

const ctx = vm.createContext(sandbox);
vm.runInContext(contentCode, ctx);
console.log("Run finished.");
