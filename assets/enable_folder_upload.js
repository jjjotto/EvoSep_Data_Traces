(function () {
  function applyDirectoryAttributes() {
    const uploadRoot = document.getElementById('upload-data');
    if (!uploadRoot) {
      return;
    }

    const inputs = uploadRoot.querySelectorAll('input[type="file"]');
    inputs.forEach((input) => {
      if (!input.hasAttribute('webkitdirectory')) {
        ['directory', 'webkitdirectory', 'mozdirectory', 'msdirectory', 'odirectory'].forEach((attr) => {
          input.setAttribute(attr, '');
        });
      }
    });
  }

  function startObserver() {
    applyDirectoryAttributes();

    const observer = new MutationObserver(() => {
      applyDirectoryAttributes();
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startObserver);
  } else {
    startObserver();
  }
})();
