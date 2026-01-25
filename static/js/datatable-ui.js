$("#trail-table tbody").on("click", "tr", function (e) {
  if ($(e.target).closest("a").length) return;

  if (window.innerWidth >= 1024) {
    var detailUrl = $(this).find("td[data-detail-url]").data("detail-url");
    if (detailUrl) {
      window.location.href = detailUrl;
    }
  }
});

if (window.innerWidth >= 1024) {
  $("#trail-table tbody tr").css("cursor", "pointer");
}
