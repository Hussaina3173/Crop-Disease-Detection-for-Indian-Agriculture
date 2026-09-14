(function () {
  var loginView = document.getElementById('login-view');
  var appView = document.getElementById('app-view');
  var loginForm = document.getElementById('login-form');
  var loginError = document.getElementById('login-error');
  var greeting = document.getElementById('greeting');
  var logoutBtn = document.getElementById('logout-btn');
  var registerForm = document.getElementById('register-form');
  var forgotForm = document.getElementById('forgot-form');
  var loginNotice = document.getElementById('login-notice');
  var authForms = document.querySelectorAll('.login-form');
  var resetDestination = document.getElementById('reset-destination');
  var resetCountryCode = document.getElementById('reset-country-code');
  var resetPhoneField = resetDestination ? resetDestination.closest('.field') : null;
  var resetCodeInput = document.createElement('input');
  var resetNewPasswordInput = document.createElement('input');
  var resetStage = false;
  var dropzone = document.getElementById('dropzone');
  var fileInput = document.getElementById('file-input');
  var previewBlock = document.getElementById('preview-block');
  var previewImg = document.getElementById('preview-img');
  var previewName = document.getElementById('preview-name');
  var analyzeBtn = document.getElementById('analyze-btn');
  var clearBtn = document.getElementById('clear-btn');
  var resultEmpty = document.getElementById('result-empty');
  var resultLoading = document.getElementById('result-loading');
  var resultContent = document.getElementById('result-content');
  var currentFile = null;
  var currentObjectUrl = null;
  var latestPrediction = null;

  document.querySelectorAll('input[type="password"]').forEach(function (input) {
    var wrapper = document.createElement('div');
    var toggle = document.createElement('button');
    wrapper.className = 'password-field';
    toggle.type = 'button';
    toggle.className = 'password-toggle';
    toggle.setAttribute('aria-label', 'Show password');
    toggle.title = 'Show password';
    toggle.innerHTML = '<svg class="eye-open" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg><svg class="eye-closed hidden" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m3 3 18 18M10.6 6.2A10.7 10.7 0 0 1 12 6c6 0 9.5 6 9.5 6a17 17 0 0 1-3.1 3.8M6.2 6.8C3.8 8.2 2.5 12 2.5 12s3.5 6 9.5 6c.8 0 1.6-.1 2.3-.3"/></svg>';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    wrapper.appendChild(toggle);
    toggle.addEventListener('click', function () {
      var visible = input.type === 'text';
      input.type = visible ? 'password' : 'text';
      toggle.setAttribute('aria-label', visible ? 'Show password' : 'Hide password');
      toggle.title = visible ? 'Show password' : 'Hide password';
      toggle.querySelector('.eye-open').classList.toggle('hidden', !visible);
      toggle.querySelector('.eye-closed').classList.toggle('hidden', visible);
    });
  });

  loginForm.addEventListener('submit', async function (event) {
    event.preventDefault();
    var id = document.getElementById('farmer-id').value.trim().toLowerCase();
    var password = document.getElementById('password').value.trim();
    try {
      var response = await fetch('/api/auth/login', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({identifier: id, password: password}) });
      var result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Log in failed');
      greeting.textContent = 'Welcome, ' + result.user.name;
      loginView.classList.add('hidden'); appView.classList.remove('hidden');
    } catch (error) { loginError.textContent = error.message; loginError.classList.remove('hidden'); }
  });

  function showAuthForm(form) { authForms.forEach(function (item) { item.classList.add('hidden'); }); form.classList.remove('hidden'); }
  document.getElementById('show-register-btn').addEventListener('click', function () { showAuthForm(registerForm); });
  document.getElementById('show-login-btn').addEventListener('click', function () { showAuthForm(loginForm); });
  document.getElementById('forgot-password-btn').addEventListener('click', function () { showAuthForm(forgotForm); });
  document.getElementById('cancel-forgot-btn').addEventListener('click', function () { showAuthForm(loginForm); });

  if (resetDestination && resetCountryCode) {
    var recoveryChoice = document.createElement('div');
    recoveryChoice.className = 'recovery-choice';
    recoveryChoice.innerHTML = '<button type="button" class="choice-button active" id="reset-email-choice">Email</button><button type="button" class="choice-button" id="reset-mobile-choice">Mobile SMS</button>';
    var resetLabel = resetDestination.closest('.field').querySelector('label');
    resetLabel.parentNode.insertBefore(recoveryChoice, resetLabel.nextSibling);
    var phoneWrapper = resetCountryCode.parentNode;
    var emailChoice = recoveryChoice.querySelector('#reset-email-choice');
    var mobileChoice = recoveryChoice.querySelector('#reset-mobile-choice');
    function setRecoveryChannel(channel) {
      var mobile = channel === 'mobile';
      emailChoice.classList.toggle('active', !mobile); mobileChoice.classList.toggle('active', mobile);
      resetCountryCode.classList.toggle('hidden', !mobile);
      resetDestination.type = mobile ? 'tel' : 'email';
      resetDestination.inputMode = mobile ? 'numeric' : 'email';
      resetDestination.placeholder = mobile ? '98765 43210' : 'you@example.com';
      resetLabel.textContent = mobile ? 'Mobile number' : 'Email address';
      if (mobile) phoneWrapper.classList.add('phone-field'); else phoneWrapper.classList.remove('phone-field');
    }
    emailChoice.addEventListener('click', function () { setRecoveryChannel('email'); });
    mobileChoice.addEventListener('click', function () { setRecoveryChannel('mobile'); });
    setRecoveryChannel('email');
  }

  registerForm.addEventListener('submit', async function (event) {
    event.preventDefault();
    var errorBox = document.getElementById('register-error');
    var mobileNumber = document.getElementById('register-mobile').value.replace(/\D/g, '');
    var payload = {name: document.getElementById('register-name').value.trim(), email: document.getElementById('register-email').value.trim().toLowerCase(), mobile: mobileNumber ? document.getElementById('register-country-code').value + mobileNumber : '', password: document.getElementById('register-password').value};
    try { var response = await fetch('/api/auth/register', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)}); var result = await response.json(); if (!response.ok) throw new Error(result.error); loginForm.reset(); document.getElementById('farmer-id').value = payload.email || payload.mobile; loginNotice.textContent = 'Account created successfully. Log in with your new password.'; loginNotice.classList.remove('hidden'); showAuthForm(loginForm); } catch (error) { errorBox.textContent = error.message; errorBox.classList.remove('hidden'); }
  });

  forgotForm.addEventListener('submit', async function (event) {
    event.preventDefault();
    var errorBox = document.getElementById('forgot-error');
    if (resetStage) {
      var resetDestinationValue = resetDestination.value.indexOf('@') === -1 ? document.getElementById('reset-country-code').value + resetDestination.value.replace(/\D/g, '') : resetDestination.value.trim().toLowerCase();
      try { var resetResponse = await fetch('/api/auth/reset-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({destination: resetDestinationValue, token: resetCodeInput.value.trim(), new_password: resetNewPasswordInput.value})}); var resetResult = await resetResponse.json(); if (!resetResponse.ok) throw new Error(resetResult.error); errorBox.textContent = resetResult.message; errorBox.classList.remove('hidden'); resetStage = false; forgotForm.querySelector('button[type="submit"]').textContent = 'Send reset instructions'; resetCodeInput.required = false; resetNewPasswordInput.required = false; resetCodeInput.closest('.field').classList.add('hidden'); resetNewPasswordInput.closest('.field').classList.add('hidden'); } catch (error) { errorBox.textContent = error.message; errorBox.classList.remove('hidden'); }
      return;
    }
    var destinationInput = document.getElementById('reset-destination');
    var destination = destinationInput.value.indexOf('@') === -1 ? document.getElementById('reset-country-code').value + destinationInput.value.replace(/\D/g, '') : destinationInput.value.trim().toLowerCase();
    try { var response = await fetch('/api/auth/forgot-password', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({destination: destination})}); var result = await response.json(); if (!response.ok) throw new Error(result.error); errorBox.textContent = result.message + (result.development_token ? ' Check your email for the 6-digit code.' : ' Check your email or phone for the 6-digit code.'); errorBox.classList.remove('hidden'); resetStage = true; resetCodeInput.required = true; resetNewPasswordInput.required = true; forgotForm.querySelector('button[type="submit"]').textContent = 'Reset password'; resetCodeInput.closest('.field').classList.remove('hidden'); resetNewPasswordInput.closest('.field').classList.remove('hidden'); } catch (error) { errorBox.textContent = error.message; errorBox.classList.remove('hidden'); }
  });

  function addResetField(input, labelText, placeholder, type) {
    var field = document.createElement('div'); field.className = 'field hidden';
    var label = document.createElement('label'); label.textContent = labelText; field.appendChild(label);
    input.type = type; input.placeholder = placeholder; input.required = false; input.autocomplete = type === 'password' ? 'new-password' : 'one-time-code'; field.appendChild(input);
    forgotForm.querySelector('.btn-primary').parentNode.insertBefore(field, forgotForm.querySelector('.btn-primary'));
    return field;
  }
  addResetField(resetCodeInput, '6-digit reset code', '123456', 'text');
  addResetField(resetNewPasswordInput, 'New password', 'At least 8 characters', 'password');

  logoutBtn.addEventListener('click', function () {
    appView.classList.add('hidden'); loginView.classList.remove('hidden'); loginForm.reset(); resetUpload();
  });
  dropzone.addEventListener('click', function () { fileInput.click(); });
  dropzone.addEventListener('dragover', function (event) { event.preventDefault(); dropzone.classList.add('drag-over'); });
  dropzone.addEventListener('dragleave', function () { dropzone.classList.remove('drag-over'); });
  dropzone.addEventListener('drop', function (event) { event.preventDefault(); dropzone.classList.remove('drag-over'); if (event.dataTransfer.files[0]) handleFile(event.dataTransfer.files[0]); });
  fileInput.addEventListener('change', function () { if (fileInput.files[0]) handleFile(fileInput.files[0]); });
  clearBtn.addEventListener('click', resetUpload);

  function handleFile(file) {
    if (!/^image\/(png|jpeg)$/.test(file.type)) { window.alert('Please choose a JPG or PNG image.'); return; }
    if (file.size > 10 * 1024 * 1024) { window.alert('Please choose an image smaller than 10MB.'); return; }
    if (currentObjectUrl) URL.revokeObjectURL(currentObjectUrl);
    currentFile = file; currentObjectUrl = URL.createObjectURL(file);
    previewImg.src = currentObjectUrl; previewName.textContent = file.name;
    previewBlock.classList.remove('hidden'); clearBtn.classList.remove('hidden'); analyzeBtn.disabled = false;
    resultEmpty.classList.remove('hidden'); resultLoading.classList.add('hidden'); resultContent.classList.add('hidden');
  }

  function resetUpload() {
    fileInput.value = ''; currentFile = null; latestPrediction = null;
    if (currentObjectUrl) { URL.revokeObjectURL(currentObjectUrl); currentObjectUrl = null; }
    previewBlock.classList.add('hidden'); clearBtn.classList.add('hidden'); analyzeBtn.disabled = true;
    resultEmpty.classList.remove('hidden'); resultLoading.classList.add('hidden'); resultContent.classList.add('hidden');
  }

  analyzeBtn.addEventListener('click', async function () {
    if (!currentFile) return;
    resultEmpty.classList.add('hidden'); resultContent.classList.add('hidden'); resultLoading.classList.remove('hidden'); analyzeBtn.disabled = true;
    var formData = new FormData(); formData.append('image', currentFile);
    try {
      var response = await fetch('/api/analyze', { method: 'POST', body: formData });
      var result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Analysis failed');
      latestPrediction = result;
      renderResult(result);
    } catch (error) {
      renderError(error.message);
    } finally {
      resultLoading.classList.add('hidden'); resultContent.classList.remove('hidden'); analyzeBtn.disabled = false;
    }
  });

  function escapeHtml(value) { return String(value).replace(/[&<>'"]/g, function (character) { return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]; }); }
  function renderResult(result) {
    var percent = Math.round(result.confidence * 100);
    var statusClass = result.uncertain ? 'uncertain' : (result.healthy ? 'healthy' : 'disease');
    var statusLabel = result.uncertain ? 'Needs visual model' : (result.healthy ? 'Healthy' : 'Disease detected');
    var recommendations = (result.recommendations || []).map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join('');
    resultContent.innerHTML = '<span class="result-status ' + statusClass + '"><span class="dot"></span>' + statusLabel + '</span>' +
      '<h3 class="disease-name">' + escapeHtml(result.disease) + '</h3>' +
      '<div class="result-crop">Crop identified: ' + escapeHtml(result.crop) + '</div>' +
      '<div class="confidence-block"><div class="confidence-label"><span>' + (result.uncertain ? 'Screening confidence' : 'Model confidence') + '</span><span>' + percent + '%</span></div><div class="confidence-track"><div class="confidence-fill" style="width:' + percent + '%"></div></div></div>' +
      '<div class="recommend-block"><h4>Recommended action</h4><ul>' + recommendations + '</ul></div>' +
      '<div class="result-note">Provider: ' + escapeHtml(result.provider || 'local_model') + '<br>' + escapeHtml(result.note || 'Prediction returned by the trained model.') + '</div>';
  }
  function renderError(message) {
    resultContent.innerHTML = '<span class="result-status disease"><span class="dot"></span>Analysis unavailable</span><h3 class="disease-name">No diagnosis returned</h3><div class="result-note">' + escapeHtml(message) + '</div>';
  }

  var chatForm = document.getElementById('chat-form');
  var chatQuestion = document.getElementById('chat-question');
  var chatLog = document.getElementById('chat-log');
  chatForm.addEventListener('submit', async function (event) {
    event.preventDefault();
    var question = chatQuestion.value.trim();
    if (!question) return;
    addChatMessage(question, 'user');
    chatQuestion.value = '';
    try {
      var context = latestPrediction ? 'Latest image diagnosis: crop=' + latestPrediction.crop + ', disease=' + latestPrediction.disease + ', confidence=' + latestPrediction.confidence + ', provider=' + latestPrediction.provider : 'The user has not analyzed an image yet.';
      var chatData = new FormData();
      chatData.append('question', question);
      chatData.append('context', context);
      if (currentFile) chatData.append('image', currentFile);
      var response = await fetch('/api/chat', { method: 'POST', body: chatData });
      var result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Chat request failed');
      addChatMessage(result.answer, 'bot');
    } catch (error) {
      addChatMessage(error.message, 'bot');
    }
    loadChatKpis();
  });

  function addChatMessage(message, role) {
    var empty = chatLog.querySelector('.chat-empty');
    if (empty) empty.remove();
    var item = document.createElement('p');
    item.className = 'chat-message ' + role;
    item.textContent = message;
    chatLog.appendChild(item);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  async function loadChatKpis() {
    try {
      var response = await fetch('/api/chat/kpis');
      var metrics = await response.json();
      document.getElementById('kpi-total').textContent = metrics.total_queries;
      document.getElementById('kpi-gemini').textContent = metrics.gemini_queries;
      document.getElementById('kpi-latency').textContent = metrics.average_latency_seconds + 's';
    } catch (error) {
      // KPI display is supplemental and should not block diagnosis workflows.
    }
  }
  loadChatKpis();
}());