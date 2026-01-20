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
    details: {
      type: "column",
      target: "tr",
      renderer: function (api, rowIdx, columns) {
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
              '" style="position:absolute;top:2px;right:0;">もっと見る →</a>',
          );
        }

        wrapper.append(
          $('<ul style="margin:0;padding:0 70px 0 0;"></ul>').append(data),
        );

        return wrapper;
      },
    },
  },
});
