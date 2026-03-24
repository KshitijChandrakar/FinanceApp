// ─── Sanitize inputs (full or partial) ─────────────────────────────────────
function sanitizeInputs(mode = "full") {
  // resolve effective category values (locked override select)
  let srcCatRaw =
    currentmode === "single-buy" ? "assets" : srccategoryselect.value;
  let dstCatRaw =
    currentmode === "single-sell" ? "assets" : dstcategoryselect.value;
  const srcSubRaw = srcsubcategoryselect.value;
  const dstSubRaw = dstsubcategoryselect.value;
  const amountRaw = amountinput.value;

  const srcCat = srcCatRaw?.trim() || "";
  const dstCat = dstCatRaw?.trim() || "";

  if (mode === "full") {
    if (!srcCat || !categories[srcCat])
      return {
        ok: false,
        error: "Please select a valid source category.",
      };
    if (!srcSubRaw || !categories[srcCat]?.includes(srcSubRaw))
      return {
        ok: false,
        error: "Please select a valid source subcategory.",
      };
    if (!dstCat || !categories[dstCat])
      return {
        ok: false,
        error: "Please select a valid destination category.",
      };
    if (!dstSubRaw || !categories[dstCat]?.includes(dstSubRaw))
      return {
        ok: false,
        error: "Please select a valid destination subcategory.",
      };
    if (srcCat === dstCat && srcSubRaw === dstSubRaw)
      return {
        ok: false,
        error: "Source and destination cannot be the same.",
      };
    const amountNum = parseFloat(amountRaw);
    if (isNaN(amountNum) || amountNum <= 0 || !isFinite(amountNum))
      return { ok: false, error: "Amount must be a positive number." };
    const finalAmount = Math.round(amountNum * 100) / 100;
    return {
      ok: true,
      srcCat,
      srcSub: srcSubRaw,
      dstCat,
      dstSub: dstSubRaw,
      amount: finalAmount,
    };
  }
  // partial preview
  const amountNum = parseFloat(amountRaw);
  return {
    ok: true,
    srcCat: srcCat && categories[srcCat] ? srcCat : null,
    srcSub:
      srcCat && srcSubRaw && categories[srcCat]?.includes(srcSubRaw)
        ? srcSubRaw
        : null,
    dstCat: dstCat && categories[dstCat] ? dstCat : null,
    dstSub:
      dstCat && dstSubRaw && categories[dstCat]?.includes(dstSubRaw)
        ? dstSubRaw
        : null,
    amount:
      !isNaN(amountNum) && amountNum > 0 && isFinite(amountNum)
        ? Math.round(amountNum * 100) / 100
        : null,
  };
}
