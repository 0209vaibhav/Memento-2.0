// Confirmation Dialog Function
function showConfirmationDialog(options = {}) {
  const {
    title = 'Confirm Action',
    message = 'Are you sure you want to proceed?',
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    onConfirm = () => {},
    onCancel = () => {}
  } = options;

  // Get or create dialog element
  let dialog = document.getElementById('confirmation-dialog');
  if (!dialog) {
    dialog = document.createElement('div');
    dialog.id = 'confirmation-dialog';
    dialog.className = 'confirmation-dialog hidden';
    dialog.innerHTML = `
      <div class="confirmation-dialog-content">
        <div class="confirmation-dialog-header">
          <h3>${title}</h3>
          <button class="close-dialog-btn">&times;</button>
        </div>
        <div class="confirmation-dialog-body">
          <p>${message}</p>
        </div>
        <div class="confirmation-dialog-footer">
          <button class="cancel-btn">${cancelText}</button>
          <button class="confirm-btn">${confirmText}</button>
        </div>
      </div>
    `;
    document.body.appendChild(dialog);
  }

  // Update dialog content
  dialog.querySelector('.confirmation-dialog-header h3').textContent = title;
  dialog.querySelector('.confirmation-dialog-body p').textContent = message;
  dialog.querySelector('.confirm-btn').textContent = confirmText;
  dialog.querySelector('.cancel-btn').textContent = cancelText;

  // Show dialog
  dialog.classList.remove('hidden');

  // Handle dialog close button
  const closeBtn = dialog.querySelector('.close-dialog-btn');
  closeBtn.onclick = () => {
    dialog.classList.add('hidden');
    onCancel();
  };

  // Handle cancel button
  const cancelBtn = dialog.querySelector('.cancel-btn');
  cancelBtn.onclick = () => {
    dialog.classList.add('hidden');
    onCancel();
  };

  // Handle confirm button
  const confirmBtn = dialog.querySelector('.confirm-btn');
  confirmBtn.onclick = () => {
    dialog.classList.add('hidden');
    onConfirm();
  };

  // Handle clicking outside the dialog
  dialog.onclick = (e) => {
    if (e.target === dialog) {
      dialog.classList.add('hidden');
      onCancel();
    }
  };

  // Return a promise that resolves when confirmed or rejects when cancelled
  return new Promise((resolve, reject) => {
    confirmBtn.onclick = () => {
      dialog.classList.add('hidden');
      onConfirm();
      resolve(true);
    };

    const handleCancel = () => {
      dialog.classList.add('hidden');
      onCancel();
      reject(false);
    };

    closeBtn.onclick = handleCancel;
    cancelBtn.onclick = handleCancel;
    dialog.onclick = (e) => {
      if (e.target === dialog) {
        handleCancel();
      }
    };
  });
} 