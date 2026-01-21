
/**
 * Mendeteksi tipe URL yang dimasukkan (Channel atau Video).
 * @param {string} url - URL YouTube yang akan diperiksa.
 * @returns {string} - 'channel', 'video', atau 'unknown'.
 */
window.detectUrlType = function (url) {
    if (!url) return 'unknown';
    if (url.includes('@') || url.includes('/channel/') || url.includes('/c/') || url.includes('/user/')) {
        return 'channel';
    }
    else if (url.includes('watch?v=') || url.includes('youtu.be') || url.includes('/shorts/') || url.includes('/live/')) {
        return 'video';
    }
    return 'unknown';
};

/**
 * Memicu analisis video secara otomatis berdasarkan URL yang diberikan.
 * Mengisi input URL, memberikan umpan balik visual, dan mengklik tombol analisis.
 * @param {string} url - URL video yang akan dianalisis.
 */
window.analyzeVideo = function (url) {
    const urlInput = document.getElementById('urlInput');
    const analyzeBtn = document.getElementById('analyzeBtn');

    if (urlInput && analyzeBtn) {
        urlInput.value = url;
        urlInput.dispatchEvent(new Event('input'));

        urlInput.classList.add('highlight-input');
        setTimeout(() => urlInput.classList.remove('highlight-input'), 500);

        window.scrollTo({ top: 0, behavior: 'smooth' });

        setTimeout(() => {
            analyzeBtn.click();
        }, 300);
    }
};

/**
 * Mengatur visibilitas dan status (enabled/disabled) input form berdasarkan tipe URL.
 * Menampilkan input khusus channel atau video sesuai deteksi URL.
 */
window.toggleInputFields = function () {
    const urlInput = document.getElementById('urlInput');
    const videoInputContainer = document.getElementById('videoInputContainer');
    const channelInputContainer = document.getElementById('channelInputContainer');
    const commentsPerVideoContainer = document.getElementById('commentsPerVideoContainer');
    const maxResultsSelect = document.getElementById('maxResults');
    const videoCountSelect = document.getElementById('videoCount');
    const commentsPerVideoSelect = document.getElementById('commentsPerVideo');

    if (!urlInput) return;

    const url = urlInput.value.trim();
    const urlType = window.detectUrlType(url);

    console.log("Input berubah, Tipe:", urlType);

    if (urlType === 'channel') {
        if (videoInputContainer) videoInputContainer.classList.add('hidden');
        if (channelInputContainer) channelInputContainer.classList.remove('hidden');
        if (commentsPerVideoContainer) commentsPerVideoContainer.classList.remove('hidden');

        if (maxResultsSelect) maxResultsSelect.disabled = true;
        if (videoCountSelect) videoCountSelect.disabled = false;
        if (commentsPerVideoSelect) commentsPerVideoSelect.disabled = false;

    } else {
        if (videoInputContainer) videoInputContainer.classList.remove('hidden');
        if (channelInputContainer) channelInputContainer.classList.add('hidden');
        if (commentsPerVideoContainer) commentsPerVideoContainer.classList.add('hidden');

        if (maxResultsSelect) maxResultsSelect.disabled = false;
        if (videoCountSelect) videoCountSelect.disabled = true;
        if (commentsPerVideoSelect) commentsPerVideoSelect.disabled = true;
    }
};

/**
 * Memperbarui tampilan Floating Action Button (FAB) berdasarkan jumlah item yang dipilih.
 * Menampilkan jumlah item terpilih pada badge FAB.
 */
window.updateFab = function () {
    const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
    const fabContainer = document.getElementById('fabContainer');
    const fabCount = document.getElementById('fabCount');
    const modCount = document.getElementById('modCountText');

    if (fabCount) fabCount.innerText = checkedBoxes.length;
    if (modCount) modCount.innerText = checkedBoxes.length;

    if (fabContainer) {
        checkedBoxes.length > 0 ? fabContainer.classList.remove('hidden') : fabContainer.classList.add('hidden');
    }
};

/**
 * Secara otomatis mencentang baris komentar yang terdeteksi sebagai 'gambling'.
 * Memicu pembaruan FAB setelah pencentangan otomatis.
 */
window.autoCheckGamblingComments = function () {
    const checkboxes = document.querySelectorAll('.row-checkbox');
    if (checkboxes.length > 0) {
        let hasChecked = false;
        checkboxes.forEach(cb => {
            const row = cb.closest('tr');
            if (row && row.dataset.type === 'gambling' && !cb.checked) {
                cb.checked = true;
                hasChecked = true;
            }
        });
        if (hasChecked) {
            window.updateFab();
        }
    }
};

/**
 * Mengubah status centang semua checkbox baris berdasarkan status checkbox 'Select All'.
 * @param {HTMLInputElement} source - Checkbox utama (Select All).
 */
window.toggleAll = function (source) {
    const checkboxes = document.querySelectorAll('.row-checkbox');
    if (checkboxes.length === 0) return;

    checkboxes.forEach(cb => {
        if (cb.closest('tr').style.display !== 'none') {
            cb.checked = source.checked;
        }
    });
    window.updateFab();
};

/**
 * Memfilter tampilan tabel komentar berdasarkan tipe (semua, bersih, atau judol).
 * @param {string} value - Nilai filter ('all', 'bersih', 'gambling').
 */
window.filterTable = function (value) {
    const rows = document.querySelectorAll('.comment-row');
    if (rows.length === 0) return;

    rows.forEach(row => {
        if (value === 'all') row.style.display = '';
        else row.style.display = (row.dataset.type === value) ? '' : 'none';
    });
    window.updateFab();
};

/**
 * Membuka modal konfirmasi moderasi jika user sudah login (FAB tersedia).
 * Jika user belum login, membuka modal permintaan login.
 */
window.openModerationModal = function () {
    const fabContainer = document.getElementById('fabContainer');

    if (!fabContainer) {
        const loginModal = document.getElementById('loginRequiredModal');
        if (loginModal) loginModal.classList.remove('hidden');
    } else {
        const modModal = document.getElementById('moderationModal');
        if (modModal) modModal.classList.remove('hidden');
    }
};

/**
 * Menutup modal moderasi.
 */
window.closeModerationModal = function () {
    const el = document.getElementById('moderationModal');
    if (el) el.classList.add('hidden');
};

/**
 * Menutup modal yang meminta login.
 */
window.closeLoginRequiredModal = function () {
    const el = document.getElementById('loginRequiredModal');
    if (el) el.classList.add('hidden');
};

/**
 * Menutup modal error.
 */
window.closeErrorModal = function () {
    const el = document.getElementById('errorModal');
    if (el) el.classList.add('hidden');
};

/**
 * Menutup modal sukses.
 */
window.closeSuccessModal = function () {
    const el = document.getElementById('successModal');
    if (el) el.classList.add('hidden');
};

/**
 * Membuka modal sukses dengan pesan tertentu.
 * @param {string} msg - Pesan sukses yang akan ditampilkan.
 */
window.openSuccessModal = function (msg) {
    const msgEl = document.getElementById('successModalMsg');
    const modalEl = document.getElementById('successModal');
    if (msgEl) msgEl.innerText = msg;
    if (modalEl) modalEl.classList.remove('hidden');
};

/**
 * Membuka modal error dengan pesan tertentu.
 * @param {string} msg - Pesan error yang akan ditampilkan.
 */
window.openErrorModal = function (msg) {
    const msgEl = document.getElementById('errorModalMsg');
    const modalEl = document.getElementById('errorModal');
    if (msgEl) msgEl.innerText = msg;
    if (modalEl) modalEl.classList.remove('hidden');
};

/**
 * Menginisialisasi logika sidebar (buka/tutup) untuk tampilan mobile.
 * Menangani event klik tombol burger, overlay, dan tombol escape.
 */
window.initSidebar = function () {
    const burgerBtn = document.getElementById('burgerMenu');
    const burgerBtnSidebar = document.getElementById('burgerMenuSidebar');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    function toggleSidebar() {
        if (sidebar) sidebar.classList.toggle('active');
        if (overlay) overlay.classList.toggle('active');
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
    }

    if (burgerBtn) {
        burgerBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSidebar();
        });
    }

    if (burgerBtnSidebar) {
        burgerBtnSidebar.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleSidebar();
        });
    }

    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }

    const sidebarLinks = document.querySelectorAll('.sidebar-item');
    sidebarLinks.forEach(link => {
        link.addEventListener('click', closeSidebar);
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeSidebar();
    });
};

/**
 * Fungsi inisialisasi utama aplikasi.
 * Mengatur konfigurasi, sidebar, event listener form, dan logika moderasi.
 * @param {Object} config - Konfigurasi situs (csrfToken, moderateUrl, dll).
 */
window.initMain = function (config) {
    window.siteConfig = config || {};
    console.log("Main Script Initialized with Config");

    window.initSidebar();

    const urlInput = document.getElementById('urlInput');

    if (urlInput) {
        urlInput.addEventListener('input', window.toggleInputFields);
        urlInput.addEventListener('change', window.toggleInputFields);
        window.toggleInputFields();
    }

    window.updateFab();

    const confirmBtn = document.getElementById('confirmModerationBtn');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function () {
            const checkedBoxes = document.querySelectorAll('.row-checkbox:checked');
            const ids = Array.from(checkedBoxes).map(cb => cb.value);

            if (ids.length === 0) return;

            const originalText = this.innerHTML;
            this.innerHTML = 'Memproses...';
            this.disabled = true;

            const blockUserCheckbox = document.getElementById('blockUserCheckbox');
            const blockUserVal = blockUserCheckbox && blockUserCheckbox.checked ? '1' : '0';

            const formData = new FormData();
            formData.append('csrfmiddlewaretoken', window.siteConfig.csrfToken);
            formData.append('action', 'reject');
            formData.append('block_user', blockUserVal);
            ids.forEach(id => formData.append('comment_id', id));

            if (!window.siteConfig.moderateUrl) {
                console.error("Moderate URL not found in config");
                window.openErrorModal("Konfigurasi URL tidak ditemukan.");
                this.innerHTML = originalText;
                this.disabled = false;
                return;
            }

            fetch(window.siteConfig.moderateUrl, {
                method: 'POST',
                body: formData
            })
                .then(res => res.json().then(data => ({ status: res.status, body: data })))
                .then(result => {
                    window.closeModerationModal();
                    if (result.body.ok) {
                        window.openSuccessModal(result.body.msg || "Berhasil!");
                        checkedBoxes.forEach(cb => cb.closest('tr').remove());
                        window.updateFab();
                        const selectAll = document.getElementById('selectAllCheckbox');
                        if (selectAll) selectAll.checked = false;
                    } else {
                        window.openErrorModal(result.body.msg || "Gagal moderasi.");
                    }
                })
                .catch(err => {
                    console.error(err);
                    window.closeModerationModal();
                    window.openErrorModal("Koneksi server bermasalah.");
                })
                .finally(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                });
        });
    }
};

/**
 * Event listener HTMX: Dijalankan setelah konten baru dimuat (afterSwap).
 * Memperbarui FAB dan otomatis mencentang komentar judi.
 */
document.body.addEventListener('htmx:afterSwap', function (evt) {
    if (evt.detail.target.id === "resultsContainer") {
        window.updateFab();
        setTimeout(window.autoCheckGamblingComments, 100);
    }
});

/**
 * Event listener HTMX: Dijalankan setelah request selesai dan sukses (afterRequest).
 */
document.body.addEventListener('htmx:afterRequest', function (evt) {
    if (evt.detail.target.id === "resultsContainer" && evt.detail.successful) {
        window.updateFab();
        setTimeout(window.autoCheckGamblingComments, 100);
    }
});

/**
 * Event listener HTMX: Dijalankan setelah konten menetap di DOM (afterSettle).
 */
document.body.addEventListener('htmx:afterSettle', function (evt) {
    if (evt.detail.target.id === "resultsContainer") {
        window.updateFab();
        setTimeout(window.autoCheckGamblingComments, 100);
    }
});
