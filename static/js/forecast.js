/* forecast.js — 24h AI forecast card (direction + likely range only, no entry points). */
(function () {
  var box = document.getElementById("fc");
  if (!box) return;
  var EN = !!window.FC_EN, base = window.API_BASE || "";
  var T = EN
    ? { up: "Leaning up", down: "Leaning down", flat: "Sideways", sub: "next 24h", ago: function (m) { return "Updated " + (m < 1 ? "just now" : m + " min ago") + "."; } }
    : { up: "تمایل صعودی", down: "تمایل نزولی", flat: "خنثی / رنج", sub: "۲۴ ساعت آینده", ago: function (m) { return "به‌روزرسانی: " + (m < 1 ? "همین الان" : String(m).replace(/\d/g, function (d) { return "۰۱۲۳۴۵۶۷۸۹"[d]; }) + " دقیقه پیش") + "."; } };
  var $ = function (id) { return document.getElementById(id); };
  var data = null, cur = "BTC";

  function usd(v) {
    if (v == null || !isFinite(v)) return "—";
    var d = v >= 1000 ? 0 : v >= 1 ? 2 : 4;
    return "$" + v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function pct(v) { return (v > 0 ? "+" : "") + (v * 100).toFixed(2) + "%"; }

  function chart(c) {
    var svg = $("fc-chart"), W = 600, H = 200, P = 10;
    var h = c.history, n = h.length, m = c.median.length, all = h.concat(c.p10, c.p90);
    var lo = Math.min.apply(null, all), hi = Math.max.apply(null, all), pad = (hi - lo) * 0.08 || 1;
    lo -= pad; hi += pad;
    var X = function (i) { return P + (W - 2 * P) * i / (n + m - 1); };
    var Y = function (v) { return P + (H - 2 * P) * (1 - (v - lo) / (hi - lo)); };
    var line = function (arr, off) { return arr.map(function (v, i) { return (i ? "L" : "M") + X(i + off).toFixed(1) + " " + Y(v).toFixed(1); }).join(""); };
    var lastI = n - 1, last = h[lastI];
    var up = [last].concat(c.p90), dn = [last].concat(c.p10);
    var band = line(up, lastI) + dn.slice().reverse().map(function (v, i) { return "L" + X(lastI + dn.length - 1 - i).toFixed(1) + " " + Y(v).toFixed(1); }).join("") + "Z";
    var col = c.bias === "up" ? "var(--up)" : c.bias === "down" ? "var(--down)" : "var(--signal)";
    var lg = box.querySelector(".l-med");
    if (lg) lg.style.borderTopColor = col;
    svg.innerHTML =
      '<line x1="' + X(lastI) + '" x2="' + X(lastI) + '" y1="0" y2="' + H + '" stroke="var(--line)" stroke-dasharray="3 4"/>' +
      '<path d="' + band + '" fill="var(--signal-soft)"/>' +
      '<path d="' + line(h, 0) + '" fill="none" stroke="var(--fg)" stroke-width="1.6" vector-effect="non-scaling-stroke"/>' +
      '<path d="' + line([last].concat(c.median), lastI) + '" fill="none" stroke="' + col + '" stroke-width="2" stroke-dasharray="5 4" vector-effect="non-scaling-stroke"/>' +
      '<circle cx="' + X(lastI) + '" cy="' + Y(last) + '" r="3.5" fill="var(--fg)"/>';
  }

  function show(sym) {
    cur = sym;
    var c = data.coins[sym];
    Array.prototype.forEach.call($("fc-tabs").children, function (b) { b.setAttribute("aria-selected", b.dataset.s === sym ? "true" : "false"); });
    var b = $("fc-bias");
    b.className = "fc-bias " + c.bias;
    b.innerHTML = T[c.bias] + "<small>" + T.sub + "</small>";
    $("fc-last").textContent = usd(c.last);
    var chg = $("fc-chg");
    chg.textContent = pct(c.chg_24h);
    chg.className = "num " + (c.chg_24h > 0 ? "up" : c.chg_24h < 0 ? "down" : "");
    $("fc-up").textContent = Math.round(c.up_share * 100) + "%";
    $("fc-range").textContent = c.range_24h.length === 2 ? usd(c.range_24h[0]) + " – " + usd(c.range_24h[1]) : "—";
    $("fc-age").textContent = T.ago(data.age_min || 0);
    chart(c);
  }

  function load() {
    fetch(base + "/api/forecast").then(function (r) { return r.json(); }).then(function (d) {
      if (!d || !d.ok || !d.forecast || !d.forecast.coins) return;
      data = d.forecast;
      var syms = ["BTC", "ETH", "SOL", "XRP"].filter(function (s) { return data.coins[s]; });
      if (!syms.length) return;
      $("fc-tabs").innerHTML = syms.map(function (s) { return '<button type="button" role="tab" data-s="' + s + '">' + s + "</button>"; }).join("");
      Array.prototype.forEach.call($("fc-tabs").children, function (btn) { btn.onclick = function () { show(btn.dataset.s); }; });
      box.hidden = false;
      var wait = document.getElementById("fc-wait");
      if (wait) wait.hidden = true;
      show(data.coins[cur] ? cur : syms[0]);
    }).catch(function () {});
  }
  load();
  setInterval(load, 10 * 60 * 1000);
})();
