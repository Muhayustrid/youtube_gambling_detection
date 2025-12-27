document.addEventListener('DOMContentLoaded', function () {

  // ========================================================
  // FUNGSI BANTUAN (Helpers)
  // ========================================================
  function showNotification(message, type = 'info', icon = null) {
    // Hapus notifikasi yang sudah ada
    const existing = document.querySelector('.custom-notification');
    if (existing) existing.remove();

    // Pemetaan ikon
    const iconMap = {
      'success': 'check-circle',
      'danger': 'exclamation-circle',
      'warning': 'exclamation-triangle',
      'info': 'info-circle'
    };

    const iconClass = icon || iconMap[type] || 'info-circle';

    // Buat elemen notifikasi
    const notification = document.createElement('div');
    notification.className = `custom-notification alert alert-${type} alert-dismissible fade show`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        max-width: 500px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    notification.innerHTML = `
        <i class="fas fa-${iconClass} me-2"></i>
        <strong>${message}</strong>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Hapus otomatis setelah 5 detik
    setTimeout(() => {
      notification.classList.remove('show');
      setTimeout(() => notification.remove(), 150);
    }, 5000);
  }

  function updateDeleteButton() {
    const checked = document.querySelectorAll('.row-check:checked').length;
    const btn = document.getElementById('deleteSelected');
    if (btn) {
      btn.disabled = checked === 0 || !window.oauthOk;
    }
    btn.innerHTML = checked > 0
      ? `<i class="fas fa-trash"></i> Hapus Terpilih (${checked})`
      : `<i class="fas fa-trash"></i> Hapus Terpilih`;
  }

  // ========================================================
  // 1. INISIALISASI & VALIDASI FORM ANALISIS
  // ========================================================
  const analyzeForm = document.getElementById('analyzeForm');
  const urlInput = document.getElementById('youtubeUrl');
  const urlErrorDiv = document.getElementById('urlError');
  const loadingOverlay = document.getElementById('loading');
  const loadingText = loadingOverlay ? loadingOverlay.querySelector('h3') : null; // Ambil elemen H3

  if (analyzeForm) {
    analyzeForm.addEventListener('submit', function (e) {
      e.preventDefault();

      const url = urlInput.value.trim();

      urlInput.classList.remove('is-invalid');
      urlErrorDiv.style.display = 'none';

      const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|shorts\/)|youtu\.be\/)/;

      if (!youtubeRegex.test(url)) {
        urlInput.classList.add('is-invalid');
        urlErrorDiv.style.display = 'block';
        urlInput.focus();
        return;
      }

      // --- TAMPILKAN OVERLAY  ---
      loadingOverlay.style.display = 'flex';
      if (loadingText) {
        loadingText.innerHTML = 'Sedang memulai analisis...';
      }

      // Mulai simulasi progress
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 95) progress = 95;

        if (loadingText) {
          // Ubah teks berdasarkan progress
          if (progress < 30) {
            loadingText.innerHTML = `Mengambil komentar... <strong>${Math.round(progress)}%</strong>`;
          } else if (progress < 70) {
            loadingText.innerHTML = `Menganalisis komentar... <strong>${Math.round(progress)}%</strong>`;
          } else {
            loadingText.innerHTML = `Sedang hampir selesai... <strong>${Math.round(progress)}%</strong>`;
          }
        }
      }, 800); // Update setiap 800ms

      // Submit form secara manual
      this.submit();
    });
  }

  // ========================================================
  // 2. LOGIKA STATISTIK (Hanya berjalan jika ada data komentar)
  // ========================================================
  // Statistik sekarang dihitung server-side, tidak perlu logika frontend

  // ========================================================
  // 3. INTERAKSI TABEL (Filter, Select All, dll)
  // ========================================================
  const filterPrediction = document.getElementById('filterPrediction');
  if (filterPrediction) {
    filterPrediction.addEventListener('change', function () {
      const filter = this.value;
      const rows = document.querySelectorAll('#commentsTable tbody tr');

      rows.forEach(row => {
        row.style.display = (filter === 'all' || filter === row.dataset.prediction) ? '' : 'none';
      });
      updateDeleteButton(); // Update status tombol hapus setelah filter
    });
  }

  const selectAllCheckbox = document.getElementById('selectAll');
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', function () {
      const checkboxes = document.querySelectorAll('.row-check');
      checkboxes.forEach(cb => {
        if (cb.closest('tr').style.display !== 'none') {
          cb.checked = this.checked;
        }
      });
      updateDeleteButton();
    });
  }

  // Tambahkan listener ke setiap checkbox baris
  document.querySelectorAll('.row-check').forEach(cb => {
    cb.addEventListener('change', updateDeleteButton);
  });

  // ========================================================
  // 4. AKSI AJAX (Hapus Komentar)
  // ========================================================
  const deleteSelectedBtn = document.getElementById('deleteSelected');
  if (deleteSelectedBtn) {
    deleteSelectedBtn.addEventListener('click', async function (e) {
      e.preventDefault();

      if (!window.oauthOk) {
        showNotification('Silakan login YouTube terlebih dahulu untuk melakukan moderasi.', 'warning');
        return;
      }

      const checkedBoxes = document.querySelectorAll('.row-check:checked');
      const checked = checkedBoxes.length;

      if (checked === 0) {
        showNotification('Pilih minimal 1 komentar untuk dihapus.', 'warning');
        return;
      }

      if (confirm(`Hapus ${checked} komentar yang dipilih?`)) {
        this.disabled = true;
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Menghapus...';

        const formData = new FormData();
        formData.append('action', 'reject');
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

        checkedBoxes.forEach(cb => formData.append('comment_id', cb.value));

        try {
          const response = await fetch('{% url "moderate_comments" %}', {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
          });

          const result = await response.json();

          if (result.ok) {
            checkedBoxes.forEach(cb => cb.closest('tr').remove());

            const remainingRows = document.querySelectorAll('#commentsTable tbody tr');
            if (remainingRows.length === 0) {
              document.getElementById('statsSummary').style.display = 'none';
              const tableContainer = document.querySelector('.table-container');
              tableContainer.innerHTML = `
                                <div class="text-center text-muted py-5" id="emptyState">
                                    <i class="fas fa-inbox fa-4x mb-4 opacity-50"></i>
                                    <h5>Semua komentar telah dihapus</h5>
                                    <p>Masukkan URL video YouTube dan klik Analisis untuk memulai lagi.</p>
                                </div>
                            `;
            } else {
              let judiCount = 0, cleanCount = 0;
              remainingRows.forEach(row => {
                if (row.dataset.prediction === 'judi') judiCount++;
                else cleanCount++;
              });
              document.getElementById('totalComments').textContent = remainingRows.length;
              document.getElementById('judiCount').textContent = judiCount;
              document.getElementById('cleanCount').textContent = cleanCount;
            }

            const selectAllCheckbox = document.getElementById('selectAll');
            if (selectAllCheckbox) selectAllCheckbox.checked = false;
            updateDeleteButton();

            showNotification(`Berhasil menghapus ${result.count} komentar!`, 'success');
          } else {
            let errorIcon = 'exclamation-triangle';
            let errorType = 'danger';

            if (result.error_type === 'no_permission') {
              errorIcon = 'lock';
              errorType = 'warning';
            } else if (result.error_type === 'auth') {
              errorIcon = 'user-slash';
              errorType = 'warning';
            }

            showNotification(result.msg, errorType, errorIcon);
          }
        } catch (error) {
          console.error('Error:', error);
          showNotification('Terjadi kesalahan saat menghapus komentar. Silakan coba lagi.', 'danger');
        } finally {
          this.disabled = false;
          updateDeleteButton();
        }
      }
    });
  }

  // ========================================================
  // 5. EKSPOR CSV
  // ========================================================
  const exportCsvBtn = document.getElementById('exportCsv');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', function () {
      const rows = document.querySelectorAll('#commentsTable tbody tr');
      let csv = 'Level,Username,Komentar,Komentar Bersih,Prediksi,Probabilitas,Waktu\n';

      rows.forEach(row => {
        if (row.style.display !== 'none') {
          const cells = row.querySelectorAll('td');
          const level = cells[1].textContent.trim();
          const username = cells[2].textContent.trim();
          const comment = cells[3].textContent.trim().replace(/"/g, '""');
          const clean = cells[4].textContent.trim().replace(/"/g, '""');
          const prediction = cells[5].textContent.trim();
          const probability = cells[6].querySelector('.text-nowrap').textContent.trim();
          const time = cells[7].textContent.trim();

          csv += `"${level}","${username}","${comment}","${clean}","${prediction}","${probability}","${time}"\n`;
        }
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const link = document.createElement('a');
      link.href = URL.createObjectURL(blob);
      link.download = 'deteksi_judi_youtube_' + new Date().getTime() + '.csv';
      link.click();
    });
  }

  // ========================================================
  // 6. SORTING TABEL
  // ========================================================
  (function () {
    const table = document.querySelector("#commentsTable");
    if (!table) return;
    table.querySelectorAll("th").forEach((th, colIndex) => {
      if (colIndex === 0) return; // Skip kolom checkbox
      th.style.cursor = "pointer";
      let asc = true;
      th.addEventListener("click", () => {
        const tbody = table.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));
        rows.sort((a, b) => {
          const A = a.children[colIndex].innerText.trim();
          const B = b.children[colIndex].innerText.trim();
          const numA = parseFloat(A.replace("%", "")) || A.toLowerCase();
          const numB = parseFloat(B.replace("%", "")) || B.toLowerCase();
          if (numA < numB) return asc ? -1 : 1;
          if (numA > numB) return asc ? 1 : -1;
          return 0;
        });
        rows.forEach(r => tbody.appendChild(r));
        asc = !asc;
      });
    });
  })();

});
