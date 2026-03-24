// ─── sanitise inputs (partial ok for preview) ────────────────────────────
// resolves locked categories based on currentmode before validating.
function sanitiseinputs(mode = "full") {
  // resolve effective category values (locked ones override the hidden select)
  const srccat =
    currentmode === "single-buy" ? "assets" : srccategoryselect.value.trim();
  const dstcat =
    currentmode === "single-sell" ? "assets" : dstcategoryselect.value.trim();

  const srcsub = srcsubcategoryselect.value.trim();
  const dstsub = dstsubcategoryselect.value.trim();
  const rawamount = amountinput.value.trim();

  if (mode === "full") {
    if (!srccat || !categories[srccat])
      return {
        ok: false,
        error: "please select a valid source category.",
      };
    if (!srcsub || !categories[srccat].includes(srcsub))
      return {
        ok: false,
        error: "please select a valid source subcategory.",
      };
    if (!dstcat || !categories[dstcat])
      return {
        ok: false,
        error: "please select a valid destination category.",
      };
    if (!dstsub || !categories[dstcat].includes(dstsub))
      return {
        ok: false,
        error: "please select a valid destination subcategory.",
      };
    if (srccat === dstcat && srcsub === dstsub)
      return {
        ok: false,
        error: "source and destination cannot be the same.",
      };
    const amount = parseFloat(rawamount);
    if (isNaN(amount) || amount <= 0 || !isFinite(amount))
      return { ok: false, error: "amount must be a positive number." };
    return {
      ok: true,
      srccat,
      srcsub,
      dstcat,
      dstsub,
      amount: Math.round(amount * 100) / 100,
    };
  }

  // partial mode – return whatever is filled
  const amount = parseFloat(rawamount);
  return {
    ok: true,
    srccat: srccat && categories[srccat] ? srccat : null,
    srcsub:
      srccat &&
      srcsub &&
      categories[srccat] &&
      categories[srccat].includes(srcsub)
        ? srcsub
        : null,
    dstcat: dstcat && categories[dstcat] ? dstcat : null,
    dstsub:
      dstcat &&
      dstsub &&
      categories[dstcat] &&
      categories[dstcat].includes(dstsub)
        ? dstsub
        : null,
    amount:
      !isNaN(amount) && amount > 0 && isFinite(amount)
        ? Math.round(amount * 100) / 100
        : null,
  };
}
