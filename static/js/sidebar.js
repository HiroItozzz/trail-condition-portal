const hamburger = document.getElementById("hamburger");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");

function openSidebar() {
  sidebar.classList.add("open");
  overlay.classList.add("show");
  document.body.style.overflow = "hidden";
}

function closeSidebar() {
  sidebar.classList.remove("open");
  overlay.classList.remove("show");
  document.body.style.overflow = "";
}

function toggleSidebar() {
  if (sidebar.classList.contains("open")) {
    closeSidebar();
  } else {
    openSidebar();
  }
}

hamburger.addEventListener("click", toggleSidebar);
overlay.addEventListener("click", closeSidebar);

sidebar.addEventListener("click", function (e) {
  if (e.target.matches("a")) {
    setTimeout(closeSidebar, 100);
  }
});

// スワイプジェスチャー
(function () {
  const DEAD_ZONE = 40; // ブラウザ戻るジェスチャーと競合する範囲(px)を無視
  const EDGE_ZONE = 120; // サイドバー開始を検知する範囲の外端(px)
  const SIDEBAR_WIDTH = 250;
  const THRESHOLD = 0.3; // 開閉判定の閾値（幅の30%）

  let touchStartX = 0;
  let touchStartY = 0;
  let tracking = false; // スワイプ追跡中か
  let dragging = false; // ドラッグ中か(閾値を超えた)
  let isOpen = false; // 開始時のサイドバー状態

  function isMobile() {
    return window.innerWidth < 1024;
  }

  function setTransform(px) {
    sidebar.style.transition = "none";
    sidebar.style.transform = `translateX(${px}px)`;
    // オーバーレイの不透明度を連動
    const progress = (SIDEBAR_WIDTH + px) / SIDEBAR_WIDTH;
    overlay.style.display = "block";
    overlay.style.opacity = Math.max(0, Math.min(1, progress));
  }

  function resetStyles() {
    sidebar.style.transition = "";
    sidebar.style.transform = "";
    overlay.style.opacity = "";
    overlay.style.display = "";
  }

  document.addEventListener(
    "touchstart",
    function (e) {
      if (!isMobile()) return;
      const touch = e.touches[0];
      touchStartX = touch.clientX;
      touchStartY = touch.clientY;
      isOpen = sidebar.classList.contains("open");

      // 左端スワイプ(開く)またはサイドバー/オーバーレイ上(閉じる)
      // DEAD_ZONE以内はブラウザ戻るジェスチャーと競合するため無視
      if (!isOpen && touchStartX > DEAD_ZONE && touchStartX <= EDGE_ZONE) {
        tracking = true;
      } else if (isOpen) {
        tracking = true;
      }
    },
    { passive: true },
  );

  document.addEventListener(
    "touchmove",
    function (e) {
      if (!tracking) return;
      const touch = e.touches[0];
      const dx = touch.clientX - touchStartX;
      const dy = touch.clientY - touchStartY;

      // 縦スクロールの場合はキャンセル
      if (!dragging && Math.abs(dy) > Math.abs(dx)) {
        tracking = false;
        return;
      }

      if (!dragging) {
        if (Math.abs(dx) < 10) return; // 最小移動量
        dragging = true;
      }

      if (!isOpen) {
        // 閉じた状態 → 右スワイプで開く
        const offset = Math.min(Math.max(dx - SIDEBAR_WIDTH, -SIDEBAR_WIDTH), 0);
        setTransform(offset);
      } else {
        // 開いた状態 → 左スワイプで閉じる
        const offset = Math.min(Math.max(dx, -SIDEBAR_WIDTH), 0);
        setTransform(offset);
      }
    },
    { passive: true },
  );

  document.addEventListener(
    "touchend",
    function () {
      if (!tracking || !dragging) {
        tracking = false;
        dragging = false;
        return;
      }

      const currentTransform = new DOMMatrix(
        getComputedStyle(sidebar).transform,
      ).m41;
      const progress = (SIDEBAR_WIDTH + currentTransform) / SIDEBAR_WIDTH;

      resetStyles();

      if (progress > THRESHOLD) {
        openSidebar();
      } else {
        closeSidebar();
      }

      tracking = false;
      dragging = false;
    },
    { passive: true },
  );
})();
