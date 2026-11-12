const fs = require("fs");
const vm = require("vm");

const TEXT = new Set(["innerHTML", "outerHTML", "textContent", "nodeName", "tagName", "namespaceURI", "data", "value", "id", "className", "href"]);

function fake(overrides = {}) {
  return new Proxy(function () {}, {
    get(target, key) {
      if (key in overrides) return overrides[key];
      if (key === Symbol.toPrimitive) return () => "";
      if (key === Symbol.iterator || key === "then") return undefined;
      if (key === "nextNode") return () => null;
      if (key === "length") return 0;
      if (TEXT.has(key)) return "";
      if (key === "style" || key === "prototype") return {};
      return fake();
    },
    apply: () => fake(),
    construct: () => fake(),
    set: () => true,
  });
}

const type = () => function () {};
const window = {
  document: fake({ nodeType: 9, readyState: "complete", currentScript: null }),
  console, setTimeout, clearTimeout, structuredClone, TextEncoder, TextDecoder, URL,
  addEventListener() {},
  removeEventListener() {},
  navigator: { userAgent: "node" },
  location: { href: "" },
  Element: type(),
  Node: type(),
  HTMLFormElement: type(),
  DocumentFragment: type(),
  NamedNodeMap: type(),
  NodeFilter: { SHOW_ELEMENT: 1, SHOW_TEXT: 4, SHOW_CDATA_SECTION: 8, SHOW_PROCESSING_INSTRUCTION: 64, SHOW_COMMENT: 128 },
  DOMParser: class {
    parseFromString() {
      return fake();
    }
  },
};
window.window = window;
window.self = window;

const context = vm.createContext(window);
vm.runInContext(fs.readFileSync(process.argv[2], "utf8"), context);
const blocks = JSON.parse(fs.readFileSync(0, "utf8"));

(async () => {
  const results = [];
  for (const block of blocks) {
    try {
      await context.mermaid.parse(block);
      results.push("");
    } catch (error) {
      results.push(String(error.message || error).split("\n")[0] || "parse error");
    }
  }
  console.log(JSON.stringify(results));
  process.exit(0);
})();
