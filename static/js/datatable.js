console.log("jQuery版:", $.fn.jquery);
console.log("DataTables有無:", !!$.fn.DataTable);
console.log("Responsive有無:", !!$.fn.DataTable.Responsive);

const isMobile = window.innerWidth <= 768;
const pageLength = isMobile ? 20 : 15;

var table = $("#trail-table").DataTable({
  dom: '<"datatable-header"<"dt-row1"f><"dt-row2"<"resolved-filter">l>>rtip',
  order: [[6, "desc"]],
  language: {
    url: "https://cdn.datatables.net/plug-ins/1.13.6/i18n/ja.json",
  },
  pageLength: pageLength,
  lengthMenu: [
    [10, 15, 20, 50],
    [10, 15, 20, 50],
  ],
  autoWidth: false,
  scrollX: false,
  responsive: {
    // サイドバー（約250px）を考慮したブレークポイント
    breakpoints: [
      { name: "desktop", width: Infinity },
      { name: "tablet-l", width: 1280 }, // デフォルト1024 + サイドバー256
      { name: "tablet-p", width: 1024 }, // デフォルト768 + サイドバー256
      { name: "mobile-l", width: 480 },
      { name: "mobile-p", width: 320 },
    ],
    details: {
      type: "column",
      target: "tr",
      renderer: function (api, rowIdx, columns) {
        // 1024px以上では展開しない（詳細ページへリンク）
        if (window.innerWidth >= 1024) return false;

        var row = api.row(rowIdx).node();
        var detailUrl = $(row).find("td[data-detail-url]").data("detail-url");

        var data = "";
        var sourceColumn = "";

        $.each(columns, function (i, col) {
          if (col.hidden) {
            var li =
              '<li data-dtr-index="' +
              col.columnIndex +
              '" style="padding:2px 0;">' +
              '<span class="dtr-title">' +
              col.title +
              "</span> " +
              '<span class="dtr-data">' +
              col.data +
              "</span>" +
              "</li>";

            if (col.columnIndex === 8) {
              sourceColumn = li;
            } else {
              data += li;
            }
          }
        });

        data += sourceColumn;
        if (!data) return false;

        var wrapper = $('<div style="position:relative;"></div>');
        if (detailUrl) {
          wrapper.append(
            '<a href="' +
              detailUrl +
              '" style="position: absolute; top: 1px; right: 0; color: #2563eb; font-weight: 500; font-size: 13px;">もっと見る →</a>',
          );
        }

        wrapper.append($('<ul style="margin:0;padding:0;"></ul>').append(data));

        return wrapper;
      },
    },
  },
  columnDefs: [
    { responsivePriority: 1, targets: [0, 2, 3] },
    { responsivePriority: 2, targets: [1] },
    { responsivePriority: 10000, targets: [4, 5, 6, 8] },
    { responsivePriority: 10001, targets: [7] },
    { width: "55px", targets: 0, className: "text-center" },
    { width: "60px", targets: 1, className: "text-center" },
    { width: "65px", targets: 3, className: "text-center" },
  ],
  // ↓↓↓ ここを追加 ↓↓↓
  initComplete: function () {
    // チェックボックス
    $(".resolved-filter").html(
        '<label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer whitespace-nowrap" >' +
        '<input type="checkbox" id="recent-only" class="w-4 h-4 rounded">' +
        "<span>最近の取得のみ</span>" +
        "</label>"+
      '<label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer whitespace-nowrap" style="margin-left: 4px;">' +
        '<input type="checkbox" id="hide-resolved" class="w-4 h-4 rounded" checked>' +
        "<span>解消済除く</span>" +
        "</label>",
    );
    // ソートドロップダウン
    $(".dt-row2").append(
      '<div class="sort-dropdown">' +
        '<select id="sort-select" class="text-sm border border-gray-300 rounded px-2 py-1">' +
        '<option value="6-desc">報告日↓新</option>' +
        '<option value="6-asc">報告日↑古</option>' +
        '<option value="7-desc">解消日↓新</option>' +
        '<option value="7-asc">解消日↑古</option>' +
        '<option value="2-asc">山名↑</option>' +
        '<option value="2-desc">山名↓</option>' +
        '<option value="8-asc">情報源↑</option>' +
        '<option value="8-desc">情報源↓</option>' +
        "</select>" +
        "</div>",
    );
  },
});
