(function () {
  if (window.MolaProcessing) {
    return;
  }

  var activeRequests = 0;
  var pageUnloading = false;
  var pendingForms = new Set();
  var formStates = new WeakMap();
  var jqueryBound = false;

  function injectStyles() {
    if (document.getElementById('mola-processing-styles')) {
      return;
    }

    var style = document.createElement('style');
    style.id = 'mola-processing-styles';
    style.textContent = [
      'body.mola-processing-active { cursor: progress; }',
      'body.mola-processing-active > *:not(.swal2-container) { pointer-events: none !important; }',
      'body.mola-processing-active .swal2-container,',
      'body.mola-processing-active .swal2-container * { pointer-events: auto !important; }',
      '.mola-processing-disabled { opacity: 0.7 !important; cursor: not-allowed !important; }'
    ].join('\n');

    document.head.appendChild(style);
  }

  function hasSwal() {
    return typeof window.Swal !== 'undefined' && typeof window.Swal.fire === 'function';
  }

  function isLoadingDialogOpen() {
    return hasSwal() && typeof window.Swal.isLoading === 'function' && window.Swal.isLoading();
  }

  function showLoading(message) {
    if (!hasSwal()) {
      return;
    }

    if (isLoadingDialogOpen()) {
      return;
    }

    window.Swal.fire({
      title: 'A processar...',
      text: message || 'Por favor aguarde.',
      allowOutsideClick: false,
      allowEscapeKey: false,
      showConfirmButton: false,
      didOpen: function () {
        window.Swal.showLoading();
      }
    });
  }

  function closeLoadingIfNeeded() {
    if (isLoadingDialogOpen()) {
      window.Swal.close();
    }
  }

  function getSubmitControls(form) {
    return Array.prototype.slice.call(
      form.querySelectorAll('button[type="submit"], input[type="submit"], input[type="image"], button:not([type])')
    );
  }

  function lockForm(form) {
    if (formStates.has(form)) {
      return;
    }

    var controls = getSubmitControls(form).map(function (control) {
      return {
        control: control,
        disabled: control.disabled
      };
    });

    controls.forEach(function (entry) {
      entry.control.disabled = true;
      entry.control.classList.add('mola-processing-disabled');
      entry.control.setAttribute('data-mola-processing-disabled', 'true');
    });

    formStates.set(form, { controls: controls });
    form.setAttribute('data-mola-processing-locked', 'true');
  }

  function unlockForm(form) {
    var state = formStates.get(form);

    if (state) {
      state.controls.forEach(function (entry) {
        entry.control.disabled = entry.disabled;
        entry.control.classList.remove('mola-processing-disabled');
        entry.control.removeAttribute('data-mola-processing-disabled');
      });

      formStates.delete(form);
    }

    form.removeAttribute('data-mola-processing-locked');
  }

  function clearPendingForms() {
    pendingForms.forEach(function (form) {
      unlockForm(form);
    });

    pendingForms.clear();
  }

  function refreshProcessingState(message) {
    var isBusy = activeRequests > 0 || pendingForms.size > 0;

    if (document.body) {
      document.body.classList.toggle('mola-processing-active', isBusy);
    }

    if (isBusy) {
      showLoading(message);
    } else {
      closeLoadingIfNeeded();
    }
  }

  function beginRequest(message) {
    activeRequests += 1;
    refreshProcessingState(message || 'Por favor aguarde.');
  }

  function endRequest() {
    if (activeRequests > 0) {
      activeRequests -= 1;
    }

    if (activeRequests === 0) {
      clearPendingForms();
    }

    refreshProcessingState();
  }

  function shouldHandleForm(form) {
    if (!form || form.getAttribute('data-skip-processing') === 'true') {
      return false;
    }

    var method = (form.getAttribute('method') || '').trim().toLowerCase();
    return method !== 'get';
  }

  function handleFormSubmit(event) {
    var form = event.target;

    if (!shouldHandleForm(form)) {
      return;
    }

    if (form.getAttribute('data-mola-processing-locked') === 'true') {
      event.preventDefault();
      event.stopPropagation();
      return;
    }

    pendingForms.add(form);
    lockForm(form);
    refreshProcessingState(form.getAttribute('data-processing-text') || 'A processar dados...');

    window.setTimeout(function () {
      if (pageUnloading || activeRequests > 0 || !pendingForms.has(form)) {
        return;
      }

      pendingForms.delete(form);
      unlockForm(form);
      refreshProcessingState();
    }, 450);
  }

  function bindFetch() {
    if (!window.fetch || window.fetch.__molaProcessingWrapped) {
      return;
    }

    var nativeFetch = window.fetch.bind(window);

    function wrappedFetch() {
      beginRequest('A processar pedido...');
      return nativeFetch.apply(window, arguments).finally(function () {
        endRequest();
      });
    }

    wrappedFetch.__molaProcessingWrapped = true;
    window.fetch = wrappedFetch;
  }

  function bindJQueryAjax() {
    if (jqueryBound || !window.jQuery) {
      return false;
    }

    jqueryBound = true;

    window.jQuery(document).ajaxSend(function () {
      beginRequest('A processar pedido...');
    });

    window.jQuery(document).ajaxComplete(function () {
      endRequest();
    });

    return true;
  }

  injectStyles();
  bindFetch();
  bindJQueryAjax();

  if (!jqueryBound) {
    document.addEventListener('DOMContentLoaded', bindJQueryAjax);
    window.addEventListener('load', bindJQueryAjax);
  }

  document.addEventListener('submit', handleFormSubmit, true);

  window.addEventListener('beforeunload', function () {
    pageUnloading = true;
  });

  window.MolaProcessing = {
    begin: beginRequest,
    end: endRequest,
    clear: function () {
      activeRequests = 0;
      clearPendingForms();
      refreshProcessingState();
    },
    isBusy: function () {
      return activeRequests > 0 || pendingForms.size > 0;
    }
  };
}());
