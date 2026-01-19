
  console.log("jQuery版:", $.fn.jquery);
  console.log("DataTables有無:", !!$.fn.DataTable);
  console.log("Responsive有無:", !!$.fn.DataTable.Responsive);

  // 画面サイズに応じた件数設定
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
          // 行から詳細URLを取得
          var row = api.row(rowIdx).node();
          var detailUrl = $(row).find("td[data-detail-url]").data("detail-url");

          var data = "";
          var sourceColumn = ""; // 情報源カラムを最後に

          $.each(columns, function (i, col) {
            if (col.hidden) {
              var item = "";
              var liStyle = "padding: 2px 0;";
              if (col.columnIndex === 8) {
                // 情報源
                sourceColumn =
                  '<li data-dtr-index="' +
                  col.columnIndex +
                  '" style="' +
                  liStyle +
                  '">' +
                  '<span class="dtr-title">' +
                  col.title +
                  "</span> " +
                  '<span class="dtr-data">' +
                  col.data +
                  "</span>" +
                  "</li>";
              } else {
                item =
                  '<li data-dtr-index="' +
                  col.columnIndex +
                  '" style="' +
                  liStyle +
                  '">' +
                  '<span class="dtr-title">' +
                  col.title +
                  "</span> " +
                  '<span class="dtr-data">' +
                  col.data +
                  "</span>" +
                  "</li>";
              }
              data += item;
            }
          });

          // 情報源を最後に追加
          data += sourceColumn;

          if (!data) return false;

          // 展開エリア全体をラップし、右上に「もっと見る」を配置
          var wrapper = $('<div style="position: relative;"></div>');
          if (detailUrl) {
            wrapper.append(
              '<a href="' +
                detailUrl +
                '" style="position: absolute; top: 2px; right: 0; color: #2563eb; font-weight: 500; font-size: 13px;">もっと見る →</a>',
            );
          }
          wrapper.append(
            $(
              '<ul data-dtr-index="' +
                rowIdx +
                '" style="margin: 0; padding: 0 70px 0 0;" />',
            ).append(data),
          );
          return wrapper;
        },
      },
    },
    columnDefs: [
      {
        responsivePriority: 1,
        targets: [0, 2, 3],
      }, // 山域、対象、状況種別 (最重要3列)
      {
        responsivePriority: 2,
        targets: [1],
      }, // 取得日
      {
        responsivePriority: 10000,
        targets: [4, 5, 6, 8],
      }, // 状況、詳細、報告日、情報源は折りたたみ
      {
        responsivePriority: 10001,
        targets: [7],
      }, // 解消日は最初に折りたたみ
      {
        width: "55px",
        targets: 0,
        className: "text-center",
      }, // 山域
      {
        width: "60px",
        targets: 1,
        className: "text-center",
      }, // 取得日
      {
        width: "65px",
        targets: 3,
        className: "text-center",
      }, // 状況
    ],
    initComplete: function () {
      // チェックボックスをDOMに挿入
      $(".resolved-filter").html(
        '<label class="flex items-center gap-1.5 text-sm text-gray-600 cursor-pointer whitespace-nowrap">' +
          '<input type="checkbox" id="hide-resolved" class="w-4 h-4 rounded" checked>' +
          "<span>解消済除く</span>" +
          "</label>",
      );
      // ソートドロップダウンを追加（全画面サイズ共通）
      $(".dt-row2").append(
        '<div class="sort-dropdown">' +
          '<select id="sort-select" class="text-sm border border-gray-300 rounded px-2 py-1">' +
          '<option value="">並び替え</option>' +
          '<option value="6-desc">報告日↓新</option>' +
          '<option value="6-asc">報告日↑古</option>' +
          '<option value="7-desc">解消日↓新</option>' +
          '<option value="7-asc">解消日↑古</option>' +
          '<option value="8-asc">情報源↑</option>' +
          '<option value="8-desc">情報源↓</option>' +
          "</select>" +
          "</div>",
      );
    },
  });

  // 解消済みフィルター
  var hideResolved = true;
  $.fn.dataTable.ext.search.push(function (settings, data, dataIndex) {
    if (!hideResolved) return true;

    var resolvedAt = data[7] || "";

    // 数字がなければ表示（解消日なし）
    if (!/\d/.test(resolvedAt)) return true;

    // 日付パース
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

  // ソートドロップダウン
  $(document).on("change", "#sort-select", function () {
    var val = $(this).val();
    if (val) {
      var parts = val.split("-");
      var col = parseInt(parts[0]);
      var dir = parts[1];
      table.order([col, dir]).draw();
    }
  });

  // デスクトップで行クリック時に詳細ページへ遷移
  // DataTables折りたたみ閾値（1441px）より大きい場合のみ遷移
  $("#trail-table tbody").on("click", "tr", function (e) {
    // リンククリック時は通常の遷移を許可
    if ($(e.target).is("a") || $(e.target).closest("a").length) {
      return;
    }
    // 1442px以上のみ遷移（それ以下はDataTablesのプルダウンに任せる）
    if (window.innerWidth >= 1442) {
      var detailUrl = $(this).find("td[data-detail-url]").data("detail-url");
      if (detailUrl) {
        window.location.href = detailUrl;
      }
    }
  });

  // デスクトップで行にカーソルポインターを表示
  if (window.innerWidth >= 1442) {
    $("#trail-table tbody tr").css("cursor", "pointer");
  }

  // ハンバーガーメニュー
  const hamburger = document.getElementById("hamburger");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("overlay");

  function toggleSidebar() {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("show");
    // サイドバーを開いているときは本文のスクロールを無効化
    document.body.style.overflow = sidebar.classList.contains("open")
      ? "hidden"
      : "";

    // サイドバーを開いた時に強制リペイント
    if (sidebar.classList.contains("open")) {
      requestAnimationFrame(() => {
        const computed = window.getComputedStyle(
          sidebar,
          "::before",
        ).backdropFilter;
        sidebar.style.transform = "translateZ(0.001px)";
        requestAnimationFrame(() => {
          sidebar.style.transform = "";
        });
      });
    }
  }

  hamburger.addEventListener("click", toggleSidebar);
  overlay.addEventListener("click", toggleSidebar);

  // サイドバーのtransition終了時に強制リペイント
  sidebar.addEventListener("transitionend", function (e) {
    if (e.propertyName === "transform" && sidebar.classList.contains("open")) {
      // transition終了直後に強制再描画
      const computed = window.getComputedStyle(
        sidebar,
        "::before",
      ).backdropFilter;
      void sidebar.offsetHeight; // 強制リフロー
    }
  });

  // サイドバー内リンククリック時も閉じる
  sidebar.addEventListener("click", function (e) {
    if (e.target.matches("a")) {
      setTimeout(() => {
        sidebar.classList.remove("open");
        overlay.classList.remove("show");
        document.body.style.overflow = "";
      }, 100);
    }
  });

  // backdrop-filter初期化問題の修正：強制リペイント
  // DOMContentLoadedで早めに実行
  document.addEventListener("DOMContentLoaded", function () {
    // 複数の方法で強制再描画
    setTimeout(() => {
      // 方法1: opacity微調整
      sidebar.style.opacity = "0.9999";
      // 方法2: ::beforeの計算スタイル取得
      const computed = window.getComputedStyle(
        sidebar,
        "::before",
      ).backdropFilter;
      // 方法3: 強制リフロー
      const forceReflow = sidebar.offsetHeight;

      requestAnimationFrame(() => {
        sidebar.style.opacity = "";
      });
    }, 50);
  });

  // サイドバー::beforeの高さを動的に調整
  function updateSidebarBeforeHeight() {
    const scrollHeight = sidebar.scrollHeight;
    sidebar.style.setProperty("--sidebar-height", scrollHeight + "px");
  }

  // 初回実行
  updateSidebarBeforeHeight();

  // サイドバー開閉時とリサイズ時に更新
  hamburger.addEventListener("click", () => {
    setTimeout(updateSidebarBeforeHeight, 350);
  });

  window.addEventListener("resize", updateSidebarBeforeHeight);

