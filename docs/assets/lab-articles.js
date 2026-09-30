/* Copy exact lab inputs without changing the canonical reading runtime. */
(() => {
  "use strict";
  document.querySelectorAll(".code").forEach(block => {
    const code = block.querySelector("pre > code");
    if (!code) return;
    const label = block.querySelector(".code-label")?.textContent.trim() || "code";
    const button = block.querySelector("[data-lab-copy]");
    const download = block.querySelector("[data-lab-download]");
    const status = block.querySelector(".lab-copy-status");
    if (!button || !status) return;
    download?.addEventListener("click", () => {
      let url;
      let anchor;
      try {
        const filename = download.dataset.labDownload;
        if (!filename || !/^[a-zA-Z0-9._-]+\.jsonl$/.test(filename)) {
          throw new Error("Invalid download filename");
        }
        const text = code.textContent.trimEnd() + "\n";
        text.trimEnd().split("\n").forEach(line => JSON.parse(line));
        url = URL.createObjectURL(new Blob([text], {type: "application/x-ndjson;charset=utf-8"}));
        anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        document.body.append(anchor);
        anchor.click();
        status.textContent = "Download requested: " + filename + ".";
        status.dataset.kind = "success";
      } catch (error) {
        status.textContent = "Download unavailable: " + error.message + ". Use Copy and save the text as a UTF-8 JSONL file.";
        status.dataset.kind = "error";
      } finally {
        anchor?.remove();
        if (url) setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    });
    button.addEventListener("click", async () => {
      try {
        if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(code.textContent);
        status.textContent = label + " copied.";
        status.dataset.kind = "success";
      } catch {
        const range = document.createRange();
        range.selectNodeContents(code);
        const selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
        status.textContent = "Copy unavailable. Text selected: press Ctrl+C (Command+C on Mac), or select and copy it manually.";
        status.dataset.kind = "error";
      }
    });
  });
})();
