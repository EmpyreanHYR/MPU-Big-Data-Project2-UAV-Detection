"use strict";

const stage = document.querySelector("#stage");
const fullScreen = document.querySelector("#fullscreen");
const video = document.querySelector("#video");
const pages = [...document.querySelectorAll(".slide")];
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
let current = 0;

const repository = "https://github.com/EmpyreanHYR/MPU-Big-Data-Project2-UAV-Detection";
const evidence = {
  s2: ["Data preparation record", "/blob/main/docs/datasets/PREPARATION.md"],
  s3: ["Full model diagram", "/blob/main/docs/report/figures/final_pconv_p2.pdf"],
  s4: ["Full comparison tables", "/blob/main/docs/results/EXPERIMENT_TABLES_20261105.md"],
  s5: ["Four ablation runs", "/blob/main/docs/results/SCRATCH_ABLATIONS_20261104.md"],
  s6: ["Training scale results", "/blob/main/docs/results/TRAINING_FRACTIONS_20261107.md"],
  s7: ["H10 deployment guide", "/blob/main/scripts/deployment/README.md"],
  s8: ["Full NMS threshold chart", "/blob/main/docs/report/figures/nms_selection.png"],
  s9: ["VLM experiment record", "/blob/main/experiments/pinp2_vlm/README.md"],
  s10: ["Final report PDF", "/blob/main/docs/report/report.pdf"],
};

function githubLink(label, path) {
  const link = document.createElement("a");
  link.className = "evidence-link";
  link.href = repository + path;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = label + " ↗";
  link.setAttribute("aria-label", label + " on GitHub (opens in a new tab, requires internet)");
  return link;
}

for (const page of pages) {
  const entry = evidence[page.getAttribute("aria-labelledby")];
  if (!entry) continue;
  const row = document.createElement("div");
  row.className = "evidence-row";
  row.append(githubLink(...entry));
  page.append(row);
}
const releaseLink = document.querySelector("#github-release");
if (releaseLink) releaseLink.append(githubLink("Public model and video release", "/releases/tag/gui-h10-v1.0.0"));

for (const controls of document.querySelectorAll(".view-controls")) {
  const buttons = [...controls.querySelectorAll("button[data-view]")];
  for (const button of buttons) button.addEventListener("click", () => {
    for (const item of buttons) {
      item.setAttribute("aria-pressed", String(item === button));
      document.getElementById(item.dataset.view).hidden = item !== button;
    }
  });
}

function fit() {
  const scale = Math.min(window.innerWidth / 1366, window.innerHeight / 768);
  stage.style.setProperty("--scale", String(scale));
}

function go(index, focus = false) {
  current = Math.min(Math.max(index, 0), pages.length - 1);
  if (video && !pages[current].contains(video)) {
    video.pause();
    video.controls = false;
  }
  pages.forEach((page, i) => { page.hidden = i !== current; });
  stage.classList.toggle("is-bookend", pages[current].classList.contains("bookend"));
  previous.disabled = current === 0;
  next.disabled = current === pages.length - 1;
  document.querySelector("#counter").textContent =
    String(current + 1).padStart(2, "0") + " / " + pages.length;
  const progress = document.querySelector("#progress");
  progress.max = pages.length;
  progress.value = current + 1;
  if (focus) pages[current].querySelector("h1").focus({ preventScroll: true });
}

async function toggleFullScreen() {
  if (document.fullscreenElement) await document.exitFullscreen();
  else await document.documentElement.requestFullscreen();
}

fit();
window.addEventListener("resize", fit);
fullScreen.addEventListener("click", () => toggleFullScreen().catch(() => {}));
document.querySelector("#export-pdf").addEventListener("click", async () => {
  if (document.fullscreenElement) await document.exitFullscreen().catch(() => {});
  window.print();
});
document.addEventListener("fullscreenchange", () => {
  fullScreen.textContent = document.fullscreenElement ? "Exit full screen" : "Full screen";
  fit();
});

if (pages.length) {
  const readAddress = () => {
    const target = {"#conclusion": "s10", "#demo": "demo-title"}[location.hash];
    if (target) {
      go(pages.findIndex(page => page.getAttribute("aria-labelledby") === target));
      return;
    }
    const value = /^#(\d+)$/.exec(location.hash);
    go(value ? Number(value[1]) - 1 : 0);
  };
  readAddress();
  previous.addEventListener("click", () => go(current - 1, true));
  next.addEventListener("click", () => go(current + 1, true));
  window.addEventListener("hashchange", readAddress);
}

document.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
  if (video && (document.fullscreenElement === video || event.target === video)) return;
  if (event.key.toLowerCase() === "f" && event.target !== video) {
    event.preventDefault();
    toggleFullScreen().catch(() => {});
    return;
  }
  if (!pages.length || event.target.closest("input,textarea,select,[contenteditable]")) return;
  if (event.key === " " && event.target.closest("button,a")) return;
  const direction = { ArrowRight: 1, PageDown: 1, " ": 1, ArrowLeft: -1, PageUp: -1 }[event.key];
  if (!direction) return;
  event.preventDefault();
  go(current + direction, true);
});

if (video) {
  const status = document.querySelector("#demo-status");
  const playButton = document.querySelector("#full");
  function reportVideoStatus(message) {
    status.textContent = message;
    status.hidden = !message;
  }
  function leaveVideoFullscreen() {
    if (document.fullscreenElement === video) document.exitFullscreen().catch(() => {});
  }
  playButton.addEventListener("click", () => {
    reportVideoStatus("");
    video.currentTime = 0;
    video.controls = true;
    // Start both operations during the click so the browser grants fullscreen.
    const playback = video.play();
    video.requestFullscreen().catch(() => {
      if (!video.paused) reportVideoStatus("Fullscreen is unavailable. Playing on this slide.");
    });
    playback.catch(() => {
      video.controls = false;
      leaveVideoFullscreen();
      reportVideoStatus("Video playback could not start. Try Chrome or Edge with the local presentation folder.");
    });
  });
  video.addEventListener("ended", () => {
    video.controls = false;
    video.currentTime = 0;
    leaveVideoFullscreen();
    playButton.focus({preventScroll:true});
  });
  video.addEventListener("error", () => {
    reportVideoStatus("The video is unavailable. Check that assets/project-demo.mp4 is in the presentation folder.");
  });
}

function node(svg, tag, attributes, text) {
  const item = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [name, value] of Object.entries(attributes)) item.setAttribute(name, String(value));
  if (text !== undefined) item.textContent = text;
  svg.append(item);
}

function chart(id, labels, values, xValues) {
  const svg = document.getElementById(id);
  if (!svg) return;
  const bottom = 315;
  const y = (value) => bottom - value * 6.5;
  const x = (i) => xValues ? 74 + xValues[i] * 0.275 : 132 + i * 150;
  node(svg, "text", { x: 66, y: 23 }, "Native AP50:95 (%)");
  for (const tick of [0, 10, 20, 30, 40]) {
    node(svg, "line", { x1: 64, x2: 675, y1: y(tick), y2: y(tick), class: "grid" });
    node(svg, "text", { x: 50, y: y(tick) + 6, "text-anchor": "end" }, tick);
  }
  if (xValues) node(svg, "polyline", {
    points: values.map((value, i) => x(i) + "," + y(value)).join(" "), class: "trace",
  });
  values.forEach((value, i) => {
    const fill = i === values.length - 1 ? "var(--accent)" : "var(--blue)";
    if (xValues) node(svg, "circle", { cx: x(i), cy: y(value), r: 7, fill });
    else node(svg, "rect", { x: x(i) - 42, y: y(value), width: 84, height: bottom - y(value), rx: 2, fill });
    node(svg, "text", { x: x(i), y: y(value) - 13, class: "value", "text-anchor": "middle" }, value.toFixed(3) + "%");
    node(svg, "text", { x: x(i), y: 347, "text-anchor": "middle" }, labels[i]);
  });
  if (xValues) node(svg, "text", { x: 370, y: 380, "text-anchor": "middle" }, "Training images");
}

chart("ablation", ["YOLO26n", "+ PConv", "+ P2", "PinP2"], [27.952, 24.381, 29.975, 31.274]);
chart("scale", ["500", "1,000", "1,999"], [16.353, 24.543, 31.274], [500, 1000, 1999]);

const finePointer = window.matchMedia("(any-hover: hover) and (any-pointer: fine)");
const drone = document.createElement("img");
drone.className = "drone-cursor";
drone.src = "assets/drone-cursor.svg";
drone.alt = "";
drone.draggable = false;
drone.hidden = true;
document.body.append(drone);
let droneEnabled = true;
let pointerPosition = null;

function hideDrone() {
  drone.hidden = true;
  document.documentElement.classList.remove("drone-active");
}

function showDrone() {
  if (!droneEnabled || !finePointer.matches || !pointerPosition ||
      !drone.complete || !drone.naturalWidth) {
    hideDrone();
    return;
  }
  const {x, y} = pointerPosition;
  // Leave the browser's own pointer in charge of native video controls.
  if (document.elementFromPoint(x, y)?.closest("video")) {
    hideDrone();
    return;
  }
  drone.style.transform = "translate3d(" + x + "px," + y + "px,0) translate(-50%,-50%)";
  drone.hidden = false;
  document.documentElement.classList.add("drone-active");
}

window.addEventListener("pointermove", event => {
  pointerPosition = event.pointerType === "mouse" ? {x: event.clientX, y: event.clientY} : null;
  showDrone();
}, {passive: true});
function clearDrone() {
  pointerPosition = null;
  hideDrone();
}
document.documentElement.addEventListener("pointerleave", clearDrone);
window.addEventListener("blur", clearDrone);
document.addEventListener("fullscreenchange", clearDrone);
finePointer.addEventListener("change", clearDrone);
document.addEventListener("keydown", event => {
  if (event.key.toLowerCase() !== "m" || event.repeat || event.altKey ||
      event.ctrlKey || event.metaKey) return;
  droneEnabled = !droneEnabled;
  showDrone();
});
