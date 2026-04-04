(function () {
  if (window.MolaLocale) {
    return;
  }

  var configNode = document.getElementById('molaLocaleConfig');
  var parsedConfig = {};

  if (configNode) {
    try {
      parsedConfig = JSON.parse(configNode.textContent || '{}');
    } catch (error) {
      parsedConfig = {};
    }
  }

  var translationLanguage = parsedConfig.translationLanguage || 'pt';
  var currencyConfig = parsedConfig.currency || {};
  var exactTranslations = {
    en: {
      'Validação': 'Validation',
      'Erro': 'Error',
      'Aviso': 'Warning',
      'Info': 'Info',
      'Criada': 'Created',
      'Actualizada': 'Updated',
      'Desactivada': 'Disabled',
      'Confirmado': 'Confirmed',
      'Rejeitado': 'Rejected',
      'Registada': 'Recorded',
      'Registado': 'Recorded',
      'Desembolso registado': 'Disbursement recorded',
      'Pagamento registado': 'Payment recorded',
      'Empréstimo criado': 'Loan created',
      'Preferências guardadas': 'Preferences saved',
      'A processar...': 'Processing...',
      'Por favor aguarde.': 'Please wait.',
      'A processar pedido...': 'Processing request...',
      'A processar dados...': 'Processing data...',
      'Cancelar': 'Cancel',
      'Confirmar': 'Confirm',
      'Sim': 'Yes',
      'OK': 'OK',
      'Preencha todos os campos obrigatórios.': 'Fill in all required fields.',
      'Categoria e nome são obrigatórios.': 'Category and name are required.',
      'O nome da categoria é obrigatório.': 'The category name is required.',
      'O nome do tipo de rendimento é obrigatório.': 'The income type name is required.',
      'O nome do grupo é obrigatório.': 'The group name is required.',
      'O nome do tipo de empréstimo é obrigatório.': 'The loan type name is required.',
      'Nome, taxa e tipo de período são obrigatórios.': 'Name, rate, and period type are required.',
      'Selecione um tipo de juro.': 'Select an interest type.',
      'Selecione o membro/cliente.': 'Select the member/client.',
      'Selecione o tipo de juro.': 'Select the interest type.',
      'Informe o valor do empréstimo.': 'Enter the loan amount.',
      'Informe o número de períodos.': 'Enter the number of periods.',
      'Informe o número de meses.': 'Enter the number of months.',
      'Informe o número de dias.': 'Enter the number of days.',
      'Informe o pagamento por ciclo (pode usar o valor sugerido).': 'Enter the payment per cycle (you can use the suggested amount).',
      'Pagamento por ciclo inválido. Pode usar o valor sugerido.': 'Invalid payment per cycle. You can use the suggested amount.',
      'Selecione a conta da empresa para o desembolso.': 'Select the company account for the disbursement.',
      'A taxa de juro configurada para este tipo é inválida.': 'The configured interest rate for this type is invalid.',
      'Valor do empréstimo deve ser maior que zero.': 'The loan amount must be greater than zero.',
      'Pagamento por ciclo deve ser maior que zero.': 'The payment per cycle must be greater than zero.',
      'Está a usar modo Mensal com tipo de juro Diário. Verifique se é isso que pretende.': 'You are using Monthly mode with a Daily interest type. Check if that is what you want.',
      'Está a usar modo Diário com tipo de juro Mensal. Verifique se é isso que pretende.': 'You are using Daily mode with a Monthly interest type. Check if that is what you want.',
      'Neste momento apenas o método "Taxa fixa sobre saldo" (flat) está implementado.': 'At the moment only the "Fixed rate on balance" (flat) method is implemented.',
      'Preencha conta, data e valor do desembolso.': 'Fill in the account, date, and disbursement amount.',
      'Preencha tipo de reembolso, conta, data e valor do pagamento.': 'Fill in the repayment type, account, date, and payment amount.',
      'Falha ao criar conta.': 'Failed to create the account.',
      'Falha ao actualizar conta.': 'Failed to update the account.',
      'Falha ao desactivar conta.': 'Failed to disable the account.',
      'Falha ao actualizar status.': 'Failed to update the status.',
      'Falha ao registar despesa.': 'Failed to register the expense.',
      'Falha ao registar rendimento.': 'Failed to register the income.',
      'Falha ao actualizar utilizador.': 'Failed to update the user.',
      'Falha ao criar utilizador.': 'Failed to create the user.',
      'Falha ao criar grupo.': 'Failed to create the group.',
      'Falha ao confirmar empréstimo.': 'Failed to confirm the loan.',
      'Falha ao rejeitar empréstimo.': 'Failed to reject the loan.',
      'Falha ao registar desembolso.': 'Failed to register the disbursement.',
      'Falha ao registar pagamento.': 'Failed to register the payment.',
      'Falha ao carregar detalhes do membro.': 'Failed to load member details.',
      'Não foi possível actualizar o idioma.': 'Could not update the language.',
      'Não foi possível actualizar o formato monetário.': 'Could not update the currency format.',
      'Desactivar conta?': 'Disable account?',
      'Desactivar conta do cliente?': 'Disable client account?',
      'Activar conta do cliente?': 'Enable client account?',
      'Confirmar Empréstimo?': 'Confirm loan?',
      'Aprovar Empréstimo?': 'Approve loan?',
      'Rejeitar Empréstimo?': 'Reject loan?',
      'O empréstimo será aprovado e poderá ser desembolsado.': 'The loan will be approved and can then be disbursed.',
      'O empréstimo será aprovado e poderá seguir para desembolso.': 'The loan will be approved and can proceed to disbursement.',
      'Habilitar juros de mora para este empréstimo': 'Enable late interest for this loan',
      'Arraste contratos e outros documentos aqui': 'Drag contracts and other documents here',
      'ou clique para seleccionar vários ficheiros': 'or click to select multiple files',
      'PDF, imagens e documentos Office': 'PDF, images, and Office documents',
      'Nenhum documento seleccionado ainda.': 'No document selected yet.',
      'Remover documento': 'Remove document',
      'Activados': 'Enabled',
      'Desactivados': 'Disabled',
      'Esta acção irá marcar o empréstimo como rejeitado/cancelado.': 'This action will mark the loan as rejected/cancelled.',
      'Sim, desactivar': 'Yes, disable',
      'Sim, activar': 'Yes, enable',
      'Sim, confirmar': 'Yes, confirm',
      'Sim, aprovar': 'Yes, approve',
      'Sim, rejeitar': 'Yes, reject'
    }
  };
  var phraseTranslations = {
    en: {
      'Tem a certeza que pretende desactivar a conta "': 'Are you sure you want to disable the account "',
      'Tem a certeza que pretende <strong>': 'Are you sure you want to <strong>',
      '</strong> a conta de <strong>': '</strong> the account of <strong>',
      'desactivar': 'disable',
      'activar': 'enable'
    }
  };

  function getExactTranslations() {
    return exactTranslations[translationLanguage] || {};
  }

  function getPhraseTranslations() {
    return phraseTranslations[translationLanguage] || {};
  }

  function translate(value) {
    if (typeof value !== 'string' || !value) {
      return value;
    }

    var translatedValue = value;
    var normalizedValue = value.trim();
    var exactMap = getExactTranslations();
    var phraseMap = getPhraseTranslations();

    if (Object.prototype.hasOwnProperty.call(exactMap, normalizedValue)) {
      return exactMap[normalizedValue];
    }

    Object.keys(phraseMap)
      .sort(function (left, right) {
        return right.length - left.length;
      })
      .forEach(function (source) {
        translatedValue = translatedValue.split(source).join(phraseMap[source]);
      });

    return translatedValue;
  }

  function normalizeNumber(value) {
    if (value === null || value === undefined || value === '') {
      return null;
    }

    var numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue : null;
  }

  function formatNumber(value, decimals) {
    var normalizedValue = normalizeNumber(value);
    var totalDecimals = typeof decimals === 'number' ? decimals : 2;

    if (normalizedValue === null) {
      return '';
    }

    var decimalSeparator = currencyConfig.decimalSeparator || ',';
    var thousandsSeparator = currencyConfig.thousandsSeparator || '.';
    var sign = normalizedValue < 0 ? '-' : '';
    var absoluteValue = Math.abs(normalizedValue);
    var fixedValue = absoluteValue.toFixed(totalDecimals);
    var parts = fixedValue.split('.');
    var integerPart = parts[0];
    var fractionalPart = parts[1] || '';
    var groupedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSeparator);

    if (totalDecimals <= 0) {
      return sign + groupedInteger;
    }

    return sign + groupedInteger + decimalSeparator + fractionalPart;
  }

  function formatMoney(value, options) {
    var normalizedValue = normalizeNumber(value);
    var settings = options || {};
    var decimals = typeof settings.decimals === 'number' ? settings.decimals : 2;
    var includeSymbol = settings.symbol !== false;
    var emptyValue = Object.prototype.hasOwnProperty.call(settings, 'empty')
      ? settings.empty
      : '—';

    if (normalizedValue === null) {
      return emptyValue;
    }

    var formattedNumber = formatNumber(normalizedValue, decimals);
    if (!includeSymbol) {
      return formattedNumber;
    }

    var symbol = currencyConfig.symbol || 'MT';
    var symbolSpacing = currencyConfig.symbolSpacing || ' ';
    return symbol + symbolSpacing + formattedNumber;
  }

  function formatPercent(value, decimals) {
    var normalizedValue = normalizeNumber(value);
    if (normalizedValue === null) {
      return '';
    }

    return formatNumber(normalizedValue, typeof decimals === 'number' ? decimals : 2) + '%';
  }

  function padNumber(value) {
    return String(value).padStart(2, '0');
  }

  function formatDate(value, options) {
    var settings = options || {};
    var includeTime = settings.includeTime === true;
    var emptyValue = Object.prototype.hasOwnProperty.call(settings, 'empty')
      ? settings.empty
      : '—';

    if (value === null || value === undefined || value === '') {
      return emptyValue;
    }

    if (typeof value === 'string') {
      var isoMatch = value.match(
        /^(\d{4})-(\d{2})-(\d{2})(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?)?/
      );

      if (isoMatch) {
        var datePart = isoMatch[3] + '/' + isoMatch[2] + '/' + isoMatch[1];

        if (includeTime && isoMatch[4] && isoMatch[5]) {
          return datePart + ' ' + isoMatch[4] + ':' + isoMatch[5];
        }

        return datePart;
      }
    }

    var parsedDate = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(parsedDate.getTime())) {
      return value;
    }

    var formattedDate = [
      padNumber(parsedDate.getDate()),
      padNumber(parsedDate.getMonth() + 1),
      parsedDate.getFullYear()
    ].join('/');

    if (!includeTime) {
      return formattedDate;
    }

    return formattedDate + ' ' + padNumber(parsedDate.getHours()) + ':' + padNumber(parsedDate.getMinutes());
  }

  function translateSwalOptions(options) {
    var translatedOptions = Object.assign({}, options);
    [
      'title',
      'titleText',
      'text',
      'html',
      'footer',
      'confirmButtonText',
      'denyButtonText',
      'cancelButtonText',
      'inputLabel',
      'inputPlaceholder'
    ].forEach(function (key) {
      if (typeof translatedOptions[key] === 'string') {
        translatedOptions[key] = translate(translatedOptions[key]);
      }
    });

    return translatedOptions;
  }

  function patchSweetAlert() {
    if (!window.Swal || window.Swal.__molaLocalePatched) {
      return;
    }

    var nativeFire = window.Swal.fire.bind(window.Swal);

    window.Swal.fire = function () {
      if (!arguments.length) {
        return nativeFire();
      }

      if (
        typeof arguments[0] === 'object' &&
        arguments[0] !== null &&
        !Array.isArray(arguments[0])
      ) {
        return nativeFire(translateSwalOptions(arguments[0]));
      }

      var args = Array.prototype.slice.call(arguments);
      if (typeof args[0] === 'string') {
        args[0] = translate(args[0]);
      }
      if (typeof args[1] === 'string') {
        args[1] = translate(args[1]);
      }

      return nativeFire.apply(window.Swal, args);
    };

    window.Swal.__molaLocalePatched = true;
  }

  patchSweetAlert();
  document.addEventListener('DOMContentLoaded', patchSweetAlert);

  window.MolaLocale = {
    config: parsedConfig,
    currency: currencyConfig,
    formatDate: formatDate,
    formatMoney: formatMoney,
    formatNumber: formatNumber,
    formatPercent: formatPercent,
    language: translationLanguage,
    translate: translate
  };
}());
