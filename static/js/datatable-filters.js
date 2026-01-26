var hideResolved = true;

$.fn.dataTable.ext.search.push(function (settings, data) {
  if (!hideResolved) return true;

  var resolvedAt = data[7] || "";
  if (!/\d/.test(resolvedAt)) return true;

  var m = resolvedAt.match(/(\d{2})\/(\d{2})\/(\d{2})/);
  if (!m) return true;

  var resolved = new Date(2000 + +m[1], +m[2] - 1, +m[3]);
  var today = new Date();
  today.setHours(0, 0, 0, 0);

  return resolved > today;
});

$(document).on("change", "#hide-resolved", function () {
  hideResolved = this.checked;
  table.draw();
});

$(document).on("change", "#sort-select", function () {
  var val = $(this).val();
  if (!val) return;

  var [col, dir] = val.split("-");
  // 第1キーでソート、同じ値なら報告日降順（新しい順）
  table.order([[parseInt(col), dir], [6, "desc"]]).draw();
});
