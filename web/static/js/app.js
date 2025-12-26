// Minimal JS setup
console.log('App.js loaded v0.5.6');

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded');

    // Tab Switching Logic
    const tabs = document.querySelectorAll('.nav-item');
    const sections = document.querySelectorAll('.tab-section');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            sections.forEach(s => s.classList.add('hidden'));
            
            const targetId = tab.dataset.target;
            const targetSection = document.getElementById(targetId);
            if (targetSection) {
                targetSection.classList.remove('hidden');
            }
        });
    });

    // --- Modal Logic ---
    
    function openModal(modalId) {
        console.log('Opening modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('show');
            // Support legacy 'active' class used in settings_form.html
            modal.classList.add('active');
        } else {
            console.error('Modal element not found:', modalId);
        }
    }

    function closeModal(modalId) {
        console.log('Closing modal:', modalId);
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('show');
            modal.classList.remove('active');
        }
    }

    // Help Modal
    const helpBtn = document.getElementById('help-btn');
    if (helpBtn) {
        helpBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('help-modal');
        });
    }

    const closeHelpBtn = document.querySelector('#help-modal .close-modal-btn');
    if (closeHelpBtn) {
        closeHelpBtn.addEventListener('click', () => closeModal('help-modal'));
    }

    // Upload Modal
    const uploadBtn = document.getElementById('upload-btn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openModal('upload-modal');
        });
    }

    // Close buttons for Upload Modal
    const closeUploadBtns = [
        document.getElementById('close-upload-modal-btn'),
        document.getElementById('x-close-upload-modal-btn')
    ];
    closeUploadBtns.forEach(btn => {
        if (btn) {
            btn.addEventListener('click', () => closeModal('upload-modal'));
        }
    });

    // Close any modal when clicking overlay
    const overlays = document.querySelectorAll('.modal-overlay');
    overlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('show');
                overlay.classList.remove('active');
            }
        });
    });
});

// Variant tab switching (event delegation for HTMX swaps)
document.addEventListener('click', (event) => {
    const tab = event.target.closest('.variant-tab');
    if (!tab) return;

    const wrapper = tab.closest('.result-wrapper');
    if (!wrapper) return;

    const targetId = tab.getAttribute('data-variant-tab');
    if (targetId === null) return;

    const tabs = wrapper.querySelectorAll('.variant-tab');
    const panels = wrapper.querySelectorAll('.variant-panel');

    tabs.forEach((item) => item.classList.remove('active'));
    tab.classList.add('active');

    panels.forEach((panel) => {
        const panelId = panel.getAttribute('data-variant-panel');
        if (panelId === targetId) {
            panel.classList.add('active');
        } else {
            panel.classList.remove('active');
        }
    });
});

// Member modal management
let currentMemberName = "";

function openMemberModal(name, minDaysDay, minDaysNight) {
    currentMemberName = name;
    const modal = document.getElementById('member-modal');
    if (modal) {
        document.getElementById("modal-member-name").textContent = name;
        document.getElementById("modal-min-days-day").value = minDaysDay || "";
        document.getElementById("modal-min-days-night").value = minDaysNight || "";
        modal.classList.add('active');
        modal.classList.add('show');
    }
}

function closeMemberModal() {
    const modal = document.getElementById('member-modal');
    if (modal) {
        modal.classList.remove('active');
        modal.classList.remove('show');
    }
    currentMemberName = "";
}

function saveMemberAttributes() {
    if (!currentMemberName) {
        console.error('No member selected');
        return;
    }

    const data = {
        name: currentMemberName,
        min_days_day: document.getElementById("modal-min-days-day").value,
        min_days_night: document.getElementById("modal-min-days-night").value,
    };

    fetch("/settings/member/update", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    })
        .then((response) => response.json())
        .then((result) => {
            if (result.success) {
                closeMemberModal();
                window.location.reload();
            } else {
                alert("エラー: " + result.error);
            }
        })
        .catch((error) => {
            console.error('Save error:', error);
            alert("通信エラー: " + error);
        });
}

/**
 * メンバーを追加する関数
 * @param {HTMLInputElement} inputElement - 名前入力欄
 * @param {string} groupName - グループ名（例: 'day_index_1_2'）
 */
function addMember(inputElement, groupName) {
    const name = inputElement.value.trim();

    if (!name) {
        alert('名前を入力してください');
        return;
    }

    // 対象のリストコンテナを取得
    const listContainer = document.querySelector(`.sortable-list[data-input-name="${groupName}"]`);

    if (!listContainer) {
        console.error(`List container not found for group: ${groupName}`);
        return;
    }

    // グループに応じた移動先と勤務種別を判定
    const moveConfig = getMoveConfig(groupName);

    // 新しいメンバーカードを作成
    const memberCard = document.createElement('div');
    memberCard.className = 'member-card';
    memberCard.innerHTML = `
        <input type="hidden" name="${groupName}[]" value="${name}" class="member-id" />
        <label style="display: flex; align-items: center; width: 100%; margin: 0;">
            <input type="checkbox" name="active_${name}_${moveConfig.shiftType}" checked />
            <span style="flex: 1; font-weight: 500;">${name}</span>
        </label>
        ${moveConfig.moveButton}
        <button type="button" class="btn-edit" onclick="openMemberModal('${name}', '', '')">
            ✎
        </button>
        <button type="button" class="btn-remove" onclick="this.closest('.member-card').remove()" title="削除">
            ×
        </button>
    `;

    // リストに追加
    listContainer.appendChild(memberCard);

    // 入力欄をクリア
    inputElement.value = '';
    inputElement.focus();
}

/**
 * グループ名から移動設定を取得
 * @param {string} groupName - グループ名
 * @returns {Object} - 移動設定
 */
function getMoveConfig(groupName) {
    const configs = {
        'day_index_1_2': {
            targetGroup: 'day_index_3',
            arrow: '→',
            shiftType: 'day'
        },
        'day_index_3': {
            targetGroup: 'day_index_1_2',
            arrow: '←',
            shiftType: 'day'
        },
        'night_index_1': {
            targetGroup: 'night_index_2',
            arrow: '→',
            shiftType: 'night'
        },
        'night_index_2': {
            targetGroup: 'night_index_1',
            arrow: '←',
            shiftType: 'night'
        }
    };

    const config = configs[groupName];
    if (config) {
        return {
            shiftType: config.shiftType,
            moveButton: `<button type="button" class="btn-move" onclick="moveMemberToGroup(this, '${config.targetGroup}')" title="${config.arrow === '→' ? '右' : '左'}のグループへ移動">${config.arrow}</button>`
        };
    }

    // デフォルト（移動ボタンなし）
    return {
        shiftType: 'day',
        moveButton: ''
    };
}

/**
 * メンバーを別のグループに移動
 * @param {HTMLElement} buttonElement - クリックされたボタン要素
 * @param {string} targetGroupName - 移動先グループ名
 */
function moveMemberToGroup(buttonElement, targetGroupName) {
    const memberCard = buttonElement.closest('.member-card');
    if (!memberCard) {
        console.error('Member card not found');
        return;
    }

    // メンバー情報を取得
    const memberNameSpan = memberCard.querySelector('label span');
    const memberName = memberNameSpan ? memberNameSpan.textContent.trim() : '';
    const isActive = memberCard.querySelector('input[type="checkbox"]').checked;

    if (!memberName) {
        console.error('Member name not found');
        return;
    }

    // 移動先のリストコンテナを取得
    const targetContainer = document.querySelector(`.sortable-list[data-input-name="${targetGroupName}"]`);
    if (!targetContainer) {
        console.error(`Target container not found: ${targetGroupName}`);
        return;
    }

    // 現在のカードを削除
    memberCard.remove();

    // 移動先グループの設定を取得
    const moveConfig = getMoveConfig(targetGroupName);

    // 新しいメンバーカードを作成
    const newMemberCard = document.createElement('div');
    newMemberCard.className = 'member-card';
    newMemberCard.innerHTML = `
        <input type="hidden" name="${targetGroupName}[]" value="${memberName}" class="member-id" />
        <label style="display: flex; align-items: center; width: 100%; margin: 0;">
            <input type="checkbox" name="active_${memberName}_${moveConfig.shiftType}" ${isActive ? 'checked' : ''} />
            <span style="flex: 1; font-weight: 500;">${memberName}</span>
        </label>
        ${moveConfig.moveButton}
        <button type="button" class="btn-edit" onclick="openMemberModal('${memberName}', '', '')" title="編集">
            ✎
        </button>
        <button type="button" class="btn-remove" onclick="this.closest('.member-card').remove()" title="削除">
            ×
        </button>
    `;

    // 移動先リストに追加
    targetContainer.appendChild(newMemberCard);
}
