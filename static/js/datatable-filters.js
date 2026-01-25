var includeResolved = false;
var recentOnly = false;

$.fn.dataTable.ext.search.push(function (settings, data) {
  if (includeResolved) return true;

  var resolvedAt = data[7] || "";
  if (!/\d/.test(resolvedAt)) return true;

  var m = resolvedAt.match(/(\d{2})\/(\d{2})\/(\d{2})/);
  if (!m) return true;

  var resolved = new Date(2000 + +m[1], +m[2] - 1, +m[3]);
  var today = new Date();
  today.setHours(0, 0, 0, 0);

  return resolved > today;
});

$.fn.dataTable.ext.search.push(function (settings, data) {
  if (!recentOnly) return true;

  var updatedAt = data[1] || "";
  if (!/\d/.test(updatedAt)) return false;

  var m = updatedAt.match(/(\d{2,4})\/(\d{1,2})\/(\d{1,2})/);
  if (!m) return false;

  var year = m[1].length === 2 ? 2000 + +m[1] : +m[1];
  var updated = new Date(year, +m[2] - 1, +m[3]);
  var sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  sevenDaysAgo.setHours(0, 0, 0, 0);

  return updated >= sevenDaysAgo;
});

$(document).on("change", "#include-resolved", function () {
  includeResolved = this.checked;
  table.draw();
});

$(document).on("change", "#recent-only", function () {
  recentOnly = this.checked;
  table.draw();
});

$(document).on("change", "#sort-select", function () {
  var val = $(this).val();
  if (!val) return;

  var [col, dir] = val.split("-");
  // 第1キーでソート、同じ値なら報告日降順（新しい順）
  table.order([[parseInt(col), dir], [6, "desc"]]).draw();
});
