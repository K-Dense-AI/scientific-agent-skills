// List every option in the currently OPEN Fictiv dropdown (material, process,
// finish color, thread size, ...).
//
// Fictiv uses Ant Design selects with a *virtualized* list: only ~8 options exist
// in the DOM at a time, so reading the page text or a screenshot misses most of
// them. Open the dropdown first (click the field), then run this in the browser's
// javascript tool. It scrolls the list top-to-bottom and returns every option,
// with category headers (e.g. "Aluminum", "Stereolithography (SLA)") marked "##".
//
// It only scrolls the list; it does not select anything.
// Keep the leading `await`: the javascript tool returns the last expression's
// value and does not unwrap a bare Promise (you'd get `{}`).

await (async () => {
  const holders = [...document.querySelectorAll(
    '.ant-select-dropdown:not(.ant-select-dropdown-hidden) .rc-virtual-list-holder')];
  const dropdowns = [...document.querySelectorAll('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')];
  if (!holders.length && !dropdowns.length) return 'No open dropdown. Click the select field first, then rerun.';

  const seen = new Map();
  const grab = (root) => root.querySelectorAll('.ant-select-item').forEach((it) => {
    const label = it.innerText.trim();
    if (!label || seen.has(label)) return;
    const isGroup = it.classList.contains('ant-select-item-group');
    seen.set(label, {
      label,
      group: isGroup,
      disabled: it.classList.contains('ant-select-item-option-disabled'),
      selected: it.classList.contains('ant-select-item-option-selected'),
    });
  });

  const hold = holders[holders.length - 1];
  if (hold) {
    for (let y = 0; y <= hold.scrollHeight + 200; y += 80) {
      hold.scrollTop = y;
      await new Promise((r) => setTimeout(r, 100));
      grab(hold);
    }
    hold.scrollTop = 0;
  } else {
    grab(dropdowns[dropdowns.length - 1]);
  }

  return [...seen.values()]
    .map((o) => (o.group ? `## ${o.label}` : `${o.label}${o.selected ? '  [selected]' : ''}${o.disabled ? '  [disabled]' : ''}`))
    .join('\n');
})();
