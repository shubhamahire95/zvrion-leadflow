"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const required = [
  "templates/index.html", "static/app.css", "static/polish.css", "static/responsive.css", "static/app.js",
  "static/logo.png", "static/favicon.svg", "data/locations.json", "data/history.json"
];

for (const relative of required) {
  const file = path.join(root, relative);
  if (!fs.existsSync(file) || !fs.statSync(file).size) throw new Error(`Missing or empty asset: ${relative}`);
}

const script = fs.readFileSync(path.join(root, "static/app.js"), "utf8");
new vm.Script(script, {filename: "static/app.js"});

const html = fs.readFileSync(path.join(root, "templates/index.html"), "utf8");
for (const id of ["dashboard", "new-scrape", "live-leads", "history", "downloads", "settings"]) {
  if (!html.includes(`id="${id}"`)) throw new Error(`Missing routed section: ${id}`);
}
if (!html.includes("logo.png") || !html.includes("favicon.svg")) throw new Error("Brand assets are not referenced");
if (html.includes("Â") || html.includes("â€")) throw new Error("Template contains broken UTF-8 text");

console.log("ZVRION LeadFlow production assets validated successfully.");
