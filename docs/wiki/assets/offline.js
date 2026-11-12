(function () {
  if (location.protocol !== "file:" || !window.WIKI_PAGES) return;
  var base = location.href.replace(/[?#].*$/, "").replace(/[^/]*$/, "");

  function Offline() {
    this.listeners = {};
    this.readyState = 0;
    this.status = 0;
    this.response = "";
  }
  Offline.prototype.open = function (method, url) {
    this.url = url;
  };
  Offline.prototype.setRequestHeader = function () {};
  Offline.prototype.getResponseHeader = function () {
    return null;
  };
  Offline.prototype.abort = function () {};
  Offline.prototype.addEventListener = function (name, handler) {
    (this.listeners[name] = this.listeners[name] || []).push(handler);
  };
  Offline.prototype.send = function () {
    var self = this;
    var path = decodeURIComponent(new URL(this.url, base).href.slice(base.length)).replace(/[?#].*$/, "");
    var page = window.WIKI_PAGES[path];
    setTimeout(function () {
      self.readyState = 4;
      self.status = page === undefined ? 404 : 200;
      self.response = self.responseText = page || "";
      ["load", "loadend"].forEach(function (name) {
        (self.listeners[name] || []).forEach(function (handler) {
          handler({ target: self });
        });
      });
    }, 0);
  };
  window.XMLHttpRequest = Offline;
})();
