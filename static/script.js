document.addEventListener("DOMContentLoaded", () => {
  const checkBtn = document.getElementById("check-btn");
  const resultBox = document.getElementById("result");

  checkBtn.addEventListener("click", async () => {
    const email = document.getElementById("email-input").value;
    if (!email) {
      showToast("❗ Vui lòng nhập email!", "error");
      return;
    }

    checkBtn.innerText = "⏳ Đang kiểm tra...";
    checkBtn.disabled = true;

    try {
      const response = await fetch(`/check_mail?email=${encodeURIComponent(email)}`);
      const data = await response.json();

      if (data.link) {
        document.getElementById("account-name").textContent = data.account_name;
        document.getElementById("verification-link").textContent = data.link;
        document.getElementById("received-time").textContent = data.received_time;
        document.getElementById("expiration-time").textContent = data.expiration_time;
        resultBox.style.display = "block";
        showToast("✅ Đã tìm thấy mã xác minh!", "success");
      } else {
        resultBox.style.display = "none";
        showToast(data.message, "warning");
      }
    } catch (err) {
      showToast("⚠️ Lỗi kết nối tới máy chủ!", "error");
    }

    checkBtn.innerText = "🚀 Lấy mã xác minh";
    checkBtn.disabled = false;
  });

  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerText = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
  }
});
