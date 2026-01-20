const hamburger = document.getElementById("hamburger");
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("overlay");

function toggleSidebar() {
  sidebar.classList.toggle("open");
  overlay.classList.toggle("show");
  document.body.style.overflow = sidebar.classList.contains("open")
    ? "hidden"
    : "";
}

hamburger.addEventListener("click", toggleSidebar);
overlay.addEventListener("click", toggleSidebar);

sidebar.addEventListener("click", function (e) {
  if (e.target.matches("a")) {
    setTimeout(() => {
      sidebar.classList.remove("open");
      overlay.classList.remove("show");
      document.body.style.overflow = "";
    }, 100);
  }
});
