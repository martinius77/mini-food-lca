// Live comparison. Inputs and outputs share one block per food, so we can't
// swap an innerHTML container (it would destroy the live controls). Instead the
// server returns formatted display strings as JSON and we set them as
// textContent. No calculation or number formatting happens here — Python is the
// single source of truth. This page requires JavaScript by design.

(function () {
  "use strict";

  var form = document.getElementById("compare-form");
  var cols = document.querySelector(".columns");
  var verdictEl = document.getElementById("verdict");
  if (!form || !cols) return;

  var STORAGE_KEY = "mini-food-lca:selections";
  var FIELDS = [
    "food_a", "qty_a", "unit_a", "origin_a",
    "food_b", "qty_b", "unit_b", "origin_b",
  ];
  var SIDES = ["a", "b"];

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

  // Fill each target element <key>-<side> with the server-provided string.
  function applyData(json) {
    SIDES.forEach(function (side) {
      var data = json[side];
      if (!data) return;
      Object.keys(data).forEach(function (key) {
        var el = document.getElementById(key + "-" + side);
        if (el) el.textContent = data[key];
      });
    });
    if (verdictEl && typeof json.verdict === "string") {
      verdictEl.textContent = json.verdict;
    }
  }

  function flashHighlight() {
    // Gentle ~300ms flash on the updated numbers (the carbon heroes + verdict).
    [
      document.getElementById("carbon-a"),
      document.getElementById("carbon-b"),
      verdictEl,
    ].forEach(function (el) {
      if (!el) return;
      el.classList.remove("just-updated");
      void el.offsetWidth; // force reflow so the animation can replay
      el.classList.add("just-updated");
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

    cols.classList.add("loading");
    cols.setAttribute("aria-busy", "true");

    fetch("/compare/live?" + qs, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    })
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
      })
      .then(function (json) {
        applyData(json);
        cols.classList.remove("loading");
        cols.setAttribute("aria-busy", "false");
        inFlight = null;
        flashHighlight();
      })
      .catch(function (err) {
        if (err && err.name === "AbortError") return; // superseded; do nothing
        // Network/server error: keep the last good numbers, just log it.
        console.error("Live update failed:", err);
        cols.classList.remove("loading");
        cols.setAttribute("aria-busy", "false");
        if (inFlight === controller) inFlight = null;
      });
  }

  function scrollResultsIntoView() {
    var rect = cols.getBoundingClientRect();
    var fullyVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;
    if (!fullyVisible) {
      cols.scrollIntoView({ behavior: "smooth", block: "start" });
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
