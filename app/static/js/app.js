(function () {
  "use strict";
  const root = document.documentElement;

  // ----- theme toggle (remembered per browser) -----
  const themeBtn = document.getElementById("themeToggle");
  function setTheme(mode) {
    root.dataset.theme = mode;
    if (themeBtn) themeBtn.innerHTML = mode === "dark" ? '<i class="bi bi-sun"></i>' : '<i class="bi bi-moon-stars"></i>';
    try { localStorage.setItem("vh-theme", mode); } catch (e) { /* storage unavailable */ }
  }
  setTheme(root.dataset.theme || "light");
  themeBtn && themeBtn.addEventListener("click", () => setTheme(root.dataset.theme === "dark" ? "light" : "dark"));

  // ----- navbar shadow + mobile menu + user dropdown -----
  const nav = document.querySelector(".nav");
  const onScroll = () => nav && nav.classList.toggle("scrolled", window.scrollY > 8);
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
  const burger = document.getElementById("burger");
  burger && burger.addEventListener("click", () => nav.classList.toggle("menu-open"));

  document.querySelectorAll(".user-menu").forEach((menu) => {
    menu.querySelector(".user-chip").addEventListener("click", (e) => {
      e.stopPropagation();
      menu.classList.toggle("open");
    });
  });
  document.addEventListener("click", () => document.querySelectorAll(".user-menu.open").forEach((m) => m.classList.remove("open")));

  // ----- reveal on scroll (staggered) + progress bars + counters -----
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      el.classList.add("in");
      el.querySelectorAll(".progress > span[data-w]").forEach((bar) => (bar.style.width = bar.dataset.w + "%"));
      el.querySelectorAll("[data-count]").forEach(countUp);
      io.unobserve(el);
    });
  }, { threshold: 0.12 });

  document.querySelectorAll("[data-stagger]").forEach((group) => {
    [...group.children].forEach((child, i) => {
      child.classList.add("reveal");
      child.style.setProperty("--d", (i * 0.08).toFixed(2) + "s");
    });
  });
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
  // elements already on screen animate in right away, even if the observer is throttled
  setTimeout(() => {
    document.querySelectorAll(".reveal:not(.in)").forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.top < window.innerHeight && r.bottom > 0) {
        el.classList.add("in");
        el.querySelectorAll(".progress > span[data-w]").forEach((bar) => (bar.style.width = bar.dataset.w + "%"));
        el.querySelectorAll("[data-count]").forEach(countUp);
        io.unobserve(el);
      }
    });
  }, 60);

  function countUp(el) {
    const target = parseInt(el.dataset.count, 10) || 0;
    const duration = 1400;
    const start = performance.now();
    function tick(now) {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased).toLocaleString();
      if (p < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  // ----- button ripple -----
  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".btn");
    if (!btn) return;
    const r = btn.getBoundingClientRect();
    const size = Math.max(r.width, r.height);
    const span = document.createElement("span");
    span.className = "ripple";
    span.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX - r.left - size / 2}px;top:${e.clientY - r.top - size / 2}px`;
    btn.appendChild(span);
    setTimeout(() => span.remove(), 600);
  });

  // ----- card tilt -----
  document.querySelectorAll("[data-tilt]").forEach((card) => {
    card.addEventListener("mousemove", (e) => {
      const r = card.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      card.style.transform = `perspective(900px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg) translateY(-6px)`;
    });
    card.addEventListener("mouseleave", () => (card.style.transform = ""));
  });

  // ----- toasts auto dismiss -----
  document.querySelectorAll(".toast").forEach((toast, i) => {
    toast.style.animationDelay = i * 0.12 + "s";
    const close = () => { toast.classList.add("hide"); setTimeout(() => toast.remove(), 350); };
    toast.querySelector(".close").addEventListener("click", close);
    setTimeout(close, 5000 + i * 120);
  });

  // ----- confirm modal for destructive forms -----
  const modal = document.getElementById("confirmModal");
  let pendingForm = null;
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (form.dataset.confirmed) return;
      e.preventDefault();
      pendingForm = form;
      modal.classList.add("open");
    });
  });
  if (modal) {
    modal.querySelector("[data-cancel]").addEventListener("click", () => modal.classList.remove("open"));
    modal.addEventListener("click", (e) => { if (e.target === modal) modal.classList.remove("open"); });
    modal.querySelector("[data-ok]").addEventListener("click", () => {
      if (!pendingForm) return;
      pendingForm.dataset.confirmed = "1";
      pendingForm.submit();
    });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") modal.classList.remove("open"); });
  }

  // ----- dropzone file name preview -----
  document.querySelectorAll(".dropzone").forEach((zone) => {
    const input = zone.querySelector("input[type=file]");
    const label = zone.querySelector(".fname");
    input.addEventListener("change", () => (label.textContent = input.files[0] ? input.files[0].name : ""));
    ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, () => zone.classList.add("drag")));
    ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, () => zone.classList.remove("drag")));
  });

  // ----- auto-submit filters on change -----
  document.querySelectorAll("form[data-autosubmit] select").forEach((s) => s.addEventListener("change", () => s.form.submit()));

  // ----- demo account autofill on login page -----
  document.querySelectorAll("[data-demo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const [email, pass] = btn.dataset.demo.split("|");
      document.getElementById("email").value = email;
      document.getElementById("password").value = pass;
    });
  });

  // ----- copy token -----
  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const text = document.querySelector(btn.dataset.copy).textContent.trim();
      navigator.clipboard && navigator.clipboard.writeText(text).then(() => {
        const old = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check2"></i>';
        setTimeout(() => (btn.innerHTML = old), 1500);
      });
    });
  });
})();
