function toggleNotifications() {
  const dropdown = document.getElementById("notificationDropdown");
  dropdown.classList.toggle("show");
}

document.addEventListener("click", function (event) {
  const dropdown = document.getElementById("notificationDropdown");
  const icon = document.querySelector(".notification-icon");

  if (!dropdown.contains(event.target) && !icon.contains(event.target)) {
    dropdown.classList.remove("show");
  }
});
