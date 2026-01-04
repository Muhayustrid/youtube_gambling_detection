/**
 * Results Handler for AI Insight Display
 * Handles filtering, interactions, and enhanced UX for results_partial.html
 */

document.addEventListener('DOMContentLoaded', function() {
    // Cache DOM elements
    const filterSelect = document.getElementById('filterSelect');
    const commentsTable = document.getElementById('commentsTable');
    const resultsBody = document.getElementById('resultsBody');
    const selectAllCheckbox = document.getElementById('selectAllCheckbox');
    const fabContainer = document.querySelector('.fab-container');
    const fabBtn = document.querySelector('.fab-btn');
    const fabCount = document.querySelector('.fab-count');
    const moderationModal = document.getElementById('moderationModal');
    const cancelModerationBtn = document.getElementById('cancelModerationBtn');
    const confirmModerationBtn = document.getElementById('confirmModerationBtn');
    
    // AI Insight Elements
    const aiInsightBox = document.querySelector('.ai-insight-box');
    const insightContent = document.querySelector('.insight-content');
    
    // State
    let currentFilter = 'all';
    let checkedCount = 0;
    
    // Initialize
    init();
    
    function init() {
        setupFilterListener();
        setupCheckboxListeners();
        setupSelectAllListener();
        setupModerationModal();
        setupAIInsightInteractions();
        updateFAB();
        
        // Add smooth scroll behavior for better UX
        if (aiInsightBox) {
            setTimeout(() => {
                aiInsightBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 500);
        }
    }
    
    // Filter Functionality
    function setupFilterListener() {
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                currentFilter = e.target.value;
                filterTable(currentFilter);
            });
        }
    }
    
    function filterTable(filterValue) {
        const rows = resultsBody.querySelectorAll('tr.comment-row');
        
        rows.forEach(row => {
            const type = row.getAttribute('data-type');
            
            if (filterValue === 'all') {
                row.style.display = '';
                row.style.animation = 'fadeIn 0.3s ease-out';
            } else if (type === filterValue) {
                row.style.display = '';
                row.style.animation = 'fadeIn 0.3s ease-out';
            } else {
                row.style.display = 'none';
            }
        });
        
        // Update stats based on filter
        updateStatsForFilter(filterValue);
    }
    
    function updateStatsForFilter(filterValue) {
        const rows = Array.from(resultsBody.querySelectorAll('tr.comment-row'));
        const visibleRows = rows.filter(row => {
            const type = row.getAttribute('data-type');
            return filterValue === 'all' || type === filterValue;
        });
        
        const total = visibleRows.length;
        const gamblingCount = visibleRows.filter(row => row.getAttribute('data-type') === 'gambling').length;
        const cleanCount = total - gamblingCount;
        
        // Update stat cards with animation
        animateValue('statTotal', total);
        animateValue('statClean', cleanCount);
        animateValue('statGambling', gamblingCount);
    }
    
    // Checkbox Management
    function setupCheckboxListeners() {
        const checkboxes = document.querySelectorAll('.row-checkbox');
        checkboxes.forEach(cb => {
            cb.addEventListener('change', handleCheckboxChange);
        });
        updateFAB();
    }
    
    function handleCheckboxChange(e) {
        updateFAB();
        
        // Add visual feedback
        const row = e.target.closest('tr');
        if (e.target.checked) {
            row.style.backgroundColor = '#fef3c7';
            setTimeout(() => {
                row.style.transition = 'background-color 0.3s ease';
                row.style.backgroundColor = '';
            }, 300);
        }
    }
    
    function setupSelectAllListener() {
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                const isChecked = e.target.checked;
                const checkboxes = document.querySelectorAll('.row-checkbox');
                
                checkboxes.forEach(cb => {
                    cb.checked = isChecked;
                    // Trigger change event manually
                    cb.dispatchEvent(new Event('change'));
                });
            });
        }
    }
    
    function updateFAB() {
        const checkboxes = document.querySelectorAll('.row-checkbox');
        checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
        
        if (fabCount) {
            fabCount.textContent = checkedCount;
        }
        
        if (fabContainer) {
            if (checkedCount > 0) {
                fabContainer.classList.remove('hidden');
                fabContainer.style.transform = 'scale(1)';
            } else {
                fabContainer.style.transform = 'scale(0)';
                setTimeout(() => {
                    if (checkedCount === 0) {
                        fabContainer.classList.add('hidden');
                    }
                }, 200);
            }
        }
    }
    
    // Moderation Modal
    function setupModerationModal() {
        if (fabBtn) {
            fabBtn.addEventListener('click', () => {
                if (moderationModal) {
                    moderationModal.classList.remove('hidden');
                    moderationModal.style.opacity = '1';
                }
            });
        }
        
        if (cancelModerationBtn) {
            cancelModerationBtn.addEventListener('click', closeModal);
        }
        
        if (confirmModerationBtn) {
            confirmModerationBtn.addEventListener('click', () => {
                // Show success message
                showNotification(`${checkedCount} komentar telah dimoderasi berhasil!`, 'success');
                
                // Remove checked rows with animation
                const checkedRows = document.querySelectorAll('.row-checkbox:checked');
                checkedRows.forEach(cb => {
                    const row = cb.closest('tr');
                    row.style.transition = 'all 0.3s ease';
                    row.style.transform = 'translateX(-100%)';
                    row.style.opacity = '0';
                    setTimeout(() => {
                        row.remove();
                    }, 300);
                });
                
                // Reset checkboxes
                if (selectAllCheckbox) {
                    selectAllCheckbox.checked = false;
                }
                
                closeModal();
                updateFAB();
                
                // Update stats
                setTimeout(() => {
                    filterTable(currentFilter);
                }, 400);
            });
        }
        
        // Close modal on overlay click
        if (moderationModal) {
            moderationModal.addEventListener('click', (e) => {
                if (e.target === moderationModal) {
                    closeModal();
                }
            });
        }
    }
    
    function closeModal() {
        if (moderationModal) {
            moderationModal.style.opacity = '0';
            setTimeout(() => {
                moderationModal.classList.add('hidden');
            }, 200);
        }
    }
    
    // AI Insight Enhancements
    function setupAIInsightInteractions() {
        if (!aiInsightBox) return;
        
        // Add hover effect for better interactivity
        aiInsightBox.addEventListener('mouseenter', () => {
            aiInsightBox.style.transform = 'translateY(-2px)';
        });
        
        aiInsightBox.addEventListener('mouseleave', () => {
            aiInsightBox.style.transform = 'translateY(0)';
        });
        
        // Add click to copy functionality for insight text
        if (insightContent) {
            insightContent.style.cursor = 'pointer';
            insightContent.title = 'Klik untuk menyalin analisis';
            
            insightContent.addEventListener('click', () => {
                const text = insightContent.textContent;
                navigator.clipboard.writeText(text).then(() => {
                    showNotification('Analisis disalin ke clipboard!', 'info');
                }).catch(() => {
                    showNotification('Gagal menyalin analisis', 'error');
                });
            });
        }
        
        // Highlight risk levels in the insight
        highlightRiskLevels();
    }
    
    function highlightRiskLevels() {
        if (!insightContent) return;
        
        const content = insightContent.innerHTML;
        
        // Highlight risk levels with colors
        let highlighted = content;
        highlighted = highlighted.replace(/TINGGI/g, '<span class="risk-high">TINGGI</span>');
        highlighted = highlighted.replace(/SEDANG/g, '<span class="risk-medium">SEDANG</span>');
        highlighted = highlighted.replace(/RENDAH/g, '<span class="risk-low">RENDAH</span>');
        highlighted = highlighted.replace(/AMAN/g, '<span class="risk-safe">AMAN</span>');
        
        insightContent.innerHTML = highlighted;
    }
    
    // Utility Functions
    function animateValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (!element) return;
        
        const current = parseInt(element.textContent) || 0;
        const duration = 300;
        const steps = 20;
        const increment = (value - current) / steps;
        let step = 0;
        
        const timer = setInterval(() => {
            step++;
            const newValue = Math.round(current + (increment * step));
            element.textContent = newValue;
            
            if (step >= steps) {
                element.textContent = value;
                clearInterval(timer);
            }
        }, duration / steps);
        
        // Add pulse effect
        element.style.transform = 'scale(1.1)';
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }
    
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Style it
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#059669' : type === 'error' ? '#dc2626' : '#111827'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            font-weight: 500;
            animation: slideInRight 0.3s ease-out;
            max-width: 300px;
        `;
        
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                notification.remove();
            }, 300);
        }, 3000);
    }
    
    // Add CSS animations for notifications
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .risk-high {
            color: #dc2626 !important;
            background: #fef2f2;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-weight: 700;
        }
        
        .risk-medium {
            color: #d97706 !important;
            background: #fef3c7;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-weight: 600;
        }
        
        .risk-low {
            color: #059669 !important;
            background: #ecfdf5;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-weight: 600;
        }
        
        .risk-safe {
            color: #059669 !important;
            background: #ecfdf5;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-weight: 700;
            font-size: 1.05em;
        }
        
        .insight-content {
            cursor: pointer;
            transition: background-color 0.2s ease;
        }
        
        .insight-content:hover {
            background-color: #f9fafb;
        }
        
        .ai-insight-box {
            transition: all 0.3s ease;
        }
        
        .fab-container {
            transition: transform 0.2s ease, opacity 0.2s ease;
        }
        
        tr {
            transition: background-color 0.3s ease;
        }
    `;
    document.head.appendChild(style);
});
