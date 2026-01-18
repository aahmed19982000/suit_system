// ✅ دالة تعليم الإشعار كمقروء
function markAsRead(id) {
    fetch(`/notifications/${id}/read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const element = document.getElementById(`note-${id}`);
            if (element) {
                element.classList.remove("unread");
                const readBtn = element.querySelector('button[onclick^="markAsRead"]');
                if (readBtn) readBtn.remove();
            }
        } else {
            console.error("فشل تعليم الإشعار كمقروء:", data.error);
        }
    })
    .catch(err => console.error("خطأ في markAsRead:", err));
}

// ✅ دالة حذف الإشعار
function deleteNotification(id) {
    fetch(`/notifications/${id}/delete/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const element = document.getElementById(`note-${id}`);
            if (element) element.remove();
        } else {
            console.error("فشل حذف الإشعار:", data.error);
        }
    })
    .catch(err => console.error("خطأ في deleteNotification:", err));
}

// ✅ دالة للحصول على CSRF Token
function getCookie(name) {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            return decodeURIComponent(cookie.slice(name.length + 1));
        }
    }
    return null;
}

// ✅ دالة فتح/إغلاق قائمة الإشعارات
function toggleNotifications() {
    const dropdown = document.getElementById("notificationDropdown");
    if (dropdown) dropdown.classList.toggle("show");
}

// ✅ إغلاق القائمة لما المستخدم يضغط براها
document.addEventListener("click", function (event) {
    const dropdown = document.getElementById("notificationDropdown");
    const icon = document.querySelector(".notification-icon");
    if (!dropdown || !icon) return;

    if (!dropdown.contains(event.target) && !icon.contains(event.target)) {
        dropdown.classList.remove("show");
    }
});
