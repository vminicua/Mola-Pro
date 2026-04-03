(function (window, document, $) {
  'use strict';

  if (!$ || !$.fn || !$.fn.select2) {
    return;
  }

  function shouldSkip($select) {
    if ($select.is('[data-select2="off"], [data-select2-ignore]')) {
      return true;
    }

    if ($select.closest('.dataTables_length').length) {
      return true;
    }

    if ($select.hasClass('select2-hidden-accessible')) {
      return true;
    }

    const $modal = $select.closest('.modal');
    if ($modal.length && !$modal.hasClass('show')) {
      return true;
    }

    return false;
  }

  function getPlaceholder($select) {
    const explicitPlaceholder = $select.data('placeholder');
    if (explicitPlaceholder) {
      return explicitPlaceholder;
    }

    const firstOption = $select.find('option').first();
    if (firstOption.length && firstOption.val() === '') {
      return firstOption.text().trim();
    }

    return 'Seleccione...';
  }

  function buildOptions($select) {
    const options = {
      width: '100%',
      placeholder: getPlaceholder($select),
      allowClear: !$select.prop('multiple') && $select.find('option[value=""]').length > 0,
      dropdownAutoWidth: false
    };

    const $modal = $select.closest('.modal');
    if ($modal.length) {
      options.dropdownParent = $modal;
    }

    return options;
  }

  function init(context) {
    const $root = context ? $(context) : $(document);

    $root.find('select.form-select, select.select2').each(function () {
      const $select = $(this);

      if (shouldSkip($select)) {
        return;
      }

      $select.select2(buildOptions($select));
    });
  }

  function syncValue(selector, value) {
    const $select = selector && selector.jquery ? selector : $(selector);
    if (!$select.length) {
      return;
    }

    $select.val(value).trigger('change');
  }

  window.MolaSelect2 = {
    init: init,
    syncValue: syncValue
  };

  document.addEventListener('DOMContentLoaded', function () {
    init(document);
  });

  document.addEventListener('shown.bs.modal', function (event) {
    init(event.target);
  });
})(window, document, window.jQuery);
