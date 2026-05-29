// Live comparison: the form's current values are sent to the server, which
// returns rendered HTML for the cards. No calculation happens here — Python is
// the single source of truth. This page requires JavaScript by design.

(function () {
  "use strict";

  var form = document.getElementById("compare-form");
  var results = document.getElementById("results");
  var wrap = document.querySelector(".results-wrap");
  if (!form || !results || !wrap) return;

  var STORAGE_KEY = "mini-food-lca:selections";
  var FIELDS = [
    "food_a", "qty_a", "unit_a", "origin_a",
    "food_b", "qty_b", "unit_b", "origin_b",
  ];

  var inFlight = null; // current AbortController, so a newer change can cancel it.
  var lastQuery = null; // dedupe: a select fires both "input" and "change".

  // --- selection persistence (survives the language-switch page reload) ------

  function saveSelections() {
    var data = {};
    FIELDS.forEach(function (name) {
      var el = form.elements[name];
      if (el) data[name] = el.value;
    });
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      /* sessionStorage unavailable (private mode); persistence is best-effort */
    }
  }

  function restoreSelections() {
    var raw;
    try {
      raw = sessionStorage.getItem(STORAGE_KEY);
    } catch (e) {
      return;
    }
    if (!raw) return;
    var data;
    try {
      data = JSON.parse(raw);
    } catch (e) {
      return;
    }
    // Option values are language-independent codes, so they re-select under
    // either language.
    FIELDS.forEach(function (name) {
      var el = form.elements[name];
      if (el && data[name] != null) el.value = data[name];
    });
  }

  // --- live update -----------------------------------------------------------

  function queryString() {
    var params = new URLSearchParams();
    FIELDS.forEach(function (name) {
      var el = form.elements[name];
      if (el) params.set(name, el.value);
    });
    return params.toString();
  }

  function flashHighlight() {
    // Gentle ~300ms background flash so it's visible the numbers changed.
    // Re-trigger by removing then forcing reflow before re-adding.
    var cards = results.querySelectorAll(".card");
    cards.forEach(function (card) {
      card.classList.remove("just-updated");
      // eslint-disable-next-line no-unused-expressions
      void card.offsetWidth; // force reflow so the animation can replay
      card.classList.add("just-updated");
    });
  }

  function update() {
    var qs = queryString();
    // A <select> change fires both "input" and "change"; skip the duplicate.
    if (qs === lastQuery) return;
    lastQuery = qs;

    // Cancel any request still in flight; only the newest result should land.
    if (inFlight) inFlight.abort();
    var controller = new AbortController();
    inFlight = controller;

    wrap.classList.add("loading");
    results.setAttribute("aria-busy", "true");

    fetch("/compare/live?" + qs, { signal: controller.signal })
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.text();
      })
      .then(function (html) {
        results.innerHTML = html;
        wrap.classList.remove("loading");
        results.setAttribute("aria-busy", "false");
        inFlight = null;
        flashHighlight();
      })
      .catch(function (err) {
        if (err && err.name === "AbortError") return; // superseded; do nothing
        // Network/server error: keep the last good results, just log it.
        // Never blank the results.
        console.error("Live update failed:", err);
        wrap.classList.remove("loading");
        results.setAttribute("aria-busy", "false");
        if (inFlight === controller) inFlight = null;
      });
  }

  function scrollResultsIntoView() {
    var rect = results.getBoundingClientRect();
    var fullyVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;
    if (!fullyVisible) {
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // --- events ----------------------------------------------------------------

  // Every keystroke in the quantity field updates (no debounce); same for any
  // other input. We do NOT scroll on typing.
  form.addEventListener("input", function () {
    saveSelections();
    update();
  });

  // Dropdowns / unit select fire "change". Update, then bring results into view.
  form.addEventListener("change", function (e) {
    saveSelections();
    update();
    if (e.target && e.target.type !== "number") {
      scrollResultsIntoView();
    }
  });

  // --- boot ------------------------------------------------------------------

  restoreSelections();
  update(); // show beef vs tofu (or restored picks) immediately
})();
