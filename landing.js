const discoveryBrief = `SignalFlow workflow discovery brief

Trigger: What starts the workflow?
Inputs: Which tools and data are involved?
Decision: What rules determine the next step?
Failure: Where does the current process break?
Outcome: What observable change would make it useful?`;

const copyButton = document.querySelector("#copyBrief");
const copyStatus = document.querySelector("#copyStatus");

copyButton?.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(discoveryBrief);
    copyStatus.textContent = "Discovery brief copied. Add your workflow details and share it in your preferred channel.";
    copyButton.firstChild.textContent = "Brief copied ";
  } catch {
    copyStatus.textContent = discoveryBrief;
  }
});

document.querySelectorAll(".faq-list details").forEach((item) => {
  item.addEventListener("toggle", () => {
    const marker = item.querySelector("summary span");
    if (marker) marker.textContent = item.open ? "−" : "＋";
  });
});

const revealTargets = document.querySelectorAll(
  ".promise-band, .section-heading, .problem-grid, .service-list, .workflow-rail, .comparison, .case-study, .value-grid, .proof-layout, .integration-groups, .process-grid, .faq-list, .final-cta"
);

if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  revealTargets.forEach((target) => target.classList.add("reveal-pending"));
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("reveal-visible");
        revealObserver.unobserve(entry.target);
      });
    },
    { threshold: 0.08, rootMargin: "0px 0px -6%" }
  );
  revealTargets.forEach((target) => revealObserver.observe(target));
}
