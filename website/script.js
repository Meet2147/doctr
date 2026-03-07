document.querySelectorAll("pre").forEach((block) => {
  const btn = document.createElement("button");
  btn.textContent = "Copy";
  btn.style.cssText =
    "float:right;margin:-6px -4px 8px 0;border:1px solid #d6cfc7;background:#fffaf2;border-radius:8px;padding:4px 8px;font:500 12px 'IBM Plex Mono', monospace;cursor:pointer;";
  btn.addEventListener("click", async () => {
    await navigator.clipboard.writeText(block.innerText);
    btn.textContent = "Copied";
    setTimeout(() => {
      btn.textContent = "Copy";
    }, 1000);
  });
  block.parentElement?.insertBefore(btn, block);
});

