var excludeResolved = true; // デフォルトON: 解消済を除く
var includeNewSources = true; // デフォルトON: 新規情報源を含む

$.fn.dataTable.ext.search.push(function (settings, data) {
  if (!excludeResolved) return true; // チェックOFF: 全て表示

  var resolvedAt = data[7] || "";
  if (!/\d/.test(resolvedAt)) return true;

  var m = resolvedAt.match(/(\d{2})\/(\d{2})\/(\d{2})/);
  if (!m) return true;

  var resolved = new Date(2000 + +m[1], +m[2] - 1, +m[3]);
  var today = new Date();
  today.setHours(0, 0, 0, 0);

  return resolved > today; // 未来の解消日 = 未解消として表示
});

// 新規情報源フィルタ
$.fn.dataTable.ext.search.push(function (settings, data, dataIndex) {
  if (includeNewSources) return true; // チェックON: 全て表示

  // チェックOFF: 7日以内に作成された情報源のレコードを非表示
  var row = table.row(dataIndex).node();
  var sourceCreated = parseFloat($(row).data('source-created'));
  var sevenDaysAgo = (Date.now() / 1000) - (7 * 24 * 3600);

  if (sourceCreated > sevenDaysAgo) {
    return false; // 非表示
  }
  return true;
});

$(document).on("change", "#exclude-resolved", function () {
  excludeResolved = this.checked;
  table.draw();
});

$(document).on("change", "#include-new-sources", function () {
  includeNewSources = this.checked;
  table.draw();
});

$(document).on("change", "#sort-select", function () {
  var val = $(this).val();
  if (!val) return;

  var [col, dir] = val.split("-");
  // 第1キーでソート、同じ値なら報告日降順（新しい順）
  table.order([[parseInt(col), dir], [6, "desc"]]).draw();
});
