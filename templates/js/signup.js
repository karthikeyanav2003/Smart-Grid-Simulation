const step1 = document.getElementById('formStep1');
const step2 = document.getElementById('formStep2');
const progressBarFill = document.getElementById('progressBarFill');
const stepIndicators = document.querySelectorAll('.step');

document.getElementById('toStep2').addEventListener('click', function() {
  // Basic validation for step 1
  const firstname = document.getElementById('firstname').value;
  const lastname = document.getElementById('lastname').value;
  const email = document.getElementById('email').value;
  const dob = document.getElementById('dob').value;
  
  if (!firstname || !lastname || !email || !dob) {
    // Show errors for empty fields
    if (!firstname) document.getElementById('firstname-error').style.display = 'block';
    if (!lastname) document.getElementById('lastname-error').style.display = 'block';
    if (!email) document.getElementById('email-error').style.display = 'block';
    if (!dob) document.getElementById('dob-error').style.display = 'block';
    return;
  }
  
  // Hide all error messages
  document.querySelectorAll('.error-message').forEach(el => el.style.display = 'none');
  
  // Go to step 2
  step1.classList.remove('active');
  step2.classList.add('active');
  progressBarFill.style.width = '100%';
  stepIndicators[0].classList.add('completed');
  stepIndicators[1].classList.add('active');
});

document.getElementById('backToStep1').addEventListener('click', function() {
  step2.classList.remove('active');
  step1.classList.add('active');
  progressBarFill.style.width = '0%';
  stepIndicators[0].classList.remove('completed');
  stepIndicators[1].classList.remove('active');
});

// Form submission validation
document.getElementById('signupForm').addEventListener('submit', function(e) {
  const username = document.getElementById('signup-username').value;
  const password = document.getElementById('signup-password').value;
  const confirmPassword = document.getElementById('confirm-password').value;
  
  // Validate username
  if (username.length < 4) {
    e.preventDefault();
    document.getElementById('username-error').style.display = 'block';
    return;
  }
  
  // Validate password
  if (password.length < 8) {
    e.preventDefault();
    document.getElementById('password-error').style.display = 'block';
    return;
  }
  
  // Check if passwords match
  if (password !== confirmPassword) {
    e.preventDefault();
    document.getElementById('confirm-password-error').style.display = 'block';
    return;
  }
});

// Password strength indicator
document.getElementById('signup-password').addEventListener('input', function() {
  const password = this.value;
  const strengthFill = document.getElementById('passwordStrength');
  const feedback = document.getElementById('passwordFeedback');
  
  // Simple password strength logic
  let strength = 0;
  if (password.length >= 8) strength += 25;
  if (password.match(/[A-Z]/)) strength += 25;
  if (password.match(/[0-9]/)) strength += 25;
  if (password.match(/[^A-Za-z0-9]/)) strength += 25;
  
  strengthFill.style.width = strength + '%';
  
  // Set color based on strength
  if (strength < 50) {
    strengthFill.style.backgroundColor = '#e74c3c';
    feedback.textContent = 'Weak password';
    feedback.style.color = '#e74c3c';
  } else if (strength < 75) {
    strengthFill.style.backgroundColor = '#f39c12';
    feedback.textContent = 'Moderate password';
    feedback.style.color = '#f39c12';
  } else {
    strengthFill.style.backgroundColor = '#2ecc71';
    feedback.textContent = 'Strong password';
    feedback.style.color = '#2ecc71';
  }
});